#!/usr/bin/env python3
"""Analyze raw Issue #7 timing observations without re-running PostgreSQL."""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path


def median(values: list[float]) -> float:
    return float(statistics.median(values))


def quantile(values: list[float], q: float) -> float:
    if len(values) == 1:
        return values[0]
    ordered = sorted(values)
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = json.loads(args.raw_json.read_text(encoding="utf-8"))
    conditions = {
        condition["condition_id"]: condition for condition in payload["conditions"]
    }
    grouped: dict[str, list[float]] = defaultdict(list)
    for observation in payload["observations"]:
        grouped[observation["condition_id"]].append(
            float(observation["psql_elapsed_ms"])
        )
    expected = payload["repetitions"]
    if set(grouped) != set(conditions):
        raise SystemExit("condition coverage mismatch")
    if any(len(values) != expected for values in grouped.values()):
        raise SystemExit("repetition coverage mismatch")
    metadata_by_condition: dict[str, list[dict]] = defaultdict(list)
    for metadata in payload["metadata_observations"]:
        metadata_by_condition[metadata["condition_id"]].append(metadata)
    metadata_errors: list[str] = []
    for condition_id, condition in conditions.items():
        expected_metadata = expected * (len(condition["subset"]) or 1)
        actual_metadata = metadata_by_condition.get(condition_id, [])
        if len(actual_metadata) != expected_metadata:
            metadata_errors.append(
                f"{condition_id}: expected {expected_metadata} metadata rows, found {len(actual_metadata)}"
            )
        if condition["subset"]:
            expected_names = {
                f"{condition['table']}_{edge}" for edge in condition["subset"]
            }
            actual_names = {row["name"] for row in actual_metadata}
            if actual_names != expected_names:
                metadata_errors.append(
                    f"{condition_id}: metadata names {sorted(actual_names)} != {sorted(expected_names)}"
                )
            if any(not row["mcv_payload_built"] for row in actual_metadata):
                metadata_errors.append(f"{condition_id}: an MCV payload was not built")
        elif any(row["name"] is not None for row in actual_metadata):
            metadata_errors.append(f"{condition_id}: empty condition has statistic metadata")
    if metadata_errors:
        raise SystemExit("metadata validation failed: " + "; ".join(metadata_errors))

    rows: list[dict] = []
    for condition_id, condition in conditions.items():
        values = grouped[condition_id]
        row = dict(condition)
        row["timing"] = summary(values)
        rows.append(row)

    by_key = {
        (row["regime"], row["target_mode"], tuple(row["subset"])): row
        for row in rows
    }
    additive: list[dict] = []
    for regime in sorted({row["regime"] for row in rows}):
        for target_mode in sorted({row["target_mode"] for row in rows}):
            empty = by_key[(regime, target_mode, tuple())]
            singleton_deltas = {}
            for edge in ("ab", "bc", "cd"):
                singleton = by_key[(regime, target_mode, (edge,))]
                singleton_deltas[edge] = (
                    singleton["timing"]["median_ms"]
                    - empty["timing"]["median_ms"]
                )
            for count in (2, 3):
                for subset in [
                    subset
                    for subset in by_key
                    if subset[0] == regime
                    and subset[1] == target_mode
                    and len(subset[2]) == count
                ]:
                    current = by_key[subset]
                    observed_delta = (
                        current["timing"]["median_ms"]
                        - empty["timing"]["median_ms"]
                    )
                    predicted_delta = sum(singleton_deltas[edge] for edge in subset[2])
                    predicted_raw = (
                        empty["timing"]["median_ms"] + predicted_delta
                    )
                    noise_scale = math.sqrt(
                        current["timing"]["mad_ms"] ** 2
                        + empty["timing"]["mad_ms"] ** 2
                    )
                    noise_floor = max(1e-9, 2.0 * noise_scale)
                    relative_error = None
                    if abs(observed_delta) > noise_floor:
                        relative_error = (
                            predicted_delta - observed_delta
                        ) / observed_delta
                    additive.append(
                        {
                            "regime": regime,
                            "target_mode": target_mode,
                            "subset": list(subset[2]),
                            "empty_median_ms": empty["timing"]["median_ms"],
                            "observed_median_ms": current["timing"]["median_ms"],
                            "predicted_median_ms": predicted_raw,
                            "observed_incremental_ms": observed_delta,
                            "predicted_incremental_ms": predicted_delta,
                            "absolute_incremental_error_ms": predicted_delta
                            - observed_delta,
                            "relative_incremental_error": relative_error,
                            "noise_scale_ms": noise_scale,
                            "noise_floor_ms": noise_floor,
                            "noise_dominated": relative_error is None,
                            "observed_timing": current["timing"],
                        }
                    )

    result = {
        "schema_version": 1,
        "source_raw": str(args.raw_json),
        "provenance": payload["provenance"],
        "timing_method": payload["timing_method"],
        "condition_summaries": sorted(rows, key=lambda row: row["condition_id"]),
        "additive_comparisons": additive,
        "interpretation_policy": {
            "central_estimate": "median of seven timed runs",
            "spread": "IQR and MAD retained per condition",
            "noise_screen": "incremental differences within twice the quadrature MAD are labeled noise-dominated; this is a descriptive screening rule, not a significance test",
            "realized_sample_rows": "not observed; requested target is source-derived only",
            "payload_validation": "every nonempty condition has exactly its requested objects with a non-null MCV payload after warm-up; empty conditions have no candidate objects",
        },
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output = args.output_dir / "analysis.json"
    output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    lines = [
        "# PostgreSQL 16.14 ANALYZE maintenance-cost analysis",
        "",
        "This report uses the median of seven timed refreshes per condition.  IQR and MAD are retained; a relative incremental error is omitted when the observed increment is within the documented descriptive noise screen.",
        "",
        "## Additive proxy comparisons",
        "",
        "| Regime | Targets | Set | T(M) median ms | Additive predicted ms | Delta error ms | Relative delta error | Noise screen |",
        "|---|---|---|---:|---:|---:|---:|---|",
    ]
    for row in additive:
        relative = (
            "inconclusive"
            if row["relative_incremental_error"] is None
            else f"{row['relative_incremental_error']:.4f}"
        )
        lines.append(
            f"| {row['regime']} | {row['target_mode']} | {','.join(row['subset'])} | "
            f"{row['observed_median_ms']:.3f} | {row['predicted_median_ms']:.3f} | "
            f"{row['absolute_incremental_error_ms']:.3f} | {relative} | "
            f"{'yes' if row['noise_dominated'] else 'no'} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation",
            "",
            "The additive proxy is \u005chat{C}(M)=sum_e [T({e})-T(empty)] using condition medians within the same regime and target mode.  Raw T(M) values must be considered alongside delta errors because small or negative increments can be dominated by timing noise.  The benchmark does not observe the realized sample count and does not establish a universal PostgreSQL cost law.",
        ]
    )
    (args.output_dir / "analysis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    print(f"wrote {args.output_dir / 'analysis.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
