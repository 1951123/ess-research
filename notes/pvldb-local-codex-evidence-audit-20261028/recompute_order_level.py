#!/usr/bin/env python3
"""Read-only, full-precision replay of the frozen Issue #107 order estimand.

The existing Issue #125 analyzer verifies the archived query rows and recomputes
Issue #107's aggregate directly from those rows. This wrapper captures that
recomputed aggregate and retains the 156 per-order Test P95 values plus the
post-hoc four-contrast Bonferroni sensitivity intervals.

It reads the configured ESS_RUNTIME_PARENT archives and writes only the small
derived JSON next to this script. It does not start PostgreSQL or edit inputs.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import platform
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
for relative in (
    "src",
    "experiments/arecel-test-generalization-issue101",
    "experiments/oid-order-stress-test-issue105",
    "experiments/oid-uniform-priority-issue107",
    "experiments/oid-order-attribution-issue125",
):
    sys.path.insert(0, str(ROOT / relative))

import numpy as np
from scipy.stats import t
from ess_research.arecel.oid_sampling import (
    build_issue107_schedule,
    canonical_json_bytes,
)

import analyze_issue125 as audit


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def main() -> int:
    frozen_manifest_path = ROOT / "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json"
    sample_path = ROOT / "experiments/oid-uniform-priority-issue107/permutation-sample-v1.json"
    root_seed = 17_770_611_677_888_985_956
    generated_schedule = build_issue107_schedule(
        frozen_manifest_path, root_seed=root_seed
    )
    generated_bytes = canonical_json_bytes(generated_schedule)
    sample_bytes = sample_path.read_bytes()
    if generated_bytes != sample_bytes:
        raise RuntimeError("deterministic schedule replay differs byte-for-byte")

    captured: dict[str, Any] = {}
    original_analyze_results = audit.issue107.analyze_results

    def capture_raw_recomputation(schedule: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
        computed = original_analyze_results(schedule, records)
        captured["analysis"] = computed
        return computed

    audit.issue107.analyze_results = capture_raw_recomputation
    try:
        integrity = audit.run_analysis()
    finally:
        audit.issue107.analyze_results = original_analyze_results

    if integrity.get("status") != "COMPLETE" or not integrity.get(
        "official_aggregate_recomputed_from_raw_and_matched"
    ):
        raise RuntimeError("raw archive integrity or official aggregate comparison failed")
    analysis = captured.get("analysis")
    if not isinstance(analysis, dict):
        raise RuntimeError("raw recomputation was not captured")

    schedule, _ = audit.issue107.checked_frozen_schedule()
    strata: list[dict[str, Any]] = []
    for stratum in schedule["schedules"]:
        dataset, policy = stratum["dataset"], stratum["policy"]
        policy_result = analysis[dataset]["policies"][policy]
        estimate = policy_result["expectation"]["estimates"]["p95"]
        arm_by_order = {
            tuple(arm["permutation"]): arm
            for arm in policy_result["arms"]
        }
        order_values: list[dict[str, Any]] = []
        for scheduled in stratum["permutations"]:
            order = tuple(scheduled["permutation"])
            arm = arm_by_order.get(order)
            if arm is None:
                raise RuntimeError(f"raw results omit scheduled arm: {dataset}/{policy}/{order}")
            y_pi = arm["metrics"]["qerror"]["p95"]
            if not isinstance(y_pi, (int, float)) or not np.isfinite(y_pi):
                raise RuntimeError(f"nonfinite per-order Test P95: {dataset}/{policy}/{order}")
            order_values.append(
                {
                    "configuration_id": arm["configuration_id"],
                    "order": list(order),
                    "selection": scheduled["selection"],
                    "draw_index": scheduled["draw_index"],
                    "inclusion_probability": scheduled["inclusion_probability"],
                    "Y_pi_test_p95_qerror": float(y_pi),
                    "Y_pi_float64_hex": float(y_pi).hex(),
                }
            )

        k = len(stratum["resource_ids"])
        if policy == "nominal":
            design = {
                "fixed_count": 2,
                "fixed_weight_fraction": "2/120",
                "residual_population_size": 118,
                "srswor_sample_size": 22,
                "residual_weight_fraction": "118/120",
                "finite_population_correction_fraction": "96/118",
                "finite_population_correction": 96 / 118,
            }
        elif k == 5:
            design = {
                "finite_population_size": 120,
                "srswor_sample_size": 24,
                "finite_population_correction_fraction": "96/120",
                "finite_population_correction": 96 / 120,
            }
        else:
            design = {
                "finite_population_size": 6,
                "enumerated_order_count": 6,
                "finite_population_correction_fraction": "0/6",
                "finite_population_correction": 0.0,
            }

        strata.append(
            {
                "dataset": dataset,
                "policy": policy,
                "case_id": stratum["case_id"],
                "resource_ids": stratum["resource_ids"],
                "permutation_population_size": stratum["permutation_population_size"],
                "sample_sha256": stratum["sample_sha256"],
                "design": design,
                "order_level_Y_pi": order_values,
                "mu_hat": float(estimate["estimate"]),
                "mu_hat_float64_hex": float(estimate["estimate"]).hex(),
                "design_variance_estimate": float(estimate["design_variance_estimate"]),
                "design_standard_error": float(estimate["design_standard_error"]),
                "approximate_95_ci_t_df_21": [
                    float(estimate["approximate_95_ci"][0]),
                    float(estimate["approximate_95_ci"][1]),
                ],
                "degenerate_zero_sample_variance": estimate.get(
                    "degenerate_zero_sample_variance"
                ),
                "sample_extrema_are_global": estimate.get("sample_extrema_are_global"),
            }
        )

    family_size = 4
    alpha = 0.05
    tail_probability = 1 - alpha / (2 * family_size)
    bonferroni_t_critical = float(t.ppf(tail_probability, 21))
    t_975 = audit.issue107.confidence_interval_95(0.0, 1.0)[1]
    contrasts: list[dict[str, Any]] = []
    for dataset in audit.issue101.DATASETS:
        item = analysis[dataset]["contrast_pess_minus_nominal"]["estimates"]["p95"]
        estimate = float(item["estimate"])
        standard_error = float(item["design_standard_error"])
        contrasts.append(
            {
                "dataset": dataset,
                "estimand": "PESS minus Nominal; contrast of the two expected per-order Test P95 estimates",
                "estimate": estimate,
                "estimate_float64_hex": estimate.hex(),
                "design_variance_estimate": float(item["design_variance_estimate"]),
                "design_standard_error": standard_error,
                "original_approximate_95_ci_t_df_21": [
                    float(item["approximate_95_ci"][0]),
                    float(item["approximate_95_ci"][1]),
                ],
                "post_hoc_bonferroni_simultaneous_sensitivity_ci": [
                    estimate - bonferroni_t_critical * standard_error,
                    estimate + bonferroni_t_critical * standard_error,
                ],
            }
        )

    output = {
        "format": "ess-pvldb-local-codex-order-recomputation-v1",
        "status": "COMPLETE",
        "estimand": "For each frozen order, first compute NumPy P95 of the 10,000 Test Q-errors; then take the schedule-weighted mean over orders.",
        "quantile_implementation": "numpy.percentile(values, 95) default linear interpolation (NumPy 2.3.4), via the pinned Issue #101 metric implementation",
        "provenance": {
            "python": platform.python_version(),
            "numpy": np.__version__,
            "scipy": __import__("scipy").__version__,
            "issue125_analyzer_sha256": sha256_file(ROOT / "experiments/oid-order-attribution-issue125/analyze_issue125.py"),
            "oid_sampling_sha256": sha256_file(ROOT / "src/ess_research/arecel/oid_sampling.py"),
            "issue107_runner_sha256": sha256_file(ROOT / "experiments/oid-uniform-priority-issue107/run_issue107.py"),
            "frozen_resource_manifest_sha256": sha256_file(frozen_manifest_path),
            "deterministic_schedule_replay_byte_for_byte_match": True,
            "replayed_schedule_sha256": hashlib.sha256(generated_bytes).hexdigest(),
            "permutation_sample_sha256": integrity["permutation_sample_sha256"],
            "root_seed": root_seed,
            "archive_sha256": integrity["archive_sha256"],
            "manifest_sha256": integrity["manifest_sha256"],
            "raw_row_validation_counts": integrity["source_query_rows_validated"],
            "final_arm_count": integrity["final_configuration_count"],
            "cumulative_explain_calls_recorded": integrity["cumulative_explain_calls"],
            "raw_qerror_recomputation_and_manifest_metric_check": True,
            "official_finite_population_aggregate_exact_match": True,
        },
        "strata": strata,
        "contrasts": contrasts,
        "post_hoc_sensitivity": {
            "family": "four dataset-specific PESS-minus-Nominal contrasts",
            "family_size": family_size,
            "nominal_familywise_alpha": alpha,
            "per_tail_probability": alpha / (2 * family_size),
            "critical_quantile": tail_probability,
            "t_degrees_of_freedom": 21,
            "t_critical": bonferroni_t_critical,
            "original_two_sided_95_percent_t_critical": t_975,
            "interpretation": "Post hoc sensitivity analysis using the same frozen order samples and estimands. Bonferroni does not establish the marginal t-interval coverage assumptions or prove coverage.",
        },
    }

    output_path = Path(__file__).with_name("order-level-recomputation.json")
    output_path.write_text(
        json.dumps(output, sort_keys=True, indent=2, allow_nan=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": output["status"],
                "output": str(output_path),
                "strata": len(strata),
                "order_level_values": sum(len(row["order_level_Y_pi"]) for row in strata),
                "contrasts": len(contrasts),
                "bonferroni_t_critical": bonferroni_t_critical,
                "output_sha256": sha256_file(output_path),
                "official_aggregate_recomputed_from_raw_and_matched": integrity[
                    "official_aggregate_recomputed_from_raw_and_matched"
                ],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
