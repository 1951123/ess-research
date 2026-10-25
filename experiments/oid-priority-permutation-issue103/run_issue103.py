#!/usr/bin/env python3
"""Exact offline global-priority permutation analysis for Issue #103.

Only the frozen Issue #99 train workload, train truth, and train observations
are read. The reference loss routines are loaded from the Advisor source files
whose bytes match the source commit pinned by Issue #99.
"""

from __future__ import annotations

import argparse
from decimal import Decimal, localcontext
from fractions import Fraction
import gzip
import hashlib
import importlib
import importlib.util
import itertools
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import types
from typing import Any
from datetime import datetime, timezone


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FROZEN_PATH = ROOT / "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json"
PROTOCOL_PATH = ROOT / "experiments/add-only-greedy-issue99/protocol-v4.json"
SCALE = 10**18
DATASETS = ("forest10", "census13", "dmv11", "power7")
BUDGETS = (0, 2, 3, 4, 5)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_units(value: Fraction | str) -> int:
    """Convert an Issue #99 1e-18-quantized fraction to exact integer units."""
    fraction = value if isinstance(value, Fraction) else Fraction(value)
    scaled = fraction * SCALE
    if scaled.denominator != 1:
        raise ValueError(f"coefficient is not an integer multiple of 1e-18: {fraction}")
    return scaled.numerator


def fraction_string(value: Fraction) -> str:
    return str(value)


def decimal_string(value: Fraction, places: int = 8) -> str:
    with localcontext() as context:
        context.prec = max(40, places + 20)
        number = Decimal(value.numerator) / Decimal(value.denominator)
        return f"{number:.{places}f}"


def _edge_conflicts(endpoints: list[tuple[str, str]]) -> tuple[int, ...]:
    result = []
    for left, edge in enumerate(endpoints):
        mask = 0
        for right, other in enumerate(endpoints):
            if left != right and set(edge) & set(other):
                mask |= 1 << right
        result.append(mask)
    return tuple(result)


def priority_matching_masks(
    active_mask: int,
    orders: tuple[tuple[int, ...], ...],
    endpoints: list[tuple[str, str]],
) -> tuple[int, ...]:
    """Replay inclusion-maximal greedy matchings for all supplied priorities."""
    outcomes = []
    for order in orders:
        occupied: set[str] = set()
        matching = 0
        for edge_index in order:
            if not active_mask & (1 << edge_index):
                continue
            edge = endpoints[edge_index]
            if not occupied.intersection(edge):
                matching |= 1 << edge_index
                occupied.update(edge)
        outcomes.append(matching)
    return tuple(outcomes)


def maximal_matching_masks(active_mask: int, endpoints: list[tuple[str, str]]) -> tuple[int, ...]:
    """Enumerate the complete inclusion-maximal matching family for a task."""
    conflicts = _edge_conflicts(endpoints)
    maximal = []
    subset = active_mask
    while True:
        valid = True
        bits = subset
        while bits:
            bit = bits & -bits
            index = bit.bit_length() - 1
            if (subset ^ bit) & conflicts[index]:
                valid = False
                break
            bits ^= bit
        if valid:
            unchosen = active_mask ^ subset
            bits = unchosen
            while bits:
                bit = bits & -bits
                index = bit.bit_length() - 1
                if not subset & conflicts[index]:
                    valid = False
                    break
                bits ^= bit
        if valid:
            maximal.append(subset)
        if subset == 0:
            break
        subset = (subset - 1) & active_mask
    return tuple(sorted(maximal))


def task_loss_units(alpha: int, coefficients: tuple[int, ...], matching_mask: int) -> int:
    total = alpha
    bits = matching_mask
    while bits:
        bit = bits & -bits
        total += coefficients[bit.bit_length() - 1]
        bits ^= bit
    return abs(total)


def summarize_totals(totals: list[int]) -> dict[str, Any]:
    if not totals:
        raise ValueError("a selected set must have at least one priority permutation")
    count = len(totals)
    mean = Fraction(sum(totals), count * SCALE)
    second_moment = Fraction(sum(value * value for value in totals), count * SCALE * SCALE)
    variance = second_moment - mean * mean
    if variance < 0:
        raise AssertionError("exact variance cannot be negative")
    minimum = Fraction(min(totals), SCALE)
    maximum = Fraction(max(totals), SCALE)
    with localcontext() as context:
        context.prec = 40
        sd = (Decimal(variance.numerator) / Decimal(variance.denominator)).sqrt()
        sd_text = f"{sd:.8f}"
    return {
        "permutation_count": count,
        "mean_fraction": fraction_string(mean),
        "variance_fraction": fraction_string(variance),
        "standard_deviation_decimal": sd_text,
        "minimum_fraction": fraction_string(minimum),
        "maximum_fraction": fraction_string(maximum),
        "range_fraction": fraction_string(maximum - minimum),
    }


