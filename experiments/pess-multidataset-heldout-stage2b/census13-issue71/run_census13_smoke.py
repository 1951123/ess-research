"""Run the frozen 20-query Census13 serial/two-worker JSON smoke only."""

from __future__ import annotations

import csv
import hashlib
import importlib.util
import json
import os
import shutil
import signal
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from contextlib import ExitStack, contextmanager
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(HERE))

from census13_schedule import assign_configurations, calls_for_worker, compare_smoke_observations
from ess_research.arecel.archive import SPECS, _archive, _schema, prepare_valid_workload
from ess_research.arecel.candidates import discover_candidates
from ess_research.arecel.real import ARCHIVE_SHA256
from ess_research.task_paths import configured_root, runtime_runs

PG_REPO = Path("/home/wqts/projects/ess-postgresql")
PG_COMMIT = "f1bf37b5dd3d3a7087fc0af5de550ca31035854c"
PR58_COMMIT = "76106024611ae91505f1f05bdc35aed44d9c38c4"
PR65_COMMIT = "27677a17b7455d89e92d5028d9585418550a8ff8"
PLAN_SHA256 = "51842c6981936d9a5be39342eb5caee23b35f3137e5876064b0b1a649906d5e1"
PR58_HASHES = {
    "run_formal.py": "61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322",
    "gate_audit_v2.py": "03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4",
}
PR65_FILES = ("forest10_runner.py", "forest10_exact_selection.py", "forest10_q1.py")
HARD_SECONDS, EARLY_SECONDS = 8 * 3600, int(7.5 * 3600)
HARD_BYTES, EARLY_BYTES = 4 * 1024**3, 3 * 1024**3


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_output(repo: Path, *args: str, binary: bool = False) -> bytes | str:
    result = subprocess.run(["git", "-C", str(repo), *args], capture_output=True,
                            text=not binary, timeout=120, check=False)
    if result.returncode:
        detail = result.stderr.decode("utf-8", "replace") if binary else result.stderr
        raise RuntimeError(f"git {args[0]} failed ({result.returncode}): {detail[-400:]}")
    return result.stdout


def export_pg_source(root: Path) -> tuple[Path, str]:
    head = str(git_output(PG_REPO, "rev-parse", "--verify", f"{PG_COMMIT}^{{commit}}")).strip()
    if head != PG_COMMIT:
        raise RuntimeError("local PostgreSQL object store did not resolve the frozen commit")
    source = root / "postgresql" / "source"
    source.mkdir(parents=True)
    archive = git_output(PG_REPO, "archive", "--format=tar", PG_COMMIT, binary=True)
    import io
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:") as tar:
        for member in tar.getmembers():
            path = Path(member.name)
            if path.is_absolute() or ".." in path.parts or not (member.isdir() or member.isfile()):
                raise RuntimeError("unsafe PostgreSQL source archive member")
        tar.extractall(source, filter="data")
    if not (source / "configure").is_file():
        raise RuntimeError("pinned PostgreSQL archive lacks configure")
    return source, str(git_output(PG_REPO, "show", "-s", "--format=%H", PG_COMMIT)).strip()


def _run(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int = 7200) -> None:
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True,
                            timeout=timeout, check=False)
    if result.returncode:
        raise RuntimeError(f"{Path(command[0]).name} failed ({result.returncode}): "
                           f"{(result.stderr or result.stdout)[-500:]}")


def build_pg(root: Path) -> tuple[Path, dict[str, Any]]:
    source, commit = export_pg_source(root)
    pgroot = root / "postgresql"
    build, install = pgroot / "build", pgroot / "install"
    build.mkdir()
    env = dict(os.environ, LC_ALL="C")
    phases = {}
    for name, command, cwd in (
        ("configure", [str(source / "configure"), f"--prefix={install}", "--without-readline", "--without-zlib"], build),
        ("make", ["make", "-j2"], build),
        ("install", ["make", "install"], build),
    ):
        started = time.monotonic()
        _run(command, cwd=cwd, env=env)
        phases[name] = round(time.monotonic() - started, 3)
    version = subprocess.check_output([str(install / "bin/pg_config"), "--version"], text=True).strip()
    if version != "PostgreSQL 16.14":
        raise RuntimeError(f"unexpected PostgreSQL version: {version}")
    binary_hashes = {name: sha256_file(install / "bin" / name)
                     for name in ("postgres", "psql", "pg_ctl", "initdb")}
    return install, {"source_commit": commit, "version": version, "phase_seconds": phases,
                     "binary_sha256": binary_hashes}


