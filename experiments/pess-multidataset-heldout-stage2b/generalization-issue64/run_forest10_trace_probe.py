"""Capped 20-query, valid-only PR #7 JSON calibration-observation smoke.

The run performs no truth loading, resource optimization, or test-split work.
Its compact query-level structured observations are retained as calibration
inputs; raw SQL, rounded estimates, and server-log traces are never retained.
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
from forest10_runner import PR58Forest10Backend, pr58_candidate_specs, validate_fresh_sample_identity

QUERY_COUNT = 20
MAX_JSON_CALLS = QUERY_COUNT * 46
SOFT_WALL_SECONDS = pilot.SOFT_STOP_SECONDS
HARD_WALL_SECONDS = pilot.HARD_WALL_SECONDS
SOFT_DISK_BYTES = pilot.SOFT_STOP_DISK_BYTES
HARD_DISK_BYTES = pilot.HARD_DISK_BYTES
RUNTIME_PREFIX = "f10json-"
SUMMARY_NAME = "json-calibration-smoke-worker-summary.json"
OBSERVATIONS_NAME = "json-calibration-smoke-observations.jsonl"
FROZEN_PLAN = HERE / "forest10-json-smoke-plan-v1.json"


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
    if valid_count != 10_000:
        raise ValueError("the JSON smoke requires the frozen 10,000-query valid split")
    indices = tuple(range(QUERY_COUNT))
    if len(indices) != QUERY_COUNT:
        raise ValueError("fixed systematic sample size differs from its frozen count")
    return indices


def _bounded_call_count(eligibility: dict[int, tuple[str, ...]]) -> int:
    if len(eligibility) != QUERY_COUNT:
        raise ValueError("eligibility must cover the complete fixed probe query sample")
    count = QUERY_COUNT + sum(len(edges) for edges in eligibility.values())
    if count > MAX_JSON_CALLS:
        raise ValueError("eligibility exceeds the fixed worst-case structured-JSON call bound")
    return count


def _call_plan(workload: dict[str, Any], discovery: dict[str, Any], archive_sha256: str) -> dict[str, Any]:
    """Freeze only identities/eligibility, using the existing static screen."""
    queries = workload.get("queries")
    candidates, support_sum = _candidate_rows(discovery)
    if workload.get("dataset") != "forest10" or workload.get("split") != "valid" or len(queries or []) != 10_000:
        raise RuntimeError("official Forest10 valid workload count/split mismatch")
    if discovery.get("candidate_count") != 45 or support_sum != 164_088:
        raise RuntimeError("Forest10 candidate count/support differs from merged PR #68")
    sampled = sorted(queries, key=lambda query: int(query["source_index"]))[:QUERY_COUNT]
    if [query.get("source_index") for query in sampled] != list(_selected_source_indices(len(queries))):
        raise RuntimeError("first 20 valid queries are not the frozen ascending source_index cohort")
    candidate_ids = [edge for edge, _ in candidates]
    rows = []
    eligibility = {}
    for query in sampled:
        eligible_pairs, _ = _candidate_rows(discover_candidates([query], SOURCE_COLUMNS))
        eligible = tuple(edge for edge, _ in eligible_pairs)
        if set(eligible) - set(candidate_ids):
            raise RuntimeError("sample query has eligibility outside frozen candidate universe")
        index = int(query["source_index"])
        if query["query_id"] != f"arecel:forest10:valid:{index:06d}":
            raise RuntimeError("fixed query ID does not match its official valid source index")
        eligibility[index] = eligible
        rows.append({
            "query_id": query["query_id"], "source_index": index,
            "sql_sha256": hashlib.sha256(query["sql"].encode("utf-8")).hexdigest(),
            "eligible_candidate_ids": list(eligible),
        })
    active = {edge for edges in eligibility.values() for edge in edges}
    return {
        "format": "ess-issue64-forest10-json-smoke-call-plan-v1",
        "config": "forest10-json-only-v2.json",
        "config_sha256": _sha256(HERE / "forest10-json-only-v2.json"),
        "arecel_archive_sha256": archive_sha256,
        "full_valid_query_count": len(queries),
        "full_valid_candidate_support_sum": support_sum,
        "candidate_ids": candidate_ids,
        "queries": rows,
        "configuration_order": ["Empty"] + [edge for edge in candidate_ids if edge in active],
        "expected_structured_explain_calls": _bounded_call_count(eligibility),
        "expected_configuration_count": 1 + len(active),
    }


def _safe_probe_error(exc: BaseException, phase: str) -> dict[str, Any]:
    if isinstance(exc, pilot.PilotPostgreSQLFailure):
        return exc.record()
    return {"phase": phase, "type": type(exc).__name__, "message": "probe stage failed; details omitted"}


def _worker(root: Path) -> int:
    started = time.monotonic()
    phases: dict[str, float] = {}
    summary: dict[str, Any] = {
        "format": "ess-issue64-forest10-json-calibration-smoke-v1",
        "status": "FAILED",
        "scope": "first 20 official valid queries; structured JSON observations only; no truth, selection, or test outcomes",
        "hard_caps": {
            "wall_seconds": HARD_WALL_SECONDS,
            "soft_stop_seconds": SOFT_WALL_SECONDS,
            "disk_bytes": HARD_DISK_BYTES,
            "soft_stop_disk_bytes": SOFT_DISK_BYTES,
            "max_structured_json_calls": MAX_JSON_CALLS,
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
    json_calls = 0
    successful_calls = 0
    config_count = 0
    json_seconds = 0.0
    try:
        if root.parent.resolve() != runtime_runs("ess-research", 64).resolve() or root.is_symlink():
            raise RuntimeError("runtime root is not an isolated Issue #64 child")
        data_root = configured_root("ESS_DATA_ROOT")
        pilot._validate_socket_path(root)
        helpers, run_formal, pr58_pin = _timed_call(
            phases, "pr58_helper_fetch_hash_import", lambda: pilot._load_pinned_pr58_modules(root)
        )
        summary["pins"] = {
            "postgresql_commit": pilot.ESS_POSTGRESQL_COMMIT,
            **pr58_pin,
            "probe_sha256": _sha256(Path(__file__).resolve()),
            "issue64_protocol": "forest10-json-only-v2.json",
            "issue64_protocol_sha256": _sha256(HERE / "forest10-json-only-v2.json"),
        }

        current_phase = "valid_workload_and_candidate_preflight"

        def load_workload():
            with prepare_valid_workload(issue=64, dataset="forest10", run_root=root) as prepared:
                workload = json.loads(prepared.workload_path.read_text(encoding="utf-8"))
                discovery = discover_candidates(workload["queries"], SOURCE_COLUMNS)
                return workload, discovery, dict(prepared.manifest)

        workload, discovery, workload_manifest = _timed_call(
            phases, "valid_workload_and_candidate_preflight", load_workload
        )
        queries = workload.get("queries")
        candidates, support_sum = _candidate_rows(discovery)
        if workload_manifest.get("labels_loaded") is not False:
            raise RuntimeError("workload-only preparation did not attest labels_loaded=false")
        plan = _call_plan(workload, discovery, workload_manifest["archive_sha256"])
        if json.loads(FROZEN_PLAN.read_text(encoding="utf-8")) != plan:
            raise RuntimeError("workload/eligibility differs from the committed pre-execution call plan")
        summary["pins"]["frozen_call_plan_sha256"] = _sha256(FROZEN_PLAN)
        ordered_queries = sorted(queries, key=lambda query: int(query["source_index"]))
        sampled = ordered_queries[:QUERY_COUNT]
        sampled_eligible = {row["source_index"]: tuple(row["eligible_candidate_ids"]) for row in plan["queries"]}
        expected_calls = plan["expected_structured_explain_calls"]
        summary["workload_preflight"] = {
            "dataset": "forest10",
            "split": "valid",
            "valid_query_count": len(queries),
            "labels_loaded": False,
            "arecel_archive_sha256": workload_manifest.get("archive_sha256"),
            "candidate_count": discovery["candidate_count"],
            "candidate_support_sum": support_sum,
            "sample_schedule": {"rule": "ascending source_index, take first 20", "count": QUERY_COUNT},
            "sampled_query_ids_retained": True,
            "sql_retained": False,
            "static_candidate_pair_call_count_for_sample": sum(map(len, sampled_eligible.values())),
            "structured_json_call_count_expected": expected_calls,
            "configuration_count_expected": 1 + len({edge for edges in sampled_eligible.values() for edge in edges}),
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

        def record_build_phase(phase: str) -> None:
            nonlocal current_phase
            current_phase = phase

        prefix, pg_source, pg_build = _timed_call(
            phases,
            "private_postgresql_fetch_build_install",
            lambda: pilot._prepare_owned_postgresql(
                root, phase_sink=record_build_phase, phase_times=phases
            ),
        )
        summary["postgresql_build"] = pg_build
        del pg_source

        restore_helpers = pilot._install_pinned_pg_diagnostics(
            helpers,
            phase_sink=lambda phase: None,
            failure_sink=pg_failures,
        )
        current_phase = "isolated_cluster_bootstrap_sample_export_analyze"
        cluster_context = helpers.owned_cluster(prefix, root / "cluster", os.environ.copy())
        cluster = _timed_call(phases, "cluster_init_start_identity", cluster_context.__enter__)
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
        validate_fresh_sample_identity(sample, sample_identity, helpers)
        summary["sample"] = {**sample_identity, "bytes": identity["bytes"]}

        stats = pr58_candidate_specs(candidates)
        backend = PR58Forest10Backend(run_formal, prefix, cluster, stats, sample, sample_identity)
        active_edges = tuple(edge for edge, _ in candidates if any(edge in es for es in sampled_eligible.values()))
        config_seconds = 0.0
        observation_path = root / "results" / OBSERVATIONS_NAME
        observation_path.parent.mkdir(exist_ok=True)

        def configure(selected: tuple[str, ...]):
            nonlocal config_seconds, config_count
            before = time.monotonic()
            try:
                return backend.configure(selected)
            finally:
                config_seconds += time.monotonic() - before
                config_count += 1

        current_phase = "structured_json_calibration_observations"
        with observation_path.open("x", encoding="utf-8") as observations:
            def observe(query: dict[str, Any], config_id: str, ledger: Any, eligible: bool | None) -> None:
                nonlocal json_seconds, json_calls, successful_calls
                before = time.monotonic()
                row: dict[str, Any] = {
                    "query_id": query["query_id"],
                    "config_id": config_id,
                    "static_eligible": eligible,
                    "diagnostics_status": None,
                    "nrows_preclamp": None,
                    "mcv_diagnostics_status": None,
                    "mcv_events": [],
                }
                try:
                    estimate = backend.preclamp_estimate(query, ledger, "")
                    result = backend.last_observation
                    if result is None or result["query_id"] != query["query_id"]:
                        raise RuntimeError("structured adapter returned no query-associated observation")
                    row.update({
                        "diagnostics_status": result["diagnostics_status"],
                        "nrows_preclamp": str(estimate),
                        "mcv_diagnostics_status": result["mcv_diagnostics_status"],
                        "relation_oid": result["relation_oid"],
                        "mcv_events": result["mcv_records"],
                        "status": "SUCCESS",
                    })
                except BaseException as exc:
                    row.update({"status": "ERROR", "error_class": type(exc).__name__})
                    observations.write(json.dumps(row, sort_keys=True) + "\n")
                    observations.flush()
                    raise
                finally:
                    json_seconds += time.monotonic() - before
                    json_calls += 1
                observations.write(json.dumps(row, sort_keys=True) + "\n")
                observations.flush()
                successful_calls += 1

            current_ledger = _timed_call(phases, "empty_configuration_analyze_replay", lambda: configure(()))
            for query in sampled:
                observe(query, "Empty", current_ledger, None)
            for edge in active_edges:
                current_ledger = _timed_call(
                    phases,
                    "singleton_configuration_analyze_replays",
                    lambda edge=edge: configure((edge,)),
                )
                for query in sampled:
                    source_index = int(query["source_index"])
                    if edge in sampled_eligible[source_index]:
                        observe(query, edge, current_ledger, True)

        if json_calls != expected_calls:
            raise RuntimeError("actual structured EXPLAIN count differs from the frozen valid-only count")
        if config_count != 1 + len(active_edges):
            raise RuntimeError("actual configuration count differs from the frozen static eligibility")
        summary["calibration_observations"] = {
            "status": "SUCCESS",
            "interface": "PR7StructuredExplainAdapter / EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF)",
            "expected_calls_frozen_before_postgresql_start": expected_calls,
            "completed_calls": json_calls,
            "configuration_count": config_count,
            "singleton_configurations": len(active_edges),
            "configuration_analyze_seconds_total": round(config_seconds, 6),
            "aggregate_structured_explain_seconds": round(json_seconds, 6),
            "mean_structured_explain_seconds": round(json_seconds / json_calls, 6),
            "sample_sha256": identity["sha256"],
            "sample_bytes": identity["bytes"],
            "observation_file": f"results/{OBSERVATIONS_NAME}",
            "observation_file_sha256": _sha256(observation_path),
            "truth_objective_selection_and_test_access": False,
        }
        summary["status"] = "SUCCESS"
    except BaseException as exc:
        summary["status"] = "FAILED"
        summary["error"] = _safe_probe_error(exc, current_phase)
    finally:
        summary.setdefault("calibration_observations", {}).update({
            "attempted_calls": json_calls,
            "completed_calls": successful_calls,
            "failed_calls": json_calls - successful_calls,
            "configuration_count": config_count,
            "aggregate_structured_explain_seconds": round(json_seconds, 6),
        })
        current_phase = "postgresql_shutdown"
        if cluster_context is not None and cluster_entered:
            try:
                _timed_call(phases, "cluster_shutdown", lambda: cluster_context.__exit__(None, None, None))
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
        raise SystemExit("refusing JSON calibration smoke: runtime filesystem has less than the 2-GiB hard cap available")
    import tempfile

    root = Path(tempfile.mkdtemp(prefix=RUNTIME_PREFIX, dir=runs))
    print(f"JSON_SMOKE_RUNTIME_ROOT={root}", flush=True)
    worker_command = [sys.executable, str(Path(__file__).resolve()), "--worker", str(root)]
    return pilot._supervise(
        root,
        worker_command=worker_command,
        soft_wall_seconds=SOFT_WALL_SECONDS,
        hard_wall_seconds=HARD_WALL_SECONDS,
        soft_disk_bytes=SOFT_DISK_BYTES,
        hard_disk_bytes=HARD_DISK_BYTES,
        worker_summary_name=SUMMARY_NAME,
        summary_format="ess-issue64-forest10-json-calibration-smoke-supervisor-v1",
    )


if __name__ == "__main__":
    raise SystemExit(main())
