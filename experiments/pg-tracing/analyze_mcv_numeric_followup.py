#!/usr/bin/env python3
"""Strict acceptance checks for the Issue #5 numeric follow-up fixtures.

The checker consumes the unmodified psql stdout/stderr.  It reconstructs the
PostgreSQL ``mcv_combine_selectivities`` remainder formula from the numeric
trace, checks selection/OID/clause provenance, and reconstructs full-query raw
selectivities from separately measured singleton and pair observations.
Failures raise a non-zero exit status; no rounded EXPLAIN row is used as a
selectivity factor.
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path


ABS_TOL = 1e-15
REL_TOL = 1e-12
HETEROGENEITY_THRESHOLD = 0.1

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
TERMINATED_RE = re.compile(r"ESS_MCV_TRACE: relid=(?P<oid>\d+) candidate=none")
MARKER_RE = re.compile(r"ESS_MCV_NUMERIC_TRACE:(?P<marker>[A-Za-z0-9_]+)")
ROWS_RE = re.compile(r"\brows=(?P<rows>\d+)\b")
CATALOG_RE = re.compile(
    r"^\s*(?P<name>ess_(?:partial|hetero)_(?:ab|bc|cd))\s*\|\s*"
    r"(?P<oid>\d+)\s*\|\s*(?P<keys>[0-9 ]+)\s*\|\s*\{m\}\s*\|\s*"
    r"(?P<target>\d+)\s*\|\s*(?P<built>[tf])\s*\|\s*(?P<bytes>\d+)\s*$"
)
COUNT_RE = re.compile(
    r"^\s*(?P<marker>(?:partial|hetero)_(?:only_bc|only_ab|only_cd|none)_catalog_count)"
    r"\s*\|\s*(?P<count>\d+)\s*$"
)
HEADING_RE = re.compile(r"^=== (?P<fixture>partial|heterogeneous):(?P<name>[A-Za-z0-9_]+) ===$")


def marker(query: str) -> str:
    match = MARKER_RE.search(query)
    if not match:
        raise ValueError(f"numeric trace query has no marker: {query!r}")
    return match.group("marker")


def close(actual: float, expected: float) -> bool:
    return math.isclose(actual, expected, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def finite_positive(value: float) -> bool:
    return math.isfinite(value) and value > 0.0


def clamp_probability(value: float) -> float:
    # CLAMP_PROBABILITY in PostgreSQL clamps to [0, 1].
    return min(1.0, max(0.0, value))


def combine_from_trace(trace: dict) -> dict:
    remainder_before_clamp = trace["simple_sel"] - trace["mcv_basesel"]
    other_sel = clamp_probability(remainder_before_clamp)
    cap = 1.0 - trace["mcv_totalsel"]
    if other_sel > cap:
        other_sel = cap
    reconstructed = clamp_probability(trace["mcv_sel"] + other_sel)
    if not close(reconstructed, trace["stat_sel"]):
        raise ValueError(
            "mcv_combine_selectivities mismatch for "
            f"{trace['marker']}: reconstructed={reconstructed!r}, "
            f"trace={trace['stat_sel']!r}"
        )
    trace = dict(trace)
    trace["other_sel_before_clamp"] = remainder_before_clamp
    trace["other_sel"] = other_sel
    trace["other_sel_cap"] = cap
    trace["stat_sel_reconstructed"] = reconstructed
    return trace


def parse_logs(stdout: str, stderr: str) -> tuple[dict, dict, dict, dict]:
    base: dict[str, list[dict]] = {}
    mcv: dict[str, list[dict]] = {}
    catalog: dict[str, dict] = {}
    rollback_counts: dict[str, int] = {}
    plan_rows: dict[str, list[int]] = {}
    selection_events: dict[str, list[dict]] = {}
    pending: list[dict] = []

    for line in stderr.splitlines():
        selected = SELECTED_RE.search(line)
        claimed = CLAIMED_RE.search(line)
        terminated = TERMINATED_RE.search(line)
        if claimed:
            data = claimed.groupdict()
            pending.append(
                {
                    "event": "claimed_clause",
                    "base_relation_oid": int(data["oid"]),
                    "selected_stat_oid": int(data["stat"]),
                    "clause_index": int(data["idx"]),
                    "raw_line": line,
                }
            )
            continue
        if selected:
            data = selected.groupdict()
            pending.append(
                {
                    "event": "selected_stat",
                    "base_relation_oid": int(data["oid"]),
                    "selected_stat_oid": int(data["stat"]),
                    "raw_line": line,
                }
            )
            continue
        if terminated:
            pending.append({"event": "terminated", "raw_line": line})
            continue

        numeric = MCV_RE.search(line)
        if numeric:
            data = numeric.groupdict()
            item = {
                "marker": marker(data["query"]),
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
            mcv.setdefault(item["marker"], []).append(item)
            continue

        base_match = BASE_RE.search(line)
        if base_match:
            data = base_match.groupdict()
            item = {
                "marker": marker(data["query"]),
                "base_relation_oid": int(data["oid"]),
                "rte_index": int(data["rte"]),
                "R": float(data["R"]),
                "selectivity_preclamp": float(data["sel"]),
                "nrows_preclamp": float(data["nrows"]),
                "rows_postclamp": float(data["rows"]),
                "query": data["query"],
            }
            base.setdefault(item["marker"], []).append(item)
            selection_events[item["marker"]] = pending
            pending = []

    current_plan_marker: str | None = None
    scenario_names = {
        "scenario_only_bc": "full_only_bc",
        "scenario_only_ab": "full_only_ab",
        "scenario_only_cd": "full_only_cd",
        "scenario_none": "full_none",
    }
    for line in stdout.splitlines():
        heading = HEADING_RE.match(line)
        if heading:
            fixture = "hetero" if heading.group("fixture") == "heterogeneous" else heading.group("fixture")
            name = scenario_names.get(heading.group("name"), heading.group("name"))
            current_plan_marker = None if name == "snapshot" else f"{fixture}_{name}"
            continue
        if current_plan_marker is not None:
            rows_match = ROWS_RE.search(line)
            if rows_match:
                plan_rows.setdefault(current_plan_marker, []).append(int(rows_match.group("rows")))
                continue
        catalog_match = CATALOG_RE.match(line)
        if catalog_match:
            data = catalog_match.groupdict()
            catalog[data["name"]] = {
                "statistic_oid": int(data["oid"]),
                "keys": data["keys"].strip().split(),
                "target": int(data["target"]),
                "built_mcv": data["built"] == "t",
                "mcv_bytes": int(data["bytes"]),
            }
            continue
        count_match = COUNT_RE.match(line)
        if count_match:
            data = count_match.groupdict()
            rollback_counts[data["marker"]] = int(data["count"])

    return base, mcv, catalog, {
        "selection_events": selection_events,
        "rollback_counts": rollback_counts,
        "plan_rows": plan_rows,
    }


def one(mapping: dict[str, list[dict]], key: str) -> dict:
    values = mapping.get(key, [])
    if len(values) != 1:
        raise ValueError(f"expected exactly one trace for {key}, got {len(values)}")
    return values[0]


def raw_sel(observation: dict) -> float:
    return observation["nrows_preclamp"] / observation["R"]


def expected_plan_rows(value: float) -> int:
    # All follow-up values are far from half-integer ties.  Python's round is
    # ties-to-even, matching the default FE_TONEAREST rint mode here.
    return 1 if value <= 1.0 else int(round(value))


def check_fixture(prefix: str, base: dict, mcv: dict, catalog: dict,
                  metadata: dict) -> dict:
    expected_stats = {
        f"ess_{prefix}_ab": ("1", "2"),
        f"ess_{prefix}_bc": ("2", "3"),
        f"ess_{prefix}_cd": ("3", "4"),
    }
    for name, keys in expected_stats.items():
        if name not in catalog:
            raise ValueError(f"{prefix}: missing catalog row {name}")
        row = catalog[name]
        if tuple(row["keys"]) != keys or not row["built_mcv"] or row["mcv_bytes"] <= 0:
            raise ValueError(f"{prefix}: invalid catalog row {name}: {row}")

    required = [
        f"{prefix}_single_a", f"{prefix}_single_b", f"{prefix}_single_c", f"{prefix}_single_d",
        f"{prefix}_pair_ab" + ("_mcv" if prefix == "partial" else ""),
        *([f"{prefix}_pair_ab_nonmcv"] if prefix == "partial" else []),
        f"{prefix}_pair_bc", f"{prefix}_pair_cd", f"{prefix}_full_all",
        f"{prefix}_full_only_bc", f"{prefix}_full_only_ab", f"{prefix}_full_only_cd",
        f"{prefix}_full_none",
    ]
    for key in required:
        one(base, key)

    expected_plan_markers = set(required)
    actual_plan_markers = {
        key for key in metadata["plan_rows"] if key.startswith(prefix + "_")
    }
    if actual_plan_markers != expected_plan_markers:
        raise ValueError(
            f"{prefix}: expected exactly one EXPLAIN Plan Rows marker for each "
            f"measurement; missing={sorted(expected_plan_markers - actual_plan_markers)}, "
            f"unexpected={sorted(actual_plan_markers - expected_plan_markers)}"
        )
    for key in required:
        values = metadata["plan_rows"].get(key, [])
        if len(values) != 1:
            raise ValueError(f"{prefix}: expected one EXPLAIN Plan Rows value for {key}, got {values}")
        observation = one(base, key)
        expected_rows = expected_plan_rows(observation["nrows_preclamp"])
        if values[0] != expected_rows or values[0] != int(observation["rows_postclamp"]):
            raise ValueError(
                f"{prefix}: EXPLAIN Plan Rows mismatch for {key}: stdout={values[0]}, "
                f"trace={observation['rows_postclamp']}, predicted={expected_rows}"
            )

    all_base = [
        item
        for key, values in base.items()
        if key.startswith(prefix + "_")
        for item in values
    ]
    R_values = sorted({item["R"] for item in all_base})
    if len(R_values) != 1 or not finite_positive(R_values[0]):
        raise ValueError(f"{prefix}: inconsistent relation multiplier values {R_values}")
    relation_oid_values = {item["base_relation_oid"] for item in all_base}
    if len(relation_oid_values) != 1:
        raise ValueError(f"{prefix}: inconsistent relation OIDs {relation_oid_values}")

    expected_oids = {suffix: catalog[f"ess_{prefix}_{suffix}"]["statistic_oid"] for suffix in ("ab", "bc", "cd")}
    expected_selection = {
        f"{prefix}_pair_ab" + ("_mcv" if prefix == "partial" else ""): ([expected_oids["ab"]], [0, 1]),
        f"{prefix}_pair_bc": ([expected_oids["bc"]], [0, 1]),
        f"{prefix}_pair_cd": ([expected_oids["cd"]], [0, 1]),
        f"{prefix}_full_all": ([expected_oids["ab"], expected_oids["cd"]], [0, 1, 2, 3]),
        f"{prefix}_full_only_bc": ([expected_oids["bc"]], [1, 2]),
        f"{prefix}_full_only_ab": ([expected_oids["ab"]], [0, 1]),
        f"{prefix}_full_only_cd": ([expected_oids["cd"]], [2, 3]),
        f"{prefix}_full_none": ([], []),
    }
    selection_summary = {}
    for key, (oids, clauses) in expected_selection.items():
        events = metadata["selection_events"].get(key, [])
        selected = [e["selected_stat_oid"] for e in events if e["event"] == "selected_stat"]
        consumed = [e["clause_index"] for e in events if e["event"] == "claimed_clause"]
        termination_required = bool(oids) or bool(events)
        if (
            selected != oids
            or consumed != clauses
            or (termination_required and not any(e["event"] == "terminated" for e in events))
        ):
            raise ValueError(
                f"{prefix}: unexpected selection trace for {key}: "
                f"selected={selected}, clauses={consumed}, events={events}"
            )
        selection_summary[key] = {"selected_stat_oids": selected, "claimed_clause_indices": consumed}

    expected_mcv_counts = {
        f"{prefix}_pair_ab" + ("_mcv" if prefix == "partial" else ""): 1,
        f"{prefix}_pair_bc": 1,
        f"{prefix}_pair_cd": 1,
        f"{prefix}_full_all": 2,
        f"{prefix}_full_only_bc": 1,
        f"{prefix}_full_only_ab": 1,
        f"{prefix}_full_only_cd": 1,
    }
    if prefix == "partial":
        expected_mcv_counts[f"{prefix}_pair_ab_nonmcv"] = 1
    actual_mcv_keys = {key for key in mcv if key.startswith(prefix + "_")}
    if actual_mcv_keys != set(expected_mcv_counts):
        raise ValueError(
            f"{prefix}: numeric MCV marker set mismatch; "
            f"missing={sorted(set(expected_mcv_counts) - actual_mcv_keys)}, "
            f"unexpected={sorted(actual_mcv_keys - set(expected_mcv_counts))}"
        )

    reconstructed_mcv = {}
    for key, expected_count in expected_mcv_counts.items():
        values = mcv.get(key, [])
        if len(values) != expected_count:
            raise ValueError(
                f"{prefix}: expected {expected_count} MCV numeric traces for {key}, got {len(values)}"
            )
        reconstructed_mcv[key] = [combine_from_trace({**value}) for value in values]

    for key, traces in reconstructed_mcv.items():
        for trace in traces:
            if not close(trace["stat_sel"], trace["stat_sel_reconstructed"]):
                raise ValueError(f"{prefix}: failed combine reconstruction {key}")

    if prefix == "partial":
        partial_trace = reconstructed_mcv[f"{prefix}_pair_ab_mcv"][0]
        if not (0.0 < partial_trace["mcv_totalsel"] < 1.0):
            raise ValueError(f"partial: mcv_totalsel is not partial: {partial_trace}")
        remainder_trace = reconstructed_mcv[f"{prefix}_pair_ab_nonmcv"][0]
        if not (0.0 < remainder_trace["other_sel"] < 1.0):
            raise ValueError(f"partial: non-MCV remainder was not exercised: {remainder_trace}")
        if remainder_trace["mcv_sel"] != 0.0 or remainder_trace["mcv_basesel"] != 0.0:
            raise ValueError(f"partial: non-MCV trace unexpectedly matches MCV: {remainder_trace}")

    singles = {
        name: raw_sel(one(base, f"{prefix}_single_{name}")) for name in "abcd"
    }
    pair_names = {
        "ab": f"{prefix}_pair_ab_mcv" if prefix == "partial" else f"{prefix}_pair_ab",
        "bc": f"{prefix}_pair_bc",
        "cd": f"{prefix}_pair_cd",
    }
    pairs = {name: raw_sel(one(base, key)) for name, key in pair_names.items()}
    full_names = {
        "full_all": f"{prefix}_full_all",
        "full_only_bc": f"{prefix}_full_only_bc",
        "full_only_ab": f"{prefix}_full_only_ab",
        "full_only_cd": f"{prefix}_full_only_cd",
        "full_none": f"{prefix}_full_none",
    }
    predictions = {
        "full_all": pairs["ab"] * pairs["cd"],
        "full_only_bc": pairs["bc"] * singles["a"] * singles["d"],
        "full_only_ab": pairs["ab"] * singles["c"] * singles["d"],
        "full_only_cd": pairs["cd"] * singles["a"] * singles["b"],
        "full_none": math.prod(singles.values()),
    }
    comparisons = {}
    for name, key in full_names.items():
        observation = one(base, key)
        actual = raw_sel(observation)
        predicted = predictions[name]
        if not close(actual, predicted):
            raise ValueError(
                f"{prefix}: raw selectivity mismatch {name}: actual={actual!r}, predicted={predicted!r}"
            )
        predicted_rows = R_values[0] * predicted
        if not close(observation["nrows_preclamp"], predicted_rows):
            raise ValueError(f"{prefix}: raw row mismatch {name}")
        if observation["rows_postclamp"] != expected_plan_rows(predicted_rows):
            raise ValueError(f"{prefix}: post-clamp row mismatch {name}")
        comparisons[name] = {
            "actual_raw_selectivity": actual,
            "predicted_raw_selectivity": predicted,
            "absolute_deviation": actual - predicted,
            "relative_deviation": (actual - predicted) / actual if actual else None,
            "actual_rows_preclamp": observation["nrows_preclamp"],
            "predicted_rows_preclamp": predicted_rows,
            "actual_rows_postclamp": observation["rows_postclamp"],
            "predicted_rows_postclamp": expected_plan_rows(predicted_rows),
            "explain_rows": observation["rows_postclamp"],
        }

    factors = {
        name: pairs[name] / (singles[name[0]] * singles[name[1]])
        for name in pairs
    }
    if not all(finite_positive(value) for value in [*singles.values(), *pairs.values(), *factors.values()]):
        raise ValueError(f"{prefix}: non-positive or non-finite positive observations")
    if prefix == "hetero" and max(factors.values()) - min(factors.values()) <= HETEROGENEITY_THRESHOLD:
        raise ValueError(f"heterogeneous: correction factors are not materially different: {factors}")

    expected_counts = {
        f"{prefix}_only_bc_catalog_count": 1,
        f"{prefix}_only_ab_catalog_count": 1,
        f"{prefix}_only_cd_catalog_count": 1,
        f"{prefix}_none_catalog_count": 0,
    }
    for key, expected in expected_counts.items():
        if metadata["rollback_counts"].get(key) != expected:
            raise ValueError(f"{prefix}: rollback catalog count mismatch for {key}")

    fixture_catalog = {
        name: row for name, row in catalog.items() if name.startswith(f"ess_{prefix}_")
    }
    return {
        "relation_oid": sorted(relation_oid_values)[0],
        "relation_multiplier_values": R_values,
        "catalog": fixture_catalog,
        "selection_trace": selection_summary,
        "mcv_numeric_traces": reconstructed_mcv,
        "single_raw_selectivities": singles,
        "pair_raw_selectivities": pairs,
        "correction_factors": factors,
        "full_scenario_comparisons": comparisons,
        "rollback_catalog_counts": {key: metadata["rollback_counts"][key] for key in expected_counts},
        "tolerance": {"relative": REL_TOL, "absolute": ABS_TOL},
        "heterogeneity_threshold_absolute": HETEROGENEITY_THRESHOLD,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stdout", type=Path, required=True)
    parser.add_argument("--stderr", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    base, mcv, catalog, metadata = parse_logs(
        args.stdout.read_text(encoding="utf-8"),
        args.stderr.read_text(encoding="utf-8"),
    )
    partial = check_fixture("partial", base, mcv, catalog, metadata)
    heterogeneous = check_fixture("hetero", base, mcv, catalog, metadata)
    output = {
        "checker": "analyze_mcv_numeric_followup.py",
        "acceptance": "passed",
        "source_formula": {
            "other_sel": "clamp(simple_sel - mcv_basesel, 0, 1); cap at 1 - mcv_totalsel",
            "stat_sel": "clamp(mcv_sel + other_sel, 0, 1)",
        },
        "fixtures": {"partial": partial, "heterogeneous": heterogeneous},
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
