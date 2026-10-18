from __future__ import annotations

import copy
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path

import pytest


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
V1_RAW = HERE / "runs" / "20261018-issue9-v1" / "measurement" / "raw-observations.json"


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
                        "stream": "stderr",
                        "relid": table_oid,
                        "stats_count": len(condition.subset),
                        "built_count": len(condition.subset),
                        "user_us": cpu // 2,
                        "system_us": cpu - cpu // 2,
                        "cpu_us": cpu,
                    },
                    "cpu_trace": {
                        "stream": "stderr",
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
                for edge_index, edge in enumerate(condition.subset):
                    metadata.append(
                        {
                            "kind": "extended",
                            "condition_id": condition.condition_id,
                            "repetition": repetition,
                            "name": runner.object_name(condition.table, edge),
                            "oid": 50000 + condition_index * 1000 + repetition * 10 + edge_index,
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


def test_committed_v1_matrix_passes_strict_validation():
    assert runner.sha256_file(V1_RAW) == (
        "1aaf7d750c09d99958fc60f33528f014a9451a83007d66dc1c3ffaa2ed8e24b5"
    )
    payload = json.loads(V1_RAW.read_text(encoding="utf-8"))
    runner.validate(
        payload["observations"],
        payload["metadata_observations"],
        payload["repetitions"],
    )


def test_duplicate_object_metadata_cell_is_rejected():
    payload = synthetic_payload()
    row = next(
        row for row in payload["metadata_observations"]
        if row["kind"] == "extended" and row["name"] is not None
    )
    payload["metadata_observations"].append(copy.deepcopy(row))
    with pytest.raises(RuntimeError, match="object coverage"):
        runner.validate(
            payload["observations"],
            payload["metadata_observations"],
            payload["repetitions"],
        )


def test_duplicate_object_oid_is_rejected():
    payload = synthetic_payload()
    rows = [
        row for row in payload["metadata_observations"]
        if row["kind"] == "extended" and row["name"] is not None
    ]
    rows[1]["oid"] = rows[0]["oid"]
    with pytest.raises(RuntimeError, match="OID"):
        runner.validate(
            payload["observations"],
            payload["metadata_observations"],
            payload["repetitions"],
        )


def test_missing_per_cell_metadata_is_rejected():
    payload = synthetic_payload()
    last_extended = next(
        row for row in reversed(payload["metadata_observations"])
        if row["kind"] == "extended"
    )
    missing_cell = (last_extended["condition_id"], last_extended["repetition"])
    payload["metadata_observations"] = [
        row for row in payload["metadata_observations"]
        if not (
            row["kind"] == "extended"
            and (row["condition_id"], row["repetition"]) == missing_cell
        )
    ]
    with pytest.raises(RuntimeError, match="metadata cell coverage"):
        runner.validate(
            payload["observations"],
            payload["metadata_observations"],
            payload["repetitions"],
        )


def test_swapped_cpu_trace_groups_are_rejected():
    empty = next(c for c in runner.condition_list() if not c.subset)
    singleton = next(c for c in runner.condition_list() if c.subset == ("ab",))
    schedule = [(empty, 1, 1), (singleton, 1, 2)]
    stdout = "\n".join((
        "RUN|weakassoc__none__target100|1|1",
        "Time: 1.0 ms",
        "RUN|weakassoc__ab__target100|1|2",
        "Time: 1.0 ms",
    ))

    def trace(count: int) -> str:
        return (
            "DEBUG: ESS_EXT_CPU_TRACE: phase=BuildRelationExtStatistics "
            f"relid=1 stats_count={count} built_count={count} "
            "user_us=1 system_us=0 cpu_us=1"
        )

    # The two trace groups are deliberately swapped while remaining in one stream.
    stderr = "\n".join((trace(1), trace(1), trace(0), trace(0)))
    observations, _, _ = runner.parse_psql_output(stdout, stderr, schedule)
    with pytest.raises(RuntimeError, match="trace count"):
        runner.validate_cpu_trace_pair(observations[0], empty)


def test_cpu_trace_split_across_streams_is_rejected():
    condition = next(c for c in runner.condition_list() if not c.subset)
    schedule = [(condition, 1, 1)]
    stdout = "RUN|weakassoc__none__target100|1|1\nTime: 1.0 ms\n" + (
        "DEBUG: ESS_EXT_CPU_TRACE: phase=BuildRelationExtStatistics "
        "relid=1 stats_count=0 built_count=0 user_us=1 system_us=0 cpu_us=1\n"
    )
    stderr = (
        "DEBUG: ESS_EXT_CPU_TRACE: phase=BuildRelationExtStatistics "
        "relid=1 stats_count=0 built_count=0 user_us=1 system_us=0 cpu_us=1\n"
    )
    with pytest.raises(RuntimeError, match="exactly one ordered stream"):
        runner.parse_psql_output(stdout, stderr, schedule)
