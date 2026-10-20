"""Schema-only upper bounds for template strata; no rows or outcomes are read."""

from __future__ import annotations

from collections import Counter
from itertools import combinations, product
import hashlib
from pathlib import Path
from typing import Any

from cohort_recipe import split_for_template, template_fingerprint


# Extracted from the versioned AreCEL DatasetSpec/Forest10 source definitions.
# Numeric columns permit =, <, <=, >, >=, []; categorical permit = only.
SCHEMA = {
    "forest10": {
        "numeric": ("Elevation", "Aspect", "Slope", "Horizontal_Distance_To_Hydrology",
                    "Vertical_Distance_To_Hydrology", "Horizontal_Distance_To_Roadways",
                    "Hillshade_9am", "Hillshade_Noon", "Hillshade_3pm",
                    "Horizontal_Distance_To_Fire_Points"),
        "categorical": (),
    },
    "census13": {
        "numeric": ("age", "education_num", "capital_gain", "capital_loss", "hours_per_week"),
        "categorical": ("workclass", "education", "marital_status", "occupation",
                        "relationship", "race", "sex", "native_country"),
    },
    "dmv11": {
        "numeric": ("Reg_Valid_Date",),
        "categorical": ("Record_Type", "Registration_Class", "State", "County", "Body_Type",
                        "Fuel_Type", "Color", "Scofflaw_Indicator", "Suspension_Indicator",
                        "Revocation_Indicator"),
    },
    "power7": {
        "numeric": ("Global_active_power", "Global_reactive_power", "Voltage",
                    "Global_intensity", "Sub_metering_1", "Sub_metering_2", "Sub_metering_3"),
        "categorical": (),
    },
}
NUMERIC_OPERATORS = ("=", "<", "<=", ">", ">=", "[]")
EQUALITY = "equality-only"
RANGE = "closed-range-only"
INEQUALITY = "one-sided-inequality-only"
MIXED = "mixed-operator-families"
FAMILIES = (EQUALITY, RANGE, INEQUALITY, MIXED)
GRAPH_CLASSES = (
    "zero-edges", "one-edge", "multiple-disjoint-edges",
    "conflict-one-maximal-matching", "conflict-multiple-maximal-matchings",
)
SCHEMA_SOURCE_PINS = {
    "src/ess_research/arecel/real.py": "0c3f33594ae35cbca77f578752d28050dc88a4a9c5999965dea526eaf5f7cbf7",
    "src/ess_research/arecel/forest10.py": "e0ff5bec3acaeaae638eee760c5a3b9f57288062d23e7d05f09f3d87a787b5ac",
    "experiments/workload-structure-audit-issue59/audit_structure.py": "711be1a472439a8c27b59d5a91e6f7a0259ea22fbe69cdfdf7bef25e46fb6ebb",
    "experiments/workload-structure-audit-issue59/protocol-v1.json": "8e8d25bc9d2847936d2c45f51a3f870a8c44e632938e30db19cfe8aaf0d9063a",
}
ARECEL_GENERATOR_PIN = {
    "repository": "sfu-db/AreCELearnedYet",
    "commit": "aa52da7768023270bad884232972e0b77ec6534a",
    "path": "lecarb/workload/generator.py",
    "git_blob_sha": "72b2123a70922abc91a3d4d8455b44bb81f4223c",
    "scope_note": "pinned wsf_uniform/wsf_exponential produce equality for categorical columns and range/equality operators for numeric columns; this prospective protocol additionally admits strict numeric inequalities",
}


def verify_schema_source_pins(repo_root: Path) -> None:
    """Fail closed if schema/operator/candidate source contracts have drifted."""
    for relative, expected in SCHEMA_SOURCE_PINS.items():
        actual = hashlib.sha256((repo_root / relative).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"schema source pin mismatch: {relative}")


def predicate_bin(count: int, dimensions: int) -> str:
    if count == 1:
        return "1"
    if count == 2:
        return "2"
    if count <= 4:
        return "3-4"
    if count <= 7:
        return "5-7"
    return f"8-{dimensions}"


def _graph_class(columns: frozenset[str], edges: list[tuple[str, str]]) -> str:
    active = [(a, b) for a, b in edges if a in columns and b in columns]
    if not active:
        return "zero-edges"
    if len(active) == 1:
        return "one-edge"
    conflict = any(set(left) & set(right) for left, right in combinations(active, 2))
    if not conflict:
        return "multiple-disjoint-edges"
    maximal_count = 0
    for mask in range(1 << len(active)):
        chosen = [active[i] for i in range(len(active)) if mask & (1 << i)]
        vertices = [v for edge in chosen for v in edge]
        if len(vertices) != len(set(vertices)):
            continue
        chosen_set = set(chosen)
        if all(edge in chosen_set or set(edge) & set(vertices) for edge in active):
            maximal_count += 1
    return "conflict-one-maximal-matching" if maximal_count == 1 else "conflict-multiple-maximal-matchings"


def _family_counts(numeric_count: int, categorical_count: int) -> dict[str, int]:
    dimensions = numeric_count + categorical_count
    total = 6**numeric_count
    equality = 1
    range_only = 1 if numeric_count == dimensions else 0
    inequality_only = 4**dimensions if numeric_count == dimensions else 0
    mixed = total - equality - range_only - inequality_only
    return {EQUALITY: equality, RANGE: range_only, INEQUALITY: inequality_only, MIXED: mixed}


