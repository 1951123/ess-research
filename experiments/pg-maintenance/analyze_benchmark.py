#!/usr/bin/env python3
"""Analyze Issue #7 timings with block-bootstrap uncertainty for additive error."""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path


def median(values: list[float]) -> float:
    return float(statistics.median(values))


def quantile(values: list[float], q: float) -> float:
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * q
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


def summary(values: list[float]) -> dict:
    med = median(values)
    q1 = quantile(values, 0.25)
    q3 = quantile(values, 0.75)
    mad = median([abs(value - med) for value in values])
    return {
        "n": len(values),
        "min_ms": min(values),
        "median_ms": med,
        "q1_ms": q1,
        "q3_ms": q3,
        "iqr_ms": q3 - q1,
        "mad_ms": mad,
        "max_ms": max(values),
    }


def aggregate_summaries(additive: list[dict]) -> list[dict]:
    """Build report-level summaries using conventional statistics.median."""
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for row in additive:
        grouped[(row["regime"], row["target_mode"])].append(row)
    output = []
    for (regime, target_mode), rows in sorted(grouped.items()):
        absolute_errors = [row["absolute_additivity_error_ms"] for row in rows]
        ratios = [
            row["error_bootstrap"]["error_to_uncertainty_ratio"]
            for row in rows
            if row["error_bootstrap"]["error_to_uncertainty_ratio"] is not None
        ]
        output.append(
            {
                "regime": regime,
                "target_mode": target_mode,
                "comparison_count": len(rows),
                "median_absolute_additivity_error_ms": median(absolute_errors),
                "max_absolute_additivity_error_ms": max(absolute_errors),
                "median_error_to_uncertainty_ratio": median(ratios) if ratios else None,
                "ratio_count": len(ratios),
                "intervals_including_zero": sum(
                    row["error_bootstrap"]["includes_zero"] for row in rows
                ),
            }
        )
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-repetitions", type=int, default=5000)
    parser.add_argument("--bootstrap-seed", type=int, default=20261017)
    parser.add_argument(
        "--fixture-metrics",
        type=Path,
        help="use a regenerated derived fixture-metrics JSON instead of the raw payload copy",
    )
    return parser.parse_args()


