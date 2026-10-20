"""Offline archive-first contract tests; fixture digests are pinned before load."""

import csv
import hashlib
import importlib
import io
import json
import os
import pickle
import subprocess
import sys
import tarfile
import threading
import types
from collections import OrderedDict, namedtuple
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

from ess_research.arecel.__main__ import main
from ess_research.task_paths import (
    ConfigurationError,
    configured_root,
    runtime_runs,
    worktree_path,
)

etl = importlib.import_module("ess_research.arecel.archive")


@pytest.fixture
def roots(tmp_path, monkeypatch):
    paths = {
        "ESS_DATA_ROOT": tmp_path / "cache",
        "ESS_RUNTIME_PARENT": tmp_path / "runtime",
        "ESS_WORKTREE_PARENT": tmp_path / "worktrees",
    }
    for name, value in paths.items():
        monkeypatch.setenv(name, str(value))
    return paths


def archive_bytes(
    monkeypatch,
    dataset="census13",
    *,
    missing=None,
    duplicate=False,
    invalid_label=False,
):
    # Model the actual upstream globals; no pickle is loaded during fixture creation.
    for name in ("lecarb", "lecarb.workload", "lecarb.workload.workload"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    module = sys.modules["lecarb.workload.workload"]
    module.Query = namedtuple("Query", "predicates ncols", module=module.__name__)
    module.Label = namedtuple(
        "Label", "cardinality selectivity", module=module.__name__
    )
    source_columns, columns, _ = etl._schema(dataset)
    predicates = OrderedDict()
    cells = []
    for index, (name, (_, column_type)) in enumerate(
        zip(source_columns, columns, strict=True)
    ):
        value = 7.5 if column_type == "DOUBLE PRECISION" else "O'Brien\\town"
        cells.append(value)
        predicates[name] = (
            ("[]", (1.25, 8.5))
            if index == 0 and column_type == "DOUBLE PRECISION"
            else ("=", value)
        )
    queries = [module.Query(predicates, len(predicates))]
    labels = [module.Label(-1 if invalid_label else 17, 0.25)]
    splits = ("valid", "test") if dataset == "forest10" else ("train", "valid", "test")
    text = io.StringIO(newline="")
    writer = csv.writer(text)
    writer.writerow(source_columns)
    writer.writerow(cells)
    files = {
        f"data/{dataset}/original.csv": text.getvalue().encode(),
        f"data/{dataset}/workload/base.pkl": pickle.dumps(
            dict.fromkeys(splits, queries)
        ),
        f"data/{dataset}/workload/base-original-label.pkl": pickle.dumps(
            dict.fromkeys(splits, labels)
        ),
    }
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w:gz") as archive:
        for name, value in files.items():
            if name.endswith(missing or "NEVER"):
                continue
            member = tarfile.TarInfo(name)
            member.size = len(value)
            archive.addfile(member, io.BytesIO(value))
            if duplicate and name.endswith("original.csv"):
                archive.addfile(member, io.BytesIO(value))
        # Unrelated members are never extracted, even if their names escape.
        member = tarfile.TarInfo("../../outside")
        member.size = 6
        archive.addfile(member, io.BytesIO(b"ignore"))
    return output.getvalue()


@contextmanager
def server(payload, *, fail=False):
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            requests.append(self.path)
            self.send_response(200)
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload[:10] if fail else payload)
            self.close_connection = True

        def log_message(self, *args):
            pass

    httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{httpd.server_port}/archive", requests
    finally:
        httpd.shutdown()
        httpd.server_close()
        thread.join()


def pin(monkeypatch, payload):
    monkeypatch.setattr(etl, "ARCHIVE_SHA256", hashlib.sha256(payload).hexdigest())


def cached(roots, monkeypatch, payload):
    pin(monkeypatch, payload)
    roots["ESS_DATA_ROOT"].mkdir()
    path = roots["ESS_DATA_ROOT"] / "arecel-data.tar.gz"
    path.write_bytes(payload)
    return path


