"""Run the frozen Census13 full-valid JSON-only singleton acquisition."""

from __future__ import annotations

import json
import os
import signal
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))

import run_census13_smoke as smoke
from census13_schedule import assign_configurations, calls_for_worker
from ess_research.arecel.archive import prepare_valid_workload
from ess_research.arecel.candidates import discover_candidates
from ess_research.task_paths import runtime_runs

PLAN_SHA256 = smoke.PLAN_SHA256
STOP = threading.Event()


def _queries_and_schedule(plan: dict[str, Any]):
    with prepare_valid_workload(issue=71, dataset="census13") as prepared:
        if prepared.manifest.get("labels_loaded") is not False:
            raise RuntimeError("workload preparation unexpectedly loaded labels")
        workload = json.loads(prepared.workload_path.read_text())
    queries = workload["queries"]
    if len(queries) != plan["acquisition"]["full_valid_queries"]:
        raise RuntimeError("official Census13 valid query count differs from frozen plan")
    if [row["source_index"] for row in queries] != list(range(10_000)):
        raise RuntimeError("Census13 valid source-index sequence is incomplete or reordered")
    columns = tuple(plan["dataset_shape"]["source_columns_in_order"])
    discovery = discover_candidates(queries, columns)
    observed = {
        (row["column_a"], row["column_b"]): row["eligible_valid_query_count"]
        for row in discovery["candidates"]
    }
    candidates = []
    for fixed in plan["candidate_policy"]["candidates"]:
        endpoints = tuple(fixed["endpoints"])
        if observed.get(endpoints) != fixed["eligible_valid_query_count"]:
            raise RuntimeError(f"frozen candidate support mismatch: {fixed['id']}")
        candidates.append({"id": fixed["id"], "statistic_name": f"ess_issue71_census13_{fixed['id']}",
                           "catalog_columns": list(endpoints),
                           "eligible_valid_query_count": fixed["eligible_valid_query_count"]})
    expected_ids = [row["id"] for row in candidates]
    eligible: dict[str, list[str]] = {}
    for query in queries:
        found = discover_candidates([query], columns)
        pairs = {(item["column_a"], item["column_b"]) for item in found["candidates"]}
        eligible[query["query_id"]] = [c["id"] for c in candidates if tuple(c["catalog_columns"]) in pairs]
    support = {candidate_id: 0 for candidate_id in expected_ids}
    for query_edges in eligible.values():
        for candidate_id in query_edges:
            support[candidate_id] += 1
    if any(support[c["id"]] != c["eligible_valid_query_count"] for c in candidates):
        raise RuntimeError("per-query Census13 eligibility does not reproduce frozen candidate support")
    return queries, candidates, eligible


def _worker_measure(worker_id: int, worker, *, queries, eligible, candidates, sample,
                    prefix, helpers, run_formal, forest10_runner, output: Path,
                    failure: list[dict[str, Any]]):
    cluster, configs, relation_oid = worker
    name_to_id = {candidate["statistic_name"]: candidate["id"] for candidate in candidates}
    query_by_id = {query["query_id"]: query for query in queries}
    count = 0
    mcv_events = 0
    statuses: dict[str, int] = {}
    with output.open("x", encoding="utf-8", buffering=1) as stream:
        for config_id, selected in configs:
            if STOP.is_set():
                break
            ledger = run_formal.configure_statistics(prefix, cluster, "census13",
                                                       {row["id"]: row for row in candidates}, selected, sample)
            adapter = forest10_runner.PR7StructuredExplainAdapter(
                helpers, prefix, cluster, relation_oid, ledger, name_to_id)
            query_ids = (list(query_by_id) if config_id == "Empty" else
                         [q["query_id"] for q in queries if config_id in eligible[q["query_id"]]])
            for query_id in query_ids:
                if STOP.is_set():
                    break
                try:
                    parsed = adapter.explain(query_by_id[query_id])
                    row = {
                        "query_id": query_id,
                        "source_index": query_by_id[query_id]["source_index"],
                        "config_id": config_id,
                        "worker_id": worker_id,
                        "status": "SUCCESS",
                        "diagnostics_status": parsed["diagnostics_status"],
                        "mcv_diagnostics_status": parsed["mcv_diagnostics_status"],
                        "nrows_preclamp": parsed["estimate_preclamp"],
                        "relation_oid": parsed["relation_oid"],
                        "mcv_events": parsed["mcv_records"],
                    }
                    if row["diagnostics_status"] != "complete":
                        raise RuntimeError("structured diagnostics status is not complete")
                    stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n")
                    count += 1
                    statuses[row["mcv_diagnostics_status"]] = statuses.get(row["mcv_diagnostics_status"], 0) + 1
                    mcv_events += len(row["mcv_events"])
                except BaseException as exc:
                    STOP.set()
                    failure.append({"query_id": query_id, "config_id": config_id,
                                    "worker_id": worker_id, "error_class": type(exc).__name__,
                                    "error": str(exc)[:400]})
                    stream.write(json.dumps({"query_id": query_id, "config_id": config_id,
                                             "worker_id": worker_id, "status": "ERROR",
                                             "error_class": type(exc).__name__, "error": str(exc)[:400]},
                                            sort_keys=True, separators=(",", ":")) + "\n")
                    raise
    return {"worker_id": worker_id, "calls": count, "mcv_events": mcv_events,
            "mcv_diagnostics_counts": statuses, "output_sha256": smoke.sha256_file(output)}


