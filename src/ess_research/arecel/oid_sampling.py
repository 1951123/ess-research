"""Deterministic Issue #107 OID-order sampling and finite-population estimates.

This module uses only the Python standard library. It does not load AreCEL
workloads, labels, PostgreSQL, or query-level observations.
"""

from __future__ import annotations

import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from fractions import Fraction
from pathlib import Path
from typing import Any, Sequence


RNG_VERSION = "ess-splitmix64-fisher-yates-v1"
ROOT_SEED = 17_770_611_677_888_985_956
T_975_DF_21 = 2.079613844727662
MASK_64 = (1 << 64) - 1


class IncompletePermutationSample(ValueError):
    """Raised instead of silently estimating from an incomplete arm set."""


@dataclass(frozen=True)
class PermutationValue:
    permutation: tuple[str, ...]
    value: float | None
    plan_status: str
    diagnostics_status: str


@dataclass(frozen=True)
class MeanEstimate:
    estimate: float
    variance_estimate: float
    sample_variance: float | None
    fixed_count: int
    residual_population_size: int
    sample_size: int

    @property
    def standard_error(self) -> float:
        return math.sqrt(max(0.0, self.variance_estimate))

    @property
    def degenerate_interval(self) -> bool:
        """True for a zero sample variance before exhausting the residual population."""
        return (
            self.sample_variance == 0.0
            and self.sample_size < self.residual_population_size
        )


@dataclass(frozen=True)
class PopulationVarianceEstimate:
    raw_variance_estimate: float
    standard_deviation_estimate: float
    truncated_at_zero: bool


class SplitMix64:
    """SplitMix64 with rejection sampling for unbiased bounded integers."""

    def __init__(self, seed: int):
        if not 0 <= seed <= MASK_64:
            raise ValueError("seed must be an unsigned 64-bit integer")
        self._state = seed

    def next_u64(self) -> int:
        self._state = (self._state + 0x9E3779B97F4A7C15) & MASK_64
        value = self._state
        value = ((value ^ (value >> 30)) * 0xBF58476D1CE4E5B9) & MASK_64
        value = ((value ^ (value >> 27)) * 0x94D049BB133111EB) & MASK_64
        return (value ^ (value >> 31)) & MASK_64

    def randbelow(self, upper: int) -> int:
        if not 1 <= upper <= (1 << 64):
            raise ValueError("upper must be in [1, 2**64]")
        limit = (1 << 64) - ((1 << 64) % upper)
        while True:
            value = self.next_u64()
            if value < limit:
                return value % upper