@pytest.mark.parametrize("dataset", etl.DATASETS)
def test_zero_start_each_dataset_alone(roots, monkeypatch, dataset):
    payload = archive_bytes(monkeypatch, dataset)
    pin(monkeypatch, payload)
    with server(payload) as (url, requests):
        monkeypatch.setattr(etl, "DOWNLOAD_URL", url)
        with etl.prepare(issue=53, dataset=dataset) as prepared:
            run, derived = prepared.run_root, prepared.dataset_root
            assert derived.is_relative_to(
                roots["ESS_RUNTIME_PARENT"] / "ess-research/issue53/runs"
            )
            assert prepared.csv.is_file()
            manifest = json.loads((derived / "manifest.json").read_text())
            assert manifest["archive_sha256"] == hashlib.sha256(payload).hexdigest()
            assert manifest["config"]["seed"] is None
            assert set(manifest["splits"]) == (
                {"valid", "test"}
                if dataset == "forest10"
                else {"train", "valid", "test"}
            )
            for split in manifest["splits"]:
                workload = json.loads((derived / split / "workload.json").read_text())
                truth = json.loads((derived / split / "truth.json").read_text())
                query, label = workload["queries"][0], truth["queries"][0]
                assert (
                    query["query_id"]
                    == label["query_id"]
                    == f"arecel:{dataset}:{split}:000000"
                )
                assert (
                    "true_cardinality" not in query
                    and "source_selectivity" not in query
                )
                assert label["true_cardinality"] == 17
                assert label["source_selectivity"] == 0.25
                assert query["sql"].startswith(f"SELECT * FROM public.{dataset} WHERE ")
                assert query["source_sql"].startswith("SELECT COUNT(*) FROM ")
                assert list(p["column"] for p in query["predicates"]) == list(
                    etl._schema(dataset)[0]
                )
                if dataset in {"census13", "dmv11"}:
                    assert "E'O''Brien\\\\town'" in query["sql"]
                if dataset != "dmv11":
                    assert "between 1.25 and 8.5" in query["sql"]
            assert (
                '"' + etl._schema(dataset)[1][0][0] + '"'
                in (derived / "schema.sql").read_text()
            )
        assert not derived.exists()
        assert json.loads((run / "logs/status.json").read_text())["status"] == "success"
        assert requests == ["/archive"]
    assert [p.name for p in roots["ESS_DATA_ROOT"].iterdir()] == ["arecel-data.tar.gz"]
    assert not (roots["ESS_RUNTIME_PARENT"] / "outside").exists()


def test_offline_cache_and_distinct_runs(roots, monkeypatch):
    payload = archive_bytes(monkeypatch)
    cached(roots, monkeypatch, payload)
    monkeypatch.setattr(
        etl, "urlopen", lambda *a, **k: pytest.fail("network on cache hit")
    )
    monkeypatch.delenv("ESS_WORKTREE_PARENT")
    with etl.prepare(issue=53, dataset="census13") as first:
        with etl.prepare(issue=54, dataset="census13", keep_scratch=True) as second:
            with etl.prepare(issue=53, dataset="census13") as third:
                assert len({first.run_root, second.run_root, third.run_root}) == 3
                assert first.csv.exists()
    assert not first.csv.exists()
    assert second.csv.exists()
    assert not third.csv.exists()


@pytest.mark.parametrize("variable", ["ESS_DATA_ROOT", "ESS_RUNTIME_PARENT"])
@pytest.mark.parametrize("value", [None, "", "relative", "/"])
def test_bad_roots_fail_before_any_io(roots, monkeypatch, variable, value):
    if value is None:
        monkeypatch.delenv(variable)
    else:
        monkeypatch.setenv(variable, value)
    monkeypatch.setattr(etl, "_archive", lambda *a: pytest.fail("archive accessed"))
    with pytest.raises(ConfigurationError, match="~/.bashrc"):
        with etl.prepare(issue=53, dataset="census13"):
            pass
    assert not roots["ESS_DATA_ROOT"].exists()
    assert not roots["ESS_RUNTIME_PARENT"].exists()


def test_file_root_and_overlap_rejected(roots, monkeypatch, tmp_path):
    invalid = tmp_path / "file"
    invalid.write_text("owned")
    monkeypatch.setenv("ESS_RUNTIME_PARENT", str(invalid / "child"))
    with pytest.raises(ConfigurationError, match="not a directory"):
        configured_root("ESS_RUNTIME_PARENT")
    monkeypatch.setenv("ESS_RUNTIME_PARENT", str(roots["ESS_DATA_ROOT"] / "runtime"))
    with pytest.raises(ConfigurationError, match="disjoint"):
        with etl.prepare(issue=53, dataset="census13"):
            pass