def load_helpers(root: Path):
    source_dir = root / "pinned-helpers"
    source_dir.mkdir()
    sources = (("run_formal.py", PR58_COMMIT, "experiments/pess-multidataset-heldout-stage2b/run_formal.py", source_dir),
               ("gate_audit_v2.py", PR58_COMMIT, "experiments/pess-multidataset-heldout-stage2b/gate_audit_v2.py", source_dir))
    hashes = {}
    for name, commit, path, dest in sources:
        content = git_output(REPO_ROOT, "show", f"{commit}:{path}", binary=True)
        target = dest / name
        target.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        if digest != PR58_HASHES[name]:
            raise RuntimeError(f"PR58 {name} source hash mismatch")
        hashes[f"pr58/{name}"] = digest
    for name in PR65_FILES:
        path = f"experiments/pess-multidataset-heldout-stage2b/generalization-issue64/{name}"
        content = git_output(REPO_ROOT, "show", f"{PR65_COMMIT}:{path}", binary=True)
        (source_dir / name).write_bytes(content)
        hashes[f"pr65/{name}"] = hashlib.sha256(content).hexdigest()
    sys.path.insert(0, str(source_dir))
    import gate_audit_v2 as helpers
    import run_formal
    import forest10_runner
    return helpers, run_formal, forest10_runner, hashes


def extract_csv(root: Path) -> Path:
    spec = SPECS["census13"]
    destination = root / "input" / "census13.csv"
    destination.parent.mkdir()
    member_name = "data/census13/original.csv"
    seen = False
    with _archive(configured_root("ESS_DATA_ROOT")) as stream:
        with tarfile.open(fileobj=stream, mode="r|gz") as tar:
            for member in tar:
                if member.name.removeprefix("./") != member_name:
                    continue
                if seen or not member.isfile():
                    raise RuntimeError("duplicate or invalid Census13 CSV archive entry")
                source = tar.extractfile(member)
                if source is None:
                    raise RuntimeError("Census13 CSV archive entry is unreadable")
                with source, destination.open("xb") as target:
                    shutil.copyfileobj(source, target, 1024 * 1024)
                seen = True
    if not seen or sha256_file(destination) != spec.csv_sha256:
        raise RuntimeError("pinned Census13 CSV SHA-256 mismatch")
    with destination.open("r", encoding="utf-8", newline="") as stream:
        row_count = sum(1 for _ in csv.reader(stream)) - 1
    if row_count != spec.expected_rows:
        raise RuntimeError("Census13 source CSV row count mismatch")
    return destination


def schema_file(root: Path) -> tuple[Path, tuple[str, ...], tuple[tuple[str, str], ...]]:
    source_columns, columns, _ = _schema("census13")
    prepared = root / "input" / "prepared"
    prepared.mkdir()
    path = prepared / "schema.sql"
    path.write_text("CREATE TABLE public.census13 (\n" + ",\n".join(
        f'"{name}" {type_}' for name, type_ in columns) + "\n);\n", encoding="utf-8")
    return path, tuple(source_columns), tuple(columns)


def populate_replay_cluster(helpers, prefix: Path, cluster: dict[str, Any], schema: Path,
                            csv_path: Path, sample: Path | None, columns) -> int:
    env = dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib"))
    helpers.psql(prefix, cluster["socket_dir"], cluster["port"], schema.read_text(), env)
    escaped_csv = str(csv_path).replace("'", "''")
    helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
                 f"\\copy public.census13 FROM '{escaped_csv}' WITH (FORMAT csv, HEADER true);", env, timeout=600)
    count = helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
                         "SELECT count(*) FROM public.census13;", env, tuples=True).strip()
    if count != str(SPECS["census13"].expected_rows):
        raise RuntimeError("Census13 imported row count mismatch")
    for name, _type in columns:
        helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
                     f'ALTER TABLE public.census13 ALTER COLUMN "{name}" SET STATISTICS 300;', env)
    relation_oid = int(helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
                                    "SELECT 'public.census13'::regclass::oid;", env, tuples=True).strip())
    if sample is not None:
        header = helpers.sample_header(sample)
        if header["server_version"] != "16.14" or header["natts"] != len(columns):
            raise RuntimeError("fixed sample header does not match Census13 PG version/schema")
        if header["relation_oid"] != relation_oid or header["relation_identity"] != "6:public8:census13":
            raise RuntimeError("fixed sample relation identity does not match the target cluster table")
    return relation_oid


