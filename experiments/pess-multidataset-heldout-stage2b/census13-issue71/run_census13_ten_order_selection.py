"""Rebuild Census13 clamped-log-v2 models, then exactly enumerate ten orders."""

from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import resource
import sys
import time
import traceback
from fractions import Fraction
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))

import fit_census13_valid_and_freeze as fit
import run_census13_smoke as smoke
from exact_nominal_selection import exact_select_nominal_many
from ess_research.arecel.archive import prepare_valid_workload

FROZEN_SINGLE = HERE / "census13-clamped-log-v2-schema-order-frozen-selection-v1.json"
FINAL_OUTPUT = HERE / "census13-clamped-log-v2-ten-order-selection-v1.json"
EXPECTED_COEFFICIENT_SHA = "7671c4d8837c4f63423bb4a0cf1a132923301ef4f6d04cdf5ee380dfe6cbc0a5"
EXPECTED_ORDER_LABELS = ["schema_order", "complete_reverse",
                        *(f"python_random_seed_{i}" for i in range(8))]

_MODELS = None
_CANDIDATES = None
_CANDIDATE_ENDPOINTS = None
_PESS = None
_RUN_OUTPUT = None


def canonical_json_sha(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _write_json(path: Path, value: Any) -> None:
    temp = path.with_suffix(path.suffix + f".{os.getpid()}.tmp")
    temp.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.replace(temp, path)


def _worker(order: dict[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    label = order["label"]
    path = _RUN_OUTPUT / f"{label}.json"
    try:
        ids = order["candidate_ids"]
        by_id = {edge: endpoints for edge, endpoints in _CANDIDATES}
        ordered_candidates = [(edge, by_id[edge]) for edge in ids]
        nominal = exact_select_nominal_many(_MODELS, ordered_candidates, (0, 2, 3))

        pess_results = _PESS
        worst_cache: dict[tuple[str, ...], Fraction] = {}

        def pess_loss(selected: list[str]) -> Fraction:
            key = tuple(sorted(selected))
            if key not in worst_cache:
                worst_cache[key] = sum((
                    fit.forest10_exact_selection.model_loss(
                        model, key, "PESS", _CANDIDATE_ENDPOINTS,
                        tuple(edge for edge, _ in _CANDIDATES),
                    ) for model in _MODELS
                ), Fraction(0))
            return worst_cache[key]

        for budget in (0, 2, 3):
            row = nominal[str(budget)]
            pglobal = Fraction(pess_results[str(budget)]["objective_fraction"])
            selected_loss = pess_loss(row["selected"])
            regret = selected_loss - pglobal
            if regret < 0:
                raise ArithmeticError(f"negative exact PESS regret for {label}/B{budget}")
            row["selected_set_pess_worst_case_fraction"] = str(selected_loss)
            row["regret_vs_pess_global_fraction"] = str(regret)
            row["all_optimal_sets_pess_worst_case_fractions"] = [
                {"set": tied, "loss": str(pess_loss(tied))} for tied in row["all_optimal_sets"]
            ]

        result = {
            "order_label": label,
            "seed": order["seed"],
            "candidate_ids": ids,
            "order_sha256": canonical_json_sha(ids),
            "status": "PASS",
            "budgets": nominal,
            "elapsed_seconds": time.monotonic() - started,
            "process_max_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
            "peak_feasible_subset_count": nominal["3"]["feasible_subset_count"],
        }
        _write_json(path, result)
        return {"order_label": label, "status": "PASS", "path": str(path),
                "elapsed_seconds": result["elapsed_seconds"],
                "process_max_rss_mib": result["process_max_rss_mib"]}
    except BaseException as exc:
        failure = {"order_label": label, "status": "FAILED", "error": repr(exc),
                   "traceback": traceback.format_exc(),
                   "elapsed_seconds": time.monotonic() - started,
                   "process_max_rss_mib": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024}
        _write_json(path, failure)
        return {"order_label": label, "status": "FAILED", "path": str(path),
                "error": repr(exc), "elapsed_seconds": failure["elapsed_seconds"],
                "process_max_rss_mib": failure["process_max_rss_mib"]}


def _mem_available_bytes() -> int:
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable:"):
            return int(line.split()[1]) * 1024
    raise RuntimeError("MemAvailable is not available; refusing ten-process run")


def _build_inputs(run: Path) -> tuple[list[Any], list[tuple[str, tuple[str, str]]], dict[str, Any], dict[str, Any]]:
    verified = fit.verify(run)
    if verified.get("status") != "PASS" or verified.get("total_calls") != 288_849:
        raise ValueError("full valid observation verification failed")
    frozen = json.loads(FROZEN_SINGLE.read_text(encoding="utf-8"))
    if frozen.get("model_coefficient_sha256") != EXPECTED_COEFFICIENT_SHA:
        raise ValueError("frozen schema-order coefficient SHA is unexpected")
    if frozen.get("run_id") != run.name or frozen.get("zero_policy") != "clamped-log-v2":
        raise ValueError("frozen single-order baseline does not match run/policy")

    plan = json.loads(fit.PLAN.read_text(encoding="utf-8"))
    with prepare_valid_workload(issue=71, dataset="census13") as prepared:
        if prepared.manifest.get("labels_loaded") is not False:
            raise ValueError("valid workload loader unexpectedly read packaged labels")
        workload = json.loads(prepared.workload_path.read_text(encoding="utf-8"))
    queries = workload["queries"]
    truth = fit._valid_truth_from_official_sql(run, queries)
    empty_raw, singleton_raw = fit._load_observations(run)
    if len(queries) != 10_000 or len(empty_raw) != 10_000:
        raise ValueError("valid query/Empty input count mismatch")

    candidates = [(row["id"], tuple(row["endpoints"]))
                  for row in plan["candidate_policy"]["candidates"]]
    if len(candidates) != 78 or set(singleton_raw) != {edge for edge, _ in candidates}:
        raise ValueError("candidate/input coverage differs from frozen 78 candidates")
    available = {query["query_id"]: () for query in queries}
    with (run / "coverage.jsonl").open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            if row["query_id"] not in available:
                raise ValueError("coverage contains an unknown valid query")
            available[row["query_id"]] = tuple(row["eligible_config_ids"])
    if set(available) != set(truth):
        raise ValueError("eligibility and valid truth IDs differ")

    empty_fit = {qid: fit.clamp_fit_estimate(value) for qid, value in empty_raw.items()}
    singleton_fit = {edge: {qid: fit.clamp_fit_estimate(value) for qid, value in rows.items()}
                     for edge, rows in singleton_raw.items()}
    truth_fit = {qid: fit.clamp_fit_truth(value) for qid, value in truth.items()}

    helper_dir = run / "pinned-helpers"
    if fit.sha256_file(helper_dir / "forest10_runner.py") != "44d628108da4ca4e65c67fc4016891a99e35662067b1a9b381593ebb9d124e86":
        raise ValueError("pinned coefficient-builder SHA mismatch")
    sys.path.insert(0, str(helper_dir))
    import forest10_runner
    import forest10_exact_selection
    fit.forest10_exact_selection = forest10_exact_selection
    models = forest10_runner.build_task_models(
        tuple(query["query_id"] for query in queries), truth_fit, empty_fit,
        singleton_fit, available)
    model_digest = hashlib.sha256("\n".join(
        json.dumps({"alpha": str(model.alpha),
                    "b": {edge: str(value) for edge, value in sorted(model.b.items())},
                    "available_edges": model.available_edges}, sort_keys=True,
                   separators=(",", ":")) for model in models).encode()).hexdigest()
    if model_digest != EXPECTED_COEFFICIENT_SHA:
        raise ValueError(f"reconstructed model coefficient SHA mismatch: {model_digest}")

    orders = plan["nominal_priority_orders"]["orders"]
    if [row["label"] for row in orders] != EXPECTED_ORDER_LABELS:
        raise ValueError("frozen order labels/sequence differ")
    candidate_ids = [edge for edge, _ in candidates]
    if any(len(row["candidate_ids"]) != 78
           or set(row["candidate_ids"]) != set(candidate_ids) for row in orders):
        raise ValueError("frozen order is not an exact permutation of all 78 candidates")
    if len({canonical_json_sha(row["candidate_ids"]) for row in orders}) != 10:
        raise ValueError("frozen orders are duplicated")
    old_schema = frozen["nominal_by_order"]
    if len(old_schema) != 1 or old_schema[0]["order_label"] != "schema_order":
        raise ValueError("single-order frozen baseline is malformed")
    return models, candidates, frozen, {"plan": plan, "orders": orders,
                                        "verification": verified,
                                        "model_coefficient_sha256": model_digest,
                                        "old_schema": old_schema[0]}


def _validate_and_summarize(results: list[dict[str, Any]], frozen: dict[str, Any],
                            candidates: list[tuple[str, tuple[str, str]]]) -> dict[str, Any]:
    if len(results) != 10 or [row["order_label"] for row in results] != EXPECTED_ORDER_LABELS:
        raise ValueError("not all ten results are present in frozen order")
    if any(row.get("status") != "PASS" for row in results):
        raise RuntimeError("one or more exact enumeration tasks failed")
    pess = frozen["pess_global"]
    endpoint_map = dict(candidates)
    summary: dict[str, Any] = {}
    for budget in (0, 2, 3):
        key = str(budget)
        unique_sets: set[tuple[str, ...]] = set()
        objective_values: set[str] = set()
        positive_regrets = []
        method_matches = []
        overlapping_sets: set[tuple[str, ...]] = set()
        for result in results:
            row = result["budgets"][key]
            if row["feasible_subset_count"] != {0: 1, 2: 3_082, 3: 79_158}[budget]:
                raise ValueError(f"wrong exhaustive subset count for {result['order_label']}/B{budget}")
            objective_values.add(row["objective_fraction"])
            tied_canonical = {tuple(sorted(item)) for item in row["all_optimal_sets"]}
            unique_sets.update(tied_canonical)
            expected_pess = Fraction(pess[key]["objective_fraction"])
            for tied in row["all_optimal_sets_pess_worst_case_fractions"]:
                regret = Fraction(tied["loss"]) - expected_pess
                if regret < 0:
                    raise ArithmeticError("negative regret found in an exact result")
                if regret > 0:
                    positive_regrets.append({"order": result["order_label"],
                                             "set": tied["set"], "regret": str(regret)})
            pess_sets = {tuple(sorted(item)) for item in pess[key]["all_optimal_sets"]}
            method_matches.append({"order": result["order_label"],
                                   "same_optimal_set": tied_canonical == pess_sets})
            for selected in row["all_optimal_sets"]:
                vertices: set[str] = set()
                overlap = False
                for edge in selected:
                    pair = endpoint_map[edge]
                    if not vertices.isdisjoint(pair):
                        overlap = True
                    vertices.update(pair)
                if overlap:
                    overlapping_sets.add(tuple(sorted(selected)))
        summary[key] = {
            "distinct_nominal_optimal_sets": [list(row) for row in sorted(unique_sets)],
            "distinct_nominal_optimal_set_count": len(unique_sets),
            "distinct_nominal_objective_count": len(objective_values),
            "nominal_objective_fractions": sorted(objective_values, key=Fraction),
            "nominal_vs_pess_same_set_by_order": method_matches,
            "positive_pess_regrets": positive_regrets,
            "overlapping_optimal_resource_sets": [list(row) for row in sorted(overlapping_sets)],
        }
    return summary


def run(run: Path) -> dict[str, Any]:
    global _MODELS, _CANDIDATES, _CANDIDATE_ENDPOINTS, _PESS, _RUN_OUTPUT
    if FINAL_OUTPUT.exists():
        raise FileExistsError(FINAL_OUTPUT)
    run_id = "20261022-census13-ten-order-selection-v2"
    output_dir = Path(os.environ["ESS_RUNTIME_PARENT"]) / "ess-research" / "issue71" / "runs" / run_id
    output_dir.mkdir(parents=True, exist_ok=False)
    order_dir = output_dir / "orders"
    order_dir.mkdir()

    before_available = _mem_available_bytes()
    # The prior one-process exact run was observed at ~0.4 GiB RSS while hot.
    # Double that per-worker gives a conservative ~8 GiB for ten, below current
    # MemAvailable (>13 GiB), leaving >5 GiB for the OS and shared inputs.
    per_worker_budget = 800 * 1024**2
    workers = 10 if before_available >= workers_required_bytes(per_worker_budget, 10, 5 * 1024**3) else 8
    if workers < 10:
        if before_available < workers_required_bytes(per_worker_budget, workers, 5 * 1024**3):
            raise MemoryError("available memory is insufficient for even eight exact workers")

    models, candidates, frozen, context = _build_inputs(run)
    _MODELS = models
    _CANDIDATES = candidates
    _CANDIDATE_ENDPOINTS = dict(candidates)
    _PESS = frozen["pess_global"]
    _RUN_OUTPUT = order_dir
    orders = context["orders"]
    started = time.monotonic()
    _min_available = before_available
    _last_sample = started
    ctx = mp.get_context("fork")
    pool = ctx.Pool(processes=workers)
    async_rows = [(order, pool.apply_async(_worker, (order,))) for order in orders]
    pool.close()
    completed: dict[str, dict[str, Any]] = {}
    while len(completed) < len(async_rows):
        for order, async_result in async_rows:
            label = order["label"]
            if label in completed or not async_result.ready():
                continue
            try:
                completed[label] = async_result.get()
            except BaseException as exc:
                completed[label] = {"order_label": label, "status": "FAILED",
                                    "error": repr(exc)}
        now = time.monotonic()
        if now - _last_sample >= 1:
            _min_available = min(_min_available, _mem_available_bytes())
            _last_sample = now
        if len(completed) < len(async_rows):
            time.sleep(0.25)
    pool.join()
    elapsed = time.monotonic() - started

    per_order = []
    for order in orders:
        path = order_dir / f"{order['label']}.json"
        if not path.is_file():
            per_order.append({"order_label": order["label"], "status": "MISSING"})
        else:
            per_order.append(json.loads(path.read_text(encoding="utf-8")))
    summary_base = {
        "format": "ess-issue71-census13-clamped-log-v2-ten-order-selection-v1",
        "status": "PASS" if len(per_order) == 10 and all(r.get("status") == "PASS" for r in per_order) else "BLOCKED",
        "run_id": run_id,
        "workers": workers,
        "elapsed_seconds_total": elapsed,
        "memory_preflight": {
            "mem_available_before_bytes": before_available,
            "conservative_estimated_worker_rss_bytes": per_worker_budget,
            "estimated_ten_worker_total_bytes": 10 * per_worker_budget,
            "reserved_bytes": 5 * 1024**3,
            "minimum_mem_available_during_run_bytes": _min_available,
        },
        "input_plan_sha256": smoke.PLAN_SHA256,
        "valid_observation_raw_sha256": frozen["observation_sha256"],
        "valid_truth_sha256": frozen["valid_truth_sha256"],
        "model_coefficient_sha256": context["model_coefficient_sha256"],
        "pess_global_reused_from_frozen_result": frozen["pess_global"],
        "orders": per_order,
        "test_truth_or_outcomes_accessed": False,
    }
    if summary_base["status"] == "PASS":
        _validate_schema_replay(per_order[0], context["old_schema"])
        summary_base["aggregate"] = _validate_and_summarize(per_order, frozen, candidates)
    _write_json(output_dir / "summary.json", summary_base)
    if summary_base["status"] == "PASS":
        _write_json(FINAL_OUTPUT, summary_base)
    return summary_base


def workers_required_bytes(per_worker: int, count: int, reserve: int) -> int:
    return per_worker * count + reserve


def _validate_schema_replay(result: dict[str, Any], old: dict[str, Any]) -> None:
    if result["order_label"] != "schema_order":
        raise ValueError("first result is not schema_order")
    for budget in ("0", "2", "3"):
        new = result["budgets"][budget]
        prior = old["budgets"][budget]
        for field in ("objective_fraction", "tie_count", "all_optimal_sets", "selected",
                      "feasible_subset_count", "selected_set_pess_worst_case_fraction",
                      "regret_vs_pess_global_fraction",
                      "all_optimal_sets_pess_worst_case_fractions"):
            if new.get(field) != prior.get(field):
                raise ValueError(f"schema_order baseline mismatch at B={budget} field={field}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: run_census13_ten_order_selection.py RUN_DIR")
    result = run(Path(sys.argv[1]).resolve())
    print(json.dumps({"status": result["status"], "run_id": result["run_id"],
                      "workers": result["workers"],
                      "elapsed_seconds_total": result["elapsed_seconds_total"]}, sort_keys=True))
