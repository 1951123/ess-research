#!/usr/bin/env python3
"""Analyze Issue #9 backend CPU observations without using wall time as CPU."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path


EDGES = ("ab", "bc", "cd")
TARGETS = (100, 300)
REGIMES = ("weakassoc", "correlated")
BOOTSTRAP_REPLICATES = 5000


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def quantile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("empty bootstrap sample")
    ordered = sorted(values)
    position = probability * (len(ordered) - 1)
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] * (1 - fraction) + ordered[upper] * fraction


def subset_key(subset: list[str] | tuple[str, ...]) -> str:
    return "none" if not subset else "+".join(subset)


def load_and_validate(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("experiment") != "issue-9-pg16-fixed-target-extstats-cpu":
        raise ValueError("unexpected experiment identity")
    if payload.get("timed_observation_count") != 640:
        raise ValueError("Issue #9 analysis requires exactly 640 timed observations")
    if payload.get("condition_count") != 32 or payload.get("repetitions") != 20:
        raise ValueError("expected 32 conditions and 20 randomized blocks")
    observations = payload.get("observations", [])
    if len(observations) != 640:
        raise ValueError(f"observation count mismatch: {len(observations)}")
    keys = {(row["condition_id"], row["repetition"]) for row in observations}
    if len(keys) != 640:
        raise ValueError("duplicate or missing condition/repetition cells")
    for row in observations:
        trace = row["cpu_trace"]
        for field in ("user_us", "system_us", "cpu_us"):
            value = trace[field]
            if not isinstance(value, int) or value < 0:
                raise ValueError(f"invalid CPU value {field}={value!r}")
        if trace["cpu_us"] != trace["user_us"] + trace["system_us"]:
            raise ValueError("CPU user/system decomposition mismatch")
    return payload


def grouped_values(payload: dict) -> dict[tuple[str, int, str], list[float]]:
    values: dict[tuple[str, int, str], list[float]] = defaultdict(list)
    for row in payload["observations"]:
        key = (
            row["regime"],
            int(row["target"]),
            subset_key(row["subset"]),
        )
        values[key].append(float(row["cpu_trace"]["cpu_us"]))
    expected_subsets = {
        subset_key(subset)
        for count in range(4)
        for subset in itertools.combinations(EDGES, count)
    }
    for regime in REGIMES:
        for target in TARGETS:
            for subset in expected_subsets:
                key = (regime, target, subset)
                if len(values[key]) != 20:
                    raise ValueError(f"expected 20 blocks for {key}, found {len(values[key])}")
    return values


def block_matrix(
    payload: dict, regime: str, target: int
) -> tuple[list[int], dict[str, list[float]]]:
    rows = [
        row
        for row in payload["observations"]
        if row["regime"] == regime and int(row["target"]) == target
    ]
    by_subset: dict[str, dict[int, float]] = defaultdict(dict)
    for row in rows:
        by_subset[subset_key(row["subset"])][int(row["repetition"])] = float(
            row["cpu_trace"]["cpu_us"]
        )
    repetitions = sorted({int(row["repetition"]) for row in rows})
    matrix = {
        subset: [by_subset[subset][rep] for rep in repetitions]
        for subset in by_subset
    }
    return repetitions, matrix


def medians(matrix: dict[str, list[float]]) -> dict[str, float]:
    return {subset: statistics.median(values) for subset, values in matrix.items()}


def signed_error(
    median_map: dict[str, float], subset: tuple[str, ...]
) -> tuple[float, float, float]:
    key = subset_key(subset)
    baseline = median_map["none"]
    observed_increment = median_map[key] - baseline
    predicted_increment = sum(median_map[edge] - baseline for edge in subset)
    return observed_increment, predicted_increment, predicted_increment - observed_increment


def bootstrap_errors(
    matrix: dict[str, list[float]], subset: tuple[str, ...], seed: int
) -> list[float]:
    reps = len(matrix["none"])
    rng = random.Random(seed)
    values: list[float] = []
    key = subset_key(subset)
    for _ in range(BOOTSTRAP_REPLICATES):
        sample_indices = [rng.randrange(reps) for _ in range(reps)]
        sampled_medians = {
            name: statistics.median([matrix[name][index] for index in sample_indices])
            for name in ("none", *EDGES, key)
        }
        _, _, error = signed_error(sampled_medians, subset)
        values.append(error)
    return values


def make_analysis(payload: dict, raw_path: Path) -> dict:
    records: list[dict] = []
    subsets = [
        subset
        for count in range(2, 4)
        for subset in itertools.combinations(EDGES, count)
    ]
    for regime in REGIMES:
        for target in TARGETS:
            _, matrix = block_matrix(payload, regime, target)
            median_map = medians(matrix)
            for subset in subsets:
                observed, predicted, error = signed_error(median_map, subset)
                bootstrap = bootstrap_errors(
                    matrix,
                    subset,
                    seed=int(payload["seed"])
                    + target * 1000
                    + len(regime) * 17
                    + len(subset),
                )
                records.append(
                    {
                        "regime": regime,
                        "target": target,
                        "subset": list(subset),
                        "subset_id": subset_key(subset),
                        "baseline_median_cpu_us": median_map["none"],
                        "observed_median_increment_cpu_us": observed,
                        "predicted_median_increment_cpu_us": predicted,
                        "signed_additivity_error_cpu_us": error,
                        "absolute_additivity_error_cpu_us": abs(error),
                        "relative_error_to_observed_increment": (
                            error / observed if observed != 0 else None
                        ),
                        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
                        "bootstrap_error_ci95_cpu_us": [
                            quantile(bootstrap, 0.025),
                            quantile(bootstrap, 0.975),
                        ],
                        "bootstrap_error_median_cpu_us": quantile(bootstrap, 0.5),
                    }
                )
    return {
        "schema_version": 1,
        "experiment": payload["experiment"],
        "raw_observations_sha256": sha256_file(raw_path),
        "seed": payload["seed"],
        "repetitions": payload["repetitions"],
        "bootstrap": {
            "unit": "randomized repetition block containing all 32 conditions",
            "replicates": BOOTSTRAP_REPLICATES,
            "resampling_seed_derivation": (
                "campaign seed + target*1000 + len(regime)*17 + subset cardinality"
            ),
            "interval": (
                "percentile 95% interval for signed predicted-minus-observed "
                "median incremental CPU error"
            ),
        },
        "comparison_definition": {
            "baseline": "median CPU(empty)",
            "observed_increment": "median CPU(M) - median CPU(empty)",
            "predicted_increment": (
                "sum_e median CPU({e}) - (|M|-1)*median CPU(empty)"
            ),
            "signed_error": "predicted_increment - observed_increment",
            "primary_unit": "backend user+system CPU microseconds",
            "wall_round_trip_not_used": True,
        },
        "comparisons": records,
    }


def markdown_report(payload: dict, analysis: dict) -> str:
    lines = [
        "# Issue #9 fixed-target PostgreSQL maintenance CPU analysis",
        "",
        "This report uses the opt-in backend getrusage(RUSAGE_SELF) trace around "
        "the complete BuildRelationExtStatistics() phase. The psql round-trip "
        "measurements are retained in the raw artifact but are not the primary "
        "CPU evidence.",
        "",
        "## Campaign validation",
        "",
        f"- Conditions: {payload['condition_count']} (two regimes × two targets × eight subsets).",
        f"- Randomized repetition blocks: {payload['repetitions']}; timed observations: {payload['timed_observation_count']}.",
        f"- Raw SHA256: {analysis['raw_observations_sha256']}.",
        "- Every cell has one warm-up and one timed CPU trace; metadata validates "
        "ordinary targets, MCV targets, payload presence, OIDs, and trace relation identity.",
        "- Requested sample rows are source-derived as max(100, 300 * max(target)): "
        "30,000 at target 100 and 90,000 at target 300. Realized sample rows were "
        "not claimed or measured.",
        "",
        "## Independent singleton prediction",
        "",
        "Signed error is predicted incremental CPU minus observed incremental CPU; "
        "positive values are additive overprediction. Bootstrap intervals resample "
        "complete randomized repetition blocks.",
        "",
        "| Regime | Target | Subset | Baseline median us | Observed increment us | Predicted increment us | Signed error us | 95% block-bootstrap CI us | Relative error |",
        "|---|---:|---|---:|---:|---:|---:|---:|---:|",
    ]
    for record in analysis["comparisons"]:
        relative = (
            "n/a"
            if record["relative_error_to_observed_increment"] is None
            else f"{record['relative_error_to_observed_increment']:.4g}"
        )
        ci = record["bootstrap_error_ci95_cpu_us"]
        lines.append(
            f"| {record['regime']} | {record['target']} | {record['subset_id']} | "
            f"{record['baseline_median_cpu_us']:.1f} | "
            f"{record['observed_median_increment_cpu_us']:.1f} | "
            f"{record['predicted_median_increment_cpu_us']:.1f} | "
            f"{record['signed_additivity_error_cpu_us']:.1f} | "
            f"[{ci[0]:.1f}, {ci[1]:.1f}] | {relative} |"
        )
    lines.extend(
        [
            "",
            "## Interpretation boundary",
            "",
            "The singleton construction is an independent prediction of whole-phase "
            "CPU medians; it does not add per-object timings from the same multi-object "
            "run. A confidence interval containing zero does not prove exact additivity, "
            "and an interval excluding zero is evidence only for the stated fixture, "
            "target, build, and horizon. The campaign does not measure future refreshes "
            "or establish a universal PostgreSQL maintenance law.",
            "",
            "The fixed target controls ordinary-column and explicit MCV statistics "
            "targets. The source-derived requested sample formula is a control "
            "invariant, not an observation of the realized sample tuple count.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("raw_json", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    if args.output_dir.exists():
        raise SystemExit(f"refusing to overwrite existing analysis directory: {args.output_dir}")
    payload = load_and_validate(args.raw_json)
    grouped_values(payload)
    analysis = make_analysis(payload, args.raw_json)
    args.output_dir.mkdir(parents=True, exist_ok=False)
    (args.output_dir / "analysis.json").write_text(
        json.dumps(analysis, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.output_dir / "report.md").write_text(
        markdown_report(payload, analysis), encoding="utf-8"
    )
    print(f"wrote {args.output_dir / 'analysis.json'} and report.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