def _load_issue99_runner():
    sys.path.insert(0, str(ROOT / "src"))
    path = ROOT / "experiments/add-only-greedy-issue99/run_issue99.py"
    spec = importlib.util.spec_from_file_location("ess_issue99_train_runner", path)
    if spec is None or spec.loader is None:
        raise ImportError("could not load the frozen Issue #99 runner")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _load_pinned_reference(advisor_source: Path, pinned_commit: str):
    """Load only model/reference from a checkout matching the frozen source blobs."""
    package_root = advisor_source.resolve(strict=True) / "src/pess_ess"
    if not package_root.is_dir():
        raise ValueError("--advisor-source must contain src/pess_ess")
    verified = {}
    for relative in ("src/pess_ess/model.py", "src/pess_ess/reference.py"):
        expected = subprocess.run(
            ["git", "show", f"{pinned_commit}:{relative}"],
            cwd=advisor_source,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        ).stdout
        actual = (advisor_source / relative).read_bytes()
        if actual != expected:
            raise ValueError(f"Advisor file differs from frozen commit: {relative}")
        verified[relative] = sha256_bytes(actual)

    # Avoid importing Advisor's optional SciPy-backed solver package: the
    # exact model and independent reference modules themselves use stdlib only.
    package = types.ModuleType("pess_ess")
    package.__path__ = [str(package_root)]
    package.__package__ = "pess_ess"
    sys.modules["pess_ess"] = package
    model = importlib.import_module("pess_ess.model")
    reference = importlib.import_module("pess_ess.reference")
    return model, reference, verified


def _frozen_set_id(selected: tuple[str, ...]) -> str:
    return "M:empty" if not selected else "M:" + ",".join(selected)


def _load_frozen_inputs(runner: Any) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    frozen = json.loads(FROZEN_PATH.read_text(encoding="utf-8"))
    if frozen.get("status") != "COMPLETE" or frozen.get("split") != "train":
        raise ValueError("frozen Issue #99 train selections are not complete")
    if frozen.get("nontrain_labels_or_test_explain_used") is not False:
        raise ValueError("frozen selection manifest does not certify train-only fitting")
    all_cases = {dataset: [] for dataset in DATASETS}
    for row in frozen.get("cases", []):
        if row.get("dataset") not in all_cases or row.get("split") != "train" or row.get("status") != "COMPLETE":
            raise ValueError("frozen case list contains a non-train or incomplete case")
        if not isinstance(row.get("selected_ids"), list):
            raise ValueError("frozen case is missing its selected set")
        all_cases[row["dataset"]].append(row)
    if any(len(rows) != 10 for rows in all_cases.values()):
        raise ValueError("frozen Issue #99 manifest must contain ten cases per dataset")
    return frozen, all_cases


def _verify_selection_run(dataset: str, frozen_dataset: dict[str, Any], rows: list[dict[str, Any]], runs: Path) -> None:
    run_id = frozen_dataset["selection_run_id"]
    root = runs / run_id
    if root.is_symlink() or not root.is_dir() or root.resolve(strict=True).parent != runs.resolve(strict=True):
        raise ValueError(f"{dataset} selection run is not a direct Issue #99 runtime child")
    manifest_path = root / "selection-manifest.json"
    if sha256_file(manifest_path) != frozen_dataset["selection_manifest_sha256"]:
        raise ValueError(f"{dataset} frozen selection manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if (manifest.get("dataset") != dataset or manifest.get("split") != "train"
            or manifest.get("status") != "COMPLETE"
            or manifest.get("collection_run_id") != frozen_dataset["collection_run_id"]):
        raise ValueError(f"{dataset} selection manifest scope mismatch")
    records = [json.loads(line) for line in (root / "case-results.jsonl").read_text(encoding="utf-8").splitlines() if line]
    by_id = {row["case_id"]: row for row in records}
    if len(by_id) != 10 or len(records) != 10:
        raise ValueError(f"{dataset} selection run does not have ten distinct cases")
    for frozen_case in rows:
        actual = by_id.get(frozen_case["case_id"])
        if actual is None or actual.get("selected_ids") != frozen_case["selected_ids"]:
            raise ValueError(f"{frozen_case['case_id']} selected-set evidence mismatch")
        if actual.get("objective_fraction") != frozen_case.get("objective_fraction"):
            raise ValueError(f"{frozen_case['case_id']} frozen objective mismatch")
        if actual.get("input_hashes") != frozen_case.get("input_hashes"):
            raise ValueError(f"{frozen_case['case_id']} frozen input hashes mismatch")