def test_worktree_only_checks_its_root(roots, monkeypatch):
    monkeypatch.delenv("ESS_DATA_ROOT")
    monkeypatch.delenv("ESS_RUNTIME_PARENT")
    assert (
        worktree_path("ess-research", 53)
        == roots["ESS_WORKTREE_PARENT"] / "ess-research-issue53"
    )
    assert not roots["ESS_WORKTREE_PARENT"].exists()
    for issue in (0, -1, True, None, "53"):
        with pytest.raises(ConfigurationError):
            worktree_path("ess-research", issue)
    with pytest.raises(ConfigurationError):
        worktree_path("../escape", 53)
    monkeypatch.delenv("ESS_WORKTREE_PARENT")
    with pytest.raises(ConfigurationError, match="ESS_WORKTREE_PARENT"):
        worktree_path("ess-research", 53)


def test_import_without_any_configuration(monkeypatch):
    env = {
        key: value for key, value in os.environ.items() if not key.startswith("ESS_")
    }
    env["PYTHONPATH"] = str(Path(__file__).parents[1] / "src")
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import ess_research.arecel; import ess_research.task_paths",
        ],
        env=env,
        check=True,
    )


def test_wrong_existing_hash_never_downloads_or_unpickles(roots, monkeypatch):
    path = cached(roots, monkeypatch, archive_bytes(monkeypatch))
    path.write_bytes(b"wrong")
    monkeypatch.setattr(
        etl, "urlopen", lambda *a, **k: pytest.fail("download attempted")
    )
    monkeypatch.setattr(
        etl, "_outputs", lambda *a: pytest.fail("untrusted archive opened")
    )
    with pytest.raises(etl.PreparationError, match="SHA-256 mismatch"):
        with etl.prepare(issue=53, dataset="census13"):
            pass
    assert path.read_bytes() == b"wrong"


@pytest.mark.parametrize("failure", ["hash", "partial", "interrupt", "network"])
def test_failed_download_is_not_published(roots, monkeypatch, failure):
    payload = archive_bytes(monkeypatch)
    pin(monkeypatch, payload)
    monkeypatch.setattr(
        etl, "_outputs", lambda *a: pytest.fail("untrusted bytes opened")
    )
    with server(
        b"bad" if failure == "hash" else payload, fail=failure == "partial"
    ) as (url, _):
        monkeypatch.setattr(etl, "DOWNLOAD_URL", url)
        if failure in {"interrupt", "network"}:

            def fail(*args, **kwargs):
                raise (
                    KeyboardInterrupt()
                    if failure == "interrupt"
                    else OSError("network failed")
                )

            monkeypatch.setattr(etl, "urlopen", fail)
        with pytest.raises((etl.PreparationError, KeyboardInterrupt, OSError)):
            with etl.prepare(issue=53, dataset="census13"):
                pass
    assert list(roots["ESS_DATA_ROOT"].iterdir()) == []
    (run,) = runtime_runs("ess-research", 53).iterdir()
    assert (run / "logs/error.json").exists()
    assert not (run / "derived").exists()


def test_parallel_first_download(roots, monkeypatch):
    payload = archive_bytes(monkeypatch)
    pin(monkeypatch, payload)
    barrier = threading.Barrier(2)
    opener = etl.urlopen

    def synchronized_open(*args, **kwargs):
        barrier.wait(timeout=10)
        return opener(*args, **kwargs)

    monkeypatch.setattr(etl, "urlopen", synchronized_open)
    with server(payload) as (url, requests):
        monkeypatch.setattr(etl, "DOWNLOAD_URL", url)

        def run():
            with etl.prepare(issue=53, dataset="census13") as result:
                assert result.csv.exists()
                return result.run_root

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run) for _ in range(2)]
            assert len({future.result() for future in futures}) == 2
        assert len(requests) == 2
    (target,) = roots["ESS_DATA_ROOT"].iterdir()
    assert target.read_bytes() == payload


@pytest.mark.parametrize("kind", ["missing", "duplicate", "label"])
def test_format_errors_retain_diagnostics(roots, monkeypatch, kind):
    payload = archive_bytes(
        monkeypatch,
        missing="base.pkl" if kind == "missing" else None,
        duplicate=kind == "duplicate",
        invalid_label=kind == "label",
    )
    cached(roots, monkeypatch, payload)
    with pytest.raises(etl.PreparationError):
        with etl.prepare(issue=53, dataset="census13"):
            pass
    (run,) = runtime_runs("ess-research", 53).iterdir()
    assert (run / "logs/error.json").exists()
    assert not (run / "derived").exists()


