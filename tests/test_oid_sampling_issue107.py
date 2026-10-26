import itertools
import gzip
import hashlib
import json
import math
import statistics
import copy
import sys
import tempfile
import unittest
from pathlib import Path

from ess_research.arecel.oid_sampling import (
    IncompletePermutationSample,
    PermutationValue,
    build_issue107_schedule,
    confidence_interval_95,
    difference_estimate,
    estimate_population_variance,
    estimate_stratified_mean,
    sample_permutations,
    schedule_arm_index,
    validate_scheduled_arm,
)


REPO = Path(__file__).resolve().parents[1]
FROZEN = (
    REPO
    / "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json"
)
SAMPLE_FILE = (
    REPO / "experiments/oid-uniform-priority-issue107/permutation-sample-v1.json"
)
sys.path.insert(0, str(REPO / "experiments/arecel-test-generalization-issue101"))
sys.path.insert(0, str(REPO / "experiments/oid-order-stress-test-issue105"))
sys.path.insert(0, str(REPO / "experiments/oid-uniform-priority-issue107"))
import run_issue107
from run_issue107 import _reused_rows, analyze_results


def arm(index, value, *, plan_status="COMPLETE", diagnostics_status="complete"):
    return PermutationValue(
        permutation=(f"perm-{index}",),
        value=value,
        plan_status=plan_status,
        diagnostics_status=diagnostics_status,
    )