def validate_payload(payload: dict, conditions: dict[str, dict]) -> dict[str, dict[int, float]]:
    expected = int(payload["repetitions"])
    grouped: dict[str, dict[int, float]] = defaultdict(dict)
    duplicates: list[tuple[str, int]] = []
    for observation in payload["observations"]:
        condition_id = observation["condition_id"]
        repetition = int(observation["repetition"])
        if repetition in grouped[condition_id]:
            duplicates.append((condition_id, repetition))
        grouped[condition_id][repetition] = float(observation["psql_elapsed_ms"])
    expected_keys = {
        (condition_id, repetition)
        for condition_id in conditions
        for repetition in range(1, expected + 1)
    }
    actual_keys = {
        (condition_id, repetition)
        for condition_id, values in grouped.items()
        for repetition in values
    }
    if duplicates or actual_keys != expected_keys:
        raise SystemExit(
            "timed-cell validation failed: "
            f"duplicates={duplicates[:3]}, "
            f"missing={sorted(expected_keys - actual_keys)[:3]}, "
            f"unexpected={sorted(actual_keys - expected_keys)[:3]}"
        )

    metadata_by_condition: dict[str, list[dict]] = defaultdict(list)
    for row in payload["metadata_observations"]:
        metadata_by_condition[row["condition_id"]].append(row)
    errors: list[str] = []
    for condition_id, condition in conditions.items():
        actual = metadata_by_condition.get(condition_id, [])
        expected_count = expected * (len(condition["subset"]) or 1)
        if len(actual) != expected_count:
            errors.append(f"{condition_id}: metadata count {len(actual)} != {expected_count}")
        expected_names = {f"{condition['table']}_{edge}" for edge in condition["subset"]}
        actual_names = {row["name"] for row in actual if row["name"] is not None}
        if actual_names != expected_names:
            errors.append(f"{condition_id}: metadata names do not match expected names")
        for row in actual:
            if row["name"] is None:
                if condition["subset"]:
                    errors.append(f"{condition_id}: unexpected NONE metadata row")
                continue
            if row["name"] not in expected_names:
                continue
            edge = row["name"][len(condition["table"]) + 1 :]
            if row["statistics_target"] != condition["targets"][edge]:
                errors.append(f"{condition_id}: wrong target for {row['name']}")
            if not row["mcv_payload_built"]:
                errors.append(f"{condition_id}: MCV payload missing for {row['name']}")
    nonempty = [
        row
        for rows in metadata_by_condition.values()
        for row in rows
        if row["name"] is not None
    ]
    oids = [row["oid"] for row in nonempty]
    if any(oid is None or int(oid) <= 0 for oid in oids):
        errors.append("all nonempty metadata rows require a positive OID")
    if len(oids) != len(set(oids)):
        errors.append("nonempty OIDs are not unique")
    metadata_reps = [row.get("repetition") for row in nonempty]
    if metadata_reps and any(rep is not None for rep in metadata_reps):
        keys = [
            (row["condition_id"], row.get("repetition"), row["name"])
            for rows in metadata_by_condition.values()
            for row in rows
        ]
        if len(keys) != len(set(keys)):
            errors.append("metadata condition/repetition/name cells repeat")
        for condition_id, condition in conditions.items():
            expected_names = {f"{condition['table']}_{edge}" for edge in condition["subset"]}
            for repetition in range(1, expected + 1):
                observed_names = {
                    row["name"]
                    for row in metadata_by_condition[condition_id]
                    if row.get("repetition") == repetition and row["name"] is not None
                }
                if observed_names != expected_names:
                    errors.append(f"{condition_id} repetition {repetition}: metadata cell mismatch")
    if errors:
        raise SystemExit("metadata validation failed: " + "; ".join(errors))
    return grouped


def bootstrap_deltas(
    grouped: dict[tuple[str, ...], dict[int, float]],
    condition_ids: dict[tuple[str, ...], str],
    repetitions: int,
    count: int,
    seed: int,
) -> dict[tuple[str, ...], list[float]]:
    rng = random.Random(seed)
    subsets = [subset for subset in condition_ids if len(subset) >= 2]
    output = {subset: [] for subset in subsets}
    blocks = list(range(1, repetitions + 1))
    for _ in range(count):
        sampled = [rng.choice(blocks) for _ in blocks]
        medians = {
            subset: median([grouped[subset][block] for block in sampled])
            for subset in condition_ids
        }
        for subset in subsets:
            output[subset].append(
                sum(medians[(edge,)] for edge in subset)
                - medians[subset]
                - (len(subset) - 1) * medians[tuple()]
            )
    return output


