"""Reclassify preserved v8 observations with source-based predicate eligibility."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any

from matching_verifier import MatchingVerificationError, verify_maximal_matching
from predicate_eligibility import eligible_candidate_edges


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def write_exclusive(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        stream.write(content)


def require_fresh_outputs(paths: list[Path]) -> None:
    existing = [str(path) for path in paths if path.exists()]
    if existing:
        raise FileExistsError("refusing to overwrite derived evidence: " + ", ".join(existing))


def redacted_record(record: dict[str, Any]) -> dict[str, Any]:
    """Keep row identity and classification evidence, excluding SQL/log payloads."""

    return {
        "scenario": record["scenario"],
        "task_id": record["task_id"],
        "resources": record["resources"],
        "repetition": record["repetition"],
        "order_index": record["order_index"],
        "selected_stat_oids": record["trace_selected_stat_oids"],
        "selected_candidate_ids": record["selected_candidate_ids"],
        "trace_claimed_clauses": record["trace_claimed_clauses"],
        "trace_candidate_none_seen": record["trace_candidate_none_seen"],
        "eligible_candidate_ids": record["requested_eligible_candidate_ids"],
        "outside_restricted_gate_candidate_ids": record["outside_restricted_gate_candidate_ids"],
        "legacy_graph_failed": record["legacy_graph_failed"],
        "legacy_statuses": record.get("legacy_statuses", []),
        "status": record["status"],
        "reason": record.get("reason", ""),
    }


def reclassify(manifest: dict[str, Any], observations: list[dict[str, Any]], query_sql: dict[str, str]) -> dict[str, Any]:
    candidates = manifest["candidates"]
    tasks = {item["id"]: item for item in manifest["tasks"]}
    records = []
    for observation in observations:
        if observation["task_id"] not in tasks:
            raise ValueError(f"observation references unknown task: {observation['task_id']}")
        clauses, eligibility = eligible_candidate_edges(query_sql[observation["query_id"]], candidates)
        ledger = {item["candidate_id"]: item for item in observation["ledger"]}
        resources = observation["resources"]
        requested = [item for item in resources if eligibility[item]["eligible"]]
        outside = [item for item in resources if not eligibility[item]["eligible"]]
        available = [item for item in requested if ledger.get(item, {}).get("built_mcv")]
        selected_oids = observation["trace"]["selected_stat_oids"]
        oid_to_candidate = {str(item["statistic_oid"]): item["candidate_id"] for item in observation["ledger"]}
        unmapped_oids = [oid for oid in selected_oids if str(oid) not in oid_to_candidate]
        selected = [oid_to_candidate[str(oid)] for oid in selected_oids if str(oid) in oid_to_candidate]
        selected_outside = [item for item in selected if item not in requested]
        legacy_failed = any(item.get("status") == "FAIL" for item in observation.get("graph_checks", []))
        legacy_statuses = [item.get("status", "") for item in observation.get("graph_checks", [])]
        record: dict[str, Any] = {
            "scenario": observation["scenario"],
            "task_id": observation["task_id"],
            "resources": resources,
            "repetition": observation["repetition"],
            "order_index": observation["order_index"],
            "predicate_clauses": [clause.__dict__ for clause in clauses],
            "eligibility_by_candidate": eligibility,
            "requested_eligible_candidate_ids": requested,
            "outside_restricted_gate_candidate_ids": outside,
            "available_built_mcv_candidate_ids": available,
            "selected_candidate_ids": selected,
            "selected_outside_restricted_gate_candidate_ids": selected_outside,
            "unmapped_selected_stat_oids": unmapped_oids,
            "trace_selected_stat_oids": selected_oids,
            "trace_claimed_clauses": observation["trace"].get("claimed_clauses", []),
            "trace_candidate_none_seen": observation["trace"].get("candidate_none_seen", False),
            "legacy_graph_failed": legacy_failed,
            "legacy_statuses": legacy_statuses,
            "status": (
                "INCONCLUSIVE_UNMAPPED_SELECTED_OID" if unmapped_oids
                else "INCONCLUSIVE_SELECTED_OUTSIDE_ELIGIBILITY" if selected_outside
                else "SUPPORTED_FOR_ELIGIBLE_GRAPH"
            ),
        }
        if unmapped_oids:
            record["reason"] = "unmapped_selected_stat_oid"
        elif selected_outside:
            record["reason"] = "selected_statistic_outside_source_eligibility"
        else:
            try:
                record["matching_check"] = verify_maximal_matching(candidates, available, [item for item in selected if item in requested])
                record["matching_status"] = "PASS"
                if legacy_failed and outside:
                    record["status"] = "INCONCLUSIVE_OUTSIDE_RESTRICTED_GATE"
                    record["reason"] = "legacy_failure_used_candidate_outside_restricted_gate"
            except MatchingVerificationError as exc:
                record["matching_status"] = "FAIL"
                record["matching_error"] = str(exc)
                record["status"] = "MODEL_LIMITATION_COUNTEREXAMPLE"
        records.append(record)

    return {
        "format": "ess-issue40-v8-eligibility-reclassification-v1",
        "source_observations_preserved": True,
        "observation_count": len(records),
        "status_counts": dict(Counter(item["status"] for item in records)),
        "matching_status_counts": dict(Counter(item.get("matching_status", "NOT_APPLICABLE") for item in records)),
        "legacy_graph_failed_count": sum(item["legacy_graph_failed"] for item in records),
        "legacy_failed_status_counts": dict(Counter(item["status"] for item in records if item["legacy_graph_failed"])),
        "outside_gate_count": sum(bool(item["outside_restricted_gate_candidate_ids"]) for item in records),
        "unmapped_selected_oid_count": sum(bool(item["unmapped_selected_stat_oids"]) for item in records),
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--canonical", type=Path, required=True)
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--redacted-ledger", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    observations = [json.loads(line) for line in args.observations.read_text(encoding="utf-8").splitlines() if line]
    wanted = {item["query_id"] for item in manifest["tasks"]}
    query_sql: dict[str, str] = {}
    with gzip.open(args.canonical, "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            if item.get("query_id") in wanted:
                query_sql[item["query_id"]] = item["sql"]
    if query_sql.keys() != wanted:
        raise RuntimeError("canonical query SQL is incomplete")
    require_fresh_outputs([args.output, args.redacted_ledger])
    result = reclassify(manifest, observations, query_sql)
    ledger_text = "".join(json.dumps(redacted_record(item), sort_keys=True) + "\n" for item in result["records"])
    write_exclusive(args.redacted_ledger, ledger_text)
    result["provenance"] = {
        "source_observations_path": str(args.observations),
        "source_observations_sha256": sha256_file(args.observations),
        "redacted_ledger_path": str(args.redacted_ledger),
        "redacted_ledger_sha256": sha256_file(args.redacted_ledger),
    }
    output_text = json.dumps(result, indent=2, sort_keys=True) + "\n"
    write_exclusive(args.output, output_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
