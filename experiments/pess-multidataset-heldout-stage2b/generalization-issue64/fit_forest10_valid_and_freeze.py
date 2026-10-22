"""Fit the pinned corrected-log model from durable Forest10 valid data only."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import io
import json
import os
import sys
import tarfile
import tempfile
from collections import Counter
from decimal import Decimal
from fractions import Fraction
from pathlib import Path

HERE = Path(__file__).resolve().parent
ISSUE64_ROOT = HERE.parents[2]
sys.path.insert(0, str(ISSUE64_ROOT / "src"))
sys.path.insert(0, str(HERE))

from ess_research.arecel import archive as arecel_archive
from ess_research.arecel.archive import prepare_valid_workload
from ess_research.arecel.candidates import discover_candidates
from ess_research.arecel.forest10 import SOURCE_COLUMNS
from ess_research.task_paths import configured_root
from forest10_exact_selection import exact_select_many, maximal_matchings, model_loss
from forest10_runner import build_task_models, rational_log_ratio
import run_forest10_full_calibration_collector as collector
import verify_forest10_full_valid_observations as observation_verifier


RUN_RELATIVE = Path("runs/20261022-forest10-full-valid-v1")
EXPECTED_ARCHIVE_SHA256 = "5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79"
EXPECTED_MANIFEST_SHA256 = "a6972008f73f24ca3c1a456c96caf64e109895ef5b9525fa2b35791ca5bca99b"
EXPECTED_PLAN_SHA256 = "5483f55046e287594eb2090557c68d3334cefda8318c29a707a0631623284db2"
EXPECTED_PR58_RUN_FORMAL_SHA256 = "61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322"
EXPECTED_CONFIG_IDS = (
    "Empty", "e00_01", "e00_02", "e00_03", "e00_04", "e00_05", "e00_06", "e00_07", "e00_08", "e00_09",
    "e01_02", "e01_03", "e01_04", "e01_05", "e01_06", "e01_07", "e01_08", "e01_09",
    "e02_03", "e02_04", "e02_05", "e02_06", "e02_07", "e02_08", "e02_09",
    "e03_04", "e03_05", "e03_06", "e03_07", "e03_08", "e03_09",
    "e04_05", "e04_06", "e04_07", "e04_08", "e04_09",
    "e05_06", "e05_07", "e05_08", "e05_09",
    "e06_07", "e06_08", "e06_09", "e07_08", "e07_09", "e08_09",
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_valid_truth(cache_root: Path) -> tuple[dict[str, int], dict[str, str]]:
    """Deserialize the pinned label member, then expose only Forest10 valid labels."""
    member_name = "data/forest10/workload/base-original-label.pkl"
    labels_object = None
    with arecel_archive._archive(cache_root) as verified_archive:
        with tarfile.open(fileobj=verified_archive, mode="r|gz") as tar:
            for member in tar:
                if member.name.removeprefix("./") != member_name:
                    continue
                if labels_object is not None or not member.isfile():
                    raise ValueError("duplicate/nonregular pinned valid-truth member")
                source = tar.extractfile(member)
                if source is None:
                    raise ValueError("pinned valid-truth member is unreadable")
                with source:
                    labels_object = arecel_archive._ArchiveUnpickler(source).load()
    if not isinstance(labels_object, dict) or not isinstance(labels_object.get("valid"), list):
        raise ValueError("pinned AreCEL archive has no Forest10 valid truth list")
    valid = labels_object["valid"]
    truths: dict[str, int] = {}
    zeros = 0
    valid_digest = hashlib.sha256()
    for index, label in enumerate(valid):
        if not isinstance(label, arecel_archive.Label):
            raise ValueError(f"invalid valid Label at source index {index}")
        cardinality = arecel_archive._scalar(label.cardinality)
        if not isinstance(cardinality, int) or cardinality < 0:
            raise ValueError(f"invalid valid cardinality at source index {index}")
        query_id = f"arecel:forest10:valid:{index:06d}"
        truths[query_id] = cardinality
        zeros += cardinality == 0
        valid_digest.update((json.dumps({"query_id": query_id, "valid_truth": cardinality},
                                     sort_keys=True, separators=(",", ":")) + "\n").encode())
    if len(truths) != 10_000:
        raise ValueError(f"expected 10000 official valid truths, got {len(truths)}")
    return truths, {
        "valid_truth_count": str(len(truths)),
        "valid_truth_zero_count": str(zeros),
        "valid_truth_values_sha256": valid_digest.hexdigest(),
    }


def _write_coefficients(path: Path, queries, truths, empty, singleton, eligibility, models) -> str:
    """Write a deterministic compact per-task record of the fitted exact coefficients."""
    temp_path = path.with_name(path.name + f".{os.getpid()}.tmp")
    try:
        with temp_path.open("xb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", compresslevel=9, mtime=0) as compressed:
                with io.TextIOWrapper(compressed, encoding="utf-8", newline="\n") as text:
                    for query, model in zip(queries, models, strict=True):
                        query_id = query["query_id"]
                        record = {
                            "query_id": query_id,
                            "valid_truth": truths[query_id],
                            "target": max(1, truths[query_id]),
                            "n0_preclamp": str(empty[query_id]),
                            "alpha_fraction": str(model.alpha),
                            "b_fraction": {edge: str(model.b[edge]) for edge in eligibility[query_id]},
                        }
                        text.write(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
            raw.flush()
            os.fsync(raw.fileno())
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)
    return file_sha256(path)


def run(run_root: Path, result_path: Path, coefficients_path: Path) -> dict:
    manifest_path = run_root / collector.MANIFEST
    manifest_sha = file_sha256(manifest_path)
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise ValueError("durable collection manifest SHA-256 differs from the reviewed acquisition")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("plan_sha256") != EXPECTED_PLAN_SHA256:
        raise ValueError("collection plan pin mismatch")
    pins = manifest.get("source_pins", {})
    if pins.get("pr58_source_commit") != "76106024611ae91505f1f05bdc35aed44d9c38c4":
        raise ValueError("PR #58 source commit pin mismatch")
    if pins.get("run_formal_sha256") != EXPECTED_PR58_RUN_FORMAL_SHA256:
        raise ValueError("PR #58 corrected-log source hash mismatch")
    if manifest.get("arecel_archive_sha256") != EXPECTED_ARCHIVE_SHA256:
        raise ValueError("AreCEL archive pin mismatch")

    with prepare_valid_workload(issue=64, dataset="forest10") as prepared:
        if prepared.manifest.get("labels_loaded") is not False:
            raise ValueError("valid-workload loader did not attest labels_loaded=false")
        workload = json.loads(prepared.workload_path.read_text(encoding="utf-8"))
        discovery = discover_candidates(workload["queries"], SOURCE_COLUMNS)
        ordered, candidates, per_candidate = collector.build_schedule(workload, discovery)
        integrity = observation_verifier.verify(run_root, workload, discovery)
        if integrity.get("status") != "PASS" or integrity.get("rows") != 174_088:
            raise ValueError("durable structured observation verification failed")

        truths, truth_summary = load_valid_truth(configured_root("ESS_DATA_ROOT"))
        query_ids = tuple(row["query_id"] for row in ordered)
        if set(truths) != set(query_ids):
            raise ValueError("valid truth IDs do not exactly match official valid workload IDs")

        eligible: dict[str, list[str]] = {query_id: [] for query_id in query_ids}
        for edge, query_list in per_candidate.items():
            for query_id in query_list:
                eligible[query_id].append(edge)
        expected_order = ["Empty", *[edge for edge, _ in candidates if per_candidate[edge]]]
        if tuple(expected_order) != EXPECTED_CONFIG_IDS:
            raise ValueError("candidate/configuration order differs from frozen 45-candidate order")
        if manifest.get("schedule", {}).get("candidate_ids") != [edge for edge, _ in candidates]:
            raise ValueError("candidate IDs differ from the acquisition schedule")

        empty: dict[str, Decimal] = {}
        singleton: dict[str, dict[str, Decimal]] = {edge: {} for edge, _ in candidates}
        status_counts: Counter[str] = Counter()
        below_one = Counter()
        observation_dir = run_root / "observations"
        part_info = {row["path"]: row for row in manifest["parts"]}
        for name in sorted(part_info, key=lambda item: part_info[item]["first_sequence"]):
            with gzip.open(observation_dir / name, "rt", encoding="utf-8") as stream:
                for line in stream:
                    row = json.loads(line)
                    query_id, config_id = row["query_id"], row["config_id"]
                    estimate = Decimal(row["nrows_preclamp"])
                    status_counts[row["mcv_diagnostics_status"]] += 1
                    below_one[config_id] += estimate < 1
                    if config_id == "Empty":
                        if query_id in empty:
                            raise ValueError(f"duplicate Empty observation for {query_id}")
                        empty[query_id] = estimate
                    else:
                        if query_id not in eligible or config_id not in eligible[query_id]:
                            raise ValueError(f"singleton observation is not statically eligible: {query_id}/{config_id}")
                        if query_id in singleton[config_id]:
                            raise ValueError(f"duplicate singleton observation: {query_id}/{config_id}")
                        singleton[config_id][query_id] = estimate
        if set(empty) != set(query_ids):
            raise ValueError("Empty estimates do not cover the official valid workload exactly")
        if set(singleton) != {edge for edge, _ in candidates if per_candidate[edge]}:
            raise ValueError("singleton configuration coverage differs from frozen candidates")
        for edge, query_list in per_candidate.items():
            if set(singleton.get(edge, {})) != set(query_list):
                raise ValueError(f"singleton observations do not cover eligible valid queries for {edge}")

        models = build_task_models(query_ids, truths, empty, singleton, eligible)
        selection = exact_select_many(models, candidates, (0, 2, 3))
        endpoints = {edge: tuple(nodes) for edge, nodes in candidates}
        selected_set_diagnostics = {}
        for budget in (0, 2, 3):
            chosen = selection["Nominal"][str(budget)]["selected"]
            nominal_total = Fraction(0)
            pess_total = Fraction(0)
            tasks_with_multiple_matchings = 0
            tasks_with_loss_varying_matchings = 0
            tasks_pess_strictly_worse_than_nominal = 0
            for model in models:
                available = tuple(edge for edge in model.available_edges if edge in chosen)
                schemes = maximal_matchings(available, endpoints)
                losses = [abs(model.alpha + sum((model.b[e] for e in scheme), Fraction(0)))
                          for scheme in schemes]
                if len(schemes) > 1:
                    tasks_with_multiple_matchings += 1
                if len(set(losses)) > 1:
                    tasks_with_loss_varying_matchings += 1
                nominal = model_loss(model, chosen, "Nominal", endpoints, [edge for edge, _ in candidates])
                pess = model_loss(model, chosen, "PESS", endpoints, [edge for edge, _ in candidates])
                tasks_pess_strictly_worse_than_nominal += pess > nominal
                nominal_total += nominal
                pess_total += pess
            selected_set_diagnostics[str(budget)] = {
                "selected": chosen,
                "nominal_objective_on_selected_set_fraction": str(nominal_total),
                "pess_objective_on_selected_set_fraction": str(pess_total),
                "pess_minus_nominal_fraction": str(pess_total - nominal_total),
                "tasks_with_multiple_maximal_matchings": tasks_with_multiple_matchings,
                "tasks_where_maximal_matchings_change_loss": tasks_with_loss_varying_matchings,
                "tasks_where_pess_loss_exceeds_nominal": tasks_pess_strictly_worse_than_nominal,
            }
        coefficient_hash = _write_coefficients(coefficients_path, ordered, truths, empty, singleton, eligible, models)

    alpha_values = [model.alpha for model in models]
    b_values = [value for model in models for value in model.b.values()]
    quantized_decimal = lambda value: Decimal(value.numerator) / Decimal(value.denominator)
    result = {
        "format": "ess-issue64-forest10-valid-fit-and-selection-v1",
        "status": "FROZEN",
        "scope": "Forest10 official valid-only model fit and exact B=0/2/3 Nominal/PESS selection; no test data or PostgreSQL access",
        "inputs": {
            "analysis_script_sha256": file_sha256(Path(__file__).resolve()),
            "exact_selector_sha256": file_sha256(HERE / "forest10_exact_selection.py"),
            "model_builder_sha256": file_sha256(HERE / "forest10_runner.py"),
            "collection_manifest_sha256": manifest_sha,
            "observation_parts": len(manifest["parts"]),
            "observation_rows": integrity["rows"],
            "arecel_archive_sha256": EXPECTED_ARCHIVE_SHA256,
            "arecel_upstream_commit": arecel_archive.UPSTREAM_COMMIT,
            "valid_workload_count": len(ordered),
            "valid_truth_source_member": "data/forest10/workload/base-original-label.pkl; only labels['valid'] was used",
            "valid_truth_values_sha256": truth_summary["valid_truth_values_sha256"],
            "candidate_count": len(candidates),
            "candidate_order": [edge for edge, _ in candidates],
            "nominal_order": "same frozen candidate order, greedy matching",
        },
        "model": {
            "source": "PR #58 corrected-log run_formal.py; full commit 76106024611ae91505f1f05bdc35aed44d9c38c4",
            "run_formal_sha256": EXPECTED_PR58_RUN_FORMAL_SHA256,
            "alpha_definition": "ln(n0 / max(1, valid_truth))",
            "b_definition": "ln(n_e / n0), only for statically eligible edges",
            "positive_preclamp_inputs_only": True,
            "plan_rows_used": False,
            "no_mcv_observations_retained": True,
            "truth_summary": truth_summary,
            "observation_status_counts": dict(status_counts),
            "preclamp_estimates_below_one": dict(below_one),
            "coefficient_counts": {"alpha": len(alpha_values), "b": len(b_values)},
            "alpha_zero_count": sum(value == 0 for value in alpha_values),
            "b_zero_count": sum(value == 0 for value in b_values),
            "alpha_min_fraction": str(min(alpha_values)),
            "alpha_max_fraction": str(max(alpha_values)),
            "b_min_fraction": str(min(b_values)),
            "b_max_fraction": str(max(b_values)),
            "ln_precision_decimal_digits": 80,
            "ln_quantization": "1e-18, ROUND_HALF_EVEN",
            "coefficient_artifact": coefficients_path.name,
            "coefficient_artifact_sha256": coefficient_hash,
            "coefficient_record_schema": "one valid query per JSONL record: valid truth, target, n0, exact rational alpha, and every eligible exact rational b_e",
        },
        "selection": {
            "budgets": [0, 2, 3],
            "constraint": "|S| <= B",
            "objective": "sum over valid tasks of absolute corrected-log residual; PESS takes max over all inclusion-maximal matchings per task",
            "enumeration": "all feasible subsets; exact Fraction objective over PR #58 quantized rational coefficients",
            "feasible_subset_counts": {"0": 1, "2": 1036, "3": 15226},
            "tie_rule": "retain every exact minimizer; chosen representative is first by cardinality then frozen candidate-order tuple (implementation enumeration order)",
            "results": selection,
            "selected_set_loss_diagnostics": selected_set_diagnostics,
            "selected_sets_identical_by_budget": {
                str(budget): selection["Nominal"][str(budget)]["selected"] == selection["PESS"][str(budget)]["selected"]
                for budget in (0, 2, 3)
            },
        },
        "scientific_limits": [
            "These are valid-split model objectives/resource selections, not PostgreSQL test outcomes or Q1 evaluation.",
            "Static candidate eligibility and the maximal-matching PESS model do not assert actual PostgreSQL selection or MCV use.",
            "No held-out test workload, truth, estimates or outcomes were loaded or evaluated.",
        ],
    }
    result_path.write_text(json.dumps(result, sort_keys=True, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    default_root = HERE / RUN_RELATIVE
    parser.add_argument("--run", type=Path, default=default_root)
    parser.add_argument("--result", type=Path, default=HERE / "forest10-valid-frozen-selection-v1.json")
    parser.add_argument("--coefficients", type=Path, default=HERE / "forest10-valid-fitted-coefficients-v1.jsonl.gz")
    args = parser.parse_args()
    result = run(args.run, args.result, args.coefficients)
    print(json.dumps({
        "status": result["status"],
        "rows": result["inputs"]["observation_rows"],
        "coefficients": result["model"]["coefficient_counts"],
        "selected_sets_identical_by_budget": result["selection"]["selected_sets_identical_by_budget"],
        "result_path": str(args.result),
        "coefficient_path": str(args.coefficients),
    }, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
