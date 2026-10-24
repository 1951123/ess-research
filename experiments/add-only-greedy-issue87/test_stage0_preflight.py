from __future__ import annotations

from copy import deepcopy
import unittest
from fractions import Fraction
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from time import monotonic
from unittest.mock import patch
from pess_ess.api import result_to_dict, solve
from pess_ess.model import instance_from_dict
from pess_ess.reference import reference_nominal_objective, reference_objective

HERE = Path(__file__).resolve().parent
ADAPTER_SPEC = spec_from_file_location(
    "ess_research_issue87_adapter", HERE / "adapter.py"
)
if ADAPTER_SPEC is None or ADAPTER_SPEC.loader is None:
    raise ImportError("could not load Issue #87 adapter")
adapter = module_from_spec(ADAPTER_SPEC)
ADAPTER_SPEC.loader.exec_module(adapter)


def base_request(
    *,
    budget: int,
    alpha: str,
    candidates: list[dict[str, str | list[str]]],
    eligible: list[str],
    corrections: dict[str, str],
    priority: list[str] | None = None,
) -> dict:
    request = {
        "schema_version": "1",
        "objective": "pess",
        "backend": "master_oracle",
        "input_provenance": {"model_version": "synthetic-issue87-v1"},
        "instance": {
            "budget": str(budget),
            "candidates": candidates,
            "tasks": [
                {
                    "id": "q1",
                    "table": "t",
                    "weight": "1",
                    "alpha": alpha,
                    "eligible_candidates": eligible,
                    "corrections": corrections,
                }
            ],
        },
    }
    if priority is not None:
        request["_nominal_priority_order"] = priority
    return request


def unit_candidate(candidate_id: str, a: str, b: str) -> dict:
    return {
        "id": candidate_id,
        "table": "t",
        "endpoints": [a, b],
        "maintenance_cost": "1",
    }


def execute(payload: dict, *, max_evaluations: int | None = None) -> dict:
    instance = instance_from_dict(payload["instance"])
    limits = payload["limits"]
    result = solve(
        instance,
        objective=payload["objective"],
        backend=payload["backend"],
        priority_order=payload.get("priority_order"),
        total_time_limit=limits["total_time_seconds"],
        max_evaluations=(
            max_evaluations
            if max_evaluations is not None
            else limits["max_evaluations"]
        ),
        max_inner_matching_subsets=limits.get("max_inner_matching_subsets"),
    )
    return result_to_dict(
        result,
        backend=payload["backend"],
        objective=payload["objective"],
        priority_order=payload.get("priority_order"),
    )


