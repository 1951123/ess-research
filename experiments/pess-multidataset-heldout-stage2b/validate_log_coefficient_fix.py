"""Independently validate the Stage 2B logarithmic-coefficient fix.

The output of this script is explicitly exploratory validation-only evidence.
It reads the frozen v4 protocol, v4 validation models, and validation
calibration ledgers only.  It never opens test truth, held-out estimates,
held-out summaries, or PostgreSQL traces, and it never changes a held-out
selection.
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

from run_formal import rational_log as fixed_runner_rational_log

HERE = Path(__file__).resolve().parent
V4_RUN = HERE / "runs" / "formal-20261020-v4"
DATASETS = ("forest10", "census13")
METHODS = ("Nominal", "PESS")
BUDGETS = (0, 2, 3, 5)
PROTOCOL_SHA256 = "54867e0bf3ca116b044d77da14efe1b12d06851af522cfbeb49af14ae33733ad"
EXPLORATORY_LABEL = "EXPLORATORY VALIDATION-ONLY / NOT HELD-OUT EVIDENCE"


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
        raise TypeError(f"expected JSON object: {path}")
    return value


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise TypeError(f"expected JSON object: {path}:{line_number}")
            rows.append(value)
    return rows


def reference_rational_log(value: Decimal) -> Fraction:
    """Independent reference: high-precision Decimal.ln then 18-place Fraction."""

    if not value.is_finite() or value <= 0:
        raise ValueError("natural logarithm requires a finite positive Decimal")
    with localcontext() as context:
        context.prec = 80
        logged = value.ln()
        quantized = logged.quantize(Decimal("0.000000000000000001"))
    return Fraction(str(quantized))


def fraction_decimal(value: Fraction, places: int = 12) -> str:
    with localcontext() as context:
        context.prec = 80
        decimal = Decimal(value.numerator) / Decimal(value.denominator)
        quantized = decimal.quantize(Decimal(1).scaleb(-places))
    return format(quantized, "f")


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


def resource_sets(candidate_ids: list[str], budget: int) -> list[tuple[str, ...]]:
    return [
        tuple(candidate_ids[index] for index in range(len(candidate_ids)) if mask & (1 << index))
        for mask in range(1 << len(candidate_ids))
        if mask.bit_count() <= budget
    ]


def loss(
    task: dict[str, Any],
    selected: tuple[str, ...],
    method: str,
    candidates: dict[str, dict[str, Any]],
) -> Fraction:
    alpha = Fraction(task["alpha"])
    b = {edge: Fraction(value) for edge, value in task["b"].items()}
    available = [edge for edge in task["available_edges"] if edge in selected]
    if method == "Nominal":
        matchings = [nominal_matching(available, candidates)]
    elif method == "PESS":
        matchings = maximal_matchings(available, candidates)
    else:
        raise ValueError(f"unknown method: {method}")
    return max(
        (abs(alpha + sum((b[edge] for edge in matching), Fraction(0))) for matching in matchings),
        default=abs(alpha),
    )


def objective_rows(
    tasks: list[dict[str, Any]], candidates: dict[str, dict[str, Any]], budget: int
) -> list[dict[str, Any]]:
    candidate_ids = list(candidates)
    rows = []
    for selected in resource_sets(candidate_ids, budget):
        values = {
            method.lower(): str(
                sum((loss(task, selected, method, candidates) for task in tasks), Fraction(0))
            )
            for method in METHODS
        }
        rows.append(
            {
                "selected": list(selected),
                "cost": len(selected),
                **values,
                "nominal_pess_differ": values["nominal"] != values["pess"],
            }
        )
    return rows


def summary(rows: list[dict[str, Any]], method: str, budget: int) -> dict[str, Any]:
    scored = sorted(
        ((Fraction(row[method.lower()]), tuple(row["selected"])) for row in rows),
        key=lambda item: (item[0], item[1]),
    )
    best = scored[0][0]
    best_sets = [list(selected) for value, selected in scored if value == best]
    runner = next((value for value, _ in scored if value > best), None)
    empty = next(value for value, selected in scored if not selected)
    return {
        "method": method,
        "budget": budget,
        "best_objective": str(best),
        "best_objective_decimal": fraction_decimal(best),
        "best_sets": best_sets,
        "best_tie_count": len(best_sets),
        "runner_up_objective": None if runner is None else str(runner),
        "runner_up_objective_decimal": None if runner is None else fraction_decimal(runner),
        "runner_up_gap": None if runner is None else str(runner - best),
        "runner_up_gap_decimal": None if runner is None else fraction_decimal(runner - best),
        "empty_objective": str(empty),
        "empty_objective_decimal": fraction_decimal(empty),
        "empty_gap_to_best": str(empty - best),
        "empty_gap_to_best_decimal": fraction_decimal(empty - best),
        "empty_is_strict_best": empty == best and len(best_sets) == 1,
        "empty_is_tied_best": empty == best and len(best_sets) > 1,
    }


def coefficient_audit(
    dataset: str,
    model: dict[str, Any],
    ledger: list[dict[str, Any]],
    candidates: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str, int], dict[str, Any]]]:
    by_key: dict[tuple[str, str, int], dict[str, Any]] = {}
    for row in ledger:
        key = (row["query_id"], row["resource_set_id"], int(row["repetition"]))
        if key in by_key:
            raise RuntimeError(f"duplicate validation ledger key: {key}")
        by_key[key] = row
    audits = []
    for task in model["models"]:
        query_id = task["query_id"]
        baseline = by_key[(query_id, "calibration-empty", 0)]
        n0 = Decimal(baseline["estimate_preclamp"])
        target = Decimal(task["target_T"])
        alpha_input = n0 / target
        alpha_reference = reference_rational_log(alpha_input)
        alpha_fixed = fixed_runner_rational_log(alpha_input)
        if alpha_reference != alpha_fixed:
            raise RuntimeError(f"fixed runner alpha mismatch for {dataset}/{query_id}")
        coefficients = []
        for edge in candidates:
            row = by_key[(query_id, f"calibration-{edge}", 0)]
            estimate = Decimal(row["estimate_preclamp"])
            ratio = estimate / n0
            reference = reference_rational_log(ratio)
            fixed = fixed_runner_rational_log(ratio)
            if reference != fixed:
                raise RuntimeError(f"fixed runner b mismatch for {dataset}/{query_id}/{edge}")
            coefficients.append(
                {
                    "edge": edge,
                    "applicable_to_task": edge in task["available_edges"],
                    "estimate_preclamp": str(estimate),
                    "raw_ratio": str(ratio),
                    "recorded_v4_b": task["b"][edge],
                    "reference_log_b": str(reference),
                    "reference_log_b_decimal": fraction_decimal(reference),
                    "fixed_runner_matches_reference": True,
                }
            )
        audits.append(
            {
                "query_id": query_id,
                "source_index": task["source_index"],
                "available_edges": task["available_edges"],
                "n0_preclamp": str(n0),
                "target_T": task["target_T"],
                "raw_alpha_input_n0_over_T": str(alpha_input),
                "recorded_v4_alpha": task["alpha"],
                "reference_log_alpha": str(alpha_reference),
                "reference_log_alpha_decimal": fraction_decimal(alpha_reference),
                "fixed_runner_matches_reference": True,
                "coefficients": coefficients,
            }
        )
    return audits, by_key


def corrected_tasks(
    model: dict[str, Any],
    ledger_by_key: dict[tuple[str, str, int], dict[str, Any]],
    candidate_ids: list[str],
) -> list[dict[str, Any]]:
    tasks = []
    for original in model["models"]:
        query_id = original["query_id"]
        baseline = Decimal(ledger_by_key[(query_id, "calibration-empty", 0)]["estimate_preclamp"])
        target = Decimal(original["target_T"])
        b = {}
        for edge in candidate_ids:
            estimate = Decimal(
                ledger_by_key[(query_id, f"calibration-{edge}", 0)]["estimate_preclamp"]
            )
            b[edge] = str(reference_rational_log(estimate / baseline))
        tasks.append(
            {
                "query_id": query_id,
                "source_index": original["source_index"],
                "alpha": str(reference_rational_log(baseline / target)),
                "b": b,
                "available_edges": original["available_edges"],
                "coefficient_source": "validation calibration ledger repetition 0, protocol-log reference",
            }
        )
    return tasks


def matching_evidence(
    tasks: list[dict[str, Any]], candidates: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    evidence = []
    for task in tasks:
        matchings = maximal_matchings(task["available_edges"], candidates)
        nominal = nominal_matching(task["available_edges"], candidates)
        alpha = Fraction(task["alpha"])
        b = {edge: Fraction(value) for edge, value in task["b"].items()}
        losses = [
            {
                "matching": list(matching),
                "loss": str(abs(alpha + sum((b[edge] for edge in matching), Fraction(0)))),
            }
            for matching in matchings
        ]
        evidence.append(
            {
                "query_id": task["query_id"],
                "available_edges": task["available_edges"],
                "maximal_matching_count": len(matchings),
                "maximal_matchings": [list(matching) for matching in matchings],
                "nominal_matching": list(nominal),
                "nominal_loss": str(abs(alpha + sum((b[edge] for edge in nominal), Fraction(0)))),
                "pess_loss": max(item["loss"] for item in losses),
                "matching_losses": losses,
            }
        )
    return evidence


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
    paths = {
        "protocol_v4": HERE / "protocol-v4.json",
        "formal_runner_source": HERE / "run_formal.py",
        "validation_script_source": HERE / "validate_log_coefficient_fix.py",
    }
    for dataset in DATASETS:
        paths[f"{dataset}_validation_model"] = V4_RUN / dataset / "validation-model.json"
        paths[f"{dataset}_validation_calibration_ledger"] = (
            V4_RUN / dataset / "validation-calibration-ledger.jsonl"
        )
    return paths


def load_inputs() -> tuple[dict[str, Any], dict[str, Any], dict[str, list[dict[str, Any]]]]:
    paths = input_paths()
    protocol = read_json(paths["protocol_v4"])
    if sha256_file(paths["protocol_v4"]) != PROTOCOL_SHA256:
        raise RuntimeError("protocol-v4 SHA changed; fail closed")
    if protocol.get("status") != "FROZEN_BEFORE_HELDOUT_OUTCOME_COLLECTION_V4":
        raise RuntimeError("protocol-v4 is not frozen pre-held-out protocol")
    if protocol["measurement_contract"]["budgets_proxy_units"] != list(BUDGETS):
        raise RuntimeError("budget list changed; fail closed")
    models = {}
    ledgers = {}
    for dataset in DATASETS:
        model = read_json(paths[f"{dataset}_validation_model"])
        ledger = read_jsonl(paths[f"{dataset}_validation_calibration_ledger"])
        if model.get("protocol_sha256") != PROTOCOL_SHA256:
            raise RuntimeError(f"{dataset} model protocol SHA mismatch")
        if any(row.get("phase") != "validation_calibration" for row in ledger):
            raise RuntimeError(f"{dataset} ledger contains non-validation row")
        if any(":test:" in row.get("query_id", "") for row in ledger):
            raise RuntimeError(f"{dataset} ledger contains test query")
        models[dataset] = model
        ledgers[dataset] = ledger
    return protocol, models, ledgers


def analyze_dataset(
    dataset: str,
    protocol: dict[str, Any],
    model: dict[str, Any],
    ledger: list[dict[str, Any]],
) -> dict[str, Any]:
    candidates = candidate_map(protocol, dataset)
    candidate_ids = list(candidates)
    audits, ledger_by_key = coefficient_audit(dataset, model, ledger, candidates)
    corrected = corrected_tasks(model, ledger_by_key, candidate_ids)
    matching = matching_evidence(corrected, candidates)
    budgets = {}
    for budget in BUDGETS:
        before_rows = objective_rows(model["models"], candidates, budget)
        after_rows = objective_rows(corrected, candidates, budget)
        before_summary = {method: summary(before_rows, method, budget) for method in METHODS}
        after_summary = {method: summary(after_rows, method, budget) for method in METHODS}
        frozen = {
            method: model["selected_by_method_and_budget"][method][str(budget)]
            for method in METHODS
        }
        budgets[str(budget)] = {
            "feasible_set_count": len(before_rows),
            "before_frozen_v4_raw_ratio_model": {
                "objective_rows": before_rows,
                "summary": before_summary,
                "frozen_selection": frozen,
            },
            "after_exploratory_protocol_log_model": {
                "objective_rows": after_rows,
                "summary": after_summary,
                "selection_is_new_validation_only_diagnostic": True,
            },
            "nominal_pess_differing_sets_after": [
                row["selected"] for row in after_rows if row["nominal_pess_differ"]
            ],
        }
    return {
        "dataset": dataset,
        "candidate_ids": candidate_ids,
        "candidate_endpoints": {
            edge: candidates[edge]["source_columns"] for edge in candidate_ids
        },
        "coefficient_audit": audits,
        "corrected_tasks": corrected,
        "matching_evidence_after_fix": matching,
        "budgets": budgets,
        "formal_heldout_experiment_run": False,
    }


def md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def report(result: dict[str, Any]) -> str:
    lines = [
        "# Stage 2B logarithmic coefficient fix — exploratory validation diagnostic",
        "",
        f"> **{EXPLORATORY_LABEL}**",
        "> This artifact is not a new formal Stage 2B result. It uses the frozen v4 validation calibration records only; no test truth, held-out estimate, held-out summary, or PostgreSQL held-out run was read or executed.",
        "",
        "## Status",
        "",
        "The source fix is implemented in `run_formal.py::rational_log()`: finite positive Decimal inputs are evaluated with precision 80 using `Decimal.ln()`, then quantized to 18 decimal places and represented as `Fraction`. Nonpositive and nonfinite inputs fail closed.",
        "",
        "The frozen v4 model remains the **before** baseline. Its recorded coefficients and Empty selections are not overwritten. The **after** values below are a separately recomputed validation-only diagnostic and must not be used to retroactively validate v4 or justify a new held-out result.",
        "",
        "## Independent coefficient verification",
        "",
        "The independent reference implementation in `validate_log_coefficient_fix.py` separately performs the high-precision Decimal logarithm and compares every positive alpha/b input with the fixed runner. All comparisons must pass before this artifact is written.",
        "",
    ]
    for dataset in DATASETS:
        data = result["datasets"][dataset]
        lines.extend([
            f"### {dataset}",
            "",
            "| task | applicable edges | alpha before | alpha after log | coefficient checks |",
            "|---|---|---:|---:|---:|",
        ])
        for audit in data["coefficient_audit"]:
            checks = sum(item["fixed_runner_matches_reference"] for item in audit["coefficients"])
            lines.append(
                f"| {audit['query_id']} | {md(', '.join(audit['available_edges']))} | {audit['recorded_v4_alpha']} | {audit['reference_log_alpha']} | {checks}/{len(audit['coefficients'])} b values |"
            )
        lines.append("")
        lines.append("For each applicable edge, `diagnostic.json` retains the raw ratio, recorded v4 value, independent log value, and fixed-runner equality check. The v4 value is the raw positive ratio; the after value is the protocol-defined log coefficient.")
        lines.append("")
        lines.extend([
            "## Matching enumeration after the fix",
            "",
            "The following enumeration is independent of the runner's selection routine. It enumerates all maximal matchings of each frozen validation task graph; it is a model calculation, not a claim about PostgreSQL's actual choice.",
            "",
            "| task | applicable edges | maximal matching count | Nominal matching | PESS loss |",
            "|---|---|---:|---|---:|",
        ])
        for item in data["matching_evidence_after_fix"]:
            lines.append(
                f"| {item['query_id']} | {md(', '.join(item['available_edges']))} | {item['maximal_matching_count']} | {md(', '.join(item['nominal_matching']))} | {item['pess_loss']} |"
            )
        lines.append("")
        lines.extend([
            "## Before/after exhaustive resource-set objectives",
            "",
            "All objective rows are retained in `diagnostic.json`. Values below are exact rational strings rendered as decimals only for readability.",
            "",
        ])
        for budget in BUDGETS:
            section = data["budgets"][str(budget)]
            before = section["before_frozen_v4_raw_ratio_model"]
            after = section["after_exploratory_protocol_log_model"]
            lines.append(f"### Budget {budget} ({section['feasible_set_count']} feasible sets)")
            lines.append("")
            for method in METHODS:
                old = before["summary"][method]
                new = after["summary"][method]
                lines.append(
                    f"- **{method}:** before best `{old['best_objective_decimal']}` at `{old['best_sets']}`; after best `{new['best_objective_decimal']}` at `{new['best_sets']}`; after Empty gap `{new['empty_gap_to_best_decimal']}`; after runner-up gap `{new['runner_up_gap_decimal']}`."
                )
            lines.append("")
            lines.append("| M | before Nominal | before PESS | after Nominal | after PESS |")
            lines.append("|---|---:|---:|---:|---:|")
            after_by_set = {tuple(row["selected"]): row for row in after["objective_rows"]}
            for old_row in before["objective_rows"]:
                selected = tuple(old_row["selected"])
                new_row = after_by_set[selected]
                selected_text = "∅" if not selected else "{" + ",".join(selected) + "}"
                lines.append(
                    f"| {selected_text} | {fraction_decimal(Fraction(old_row['nominal']))} | {fraction_decimal(Fraction(old_row['pess']))} | {fraction_decimal(Fraction(new_row['nominal']))} | {fraction_decimal(Fraction(new_row['pess']))} |"
                )
            lines.append("")
        lines.extend([
            "## Interpretation boundary",
            "",
            "The after-selection changes are validation-model consequences of applying the frozen mathematical log definition to the already recorded validation calibration ledger. They are **exploratory validation-only / not held-out evidence**. No corrected resource set was applied to PostgreSQL, and no held-out measurement was run.",
            "",
            "The historical v4 execution remains a separate as-executed record using the pre-fix model. This artifact neither overwrites it nor retroactively changes its validity. A formal Stage 2B rerun would require researcher review, a separately versioned validation freeze, and explicit authorization; it is not performed here.",
            "",
        ])
    return "\n".join(lines)


def build_result() -> dict[str, Any]:
    protocol, models, ledgers = load_inputs()
    datasets = {
        dataset: analyze_dataset(dataset, protocol, models[dataset], ledgers[dataset])
        for dataset in DATASETS
    }
    paths = input_paths()
    return {
        "format": "ess-issue48-stage2b-log-coefficient-fix-exploratory-v1",
        "evidence_label": EXPLORATORY_LABEL,
        "issue": 48,
        "pr": 58,
        "protocol_sha256": PROTOCOL_SHA256,
        "historical_v4_modified": False,
        "formal_heldout_experiment_run": False,
        "test_truth_read": False,
        "heldout_estimates_read": False,
        "git_head_before_artifact_generation": git_head(),
        "inputs": {
            key: {"path": str(path), "sha256": sha256_file(path)}
            for key, path in paths.items()
        },
        "datasets": datasets,
    }


def write_exclusive(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        handle.write(content)


def write_artifacts(output: Path, result: dict[str, Any]) -> None:
    output.mkdir(parents=True, exist_ok=False)
    diagnostic = output / "diagnostic.json"
    report_path = output / "exploratory-validation-only-log-fix.md"
    write_exclusive(diagnostic, json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_exclusive(report_path, report(result))
    manifest = {
        "format": "ess-issue48-stage2b-log-coefficient-fix-sha256-manifest-v1",
        "evidence_label": EXPLORATORY_LABEL,
        "protocol_sha256": PROTOCOL_SHA256,
        "code_commit": result["git_head_before_artifact_generation"],
        "input_sha256": {key: value["sha256"] for key, value in result["inputs"].items()},
        "output_sha256": {
            "diagnostic.json": sha256_file(diagnostic),
            "exploratory-validation-only-log-fix.md": sha256_file(report_path),
        },
        "heldout_data_read": False,
    }
    manifest_path = output / "manifest.json"
    write_exclusive(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    sums = "".join(
        f"{sha256_file(path)}  {path.name}\n"
        for path in (diagnostic, report_path, manifest_path)
    )
    write_exclusive(output / "SHA256SUMS", sums)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        type=Path,
        default=V4_RUN.parent / "empty-selection-log-fix-20261020-v1",
    )
    args = parser.parse_args()
    result = build_result()
    write_artifacts(args.output, result)
    print(args.output)


if __name__ == "__main__":
    main()