def candidates_and_schedule(plan: dict[str, Any], queries: list[dict[str, Any]]):
    cols = tuple(plan["dataset_shape"]["source_columns_in_order"])
    rows = discover_candidates(queries, cols)
    observed = {(r["column_a"], r["column_b"]): r["eligible_valid_query_count"] for r in rows["candidates"]}
    candidates = []
    for item in plan["candidate_policy"]["candidates"]:
        left, right = item["endpoints"]
        if observed.get((left, right)) != item["eligible_valid_query_count"]:
            raise RuntimeError("runtime valid static eligibility differs from the frozen plan")
        candidates.append({"id": item["id"], "statistic_name": f"ess_issue71_census13_{item['id']}",
                           "catalog_columns": [left, right],
                           "eligible_valid_query_count": item["eligible_valid_query_count"]})
    eligible = {q["query_id"]: [c["id"] for c in candidates
                                if any(p["column"] in c["catalog_columns"] for p in q["predicates"])
                                and all(any(p["column"] == endpoint for p in q["predicates"])
                                        for endpoint in c["catalog_columns"])]
                for q in queries}
    frozen_ids = plan["serial_parallel_smoke"]["valid_query_ids"]
    smoke_queries = [q for q in queries if q["query_id"] in set(frozen_ids)]
    if [q["query_id"] for q in smoke_queries] != frozen_ids:
        raise RuntimeError("smoke query identity/order differs from frozen source-index list")
    return candidates, eligible, smoke_queries


def measure_mode(*, mode: str, workers: tuple[tuple[dict[str, Any], tuple[tuple[str, tuple[str, ...]], ...], int], ...],
                 queries, eligible, candidates, sample: Path, prefix: Path, helpers, run_formal,
                 forest10_runner, output_path: Path) -> dict[str, Any]:
    name_to_id = {row["statistic_name"]: row["id"] for row in candidates}

    def measure_worker(cluster, configs, relation_oid):
        rows: list[dict[str, Any]] = []
        for config_id, selected in configs:
            ledger = run_formal.configure_statistics(prefix, cluster, "census13",
                                                       {row["id"]: row for row in candidates}, selected, sample)
            adapter = forest10_runner.PR7StructuredExplainAdapter(
                helpers, prefix, cluster, relation_oid, ledger, name_to_id)
            query_ids = [q["query_id"] for q in queries] if config_id == "Empty" else [
                q["query_id"] for q in queries if config_id in eligible[q["query_id"]]]
            by_id = {q["query_id"]: q for q in queries}
            for query_id in query_ids:
                parsed = adapter.explain(by_id[query_id])
                records = parsed["mcv_records"]
                rows.append({
                    "query_id": query_id, "config_id": config_id, "status": "SUCCESS",
                    "diagnostics_status": parsed["diagnostics_status"],
                    "mcv_diagnostics_status": parsed["mcv_diagnostics_status"],
                    "nrows_preclamp": parsed["estimate_preclamp"],
                    "relation_oid": parsed["relation_oid"],
                    "mcv_candidate_ids": [r["statistic_id"] for r in records],
                    "clause_indexes": [i for r in records for i in r["clause_indexes"]],
                    "mcv_events": records,
                })
        return rows

    start = time.monotonic()
    if len(workers) == 1:
        rows = measure_worker(*workers[0])
    else:
        if mode != "parallel-2-worker" or len(workers) != 2:
            raise ValueError("only the fixed two-worker mode may run configurations concurrently")
        rows = _parallel_worker_calls(measure_worker, workers)
    elapsed = time.monotonic() - start
    output_path.write_text("\n".join(json.dumps(row, sort_keys=True, separators=(",", ":")) for row in rows) + "\n")
    mcv_counts: dict[str, int] = {}
    for row in rows:
        state = row["mcv_diagnostics_status"]
        mcv_counts[state] = mcv_counts.get(state, 0) + 1
    return {"rows": rows, "elapsed_seconds": elapsed, "calls": len(rows),
            "calls_per_second": len(rows) / elapsed if elapsed else None,
            "output_sha256": sha256_file(output_path), "mcv_diagnostics_counts": mcv_counts,
            "mcv_event_count": sum(len(row["mcv_events"]) for row in rows)}