class Issue87Stage0Preflight(unittest.TestCase):
    def test_frozen_backend_and_protocol_pins_are_explicit(self) -> None:
        protocol = adapter._protocol()
        self.assertFalse(protocol["execution_authorized"])
        self.assertEqual(
            protocol["immutable_software"]["advisor_source_commit"],
            "5d61f75fede37d34027b437c646000a3d78d00c6",
        )
        self.assertEqual(
            protocol["immutable_software"]["advisor_backend"], "add_only_greedy"
        )
        self.assertEqual(protocol["scope"]["budget_sequence"], [0, 2, 3, 4, 5])

    def test_caps_match_the_frozen_candidate_and_task_sizes(self) -> None:
        protocol = adapter._protocol()
        for dataset, candidate_count in (("forest10", 45), ("census13", 78)):
            for budget, expected in protocol["resource_limits"][
                "per_dataset_budget_caps"
            ][dataset].items():
                actual = adapter.resource_caps(
                    candidate_count=candidate_count,
                    task_count=10_000,
                    budget=int(budget),
                )
                self.assertEqual(actual["max_evaluations"], expected["max_evaluations"])
                self.assertEqual(
                    actual["max_inner_matching_subsets"],
                    expected["max_inner_matching_subsets_pess"],
                )
                self.assertEqual(
                    actual["candidate_attempts_upper_bound"],
                    expected["candidate_attempts_upper_bound"],
                )

    def test_adapting_both_objectives_does_not_mutate_base_request(self) -> None:
        request = base_request(
            budget=2,
            alpha="2",
            candidates=[unit_candidate("a-resource", "a", "b")],
            eligible=["a-resource"],
            corrections={"a-resource": "-1"},
            priority=["a-resource"],
        )
        original = deepcopy(request)

        adapter.adapt_request(request, "nominal")
        adapter.adapt_request(request, "pess")

        self.assertEqual(request, original)

    def test_ties_eligibility_exact_values_and_cross_evaluation(self) -> None:
        # Input order intentionally differs from the backend's candidate-ID tie-break.
        request = base_request(
            budget=2,
            alpha="3",
            candidates=[
                unit_candidate("z-resource", "e", "f"),
                unit_candidate("unused-resource", "g", "h"),
                unit_candidate("a-resource", "a", "b"),
            ],
            eligible=["z-resource", "a-resource"],
            corrections={"z-resource": "-1", "a-resource": "-1"},
            priority=["z-resource", "a-resource", "unused-resource"],
        )
        pess_payload = adapter.adapt_request(request, "pess")
        nominal_payload = adapter.adapt_request(request, "nominal")
        self.assertEqual(pess_payload["backend"], "add_only_greedy")
        self.assertEqual(nominal_payload["backend"], "add_only_greedy")
        self.assertNotIn("priority_order", pess_payload)
        self.assertEqual(
            nominal_payload["priority_order"],
            ["z-resource", "a-resource", "unused-resource"],
        )

        pess = execute(pess_payload)
        nominal = execute(nominal_payload)
        self.assertEqual(pess["status"], "heuristic_completed")
        self.assertEqual(nominal["status"], "heuristic_completed")
        self.assertEqual(pess["greedy"]["addition_order"], ["a-resource", "z-resource"])
        self.assertEqual(
            nominal["greedy"]["addition_order"], ["a-resource", "z-resource"]
        )
        self.assertEqual(pess["incumbent"]["selected"], ["a-resource", "z-resource"])
        self.assertEqual(nominal["incumbent"]["selected"], ["a-resource", "z-resource"])
        self.assertEqual(Fraction(pess["incumbent"]["objective_value"]), Fraction(1))
        self.assertEqual(Fraction(nominal["incumbent"]["objective_value"]), Fraction(1))
        self.assertFalse(pess["optimality"]["outer_global_optimum_fraction_certified"])
        self.assertFalse(
            nominal["optimality"]["outer_global_optimum_fraction_certified"]
        )

        instance = instance_from_dict(request["instance"])
        nominal_set = frozenset(nominal["incumbent"]["selected"])
        pess_set = frozenset(pess["incumbent"]["selected"])
        self.assertEqual(
            reference_nominal_objective(
                instance, nominal_set, tuple(nominal_payload["priority_order"])
            )[0],
            Fraction(1),
        )
        self.assertEqual(
            reference_nominal_objective(
                instance, pess_set, tuple(nominal_payload["priority_order"])
            )[0],
            Fraction(1),
        )
        self.assertEqual(reference_objective(instance, nominal_set)[0], Fraction(1))
        self.assertEqual(reference_objective(instance, pess_set)[0], Fraction(1))
        contrast = adapter.reevaluate_greedy_contrast(
            request, ["a-resource"], ["a-resource", "z-resource"]
        )
        self.assertEqual(contrast["nominal_objective_on_nominal_set_fraction"], "2")
        self.assertEqual(contrast["pess_objective_on_nominal_set_fraction"], "2")
        self.assertEqual(contrast["nominal_objective_on_pess_set_fraction"], "1")
        self.assertEqual(contrast["pess_objective_on_pess_set_fraction"], "1")
        self.assertEqual(
            contrast["cross_evaluation_work"]["fixed_set_evaluation_calls"], 4
        )

        with self.assertRaisesRegex(ValueError, "outside the candidate universe"):
            adapter.reevaluate_greedy_contrast(
                request, ["unknown-resource"], ["a-resource"]
            )

        reversed_request = dict(request)
        reversed_request["instance"] = dict(request["instance"])
        reversed_request["instance"]["candidates"] = list(
            reversed(request["instance"]["candidates"])
        )
        reversed_pess = execute(adapter.adapt_request(reversed_request, "pess"))
        self.assertEqual(
            reversed_pess["greedy"]["addition_order"], ["a-resource", "z-resource"]
        )

    def test_budget_zero_and_zero_cost_candidate(self) -> None:
        b0 = base_request(
            budget=0,
            alpha="5",
            candidates=[unit_candidate("a-resource", "a", "b")],
            eligible=["a-resource"],
            corrections={"a-resource": "-4"},
        )
        b0_result = execute(adapter.adapt_request(b0, "pess"))
        self.assertEqual(b0_result["status"], "heuristic_completed")
        self.assertEqual(b0_result["incumbent"]["selected"], [])
        self.assertEqual(b0_result["greedy"]["fixed_set_evaluation_calls"], 1)

        zero_cost = base_request(
            budget=0,
            alpha="1",
            candidates=[
                {
                    "id": "zero-resource",
                    "table": "t",
                    "endpoints": ["a", "b"],
                    "maintenance_cost": "0",
                },
                unit_candidate("unit-resource", "c", "d"),
            ],
            eligible=["zero-resource", "unit-resource"],
            corrections={"zero-resource": "-1", "unit-resource": "-1"},
        )
        zero_payload = {
            key: value for key, value in zero_cost.items() if not key.startswith("_")
        }
        zero_payload.update(
            {
                "objective": "pess",
                "backend": "add_only_greedy",
                "limits": {
                    "total_time_seconds": 10,
                    "max_evaluations": 3,
                    "max_inner_matching_subsets": 10,
                },
            }
        )
        zero_result = execute(zero_payload)
        self.assertEqual(zero_result["incumbent"]["selected"], ["zero-resource"])
        self.assertEqual(zero_result["incumbent"]["maintenance_cost"], "0")
        self.assertEqual(zero_result["termination_reason"], "no_feasible_candidate")

    def test_plateau_stops_and_interrupted_round_is_incomplete(self) -> None:
        plateau = base_request(
            budget=2,
            alpha="1",
            candidates=[
                unit_candidate("z-resource", "e", "f"),
                unit_candidate("a-resource", "a", "b"),
            ],
            eligible=["z-resource", "a-resource"],
            corrections={"z-resource": "-2", "a-resource": "-1"},
        )
        plateau_result = execute(adapter.adapt_request(plateau, "pess"))
        self.assertEqual(plateau_result["status"], "heuristic_completed")
        self.assertEqual(plateau_result["incumbent"]["selected"], ["a-resource"])
        self.assertEqual(plateau_result["termination_reason"], "no_strict_improvement")

        interrupted = base_request(
            budget=2,
            alpha="1",
            candidates=[unit_candidate("a-resource", "a", "b")],
            eligible=["a-resource"],
            corrections={"a-resource": "-1"},
        )
        interrupted_payload = adapter.adapt_request(interrupted, "pess")
        incomplete = execute(interrupted_payload, max_evaluations=1)
        self.assertEqual(incomplete["status"], "heuristic_incomplete")
        self.assertEqual(incomplete["termination_reason"], "evaluation_incomplete")
        self.assertEqual(incomplete["incumbent"]["selected"], [])
        self.assertFalse(
            incomplete["optimality"]["outer_global_optimum_fraction_certified"]
        )

    def test_cross_evaluation_that_finishes_after_deadline_is_incomplete(self) -> None:
        request = base_request(
            budget=1,
            alpha="2",
            candidates=[unit_candidate("a-resource", "a", "b")],
            eligible=["a-resource"],
            corrections={"a-resource": "-1"},
            priority=["a-resource"],
        )
        started = monotonic()
        time_limit = adapter._protocol()["resource_limits"][
            "fixed_set_cross_evaluation"
        ]["total_time_seconds"]
        with patch.object(
            adapter,
            "monotonic",
            side_effect=[started, started + time_limit + 1],
        ):
            with self.assertRaises(adapter.CrossEvaluationIncomplete) as raised:
                adapter.reevaluate_greedy_contrast(
                    request, ["a-resource"], ["a-resource"]
                )

        self.assertEqual(str(raised.exception), "time_limit_seconds")
        self.assertEqual(raised.exception.completed_fixed_set_evaluations, 1)


if __name__ == "__main__":
    unittest.main()
