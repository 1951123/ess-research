"""Derive a fair-cost/accounting analysis from preserved Stage 0B v1 JSONL.

This deliberately does not rewrite the frozen v1 observations.  It reports
the timing fields that v1 actually captured, marks end-to-end method timing as
NOT MEASURED, and summarizes the matched original-model ablation without
turning solver-core timing into a speedup claim.
"""

from __future__ import annotations

import argparse
import json
from fractions import Fraction
from pathlib import Path
from statistics import median

from stage0b_serialization import instance_from_json, read_json

SETUPS = (
    "unrounded",
    "coarse_uniform_delta_1",
    "matching_aware_eta_1_2",
    "matching_aware_eta_1_4",
)


def task_count_for(run_dir: Path, instance_name: str) -> int:
    instance_path = run_dir.parent.parent / "instances" / f"{instance_name}.json"
    return len(json.loads(instance_path.read_text())["tasks"])


def fraction(value: str | int | None) -> Fraction | None:
    return None if value is None else Fraction(value)


def text(value: Fraction | None) -> str | None:
    if value is None:
        return None
    return str(value.numerator) if value.denominator == 1 else f"{value.numerator}/{value.denominator}"


def exact_stats(values: list[Fraction]) -> dict[str, str | None]:
    if not values:
        return {"count": 0, "mean": None, "median": None, "min": None, "max": None}
    ordered = sorted(values)
    return {
        "count": len(values),
        "mean": text(sum(values, Fraction(0)) / len(values)),
        "median": text(Fraction(median(ordered))),
        "min": text(ordered[0]),
        "max": text(ordered[-1]),
    }


def float_stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {"count": 0, "sum_seconds": None, "median_seconds": None}
    return {"count": len(values), "sum_seconds": sum(values), "median_seconds": median(values)}


def naive_eta(instance, rounded_by_task: dict[str, dict[str, Fraction]]) -> Fraction:
    """Use the same rounded coefficients with an all-eligible-edge bound."""

    return sum(
        (
            task.weight
            * sum(
                (
                    abs(task.coefficients[label] - rounded_by_task[task.name][label])
                    for label in task.coefficients
                ),
                Fraction(0),
            )
            for task in instance.tasks
        ),
        Fraction(0),
    )


def same_rounded_bound_ablation(rows: list[dict], run_dir: Path) -> dict:
    """Compare matching-aware eta with a naive all-edge eta on each frozen row."""

    instances = {}
    records = []
    for row in rows:
        instance = instances.setdefault(
            row["instance"],
            instance_from_json(
                read_json(run_dir.parent.parent / "instances" / f"{row['instance']}.json")
            ),
        )
        rounded = {
            task: {label: Fraction(value) for label, value in coefficients.items()}
            for task, coefficients in row["rounded_coefficients"].items()
        }
        matching_eta = fraction(row["perturbation"]["eta"])
        all_edge_eta = naive_eta(instance, rounded)
        if matching_eta is None:
            raise AssertionError("v1 eta must be present for the same-rounded ablation")
        if matching_eta > all_edge_eta:
            raise AssertionError(
                f"matching-aware eta exceeded naive eta for {row['setup']} / {row['instance']}"
            )
        records.append(
            {
                "setup": row["setup"],
                "tier": row["tier"],
                "instance": row["instance"],
                "matching_aware_eta": text(matching_eta),
                "naive_all_edge_eta": text(all_edge_eta),
                "tightening": text(all_edge_eta - matching_eta),
                "strictly_tighter": matching_eta < all_edge_eta,
            }
        )

    by_setup = {}
    for setup in SETUPS:
        selected = [record for record in records if record["setup"] == setup]
        gains = [fraction(record["tightening"]) for record in selected]
        positive = [record for record in selected if record["strictly_tighter"]]
        zero = [record for record in selected if not record["strictly_tighter"]]
        by_setup[setup] = {
            "rows": len(selected),
            "strictly_tighter_count": len(positive),
            "equal_count": len(zero),
            "total_tightening": text(sum(gains, Fraction(0))),
            "mean_tightening": text(sum(gains, Fraction(0)) / len(gains)),
            "max_tightening": text(max(gains, default=Fraction(0))),
            "strictly_tighter_rows": positive,
            "zero_gain_rows": zero,
        }
    return {"by_setup": by_setup, "rows": records}