class OIDPermutationSamplingTests(unittest.TestCase):
    def test_nominal_fixed_orders_are_not_resampled(self):
        ids = ("a", "b", "c", "d", "e")
        fixed = (ids, tuple(reversed(ids)))
        records = sample_permutations(
            ids, random_sample_size=22, seed=123456789, fixed_orders=fixed
        )
        fixed_keys = {tuple(order) for order in fixed}
        sampled_keys = {
            tuple(record["permutation"])
            for record in records
            if record["selection"] == "srswor"
        }
        all_keys = [tuple(record["permutation"]) for record in records]
        self.assertEqual(len(records), 24)
        self.assertEqual(len(set(all_keys)), 24)
        self.assertEqual(sampled_keys & fixed_keys, set())
        self.assertEqual(
            {tuple(record["permutation"]) for record in records[:2]}, fixed_keys
        )

    def test_sample_size_and_population_boundaries(self):
        ids5 = ("a", "b", "c", "d", "e")
        nominal = sample_permutations(
            ids5,
            random_sample_size=22,
            seed=7,
            fixed_orders=(ids5, tuple(reversed(ids5))),
        )
        pess5 = sample_permutations(ids5, random_sample_size=24, seed=8)
        ids3 = ("a", "b", "c")
        pess3 = sample_permutations(
            ids3,
            random_sample_size=math.factorial(3),
            seed=None,
            enumerate_all=True,
        )
        self.assertEqual((len(nominal), len(pess5), len(pess3)), (24, 24, 6))
        self.assertTrue(
            set(tuple(r["permutation"]) for r in nominal).issubset(
                set(itertools.permutations(sorted(ids5)))
            )
        )
        self.assertEqual(
            {tuple(r["permutation"]) for r in pess3},
            set(itertools.permutations(sorted(ids3))),
        )
        with self.assertRaises(ValueError):
            sample_permutations(ids3, random_sample_size=7, seed=9)

    def test_seed_and_frozen_schedule_are_reproducible(self):
        ids = ("e1", "e2", "e3", "e4", "e5")
        args = dict(
            resource_ids=ids,
            random_sample_size=24,
            seed=0x123456789ABCDEF0,
        )
        self.assertEqual(sample_permutations(**args), sample_permutations(**args))
        other = sample_permutations(**{**args, "seed": 0x123456789ABCDEF1})
        self.assertNotEqual(sample_permutations(**args), other)

        expected = build_issue107_schedule(FROZEN)
        actual_bytes = json.dumps(
            expected, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8") + b"\n"
        self.assertEqual(actual_bytes, SAMPLE_FILE.read_bytes())
        self.assertEqual(sum(len(item["permutations"]) for item in expected["schedules"]), 156)
        by_set = {
            (item["dataset"], item["policy"]): item
            for item in expected["schedules"]
        }
        self.assertEqual(len(by_set), 8)
        selection_counts = {
            selection: sum(
                row["selection"] == selection
                for schedule in expected["schedules"]
                for row in schedule["permutations"]
            )
            for selection in ("fixed", "srswor", "enumerated")
        }
        self.assertEqual(selection_counts, {"fixed": 8, "srswor": 136, "enumerated": 12})
        index = schedule_arm_index(expected)
        for dataset in ("forest10", "census13", "dmv11", "power7"):
            nominal = by_set[(dataset, "nominal")]
            self.assertEqual((nominal["fixed_count"], nominal["random_sample_size"], len(nominal["permutations"])), (2, 22, 24))
            self.assertEqual(nominal["permutation_population_size"], 120)
            fixed_order = nominal["permutations"][0]["permutation"]
            self.assertEqual(
                validate_scheduled_arm(
                    index,
                    dataset=dataset,
                    policy="nominal",
                    case_id=nominal["case_id"],
                    resource_ids=nominal["resource_ids"],
                    permutation=fixed_order,
                    selection="fixed",
                )["selection"],
                "fixed",
            )
            with self.assertRaises(IncompletePermutationSample):
                validate_scheduled_arm(
                    index,
                    dataset=dataset,
                    policy="nominal",
                    case_id=nominal["case_id"],
                    resource_ids=nominal["resource_ids"],
                    permutation=fixed_order,
                    selection="srswor",
                )
        for dataset in ("census13", "dmv11"):
            pess5 = by_set[(dataset, "pess")]
            self.assertEqual((pess5["fixed_count"], pess5["random_sample_size"], len(pess5["permutations"])), (0, 24, 24))
            self.assertEqual(pess5["permutation_population_size"], 120)
        for dataset in ("forest10", "power7"):
            pess3 = by_set[(dataset, "pess")]
            self.assertEqual(
                (
                    pess3["fixed_count"],
                    pess3["random_sample_size"],
                    len(pess3["permutations"]),
                ),
                (0, 0, 6),
            )
            self.assertTrue(all(row["selection"] == "enumerated" for row in pess3["permutations"]))

    def test_nominal_estimator_uses_certainty_and_residual_weights(self):
        fixed = [arm("fixed-0", 100.0), arm("fixed-1", 200.0)]
        sampled = [arm(f"s-{i}", 2.0) for i in range(22)]
        estimate = estimate_stratified_mean(
            fixed,
            sampled,
            expected_fixed_count=2,
            expected_sample_size=22,
            residual_population_size=118,
        )
        expected = (2 / 120) * 150 + (118 / 120) * 2
        naive_observed_mean = (300 + 22 * 2) / 24
        self.assertAlmostEqual(estimate.estimate, expected)
        self.assertNotAlmostEqual(estimate.estimate, naive_observed_mean)
        self.assertAlmostEqual(estimate.variance_estimate, 0.0)
        self.assertTrue(estimate.degenerate_interval)

    def test_delta_variance_and_interval_use_independent_designs(self):
        nominal = estimate_stratified_mean(
            [arm("n-fixed-0", 10), arm("n-fixed-1", 12)],
            [arm(f"n-s-{i}", float(i)) for i in range(22)],
            expected_fixed_count=2,
            expected_sample_size=22,
            residual_population_size=118,
        )
        pess = estimate_stratified_mean(
            [],
            [arm(f"p-s-{i}", float(2 * i)) for i in range(24)],
            expected_fixed_count=0,
            expected_sample_size=24,
            residual_population_size=120,
        )
        delta = difference_estimate(pess, nominal)
        self.assertAlmostEqual(delta.estimate, pess.estimate - nominal.estimate)
        self.assertAlmostEqual(
            delta.variance_estimate,
            pess.variance_estimate + nominal.variance_estimate,
        )
        low, high = confidence_interval_95(delta.estimate, delta.standard_error)
        self.assertAlmostEqual(
            high - delta.estimate,
            2.079613844727662 * delta.standard_error,
        )
        self.assertAlmostEqual(delta.estimate - low, high - delta.estimate)

    def test_finite_population_variance_estimator_matches_enumerated_design(self):
        fixed = [arm("certainty", 11.0)]
        residual_population = (1.0, 2.0, 5.0, 9.0, 16.0)
        n = 2
        estimates = []
        variance_estimates = []
        sd_variance_estimates = []
        for sample_index, values in enumerate(itertools.combinations(residual_population, n)):
            sampled = [arm(f"s{sample_index}-{i}", value) for i, value in enumerate(values)]
            result = estimate_stratified_mean(
                fixed,
                sampled,
                expected_fixed_count=1,
                expected_sample_size=n,
                residual_population_size=len(residual_population),
            )
            pop_var = estimate_population_variance(
                fixed,
                sampled,
                expected_fixed_count=1,
                expected_sample_size=n,
                residual_population_size=len(residual_population),
            )
            estimates.append(result.estimate)
            variance_estimates.append(result.variance_estimate)
            sd_variance_estimates.append(pop_var.raw_variance_estimate)

        exact_design_variance = statistics.pvariance(estimates)
        self.assertAlmostEqual(
            math.fsum(variance_estimates) / len(variance_estimates),
            exact_design_variance,
        )
        full_population = (11.0, *residual_population)
        exact_population_variance = statistics.pvariance(full_population)
        self.assertAlmostEqual(
            math.fsum(sd_variance_estimates) / len(sd_variance_estimates),
            exact_population_variance,
        )

    def test_full_enumeration_has_zero_sampling_variance_but_nonzero_spread(self):
        all_arms = [arm(i, value) for i, value in enumerate((1.0, 2.0, 4.0, 8.0, 16.0, 32.0))]
        estimate = estimate_stratified_mean(
            [],
            all_arms,
            expected_fixed_count=0,
            expected_sample_size=6,
            residual_population_size=6,
        )
        variance = estimate_population_variance(
            [],
            all_arms,
            expected_fixed_count=0,
            expected_sample_size=6,
            residual_population_size=6,
        )
        self.assertEqual(estimate.variance_estimate, 0.0)
        self.assertFalse(estimate.degenerate_interval)
        self.assertGreater(variance.standard_deviation_estimate, 0.0)
        self.assertAlmostEqual(estimate.estimate, statistics.mean((1, 2, 4, 8, 16, 32)))

    def test_incomplete_or_invalid_arm_cannot_enter_estimator(self):
        fixed = [arm("fixed-0", 3), arm("fixed-1", 5)]
        incomplete = [arm(f"s-{i}", 4) for i in range(21)]
        with self.assertRaises(IncompletePermutationSample):
            estimate_stratified_mean(
                fixed,
                incomplete,
                expected_fixed_count=2,
                expected_sample_size=22,
                residual_population_size=118,
            )
        invalid = [arm(f"s-{i}", 4) for i in range(22)]
        invalid[-1] = arm("s-21", 4, diagnostics_status="missing")
        with self.assertRaises(IncompletePermutationSample):
            estimate_stratified_mean(
                fixed,
                invalid,
                expected_fixed_count=2,
                expected_sample_size=22,
                residual_population_size=118,
            )

    def test_empty_diagnostics_are_valid_complete_query_outcomes(self):
        estimate = estimate_stratified_mean(
            [],
            [arm(i, float(i + 1), diagnostics_status="empty") for i in range(24)],
            expected_fixed_count=0,
            expected_sample_size=24,
            residual_population_size=120,
        )
        self.assertTrue(math.isfinite(estimate.estimate))

    def test_runner_aggregates_frozen_sample_and_exact_contrast(self):
        schedule = build_issue107_schedule(FROZEN)
        arms = []
        for stratum in schedule["schedules"]:
            for index, row in enumerate(stratum["permutations"]):
                if stratum["policy"] == "nominal" and row["selection"] == "fixed":
                    value = 100.0 + 100.0 * index
                else:
                    value = 1.0 + index
                arms.append(
                    {
                        "dataset": stratum["dataset"],
                        "policy": stratum["policy"],
                        "case_id": stratum["case_id"],
                        "permutation": row["permutation"],
                        "selection": row["selection"],
                        "draw_index": row["draw_index"],
                        "inclusion_probability": row["inclusion_probability"],
                        "permutation_sample_sha256": stratum["sample_sha256"],
                        "metrics": {
                            "statistical_status": "COMPLETE",
                            "qerror": {
                                "mean": value * 0.7,
                                "p50": value * 0.5,
                                "p95": value,
                                "p99": value * 1.2,
                            },
                        },
                    }
                )
        result = analyze_results(schedule, arms)
        self.assertEqual(set(result), {"forest10", "census13", "dmv11", "power7"})
        for dataset, record in result.items():
            nominal = record["policies"]["nominal"]["expectation"]
            pess = record["policies"]["pess"]["expectation"]
            self.assertEqual(nominal["status"], "COMPLETE")
            self.assertEqual(pess["status"], "COMPLETE")
            self.assertEqual(record["contrast_pess_minus_nominal"]["status"], "COMPLETE")
            delta = record["contrast_pess_minus_nominal"]["estimates"]["p95"]
            self.assertAlmostEqual(
                delta["estimate"],
                pess["estimates"]["p95"]["estimate"] - nominal["estimates"]["p95"]["estimate"],
            )
            self.assertAlmostEqual(
                delta["design_variance_estimate"],
                pess["estimates"]["p95"]["design_variance_estimate"]
                + nominal["estimates"]["p95"]["design_variance_estimate"],
            )
        for dataset in ("forest10", "power7"):
            pess3 = result[dataset]["policies"]["pess"]["expectation"]
            self.assertEqual(pess3["estimates"]["p95"]["design_standard_error"], 0.0)
            self.assertTrue(pess3["estimates"]["p95"]["sample_extrema_are_global"])

        missing = analyze_results(schedule, arms[:-1])
        self.assertEqual(missing["power7"]["policies"]["pess"]["expectation"]["status"], "INCOMPLETE")
        self.assertEqual(missing["power7"]["contrast_pess_minus_nominal"]["status"], "INCOMPLETE")
        duplicate = analyze_results(schedule, [*arms, arms[-1]])
        self.assertEqual(duplicate["power7"]["policies"]["pess"]["expectation"]["status"], "INCOMPLETE")
        wrong_stratum = [dict(row) for row in arms]
        fixed_index = next(i for i, row in enumerate(wrong_stratum) if row["selection"] == "fixed")
        wrong_stratum[fixed_index]["selection"] = "srswor"
        rejected = analyze_results(schedule, wrong_stratum)
        self.assertEqual(rejected["forest10"]["policies"]["nominal"]["expectation"]["status"], "INCOMPLETE")

    def test_reused_member_recomputes_only_complete_matching_test_rows(self):
        rows = []
        queries = []
        truths = []
        selected = ["a", "b"]
        for index in range(10_000):
            truth = index % 4
            plan_rows = (index // 4) % 5
            qerror, rounded = __import__(
                "run_issue101"
            ).qerror_for_plan_rows(plan_rows, truth)
            query_id = f"arecel:toy:test:{index:06d}"
            queries.append({"query_id": query_id})
            truths.append(truth)
            rows.append(
                {
                    "dataset": "toy",
                    "order": "canonical",
                    "configuration_id": "toy-canonical",
                    "selected_ids": selected,
                    "query_id": query_id,
                    "source_index": index,
                    "true_cardinality": truth,
                    "estimate_plan_rows": plan_rows,
                    "estimate_rounded_r1": rounded,
                    "qerror": qerror,
                    "status": "VALID",
                    "diagnostics_status": "empty" if index % 2 else "complete",
                    "diagnostics_event_count": 0,
                    "mcv_events": [],
                    "mcv_selection_ids": [],
                    "mcv_estimate_ids": [],
                }
            )
        body = b"".join(
            (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
            for row in rows
        )
        member = gzip.compress(body, mtime=0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "raw.gz"
            path.write_bytes(member)
            old_arm = {
                "raw_member_offset": 0,
                "raw_member_bytes": len(member),
                "raw_member_sha256": hashlib.sha256(member).hexdigest(),
            }
            reused, metrics = _reused_rows(
                path,
                old_arm,
                dataset="toy",
                old_order="canonical",
                permutation=selected,
                queries=queries,
                truths=truths,
            )
            self.assertEqual(len(reused), 10_000)
            self.assertEqual(metrics["valid_count"], 10_000)
            self.assertEqual(metrics["status"], "COMPLETE")
            rows[-1]["diagnostics_status"] = "missing"
            broken = gzip.compress(
                b"".join((json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
                         for row in rows),
                mtime=0,
            )
            path.write_bytes(broken)
            old_arm.update(raw_member_bytes=len(broken), raw_member_sha256=hashlib.sha256(broken).hexdigest())
            with self.assertRaises(ValueError):
                _reused_rows(
                    path,
                    old_arm,
                    dataset="toy",
                    old_order="canonical",
                    permutation=selected,
                    queries=queries,
                    truths=truths,
                )

    def test_issue105_catalog_audit_accepts_frozen_three_object_set(self):
        selected = ["e01_02", "e02_03", "e03_04"]
        candidates = {
            candidate_id: {
                "statistic_name": f"stat_{candidate_id}",
                "catalog_columns": [f"c{index}", f"c{index + 1}"],
            }
            for index, candidate_id in enumerate(selected, start=1)
        }
        rows = []
        helper_ledger = []
        for index, candidate_id in enumerate(selected, start=1):
            row = {
                "statistic_name": candidates[candidate_id]["statistic_name"],
                "oid": 16_300 + index,
                "attnames": candidates[candidate_id]["catalog_columns"],
                "kinds": ["m"],
                "statistics_target": 300,
                "mcv_payload_present": True,
                "mcv_item_count": 4,
                "stxkind": "{m}",
                "mcv_content_sha256": f"sha-{candidate_id}",
                "stxkeys": str(index),
            }
            rows.append(row)
            helper_ledger.append({
                key: row[key]
                for key in (
                    "statistic_name", "oid", "statistics_target",
                    "mcv_payload_present", "mcv_item_count", "stxkeys",
                )
            })
        oid_to_id = run_issue107.issue105.validate_catalog_rows(
            "forest10", "pess-three-object", selected, candidates, rows, helper_ledger
        )
        self.assertEqual(oid_to_id, {16_301: selected[0], 16_302: selected[1], 16_303: selected[2]})

    def test_continuation_scope_contains_only_unexecuted_frozen_census_arms(self):
        schedule = build_issue107_schedule(FROZEN)
        index = schedule_arm_index(schedule)
        prior = {"attempted_explain_calls": 1_440_000, "datasets": {}}
        for stratum in schedule["schedules"]:
            dataset = stratum["dataset"]
            prior["datasets"].setdefault(dataset, {"arms": []})
            for row in stratum["permutations"]:
                is_target = (
                    dataset in {"forest10", "power7"}
                    and stratum["policy"] == "pess"
                    and row["selection"] == "enumerated"
                )
                prior["datasets"][dataset]["arms"].append({
                    "dataset": dataset,
                    "policy": stratum["policy"],
                    "case_id": stratum["case_id"],
                    "resource_ids": list(stratum["resource_ids"]),
                    "permutation": row["permutation"],
                    "selection": row["selection"],
                    "draw_index": row["draw_index"],
                    "inclusion_probability": row["inclusion_probability"],
                    "status": "CONFIGURATION_INVALID" if is_target else "COMPLETE",
                    "attempted_explain_calls": 0 if is_target else 10_000,
                })
        targets = run_issue107.continuation_targets(prior, schedule, index)
        self.assertEqual(len(targets), 12)
        self.assertTrue(all(ds in {"forest10", "power7"} and policy == "pess" for ds, policy, _ in targets))

        extra_failure = copy.deepcopy(prior)
        extra_failure["datasets"]["forest10"]["arms"][0]["status"] = "CONFIGURATION_INVALID"
        with self.assertRaises(RuntimeError):
            run_issue107.continuation_targets(extra_failure, schedule, index)

        attempted = copy.deepcopy(prior)
        first_target = next(iter(targets))
        row = next(
            arm for arm in attempted["datasets"][first_target[0]]["arms"]
            if tuple(arm["permutation"]) == first_target[2]
        )
        row["attempted_explain_calls"] = 10_000
        with self.assertRaises(RuntimeError):
            run_issue107.continuation_targets(attempted, schedule, index)

if __name__ == "__main__":
    unittest.main()
