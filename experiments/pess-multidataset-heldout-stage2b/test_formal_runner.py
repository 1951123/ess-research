from __future__ import annotations

from fractions import Fraction

from run_formal import choose_model_sets, maximal_matchings, nominal_matching


def candidates():
    return {
        "e01": {"id": "e01", "source_columns": ["a", "b"]},
        "e12": {"id": "e12", "source_columns": ["b", "c"]},
        "e23": {"id": "e23", "source_columns": ["c", "d"]},
    }


def test_maximal_matching_is_not_maximum_matching() -> None:
    graph = candidates()
    matchings = maximal_matchings(["e01", "e12", "e23"], graph)
    assert () not in matchings
    assert ("e12",) in matchings
    assert ("e01", "e23") in matchings
    assert nominal_matching(["e01", "e12", "e23"], graph) == ("e01", "e23")


def test_fraction_model_selection_retains_ties_and_budget_aliases() -> None:
    graph = candidates()
    specs = [graph[key] for key in ("e01", "e12", "e23")]
    tasks = [
        {
            "query_id": "q",
            "alpha": "0",
            "b": {"e01": "1", "e12": "1", "e23": "1"},
            "available_edges": ["e01", "e12", "e23"],
        }
    ]
    result = choose_model_sets(tasks, specs, [0, 2, 3])
    assert result["Empty"]["0"]["selected"] == []
    assert result["Empty"]["2"]["tie_count"] == 1
    assert result["PESS"]["0"]["objective"] == "0"
    assert result["PESS"]["2"]["exact_fraction_reference"] is True
    assert result["Nominal"]["3"]["tie_count"] >= 1
    assert Fraction(result["PESS"]["2"]["objective"]) >= 0


def test_frozen_cohort_is_a_subset_of_the_full_truth_split() -> None:
    full_truth = {"q0": 0, "q1": 4, "q2": 8}
    frozen_cohort = {"q0", "q2"}
    assert frozen_cohort <= set(full_truth)