def _parallel_worker_calls(worker_function, workers):
    if len(workers) != 2:
        raise ValueError("the frozen smoke parallel mode requires exactly two workers")
    with ThreadPoolExecutor(max_workers=2, thread_name_prefix="census13-config-worker") as pool:
        futures = [pool.submit(worker_function, *worker) for worker in workers]
        # Collect deterministically; each worker's own query loop remains serial.
        return [row for future in futures for row in future.result()]


def allocated_bytes(root: Path, external_paths: tuple[Path, ...] = ()) -> int:
    total = 0
    for base in (root, *external_paths):
        if not base.exists():
            continue
        paths = (base, *base.rglob("*"))
        for path in paths:
            if path.is_symlink():
                continue
            if path.is_file():
                total += path.stat().st_blocks * 512
    return total


class AggregateGuard:
    def __init__(self, root: Path):
        self.root = root
        self.started = time.monotonic()
        self.peak = 0
        self.stop_reason = None
        self.external_paths: list[Path] = []
        self._halt = threading.Event()
        self.thread = threading.Thread(target=self._watch, daemon=True)

    def _watch(self):
        while not self._halt.wait(1):
            try:
                used = allocated_bytes(self.root, tuple(self.external_paths))
            except FileNotFoundError:
                continue
            self.peak = max(self.peak, used)
            elapsed = time.monotonic() - self.started
            if used >= EARLY_BYTES:
                self.stop_reason = "aggregate run directory reached 3-GiB early-stop threshold"
                os.kill(os.getpid(), signal.SIGINT)
            elif elapsed >= EARLY_SECONDS:
                self.stop_reason = "aggregate run reached 7.5-hour early-stop threshold"
                os.kill(os.getpid(), signal.SIGINT)
            if used >= HARD_BYTES or elapsed >= HARD_SECONDS:
                self.stop_reason = "aggregate run exceeded hard resource cap"
                os.kill(os.getpid(), signal.SIGINT)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_):
        self._halt.set()
        self.thread.join(timeout=3)
        self.peak = max(self.peak, allocated_bytes(self.root, tuple(self.external_paths)))

    def add_external(self, path: Path) -> None:
        self.external_paths.append(path)

    def remove_external(self, path: Path) -> None:
        if path in self.external_paths:
            self.external_paths.remove(path)


@contextmanager
def owned_cluster(helpers, prefix: Path, root: Path, env: dict[str, str], guard: AggregateGuard):
    """Use run-local PGDATA/logs and a short private /tmp socket path."""
    pgdata = root / "pgdata"
    log_path = root / "server.log"
    if root.exists():
        raise RuntimeError("refusing to reuse a Census13 smoke cluster directory")
    root.mkdir(parents=True)
    with tempfile.TemporaryDirectory(prefix=f"e71-{root.name[-12:]}-") as socket_name:
        socket_dir = Path(socket_name)
        guard.add_external(socket_dir)
        cluster_env = dict(env, LD_LIBRARY_PATH=str(prefix / "lib"))
        started = False
        try:
            helpers.run_command([str(prefix / "bin/initdb"), "-D", str(pgdata), "--no-locale",
                                 "--encoding=UTF8", "-U", "wqts"], env=cluster_env, timeout=180)
            port = helpers.reserve_port()
            options = (f"-p {port} -k {socket_dir} -c log_min_messages=debug1 "
                       "-c log_line_prefix='%m [%p] %u@%d app=%a '")
            helpers.run_command([str(prefix / "bin/pg_ctl"), "-D", str(pgdata), "-l", str(log_path),
                                 "-o", options, "-w", "start"], env=cluster_env, timeout=120)
            started = True
            identity = helpers.psql(prefix, socket_dir, port,
                "SELECT current_setting('data_directory'), current_setting('port'), current_database(), version();",
                cluster_env, tuples=True)
            fields = identity.strip().split("|")
            helpers.validate_cluster_identity(fields, pgdata, port)
            yield {"pgdata": pgdata, "socket_dir": socket_dir, "port": port,
                   "server_log": log_path, "identity": fields}
        finally:
            if started:
                helpers.run_command([str(prefix / "bin/pg_ctl"), "-D", str(pgdata), "-m", "fast",
                                     "-w", "stop"], env=cluster_env, timeout=120)
            guard.remove_external(socket_dir)


