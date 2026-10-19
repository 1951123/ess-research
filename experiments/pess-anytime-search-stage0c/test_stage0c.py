from __future__ import annotations

from pathlib import Path

from reference import exhaustive, load, verify_selected
from search import run_method

ROOT = Path(__file__).parent


def test_v2_fixed_greedy_trap_is_reproduced() -> None:
    instance = load(ROOT / "instances" / "tiny_greedy_trap_04.json")
    truth = exhaustive(instance)
    greedy = run_method(instance, "greedy", 10.0)
    assert truth["objective"] == 0
    assert truth["optimal_sets"] == (frozenset({"g4", "g5"}),)
    assert greedy["selected"] == []
    assert greedy["objective"] == "4"
    verify_selected(instance, greedy["selected"], greedy["objective"])


def test_all_v2_methods_return_independently_evaluable_feasible_incumbents() -> None:
    methods = ("empty", "singleton", "greedy", "basic", "cache_only", "pess_order", "pess_order_cache")
    for path in sorted((ROOT / "instances").glob("*.json")):
        instance = load(path)
        for method in methods:
            result = run_method(instance, method, 10.0)
            checked = verify_selected(instance, result["selected"], result["objective"])
            assert checked["objective"] == result["objective"]
            assert all(item["evaluated_incumbent"] for item in result["trace"])
