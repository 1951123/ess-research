"""Build the exact-rational model input from measured Forest10 PG traces.

The PostgreSQL JSON is the measurement layer.  This small adapter creates a
separate model instance consumed by the merged exact Fraction runner; it does
not deserialize pickles and it does not infer statistic selection from
EXPLAIN output.  A fixed decimal quantization of Decimal natural logs is
recorded explicitly because measured binary floating-point values have no
exact rational logarithm in general.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
from decimal import Decimal, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def dec_ln(value: Fraction, places: int = 18) -> str:
    if value <= 0:
        raise ValueError("natural log input must be positive")
    with localcontext() as context:
        context.prec = 80
        result = (Decimal(value.numerator) / Decimal(value.denominator)).ln()
        quantum = Decimal(1).scaleb(-places)
        result = result.quantize(quantum)
    return format(result, "f")


def canonical_tasks(root: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    wanted = {item["query_id"]: item for item in manifest["selection_tasks"]["tasks"]}
    path = root / "arecel" / "audit-v1" / "forest10.canonical.jsonl.gz"
    records: dict[str, dict[str, Any]] = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if record.get("query_id") in wanted:
                records[record["query_id"]] = record
    if set(records) != set(wanted):
        raise ValueError("not all frozen tasks are present in canonical workload")
    return records


def final_trace(record: dict[str, Any]) -> dict[str, str]:
    values = [item for item in record["trace"]["numeric"] if "base_relation_oid" in item]
    if len(values) != 1:
        raise ValueError(f"expected one final base-relation trace, got {len(values)}")
    return values[0]


def first_measurements(calibration: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    selected: dict[tuple[str, str], dict[str, Any]] = {}
    for record in calibration["results"]:
        if record["repetition"] != 0:
            continue
        key = (record["candidate_id"], record["task"]["candidate_id"])
        if key in selected:
            raise ValueError(f"duplicate first-repetition measurement for {key}")
        selected[key] = record
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("real-input-manifest.json"))
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = (args.data_root or Path(os.environ["ESS_DATA_ROOT"])).expanduser().resolve()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    if manifest["data_root"] != str(root):
        raise ValueError("manifest data_root does not match supplied data root")
    if calibration["manifest_sha256"] != sha256_file(args.manifest):
        raise ValueError("calibration was not run from this frozen manifest")
    tasks = canonical_tasks(root, manifest)
    measurements = first_measurements(calibration)
    candidates = manifest["candidate_rule"]["candidates"]
    candidate_ids = [item["id"] for item in candidates]
    candidate_columns = {item["id"]: tuple(item["columns"]) for item in candidates}
    task_specs: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []
    provenance: list[dict[str, Any]] = []

    for frozen in manifest["selection_tasks"]["tasks"]:
        query = tasks[frozen["query_id"]]
        truth = int(frozen["truth"])
        predicate_columns = {item["column"] for item in query["source_query"]["predicates"]}
        if truth <= 0:
            excluded.append(
                {
                    "candidate_id": frozen["candidate_id"],
                    "query_id": frozen["query_id"],
                    "truth": truth,
                    "reason": "positive pre-clamp log-loss target condition T_i>0 failed",
                }
            )
            continue
        task_id = f"real_task_{frozen['candidate_id']}"
        baseline_record = measurements[("baseline", frozen["candidate_id"])]
        baseline_trace = final_trace(baseline_record)
        n0 = Fraction(baseline_trace["nrows_preclamp"])
        if n0 <= 0:
            raise ValueError(f"nonpositive baseline pre-clamp estimate for {task_id}")
        alpha = dec_ln(n0 / truth)
        corrections: dict[str, str] = {}
        eligible: list[str] = []
        task_measurements: dict[str, Any] = {}
        for candidate_id in candidate_ids:
            columns = candidate_columns[candidate_id]
            if not set(columns).issubset(predicate_columns):
                continue
            eligible.append(candidate_id)
            measured = measurements[(candidate_id, frozen["candidate_id"])]
            trace = final_trace(measured)
            n1 = Fraction(trace["nrows_preclamp"])
            if n1 <= 0:
                raise ValueError(f"nonpositive candidate pre-clamp estimate for {task_id}/{candidate_id}")
            corrections[candidate_id] = dec_ln(n1 / n0)
            task_measurements[candidate_id] = {
                "nrows_preclamp": trace["nrows_preclamp"],
                "selected_stat_oids": sorted(
                    {item.get("selected_stat_oid") for item in measured["trace"]["numeric"] if item.get("selected_stat_oid")}
                ),
                "mcv_row_count": len(measured["mcv_rows"]),
            }
        task_specs.append(
            {
                "id": task_id,
                "source_query_id": frozen["query_id"],
                "split": "valid",
                "table": "public.forest10_original",
                "weight": "1",
                "alpha": alpha,
                "eligible_candidates": eligible,
                "corrections": corrections,
                "truth_cardinality": truth,
                "source_query_sha256": frozen["source_query_sha256"],
                "measurement": {
                    "baseline_nrows_preclamp": baseline_trace["nrows_preclamp"],
                    "candidate_nrows_preclamp": task_measurements,
                },
            }
        )
        provenance.append(
            {
                "task_id": task_id,
                "source_query_id": frozen["query_id"],
                "truth": truth,
                "baseline_nrows_preclamp": baseline_trace["nrows_preclamp"],
                "positive_log_conditions": {"n0_gt_0": True, "truth_gt_0": True},
            }
        )

    instance = {
        "format": "forest10-real-pg-calibrated-model-v1",
        "status": "REAL_PG_CALIBRATED_INPUTS_EXCLUDING_NONPOSITIVE_TRUTH_TASKS",
        "dataset_identity": {
            "dataset": "Forest10",
            "source_table": "public.forest10_original",
            "source_commit": manifest["source"]["upstream_commit"],
            "csv_sha256": manifest["source"]["csv_sha256"],
            "derived_canonical_sha256": manifest["source"]["derived_canonical_sha256"],
            "real_query_ids_used": [item["source_query_id"] for item in task_specs],
            "truth_cardinalities_used": [item["truth_cardinality"] for item in task_specs],
        },
        "candidate_rule": {
            "kind": manifest["candidate_rule"]["kind"],
            "statistics_target": manifest["candidate_rule"]["statistics_target"],
            "columns_are_source_names": True,
            "precommitted_before_strategy_evaluation": True,
        },
        "nominal_order": manifest["decision_protocol"]["nominal_order"],
        "budgets": [str(item) for item in manifest["decision_protocol"]["budgets"]],
        "maintenance_proxy": {
            "kind": "one unit per candidate",
            "interpretation": "additive proxy only; not physical ANALYZE cost",
        },
        "parameter_provenance": {
            "alpha_and_corrections": "Decimal natural logs of measured positive pre-clamp ratios, quantized to 18 decimal places and then consumed as exact Fraction strings",
            "pg_measurement_source": str(args.calibration),
            "positive_preclamp_conditions": "all retained tasks have n0>0, T>0, and every eligible measured n1>0; zero/clamped Plan Rows are not used",
            "weights": "unit weight from frozen protocol",
            "excluded_tasks": excluded,
            "independent_reference": "run_experiment.py and verify_reference.py remain the optimization/reference implementations",
        },
        "candidates": [
            {
                "id": item["id"],
                "table": "public.forest10_original",
                "endpoints": list(item["columns"]),
                "maintenance_cost": "1",
            }
            for item in candidates
        ],
        "tasks": task_specs,
        "calibration_provenance": {
            "calibration_sha256": sha256_file(args.calibration),
            "manifest_sha256": sha256_file(args.manifest),
            "sample_sha256": calibration["sample"]["sha256"],
            "repetitions": calibration["protocol"]["repetitions"],
            "first_repetition_used_for_model": True,
            "repeat_replay_measurement": "fixed sample statistics and numeric values matched after ignoring recreated statistic OIDs and query markers",
            "task_measurements": provenance,
        },
    }
    args.output.write_text(json.dumps(instance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": sha256_file(args.output), "retained_tasks": len(task_specs), "excluded_tasks": excluded}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
