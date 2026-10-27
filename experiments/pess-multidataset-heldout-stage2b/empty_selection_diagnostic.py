"""Validation-only diagnosis of the Stage 2B Empty selections.

This module intentionally reads only the frozen v4 protocol, the v4 frozen
validation model, and the v4 validation calibration ledger.  It does not open
test truth, held-out estimates, held-out summaries, or PostgreSQL traces.

The reference arithmetic for the recorded v4 model uses Fraction values.  A
separate, explicitly non-authoritative Decimal-log counterfactual is emitted
to measure the impact of the discovered coefficient implementation defect.
It is not a replacement for v4 evidence and is never used to select or run a
held-out resource set.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from collections.abc import Iterable
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
V4_RUN = HERE / "runs" / "formal-20261020-v4"
DATASETS = ("forest10", "census13")
METHODS = ("Empty", "Nominal", "PESS")
MODEL_METHODS = ("Nominal", "PESS")
BUDGETS = (0, 2, 3, 5)
PROTOCOL_SHA256 = "54867e0bf3ca116b044d77da14efe1b12d06851af522cfbeb49af14ae33733ad"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise TypeError(f"expected object in {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError(f"expected object in {path}:{line_number}")
            rows.append(value)
    return rows


def fraction_decimal(value: Fraction, places: int = 12) -> str:
    with localcontext() as context:
        context.prec = 80
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
        quantized = decimal.quantize(Decimal(1).scaleb(-places))
    return format(quantized, "f")


def decimal_string(value: Decimal, places: int = 12) -> str:
    with localcontext() as context:
        context.prec = 80
        quantized = value.quantize(Decimal(1).scaleb(-places))
    return format(quantized, "f")


def quantized_fraction(value: Decimal) -> Fraction:
    """Match the v4 rationalization, without silently taking a logarithm."""

    with localcontext() as context:
        context.prec = 80
        quantized = value.quantize(Decimal("0.000000000000000001"))
    return Fraction(str(quantized))


def log_decimal(value: Decimal) -> Decimal:
    with localcontext() as context:
        context.prec = 80
        return value.ln()


def candidate_map(protocol: dict[str, Any], dataset: str) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in protocol["datasets"][dataset]["candidates"]}


def maximal_matchings(
    available: Iterable[str], candidates: dict[str, dict[str, Any]]
) -> list[tuple[str, ...]]:
    ordered = list(available)
    result: list[tuple[str, ...]] = []

    def disjoint(left: str, right: str) -> bool:
        return set(candidates[left]["source_columns"]).isdisjoint(
            candidates[right]["source_columns"]
        )

    def recurse(index: int, selected: list[str]) -> None:
        if index == len(ordered):
            selected_set = set(selected)
            if all(
                edge in selected_set
                or any(not disjoint(edge, chosen) for chosen in selected)
                for edge in ordered
            ):
                result.append(tuple(selected))
            return
        edge = ordered[index]
        recurse(index + 1, selected)
        if all(disjoint(edge, chosen) for chosen in selected):
            selected.append(edge)
            recurse(index + 1, selected)
            selected.pop()

    recurse(0, [])
    return sorted(set(result))


def nominal_matching(
    available: Iterable[str], candidates: dict[str, dict[str, Any]]
) -> tuple[str, ...]:
    selected: list[str] = []
    for edge in available:
        endpoints = set(candidates[edge]["source_columns"])
        if all(
            endpoints.isdisjoint(candidates[chosen]["source_columns"])
            for chosen in selected
        ):
            selected.append(edge)
    return tuple(selected)


def model_loss(
    task: dict[str, Any],
    selected: tuple[str, ...],
    method: str,
    candidates: dict[str, dict[str, Any]],
) -> Fraction:
    alpha = Fraction(task["alpha"])
    b = {edge: Fraction(value) for edge, value in task["b"].items()}
    available = [edge for edge in task["available_edges"] if edge in selected]
    if method == "Empty":
        return abs(alpha)
    if method == "Nominal":
        matching = nominal_matching(available, candidates)
        return abs(alpha + sum((b[edge] for edge in matching), Fraction(0)))
    if method == "PESS":
        return max(
            abs(alpha + sum((b[edge] for edge in matching), Fraction(0)))
            for matching in maximal_matchings(available, candidates)
        )
    raise ValueError(f"unknown method: {method}")


def decimal_model_loss(
    task: dict[str, Any],
    selected: tuple[str, ...],
    method: str,
    candidates: dict[str, dict[str, Any]],
    alpha: Decimal,
    b: dict[str, Decimal],
) -> Decimal:
    available = [edge for edge in task["available_edges"] if edge in selected]
    if method == "Empty":
        return abs(alpha)
    if method == "Nominal":
        matchings = [nominal_matching(available, candidates)]
    else:
        matchings = maximal_matchings(available, candidates)
    return max(
        (abs(alpha + sum((b[edge] for edge in matching), Decimal(0))) for matching in matchings),
        default=abs(alpha),
    )


def all_resource_sets(candidate_ids: list[str], budget: int) -> list[tuple[str, ...]]:
    return [
        tuple(candidate_ids[index] for index in range(len(candidate_ids)) if mask & (1 << index))
        for mask in range(1 << len(candidate_ids))
        if mask.bit_count() <= budget
    ]


def git_head() -> str | None:
    try:
        return subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=HERE,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def input_paths() -> dict[str, Path]:
    paths = {"protocol_v4": HERE / "protocol-v4.json"}
    for dataset in DATASETS:
        paths[f"{dataset}_validation_model"] = V4_RUN / dataset / "validation-model.json"
        paths[f"{dataset}_validation_calibration_ledger"] = (
            V4_RUN / dataset / "validation-calibration-ledger.jsonl"
        )
    paths["formal_runner_source"] = HERE / "run_formal.py"
    return paths


def load_frozen_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, list[dict[str, Any]]]]:
    paths = input_paths()
    protocol = read_json(paths["protocol_v4"])
    if sha256_file(paths["protocol_v4"]) != PROTOCOL_SHA256:
        raise RuntimeError("protocol-v4.json SHA-256 changed; fail closed")
    if protocol.get("status") != "FROZEN_BEFORE_HELDOUT_OUTCOME_COLLECTION_V4":
        raise RuntimeError("protocol-v4 is not the frozen pre-held-out protocol")
    if protocol["measurement_contract"]["budgets_proxy_units"] != list(BUDGETS):
        raise RuntimeError("frozen budget list changed; fail closed")
    if protocol["measurement_contract"]["methods"] != list(METHODS):
        raise RuntimeError("frozen method list changed; fail closed")

    models: dict[str, Any] = {}
    ledgers: dict[str, list[dict[str, Any]]] = {}
    for dataset in DATASETS:
        model = read_json(paths[f"{dataset}_validation_model"])
        ledger = read_jsonl(paths[f"{dataset}_validation_calibration_ledger"])
        if model.get("protocol_sha256") != PROTOCOL_SHA256:
            raise RuntimeError(f"{dataset} model protocol SHA mismatch; fail closed")
        if model.get("dataset") != dataset:
            raise RuntimeError(f"{dataset} model dataset mismatch; fail closed")
        if any(row.get("phase") != "validation_calibration" for row in ledger):
            raise RuntimeError(f"{dataset} ledger contains a non-validation phase; fail closed")
        if any(":test:" in row.get("query_id", "") for row in ledger):
            raise RuntimeError(f"{dataset} ledger contains a test query; fail closed")
        models[dataset] = model
        ledgers[dataset] = ledger
    return protocol, models, ledgers


def coefficient_audit(
    model: dict[str, Any],
    ledger: list[dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
    validation_records: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, int], dict[str, Any]]]:
    by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in ledger:
        key = (row["query_id"], row["resource_set_id"], int(row["repetition"]))
        if key in by_key:
            raise RuntimeError(f"duplicate validation ledger key: {key}")
        by_key[key] = row

    coverage = {row["query_id"]: row for row in validation_records}
    audits = []
    for task in model["models"]:
        query_id = task["query_id"]
        if query_id not in coverage:
            raise RuntimeError(f"missing frozen validation coverage record: {query_id}")
        available = list(task["available_edges"])
        if set(available) != set(coverage[query_id]["covered_candidates"]):
            raise RuntimeError(f"model/coverage edge mismatch for {query_id}")
        baseline = by_key[(query_id, "calibration-empty", 0)]
        n0 = Decimal(baseline["estimate_preclamp"])
        if n0 <= 0:
            raise RuntimeError(f"nonpositive validation baseline for {query_id}")
        if str(n0) != task["n0_preclamp"]:
            raise RuntimeError(f"model n0 does not match validation ledger for {query_id}")
        target = max(1, int(task["true_cardinality"]))
        if target != int(task["target_T"]):
            raise RuntimeError(f"target_T mismatch for {query_id}")

        alpha_raw = n0 / Decimal(target)
        alpha_log = log_decimal(alpha_raw)
        alpha_recorded = Fraction(task["alpha"])
        alpha_v4 = quantized_fraction(alpha_raw)
        if alpha_recorded != alpha_v4:
            raise RuntimeError(f"recorded alpha is not v4-rationalized n0/T for {query_id}")
        coefficients = []
        for edge in candidates:
            row = by_key[(query_id, f"calibration-{edge}", 0)]
            estimate = Decimal(row["estimate_preclamp"])
            if estimate <= 0:
                raise RuntimeError(f"nonpositive validation estimate for {query_id}/{edge}")
            ratio = estimate / n0
            recorded = Fraction(task["b"][edge])
            v4_value = quantized_fraction(ratio)
            if recorded != v4_value:
                raise RuntimeError(f"recorded b is not v4-rationalized ne/n0 for {query_id}/{edge}")
            coefficients.append(
                {
                    "edge": edge,
                    "estimate_preclamp_rep0": str(estimate),
                    "estimate_preclamp_rep1": by_key[(query_id, f"calibration-{edge}", 1)][
                        "estimate_preclamp"
                    ],
                    "raw_ratio_ne_over_n0": str(ratio),
                    "recorded_v4_b": str(recorded),
                    "protocol_log_b": decimal_string(log_decimal(ratio)),
                    "recorded_equals_protocol_log": recorded == quantized_fraction(log_decimal(ratio)),
                    "applicable_to_task": edge in available,
                }
            )
        repeat_values = [
            by_key[(query_id, resource_set_id, 0)]["estimate_preclamp"]
            == by_key[(query_id, resource_set_id, 1)]["estimate_preclamp"]
            for resource_set_id in ["calibration-empty"]
            + [f"calibration-{edge}" for edge in candidates]
        ]
        audits.append(
            {
                "query_id": query_id,
                "source_index": task["source_index"],
                "available_edges": available,
                "covered_candidates_from_frozen_protocol": coverage[query_id]["covered_candidates"],
                "true_cardinality_recorded_in_frozen_model": task["true_cardinality"],
                "target_T": target,
                "n0_preclamp": str(n0),
                "recorded_v4_alpha": str(alpha_recorded),
                "raw_ratio_n0_over_T": str(alpha_raw),
                "protocol_log_alpha": decimal_string(alpha_log),
                "recorded_alpha_equals_protocol_log": alpha_recorded
                == quantized_fraction(alpha_log),
                "coefficients": coefficients,
                "all_repeat_estimates_identical": all(repeat_values),
                "parameter_sources": {
                    "n0_and_ne": "v4 validation-calibration-ledger.jsonl repetition 0 positive_preclamp estimates",
                    "target_T": "v4 validation-model.json recorded validation target (T=max(1,N))",
                    "recorded_alpha_b": "v4 validation-model.json",
                    "test_truth_or_heldout_estimates_read": False,
                },
            }
        )
    return audits, by_key


def task_matching_evidence(
    tasks: list[dict[str, Any]], candidates: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    evidence = []
    for task in tasks:
        available = list(task["available_edges"])
        matchings = maximal_matchings(available, candidates)
        nominal = nominal_matching(available, candidates)
        matching_losses = []
        alpha = Fraction(task["alpha"])
        b = {edge: Fraction(value) for edge, value in task["b"].items()}
        for matching in matchings:
            matching_losses.append(
                {
                    "matching": list(matching),
                    "loss": str(abs(alpha + sum((b[edge] for edge in matching), Fraction(0)))),
                    "loss_decimal": fraction_decimal(
                        abs(alpha + sum((b[edge] for edge in matching), Fraction(0)))
                    ),
                }
            )
        nominal_loss = abs(alpha + sum((b[edge] for edge in nominal), Fraction(0)))
        evidence.append(
            {
                "query_id": task["query_id"],
                "available_edges": available,
                "available_edge_endpoints": {
                    edge: candidates[edge]["source_columns"] for edge in available
                },
                "maximal_matching_count": len(matchings),
                "maximal_matchings": [list(matching) for matching in matchings],
                "nominal_matching": list(nominal),
                "nominal_loss_full_available": str(nominal_loss),
                "pess_loss_full_available": str(max(item["loss"] for item in matching_losses)),
                "matching_losses_full_available": matching_losses,
                "nominal_pess_differ": nominal_loss
                != max(abs(alpha + sum((b[edge] for edge in matching), Fraction(0))) for matching in matchings),
            }
        )
    return evidence


def rank_summary(
    rows: list[dict[str, Any]], budget: int, method: str
) -> dict[str, Any]:
    scored = sorted(
        ((Fraction(row[method.lower()]), tuple(row["selected"])) for row in rows),
        key=lambda item: (item[0], item[1]),
    )
    best = scored[0][0]
    best_sets = [list(selected) for value, selected in scored if value == best]
    runner_up = next((value for value, _ in scored if value > best), None)
    empty = next(value for value, selected in scored if not selected)
    return {
        "method": method,
        "budget": budget,
        "feasible_set_count": len(rows),
        "best_objective": str(best),
        "best_objective_decimal": fraction_decimal(best),
        "best_sets": best_sets,
        "best_tie_count": len(best_sets),
        "runner_up_objective": None if runner_up is None else str(runner_up),
        "runner_up_objective_decimal": None
        if runner_up is None
        else fraction_decimal(runner_up),
        "runner_up_gap": None if runner_up is None else str(runner_up - best),
        "runner_up_gap_decimal": None
        if runner_up is None
        else fraction_decimal(runner_up - best),
        "empty_objective": str(empty),
        "empty_objective_decimal": fraction_decimal(empty),
        "empty_gap_to_best": str(empty - best),
        "empty_gap_to_best_decimal": fraction_decimal(empty - best),
        "empty_is_strict_best": empty == best and len(best_sets) == 1,
        "empty_is_tied_best": empty == best and len(best_sets) > 1,
        "sets_strictly_better_than_empty": sum(value < empty for value, _ in scored),
        "empty_rank_with_ties": 1 + sum(value < empty for value, _ in scored),
    }


def decimal_counterfactual(
    tasks: list[dict[str, Any]],
    candidate_ids: list[str],
    candidates: dict[str, dict[str, Any]],
    ledger_by_key: dict[tuple[str, str, int], dict[str, Any]],
) -> dict[str, Any]:
    """Evaluate protocol-log coefficients without treating them as v4 evidence."""

    task_coefficients = []
    for task in tasks:
        baseline = Decimal(ledger_by_key[(task["query_id"], "calibration-empty", 0)]["estimate_preclamp"])
        target = Decimal(task["target_T"])
        alpha = log_decimal(baseline / target)
        b = {}
        for edge in candidate_ids:
            estimate = Decimal(
                ledger_by_key[(task["query_id"], f"calibration-{edge}", 0)]["estimate_preclamp"]
            )
            b[edge] = log_decimal(estimate / baseline)
        task_coefficients.append((task, alpha, b))

    output: dict[str, Any] = {
        "status": "diagnostic_only_not_v4_result",
        "arithmetic": "Decimal natural logs at precision 80; no exact Fraction certificate",
        "heldout_data_read": False,
        "budgets": {},
    }
    for budget in BUDGETS:
        sets = all_resource_sets(candidate_ids, budget)
        rows = []
        for selected in sets:
            row = {"selected": list(selected)}
            for method in MODEL_METHODS:
                row[method.lower()] = sum(
                    (
                        decimal_model_loss(task, selected, method, candidates, alpha, b)
                        for task, alpha, b in task_coefficients
                    ),
                    Decimal(0),
                )
            rows.append(row)
        summary = {}
        for method in MODEL_METHODS:
            scored = sorted(
                ((row[method.lower()], tuple(row["selected"])) for row in rows),
                key=lambda item: (item[0], item[1]),
            )
            best = scored[0][0]
            summary[method] = {
                "best_objective": decimal_string(best),
                "best_sets": [list(selected) for value, selected in scored if value == best],
                "empty_objective": decimal_string(next(value for value, selected in scored if not selected)),
            }
        output["budgets"][str(budget)] = summary
    return output


def analyze_dataset(
    dataset: str,
    protocol: dict[str, Any],
    model: dict[str, Any],
    ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates = candidate_map(protocol, dataset)
    candidate_ids = list(candidates)
    validation_records = protocol["datasets"][dataset]["validation_calibration"]["records"]
    coefficient_audits, ledger_by_key = coefficient_audit(
        model, ledger, candidates, validation_records
    )
    matching_evidence = task_matching_evidence(model["models"], candidates)
    budgets = {}
    for budget in BUDGETS:
        rows = []
        for selected in all_resource_sets(candidate_ids, budget):
            empty = sum(
                (model_loss(task, selected, "Empty", candidates) for task in model["models"]),
                Fraction(0),
            )
            nominal = sum(
                (model_loss(task, selected, "Nominal", candidates) for task in model["models"]),
                Fraction(0),
            )
            pess = sum(
                (model_loss(task, selected, "PESS", candidates) for task in model["models"]),
                Fraction(0),
            )
            rows.append(
                {
                    "selected": list(selected),
                    "cost": len(selected),
                    "empty": str(empty),
                    "empty_decimal": fraction_decimal(empty),
                    "nominal": str(nominal),
                    "nominal_decimal": fraction_decimal(nominal),
                    "pess": str(pess),
                    "pess_decimal": fraction_decimal(pess),
                    "nominal_pess_differ": nominal != pess,
                }
            )
        summaries = {method: rank_summary(rows, budget, method) for method in MODEL_METHODS}
        summaries["Empty"] = {
            "method": "Empty",
            "budget": budget,
            "feasible_set_count": 1,
            "selected": [],
            "objective": rows[0]["empty"],
            "objective_decimal": rows[0]["empty_decimal"],
            "runner_up": None,
            "selection_is_fixed_by_method": True,
        }
        frozen = {
            method: model["selected_by_method_and_budget"][method][str(budget)]
            for method in METHODS
        }
        for method in MODEL_METHODS:
            expected = summaries[method]
            actual = frozen[method]
            actual_sets = [list(item) for item in expected["best_sets"]]
            if actual["selected"] != actual_sets[0] or actual["tie_count"] != expected["best_tie_count"]:
                raise RuntimeError(f"frozen selection mismatch for {dataset}/{method}/{budget}")
        if frozen["Empty"]["selected"] != []:
            raise RuntimeError(f"frozen Empty selection mismatch for {dataset}/{budget}")
        budgets[str(budget)] = {
            "feasible_set_count": len(rows),
            "objective_rows": rows,
            "summaries": summaries,
            "frozen_v4_selection": frozen,
            "nominal_pess_different_set_count": sum(row["nominal_pess_differ"] for row in rows),
            "nominal_pess_different_sets": [
                row["selected"] for row in rows if row["nominal_pess_differ"]
            ],
        }
    return {
        "dataset": dataset,
        "candidate_ids_in_protocol_order": candidate_ids,
        "candidate_endpoints": {
            edge: candidates[edge]["source_columns"] for edge in candidate_ids
        },
        "calibration_task_count": len(model["models"]),
        "coefficient_audit": coefficient_audits,
        "matching_evidence": matching_evidence,
        "budgets": budgets,
        "correct_protocol_log_counterfactual": decimal_counterfactual(
            model["models"], candidate_ids, candidates, ledger_by_key
        ),
    }


def md_escape(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def make_report(result: dict[str, Any]) -> str:
    lines = [
        "# Stage 2B Empty-selection diagnostic",
        "",
        "> Validation-only diagnostic. It reads the frozen v4 protocol, frozen validation models, and validation calibration ledgers only. It does not read test truth, held-out estimates, held-out summaries, or PostgreSQL held-out traces.",
        "",
        "## Decision and scope",
        "",
        "**Diagnostic conclusion: INCONCLUSIVE for a protocol-conformant Stage 2B decision.** The recorded v4 model selects Empty strictly at every positive budget, but the coefficient implementation is not the frozen protocol: the protocol requires natural logs while `run_formal.py:rational_log()` only quantizes the raw ratio. The existing v4 evidence is preserved and is not reclassified or overwritten by this diagnostic.",
        "",
        "The bounded as-executed v4 physical contrast remains the historical result recorded by v4; this report does not rerun or reinterpret held-out PostgreSQL measurements. A valid protocol-level decision requires an independently reviewed implementation correction, a newly frozen validation model, and a separately authorized held-out run.",
        "",
        "## Root cause found",
        "",
        "`protocol-v4.json` defines `alpha=ln(n0/T)` and `b_e=ln(ne/n0)`. In the v4 runner, `rational_log(value)` quantizes `value` and returns it as a `Fraction`; it does not call `Decimal.ln()`. The calls at the calibration coefficient construction therefore record `n0/T` and `ne/n0`, not their logarithms. The model files also label this as natural-log rationalization, so the label and implementation disagree.",
        "",
        "This is a model implementation defect, not evidence that the candidate graph has only singleton edges or that PESS is structurally incapable of differing from Nominal. The frozen raw-ratio coefficients are all positive in these calibration tasks, and every candidate is applicable to at least one task. Consequently, adding any candidate increases at least one task-wise absolute loss; Empty is strictly optimal whenever a non-empty set is feasible.",
        "",
        "The protocol-log counterfactual in the machine-readable output is diagnostic only. It uses the same validation ledger and graph, does not read held-out data, and is not a replacement result; it shows that correcting the formula changes the resource-selection question materially.",
        "",
        "## Immutable inputs",
        "",
        f"- protocol SHA-256: `{result['provenance']['inputs']['protocol_v4']['sha256']}`",
        f"- diagnostic code commit before artifact generation: `{result['provenance']['git_head_before_artifact_generation']}`",
        f"- formal runner source SHA-256: `{result['provenance']['inputs']['formal_runner_source']['sha256']}`",
        "- recorded model arithmetic: exact `Fraction` over the values already present in v4 `validation-model.json`",
        "- held-out data read: **false**",
        "",
        "## Validation task and matching evidence",
        "",
    ]
    for dataset in DATASETS:
        data = result["datasets"][dataset]
        lines.extend([f"### {dataset}", "", "| task | applicable candidates | maximal matchings | Nominal matching |", "|---|---|---:|---|"])
        for task in data["matching_evidence"]:
            lines.append(
                "| "
                + " | ".join(
                    [
                        md_escape(task["query_id"]),
                        md_escape(", ".join(task["available_edges"])),
                        str(task["maximal_matching_count"]),
                        md_escape(", ".join(task["nominal_matching"])),
                    ]
                )
                + " |"
            )
        lines.append("")
        lines.append("Applicable-edge coefficients (recorded v4 value; protocol-log value in parentheses):")
        lines.append("")
        lines.append("| task | alpha | applicable b values | full-graph Nominal loss | full-graph PESS loss |")
        lines.append("|---|---:|---|---:|---:|")
        audit_by_id = {item["query_id"]: item for item in data["coefficient_audit"]}
        matching_by_id = {item["query_id"]: item for item in data["matching_evidence"]}
        for task_id, audit in audit_by_id.items():
            applicable = [item for item in audit["coefficients"] if item["applicable_to_task"]]
            b_text = "; ".join(
                f"{item['edge']}={item['recorded_v4_b']} ({item['protocol_log_b']})"
                for item in applicable
            )
            match = matching_by_id[task_id]
            lines.append(
                f"| {task_id} | {audit['recorded_v4_alpha']} ({audit['protocol_log_alpha']}) | {b_text} | {match['nominal_loss_full_available']} | {match['pess_loss_full_available']} |"
            )
        lines.append("")
        lines.append("## Frozen v4 objective enumeration")
        lines.append("")
        lines.append("Exact values are in `diagnostic.json`; table values are decimal renderings of the exact Fraction reference.")
        lines.append("")
        for budget in BUDGETS:
            section = data["budgets"][str(budget)]
            lines.append(f"### {dataset}, budget {budget} ({section['feasible_set_count']} feasible sets)")
            lines.append("")
            for method in METHODS:
                summary = section["summaries"][method]
                if method == "Empty":
                    lines.append(
                        f"- **Empty:** fixed set `∅`, objective `{summary['objective_decimal']}`; no alternative is feasible under the Empty method."
                    )
                else:
                    lines.append(
                        f"- **{method}:** best `{summary['best_objective_decimal']}` at `{summary['best_sets']}`; runner-up `{summary['runner_up_objective_decimal']}`; gap `{summary['runner_up_gap_decimal']}`; Empty gap-to-best `{summary['empty_gap_to_best_decimal']}`; best ties `{summary['best_tie_count']}."
                    )
            lines.append("")
            lines.append("| selected M | cost | Empty objective | Nominal objective | PESS objective | N/P differ |")
            lines.append("|---|---:|---:|---:|---:|:---:|")
            for row in section["objective_rows"]:
                selected = "∅" if not row["selected"] else "{" + ",".join(row["selected"]) + "}"
                lines.append(
                    f"| {selected} | {row['cost']} | {row['empty_decimal']} | {row['nominal_decimal']} | {row['pess_decimal']} | {'yes' if row['nominal_pess_differ'] else 'no'} |"
                )
            lines.append("")
            lines.append(
                f"Nominal/PESS differing resource-set count: `{section['nominal_pess_different_set_count']}`; sets are listed in `diagnostic.json` under `nominal_pess_different_sets`."
            )
            lines.append("")
        lines.append("## Log-formula impact (diagnostic-only counterfactual)")
        lines.append("")
        counterfactual = data["correct_protocol_log_counterfactual"]
        lines.append("This section is not a v4 result and was not used to run or select held-out measurements.")
        lines.append("")
        lines.append("| budget | method | Empty objective | best corrected-log objective | best set(s) |")
        lines.append("|---:|---|---:|---:|---|")
        for budget in BUDGETS:
            for method in MODEL_METHODS:
                item = counterfactual["budgets"][str(budget)][method]
                lines.append(
                    f"| {budget} | {method} | {item['empty_objective']} | {item['best_objective']} | {item['best_sets']} |"
                )
        lines.append("")
    lines.extend(
        [
            "## Scientific boundary and next step",
            "",
            "This diagnosis establishes a validation-model implementation inconsistency and explains the observed Empty selections within the recorded v4 model. It does not establish PostgreSQL behavior, PESS superiority, a corrected held-out result, or a population-level claim. The appropriate current status for a protocol-conformant Stage 2B decision is **INCONCLUSIVE**, fail closed. Correct the implementation only through a reviewed change, re-freeze validation-only evidence, and obtain explicit authorization before any new held-out measurement.",
            "",
        ]
    )
    return "\n".join(lines)


def build_result() -> dict[str, Any]:
    protocol, models, ledgers = load_frozen_inputs()
    paths = input_paths()
    datasets = {
        dataset: analyze_dataset(dataset, protocol, models[dataset], ledgers[dataset])
        for dataset in DATASETS
    }
    provenance = {
        "analysis_scope": "validation-only",
        "heldout_data_read": False,
        "test_truth_read": False,
        "protocol_sha256": PROTOCOL_SHA256,
        "git_head_before_artifact_generation": git_head(),
        "inputs": {
            key: {"path": str(path), "sha256": sha256_file(path)}
            for key, path in paths.items()
        },
        "output_contract": {
            "exact_recorded_v4_objectives": "Fraction strings",
            "corrected_log_counterfactual": "Decimal precision 80, diagnostic only",
            "historical_v1_v4_evidence_modified": False,
        },
    }
    return {
        "format": "ess-issue48-stage2b-empty-selection-diagnostic-v1",
        "status": "INCONCLUSIVE_FOR_PROTOCOL_CONFORMANT_STAGE2B",
        "issue": 48,
        "pr": 58,
        "provenance": provenance,
        "datasets": datasets,
    }


def write_exclusive(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)


def write_artifacts(output: Path, result: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=False)
    diagnostic_path = output / "diagnostic.json"
    report_path = output / "empty-selection-diagnostic.md"
    write_exclusive(diagnostic_path, json.dumps(result, indent=2, sort_keys=True) + "\n")
    write_exclusive(report_path, make_report(result))
    manifest = {
        "format": "ess-issue48-stage2b-empty-selection-diagnostic-sha256-manifest-v1",
        "protocol_sha256": PROTOCOL_SHA256,
        "code_commit": result["provenance"]["git_head_before_artifact_generation"],
        "files": {
            "diagnostic.json": sha256_file(diagnostic_path),
            "empty-selection-diagnostic.md": sha256_file(report_path),
        },
        "input_sha256": {
            key: value["sha256"] for key, value in result["provenance"]["inputs"].items()
        },
        "heldout_data_read": False,
    }
    manifest_path = output / "manifest.json"
    write_exclusive(manifest_path, json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    sums = []
    for path in (diagnostic_path, report_path, manifest_path):
        sums.append(f"{sha256_file(path)}  {path.name}")
    write_exclusive(output / "SHA256SUMS", "\n".join(sums) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=V4_RUN.parent / "empty-selection-diagnostic-20261020-v1",
        help="new, exclusive output directory",
    )
    args = parser.parse_args()
    result = build_result()
    write_artifacts(args.output, result)
    print(args.output)


if __name__ == "__main__":
    main()