def execute(root: Path) -> dict[str, Any]:
    started = time.monotonic()
    root.mkdir(parents=True, exist_ok=False)
    guard = AggregateGuard(root)
    original_sigint = signal.getsignal(signal.SIGINT)
    def stop_handler(_sig, _frame):
        raise KeyboardInterrupt("aggregate smoke resource guard stopped the run")
    signal.signal(signal.SIGINT, stop_handler)
    result: dict[str, Any] = {"status": "INCOMPLETE", "run_id": root.name,
                              "official_test_access": False, "truth_loaded": False}
    phase = "initialization"
    try:
        with guard:
            phase = "input_validation"
            plan_path = HERE / "census13-stage2b-plan-v1.json"
            if sha256_file(plan_path) != PLAN_SHA256:
                raise RuntimeError("frozen Census13 plan SHA-256 mismatch")
            plan = json.loads(plan_path.read_text())
            csv_path = extract_csv(root)
            with prepare_valid_workload(issue=71, dataset="census13") as prepared:
                if prepared.manifest["labels_loaded"] is not False or prepared.manifest["archive_sha256"] != ARCHIVE_SHA256:
                    raise RuntimeError("valid-only workload provenance check failed")
                workload = json.loads(prepared.workload_path.read_text())
            candidates, eligible, queries = candidates_and_schedule(plan, workload["queries"])
            smoke_ids = {q["query_id"] for q in queries}
            smoke_eligible = {qid: eligible[qid] for qid in smoke_ids}
            serial_assign = assign_configurations(candidates, 1)
            parallel_assign = assign_configurations(candidates, 2)
            serial_calls = calls_for_worker(serial_assign[0], [q["query_id"] for q in queries], smoke_eligible)
            expected = plan["serial_parallel_smoke"]["calls_per_mode"]
            parallel_call_count = sum(len(calls_for_worker(rows, [q["query_id"] for q in queries], smoke_eligible))
                                      for rows in parallel_assign)
            if len(serial_calls) != expected or parallel_call_count != expected:
                raise RuntimeError("runtime smoke schedule differs from the frozen 501-call plan")
            schema, _source_cols, columns = schema_file(root)
            phase = "postgresql_build"
            prefix, build = build_pg(root)
            result["postgresql_build"] = build
            phase = "pinned_helper_load"
            helpers, run_formal, forest10_runner, helper_hashes = load_helpers(root)
            result["helper_commits"] = {"pr58": PR58_COMMIT, "pr65": PR65_COMMIT}
            result["helper_sha256"] = helper_hashes

            setup_root = root / "clusters"
            phase = "serial_cluster_setup_and_sample_export"
            with ExitStack() as stack:
                cluster_a = stack.enter_context(owned_cluster(helpers, prefix, setup_root / "serial-reference", os.environ.copy(), guard))
                sample, sample_identity = run_formal.bootstrap_cluster(
                    prefix, cluster_a, schema.parent, "census13",
                    {"catalog_columns": [name for name, _ in columns], "source_rows": SPECS["census13"].expected_rows},
                    csv_path)
                sample_sha = sample_identity["sha256"]
                header = helpers.sample_header(sample)
                if sample_sha != sha256_file(sample) or header != sample_identity["header"]:
                    raise RuntimeError("fresh Census13 fixed-sample identity/hash check failed")
                rel_oid_a = int(helpers.psql(prefix, cluster_a["socket_dir"], cluster_a["port"],
                                            "SELECT 'public.census13'::regclass::oid;", dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib")), tuples=True).strip())
                if header["relation_oid"] != rel_oid_a or header["relation_identity"] != "6:public8:census13":
                    raise RuntimeError("exported fixed sample does not identify public.census13 in source cluster")

                phase = "serial_501_explains"
                serial = measure_mode(mode="serial", workers=((cluster_a, serial_assign[0], rel_oid_a),),
                                      queries=queries, eligible=eligible, candidates=candidates, sample=sample,
                                      prefix=prefix, helpers=helpers, run_formal=run_formal,
                                      forest10_runner=forest10_runner, output_path=root / "serial-smoke.jsonl")
                result["serial"] = {k: v for k, v in serial.items() if k != "rows"}

                phase = "parallel_cluster_setup_and_sample_replay"
                cluster_b = stack.enter_context(owned_cluster(helpers, prefix, setup_root / "parallel-worker0", os.environ.copy(), guard))
                cluster_c = stack.enter_context(owned_cluster(helpers, prefix, setup_root / "parallel-worker1", os.environ.copy(), guard))
                rel_oid_b = populate_replay_cluster(helpers, prefix, cluster_b, schema, csv_path, sample, columns)
                rel_oid_c = populate_replay_cluster(helpers, prefix, cluster_c, schema, csv_path, sample, columns)
                workers = ((cluster_b, parallel_assign[0], rel_oid_b), (cluster_c, parallel_assign[1], rel_oid_c))
                phase = "parallel_501_explains"
                parallel = measure_mode(mode="parallel-2-worker", workers=workers, queries=queries,
                                        eligible=eligible, candidates=candidates, sample=sample,
                                        prefix=prefix, helpers=helpers, run_formal=run_formal,
                                        forest10_runner=forest10_runner, output_path=root / "parallel-smoke.jsonl")
                result["parallel"] = {k: v for k, v in parallel.items() if k != "rows"}
                phase = "serial_parallel_parity"
                expected_pairs = serial_calls
                parity = compare_smoke_observations(serial["rows"], parallel["rows"], expected_pairs)
                result.update({"status": "PASS", "postgresql": build, "helper_commits": {
                    "pr58": PR58_COMMIT, "pr65": PR65_COMMIT}, "helper_sha256": helper_hashes,
                    "sample": {"sha256": sample_sha, "bytes": sample.stat().st_size,
                               "header": header, "serial_relation_oid": rel_oid_a,
                               "parallel_worker_relation_oids": [rel_oid_b, rel_oid_c]},
                    "queries": [q["query_id"] for q in queries], "calls_per_mode": expected,
                    "serial": {k: v for k, v in serial.items() if k != "rows"},
                    "parallel": {k: v for k, v in parallel.items() if k != "rows"},
                    "parallel_speedup": serial["elapsed_seconds"] / parallel["elapsed_seconds"],
                    "parity": parity, "run_directory_peak_bytes": guard.peak,
                    "resource_guard": "PASS"})
            result["cluster_shutdown"] = "PASS"
            for binary, digest in build["binary_sha256"].items():
                if sha256_file(prefix / "bin" / binary) != digest:
                    raise RuntimeError(f"shared PostgreSQL install changed during the smoke: {binary}")
            result["shared_install_unchanged"] = True
    except BaseException as exc:
        result.update({"status": "BLOCKED", "error_class": type(exc).__name__,
                       "phase": phase, "error": str(exc)[:500], "serial_fallback": "serial smoke completed before a parallel/parity failure" if "serial" in result else None,
                       "resource_guard_stop_reason": guard.stop_reason,
                       "run_directory_peak_bytes": guard.peak})
    finally:
        result["elapsed_seconds_total"] = round(time.monotonic() - started, 3)
        result["run_directory_peak_bytes"] = max(result.get("run_directory_peak_bytes", 0), guard.peak)
        (root / "smoke-summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        signal.signal(signal.SIGINT, original_sigint)
    return result


def main() -> int:
    runs = runtime_runs("ess-research", 71)
    runs.mkdir(parents=True, exist_ok=True)
    run_id = time.strftime("%Y%m%d-%H%M%S-census13-smoke", time.gmtime())
    root = runs / run_id
    result = execute(root)
    print(json.dumps({k: v for k, v in result.items() if k not in {"postgresql", "helper_sha256"}}, indent=2))
    return 0 if result["status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
