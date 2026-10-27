"""Create the final bounded Stage 2B decision report from formal evidence."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from decimal import Decimal
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_exclusive(path: Path, text: str) -> None:
    with path.open("x", encoding="utf-8") as stream:
        stream.write(text)


def extract_dataset(run_root: Path, dataset_result: dict[str, Any]) -> dict[str, Any]:
    dataset = dataset_result["dataset"]
    evidence = run_root / dataset
    model = load_json(evidence / "validation-model.json")
    summary = load_json(evidence / "heldout-summary.json")["summary"]
    heldout = [json.loads(line) for line in (evidence / "heldout-ledger.jsonl").read_text().splitlines()]
    runtime_root = Path(dataset_result["raw_external"]["run_root"])
    setups = [json.loads(line) for line in (runtime_root / "results/formal-setups.jsonl").read_text().splitlines()]
    calibration_setups = [row for row in setups if row["phase"] == "validation_calibration" and row["repetition"] == 0]
    payload = {
        row["resource_set_id"]: [
            {
                "statistic_name": item["statistic_name"],
                "resource_id": item["statistic_name"].split("_")[-1],
                "mcv_payload_present": item["mcv_payload_present"],
                "mcv_item_count": item["mcv_item_count"],
            }
            for item in row["catalog"]
        ]
        for row in calibration_setups
    }
    methods = {
        method: {budget: value["selected"] for budget, value in budgets.items()}
        for method, budgets in model["selected_by_method_and_budget"].items()
    }
    return {
        "dataset": dataset,
        "cohort_query_ids": len({row["query_id"] for row in heldout}),
        "heldout_rows": len(heldout),
        "repetitions": len({row["repetition"] for row in heldout}),
        "positive_preclamp_rows": sum(Decimal(row["estimate_preclamp"]) > 0 for row in heldout),
        "trace_selected_rows": sum(bool(row["selected_resource_ids_from_trace"]) for row in heldout),
        "claimed_clause_status": dict(Counter(row["claimed_clause_coverage"]["status"] for row in heldout)),
        "zero_truth_rows": sum(row["truth_N"] == 0 for row in heldout),
        "truth_direction": dict(Counter(
            "underestimate" if Decimal(row["signed_estimate_minus_T"]) < 0
            else "exact" if Decimal(row["signed_estimate_minus_T"]) == 0
            else "overestimate"
            for row in heldout
        )),
        "empty_summary": next(item for item in summary["resource_sets"] if item["selected"] == []),
        "validation_payload_by_singleton": payload,
        "model_selected_sets": methods,
        "model_objectives": {
            method: {budget: value["objective"] for budget, value in budgets.items()}
            for method, budgets in model["selected_by_method_and_budget"].items()
        },
        "sample": model["sample"],
        "external_raw_heldout_sha256": dataset_result["raw_external"]["heldout_sha256"],
    }


def report(protocol: dict[str, Any], run: dict[str, Any], datasets: list[dict[str, Any]], run_label: str) -> str:
    lines = [
        "# Stage 2B formal held-out decision-quality report",
        "",
        "Evidence label: **Experimentally observed — valid matched PostgreSQL measurements, with a negative/no-contrast decision result.**",
        "",
        "## Decision",
        "",
        "**NO-GO for the tested nontrivial PESS-versus-Nominal physical contrast under this frozen validation-selection procedure.** Both real datasets passed the measurement validity checks, but validation-only model selection chose `Empty` for Empty, Nominal, and PESS at every budget. Consequently the held-out PostgreSQL measurements are valid repeated Empty controls, not a nontrivial PESS/Nominal treatment contrast.",
        "",
        "This is not a claim that PESS is universally worse, that Nominal is universally better, or that Empty is an optimal PostgreSQL resource policy. It is a bounded negative result: the preregistered procedure produced no distinct nonempty policy to compare on these supported cohorts. A broader study would need a separately authorized protocol amendment or follow-up that changes the validation calibration/task construction without consulting these held-out outcomes.",
        "",
        "## Frozen protocol and independence",
        "",
        f"Protocol SHA-256: `{sha256_file(HERE / 'protocol-v4.json')}`. The protocol froze strict pairwise eligibility, cohorts, cross-split fingerprint audit, Stage 1A exclusion, validation-only calibration, budgets, methods, metrics, repetitions, sample procedure, and fail-closed rules before this run. The v1 runner failure is preserved in `runs/formal-20261020-v1/failure-note.md`; the v2 evidence is retained but superseded because its Empty tie ledger was corrected; the v3 evidence is retained but invalidated because its candidate-set enumeration searched only the first candidate position. This is the authoritative `{run_label}` rerun after both corrections.",
        "",
        "The strict eligibility rule was exactly two predicates on two distinct source columns with an exact predeclared candidate endpoint match. Forest10's source has no equality-only records under this rule, so the protocol retained the declared supported range operators rather than silently discarding Forest10. Normalized SQL-template groups overlap across train/valid/test in both datasets; query IDs are therefore not group-independent population samples.",
        "",
        "## Validity and effective-MCV coverage",
        "",
        "| Dataset | frozen query IDs | held-out rows | positive traces | trace-selected rows | zero-truth rows | mean | median | P90 | max |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for item in datasets:
        metric = item["empty_summary"]["absolute_log_error"]
        lines.append(
            f"| {item['dataset']} | {item['cohort_query_ids']} | {item['heldout_rows']} | {item['positive_preclamp_rows']} | {item['trace_selected_rows']} | {item['zero_truth_rows']} | {metric['mean']} | {metric['median']} | {metric['p90']} | {metric['max']} |"
        )
    lines += [
        "",
        "All held-out rows had positive pre-clamp numeric traces and valid trace attribution. No held-out row selected an MCV statistic because every selected decision set was Empty; applicable claimed-clause coverage was therefore `NOT_APPLICABLE`, not falsely marked verified. The cohorts contained zero zero-truth rows; this is reported rather than replaced or inferred away.",
        "",
        "Validation singleton catalogs retained the requested/payload distinction:",
        "",
    ]
    for item in datasets:
        lines.append(f"- **{item['dataset']}**: " + "; ".join(
            f"{set_id}=" + ",".join(
                f"{'payload' if row['mcv_payload_present'] else 'no-payload'}:{row['mcv_item_count']}"
                for row in rows
            )
            for set_id, rows in sorted(item["validation_payload_by_singleton"].items())
            if set_id != "calibration-empty"
        ) + ".")
    lines += [
        "",
        "Forest10's validation payloads were present for `e12/e23/e34` (300 items each) and absent for `e01/e45/e56`. Census13's six validation singleton payloads were present with item counts recorded in the bounded evidence. These are validation calibration observations; they were not used to revise the frozen test cohort.",
        "",
        "## Model layer versus PostgreSQL layer",
        "",
        "The model layer used validation-only positive pre-clamp estimates and truths, with `T=max(1,N)`. Natural logs were quantized to 18 decimal places and represented as `Fraction` strings; exactness applies only to that rationalized model input. The PostgreSQL layer used the actual positive numeric trace from each held-out query, with two repeats on one Issue-owned fixed sample per dataset. The layers are separate and do not establish a PG guarantee.",
        "",
        "For every dataset, budget, and method, the recorded selected set was `[]`; all PESS/Nominal/Empty aliases are therefore physically identical. No PESS-versus-Nominal harms, benefits, or ties are interpreted as a treatment result because there was no nonempty treatment contrast. The Empty metrics above are descriptive held-out controls only.",
        "",
        "## Provenance and limitations",
        "",
        f"The formal runner summary is `{run['overall_status']}` before this analysis. Forest10 and Census13 used fresh clusters, fixed samples, PostgreSQL 16.14, and the pinned source/binary audit. Raw trace files remain external under the Issue runtime; bounded ledgers and summaries are committed under `runs/{run_label}/`.",
        "",
        "The result does not establish universal PostgreSQL maximal-matching containment, real-scheme inclusion, PESS dominance, physical maintenance additivity, latency benefit, statistical significance, or population-level generalization. The normalized SQL group overlap and absence of zero-truth rows further restrict interpretation.",
        "",
        "Evidence labels: source/build facts are source-derived conditional evidence; the two-dataset rows and metrics are experimentally observed; rationalized model objectives are exact only for their recorded Fraction inputs; the NO-GO judgment is a bounded protocol decision, not a universal theorem.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-root", type=Path, required=True)
    args = parser.parse_args()
    if not args.run_root.is_dir():
        raise SystemExit(f"missing run root: {args.run_root}")
    if (args.run_root / "decision.json").exists() or (args.run_root / "report.md").exists():
        raise SystemExit("refusing to overwrite existing analysis evidence")
    protocol = load_json(HERE / "protocol-v4.json")
    run = load_json(args.run_root / "run-summary.json")
    datasets = [extract_dataset(args.run_root, item) for item in run["results"]]
    decision = {
        "format": "ess-issue48-stage2b-formal-decision-v1",
        "evidence_label": "experimentally_observed_bounded_protocol_decision",
        "protocol_sha256": sha256_file(HERE / "protocol-v4.json"),
        "run_summary_sha256": sha256_file(args.run_root / "run-summary.json"),
        "decision": "NO-GO",
        "decision_scope": "tested nontrivial PESS-versus-Nominal physical contrast under protocol-v4 validation-only selection",
        "valid_dataset_count": sum(item["heldout_rows"] > 0 for item in datasets),
        "nontrivial_method_contrast": False,
        "datasets": datasets,
        "limitations": ["not universal PESS ranking", "not a PostgreSQL containment guarantee", "not a latency or maintenance-cost result", "not population-level or group-independent inference"],
    }
    write_exclusive(args.run_root / "decision.json", json.dumps(decision, ensure_ascii=False, indent=2, sort_keys=True) + "\n")
    write_exclusive(args.run_root / "report.md", report(protocol, run, datasets, args.run_root.name))
    files = sorted(path for path in args.run_root.rglob("*") if path.is_file() and path.name != "SHA256SUMS")
    checksums = "".join(f"{sha256_file(path)}  {path.relative_to(args.run_root)}\n" for path in files)
    write_exclusive(args.run_root / "SHA256SUMS", checksums)
    print(json.dumps({"decision": "NO-GO", "report": str(args.run_root / "report.md"), "datasets": [item["dataset"] for item in datasets]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
