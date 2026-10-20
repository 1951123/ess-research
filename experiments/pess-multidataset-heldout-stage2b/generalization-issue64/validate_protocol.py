"""Static, outcome-free validation for the Issue #64 protocol draft."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROTOCOL = Path(__file__).with_name("protocol-v1.json")
EXPECTED_DATASETS = {"forest10", "census13", "dmv11", "power7"}
EXPECTED_BUDGETS = [0, 2, 3, 5]


def validate(document: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    if document.get("format") != "ess-stage2b-extstats-generalization-protocol-v1":
        errors.append("unexpected protocol format")
    if document.get("status") != "OUTCOME_FREE_DRAFT_REQUIRES_RESEARCHER_APPROVAL":
        errors.append("draft must remain explicitly unapproved")
    if document.get("phase0_only") is not True:
        errors.append("phase0_only must be true")
    auth = document.get("authorization", {})
    for key in (
        "new_postgresql_heldout_measurements",
        "test_truth_or_test_estimates_read_for_design",
        "historical_v1_v4_evidence_modified",
        "ess_postgresql_or_ess_advisor_modified",
        "paper_modified",
    ):
        if auth.get(key) is not False:
            errors.append(f"authorization.{key} must be false")

    scope = document.get("scope", {})
    if set(scope.get("datasets", [])) != EXPECTED_DATASETS:
        errors.append("dataset scope must be the four declared AreCEL datasets")
    if scope.get("methods") != ["Empty", "Nominal", "PESS"]:
        errors.append("method set must be Empty/Nominal/PESS")

    candidates = document.get("candidate_universe", {})
    for dataset in sorted(EXPECTED_DATASETS):
        pairs = candidates.get(dataset)
        if not isinstance(pairs, list) or not pairs:
            errors.append(f"candidate universe missing for {dataset}")
            continue
        ids = [item.split(":", 1)[0] for item in pairs]
        if len(ids) != len(set(ids)):
            errors.append(f"candidate IDs are not unique for {dataset}")

    budget = document.get("calibration_and_selection", {}).get("resource_budget", {})
    if budget.get("budgets") != EXPECTED_BUDGETS:
        errors.append("budgets must remain [0, 2, 3, 5]")

    metric = document.get("metrics", {}).get("primary", {})
    if metric.get("name") != "per-dataset P95 Q-error with one-row floor (Q1)":
        errors.append("primary metric must be explicit Q1 P95")
    if "max(E,A,1)/max(min(E,A),1)" not in metric.get("formula", ""):
        errors.append("Q1 floor formula missing")
    if "not exactly AreCEL" not in metric.get("adaptation_note", ""):
        errors.append("Q1 must be distinguished from natural AreCEL Q-error")

    cohort = document.get("cohort_and_independence", {})
    if "not fresh held-out evidence" not in cohort.get("legacy_arecel_test", ""):
        errors.append("legacy test exposure boundary missing")
    for key in ("group_split", "historical_overlap", "test_freeze"):
        if not cohort.get(key):
            errors.append(f"cohort independence field missing: {key}")

    gates = document.get("postgresql_physical_evaluation", {})
    for key in ("same_conditions", "sample_gate", "coverage", "mismatch", "failure_policy"):
        if not gates.get(key):
            errors.append(f"PostgreSQL physical gate missing: {key}")

    feasibility = document.get("phase0_feasibility", {})
    preflight = feasibility.get("per_dataset_preflight", {})
    if set(preflight) != EXPECTED_DATASETS:
        errors.append("per-dataset feasibility checklist must cover all four datasets")
    for dataset in EXPECTED_DATASETS & set(preflight):
        row = preflight[dataset]
        if not row.get("csv_rows") or not row.get("future_required"):
            errors.append(f"per-dataset provenance/future checklist incomplete: {dataset}")
    if feasibility.get("PostgreSQL") != "NOT RUN; Gate A readiness does not authorize held-out execution":
        errors.append("Phase 0 PostgreSQL non-execution status missing")
    return errors


def main() -> int:
    document = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    errors = validate(document)
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: protocol schema and Phase 0 safety invariants")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