def test_consumption_failure_only_cleans_owned_derived(roots, monkeypatch):
    cached(roots, monkeypatch, archive_bytes(monkeypatch))
    sentinel = roots["ESS_RUNTIME_PARENT"] / "historical" / "pgdata"
    sentinel.mkdir(parents=True)
    (sentinel / "owned-by-other").write_text("preserve")
    with pytest.raises(RuntimeError, match="consumer failed"):
        with etl.prepare(issue=53, dataset="census13") as prepared:
            (prepared.dataset_root / "outside-link").symlink_to(
                sentinel, target_is_directory=True
            )
            (prepared.run_root / "results/science.json").write_text(
                "observed elsewhere"
            )
            (prepared.run_root / "pgdata").mkdir()
            raise RuntimeError("consumer failed")
    assert not prepared.dataset_root.exists()
    assert (sentinel / "owned-by-other").read_text() == "preserve"
    assert (prepared.run_root / "pgdata").exists()
    assert (prepared.run_root / "results/science.json").exists()
    assert (
        json.loads((prepared.run_root / "logs/status.json").read_text())["status"]
        == "failed"
    )


def test_replaced_derived_not_deleted(roots, monkeypatch):
    cached(roots, monkeypatch, archive_bytes(monkeypatch))
    with etl.prepare(issue=53, dataset="census13") as prepared:
        prepared.dataset_root.rename(prepared.run_root / "moved")
        prepared.dataset_root.mkdir()
        (prepared.dataset_root / "unknown").write_text("preserve")
    assert (prepared.dataset_root / "unknown").exists()


def test_cli_runs_consumer_before_cleanup(roots, monkeypatch, capsys):
    cached(roots, monkeypatch, archive_bytes(monkeypatch))
    code = "import os,pathlib; p=pathlib.Path(os.environ['ESS_ARECEL_DATASET_ROOT']); assert (p/'valid/workload.json').exists(); assert pathlib.Path(os.environ['ESS_ISSUE_ROOT'])==p.parent"
    assert (
        main(
            [
                "prepare",
                "--issue",
                "53",
                "--dataset",
                "census13",
                "--",
                sys.executable,
                "-c",
                code,
            ]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert not Path(result["dataset_root"]).exists()
    assert (
        main(
            [
                "prepare",
                "--issue",
                "53",
                "--dataset",
                "census13",
                "--",
                sys.executable,
                "-c",
                "raise SystemExit(7)",
            ]
        )
        == 1
    )


def test_cli_explicit_retention(roots, monkeypatch, capsys):
    cached(roots, monkeypatch, archive_bytes(monkeypatch))
    assert (
        main(["prepare", "--issue", "53", "--dataset", "census13", "--keep-scratch"])
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert Path(result["dataset_root"]).exists()
    with pytest.raises(SystemExit):
        main(["prepare", "--issue", "53", "--dataset", "census13"])


def test_runtime_symlink_cannot_redirect_into_cache(roots, monkeypatch):
    roots["ESS_DATA_ROOT"].mkdir()
    roots["ESS_RUNTIME_PARENT"].mkdir()
    (roots["ESS_RUNTIME_PARENT"] / "ess-research").symlink_to(
        roots["ESS_DATA_ROOT"], target_is_directory=True
    )
    with pytest.raises(ConfigurationError, match="symlink"):
        with etl.prepare(issue=53, dataset="census13"):
            pass
    assert list(roots["ESS_DATA_ROOT"].iterdir()) == []


@pytest.mark.parametrize("operator", ["=", "<", "<=", ">", ">="])
def test_exact_predicate_rendering_and_unconstrained_columns(operator):
    query = etl.Query(
        OrderedDict(
            [
                ("Elevation", (operator, 4)),
                ("Aspect", None),
                ("Slope", ("[]", (1.5, 3))),
            ]
        ),
        2,
    )
    result = etl._query(query, "forest10")
    assert (
        result["source_sql"]
        == f'SELECT COUNT(*) FROM public."forest10_original" WHERE "Elevation" {operator} 4 AND "Slope" between 1.5 and 3;'
    )
    assert (
        result["sql"]
        == f'SELECT * FROM public.forest10 WHERE "elevation" {operator} 4 AND "slope" between 1.5 and 3;'
    )


def test_public_api_and_legacy_import_are_lazy():
    code = "import sys; from ess_research.arecel import prepare; assert callable(prepare); from ess_research.arecel import prepare as again; assert prepare is again"
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).parents[1] / "src"))
    subprocess.run([sys.executable, "-c", code], env=env, check=True)
    result = subprocess.run(
        [sys.executable, "-m", "ess_research.arecel.forest10", "--help"],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert "RuntimeWarning" not in result.stderr