def make_comparison(
    regime: str,
    target_mode: str,
    subset: tuple[str, ...],
    by_key: dict[tuple[str, str, tuple[str, ...]], dict],
    bootstrap_values: list[float],
) -> dict:
    empty = by_key[(regime, target_mode, tuple())]
    current = by_key[(regime, target_mode, subset)]
    singleton_deltas = {
        edge: by_key[(regime, target_mode, (edge,))]["timing"]["median_ms"]
        - empty["timing"]["median_ms"]
        for edge in subset
    }
    observed_increment = current["timing"]["median_ms"] - empty["timing"]["median_ms"]
    predicted_increment = sum(singleton_deltas.values())
    discrepancy = predicted_increment - observed_increment
    increment_scale = math.sqrt(
        current["timing"]["mad_ms"] ** 2 + empty["timing"]["mad_ms"] ** 2
    )
    increment_floor = 2.0 * increment_scale
    lower = quantile(bootstrap_values, 0.025)
    upper = quantile(bootstrap_values, 0.975)
    half_width = (upper - lower) / 2.0
    increment_detectable = abs(observed_increment) > increment_floor
    relative = None
    relative_status = "inconclusive_increment_noise"
    if increment_detectable and abs(observed_increment) > 1e-12:
        relative = discrepancy / observed_increment
        relative_status = "reported"
    return {
        "regime": regime,
        "target_mode": target_mode,
        "subset": list(subset),
        "empty_median_ms": empty["timing"]["median_ms"],
        "observed_median_ms": current["timing"]["median_ms"],
        "predicted_median_ms": empty["timing"]["median_ms"] + predicted_increment,
        "observed_incremental_ms": observed_increment,
        "predicted_incremental_ms": predicted_increment,
        "signed_additivity_error_ms": discrepancy,
        "absolute_additivity_error_ms": abs(discrepancy),
        "relative_additivity_error": relative,
        "relative_additivity_error_status": relative_status,
        "increment_noise_scale_ms": increment_scale,
        "increment_noise_floor_ms": increment_floor,
        "increment_detectability": increment_detectable,
        "error_bootstrap": {
            "method": "resample complete randomized repetition blocks and recompute all contributing medians",
            "replications": len(bootstrap_values),
            "lower_95_ms": lower,
            "upper_95_ms": upper,
            "half_width_95_ms": half_width,
            "includes_zero": lower <= 0.0 <= upper,
            "fraction_positive": sum(value > 0 for value in bootstrap_values) / len(bootstrap_values),
            "error_to_uncertainty_ratio": abs(discrepancy) / half_width if half_width > 1e-12 else None,
            "status": "inconclusive_noise_scale" if lower <= 0.0 <= upper else "descriptive_interval_excludes_zero",
        },
        "observed_timing": current["timing"],
    }