def canonical_json_bytes(value: Any) -> bytes:
    """Canonical UTF-8 JSON bytes used by the schedule and SHA-256 records."""
    return (
        json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def derive_stratum_seed(
    root_seed: int, dataset: str, policy: str, resource_ids: Sequence[str]
) -> int:
    ids = tuple(sorted(resource_ids))
    material = (
        f"ess-issue107-seed-v1\0{root_seed}\0{dataset}\0{policy}\0{','.join(ids)}"
    ).encode("utf-8")
    return int.from_bytes(hashlib.sha256(material).digest()[:8], "big")


def _validate_resources(resource_ids: Sequence[str]) -> tuple[str, ...]:
    ids = tuple(sorted(resource_ids))
    if not ids or any(not isinstance(item, str) or not item for item in ids):
        raise ValueError("resource_ids must contain nonempty strings")
    if len(set(ids)) != len(ids):
        raise ValueError("resource_ids must be unique")
    return ids


def _validate_order(order: Sequence[str], ids: tuple[str, ...]) -> tuple[str, ...]:
    result = tuple(order)
    if len(result) != len(ids) or set(result) != set(ids):
        raise ValueError("each fixed order must be a permutation of resource_ids")
    return result


def _fisher_yates(values: list[tuple[str, ...]], seed: int) -> list[tuple[str, ...]]:
    rng = SplitMix64(seed)
    for index in range(len(values) - 1, 0, -1):
        swap_index = rng.randbelow(index + 1)
        values[index], values[swap_index] = values[swap_index], values[index]
    return values


def sample_permutations(
    resource_ids: Sequence[str],
    *,
    random_sample_size: int,
    seed: int | None,
    fixed_orders: Sequence[Sequence[str]] = (),
    enumerate_all: bool = False,
) -> list[dict[str, Any]]:
    """Return fixed arms plus a uniform SRSWOR sample (or a full census).

    The selected records are in deterministic execution order: fixed arms in
    caller order, then sampled arms in Fisher-Yates draw order. For a census,
    all orders are emitted lexicographically and are marked ``enumerated``.
    """
    ids = _validate_resources(resource_ids)
    population = list(itertools.permutations(ids))
    fixed = [_validate_order(order, ids) for order in fixed_orders]
    if len(set(fixed)) != len(fixed):
        raise ValueError("fixed orders must be distinct")
    fixed_set = set(fixed)
    residual = [order for order in population if order not in fixed_set]

    if enumerate_all:
        if fixed or random_sample_size != len(population):
            raise ValueError("enumerate_all requires no fixed orders and the full size")
        return [
            {
                "permutation": list(order),
                "selection": "enumerated",
                "draw_index": None,
                "inclusion_probability": "1",
            }
            for order in population
        ]

    if not isinstance(random_sample_size, int) or random_sample_size < 0:
        raise ValueError("random_sample_size must be a nonnegative integer")
    if random_sample_size > len(residual):
        raise ValueError("sample size exceeds the residual permutation population")
    if random_sample_size and seed is None:
        raise ValueError("a seed is required for a nonempty random sample")

    records: list[dict[str, Any]] = [
        {
            "permutation": list(order),
            "selection": "fixed",
            "draw_index": None,
            "inclusion_probability": "1",
        }
        for order in fixed
    ]
    if random_sample_size:
        shuffled = _fisher_yates(residual.copy(), int(seed))
        inclusion = str(Fraction(random_sample_size, len(residual)))
        records.extend(
            {
                "permutation": list(order),
                "selection": "srswor",
                "draw_index": index,
                "inclusion_probability": inclusion,
            }
            for index, order in enumerate(shuffled[:random_sample_size])
        )
    if len({tuple(record["permutation"]) for record in records}) != len(records):
        raise AssertionError("sample generator produced duplicate permutations")
    return records


def _b5_selections(manifest: dict[str, Any]) -> dict[str, dict[str, dict[str, Any]]]:
    selections: dict[str, dict[str, dict[str, Any]]] = {}
    for case in manifest.get("cases", []):
        if case.get("budget") != 5 or case.get("objective") not in {"nominal", "pess"}:
            continue
        if case.get("status") != "COMPLETE":
            raise ValueError(f"frozen case is incomplete: {case.get('case_id')}")
        ds = case["dataset"]
        policy = case["objective"]
        if policy in selections.setdefault(ds, {}):
            raise ValueError(f"duplicate frozen B=5 case: {ds}/{policy}")
        selections[ds][policy] = case
    expected_datasets = {"forest10", "census13", "dmv11", "power7"}
    if set(selections) != expected_datasets:
        raise ValueError("frozen B=5 manifest does not contain exactly the four datasets")
    for ds, policies in selections.items():
        if set(policies) != {"nominal", "pess"}:
            raise ValueError(f"missing frozen B=5 policy case for {ds}")
        if policies["nominal"]["input_hashes"]["candidate_map_sha256"] != policies[
            "pess"
        ]["input_hashes"]["candidate_map_sha256"]:
            raise ValueError(f"candidate map differs between policies for {ds}")
        n_set = set(policies["nominal"]["selected_ids"])
        p_set = set(policies["pess"]["selected_ids"])
        if n_set == p_set:
            raise ValueError(f"B=5 policy sets unexpectedly duplicate for {ds}")
    return selections


def build_issue107_schedule(
    frozen_manifest_path: Path, root_seed: int = ROOT_SEED
) -> dict[str, Any]:
    manifest_bytes = frozen_manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    frozen = _b5_selections(manifest)
    schedules: list[dict[str, Any]] = []
    for dataset in ("forest10", "census13", "dmv11", "power7"):
        for policy in ("nominal", "pess"):
            case = frozen[dataset][policy]
            ids = tuple(sorted(case["selected_ids"]))
            candidate_map_sha = case["input_hashes"]["candidate_map_sha256"]
            k = len(ids)
            population_size = math.factorial(k)
            if policy == "nominal":
                if k != 5:
                    raise ValueError(f"Nominal set must have five objects: {dataset}")
                fixed = (ids, tuple(reversed(ids)))
                random_count = 22
                enumerate_all = False
            elif k == 5:
                fixed = ()
                random_count = 24
                enumerate_all = False
            elif k == 3:
                fixed = ()
                random_count = population_size
                enumerate_all = True
            else:
                raise ValueError(f"unexpected frozen PESS set size {k}: {dataset}")

            seed = None if enumerate_all else derive_stratum_seed(
                root_seed, dataset, policy, ids
            )
            arms = sample_permutations(
                ids,
                random_sample_size=random_count,
                seed=seed,
                fixed_orders=fixed,
                enumerate_all=enumerate_all,
            )
            schedule = {
                "dataset": dataset,
                "policy": policy,
                "case_id": case["case_id"],
                "candidate_map_sha256": candidate_map_sha,
                "resource_ids": list(ids),
                "permutation_population_size": population_size,
                "fixed_count": len(fixed),
                "random_sample_size": 0 if enumerate_all else random_count,
                "residual_population_size": population_size - len(fixed),
                "rng_version": RNG_VERSION,
                "stratum_seed_hex": None if seed is None else f"{seed:016x}",
                "permutations": arms,
            }
            schedule["sample_sha256"] = hashlib.sha256(
                canonical_json_bytes(arms)
            ).hexdigest()
            if len(arms) != (6 if enumerate_all else len(fixed) + random_count):
                raise AssertionError("generated schedule has an unexpected size")
            schedules.append(schedule)

    return {
        "format": "ess-issue107-oid-permutation-sample-v1",
        "root_seed": root_seed,
        "rng_version": RNG_VERSION,
        "seed_derivation": "first 8 SHA-256 bytes, big-endian, over NUL-delimited root seed/dataset/policy/sorted IDs",
        "draw_algorithm": "SplitMix64 v1; Fisher-Yates; rejection-sampled randbelow; take the first n from a shuffled residual population",
        "serialization": "UTF-8 canonical JSON, sorted keys, compact separators, terminal LF",
        "frozen_manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "schedules": schedules,
    }


def _checked_values(
    arms: Sequence[PermutationValue], expected_count: int, label: str
) -> tuple[float, ...]:
    if len(arms) != expected_count:
        raise IncompletePermutationSample(
            f"{label}: expected {expected_count} arms, got {len(arms)}"
        )
    if len({arm.permutation for arm in arms}) != len(arms):
        raise IncompletePermutationSample(f"{label}: duplicate permutation arm")
    values: list[float] = []
    for arm in arms:
        if arm.plan_status != "COMPLETE" or arm.diagnostics_status != "complete":
            raise IncompletePermutationSample(
                f"{label}: incomplete arm {arm.permutation}: "
                f"plan={arm.plan_status}, diagnostics={arm.diagnostics_status}"
            )
        if arm.value is None or not math.isfinite(float(arm.value)):
            raise IncompletePermutationSample(
                f"{label}: missing or nonfinite statistic for {arm.permutation}"
            )
        values.append(float(arm.value))
    return tuple(values)


def _sample_variance(values: Sequence[float]) -> float:
    if len(values) < 2:
        raise ValueError("at least two observations are needed for sample variance")
    mean = math.fsum(values) / len(values)
    return math.fsum((value - mean) ** 2 for value in values) / (len(values) - 1)


def estimate_stratified_mean(
    fixed_arms: Sequence[PermutationValue],
    sampled_arms: Sequence[PermutationValue],
    *,
    expected_fixed_count: int,
    expected_sample_size: int,
    residual_population_size: int,
) -> MeanEstimate:
    """Estimate the uniform permutation mean under certainty + SRSWOR strata."""
    if expected_fixed_count < 0 or residual_population_size <= 0:
        raise ValueError("invalid finite-population stratum sizes")
    if len(fixed_arms) != expected_fixed_count:
        raise IncompletePermutationSample(
            f"fixed stratum: expected {expected_fixed_count} arms, got {len(fixed_arms)}"
        )
    if not 1 <= expected_sample_size <= residual_population_size:
        raise ValueError("sample size must be in [1, residual population size]")
    fixed_values = _checked_values(fixed_arms, expected_fixed_count, "fixed stratum")
    sample_values = _checked_values(
        sampled_arms, expected_sample_size, "random stratum"
    )
    all_permutations = [arm.permutation for arm in fixed_arms]
    all_permutations.extend(arm.permutation for arm in sampled_arms)
    if len(set(all_permutations)) != len(all_permutations):
        raise IncompletePermutationSample("fixed and random strata overlap")

    residual_n = residual_population_size
    total_n = expected_fixed_count + residual_n
    sample_n = expected_sample_size
    residual_mean = math.fsum(sample_values) / sample_n
    estimate = (math.fsum(fixed_values) + residual_n * residual_mean) / total_n

    if sample_n == residual_n:
        sample_var = _sample_variance(sample_values) if sample_n >= 2 else None
        variance = 0.0
    else:
        sample_var = _sample_variance(sample_values)
        variance = (
            (residual_n / total_n) ** 2
            * (1.0 - sample_n / residual_n)
            * sample_var
            / sample_n
        )
    return MeanEstimate(
        estimate=estimate,
        variance_estimate=variance,
        sample_variance=sample_var,
        fixed_count=expected_fixed_count,
        residual_population_size=residual_n,
        sample_size=sample_n,
    )


def difference_estimate(
    pess: MeanEstimate, nominal: MeanEstimate
) -> MeanEstimate:
    """PESS minus Nominal for independently sampled permutation strata."""
    return MeanEstimate(
        estimate=pess.estimate - nominal.estimate,
        variance_estimate=pess.variance_estimate + nominal.variance_estimate,
        sample_variance=None,
        fixed_count=pess.fixed_count + nominal.fixed_count,
        residual_population_size=(
            pess.residual_population_size + nominal.residual_population_size
        ),
        sample_size=pess.sample_size + nominal.sample_size,
    )


def confidence_interval_95(estimate: float, standard_error: float) -> tuple[float, float]:
    """Conservative t-based interval using the protocol's minimum df=21."""
    half_width = T_975_DF_21 * standard_error
    return estimate - half_width, estimate + half_width


def estimate_population_variance(
    fixed_arms: Sequence[PermutationValue],
    sampled_arms: Sequence[PermutationValue],
    *,
    expected_fixed_count: int,
    expected_sample_size: int,
    residual_population_size: int,
) -> PopulationVarianceEstimate:
    """Estimate permutation-outcome variance, correcting for mean estimation.

    The raw estimator is unbiased for the finite-population variance with
    denominator N. Its square root is truncated at zero only if sampling noise
    makes the unbiased variance estimate negative; the truncation is reported.
    """
    mean = estimate_stratified_mean(
        fixed_arms,
        sampled_arms,
        expected_fixed_count=expected_fixed_count,
        expected_sample_size=expected_sample_size,
        residual_population_size=residual_population_size,
    )
    fixed_values = _checked_values(fixed_arms, expected_fixed_count, "fixed stratum")
    sample_values = _checked_values(
        sampled_arms, expected_sample_size, "random stratum"
    )
    total_n = expected_fixed_count + residual_population_size
    estimated_second_moment = (
        math.fsum(value * value for value in fixed_values)
        + residual_population_size
        * math.fsum(value * value for value in sample_values)
        / expected_sample_size
    ) / total_n
    raw_variance = (
        estimated_second_moment
        - mean.estimate**2
        + mean.variance_estimate
    )
    truncated = raw_variance < 0.0
    return PopulationVarianceEstimate(
        raw_variance_estimate=raw_variance,
        standard_deviation_estimate=math.sqrt(max(0.0, raw_variance)),
        truncated_at_zero=truncated,
    )


def main() -> None:
    repo = Path(__file__).resolve().parents[3]
    manifest_path = (
        repo / "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json"
    )
    schedule = build_issue107_schedule(manifest_path)
    print(canonical_json_bytes(schedule).decode("utf-8"), end="")


if __name__ == "__main__":
    main()
