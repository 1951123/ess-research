"""Run the approved Forest10 official-test Q1 evaluation on frozen selections."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))

from ess_research.arecel import archive as arecel_archive
from ess_research.arecel.candidates import discover_candidates
from ess_research.arecel.forest10 import EXPECTED_ROWS, SOURCE_COLUMNS
from ess_research.task_paths import configured_root, runtime_runs
import forest10_runner as runner
import run_forest10_setup_pilot as pilot

PLAN_PATH = HERE / "forest10-test-evaluation-plan-v1.json"
PLAN_SHA256 = "bafee85b8d8be674c045610362f9a1af34eda3993f169c09a64c7df3aeb23f86"
SELECTION_PATH = HERE / "forest10-valid-frozen-selection-v1.json"
SELECTION_SHA256 = "10bcf1f6026aa4de025cbef360c8302aafb2f082d49138c4c5da2d1331f4c798"
RUN_PREFIX = "f10-test-eval-"
PG_SPEC = "f1bf37b5dd3d3a7087fc0af5de550ca31035854c"
ARECEL_ARCHIVE_SHA = "5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79"
HARD_WALL = 8 * 60 * 60
SOFT_WALL = 7 * 60 * 60 + 30 * 60
HARD_DISK = 4 * 1024**3
SOFT_DISK = 3 * 1024**3


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _frozen_inputs() -> tuple[dict[str, Any], dict[str, Any]]:
    if sha256(PLAN_PATH) != PLAN_SHA256:
        raise RuntimeError("test evaluation plan hash mismatch")
    if sha256(SELECTION_PATH) != SELECTION_SHA256:
        raise RuntimeError("frozen valid-selection hash mismatch")
    plan = json.loads(PLAN_PATH.read_text(encoding="utf-8"))
    frozen = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    if plan.get("status") != "FROZEN_BEFORE_TEST_OUTCOME_ACCESS":
        raise RuntimeError("test evaluation plan is not frozen")
    expected = plan.get("frozen_selection", {}).get("selected_sets", {})
    for method in ("Nominal", "PESS"):
        for budget in (0, 2, 3):
            chosen = frozen["selection"]["results"][method][str(budget)]["selected"]
            if chosen != expected.get(f"B{budget}"):
                raise RuntimeError("execution plan selections differ from the frozen valid result")
    return plan, frozen


def _selected_sets(frozen: dict[str, Any]) -> dict[str, tuple[str, ...]]:
    selected: dict[str, tuple[str, ...]] = {}
    for method in ("Nominal", "PESS"):
        for budget in (0, 2, 3):
            result = frozen["selection"]["results"][method][str(budget)]
            chosen = tuple(result["selected"])
            if chosen != tuple(frozen["selection"]["results"][method][str(budget)]["all_optimal_sets"][0]):
                raise RuntimeError("frozen representative is not a frozen minimizer")
            selected[f"{method}_B{budget}"] = chosen
    if selected["Nominal_B0"] != selected["PESS_B0"] or selected["Nominal_B2"] != selected["PESS_B2"] or selected["Nominal_B3"] != selected["PESS_B3"]:
        raise RuntimeError("frozen Nominal/PESS choices diverged from the reviewed result")
    if tuple(dict.fromkeys(selected.values())) != ((), selected["Nominal_B2"], selected["Nominal_B3"]):
        raise RuntimeError("distinct deployment set schedule differs from the frozen plan")
    return selected


def _candidate_edges(candidate_ids: list[str]) -> tuple[tuple[str, tuple[str, str]], ...]:
    edges = []
    for candidate_id in candidate_ids:
        try:
            left, right = (int(part) for part in candidate_id[1:].split("_"))
            pair = (SOURCE_COLUMNS[left], SOURCE_COLUMNS[right])
        except (ValueError, IndexError) as exc:
            raise RuntimeError(f"invalid frozen candidate ID: {candidate_id}") from exc
        edges.append((candidate_id, pair))
    if len(edges) != 45 or len({edge for edge, _ in edges}) != 45:
        raise RuntimeError("frozen candidate universe is not the complete 45-edge Forest10 set")
    return tuple(edges)


def _load_test_inputs(run_root: Path) -> tuple[list[dict[str, Any]], dict[str, int], dict[str, Any], Path]:
    derived = run_root / "input" / "prepared"
    derived.mkdir(parents=True)
    archive_path = configured_root("ESS_DATA_ROOT")
    with arecel_archive._archive(archive_path) as archive:
        counts = arecel_archive._outputs(archive, "forest10", derived)
    if counts.get("test") != 10_000:
        raise RuntimeError("pinned official Forest10 test split is not exactly 10,000 queries")
    # Verify the archive independently; no unpinned dataset copy is accepted.
    with arecel_archive._open_verified(archive_path / "arecel-data.tar.gz") as verified:
        archive_sha = arecel_archive._sha256(verified)
    if archive_sha != ARECEL_ARCHIVE_SHA:
        raise RuntimeError("AreCEL archive differs from the frozen source pin")
    workload = json.loads((derived / "test" / "workload.json").read_text(encoding="utf-8"))
    truth_doc = json.loads((derived / "test" / "truth.json").read_text(encoding="utf-8"))
    if workload.get("split") != "test" or truth_doc.get("split") != "test":
        raise RuntimeError("loaded workload/truth are not the official test split")
    queries = sorted(workload["queries"], key=lambda row: int(row["source_index"]))
    truths_rows = sorted(truth_doc["queries"], key=lambda row: int(row["source_index"]))
    expected_ids = [f"arecel:forest10:test:{i:06d}" for i in range(10_000)]
    if [row["query_id"] for row in queries] != expected_ids or [row["query_id"] for row in truths_rows] != expected_ids:
        raise RuntimeError("test query/truth identities are not the complete ordered official split")
    truths = {row["query_id"]: row["true_cardinality"] for row in truths_rows}
    if any(isinstance(value, bool) or not isinstance(value, int) or value < 0 for value in truths.values()):
        raise RuntimeError("official test truth contains an invalid cardinality")
    for query in queries:
        if not query["sql"].startswith("SELECT * FROM public.forest10 WHERE "):
            raise RuntimeError("test SQL is not adapted to public.forest10")
    source = {
        "archive_sha256": archive_sha,
        "test_query_count": len(queries),
        "test_truth_count": len(truths),
        "test_truth_canonical_sha256": hashlib.sha256(
            "".join(json.dumps({"query_id": qid, "true_cardinality": truths[qid]}, sort_keys=True, separators=(",", ":")) + "\n" for qid in expected_ids).encode()
        ).hexdigest(),
        "workload_sha256": sha256(derived / "test" / "workload.json"),
        "truth_file_sha256": sha256(derived / "test" / "truth.json"),
    }
    return queries, truths, source, derived


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, sort_keys=True, indent=2) + "\n", encoding="utf-8")


def _worker(run_root: Path) -> int:
    started = time.monotonic()
    summary: dict[str, Any] = {"status": "FAILED", "phase_seconds": {}, "error": None}
    cluster_context = None
    cluster_entered = False
    restore = None
    failures: list[dict[str, Any]] = []
    try:
        runtime_root = runtime_runs("ess-research", 64).resolve()
        if run_root.is_symlink() or run_root.parent.resolve() != runtime_root:
            raise RuntimeError("test evaluation run must be a direct Issue #64 runtime child")
        plan, frozen = _frozen_inputs()
        selected = _selected_sets(frozen)
        summary["frozen_inputs"] = {
            "plan_sha256": PLAN_SHA256,
            "selection_sha256": SELECTION_SHA256,
            "selection_status": frozen["status"],
            "execution_code_commit": os.environ.get("ESS_ISSUE64_EXECUTION_COMMIT", "recorded-by-caller"),
        }
        if int(plan["expected_plan_calls"]) != 30_000:
            raise RuntimeError("frozen test plan call count is not 30,000")
        t = time.monotonic()
        queries, truths, source, derived = _load_test_inputs(run_root)
        summary["phase_seconds"]["test_input_load_and_identity"] = round(time.monotonic() - t, 3)
        summary["test_input"] = source

        t = time.monotonic()
        gate_audit, run_formal, helper_pin = pilot._load_pinned_pr58_modules(run_root)
        summary["phase_seconds"]["pinned_pr58_helper_acquisition"] = round(time.monotonic() - t, 3)
        summary["pr58_helper"] = helper_pin

        source_columns, columns, _ = arecel_archive._schema("forest10")
        if tuple(source_columns) != SOURCE_COLUMNS:
            raise RuntimeError("Forest10 schema source-column order differs from the pinned contract")
        prepared_root = run_root / "input" / "pg-table"
        prepared_root.mkdir()
        (prepared_root / "schema.sql").write_text(
            "CREATE TABLE public.forest10 (\n" + ",\n".join(
                f'  "{name}" {type_}' for name, type_ in columns
            ) + "\n);\n", encoding="utf-8"
        )
        csv_path = derived / "table.csv"
        t = time.monotonic()
        prefix, _source, build = pilot._prepare_owned_postgresql(
            run_root, phase_sink=lambda _: None, phase_times=summary["phase_seconds"]
        )
        summary["postgresql"] = build
        summary["phase_seconds"]["postgresql_build_install"] = round(time.monotonic() - t, 3)
        restore = pilot._install_pinned_pg_diagnostics(gate_audit, phase_sink=lambda _: None, failure_sink=failures)
        cluster_context = gate_audit.owned_cluster(prefix, run_root / "cluster", os.environ.copy())
        t = time.monotonic()
        cluster = cluster_context.__enter__()
        cluster_entered = True
        summary["phase_seconds"]["cluster_start"] = round(time.monotonic() - t, 3)

        t = time.monotonic()
        sample, identity = run_formal.bootstrap_cluster(
            prefix, cluster, prepared_root, "forest10",
            {"catalog_columns": [name for name, _ in columns], "source_rows": EXPECTED_ROWS}, csv_path,
        )
        sample_identity = {key: identity[key] for key in ("table", "header", "sha256")}
        runner.validate_fresh_sample_identity(sample, sample_identity, run_formal)
        summary["sample"] = {
            "table": identity["table"], "header": identity["header"],
            "bytes": identity["bytes"], "sha256": identity["sha256"],
        }
        summary["phase_seconds"]["fresh_table_sample_export_analyze"] = round(time.monotonic() - t, 3)

        candidate_ids = frozen["inputs"]["candidate_order"]
        candidates = runner.pr58_candidate_specs(_candidate_edges(candidate_ids))
        backend = runner.PR58Forest10Backend(run_formal, prefix, cluster, candidates, sample, sample_identity)
        t = time.monotonic()
        result = runner.evaluate_frozen_selections(
            queries, truths, selected, backend, expected_query_count=10_000,
        )
        summary["phase_seconds"]["test_explain_and_metrics"] = round(time.monotonic() - t, 3)
        if len(result["query_observations"]) != 30_000 or result["selection_sets_measured"] != 3:
            raise RuntimeError("test observations differ from the predeclared 30,000-row/3-set schedule")

        output = run_root / "forest10-test-observations.jsonl.gz"
        with output.open("xb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=6, mtime=0) as compressed:
                for row in result["query_observations"]:
                    compressed.write((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode())
            raw.flush()
            os.fsync(raw.fileno())
        summary["observation_file"] = {"path": output.name, "rows": len(result["query_observations"]), "bytes": output.stat().st_size, "sha256": sha256(output)}
        summary["metrics"] = result["metrics"]
        summary["paired_q1"] = result["paired_q1"]
        summary["selection_aliases"] = {key: list(value) for key, value in selected.items()}
        summary["estimator"] = result["estimator"]
        summary["status"] = "COMPLETE" if all(value["status"] == "COMPLETE" for value in result["metrics"].values()) else "INCONCLUSIVE_UNRESOLVED_ROWS"
        summary["failures"] = failures
    except BaseException as exc:
        summary["error"] = {"phase": summary.get("current_phase", "worker"), "error_class": type(exc).__name__, "message": str(exc).splitlines()[0][:240]}
    finally:
        if cluster_context is not None and cluster_entered:
            try:
                cluster_context.__exit__(None, None, None)
                summary["postgresql_shutdown"] = "PASS"
            except BaseException as exc:
                summary["postgresql_shutdown"] = "FAIL"
                summary["cleanup_error"] = type(exc).__name__
                summary["status"] = "FAILED"
        if restore is not None:
            restore()
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        _write_json(run_root / "test-evaluation-summary.json", summary)
    return 0 if summary["status"] == "COMPLETE" else 2


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        return _worker(args.worker.resolve())
    _frozen_inputs()
    runs = runtime_runs("ess-research", 64)
    runs.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(runs).free < HARD_DISK:
        raise SystemExit("insufficient free space for the frozen 4-GiB runtime cap")
    run_root = Path(tempfile.mkdtemp(prefix=RUN_PREFIX, dir=runs))
    print(f"TEST_EVALUATION_RUN_ROOT={run_root}", flush=True)
    return pilot._supervise(
        run_root,
        worker_command=[sys.executable, str(Path(__file__).resolve()), "--worker", str(run_root)],
        soft_wall_seconds=SOFT_WALL, hard_wall_seconds=HARD_WALL,
        soft_disk_bytes=SOFT_DISK, hard_disk_bytes=HARD_DISK,
        worker_summary_name="test-evaluation-summary.json",
        summary_format="ess-issue64-forest10-test-evaluation-supervisor-v1",
    )


if __name__ == "__main__":
    raise SystemExit(main())
