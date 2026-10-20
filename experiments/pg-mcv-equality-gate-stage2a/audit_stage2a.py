#!/usr/bin/env python3
"""Independently re-audit redacted Stage 2A observations."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from matching_verifier import MatchingVerificationError, verify_maximal_matching
from source_ledger import build_source_ledger, parse_equality_clauses, verify_trace_against_ledger


def audit(observations: Path, manifest: Path) -> dict[str, object]:
    frozen = json.loads(manifest.read_text())
    definitions = frozen["fixture"]["candidate_definitions"]
    statuses: Counter[str] = Counter()
    selected_patterns: Counter[tuple[str, ...]] = Counter()
    ledger_mismatches: list[dict[str, object]] = []
    matching_errors: list[dict[str, object]] = []
    rows = [json.loads(line) for line in observations.read_text().splitlines() if line.strip()]
    for row in rows:
        clauses = parse_equality_clauses(row["query_sql"], next(
            item["expected_columns"] for item in frozen["fixture"]["queries"] if item["id"] == row["query_id"]
        ))
        ledger = build_source_ledger(row["catalog_rows"], clauses)
        gate = verify_trace_against_ledger(ledger, row["catalog_rows"], row["trace"])
        status = str(gate["status"])
        statuses[status] += 1
        selected_patterns[tuple(gate["selected_candidate_ids"])] += 1
        if ledger["expected_selected_oids"] != row["source_ledger"]["expected_selected_oids"] or gate["status"] != row["gate"]["status"]:
            ledger_mismatches.append({
                "setup_id": row["setup_id"],
                "query_id": row["query_id"],
                "stored_gate": row["gate"],
                "recomputed_gate": gate,
            })
        if status == "WITHIN_GATE_PASS":
            try:
                verify_maximal_matching(definitions, ledger["usable_ids"], gate["selected_candidate_ids"])
            except MatchingVerificationError as error:
                matching_errors.append({
                    "setup_id": row["setup_id"],
                    "query_id": row["query_id"],
                    "error": str(error),
                })
    return {
        "format": "ess-issue47-stage2a-independent-audit-v1",
        "observation_count": len(rows),
        "status_counts": dict(sorted(statuses.items())),
        "selected_patterns": {"|".join(pattern): count for pattern, count in sorted(selected_patterns.items())},
        "ledger_mismatch_count": len(ledger_mismatches),
        "matching_error_count": len(matching_errors),
        "ledger_mismatches": ledger_mismatches,
        "matching_errors": matching_errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--observations", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = audit(args.observations, args.manifest)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if not result["ledger_mismatch_count"] and not result["matching_error_count"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