def execute(root: Path) -> dict[str, Any]:
    if smoke.sha256_file(HERE / "census13-stage2b-plan-v1.json") != PLAN_SHA256:
        raise RuntimeError("frozen Census13 plan checksum mismatch")
    plan = json.loads((HERE / "census13-stage2b-plan-v1.json").read_text())
    if plan["acquisition"]["total_calls"] != 288_849:
        raise RuntimeError("frozen full-valid call count is not 288849")
    if root.exists():
        raise FileExistsError(f"refusing to reuse run directory: {root}")
    root.mkdir(parents=True)
    started = time.monotonic()
    guard = smoke.AggregateGuard(root)
    original_sigint = signal.getsignal(signal.SIGINT)
    result: dict[str, Any] = {"status": "INCOMPLETE", "run_id": root.name,
                              "truth_loaded": False, "test_truth_loaded": False,
                              "test_estimates_or_outcomes_accessed": False,
                              "frozen_plan_sha256": PLAN_SHA256}
    phase = "initialization"
    failure: list[dict[str, Any]] = []
    cluster_contexts = []
    try:
        def stop_handler(_sig, _frame):
            STOP.set()
            raise KeyboardInterrupt("aggregate 7.5-hour/3-GiB watchdog requested stop")
        signal.signal(signal.SIGINT, stop_handler)
        STOP.clear()
        with guard:
            phase = "valid_workload_and_static_schedule"
            csv_path = smoke.extract_csv(root)
            queries, candidates, eligible = _queries_and_schedule(plan)
            query_ids = [query["query_id"] for query in queries]
            assignments = assign_configurations(candidates, 2)
            expected_pairs = [pair for pairs in assignments
                              for pair in calls_for_worker(pairs, query_ids, eligible)]
            expected_total = plan["acquisition"]["total_calls"]
            if len(expected_pairs) != expected_total or len(set(expected_pairs)) != expected_total:
                raise RuntimeError("two-worker full-valid schedule count/uniqueness mismatch")
            empty_count = sum(config == "Empty" for _query, config in expected_pairs)
            singleton_count = len(expected_pairs) - empty_count
            if (empty_count, singleton_count) != (10_000, 278_849):
                raise RuntimeError("runtime schedule differs from 10000 Empty + 278849 singleton calls")
            schema, _source_cols, columns = smoke.schema_file(root)
            phase = "pinned_postgresql_build"
            prefix, build = smoke.build_pg(root)
            result["postgresql_build"] = build
            phase = "pinned_helper_loading"
            helpers, run_formal, forest10_runner, helper_hashes = smoke.load_helpers(root)
            result["helper_commits"] = {"pr58": smoke.PR58_COMMIT, "pr65": smoke.PR65_COMMIT}
            result["helper_sha256"] = helper_hashes
            phase = "two_cluster_setup_and_fixed_sample"
            root_clusters = root / "clusters"
            clusters = []
            for index in range(2):
                context = smoke.owned_cluster(helpers, prefix, root_clusters / f"worker{index}",
                                               os.environ.copy(), guard)
                cluster_contexts.append(context)
                clusters.append(context.__enter__())
            # Preserve explicit reverse-order cluster cleanup even when collection fails.
            class ClusterStack:
                def __enter__(self): return self
                def __exit__(self, *_):
                    while cluster_contexts:
                        cluster_contexts.pop().__exit__(None, None, None)
            with ClusterStack():
                first_cluster = clusters[0]
                sample, sample_identity = run_formal.bootstrap_cluster(
                    prefix, first_cluster, schema.parent, "census13",
                    {"catalog_columns": [name for name, _ in columns],
                     "source_rows": smoke.SPECS["census13"].expected_rows}, csv_path)
                if smoke.sha256_file(sample) != sample_identity["sha256"]:
                    raise RuntimeError("fixed sample SHA-256 differs from bootstrap identity")
                header = helpers.sample_header(sample)
                if header != sample_identity["header"] or header["relation_identity"] != "6:public8:census13":
                    raise RuntimeError("fixed ANALYZE sample header/relation identity mismatch")
                relation_oids = [int(helpers.psql(prefix, cluster["socket_dir"], cluster["port"],
                    "SELECT 'public.census13'::regclass::oid;",
                    dict(os.environ, LD_LIBRARY_PATH=str(prefix / "lib")), tuples=True).strip())
                    for cluster in clusters]
                if header["relation_oid"] != relation_oids[0]:
                    raise RuntimeError("sample header relation OID differs from export cluster")
                smoke.populate_replay_cluster(helpers, prefix, clusters[1], schema, csv_path, sample, columns)
                output_dir = root / "observations"
                output_dir.mkdir()
                failures: list[dict[str, Any]] = []
                phase = "288849_json_explains"
                started_measurement = time.monotonic()
                with ThreadPoolExecutor(max_workers=2, thread_name_prefix="census13-full-worker") as pool:
                    futures = [pool.submit(_worker_measure, i, (clusters[i], assignments[i], relation_oids[i]),
                        queries=queries, eligible=eligible, candidates=candidates, sample=sample,
                        prefix=prefix, helpers=helpers, run_formal=run_formal,
                        forest10_runner=forest10_runner, output=output_dir / f"worker{i}.jsonl",
                        failure=failures) for i in range(2)]
                    worker_results = []
                    for future in futures:
                        worker_results.append(future.result())
                measurement_seconds = time.monotonic() - started_measurement
                if failures or STOP.is_set():
                    raise RuntimeError(f"full-valid collection stopped with {len(failures)} failed observation(s)")
                if sum(row["calls"] for row in worker_results) != expected_total:
                    raise RuntimeError("worker outputs do not contain all frozen EXPLAIN calls")
                coverage_path = root / "coverage.jsonl"
                with coverage_path.open("x", encoding="utf-8") as stream:
                    for query in queries:
                        stream.write(json.dumps({"query_id": query["query_id"],
                            "source_index": query["source_index"], "eligible_config_ids": eligible[query["query_id"]]},
                            sort_keys=True, separators=(",", ":")) + "\n")
                result.update({"status": "COLLECTED_UNVERIFIED", "queries": len(queries),
                    "candidate_count": len(candidates), "configuration_count": len(candidates) + 1,
                    "calls_expected": expected_total, "empty_calls": empty_count,
                    "singleton_calls": singleton_count, "worker_results": worker_results,
                    "worker_count": 2, "sample": {"sha256": sample_identity["sha256"],
                        "bytes": sample_identity["bytes"], "header": header,
                        "relation_oids_by_worker": relation_oids},
                    "measurement_seconds": round(measurement_seconds, 3),
                    "calls_per_second": round(expected_total / measurement_seconds, 6),
                    "cluster_shutdown": "PASS"})
            for name, digest in build["binary_sha256"].items():
                if smoke.sha256_file(prefix / "bin" / name) != digest:
                    raise RuntimeError(f"shared PostgreSQL installation changed: {name}")
            result["shared_install_unchanged"] = True
            result["status"] = "PASS_PENDING_READ_ONLY_VERIFICATION"
    except BaseException as exc:
        STOP.set()
        result.update({"status": "BLOCKED", "phase": phase,
            "error_class": type(exc).__name__, "error": str(exc)[:700],
            "failures": failure, "resource_guard_stop_reason": guard.stop_reason})
    finally:
        while cluster_contexts:
            try:
                cluster_contexts.pop().__exit__(None, None, None)
            except Exception:
                pass
        guard.__exit__()
        result["elapsed_seconds_total"] = round(time.monotonic() - started, 3)
        result["run_directory_peak_bytes"] = guard.peak
        result["resource_guard"] = {"hard_hours": 8, "early_stop_hours": 7.5,
            "hard_bytes": 4 * 1024**3, "early_stop_bytes": 3 * 1024**3,
            "stop_reason": guard.stop_reason}
        (root / "run-summary.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
        signal.signal(signal.SIGINT, original_sigint)
    return result


def main() -> int:
    run_root = runtime_runs("ess-research", 71)
    run_root.mkdir(parents=True, exist_ok=True)
    root = run_root / (time.strftime("%Y%m%d-%H%M%S-census13-full-valid", time.gmtime()))
    result = execute(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["status"] == "PASS_PENDING_READ_ONLY_VERIFICATION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
