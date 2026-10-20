"""Create bounded summaries from the raw Issue #38 held-out run."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter, defaultdict
from collections.abc import Iterable
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as stream:
        return [json.loads(line) for line in stream if line.strip()]


def fmt(value: Decimal) -> str:
    return format(value, "f")


def metric(values: Iterable[Decimal]) -> dict[str, Any]:
    ordered = sorted(values)
    if not ordered:
        return {"count": 0}
    count = len(ordered)
    with localcontext() as context:
        context.prec = 60
        mean = sum(ordered, Decimal(0)) / Decimal(count)
        middle = (ordered[(count - 1) // 2] + ordered[count // 2]) / Decimal(2)
        rank = max(1, math.ceil(0.90 * count))
        p90 = ordered[rank - 1]
    return {
        "count": count,
        "mean": fmt(mean),
        "median": fmt(middle),
        "p90_nearest_rank_ceiling": fmt(p90),
        "max": fmt(ordered[-1]),
    }


def signed_counts(rows: list[dict[str, Any]]) -> dict[str, int]:
    result = Counter()
    for row in rows:
        value = Decimal(row["signed_estimate_minus_T"])
        result["underestimate"] += int(value < 0)
        result["exact"] += int(value == 0)
        result["overestimate"] += int(value > 0)
    return dict(result)


def delta_metric(values: list[Decimal]) -> dict[str, Any]:
    result = metric(values)
    result["benefit_negative_delta"] = sum(value < 0 for value in values)
    result["tie_zero_delta"] = sum(value == 0 for value in values)
    result["harm_positive_delta"] = sum(value > 0 for value in values)
    return result


def query_level_paired_delta(
    rows: list[dict[str, Any]], baseline_rows: list[dict[str, Any]], value_key: str
) -> dict[str, Any]:
    """Summarize paired deltas after averaging the fixed repetitions per query ID."""
    values = {
        (row["query_id"], row["repetition"]): Decimal(row[value_key])
        for row in rows
    }
    baseline = {
        (row["query_id"], row["repetition"]): Decimal(row[value_key])
        for row in baseline_rows
    }
    query_ids = sorted({row["query_id"] for row in rows})
    if set(values) != set(baseline):
        raise ValueError("paired rows do not have matching query/repetition keys")
    repetitions_by_query = {
        query_id: sorted(repetition for current_query, repetition in values if current_query == query_id)
        for query_id in query_ids
    }
    if any(len(repetitions) != 2 for repetitions in repetitions_by_query.values()):
        raise ValueError("query-level paired summary requires exactly two repetitions per query")
    per_query: list[tuple[Decimal, str, Decimal]] = []
    repeat_spreads: list[Decimal] = []
    for query_id in query_ids:
        repetitions = repetitions_by_query[query_id]
        deltas = [
            values[(query_id, repetition)] - baseline[(query_id, repetition)]
            for repetition in repetitions
        ]
        per_query.append((sum(deltas, Decimal(0)) / Decimal(len(deltas)), query_id, max(deltas) - min(deltas)))
        repeat_spreads.append(abs(deltas[0] - deltas[1]))
    ordered_harms = sorted(per_query, reverse=True)[:3]
    ordered_benefits = sorted(per_query)[:3]
    return {
        "aggregation": "mean of the two repetition-level deltas per query ID",
        "independent_query_count": len(per_query),
        "delta_abs_log_error": delta_metric([item[0] for item in per_query]),
        "within_query_repeat_delta_spread": metric(repeat_spreads),
        "largest_query_level_harms": [
            {"delta": fmt(item[0]), "query_id": item[1]}
            for item in ordered_harms
        ],
        "largest_query_level_benefits": [
            {"delta": fmt(item[0]), "query_id": item[1]}
            for item in ordered_benefits
        ],
    }


def set_aliases(protocol: dict[str, Any], selected: tuple[str, ...]) -> list[dict[str, Any]]:
    aliases: list[dict[str, Any]] = []
    for budget, by_method in protocol["reference_issue23"]["frozen_selection_sets"]["by_budget_and_method"].items():
        for method, value in by_method.items():
            if tuple(value["selected"]) == selected:
                aliases.append({"budget": budget, "method": method, "tie_count": value["tie_count"]})
    return aliases


def setup_payload(setup: dict[str, Any]) -> dict[str, Any]:
    stats: list[dict[str, Any]] = []
    for line in setup["catalog"]["statistics"]:
        fields = line.split("|")
        if len(fields) != 6:
            continue
        stats.append(
            {
                "oid": fields[0],
                "name": fields[1],
                "keys": fields[2],
                "target": fields[3],
                "mcv_payload_present": fields[4] in {"f", "false"},
                "mcv_bytes": int(fields[5]),
                "mcv_item_count": setup["catalog"]["mcv_item_counts"].get(fields[1], 0),
            }
        )
    return {
        "set_id": setup["set_id"],
        "repetition": setup["repetition"],
        "selected": setup["selected"],
        "table_identity": setup["catalog"]["table"],
        "statistics": stats,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--model-evidence", type=Path, required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads(args.protocol.read_text(encoding="utf-8"))
    evidence = json.loads(args.model_evidence.read_text(encoding="utf-8"))
    summary_raw = json.loads((args.raw_dir / "raw-run-summary.json").read_text(encoding="utf-8"))
    setups = load_jsonl(args.raw_dir / "setups.jsonl")
    measurements = load_jsonl(args.raw_dir / "measurements.jsonl")
    if not summary_raw["all_measurements_valid"]:
        raise ValueError("raw run is not fully valid")
    if len(measurements) != 1200 or len(setups) != 20:
        raise ValueError("unexpected raw row counts")
    if any(row.get("status") != "valid" for row in measurements):
        raise ValueError("invalid measurement in raw JSONL")

    by_set: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in measurements:
        by_set[row["set_id"]].append(row)
    setup_by_set: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in setups:
        setup_by_set[row["set_id"]].append(row)
    empty_id = "set-00-empty"
    query_truth = {row["query_id"]: row["truth_N"] for row in measurements}
    selected_query_ids = sorted(query_truth)
    top_tail_ids = sorted(selected_query_ids, key=lambda query_id: (-query_truth[query_id], query_id))[: math.ceil(0.10 * len(selected_query_ids))]
    tail_set = set(top_tail_ids)

    set_summaries: list[dict[str, Any]] = []
    for set_id in sorted(by_set):
        rows = by_set[set_id]
        selected = tuple(rows[0]["selected_resource_ids"])
        errors = [Decimal(row["absolute_log_error"]) for row in rows]
        zero_truth = [row for row in rows if row["truth_N"] == 0]
        tail_rows = [row for row in rows if row["query_id"] in tail_set]
        selected_counts = Counter(
            candidate
            for row in rows
            for candidate in row["selected_resource_ids_from_trace"]
        )
        by_query_rep = {(row["query_id"], row["repetition"]): row for row in rows}
        repetition_pairs = [
            (by_query_rep[(query_id, 0)], by_query_rep[(query_id, 1)])
            for query_id in sorted({row["query_id"] for row in rows})
        ]
        repetition_error_deltas = [
            abs(Decimal(first["absolute_log_error"]) - Decimal(second["absolute_log_error"]))
            for first, second in repetition_pairs
        ]
        repetition_selection_changes = sum(
            first["selected_resource_ids_from_trace"] != second["selected_resource_ids_from_trace"]
            for first, second in repetition_pairs
        )
        set_summaries.append(
            {
                "set_id": set_id,
                "selected": list(selected),
                "maintenance_proxy_units": len(selected),
                "issue23_aliases": set_aliases(protocol, selected),
                "measurement_count": len(rows),
                "absolute_log_error": metric(errors),
                "signed_direction_counts": signed_counts(rows),
                "zero_truth": {"count": len(zero_truth), "absolute_log_error": metric([Decimal(row["absolute_log_error"]) for row in zero_truth])},
                "tail_true_N_top_decile": {"query_ids": top_tail_ids, "absolute_log_error": metric([Decimal(row["absolute_log_error"]) for row in tail_rows])},
                "trace_selected_candidate_counts": dict(sorted(selected_counts.items())),
                "trace_selected_query_count": sum(bool(row["selected_resource_ids_from_trace"]) for row in rows),
                "repetition_instability": {
                    "query_pair_count": len(repetition_pairs),
                    "absolute_log_error_delta": metric(repetition_error_deltas),
                    "trace_selection_changed_query_count": repetition_selection_changes,
                },
                "catalog_snapshots": [setup_payload(row) for row in setup_by_set[set_id]],
            }
        )

    empty_rows = {(row["repetition"], row["query_id"]): Decimal(row["absolute_log_error"]) for row in by_set[empty_id]}
    paired_empty: list[dict[str, Any]] = []
    for set_id in sorted(by_set):
        if set_id == empty_id:
            continue
        rows = by_set[set_id]
        deltas = [Decimal(row["absolute_log_error"]) - empty_rows[(row["repetition"], row["query_id"])] for row in rows]
        selected = tuple(rows[0]["selected_resource_ids"])
        worst_harm = sorted(
            (
                (delta, row["query_id"], row["repetition"], Decimal(row["absolute_log_error"]), empty_rows[(row["repetition"], row["query_id"])])
                for delta, row in zip(deltas, rows)
            ),
            reverse=True,
        )[:3]
        best_gain = sorted(
            (
                (delta, row["query_id"], row["repetition"], Decimal(row["absolute_log_error"]), empty_rows[(row["repetition"], row["query_id"])])
                for delta, row in zip(deltas, rows)
            )
        )[:3]
        paired_empty.append(
            {
                "set_id": set_id,
                "selected": list(selected),
                "issue23_aliases": set_aliases(protocol, selected),
                "delta_abs_log_error_vs_empty": delta_metric(deltas),
                "query_level_paired_delta_vs_empty": query_level_paired_delta(
                    rows, by_set[empty_id], "absolute_log_error"
                ),
                "largest_harms": [
                    {"delta": fmt(item[0]), "query_id": item[1], "repetition": item[2], "set_error": fmt(item[3]), "empty_error": fmt(item[4])}
                    for item in worst_harm
                ],
                "largest_benefits": [
                    {"delta": fmt(item[0]), "query_id": item[1], "repetition": item[2], "set_error": fmt(item[3]), "empty_error": fmt(item[4])}
                    for item in best_gain
                ],
            }
        )

    nominal = ("e12", "e23", "e34")
    nominal_id = next((row["set_id"] for row in set_summaries if tuple(row["selected"]) == nominal), None)
    paired_nominal: list[dict[str, Any]] = []
    if nominal_id is not None:
        nominal_rows = {(row["repetition"], row["query_id"]): Decimal(row["absolute_log_error"]) for row in by_set[nominal_id]}
        for set_id in sorted(by_set):
            if set_id == nominal_id:
                continue
            rows = by_set[set_id]
            deltas = [Decimal(row["absolute_log_error"]) - nominal_rows[(row["repetition"], row["query_id"])] for row in rows]
            paired_nominal.append(
                {
                    "set_id": set_id,
                    "selected": rows[0]["selected_resource_ids"],
                    "delta_abs_log_error_vs_nominal": delta_metric(deltas),
                    "query_level_paired_delta_vs_nominal": query_level_paired_delta(
                        rows, by_set[nominal_id], "absolute_log_error"
                    ),
                }
            )

    model_results = []
    for row in evidence["objective_results"]:
        for method, value in row["methods"].items():
            model_results.append(
                {
                    "budget": row["budget"],
                    "method": method,
                    "selected": value["selected"],
                    "exact_objective": value["objective"],
                    "pessimistic_taskwise_bound": value["pessimistic_taskwise_bound"],
                    "max_shared_order_loss": value["max_shared_order_loss"],
                    "nominal_order_loss": value["nominal_order_loss"],
                    "tie_count": value["tie_count"],
                }
            )
    failed_attempt = args.raw_dir.parent / "heldout-v1"
    failed_attempt_log = args.raw_dir.parent.parent / "logs" / "heldout-run.stdout"
    result = {
        "format": "ess-issue38-forest10-heldout-summary-v1",
        "evidence_label": "experimentally_observed_author_reported_local_postgresql_measurement",
        "protocol_sha256": sha256_file(args.protocol),
        "raw_run_summary": summary_raw,
        "raw_files": {
            "runtime_manifest_sha256": summary_raw["runtime_manifest_sha256"],
            "setups_sha256": summary_raw["setups_sha256"],
            "measurements_sha256": summary_raw["measurements_sha256"],
        },
        "cohort": {
            "selected_query_count": len(selected_query_ids),
            "measurement_count": len(measurements),
            "repetitions": 2,
            "zero_truth_measurement_count": sum(row["truth_N"] == 0 for row in measurements),
            "zero_truth_query_ids": sorted(query_id for query_id, truth in query_truth.items() if truth == 0),
            "tail_rule": "six query IDs with largest true N; ties by query_id",
            "tail_query_ids": top_tail_ids,
            "truth_cardinality_min": min(query_truth.values()),
            "truth_cardinality_max": max(query_truth.values()),
        },
        "set_summaries": set_summaries,
        "paired_vs_empty": paired_empty,
        "paired_vs_nominal_e12_e23_e34": paired_nominal,
        "issue23_model_layer_separate": {
            "evidence_sha256": sha256_file(args.model_evidence),
            "status": evidence["evidence_label"],
            "results": model_results,
            "interpretation": "exact Fraction/rationalized measured-input model certificates on six valid selection tasks; not held-out PostgreSQL test outcomes",
        },
        "failed_harness_attempt_preserved": {
            "path": str(failed_attempt),
            "partial_measurement_count": 120,
            "cause": "catalog row parser used the complete pipe-delimited tail instead of the statistics name; stopped before non-empty-set outcome collection",
            "stdout_sha256": sha256_file(failed_attempt_log) if failed_attempt_log.is_file() else None,
        },
        "limitations": [
            "The 60-query cohort is deterministic and held out from Issue #23 selection, but is a bounded syntax/coverage cohort, not population-level generalization.",
            "The PostgreSQL build is instrumented ess-postgresql 16.14, not pristine upstream PostgreSQL.",
            "Pre-clamp values are numeric trace outputs; Plan Rows are recorded only as secondary values and latency was not measured.",
            "The unordered resource sets were instantiated in frozen candidate-ID creation order; this is an evaluation construction, not a claim that all catalog orders are physically realized.",
            "The descriptive PG observations do not establish real possible-scheme containment by the prescribed maximal-matching family and do not support universal PESS dominance.",
            "The additive one-unit resource cost remains a proxy and no physical maintenance benefit is claimed.",
        ],
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": sha256_file(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