def analyze(run_dir: Path) -> dict:
    rows = [json.loads(line) for line in (run_dir / "observations.jsonl").read_text().splitlines()]
    by_setup = {}
    for setup in SETUPS:
        selected = [row for row in rows if row["setup"] == setup]
        tiny = [row for row in selected if row["tier"] == "small"]
        stress = [row for row in selected if row["tier"] == "stress"]
        tiny_incumbents = [fraction(row["original"]["incumbent_value"]) for row in tiny]
        tiny_gaps = [fraction(row["original"]["gap"]) for row in tiny if row["original"]["gap"] is not None]
        stress_incumbents = [fraction(row["original"]["incumbent_value"]) for row in stress]
        matching_calls = sum(
            task_count_for(run_dir, row["instance"])
            * (4 if setup.startswith("matching_aware") else 3)
            for row in selected
        )
        tiny_partial_seconds = [
            row["approximation"]["elapsed_seconds"] + row["certificate_overhead_seconds"]
            for row in tiny
        ]
        tiny_core_seconds = [row["approximation"]["elapsed_seconds"] for row in tiny]
        state_counts = [row["approximation"]["states"] for row in tiny]
        by_setup[setup] = {
            "rows": len(selected),
            "tiny_rows": len(tiny),
            "stress_rows": len(stress),
            "tiny_original_incumbent": exact_stats(tiny_incumbents),
            "tiny_original_certified_gap": exact_stats(tiny_gaps),
            "tiny_tau_attainment": sum(row["original"]["target_reached"] for row in tiny),
            "stress_original_feasible_score": exact_stats(stress_incumbents),
            "stress_global_gap": "NO_GLOBAL_GAP",
            "rounded_solver_core_time": float_stats(tiny_core_seconds),
            "recorded_partial_core_plus_certificate_time": float_stats(tiny_partial_seconds),
            "end_to_end_method_time": "NOT_MEASURED_V1",
            "timing_variance": "NOT_ESTIMATED_SINGLE_RUN",
            "tiny_rounded_objective_calls": sum(state_counts),
            "stress_objective_calls": "NOT_RECORDED_V1_GREEDY_NEIGHBOR_EVALUATIONS",
            "matching_oracle_calls": matching_calls,
            "matching_oracle_call_basis": "source-derived exact count: three certificate matching computations per task, plus one nu computation per task for matching-aware delta setup",
            "tiny_state_counts": state_counts,
        }

    tiny_by_instance = {}
    for instance in sorted({row["instance"] for row in rows if row["tier"] == "small"}):
        counts = {
            setup: next(row["approximation"]["states"] for row in rows if row["instance"] == instance and row["setup"] == setup)
            for setup in SETUPS
        }
        tiny_by_instance[instance] = counts
    no_state_reduction = all(len(set(counts.values())) == 1 for counts in tiny_by_instance.values())
    bound_ablation = same_rounded_bound_ablation(rows, run_dir)
    return {
        "source_run": str(run_dir),
        "source_evidence_preserved": True,
        "rows": len(rows),
        "by_setup": by_setup,
        "same_rounded_bound_ablation": bound_ablation,
        "tiny_state_counts_equal_across_setups": no_state_reduction,
        "end_to_end_comparison_status": "NOT_MEASURED",
        "end_to_end_reason": "v1 starts the recorded timers after delta setup/quantization and does not record every greedy neighbor objective call or peak memory; solver-core timings are diagnostic only",
        "resource_cap_status": "SELECTION_ENGINE_ONLY_IN_V1",
        "memory_cap_status": "NOT_ENFORCED_IN_V1",
        "decision": "INCONCLUSIVE",
        "decision_reason": "The matched tiny engines enumerate the same state space and have no measured end-to-end timing; Reference B is unavailable and stress rows have no global rounded lower bound.",
    }


