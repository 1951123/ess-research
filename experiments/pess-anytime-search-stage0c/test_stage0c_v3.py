from __future__ import annotations

import pytest
from protocol import input_paths, write_json_once
from reference import load
from search_timed import run_method


def test_manifest_is_explicit_and_fail_closed() -> None:
    from pathlib import Path

    root = Path(__file__).parent
    assert len(input_paths(root, "stage0c-v1")) == 5
    assert len(input_paths(root, "stage0c-v1", gate_a=True)) == 3
    assert len(input_paths(root, "stage0c-v2")) == 6
    assert len(input_paths(root, "stage0c-v2", gate_a=True)) == 4
    assert len(input_paths(root, "stage0c-v3")) == 6


def test_output_policy_refuses_overwrite(tmp_path) -> None:
    target = tmp_path / "evidence.json"
    write_json_once(target, {"version": 1})
    with pytest.raises(FileExistsError):
        write_json_once(target, {"version": 2})


def test_slow_evaluator_has_causal_checkpoints_and_positive_wall_time() -> None:
    from pathlib import Path

    instance = load(Path(__file__).parent / "instances" / "tiny_greedy_trap_04.json")
    result = run_method(
        instance,
        "singleton",
        0.15,
        checkpoints=(0.05, 0.1),
        objective_delay=0.06,
    )
    history = result["incumbent_history"]
    assert result["wall_seconds"] > 0
    assert max(item["completed_elapsed_seconds"] for item in history) > 0.05
    for point in result["trace"]:
        if point["available"]:
            assert point["completion_elapsed_seconds"] <= point["checkpoint_seconds"]
            assert any(
                item["completed_elapsed_seconds"] == point["completion_elapsed_seconds"]
                for item in history
            )
        else:
            assert point["selected"] is None
            assert point["objective"] is None

