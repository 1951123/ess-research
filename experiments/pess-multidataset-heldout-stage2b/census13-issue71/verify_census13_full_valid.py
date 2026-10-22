"""Read-only verification of the frozen full Census13 valid observation run."""

from __future__ import annotations

import hashlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))

from census13_schedule import assign_configurations, calls_for_worker
from run_census13_full_valid import PLAN_SHA256, _queries_and_schedule, smoke
sha256_file = smoke.sha256_file


def raw_preclamp(value: Any, *, query_id: str, config_id: str) -> Decimal:
    """Parse a preserved JSON numeric token; zero is valid, non-finite is not."""
    if isinstance(value, bool) or value is None:
        raise ValueError(f"missing/malformed pre-clamp estimate at {query_id}/{config_id}")
    try:
        estimate = Decimal(str(value))
    except (InvalidOperation, ValueError) as exc:
        raise ValueError(f"malformed pre-clamp estimate at {query_id}/{config_id}") from exc
    if not estimate.is_finite() or estimate < 0:
        raise ValueError(f"negative/nonfinite pre-clamp estimate at {query_id}/{config_id}")
    return estimate


def verify(run_dir: Path) -> dict[str, Any]:
    plan_path = HERE / "census13-stage2b-plan-v1.json"
    if sha256_file(plan_path) != PLAN_SHA256:
        raise ValueError("frozen plan digest mismatch")
    plan = json.loads(plan_path.read_text())
    summary_path = run_dir / "run-summary.json"
    summary = json.loads(summary_path.read_text())
    if summary.get("status") != "PASS_PENDING_READ_ONLY_VERIFICATION":
        raise ValueError("run is not a completed successful acquisition")
    if any(summary.get(flag) is not False for flag in
           ("truth_loaded", "test_truth_loaded", "test_estimates_or_outcomes_accessed")):
        raise ValueError("acquisition crossed the outcome-free boundary")
    if summary.get("frozen_plan_sha256") != PLAN_SHA256:
        raise ValueError("run summary does not attest the frozen plan")
    if summary.get("cluster_shutdown") != "PASS" or summary.get("resource_guard", {}).get("stop_reason"):
        raise ValueError("cluster shutdown or run resource guard did not pass")
    if summary.get("run_directory_peak_bytes", 2**63) >= 4 * 1024**3:
        raise ValueError("run directory reached the 4-GiB hard cap")
    if summary.get("elapsed_seconds_total", 2**63) >= 8 * 3600:
        raise ValueError("run reached the 8-hour hard cap")
    if summary.get("candidate_count") != 78 or summary.get("queries") != 10_000:
        raise ValueError("run query/candidate count differs from the frozen scope")

    queries, candidates, eligible = _queries_and_schedule(plan)
    query_ids = [query["query_id"] for query in queries]
    if len(query_ids) != 10_000 or len(query_ids) != len(set(query_ids)):
        raise ValueError("official valid query identity set is incomplete or duplicated")
    assignments = assign_configurations(candidates, 2)
    expected_by_worker = [calls_for_worker(configs, query_ids, eligible) for configs in assignments]
    expected_total = sum(map(len, expected_by_worker))
    if expected_total != 288_849:
        raise ValueError("reconstructed full-valid schedule is not 288849 calls")

    worker_summaries = {item["worker_id"]: item for item in summary.get("worker_results", [])}
    if set(worker_summaries) != {0, 1}:
        raise ValueError("both worker result summaries are required")
    config_counts: dict[str, int] = {}
    raw_value_counts = {"Empty": {"zero": 0, "positive_below_one": 0},
                        "singleton": {"zero": 0, "positive_below_one": 0}}
    config_query_hashes: dict[str, str] = {}
    total = 0
    for worker_id in (0, 1):
        path = run_dir / "observations" / f"worker{worker_id}.jsonl"
        if smoke.sha256_file(path) != worker_summaries[worker_id]["output_sha256"]:
            raise ValueError(f"worker{worker_id} raw JSONL checksum mismatch")
        expected = expected_by_worker[worker_id]
        found: list[tuple[str, str]] = []
        per_config_ids: dict[str, list[str]] = {}
        with path.open(encoding="utf-8") as stream:
            for line_no, line in enumerate(stream, 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(f"worker{worker_id} invalid JSON line {line_no}") from exc
                if row.get("status") != "SUCCESS" or row.get("worker_id") != worker_id:
                    raise ValueError(f"worker{worker_id} failed/misassigned observation at line {line_no}")
                query_id, config_id = row.get("query_id"), row.get("config_id")
                if not isinstance(query_id, str) or not isinstance(config_id, str):
                    raise ValueError(f"worker{worker_id} missing observation identity at line {line_no}")
                found.append((query_id, config_id))
                per_config_ids.setdefault(config_id, []).append(query_id)
                if row.get("diagnostics_status") != "complete":
                    raise ValueError(f"incomplete ESS diagnostics at {query_id}/{config_id}")
                estimate = raw_preclamp(row.get("nrows_preclamp"), query_id=query_id,
                                         config_id=config_id)
                kind = "Empty" if config_id == "Empty" else "singleton"
                if estimate == 0:
                    raw_value_counts[kind]["zero"] += 1
                elif estimate < 1:
                    raw_value_counts[kind]["positive_below_one"] += 1
                events = row.get("mcv_events")
                state = row.get("mcv_diagnostics_status")
                if not isinstance(events, list) or state not in {"VERIFIED", "NO_MCV_EVENTS"}:
                    raise ValueError(f"invalid MCV diagnostic status at {query_id}/{config_id}")
                if (state == "NO_MCV_EVENTS") != (len(events) == 0):
                    raise ValueError(f"MCV event/status mismatch at {query_id}/{config_id}")
                for event in events:
                    if (not isinstance(event.get("statistic_id"), str)
                            or not isinstance(event.get("clause_indexes"), list)
                            or not event["clause_indexes"]):
                        raise ValueError(f"unmapped/incomplete MCV event at {query_id}/{config_id}")
                    if any(isinstance(event.get(field), bool) or not isinstance(event.get(field), int)
                           or event[field] <= 0 for field in ("relation_oid", "stat_oid")):
                        raise ValueError(f"invalid MCV relation/statistic OID at {query_id}/{config_id}")
                config_counts[config_id] = config_counts.get(config_id, 0) + 1
        if found != list(expected):
            raise ValueError(f"worker{worker_id} output differs from exact frozen schedule/order")
        for config_id, ids in per_config_ids.items():
            config_query_hashes[f"{worker_id}:{config_id}"] = hashlib.sha256(
                "\n".join(ids).encode("utf-8")).hexdigest()
        if len(found) != worker_summaries[worker_id]["calls"]:
            raise ValueError(f"worker{worker_id} summary call count mismatch")
        total += len(found)

    if total != 288_849 or config_counts.get("Empty") != 10_000:
        raise ValueError("verified coverage count does not match frozen totals")
    if set(config_counts) != {"Empty", *(candidate["id"] for candidate in candidates)}:
        raise ValueError("one or more frozen configurations are missing")
    for candidate in candidates:
        if config_counts[candidate["id"]] != candidate["eligible_valid_query_count"]:
            raise ValueError(f"singleton observation count differs for {candidate['id']}")

    coverage_path = run_dir / "coverage.jsonl"
    coverage_rows = [json.loads(line) for line in coverage_path.read_text().splitlines()]
    expected_coverage = [{"query_id": query["query_id"], "source_index": query["source_index"],
                          "eligible_config_ids": eligible[query["query_id"]]} for query in queries]
    if coverage_rows != expected_coverage:
        raise ValueError("persisted query/config eligibility coverage differs from frozen valid workload")

    sample_path = run_dir / "clusters" / "results" / "census13.fixed-sample"
    if not sample_path.is_file() or smoke.sha256_file(sample_path) != summary["sample"]["sha256"]:
        raise ValueError("local fixed sample is absent or its digest differs from run summary")
    if summary["sample"]["header"].get("server_version") != "16.14":
        raise ValueError("sample header does not attest PostgreSQL 16.14")
    return {"format": "ess-issue71-census13-full-valid-verification-v1", "status": "PASS",
            "run_id": summary["run_id"], "frozen_plan_sha256": PLAN_SHA256,
            "valid_query_count": len(queries), "candidate_count": len(candidates),
            "configuration_count": len(config_counts), "total_calls": total,
            "empty_calls": config_counts["Empty"],
            "singleton_calls": total - config_counts["Empty"],
            "configuration_call_counts": dict(sorted(config_counts.items())),
            "raw_preclamp_counts_by_configuration_family": raw_value_counts,
            "worker_call_counts": {str(key): value["calls"] for key, value in worker_summaries.items()},
            "configuration_ordered_query_sha256": dict(sorted(config_query_hashes.items())),
            "raw_worker_sha256": {str(key): value["output_sha256"] for key, value in worker_summaries.items()},
            "coverage_sha256": sha256_file(coverage_path),
            "sample_sha256": summary["sample"]["sha256"],
            "run_directory_peak_bytes": summary["run_directory_peak_bytes"],
            "elapsed_seconds_total": summary["elapsed_seconds_total"],
            "model_fit_or_selection_performed": False,
            "test_truth_or_outcomes_accessed": False}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_census13_full_valid.py RUN_DIR")
    print(json.dumps(verify(Path(sys.argv[1]).resolve()), indent=2, sort_keys=True))
