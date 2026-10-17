#!/usr/bin/env python3
"""Reconstruct fixed-snapshot MCV selectivity identities from raw traces.

The script consumes the unmodified psql stdout/stderr captured from
mcv_numeric_snapshot.sql.  It never uses EXPLAIN row counts as selectivity
factors; row counts are parsed only as a separate final-output comparison.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


BASE_RE = re.compile(
    r"ESS_MCV_NUMERIC_TRACE: base_relation_oid=(?P<oid>\d+) "
    r"rte_index=(?P<rte>\d+) rel_tuples=(?P<R>\S+) "
    r"selectivity_preclamp=(?P<sel>\S+) nrows_preclamp=(?P<nrows>\S+) "
    r"rows_postclamp=(?P<rows>\S+) query=(?P<query>.*)$"
)
MCV_RE = re.compile(
    r"ESS_MCV_NUMERIC_TRACE: relid=(?P<oid>\d+) "
    r"selected_stat_oid=(?P<stat>\d+) stat_clause_count=(?P<count>\d+) "
    r"simple_sel=(?P<simple>\S+) mcv_sel=(?P<mcv>\S+) "
    r"mcv_basesel=(?P<base>\S+) mcv_totalsel=(?P<total>\S+) "
    r"stat_sel=(?P<stat_sel>\S+) query=(?P<query>.*)$"
)
SELECTED_RE = re.compile(
    r"ESS_MCV_TRACE: relid=(?P<oid>\d+) selected_stat_oid=(?P<stat>\d+)"
)
CLAIMED_RE = re.compile(
    r"ESS_MCV_TRACE: relid=(?P<oid>\d+) selected_stat_oid=(?P<stat>\d+) "
    r"claimed_clause_index=(?P<idx>\d+)"
)
MARKER_RE = re.compile(r"ESS_MCV_NUMERIC_TRACE:(?P<marker>[A-Za-z0-9_]+)")
ROWS_RE = re.compile(r"\brows=(?P<rows>\d+)\b")
SCENARIO_TO_MEASUREMENT = {
    "only_bc": "full_only_bc",
    "only_ab": "full_only_ab",
    "only_cd": "full_only_cd",
    "none": "full_none",
}


def marker(query: str) -> str:
    match = MARKER_RE.search(query)
    if not match:
        raise ValueError(f"numeric trace query has no marker: {query!r}")
    return match.group("marker")


def finite_positive(value: float) -> bool:
    return math.isfinite(value) and value > 0.0


def parse_trace(stderr: str) -> tuple[dict[str, list[dict]], dict[str, list[dict]], dict[str, list[dict]]]:
    base: dict[str, list[dict]] = {}
    mcv: dict[str, list[dict]] = {}
    selected: dict[str, list[dict]] = {}
    for line in stderr.splitlines():
        base_match = BASE_RE.search(line)
        if base_match:
            data = base_match.groupdict()
            item = {
                "base_relation_oid": int(data["oid"]),
                "rte_index": int(data["rte"]),
                "R": float(data["R"]),
                "selectivity_preclamp": float(data["sel"]),
                "nrows_preclamp": float(data["nrows"]),
                "rows_postclamp": float(data["rows"]),
                "query": data["query"],
            }
            base.setdefault(marker(data["query"]), []).append(item)
            continue
        mcv_match = MCV_RE.search(line)
        if mcv_match:
            data = mcv_match.groupdict()
            item = {
                "base_relation_oid": int(data["oid"]),
                "selected_stat_oid": int(data["stat"]),
                "stat_clause_count": int(data["count"]),
                "simple_sel": float(data["simple"]),
                "mcv_sel": float(data["mcv"]),
                "mcv_basesel": float(data["base"]),
                "mcv_totalsel": float(data["total"]),
                "stat_sel": float(data["stat_sel"]),
                "query": data["query"],
            }
            mcv.setdefault(marker(data["query"]), []).append(item)
            continue
        selected_match = SELECTED_RE.search(line)
        if selected_match:
            data = selected_match.groupdict()
            query_match = re.search(r"query=(.*)$", line)
            # Existing ESS_MCV_TRACE does not carry query text.  The psql
            # source line and OIDs are retained separately for auditability.
            selected.setdefault("unscoped", []).append(
                {
                    "base_relation_oid": int(data["oid"]),
                    "selected_stat_oid": int(data["stat"]),
                    "raw_line": line,
                    "query": query_match.group(1) if query_match else None,
                }
            )
    return base, mcv, selected


def parse_plan_rows(stdout: str) -> dict[str, int]:
    current: str | None = None
    result: dict[str, int] = {}
    for line in stdout.splitlines():
        marker_match = re.search(r"=== (?:measurement|scenario):([A-Za-z0-9_]+) ===", line)
        if marker_match:
            current = SCENARIO_TO_MEASUREMENT.get(
                marker_match.group(1), marker_match.group(1)
            )
            continue
        if current is not None:
            rows_match = ROWS_RE.search(line)
            if rows_match:
                result[current] = int(rows_match.group("rows"))
                current = None
    return result


def one_base(base: dict[str, list[dict]], key: str) -> dict:
    values = base.get(key, [])
    if len(values) != 1:
        raise ValueError(f"expected one base trace for {key}, got {len(values)}")
    return values[0]


def raw_selectivity(observation: dict) -> float:
    return observation["nrows_preclamp"] / observation["R"]


def compare(actual: float, predicted: float) -> dict:
    absolute = actual - predicted
    relative = absolute / actual if actual != 0.0 else None
    log_residual = (
        math.log(actual) - math.log(predicted)
        if finite_positive(actual) and finite_positive(predicted)
        else None
    )
    return {
        "actual": actual,
        "predicted": predicted,
        "absolute_deviation": absolute,
        "relative_deviation": relative,
        "log_residual": log_residual,
        "finite_positive_actual": finite_positive(actual),
        "finite_positive_predicted": finite_positive(predicted),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdout", type=Path, required=True)
    parser.add_argument("--stderr", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    stdout = args.stdout.read_text(encoding="utf-8")
    stderr = args.stderr.read_text(encoding="utf-8")
    base, mcv, selected = parse_trace(stderr)
    plan_rows = parse_plan_rows(stdout)

    required = [
        "single_a", "single_b", "single_c", "single_d",
        "pair_ab", "pair_bc", "pair_cd", "full_all",
        "full_only_bc", "full_only_ab", "full_only_cd", "full_none",
        "single_a_rare", "pair_ab_rare",
    ]
    missing = sorted(set(required) - set(base))
    if missing:
        raise ValueError(f"missing base traces: {missing}")

    singles = {name[-1]: raw_selectivity(one_base(base, f"single_{name[-1]}")) for name in "abcd"}
    pairs = {name[5:]: raw_selectivity(one_base(base, name)) for name in ("pair_ab", "pair_bc", "pair_cd")}
    R = one_base(base, "full_all")["R"]
    R_values = {item["R"] for values in base.values() for item in values}

    pair_mcv_checks = {}
    for name in ("pair_ab", "pair_bc", "pair_cd"):
        values = mcv.get(name, [])
        if len(values) != 1:
            raise ValueError(f"expected one MCV numeric trace for {name}, got {len(values)}")
        pair_mcv_checks[name] = {
            "raw_selectivity": pairs[name[5:]],
            "stat_sel": values[0]["stat_sel"],
            "residual": pairs[name[5:]] - values[0]["stat_sel"],
            "trace": values[0],
        }

    predicted = {
        "full_all": pairs["ab"] * pairs["cd"],
        "full_only_bc": pairs["bc"] * singles["a"] * singles["d"],
        "full_only_ab": pairs["ab"] * singles["c"] * singles["d"],
        "full_only_cd": pairs["cd"] * singles["a"] * singles["b"],
        "full_none": math.prod(singles.values()),
    }
    actual = {name: raw_selectivity(one_base(base, name)) for name in predicted}
    comparisons = {name: compare(actual[name], predicted[name]) for name in predicted}

    raw_rows = {
        name: {
            "actual": one_base(base, name)["nrows_preclamp"],
            "predicted": R * predicted[name],
            "relative_deviation": (
                (one_base(base, name)["nrows_preclamp"] - R * predicted[name])
                / one_base(base, name)["nrows_preclamp"]
            ),
            "plan_rows": one_base(base, name)["rows_postclamp"],
            "explain_rows": plan_rows.get(name),
        }
        for name in predicted
    }

    positivity = {
        "ordinary": {key: finite_positive(value) for key, value in singles.items()},
        "pairs": {key: finite_positive(value) for key, value in pairs.items()},
        "rare_single_a": raw_selectivity(one_base(base, "single_a_rare")),
        "rare_pair_ab": raw_selectivity(one_base(base, "pair_ab_rare")),
    }

    correction_factors = {
        name: pairs[name] / (singles[name[0]] * singles[name[1]])
        if finite_positive(pairs[name])
        and finite_positive(singles[name[0]])
        and finite_positive(singles[name[1]])
        else None
        for name in pairs
    }

    output = {
        "source": "pre-clamp ESS_MCV_NUMERIC_TRACE observations",
        "relation_multiplier_values": sorted(R_values),
        "common_relation_multiplier": len(R_values) == 1,
        "single_raw_selectivities": singles,
        "pair_raw_selectivities": pairs,
        "singleton_product_correction_factors": correction_factors,
        "selected_statistics_by_marker": {
            key: [item["selected_stat_oid"] for item in values]
            for key, values in sorted(mcv.items())
        },
        "mcv_numeric_traces": mcv,
        "pair_mcv_combine_checks": pair_mcv_checks,
        "full_scenario_comparisons": comparisons,
        "full_scenario_raw_rows": raw_rows,
        "plan_rows": plan_rows,
        "positivity": positivity,
        "base_trace_counts": {key: len(value) for key, value in sorted(base.items())},
        "mcv_trace_counts": {key: len(value) for key, value in sorted(mcv.items())},
        "existing_selection_trace_lines": selected["unscoped"],
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