def _load_train_inputs(dataset: str, frozen_dataset: dict[str, Any], rows: list[dict[str, Any]], runner: Any, runs: Path):
    collection_root = runs / frozen_dataset["collection_run_id"]
    if collection_root.is_symlink() or not collection_root.is_dir() or collection_root.resolve(strict=True).parent != runs.resolve(strict=True):
        raise ValueError(f"{dataset} collection is not a direct Issue #99 runtime child")
    manifest_path = collection_root / "collection-manifest.json"
    if sha256_file(manifest_path) != frozen_dataset["collection_manifest_sha256"]:
        raise ValueError(f"{dataset} collection manifest hash mismatch")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("dataset") != dataset or manifest.get("split") != "train" or manifest.get("status") != "COMPLETE":
        raise ValueError(f"{dataset} collection is not a complete train collection")
    protocol = runner.PROTOCOL
    source_pin = protocol["source_pins"]
    if (manifest.get("workload_pickle_sha256") != source_pin["train_workload_hashes"][dataset]
            or manifest.get("label_pickle_sha256") != source_pin["train_label_hashes"][dataset]):
        raise ValueError(f"{dataset} archived train input hashes differ from Issue #99 protocol")

    queries, candidates, eligible = runner._load_train_workload_only(dataset, Path("."))
    if len(queries) != manifest.get("train_query_count"):
        raise ValueError(f"{dataset} train workload count mismatch")
    candidate_ids = [candidate["id"] for candidate in candidates]
    candidate_map_rows = [{"id": candidate["id"], "endpoints": candidate["endpoints"]} for candidate in candidates]
    candidate_map_hash = sha256_bytes(json.dumps(candidate_map_rows, ensure_ascii=True, separators=(",", ":")).encode())
    candidate_file = collection_root / "train/candidate-map.json"
    if not candidate_file.is_file() or json.loads(candidate_file.read_text(encoding="utf-8")) != candidate_map_rows:
        raise ValueError(f"{dataset} candidate map differs from the train workload")
    if candidate_map_hash != manifest["candidate_map_sha256"]:
        raise ValueError(f"{dataset} candidate map hash differs from the collection manifest")
    support_path = collection_root / "train/candidate-support.json"
    support = json.loads(support_path.read_text(encoding="utf-8"))
    expected_support = [{"id": candidate["id"], "train_query_count": candidate["train_query_count"]} for candidate in candidates]
    if support != expected_support:
        raise ValueError(f"{dataset} support map differs from the train workload")
    support_hash = sha256_bytes(json.dumps(expected_support, ensure_ascii=True, separators=(",", ":")).encode())
    if support_hash != manifest["train_support_map_sha256"]:
        raise ValueError(f"{dataset} support map hash differs from the collection manifest")

    truth = runner._load_train_truth(collection_root, queries, manifest)
    count = len(queries)
    empty: list[str | None] = [None] * count
    singleton: dict[str, list[str | None]] = {candidate_id: [None] * count for candidate_id in candidate_ids}
    observation_files = []
    observed = 0
    worker_ids = sorted(worker.get("worker_id") for worker in manifest.get("workers", []))
    if worker_ids != list(range(manifest.get("parallelism", 0))):
        raise ValueError(f"{dataset} worker IDs do not match collection parallelism")
    expected_oid = manifest["sample"]["header"]["relation_oid"]
    for worker_id in worker_ids:
        worker_path = collection_root / "observations" / f"worker{worker_id}-manifest.json"
        worker_manifest = json.loads(worker_path.read_text(encoding="utf-8"))
        if worker_manifest.get("worker_id") != worker_id:
            raise ValueError(f"{dataset} worker manifest ID mismatch")
        parts = worker_manifest.get("parts", [])
        if worker_manifest.get("committed_observation_count") != sum(part["rows"] for part in parts):
            raise ValueError(f"{dataset} worker committed row count mismatch")
        for part in parts:
            path = collection_root / "observations" / part["path"]
            if path.is_symlink() or not path.is_file() or sha256_file(path) != part["sha256"]:
                raise ValueError(f"{dataset} observation part hash mismatch: {part['path']}")
            observation_files.append({"path": str(path.relative_to(collection_root)), "sha256": part["sha256"], "rows": part["rows"]})
            part_rows = 0
            with gzip.open(path, "rt", encoding="utf-8") as stream:
                for line in stream:
                    row = json.loads(line)
                    part_rows += 1
                    observed += 1
                    if row.get("status") != "SUCCESS" or row.get("diagnostics_status") != "complete":
                        raise ValueError(f"{dataset} contains a non-success train observation")
                    index = row.get("source_index")
                    if (isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < count
                            or row.get("query_id") != queries[index]["query_id"]):
                        raise ValueError(f"{dataset} observation has an invalid train task identity")
                    if row.get("relation_oid") != expected_oid:
                        raise ValueError(f"{dataset} observation OID differs from the frozen sample")
                    raw = str(row.get("nrows_preclamp"))
                    estimate = Decimal(raw)
                    if not estimate.is_finite() or estimate < 0:
                        raise ValueError(f"{dataset} invalid train pre-clamp estimate")
                    config = row.get("configuration_id")
                    target = empty if config == "Empty" else singleton.get(config)
                    if target is None:
                        raise ValueError(f"{dataset} unknown singleton configuration {config}")
                    if target[index] is not None:
                        raise ValueError(f"{dataset} duplicate train observation for {row['query_id']}/{config}")
                    if config != "Empty" and config not in eligible[queries[index]["query_id"]]:
                        raise ValueError(f"{dataset} singleton outside train task eligibility")
                    target[index] = raw
            if part_rows != part["rows"]:
                raise ValueError(f"{dataset} observation part row count mismatch")
    if any(value is None for value in empty):
        raise ValueError(f"{dataset} train baseline does not cover all tasks")
    for candidate in candidates:
        cid = candidate["id"]
        expected = candidate["train_query_count"]
        if sum(value is not None for value in singleton[cid]) != expected:
            raise ValueError(f"{dataset}/{cid} singleton count differs from frozen train support")
    if observed != manifest["expected_observations"] or observed != manifest["completed_observations"]:
        raise ValueError(f"{dataset} raw observation count differs from complete manifest")
    observation_aggregate = sha256_bytes(json.dumps(observation_files, ensure_ascii=True, sort_keys=True, separators=(",", ":")).encode())
    if observation_aggregate != frozen_dataset["observation_aggregate_sha256"]:
        raise ValueError(f"{dataset} raw observation aggregate differs from frozen Issue #99 source")
    return collection_root, manifest, queries, candidates, eligible, truth, empty, singleton, observation_aggregate


