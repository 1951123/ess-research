"""Verify and deterministically compress the authorized Census13 smoke records."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from pathlib import Path

from census13_schedule import assign_configurations, calls_for_worker, compare_smoke_observations
from freeze_census13_plan import REPO_ROOT
from ess_research.arecel.archive import prepare_valid_workload
from ess_research.arecel.candidates import discover_candidates


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_and_persist(run_dir: Path, output_dir: Path) -> dict:
    plan_path = Path(__file__).with_name("census13-stage2b-plan-v1.json")
    plan = json.loads(plan_path.read_text())
    summary = json.loads((run_dir / "smoke-summary.json").read_text())
    if summary.get("status") != "PASS" or summary.get("truth_loaded") is not False or summary.get("official_test_access") is not False:
        raise ValueError("smoke run is not a successful outcome-free run")
    with prepare_valid_workload(issue=71, dataset="census13") as prepared:
        if prepared.manifest.get("labels_loaded") is not False:
            raise ValueError("valid workload preparation does not attest labels_loaded=false")
        workload = json.loads(prepared.workload_path.read_text())
    queries = workload["queries"]
    columns = tuple(plan["dataset_shape"]["source_columns_in_order"])
    discovery = discover_candidates(queries, columns)
    support = {(row["column_a"], row["column_b"]): row["eligible_valid_query_count"]
               for row in discovery["candidates"]}
    candidates = plan["candidate_policy"]["candidates"]
    for candidate in candidates:
        pair = tuple(candidate["endpoints"])
        if support.get(pair) != candidate["eligible_valid_query_count"]:
            raise ValueError("valid static eligibility differs from frozen Census13 plan")

    wanted_ids = plan["serial_parallel_smoke"]["valid_query_ids"]
    query_map = {query["query_id"]: query for query in queries}
    if len(query_map) != len(queries) or any(query_id not in query_map for query_id in wanted_ids):
        raise ValueError("frozen smoke query IDs are missing or duplicated")
    smoke_queries = [query_map[query_id] for query_id in wanted_ids]
    candidate_specs = [{"id": row["id"], "eligible_valid_query_count": row["eligible_valid_query_count"]}
                       for row in candidates]
    eligible = {}
    for query in smoke_queries:
        found = discover_candidates([query], columns)
        eligible[query["query_id"]] = [row["id"] for row in candidates
            if any(item["column_a"] == row["endpoints"][0] and item["column_b"] == row["endpoints"][1]
                   for item in found["candidates"])]
    serial_assignment = assign_configurations(candidate_specs, 1)
    expected = calls_for_worker(serial_assignment[0], wanted_ids, eligible)
    if len(expected) != plan["serial_parallel_smoke"]["calls_per_mode"]:
        raise ValueError("reconstructed smoke schedule differs from frozen call count")

    def read_rows(name: str):
        path = run_dir / name
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
        if sha256(path) != summary["serial" if name.startswith("serial") else "parallel"]["output_sha256"]:
            raise ValueError(f"raw observation digest differs from run summary: {name}")
        return path, rows

    serial_path, serial = read_rows("serial-smoke.jsonl")
    parallel_path, parallel = read_rows("parallel-smoke.jsonl")
    parity = compare_smoke_observations(serial, parallel, expected)
    if len(serial) != len(parallel) or len(serial) != len(expected):
        raise ValueError("serial/parallel observation counts differ from the frozen schedule")
    output_dir.mkdir(parents=True, exist_ok=False)
    artifacts = {}
    for label, source in (("serial", serial_path), ("parallel", parallel_path)):
        target = output_dir / f"{label}-smoke.jsonl.gz"
        with source.open("rb") as raw, target.open("xb") as out:
            with gzip.GzipFile(fileobj=out, mode="wb", filename="", compresslevel=9, mtime=0) as compressed:
                while block := raw.read(1024 * 1024):
                    compressed.write(block)
        artifacts[target.name] = {"sha256": sha256(target), "bytes": target.stat().st_size,
                                  "source_sha256": sha256(source), "rows": len(serial if label == "serial" else parallel)}
    result = {
        "format": "ess-issue71-census13-smoke-verification-v1",
        "status": "PASS",
        "run_id": summary["run_id"],
        "frozen_plan_sha256": sha256(plan_path),
        "valid_only": True,
        "labels_loaded": False,
        "test_truth_loaded": False,
        "calls_per_mode": len(expected),
        "query_count": len(wanted_ids),
        "parity": parity,
        "elapsed_seconds_total": summary["elapsed_seconds_total"],
        "serial": summary["serial"],
        "parallel": summary["parallel"],
        "speedup": summary["parallel_speedup"],
        "peak_allocated_bytes": summary["run_directory_peak_bytes"],
        "sample_sha256": summary["sample"]["sha256"],
        "artifacts": artifacts,
    }
    (output_dir / "verification.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = verify_and_persist(args.run_dir, args.output_dir)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
