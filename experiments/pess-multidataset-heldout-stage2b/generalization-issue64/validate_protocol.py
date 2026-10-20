"""Static, outcome-free validation for the Issue #64 protocol draft."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


PROTOCOL = Path(__file__).with_name("protocol-v1.json")
EXPECTED_DATASETS = {"forest10", "census13", "dmv11", "power7"}
EXPECTED_BUDGETS = [0, 2, 3, 5]
EXPECTED_TEST_GROUPS = 1000
EXPECTED_REPLICATES = 2
EXPECTED_MAX_TREATMENTS = 7
ISSUE59_PROTOCOL_SHA256 = "8e8d25bc9d2847936d2c45f51a3f870a8c44e632938e30db19cfe8aaf0d9063a"


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
    if candidates.get("source_protocol_sha256") != ISSUE59_PROTOCOL_SHA256:
        errors.append("candidate universe must pin the reviewed Issue #59 protocol hash")
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
    if "not a measured/proxy-weighted physical" not in budget.get("meaning", ""):
        errors.append("resource budget must be explicitly count-based, not physical cost")

    metric = document.get("metrics", {}).get("primary", {})
    if metric.get("name") != "per-dataset P95 Q-error with one-row floor (Q1)":
        errors.append("primary metric must be explicit Q1 P95")
    if "max(E,A,1)/max(min(E,A),1)" not in metric.get("formula", ""):
        errors.append("Q1 floor formula missing")
    if "not exactly AreCEL" not in metric.get("adaptation_note", ""):
        errors.append("Q1 must be distinguished from natural AreCEL Q-error")
    if "metric_reference.py::q1" not in metric.get("formula_reference", ""):
        errors.append("Q1 formula must point to its tested pure reference implementation")
    if "round_half_even_50" not in metric.get("quantile", ""):
        errors.append("per-policy replicate aggregation precision/rounding missing")
    if "round_half_even_50" not in metric.get("contrast", ""):
        errors.append("paired estimand must use the same explicit log-Q1 aggregation")
    pair_class = metric.get("pairwise_classification", "")
    if "same recorded delta_i" not in pair_class or "delta_i<0" not in pair_class:
        errors.append("benefit/harm/tie classification must use the paired log-Q1 estimand")
    if "UNRESOLVED" not in metric.get("replicate_failure", ""):
        errors.append("missing replicate handling is not predeclared")
    if "INCONCLUSIVE" not in metric.get("replicate_failure", ""):
        errors.append("incomplete cohort must fail closed")

    cohort = document.get("cohort_and_independence", {})
    if "not fresh held-out evidence" not in cohort.get("legacy_arecel_test", ""):
        errors.append("legacy test exposure boundary missing")
    for key in ("group_split", "historical_overlap", "test_freeze"):
        if not cohort.get(key):
            errors.append(f"cohort independence field missing: {key}")
    recipe = document.get("cohort_generation_recipe", {})
    if recipe.get("status") != "DETERMINISTIC_RECIPE_SPECIFIED_NOT_EXECUTED_NO_QUERY_MANIFEST_EXISTS_YET":
        errors.append("cohort status must say recipe-only and not generated")
    if recipe.get("seed_by_dataset", {}) != {
        "forest10": 6401, "census13": 6402, "dmv11": 6403, "power7": 6404
    }:
        errors.append("per-dataset cohort seeds are not frozen")
    if "normalised_template" not in recipe.get("fingerprint_contract", {}).get("template", ""):
        errors.append("template normalization must cite the Issue #59 implementation")
    if "1000000" not in recipe.get("selection_and_size", {}).get("deterministic_acceptance", ""):
        errors.append("bounded deterministic cohort acceptance recipe missing")
    if recipe.get("selection_and_size", {}).get("maximum_template_attempts_per_dataset") != 1_000_000:
        errors.append("maximum template-generation attempts must be an exact hard limit")
    if len(recipe.get("historical_fingerprint_gate", {}).get("coverage_required", [])) < 4:
        errors.append("historical fingerprint coverage inventory is incomplete")
    if "blocks cohort freeze" not in recipe.get("historical_fingerprint_gate", {}).get("acceptance", "").lower():
        errors.append("missing historical fingerprint coverage must block cohort freeze")
    selection = recipe.get("selection_and_size", {})
    schema_gate = selection.get("schema_capacity_gate", {})
    if "schema_capacity.py" not in schema_gate.get("implementation", ""):
        errors.append("schema-only stratum capacity implementation is not pinned")
    if len(schema_gate.get("source_pins", {})) < 4:
        errors.append("schema/operator/candidate source pins are incomplete")
    arecel_pin = schema_gate.get("arecel_generator_reference", {})
    if arecel_pin.get("commit") != "aa52da7768023270bad884232972e0b77ec6534a" or len(arecel_pin.get("git_blob_sha", "")) != 40:
        errors.append("AreCEL categorical/operator source reference is not commit/blob pinned")
    if "strict numeric < and >" not in schema_gate.get("supported_operator_rule", ""):
        errors.append("prospective operator extension beyond AreCEL defaults is not disclosed")
    quota_table = schema_gate.get("quota_by_dataset_split", {})
    if not schema_gate.get("quota_status", "").startswith("PROVISIONAL_SCHEMA_ONLY_TARGETS_NOT_FINAL"):
        errors.append("schema-only quota table must remain provisional until pool feasibility passes")
    if recipe.get("historical_fingerprint_gate", {}).get("phase0_check_result") != "BLOCKED_INCOMPLETE_HISTORICAL_FINGERPRINT_LEDGER; no candidate pool was accepted or frozen":
        errors.append("incomplete historical fingerprint evidence must explicitly block cohort freeze")
    for dataset in sorted(EXPECTED_DATASETS):
        dataset_quotas = quota_table.get(dataset, {})
        if set(dataset_quotas) != {"calibration", "heldout"}:
            errors.append(f"schema-derived split quotas missing for {dataset}")
            continue
        for split, quotas in dataset_quotas.items():
            if sum(quotas.values()) != EXPECTED_TEST_GROUPS:
                errors.append(f"{dataset}/{split} predicate-bin quotas must sum to 1000")
            if quotas.get("1") != 0:
                errors.append(f"{dataset}/{split} singleton bin must be descriptive only")
            if sum(value for bin_name, value in quotas.items() if bin_name not in ("1", "2")) < EXPECTED_TEST_GROUPS // 2:
                errors.append(f"{dataset}/{split} requires at least 500 queries with >=3 predicates")
    if "STRUCTURALLY_INFEASIBLE" not in schema_gate.get("capacity_rule", ""):
        errors.append("schema-infeasible strata must be distinguished from attempt-pool shortfalls")
    if "conflict with exactly one maximal matching" not in selection.get("minimum_shape_coverage", "").lower():
        errors.append("exclusive graph-stratum feasibility correction missing")

    gates = document.get("postgresql_physical_evaluation", {})
    for key in ("same_conditions", "sample_gate", "coverage", "mismatch", "failure_policy"):
        if not gates.get(key):
            errors.append(f"PostgreSQL physical gate missing: {key}")
    if not gates.get("sample_block_definition"):
        errors.append("matched sample-block identity is not operationally defined")
    if "exactly one ANALYZE" not in gates.get("treatment_order_and_analyze", ""):
        errors.append("treatment-specific ANALYZE sequence is not frozen")
    if "does not invalidate its Q1" not in gates.get("coverage", ""):
        errors.append("trace completeness must be separated from Q1 validity")
    if "random" not in gates.get("same_conditions", "") and "permutation" not in gates.get("same_conditions", ""):
        errors.append("treatment execution order is not frozen/counterbalanced")

    caps = document.get("prospective_caps", {})
    if caps.get("test_template_groups_per_dataset") != EXPECTED_TEST_GROUPS:
        errors.append("test group count must be an exact 1000-group hard limit")
    if caps.get("hard_max_calibration_queries_per_dataset") != EXPECTED_TEST_GROUPS:
        errors.append("calibration query count must be hard-capped at 1000 per dataset")
    if caps.get("hard_max_heldout_queries_per_dataset") != EXPECTED_TEST_GROUPS:
        errors.append("held-out query count must be hard-capped at 1000 per dataset")
    if caps.get("queries_per_group") != 1:
        errors.append("query/group ratio must be exactly one")
    split_counts = recipe.get("selection_and_size", {}).get("per_dataset", {})
    if split_counts.get("calibration_groups") != EXPECTED_TEST_GROUPS:
        errors.append("calibration cohort count must be fixed at 1000 groups")
    if split_counts.get("heldout_groups") != EXPECTED_TEST_GROUPS:
        errors.append("held-out cohort count must be fixed at 1000 groups")
    if split_counts.get("queries_per_group") != 1:
        errors.append("cohort manifest must contain one SQL query per group")
    expected_calibration_plan_cap = (
        len(EXPECTED_DATASETS)
        * caps.get("calibration_template_groups_per_dataset", 0)
        * caps.get("queries_per_group", 0)
        * caps.get("max_calibration_sets_per_dataset", 0)
        * caps.get("calibration_sample_replicates", 0)
    )
    expected_heldout_plan_cap = (
        len(EXPECTED_DATASETS)
        * EXPECTED_TEST_GROUPS
        * caps.get("queries_per_group", 0)
        * caps.get("max_unique_treatment_sets_per_dataset", 0)
        * caps.get("heldout_sample_replicates", 0)
    )
    if caps.get("max_calibration_query_plans") != expected_calibration_plan_cap:
        errors.append("calibration query-plan cap does not match the frozen maximum design")
    if caps.get("max_heldout_query_plans") != expected_heldout_plan_cap:
        errors.append("held-out query-plan cap does not match the frozen maximum design")
    if caps.get("max_count_query_plans") != expected_calibration_plan_cap + expected_heldout_plan_cap:
        errors.append("total query-plan hard cap does not match the two-phase maximum design")

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
    pin = document.get("provenance", {}).get("corrected_log_reference_pin", {})
    for key in (
        "validation_diagnostic_code_commit",
        "formal_runner_source_sha256",
        "independent_validation_source_sha256",
        "regression_test_source_sha256",
        "frozen_protocol_v4_sha256",
        "manifest_sha256",
    ):
        value = pin.get(key, "")
        if len(value) != 40 and key == "validation_diagnostic_code_commit":
            errors.append(f"corrected-log reference pin malformed: {key}")
        elif key != "validation_diagnostic_code_commit" and (
            len(value) != 64 or any(ch not in "0123456789abcdef" for ch in value)
        ):
            errors.append(f"corrected-log reference pin malformed: {key}")
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