def _scenario_state(selected: tuple[str, ...], candidates_by_id: dict[str, dict[str, Any]]) -> dict[str, Any]:
    endpoints = [tuple(candidates_by_id[item]["endpoints"]) for item in selected]
    orders = tuple(itertools.permutations(range(len(selected))))
    if not orders:
        orders = ((),)
    return {
        "selected_ids": list(selected),
        "set_id": _frozen_set_id(selected),
        "endpoints": endpoints,
        "orders": orders,
        "outcome_cache": {},
        "maximal_cache": {},
        "all_matching_cache": {},
        "verified_active_masks": set(),
        "totals": [0] * len(orders),
        "pess_total_units": 0,
        "reference_nominal_total_units": 0,
        "reference_pess_total_units": 0,
        "selected": frozenset(selected),
        "nominal_order": selected,
        "canonical_order_index": 0,
    }


def _evaluate_dataset(
    dataset: str,
    frozen_dataset: dict[str, Any],
    frozen_rows: list[dict[str, Any]],
    runner: Any,
    model_module: Any,
    reference_module: Any,
    runs: Path,
) -> dict[str, Any]:
    _verify_selection_run(dataset, frozen_dataset, frozen_rows, runs)
    (collection_root, collection, queries, candidates, eligible, truth, empty,
     singleton, observations_aggregate) = _load_train_inputs(dataset, frozen_dataset, frozen_rows, runner, runs)
    candidate_ids = [candidate["id"] for candidate in candidates]
    candidates_by_id = {candidate["id"]: candidate for candidate in candidates}
    unique_sets = sorted({tuple(candidate_id for candidate_id in candidate_ids if candidate_id in set(row["selected_ids"]))
                          for row in frozen_rows}, key=lambda values: (len(values), values))
    states = {selected: _scenario_state(selected, candidates_by_id) for selected in unique_sets}
    state_instances = {}
    for selected, state in states.items():
        advisor_candidates = tuple(
            model_module.Candidate(item, f"public.{dataset}", tuple(candidates_by_id[item]["endpoints"]), Fraction(1))
            for item in selected
        )
        state_instances[selected] = model_module.Instance(advisor_candidates, (), Fraction(0))

    model_hash = hashlib.sha256()
    alpha_zero = 0
    correction_count = 0
    clamp = dataset == "census13"
    selected_union = {item for selected in unique_sets for item in selected}
    for index, query in enumerate(queries):
        query_id = query["query_id"]
        raw_n0 = Decimal(empty[index])
        if raw_n0 == 0:
            alpha_zero += 1
        if clamp:
            model_n0 = max(Decimal(1), raw_n0)
        else:
            if raw_n0 <= 0:
                raise ValueError(f"{dataset} positive-preclamp model has nonpositive train baseline")
            model_n0 = raw_n0
        model_truth = max(1, truth[query_id])
        alpha = runner._log_ratio(model_n0, model_truth)
        alpha_units = exact_units(alpha)
        available = eligible[query_id]
        correction_json: dict[str, str] = {}
        selected_corrections: dict[str, int] = {}
        for candidate_id in available:
            raw_n1_text = singleton[candidate_id][index]
            if raw_n1_text is None:
                raise ValueError(f"{dataset} missing eligible train singleton {query_id}/{candidate_id}")
            raw_n1 = Decimal(raw_n1_text)
            if clamp:
                model_n1 = max(Decimal(1), raw_n1)
            else:
                if raw_n1 <= 0:
                    raise ValueError(f"{dataset} positive-preclamp model has nonpositive singleton")
                model_n1 = raw_n1
            correction = runner._log_ratio(model_n1, model_n0)
            correction_json[candidate_id] = correction
            correction_count += 1
            if candidate_id in selected_union:
                selected_corrections[candidate_id] = exact_units(correction)
        model_row = {"query_id": query_id, "alpha": alpha, "b": correction_json, "available_edges": list(available)}
        model_hash.update((json.dumps(model_row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode())
        available_set = set(available)

        for selected, state in states.items():
            active_mask = 0
            active_ids = []
            active_coefficients = [0] * len(selected)
            for edge_index, candidate_id in enumerate(selected):
                if candidate_id in available_set:
                    active_mask |= 1 << edge_index
                    active_ids.append(candidate_id)
                    active_coefficients[edge_index] = selected_corrections[candidate_id]
            outcomes = state["outcome_cache"].get(active_mask)
            if outcomes is None:
                outcomes = priority_matching_masks(active_mask, state["orders"], state["endpoints"])
                state["outcome_cache"][active_mask] = outcomes
            maximal = state["maximal_cache"].get(active_mask)
            if maximal is None:
                maximal = maximal_matching_masks(active_mask, state["endpoints"])
                state["maximal_cache"][active_mask] = maximal
            if active_mask not in state["verified_active_masks"]:
                if not set(outcomes) <= set(maximal):
                    raise AssertionError("priority policy produced a non-maximal eligible matching")
                state["verified_active_masks"].add(active_mask)
            all_matchings = state["all_matching_cache"].get(active_mask)
            if all_matchings is None:
                all_matchings = tuple(sorted(set(outcomes) | set(maximal)))
                state["all_matching_cache"][active_mask] = all_matchings
            coefficients = tuple(active_coefficients)
            loss_by_matching = {matching: task_loss_units(alpha_units, coefficients, matching)
                                for matching in all_matchings}
            for permutation_index, matching in enumerate(outcomes):
                state["totals"][permutation_index] += loss_by_matching[matching]
            own_pess = max(loss_by_matching[matching] for matching in maximal)
            state["pess_total_units"] += own_pess

            task = model_module.Task(
                query_id,
                f"public.{dataset}",
                Fraction(1),
                Fraction(alpha_units, SCALE),
                tuple(active_ids),
                {item: Fraction(selected_corrections[item], SCALE) for item in active_ids},
            )
            selected_set = state["selected"]
            source_pess, _ = reference_module.reference_task_loss(
                state_instances[selected], task, selected_set
            )
            source_pess_units = exact_units(source_pess)
            if source_pess_units != own_pess:
                raise AssertionError(f"{dataset} optimized/reference PESS task mismatch at {query_id}/{state['set_id']}")
            state["reference_pess_total_units"] += source_pess_units

            canonical_mask = outcomes[state["canonical_order_index"]]
            source_nominal, source_matching = reference_module.reference_nominal_task_loss(
                state_instances[selected], task, selected_set, state["nominal_order"]
            )
            source_nominal_units = exact_units(source_nominal)
            if source_nominal_units != loss_by_matching[canonical_mask]:
                raise AssertionError(f"{dataset} optimized/reference Nominal task mismatch at {query_id}/{state['set_id']}")
            expected_matching = frozenset(selected[bit] for bit in range(len(selected)) if canonical_mask & (1 << bit))
            if source_matching != expected_matching:
                raise AssertionError(f"{dataset} Nominal matching differs from frozen global priority semantics")
            state["reference_nominal_total_units"] += source_nominal_units

        if (index + 1) % 10000 == 0:
            print(json.dumps({"event": "progress", "dataset": dataset, "tasks": index + 1,
                              "task_count": len(queries)}, separators=(",", ":")), flush=True)

    expected_fit = frozen_dataset["model_fit"]
    if model_hash.hexdigest() != expected_fit["coefficient_digest_sha256"]:
        raise ValueError(f"{dataset} reconstructed model digest differs from frozen Issue #99")
    if correction_count != expected_fit["coefficient_count"]:
        raise ValueError(f"{dataset} reconstructed coefficient count differs from frozen Issue #99")
    if len(queries) != expected_fit["task_count"]:
        raise ValueError(f"{dataset} train task count differs from frozen Issue #99")

    scenario_results = {}
    for selected, state in states.items():
        statistics = summarize_totals(state["totals"])
        nominal_units = state["totals"][state["canonical_order_index"]]
        if nominal_units != state["reference_nominal_total_units"]:
            raise AssertionError(f"{dataset} total fixed Nominal mismatch for {state['set_id']}")
        if state["pess_total_units"] != state["reference_pess_total_units"]:
            raise AssertionError(f"{dataset} total fixed PESS mismatch for {state['set_id']}")
        nominal = Fraction(nominal_units, SCALE)
        pess = Fraction(state["pess_total_units"], SCALE)
        maximum = Fraction(max(state["totals"]), SCALE)
        mean = Fraction(statistics["mean_fraction"])
        if mean > maximum or maximum > pess:
            raise AssertionError(f"{dataset} expectation/global maximum/PESS bound failed for {state['set_id']}")
        stats_with_bounds = {
            **statistics,
            "nominal_fraction": fraction_string(nominal),
            "pess_fraction": fraction_string(pess),
            "max_minus_mean_fraction": fraction_string(maximum - mean),
            "pess_minus_max_fraction": fraction_string(pess - maximum),
            "unique_global_loss_count": len(set(state["totals"])),
            "task_matching_multiplicity_note": "All |M|! permutations contribute individually, including repeated induced matchings.",
        }
        scenario_results[state["set_id"]] = {
            "set_id": state["set_id"],
            "selected_ids": list(selected),
            "selected_count": len(selected),
            **stats_with_bounds,
        }

    case_results = []
    for row in frozen_rows:
        selected = tuple(item for item in candidate_ids if item in set(row["selected_ids"]))
        result = scenario_results[_frozen_set_id(selected)]
        frozen_value = Fraction(row["objective_fraction"])
        computed = Fraction(result["nominal_fraction"] if row["objective"] == "nominal" else result["pess_fraction"])
        if frozen_value != computed:
            raise ValueError(f"{row['case_id']} frozen objective does not match recomputed exact train value")
        case_results.append({
            "case_id": row["case_id"], "dataset": dataset, "budget": row["budget"],
            "objective": row["objective"], "selected_ids": row["selected_ids"],
            "set_id": result["set_id"], "frozen_objective_fraction": row["objective_fraction"],
        })

    budget_results = []
    for budget in BUDGETS:
        nominal_row = next(row for row in frozen_rows if row["budget"] == budget and row["objective"] == "nominal")
        pess_row = next(row for row in frozen_rows if row["budget"] == budget and row["objective"] == "pess")
        nominal_selected = tuple(item for item in candidate_ids if item in set(nominal_row["selected_ids"]))
        pess_selected = tuple(item for item in candidate_ids if item in set(pess_row["selected_ids"]))
        nominal_result = scenario_results[_frozen_set_id(nominal_selected)]
        pess_result = scenario_results[_frozen_set_id(pess_selected)]
        paired = {
            "mean_pess_selected_minus_nominal_selected_fraction": fraction_string(
                Fraction(pess_result["mean_fraction"]) - Fraction(nominal_result["mean_fraction"])
            ),
            "global_max_pess_selected_minus_nominal_selected_fraction": fraction_string(
                Fraction(pess_result["maximum_fraction"]) - Fraction(nominal_result["maximum_fraction"])
            ),
            "taskwise_pess_bound_pess_selected_minus_nominal_selected_fraction": fraction_string(
                Fraction(pess_result["pess_fraction"]) - Fraction(nominal_result["pess_fraction"])
            ),
            "selected_sets_equal": nominal_selected == pess_selected,
        }
        if nominal_selected == pess_selected and any(Fraction(value) != 0 for key, value in paired.items() if key.endswith("fraction")):
            raise AssertionError("identical Nominal/PESS selected sets must have identical paired results")
        budget_results.append({
            "budget": budget,
            "nominal_selected_ids": list(nominal_selected),
            "nominal_set_id": nominal_result["set_id"],
            "nominal_frozen_objective_fraction": nominal_row["objective_fraction"],
            "nominal_set_metrics": nominal_result,
            "pess_selected_ids": list(pess_selected),
            "pess_set_id": pess_result["set_id"],
            "pess_frozen_objective_fraction": pess_row["objective_fraction"],
            "pess_set_metrics": pess_result,
            "paired_contrast": paired,
        })

    return {
        "dataset": dataset,
        "train_task_count": len(queries),
        "unique_selected_set_count": len(unique_sets),
        "candidate_count": len(candidates),
        "input_provenance": {
            "collection_run_id": frozen_dataset["collection_run_id"],
            "collection_manifest_sha256": frozen_dataset["collection_manifest_sha256"],
            "selection_run_id": frozen_dataset["selection_run_id"],
            "selection_manifest_sha256": frozen_dataset["selection_manifest_sha256"],
            "workload_pickle_sha256": collection["workload_pickle_sha256"],
            "label_pickle_sha256": collection["label_pickle_sha256"],
            "train_truth_gzip_sha256": collection["train_truth"]["sha256"],
            "train_truth_values_sha256": collection["train_truth"]["canonical_values_sha256"],
            "candidate_map_sha256": collection["candidate_map_sha256"],
            "train_support_map_sha256": collection["train_support_map_sha256"],
            "observation_aggregate_sha256": observations_aggregate,
            "reconstructed_coefficient_digest_sha256": model_hash.hexdigest(),
        },
        "model_fit_checks": {
            "task_count": len(queries),
            "coefficient_count": correction_count,
            "coefficient_digest_matches_frozen": True,
            "transform": expected_fit["transform"],
            "quantization": expected_fit["logs"],
        },
        "sets": [scenario_results[_frozen_set_id(selected)] for selected in unique_sets],
        "budgets": budget_results,
        "frozen_cases": case_results,
    }


def _build_report(summary: dict[str, Any]) -> str:
    lines = [
        "# Issue #103 — OID-priority permutation uncertainty",
        "",
        "**Evidence label: experimentally observed, offline exact train-model calculation.** This is a counterfactual uniform distribution over global priority permutations, not an empirical PostgreSQL OID distribution.",
        "",
        "## Method and scope",
        "",
        f"The analysis used the four frozen Issue #99 training models ({summary['train_queries_per_dataset']:,} tasks per dataset), the exact frozen Nominal/PESS resource sets at B=0,2,3,4,5, and all distinct resource sets ({summary['unique_selected_sets']} total). It enumerated every global priority permutation for each set, applying the same deterministic greedy inclusion-maximal matching on each task’s statically eligible selected edges. Permutation multiplicity was retained even when orders induced the same task matching.",
        "",
        "Coefficients were reconstructed from the pinned train workload, train truth, and Issue #99 raw singleton/baseline observations using the Issue #99 log transform and 1e-18 quantization. Each full coefficient digest matched the frozen train-model digest. For every task and selected set, the optimized integer-scaled calculation was compared with the pinned Advisor exact Fraction reference routines for both fixed-priority Nominal loss and task-wise PESS loss. Every frozen selection objective also matched exactly.",
        "",
        "The comparison remains within the Issue #99 pre-clamp/clamped-log train model. To rebuild train task applicability, the trusted Issue #99 workload pickle was deserialized as a split container and only its `train` member was explicitly selected; no labels pickle was opened. No PostgreSQL query, ANALYZE, OID DDL, refitting, reselection, Issue #101 artifact, held-out label, or test outcome was read or run.",
        "",
        "## Results",
        "",
        "The following values are shown as decimals for readability; exact fractions for means, variances, extrema, Nominal values, PESS bounds, and paired contrasts are in `summary-v1.json`.",
        "",
    ]
    for dataset in summary["datasets"]:
        lines.extend([f"### {dataset['dataset']}", "", "| B | Nominal-selected M | E[L] ± SD; [min, max] | N(M) | P(M) | PESS-selected M | E[L] ± SD; [min, max] | N(M) | P(M) | ΔE (PESS set − Nominal set) |", "|---:|---|---:|---:|---:|---|---:|---:|---:|---:|"])
        for row in dataset["budgets"]:
            n = row["nominal_set_metrics"]
            p = row["pess_set_metrics"]
            n_ids = ", ".join(row["nominal_selected_ids"]) or "∅"
            p_ids = ", ".join(row["pess_selected_ids"]) or "∅"
            n_summary = f"{decimal_string(Fraction(n['mean_fraction']))} ± {n['standard_deviation_decimal']}; [{decimal_string(Fraction(n['minimum_fraction']))}, {decimal_string(Fraction(n['maximum_fraction']))}]"
            p_summary = f"{decimal_string(Fraction(p['mean_fraction']))} ± {p['standard_deviation_decimal']}; [{decimal_string(Fraction(p['minimum_fraction']))}, {decimal_string(Fraction(p['maximum_fraction']))}]"
            lines.append(f"| {row['budget']} | {{{n_ids}}} | {n_summary} | {decimal_string(Fraction(n['nominal_fraction']))} | {decimal_string(Fraction(n['pess_fraction']))} | {{{p_ids}}} | {p_summary} | {decimal_string(Fraction(p['nominal_fraction']))} | {decimal_string(Fraction(p['pess_fraction']))} | {decimal_string(Fraction(row['paired_contrast']['mean_pess_selected_minus_nominal_selected_fraction']))} |")
        lines.append("")
    lines.extend([
        "## Interpretation and limits",
        "",
        "For every evaluated set, the exact calculation satisfies `Eπ L(M,π) ≤ maxπ L(M,π) ≤ P(M)`. The second inequality is conditional on each priority-induced scheme belonging to the frozen inclusion-maximal matching family, which is how the analysis constructs it. `P(M)` is task-wise adversarial and can exceed the maximum under one shared global permutation. Uniform priority permutations also do not imply uniform probabilities over task matchings.",
        "",
        "The Nominal priority is the frozen candidate-ID order used by Issue #99; it is one counterfactual order in this analysis, not a claim about an observed PostgreSQL OID order. Results describe training-model loss only and do not establish actual PostgreSQL choice probabilities, held-out generalization, or a universal Nominal/PESS winner.",
        "",
        "## Reproduction and provenance",
        "",
        f"- Analysis source commit: `{summary['analysis_source_commit']}`; analysis script SHA-256: `{summary['analysis_script_sha256']}`.",
        f"- Frozen selection SHA-256: `{summary['frozen_selection_sha256']}`; Issue #99 protocol-v4 SHA-256: `{summary['issue99_protocol_sha256']}`.",
        f"- Advisor reference source commit: `{summary['advisor_reference_commit']}`; `model.py` SHA-256: `{summary['advisor_reference_file_sha256']['src/pess_ess/model.py']}`; `reference.py` SHA-256: `{summary['advisor_reference_file_sha256']['src/pess_ess/reference.py']}`.",
        f"- Python: `{summary['python_version']}`. Summary JSON contains per-dataset runtime IDs, source hashes, model digest checks, exact fractions, all 40 frozen case mappings, and paired contrasts.",
        "- The workload pickle deserializer materialized its split container; the script explicitly iterated only its train split. The labels pickle was not opened. The analysis reads no Issue #101 runtime path or test-split outcome artifact.",
        "",
    ])
    return "\n".join(lines)


def run(advisor_source: Path, output_json: Path, output_report: Path) -> dict[str, Any]:
    if not os.environ.get("ESS_DATA_ROOT") or not os.environ.get("ESS_RUNTIME_PARENT"):
        raise ValueError("ESS_DATA_ROOT and ESS_RUNTIME_PARENT must be initialized in this shell")
    runner = _load_issue99_runner()
    frozen, cases_by_dataset = _load_frozen_inputs(runner)
    pinned_advisor = runner.PROTOCOL["source_pins"]["advisor_source_commit"]
    model_module, reference_module, advisor_hashes = _load_pinned_reference(advisor_source, pinned_advisor)
    runs = (Path(os.environ["ESS_RUNTIME_PARENT"]) / "ess-research/issue99/runs").resolve(strict=True)
    dataset_results = []
    for dataset in DATASETS:
        print(json.dumps({"event": "dataset_started", "dataset": dataset}, separators=(",", ":")), flush=True)
        dataset_results.append(_evaluate_dataset(
            dataset, frozen["datasets"][dataset], cases_by_dataset[dataset], runner,
            model_module, reference_module, runs,
        ))
        print(json.dumps({"event": "dataset_complete", "dataset": dataset}, separators=(",", ":")), flush=True)
    summary = {
        "format": "ess-issue103-oid-priority-permutation-summary-v1",
        "issue": 103,
        "status": "COMPLETE",
        "run_id": datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ-issue103-offline-exact"),
        "analysis_source_commit": subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, stdout=subprocess.PIPE, text=True).stdout.strip(),
        "analysis_script_sha256": sha256_file(Path(__file__).resolve()),
        "frozen_selection_sha256": sha256_file(FROZEN_PATH),
        "issue99_protocol_sha256": sha256_file(PROTOCOL_PATH),
        "issue99_builder_sha256": sha256_file(ROOT / "experiments/add-only-greedy-issue99/run_issue99.py"),
        "advisor_reference_commit": pinned_advisor,
        "advisor_reference_file_sha256": advisor_hashes,
        "python_version": platform.python_version(),
        "train_queries_per_dataset": runner.PROTOCOL["scientific_scope"]["train_queries_per_dataset"],
        "datasets_analyzed": list(DATASETS),
        "budgets": list(BUDGETS),
        "uniform_global_permutation_model": True,
        "permutation_multiplicity_retained": True,
        "heldout_labels_or_issue101_outcomes_read": False,
        "issue101_artifacts_read": False,
        "nontrain_workload_container_materialized_by_pickle": True,
        "train_split_explicitly_selected": True,
        "label_pickle_opened": False,
        "postgresql_commands_run": False,
        "unique_selected_sets": sum(item["unique_selected_set_count"] for item in dataset_results),
        "datasets": dataset_results,
    }
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    output_report.write_text(_build_report(summary), encoding="utf-8")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--advisor-source", type=Path, required=True, help="ess-advisor checkout containing the Issue #99 pinned source commit")
    parser.add_argument("--output-json", type=Path, default=HERE / "summary-v1.json")
    parser.add_argument("--output-report", type=Path, default=HERE / "findings-v1.md")
    args = parser.parse_args()
    summary = run(args.advisor_source, args.output_json, args.output_report)
    print(json.dumps({"event": "analysis_complete", "status": summary["status"],
                      "summary": str(args.output_json), "report": str(args.output_report)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