def markdown(analysis: dict) -> str:
    lines = [
        "# Stage 0B v1 follow-up accounting analysis",
        "",
        "This file is derived from the preserved `runs/20261019-issue33-v1/` evidence; it does not rewrite that evidence.",
        "",
        "## Matched tiny ablation",
        "",
        "| setup | original incumbent mean/median | certified gap mean/median | tau | rounded-core seconds (sum/median) | recorded partial seconds, tiny n=12 (sum/median) |",
        "|---|---|---|---:|---:|---:|",
    ]
    for setup in SETUPS:
        row = analysis["by_setup"][setup]
        incumbent = row["tiny_original_incumbent"]
        gap = row["tiny_original_certified_gap"]
        core = row["rounded_solver_core_time"]
        partial = row["recorded_partial_core_plus_certificate_time"]
        lines.append(
            f"| `{setup}` | {incumbent['mean']} / {incumbent['median']} | {gap['mean']} / {gap['median']} | {row['tiny_tau_attainment']}/12 | {core['sum_seconds']:.6f} / {core['median_seconds']:.6f} | {partial['sum_seconds']:.6f} / {partial['median_seconds']:.6f} |"
        )
    lines += [
        "",
        f"All tiny setups used the same feasible state count per instance: `{analysis['tiny_state_counts_equal_across_setups']}`. This is a negative result for state-space reduction; the recorded solver-core times are single-run diagnostics and are not end-to-end method times.",
        "",
        "## Same-rounded perturbation-bound ablation",
        "",
        "For every frozen v1 row, the matching-aware `eta = sum_i w_i max_ordinary_matching(sum_e |error_e|)` is compared with `eta_naive = sum_i w_i sum_{eligible e} |error_e|` using the identical recorded rounded coefficients. The exact row-level values are retained in `analysis-v1.json`.",
        "",
        "| setup | matching-aware strictly tighter | equal / zero gain | rows | total tightening | mean tightening | max tightening |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for setup in SETUPS:
        row = analysis["same_rounded_bound_ablation"]["by_setup"][setup]
        lines.append(
            f"| `{setup}` | {row['strictly_tighter_count']} | {row['equal_count']} | {row['rows']} | {row['total_tightening']} | {row['mean_tightening']} | {row['max_tightening']} |"
        )
    lines += [
        "",
        "Positive gains are listed exactly below; all other rows are explicit zero-gain cases in the JSON report:",
    ]
    for setup in SETUPS:
        positive = analysis["same_rounded_bound_ablation"]["by_setup"][setup]["strictly_tighter_rows"]
        if not positive:
            lines.append(f"- `{setup}`: no strict tightening; all rows are zero-gain.")
            continue
        details = ", ".join(
            f"`{record['instance']}` ({record['tier']}): {record['matching_aware_eta']} -> {record['naive_all_edge_eta']} (gain {record['tightening']})"
            for record in positive
        )
        lines.append(f"- `{setup}`: {details}.")
    lines += [
        "",
        "## Stress tier",
        "",
        "| setup | original feasible score mean/median | global gap |",
        "|---|---|---|",
    ]
    for setup in SETUPS:
        row = analysis["by_setup"][setup]
        score = row["stress_original_feasible_score"]
        lines.append(f"| `{setup}` | {score['mean']} / {score['median']} | `{row['stress_global_gap']}` |")
    lines += [
        "",
        "## Accounting limits",
        "",
        "- End-to-end comparison: **NOT MEASURED** in v1. Delta/nu setup, quantization, original incumbent evaluation, complete matching-oracle counts, and peak memory were not all inside the recorded timer.",
        "- The JSON records source-derived matching-oracle call counts for the deterministic certificate path; stress greedy neighbor objective calls remain **NOT RECORDED** because v1 only stored accepted-extension states.",
        "- v1 wall caps are therefore interpreted as **selection-engine-only** caps; the declared memory cap was **NOT ENFORCED**. No full-pipeline resource claim is made.",
        "- Stress greedy rows retain original feasible scores but report **NO GLOBAL GAP**. Reference B remains **NOT EXECUTED**.",
        "- Decision remains **INCONCLUSIVE** and there is no speedup claim.",
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    result = analyze(args.run_dir)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "analysis-v1.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    (args.output_dir / "analysis-v1.md").write_text(markdown(result))


if __name__ == "__main__":
    main()
