"""Capped valid-only throughput probe for the pinned PR #58 trace path.

The probe runs only after explicit researcher authorization. It performs no
truth loading, resource optimization, or test-split work, and never persists
per-query trace/estimate results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ISSUE64_ROOT = HERE.parents[2]
sys.path.insert(0, str(ISSUE64_ROOT / "src"))
sys.path.insert(0, str(HERE))

import run_forest10_setup_pilot as pilot
from ess_research.arecel.archive import _schema, prepare_valid_workload
from ess_research.arecel.candidates import discover_candidates
from ess_research.arecel.forest10 import EXPECTED_ROWS, SOURCE_COLUMNS
from ess_research.task_paths import configured_root, runtime_runs

QUERY_COUNT = 20
QUERY_STRIDE = 500
MAX_TRACE_CALLS = QUERY_COUNT * 46
CALIBRATION_TRACE_CALLS = 174_088
SOFT_WALL_SECONDS = 8 * 60
HARD_WALL_SECONDS = 10 * 60
SOFT_DISK_BYTES = 384 * 1024**2
HARD_DISK_BYTES = 512 * 1024**2
RUNTIME_PREFIX = "f10trace-"
SUMMARY_NAME = "trace-worker-summary.json"
SOURCE_COMMIT = "23c7c2fdd4bfb561f3257d947fee956a2999fdb6"
RUN_FORMAL_SHA256 = "61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322"
SAMPLE_SOURCE_SHA256 = "661c03c59a2a4ca1273a205d3e0c1ae2f2dc9c1fdf8c39076cd0085be6880e68"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _candidate_rows(discovery: dict[str, Any]) -> tuple[list[tuple[str, tuple[str, str]]], int]:
    columns = {name: index for index, name in enumerate(SOURCE_COLUMNS)}
    result = []
    support_sum = 0
    for row in discovery["candidates"]:
        left, right = row["column_a"], row["column_b"]
        i, j = sorted((columns[left], columns[right]))
        result.append((f"e{i:02d}_{j:02d}", (SOURCE_COLUMNS[i], SOURCE_COLUMNS[j])))
        support_sum += int(row["eligible_valid_query_count"])
    return result, support_sum


def _timed_call(phases: dict[str, float], key: str, callback):
    start = time.monotonic()
    try:
        return callback()
    finally:
        phases[key] = phases.get(key, 0.0) + (time.monotonic() - start)


def _selected_source_indices(valid_count: int = 10_000) -> tuple[int, ...]:
    if valid_count != 10_000 or QUERY_STRIDE <= 0:
        raise ValueError("the throughput probe requires the frozen 10,000-query valid split")
    indices = tuple(range(0, valid_count, QUERY_STRIDE))
    if len(indices) != QUERY_COUNT:
        raise ValueError("fixed systematic sample size differs from its frozen count")
    return indices


def _bounded_call_count(eligibility: dict[int, tuple[str, ...]]) -> int:
    if len(eligibility) != QUERY_COUNT:
        raise ValueError("eligibility must cover the complete fixed probe query sample")
    count = QUERY_COUNT + sum(len(edges) for edges in eligibility.values())
    if count > MAX_TRACE_CALLS:
        raise ValueError("eligibility exceeds the fixed worst-case trace-call bound")
    return count


def _safe_probe_error(exc: BaseException, phase: str) -> dict[str, Any]:
    if isinstance(exc, pilot.PilotPostgreSQLFailure):
        return exc.record()
    return {"phase": phase, "type": type(exc).__name__, "message": "probe stage failed; details omitted"}


def _worker(root: Path) -> int:
    started = time.monotonic()
    phases: dict[str, float] = {}
    summary: dict[str, Any] = {
        "format": "ess-issue64-forest10-valid-trace-throughput-v1",
        "status": "FAILED",
        "scope": "valid-only trace throughput; no truth, selection objective, or test outcomes",
        "hard_caps": {
            "wall_seconds": HARD_WALL_SECONDS,
            "soft_stop_seconds": SOFT_WALL_SECONDS,
            "disk_bytes": HARD_DISK_BYTES,
            "soft_stop_disk_bytes": SOFT_DISK_BYTES,
            "max_trace_calls": MAX_TRACE_CALLS,
        },
        "phases_seconds": phases,
        "error": None,
    }
    current_phase = "preflight"
    cluster_context = None
    cluster_entered = False
    restore_helpers = None
    pg_failures: list[dict[str, Any]] = []
    sample: Path | None = None
    csv_path: Path | None = None
    schema_path: Path | None = None
    try:
        if root.parent.resolve() != runtime_runs("ess-research", 64).resolve() or root.is_symlink():
            raise RuntimeError("runtime root is not an isolated Issue #64 child")
        runtime = configured_root("ESS_RUNTIME_PARENT")
        data_root = configured_root("ESS_DATA_ROOT")
        prefix = runtime / "issue38" / "pg-prefix"
        pg_source = runtime / "issue38" / "pg-src"
        pg_manifest = runtime / "issue38" / "results" / "heldout-v1" / "runtime-manifest.json"
        pr58_root = ISSUE64_ROOT.parent / "ess-research-issue48" / "experiments" / "pess-multidataset-heldout-stage2b"
        run_formal_path = pr58_root / "run_formal.py"
        if _sha256(run_formal_path) != RUN_FORMAL_SHA256:
            raise RuntimeError("pinned PR #58 run_formal.py SHA-256 mismatch")
        if str(pr58_root) not in sys.path:
            sys.path.insert(0, str(pr58_root))
        import gate_audit_v2 as helpers
        import run_formal

        if helpers.EXPECTED_PG_COMMIT != SOURCE_COMMIT:
            raise RuntimeError("pinned PostgreSQL source commit mismatch")
        if helpers.audit_pg_source(pg_source).get("status") != "VERIFIED":
            raise RuntimeError("pinned PostgreSQL source audit failed")
        if helpers.audit_pg_binary(prefix, pg_manifest).get("status") != "VERIFIED":
            raise RuntimeError("pinned PostgreSQL binary audit failed")
        if _sha256(pg_source / "src/backend/commands/analyze_sample_cache.c") != SAMPLE_SOURCE_SHA256:
            raise RuntimeError("pinned sample import source SHA-256 mismatch")
        summary["pins"] = {
            "postgresql_commit": SOURCE_COMMIT,
            "run_formal_sha256": RUN_FORMAL_SHA256,
            "trace_helper_sha256": _sha256(pr58_root / "gate_audit_v2.py"),
            "probe_sha256": _sha256(Path(__file__).resolve()),
            "issue64_protocol_sha256": _sha256(HERE / "protocol-v1.json"),
        }

        current_phase = "valid_workload_and_candidate_preflight"

        def load_workload():
            with prepare_valid_workload(issue=64, dataset="forest10") as prepared:
                workload = json.loads(prepared.workload_path.read_text(encoding="utf-8"))
                discovery = discover_candidates(workload["queries"], SOURCE_COLUMNS)
                return workload, discovery, dict(prepared.manifest)

        workload, discovery, workload_manifest = _timed_call(
            phases, "valid_workload_and_candidate_preflight", load_workload
        )
        queries = workload.get("queries")
        candidates, support_sum = _candidate_rows(discovery)
        if workload.get("split") != "valid" or len(queries or []) != 10_000:
            raise RuntimeError("official Forest10 valid workload count/split mismatch")
        if workload_manifest.get("labels_loaded") is not False:
            raise RuntimeError("workload-only preparation did not attest labels_loaded=false")
        if discovery.get("candidate_count") != 45 or support_sum != 164_088:
            raise RuntimeError("Forest10 candidate count/support differs from merged PR #68")
        selected_indices = _selected_source_indices(len(queries))
        sampled = [queries[index] for index in selected_indices]
        if [query.get("source_index") for query in sampled] != list(selected_indices):
            raise RuntimeError("valid query source indices are not in the expected order")
        candidate_ids = {edge for edge, _ in candidates}
        sampled_eligible: dict[int, tuple[str, ...]] = {}
        for index, query in zip(selected_indices, sampled, strict=True):
            one = discover_candidates([query], SOURCE_COLUMNS)
            eligible = tuple(
                f"e{min(SOURCE_COLUMNS.index(row['column_a']), SOURCE_COLUMNS.index(row['column_b'])):02d}_"
                f"{max(SOURCE_COLUMNS.index(row['column_a']), SOURCE_COLUMNS.index(row['column_b'])):02d}"
                for row in one["candidates"]
            )
            if set(eligible) - candidate_ids:
                raise RuntimeError("sample query has eligibility outside frozen candidate universe")
            sampled_eligible[index] = eligible
        expected_calls = _bounded_call_count(sampled_eligible)
        if not 0 < expected_calls <= MAX_TRACE_CALLS:
            raise RuntimeError("fixed valid trace sample violates its predeclared call cap")
        summary["workload_preflight"] = {
            "dataset": "forest10",
            "split": "valid",
            "valid_query_count": len(queries),
            "labels_loaded": False,
            "arecel_archive_sha256": workload_manifest.get("archive_sha256"),
            "candidate_count": discovery["candidate_count"],
            "candidate_support_sum": support_sum,
            "sample_schedule": {"source_index_start": 0, "stride": QUERY_STRIDE, "count": QUERY_COUNT},
            "sampled_query_ids_or_sql_retained": False,
            "static_candidate_pair_call_count_for_sample": sum(map(len, sampled_eligible.values())),
            "trace_call_count_expected": expected_calls,
        }

        source_columns, columns, _ = _schema("forest10")
        if tuple(source_columns) != SOURCE_COLUMNS:
            raise RuntimeError("Forest10 source column order differs from pinned ETL")
        input_root = root / "input"
        prepared_root = input_root / "prepared"
        prepared_root.mkdir(parents=True)
        schema_path = prepared_root / "schema.sql"
        schema_sql = "CREATE TABLE public.forest10 (\n" + ",\n".join(
            f'  "{name}" {type_}' for name, type_ in columns
        ) + "\n);\n"
        schema_path.write_text(schema_sql, encoding="utf-8")
        csv_path = input_root / "forest10-original.csv"
        input_root.mkdir(exist_ok=True)
        _timed_call(phases, "pinned_csv_extract", lambda: pilot._extract_csv(data_root, csv_path))

        restore_helpers = pilot._install_pinned_pg_diagnostics(
            helpers,
            phase_sink=lambda phase: None,
            failure_sink=pg_failures,
        )
        current_phase = "isolated_cluster_bootstrap_sample_export_analyze"
        cluster_context = helpers.owned_cluster(prefix, root / "cluster", os.environ.copy())
        cluster = cluster_context.__enter__()
        cluster_entered = True
        spec = {"catalog_columns": [name for name, _ in columns], "source_rows": EXPECTED_ROWS}
        sample, identity = _timed_call(
            phases,
            "table_bootstrap_and_initial_sample_export_analyze",
            lambda: run_formal.bootstrap_cluster(prefix, cluster, prepared_root, "forest10", spec, csv_path),
        )
        sample_identity = {key: identity[key] for key in ("table", "header", "sha256")}
        if sample_identity["table"] != "public.forest10":
            raise RuntimeError("fixed sample was not exported from public.forest10")
        from forest10_runner import pr58_candidate_specs, validate_fresh_sample_identity

        validate_fresh_sample_identity(sample, sample_identity, helpers)
        stats = pr58_candidate_specs(candidates)
        statistic_name_to_id = {str(row["statistic_name"]): str(row["id"]) for row in stats}
        server_log = cluster["server_log"]
        log_start_bytes = server_log.stat().st_size
        latest_offset = log_start_bytes
        config_seconds = 0.0
        config_max_seconds = 0.0
        trace_seconds = 0.0
        trace_max_seconds = 0.0
        trace_calls = 0
        current_phase = "trace_configuration_and_valid_queries"

        def configure(selected: tuple[str, ...]):
            nonlocal config_seconds, config_max_seconds
            before = time.monotonic()
            try:
                return helpers.configure_statistics(prefix, cluster, "forest10", {row["id"]: row for row in stats}, selected, sample)
            finally:
                elapsed = time.monotonic() - before
                config_seconds += elapsed
                config_max_seconds = max(config_max_seconds, elapsed)

        def trace_one(query: dict[str, Any], marker: str) -> None:
            nonlocal latest_offset, trace_seconds, trace_max_seconds, trace_calls
            if trace_calls >= MAX_TRACE_CALLS:
                raise RuntimeError("fixed maximum trace-call count reached")
            before = time.monotonic()
            try:
                result, next_offset = run_formal.run_query(
                    prefix, cluster, dict(query), current_ledger, marker, latest_offset, statistic_name_to_id
                )
                latest_offset = next_offset
                del result
            finally:
                elapsed = time.monotonic() - before
                trace_seconds += elapsed
                trace_max_seconds = max(trace_max_seconds, elapsed)
                trace_calls += 1

        current_ledger = _timed_call(phases, "empty_configuration_analyze_replay", lambda: configure(()))
        for index, query in zip(selected_indices, sampled, strict=True):
            trace_one(query, f"issue64-trace-probe-empty-{index:05d}")
        for edge, _pair in candidates:
            current_ledger = _timed_call(
                phases,
                "singleton_configuration_analyze_replays",
                lambda edge=edge: configure((edge,)),
            )
            for index, query in zip(selected_indices, sampled, strict=True):
                if edge in sampled_eligible[index]:
                    trace_one(query, f"issue64-trace-probe-{edge}-{index:05d}")
        if trace_calls != expected_calls:
            raise RuntimeError("actual trace-call count differs from the precomputed valid-only count")
        log_end_bytes = server_log.stat().st_size
        summary["trace_measurement"] = {
            "status": "SUCCESS",
            "completed_trace_calls": trace_calls,
            "maximum_trace_calls": MAX_TRACE_CALLS,
            "aggregate_run_query_seconds": round(trace_seconds, 6),
            "mean_run_query_seconds": round(trace_seconds / trace_calls, 6),
            "maximum_single_run_query_seconds": round(trace_max_seconds, 6),
            "calls_per_second": round(trace_calls / trace_seconds, 6),
            "log_bytes_added_during_46_configs_and_sampled_traces": max(0, log_end_bytes - log_start_bytes),
            "configuration_count": 46,
            "configuration_analyze_seconds_total": round(config_seconds, 6),
            "configuration_analyze_seconds_max": round(config_max_seconds, 6),
            "sample_sha256": identity["sha256"],
            "sample_bytes": identity["bytes"],
            "per_query_estimates_plan_output_oids_and_trace_lines_retained": False,
        }
        non_trace = time.monotonic() - started - trace_seconds
        projected_trace_seconds = trace_seconds / trace_calls * CALIBRATION_TRACE_CALLS
        summary["planning_projection"] = {
            "calibration_trace_calls": CALIBRATION_TRACE_CALLS,
            "projected_trace_seconds_linear_from_probe_mean": round(projected_trace_seconds, 1),
            "observed_non_trace_seconds_including_46_replays": round(non_trace, 1),
            "projected_total_seconds_linear": round(non_trace + projected_trace_seconds, 1),
            "projection_status": "EXTRAPOLATION_ONLY; 20 systematic valid queries are not a runtime guarantee",
            "nominal_quiet_window_floor_seconds": round(CALIBRATION_TRACE_CALLS * 0.20, 1),
            "projected_config_and_trace_log_bytes_linear": round(
                max(0, log_end_bytes - log_start_bytes) / trace_calls * CALIBRATION_TRACE_CALLS
            ),
        }
        summary["status"] = "SUCCESS"
    except BaseException as exc:
        summary["status"] = "FAILED"
        summary["error"] = _safe_probe_error(exc, current_phase)
    finally:
        current_phase = "postgresql_shutdown"
        if cluster_context is not None and cluster_entered:
            try:
                cluster_context.__exit__(None, None, None)
                summary["postgresql_shutdown"] = "PASS"
            except BaseException as exc:
                summary["status"] = "FAILED"
                summary["postgresql_shutdown"] = "FAIL"
                summary["cleanup_error"] = _safe_probe_error(exc, current_phase)
        if restore_helpers is not None:
            restore_helpers()
        if csv_path is not None:
            csv_path.unlink(missing_ok=True)
        if schema_path is not None:
            schema_path.unlink(missing_ok=True)
        if sample is not None:
            sample.unlink(missing_ok=True)
        log_file = root / "cluster" / "server.log"
        if log_file.exists():
            log_file.unlink(missing_ok=True)
        summary["worker_elapsed_seconds"] = round(time.monotonic() - started, 3)
        pilot._merge_pg_failures(summary, pg_failures)
        (root / SUMMARY_NAME).write_text(json.dumps(summary, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    return 0 if summary["status"] == "SUCCESS" else 2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--researcher-approved", action="store_true")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker is not None:
        return _worker(args.worker.resolve())
    if not args.researcher_approved:
        raise SystemExit("refusing to run without explicit --researcher-approved")
    runs = runtime_runs("ess-research", 64)
    runs.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(runs).free < HARD_DISK_BYTES:
        raise SystemExit("refusing trace probe: runtime filesystem has less than the 512-MiB hard cap available")
    import tempfile

    root = Path(tempfile.mkdtemp(prefix=RUNTIME_PREFIX, dir=runs))
    worker_command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(root)]
    return pilot._supervise(
        root,
        worker_command=worker_command,
        soft_wall_seconds=SOFT_WALL_SECONDS,
        hard_wall_seconds=HARD_WALL_SECONDS,
        soft_disk_bytes=SOFT_DISK_BYTES,
        hard_disk_bytes=HARD_DISK_BYTES,
        worker_summary_name=SUMMARY_NAME,
        summary_format="ess-issue64-forest10-valid-trace-throughput-supervisor-v1",
    )


if __name__ == "__main__":
    raise SystemExit(main())
