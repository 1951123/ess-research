from fractions import Fraction

from analyze_issue95 import analyze_instance, task_result
from pess_ess.model import instance_from_dict
from pess_ess.reference import ReferenceWork


def _tiny_instance():
    return instance_from_dict(
        {
            "budget": "4",
            "candidates": [
                {
                    "id": "a",
                    "table": "t",
                    "endpoints": ["u", "v"],
                    "maintenance_cost": "1",
                },
                {
                    "id": "b",
                    "table": "t",
                    "endpoints": ["v", "w"],
                    "maintenance_cost": "1",
                },
                {
                    "id": "c",
                    "table": "t",
                    "endpoints": ["x", "y"],
                    "maintenance_cost": "1",
                },
                {
                    "id": "d",
                    "table": "t",
                    "endpoints": ["z", "w2"],
                    "maintenance_cost": "1",
                },
            ],
            "tasks": [
                {
                    "id": "risk-task",
                    "table": "t",
                    "weight": "1",
                    "alpha": "0",
                    "eligible_candidates": ["a", "b"],
                    "corrections": {"a": "1", "b": "3"},
                },
                {
                    "id": "risk-task-z",
                    "table": "t",
                    "weight": "1",
                    "alpha": "0",
                    "eligible_candidates": ["a", "b"],
                    "corrections": {"a": "1", "b": "3"},
                },
                {
                    "id": "tie-task",
                    "table": "t",
                    "weight": "1",
                    "alpha": "0",
                    "eligible_candidates": ["a", "b"],
                    "corrections": {"a": "1", "b": "1"},
                },
                {
                    "id": "no-conflict-task",
                    "table": "t",
                    "weight": "1",
                    "alpha": "0",
                    "eligible_candidates": ["c", "d"],
                    "corrections": {"c": "1", "d": "-1"},
                },
            ],
        }
    )


def test_attribution_separates_conflict_from_positive_risk_and_concentrates():
    instance = _tiny_instance()
    summary = analyze_instance(
        instance,
        frozenset(instance.candidate_ids),
        ("a", "b", "c", "d"),
        nominal_total=Fraction(3),
        pess_total=Fraction(7),
    )

    assert summary["summed_task_risk_fraction"] == "4"
    assert summary["positive_risk_task_count"] == 2
    assert summary["tasks_with_applicable_endpoint_conflict_count"] == 3
    assert summary["positive_risk_without_conflict_count"] == 0
    assert summary["zero_risk_with_conflict_count"] == 1
    assert summary["zero_risk_without_conflict_count"] == 1
    assert summary["top_10_positive_risk"]["risk_sum_fraction"] == "4"
    witness = summary["largest_risk_witnesses"][0]
    assert [item["task_id"] for item in summary["largest_risk_witnesses"]] == [
        "risk-task",
        "risk-task-z",
    ]
    assert witness["task_id"] == "risk-task"
    assert witness["nominal_matching_ids"] == ["a"]
    assert witness["pess_worst_matching_ids"] == ["b"]
    assert witness["nominal_loss_fraction"] == "1"
    assert witness["pess_loss_fraction"] == "3"
    assert witness["risk_fraction"] == "2"


def test_equal_worst_losses_choose_lexicographically_smallest_matching():
    instance = _tiny_instance()
    task = instance.task_map["tie-task"]
    attributed = task_result(
        instance,
        task,
        frozenset(("a", "b")),
        ("a", "b", "c", "d"),
        ReferenceWork(),
    )

    assert attributed.nominal_matching == frozenset(("a",))
    assert attributed.pess_matching == frozenset(("a",))
    assert attributed.risk == 0
    assert attributed.conflicts == (("a", "b"),)