def main() -> int:
    args = parse_args()
    payload = json.loads(args.raw_json.read_text(encoding="utf-8"))
    conditions = {row["condition_id"]: row for row in payload["conditions"]}
    grouped_by_id = validate_payload(payload, conditions)
    rows = []
    for condition_id, condition in conditions.items():
        row = dict(condition)
        row["timing"] = summary(list(grouped_by_id[condition_id].values()))
        rows.append(row)
    by_key = {
        (row["regime"], row["target_mode"], tuple(row["subset"])): row
        for row in rows
    }
    additive = []
    group_index = 0
    for regime in sorted({row["regime"] for row in rows}):
        for target_mode in sorted({row["target_mode"] for row in rows}):
            local = {
                tuple(row["subset"]): row["condition_id"]
                for row in rows
                if row["regime"] == regime and row["target_mode"] == target_mode
            }
            grouped = {
                subset: grouped_by_id[condition_id]
                for subset, condition_id in local.items()
            }
            bootstraps = bootstrap_deltas(
                grouped, local, int(payload["repetitions"]), args.bootstrap_repetitions,
                args.bootstrap_seed + group_index,
            )
            group_index += 1
            for subset, values in bootstraps.items():
                additive.append(make_comparison(regime, target_mode, subset, by_key, values))

    aggregate = aggregate_summaries(additive)
    fixture_metrics = payload.get("fixture_metrics")
    fixture_metrics_source = "embedded raw observation payload"
    if args.fixture_metrics is not None:
        fixture_metrics = json.loads(args.fixture_metrics.read_text(encoding="utf-8"))
        fixture_metrics_source = str(args.fixture_metrics)
    result = {
        "schema_version": 2,
        "source_raw": str(args.raw_json),
        "provenance": payload["provenance"],
        "timing_method": payload["timing_method"],
        "fixture_metrics": fixture_metrics,
        "fixture_metrics_source": fixture_metrics_source,
        "condition_summaries": sorted(rows, key=lambda row: row["condition_id"]),
        "additive_comparisons": additive,
        "aggregate_summaries": aggregate,
        "bootstrap": {
            "replications": args.bootstrap_repetitions,
            "seed": args.bootstrap_seed,
            "block_definition": "one randomized condition order per repetition; resample complete repetition blocks",
            "interpretation": "descriptive interval for median-based D; not a formal significance test",
        },
        "interpretation_policy": {
            "central_estimate": "median of timed runs per condition",
            "spread": "IQR and MAD retained per condition",
            "increment_detectability": "abs(C(M)) compared with twice the quadrature MAD of current and empty conditions; descriptive only",
            "additivity_error_detectability": "D(M)=sum singleton medians - T(M) - (k-1)T(empty), with block bootstrap over all contributing conditions",
            "relative_error": "reported only when the observed increment exceeds the descriptive increment-noise screen; otherwise marked inconclusive",
            "realized_sample_rows": "not observed; requested target is source-derived only",
            "payload_validation": "unique timed cells, expected statistic names/targets, positive unique OIDs, and non-null MCV payloads are required",
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "analysis.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    lines = [
        "# PostgreSQL 16.14 ANALYZE maintenance-cost analysis",
        "",
        f"This report uses {payload['repetitions']} separately timed post-warm-up refreshes per condition. The central estimate is the condition median; randomized repetition blocks are resampled for a descriptive interval for D(M). This is not a formal significance test.",
        "",
        "## Additive proxy comparisons",
        "",
        "| Regime | Targets | Set | T(M) median ms | Additive predicted ms | Signed D ms | Relative D | D interval ms | Includes zero | Error/uncertainty | Increment screen |",
        "|---|---|---|---:|---:|---:|---:|---|---|---:|---|",
    ]
    for row in additive:
        bootstrap = row["error_bootstrap"]
        relative = "inconclusive" if row["relative_additivity_error"] is None else f"{row['relative_additivity_error']:.4f}"
        interval = f"[{bootstrap['lower_95_ms']:.3f}, {bootstrap['upper_95_ms']:.3f}]"
        ratio = bootstrap["error_to_uncertainty_ratio"]
        lines.append(
            f"| {row['regime']} | {row['target_mode']} | {','.join(row['subset'])} | "
            f"{row['observed_median_ms']:.3f} | {row['predicted_median_ms']:.3f} | "
            f"{row['signed_additivity_error_ms']:.3f} | {relative} | {interval} | "
            f"{'yes' if bootstrap['includes_zero'] else 'no'} | "
            f"{'n/a' if ratio is None else f'{ratio:.2f}'} | "
            f"{'detectable' if row['increment_detectability'] else 'noise-scale'} |"
        )
    lines.extend([
        "",
        "## Programmatic aggregate summaries",
        "",
        "The following summaries are computed from the complete comparison rows. "
        "All medians use the conventional median, including the arithmetic mean "
        "of the two middle values when there are four comparisons.",
        "",
        "| Regime | Targets | Comparisons | Median absolute D ms | Max absolute D ms | Median error/uncertainty | D intervals including zero |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for row in aggregate:
        ratio = row["median_error_to_uncertainty_ratio"]
        lines.append(
            f"| {row['regime']} | {row['target_mode']} | {row['comparison_count']} | "
            f"{row['median_absolute_additivity_error_ms']:.5f} | "
            f"{row['max_absolute_additivity_error_ms']:.5f} | "
            f"{'n/a' if ratio is None else f'{ratio:.5f}'} | "
            f"{row['intervals_including_zero']}/{row['comparison_count']} |"
        )
    lines.extend([
        "",
        "## Interpretation",
        "",
        "The additive proxy is Ĉ(M)=sum_e[T({e})-T(empty)] using medians within the same regime and target mode. The model discrepancy is D(M)=Ĉ(M)-C(M), not C(M) itself. The block bootstrap preserves complete randomized repetition blocks when recomputing all contributing medians; it does not establish a formal significance level. The benchmark measures scoped ANALYZE wall-clock time, does not observe realized sample rows, and does not establish a universal PostgreSQL CPU-cost law.",
    ])
    (args.output_dir / "analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    print(f"wrote {args.output_dir / 'analysis.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