def capacity_table(dataset: str, candidate_pairs: list[str]) -> dict[str, Any]:
    spec = SCHEMA[dataset]
    numeric, categorical = set(spec["numeric"]), set(spec["categorical"])
    names = tuple(spec["numeric"] + spec["categorical"])
    if set(names) != numeric | categorical or numeric & categorical:
        raise ValueError(f"invalid schema partition for {dataset}")
    edges = []
    for pair in candidate_pairs:
        _, endpoints = pair.split(":", 1)
        left, right = endpoints.split("/")
        if left not in names or right not in names:
            raise ValueError(f"candidate endpoint outside {dataset} schema: {pair}")
        edges.append((left, right))

    dimensions = len(names)
    table: Counter[tuple[str, str, str]] = Counter()
    for count in range(1, dimensions + 1):
        for subset in combinations(names, count):
            selected = frozenset(subset)
            family_counts = _family_counts(len(selected & numeric), len(selected & categorical))
            graph = _graph_class(selected, edges)
            bin_name = predicate_bin(count, dimensions)
            for family, n_templates in family_counts.items():
                if n_templates:
                    table[(bin_name, family, graph)] += n_templates

    # Exact split capacities for low-cardinality bins (d<=2). These finite
    # template spaces are small enough to enumerate, including their actual
    # frozen fingerprint hashes; this catches split-specific impossibility.
    low_bin_split_counts: dict[str, Counter[str]] = {
        "1": Counter(), "2": Counter()
    }
    for count in (1, 2):
        if count > dimensions:
            continue
        for subset in combinations(names, count):
            op_domains = [NUMERIC_OPERATORS if column in numeric else ("=",) for column in subset]
            for operators in product(*op_domains):
                query = {"predicates": [
                    {"column": column, "operator": operator, "value": "schema-only"}
                    for column, operator in zip(subset, operators, strict=True)
                ]}
                low_bin_split_counts[str(count)][split_for_template(
                    dataset, template_fingerprint(query)
                )] += 1

    bins = list(dict.fromkeys(predicate_bin(i, dimensions) for i in range(1, dimensions + 1)))
    capacities = {b: sum(v for (bin_name, _, _), v in table.items() if bin_name == b) for b in bins}
    joint = {
        f"{b}|{family}|{graph}": table[(b, family, graph)]
        for b in bins for family in FAMILIES for graph in GRAPH_CLASSES
    }
    return {
        "dataset": dataset,
        "dimensions": dimensions,
        "numeric_columns": len(numeric),
        "categorical_columns": len(categorical),
        "predicate_bin_capacity_upper_bound": capacities,
        "joint_bin_operator_graph_capacity_upper_bound": joint,
        "operator_family_capacity_upper_bound": {
            f"{b}|{family}": sum(v for (bn, fam, _), v in table.items() if bn == b and fam == family)
            for b in bins for family in FAMILIES
        },
        "graph_class_capacity_upper_bound": {
            f"{b}|{graph}": sum(v for (bn, _, gc), v in table.items() if bn == b and gc == graph)
            for b in bins for graph in GRAPH_CLASSES
        },
        "low_predicate_exact_template_capacity_by_split": {
            bin_name: {split: low_bin_split_counts[bin_name][split]
                       for split in ("calibration", "heldout")}
            for bin_name in ("1", "2")
        },
        "qualification": "schema-only combinatorial upper bounds; before historical quarantine, split pool realization, literal feasibility or data access",
    }


def revised_predicate_quota(capacity: dict[str, Any], groups_per_split: int = 1000) -> dict[str, dict[str, int]]:
    """Cap singleton quota by exact fingerprint-split capacity; water-fill others."""
    capacities = capacity["predicate_bin_capacity_upper_bound"]
    bins = list(capacities)
    high_bins = bins[1:]
    if not high_bins:
        raise ValueError("schema has no multi-predicate bin")
    equal_base, remainder = divmod(groups_per_split, len(bins))
    initial = {b: equal_base + (i < remainder) for i, b in enumerate(bins)}
    low_caps = capacity["low_predicate_exact_template_capacity_by_split"]
    result: dict[str, dict[str, int]] = {}
    for split in ("calibration", "heldout"):
        quotas = {
            b: min(initial[b], low_caps[b][split]) if b in low_caps else initial[b]
            for b in bins
        }
        left = groups_per_split - sum(quotas.values())
        high_bins = bins[2:]
        if not high_bins:
            raise ValueError("schema has no predicate-count bin >=3")
        # Reallocate low-bin deficits equally across d>=3 bins. This preserves
        # the high-multipredicate objective and respects global bin capacities.
        while left:
            active = [b for b in high_bins if quotas[b] < capacities[b]]
            if not active:
                raise ValueError(f"schema capacity cannot fill {groups_per_split} groups")
            q, rem = divmod(left, len(active))
            increment = {b: q + (i < rem) for i, b in enumerate(active)}
            used = 0
            for b in active:
                add = min(increment[b], capacities[b] - quotas[b])
                quotas[b] += add
                used += add
            if used == 0:
                raise ValueError("quota water-fill made no progress")
            left -= used
        if sum(quotas[b] for b in bins[2:]) < groups_per_split // 2:
            raise ValueError("multi-predicate quota falls below the predeclared 50% minimum")
        result[split] = quotas
    for bin_name in ("1", "2"):
        if sum(result[split][bin_name] for split in result) > capacities[bin_name]:
            raise ValueError(f"combined split quota exceeds global capacity for bin {bin_name}")
    for bin_name in bins[2:]:
        if sum(result[split][bin_name] for split in result) > capacities[bin_name]:
            raise ValueError(f"combined split quota exceeds global capacity for bin {bin_name}")
    return result
