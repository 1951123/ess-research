from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path


HERE = Path(__file__).parent


def load(name: str, filename: str):
    spec = importlib.util.spec_from_file_location(name, HERE / filename)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot import {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


runner = load("issue9_runner", "run_fixed_target_cpu.py")
analyzer = load("issue9_analyzer", "analyze_fixed_target_cpu.py")


def test_schedule_is_exactly_640_and_randomized():
    schedule = runner.build_schedule(seed=12345, repetitions=20)
    assert len(schedule) == 640
    assert len({(c.condition_id, r) for c, r, _ in schedule}) == 640
    assert {c.target for c, _, _ in schedule} == {100, 300}
    assert {c.regime for c, _, _ in schedule} == {"weakassoc", "correlated"}
    assert all(c.ordinary_column_target == c.target for c, _, _ in schedule)
    assert all(c.requested_sample_rows == 300 * c.target for c, _, _ in schedule)
    first_block = [c.condition_id for c, r, _ in schedule if r == 1]
    second_block = [c.condition_id for c, r, _ in schedule if r == 2]
    assert first_block != second_block


def synthetic_payload() -> dict:
    conditions = runner.condition_list()
    observations = []
    metadata = []
    for condition_index, condition in enumerate(conditions):
        table_oid = 20000 + condition_index
        for repetition in range(1, 21):
            base = 1000 + condition_index + repetition
            cpu = base + 25 * len(condition.subset)
            observations.append(
                {
                    **asdict(condition),
                    "condition_id": condition.condition_id,
                    "repetition": repetition,
                    "order_index": condition_index * 20 + repetition,
                    "psql_elapsed_ms": float(cpu) / 10,
                    "trace_stream": "stderr",
                    "warmup_cpu_trace": {
                        "relid": table_oid,
                        "stats_count": len(condition.subset),
                        "built_count": len(condition.subset),
                        "user_us": cpu // 2,
                        "system_us": cpu - cpu // 2,
                        "cpu_us": cpu,
                    },
                    "cpu_trace": {
                        "relid": table_oid,
                        "stats_count": len(condition.subset),
                        "built_count": len(condition.subset),
                        "user_us": cpu // 2,
                        "system_us": cpu - cpu // 2,
                        "cpu_us": cpu,
                    },
                }
            )
            metadata.append(
                {
                    "kind": "ordinary",
                    "condition_id": condition.condition_id,
                    "repetition": repetition,
                    "table_oid": table_oid,
                    "targets": {attr: condition.target for attr in runner.ATTRIBUTES},
                }
            )
            if condition.subset:
                for edge in condition.subset:
                    metadata.append(
                        {
                            "kind": "extended",
                            "condition_id": condition.condition_id,
                            "repetition": repetition,
                            "name": runner.object_name(condition.table, edge),
                            "oid": 50000 + condition_index,
                            "statistics_target": condition.target,
                            "mcv_payload_built": True,
                        }
                    )
            else:
                metadata.append(
                    {
                        "kind": "extended",
                        "condition_id": condition.condition_id,
                        "repetition": repetition,
                        "name": None,
                        "oid": None,
                        "statistics_target": None,
                        "mcv_payload_built": None,
                    }
                )
    return {
        "experiment": "issue-9-pg16-fixed-target-extstats-cpu",
        "timed_observation_count": 640,
        "condition_count": 32,
        "repetitions": 20,
        "seed": 12345,
        "observations": observations,
        "metadata_observations": metadata,
    }


def test_synthetic_matrix_replays_through_analysis(tmp_path):
    payload = synthetic_payload()
    raw = tmp_path / "raw.json"
    raw.write_text(json.dumps(payload), encoding="utf-8")
    loaded = analyzer.load_and_validate(raw)
    analyzer.grouped_values(loaded)
    result = analyzer.make_analysis(loaded, raw)
    assert len(result["comparisons"]) == 16
    assert all(item["bootstrap_replicates"] == 5000 for item in result["comparisons"])
