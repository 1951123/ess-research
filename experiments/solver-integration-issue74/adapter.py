"""Thin, read-only adapters for the frozen Issue #64/#71 valid-only models.

This module imports no solver code and never reads test inputs.  The returned
objects use Advisor's schema-v1 request contract; solving is a separate step.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import re
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any

ADVISOR_COMMIT = "e7bb42f5b9ac3f09dd45e341e0e215153ad5f8ec"
FOREST_ROOT = Path("experiments/pess-multidataset-heldout-stage2b/generalization-issue64")
CENSUS_ROOT = Path("experiments/pess-multidataset-heldout-stage2b/census13-issue71")
FOREST_COLUMNS = (
    "Elevation", "Aspect", "Slope", "Horizontal_Distance_To_Hydrology",
    "Vertical_Distance_To_Hydrology", "Horizontal_Distance_To_Roadways",
    "Hillshade_9am", "Hillshade_Noon", "Hillshade_3pm",
    "Horizontal_Distance_To_Fire_Points",
)
QUANTUM = Decimal("0.000000000000000001")


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _sha256_gzip_payload(path: Path) -> str:
    h = hashlib.sha256()
    with gzip.open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _fraction(value: str | int) -> str:
    return str(Fraction(value))


def _edge_endpoints(edge_id: str, columns: tuple[str, ...]) -> list[str]:
    match = re.fullmatch(r"e(\d{2})_(\d{2})", edge_id)
    if not match:
        raise ValueError(f"invalid frozen candidate ID: {edge_id}")
    i, j = map(int, match.groups())
    if i >= j or j >= len(columns):
        raise ValueError(f"candidate index outside frozen schema: {edge_id}")
    return [columns[i], columns[j]]


def _request(model_version: str, table: str,
             candidate_defs: list[tuple[str, list[str]]], task_rows: list[dict[str, Any]],
             budget: int, *, calibration_id: str, research_commit: str,
             postgresql_source_commit: str | None, nominal_order: list[str]) -> dict[str, Any]:
    candidates = [{"id": edge, "table": table, "endpoints": endpoints,
                   "maintenance_cost": "1"} for edge, endpoints in candidate_defs]
    return {
        "schema_version": "1",
        "objective": "pess",
        "backend": "master_oracle",
        "input_provenance": {
            "model_version": model_version,
            "advisor_source_commit": ADVISOR_COMMIT,
            "research_source_commit": research_commit,
            "postgresql_source_commit": postgresql_source_commit,
            "calibration_id": calibration_id,
        },
        "instance": {
            "budget": str(budget),
            "candidates": candidates,
            "tasks": task_rows,
        },
        "_nominal_priority_order": nominal_order,
    }


def _task(query_id: str, alpha: str, corrections: dict[str, str], table: str) -> dict[str, Any]:
    return {"id": query_id, "table": table, "weight": "1", "alpha": alpha,
            "eligible_candidates": list(corrections), "corrections": corrections}


def forest10_request(repo: Path, budget: int = 0, *, task_limit: int | None = None) -> dict[str, Any]:
    root = repo / FOREST_ROOT
    frozen = _json(root / "forest10-valid-frozen-selection-v1.json")
    coeff = root / "coefficients.jsonl.gz"
    if sha256(coeff) != frozen["model"]["coefficient_artifact_sha256"]:
        raise ValueError("Forest10 frozen coefficient artifact SHA-256 mismatch")
    candidate_ids = frozen["inputs"]["candidate_order"]
    candidate_defs = [(edge, _edge_endpoints(edge, FOREST_COLUMNS)) for edge in candidate_ids]
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    total = 0
    with gzip.open(coeff, "rt", encoding="utf-8") as f:
        for line in f:
            record = json.loads(line)
            total += 1
            query_id = record.get("query_id")
            if not isinstance(query_id, str) or query_id in seen:
                raise ValueError("Forest10 coefficient query IDs are malformed or duplicated")
            seen.add(query_id)
            if record["target"] != max(1, record["valid_truth"]):
                raise ValueError("Forest10 frozen target differs from T=max(1,N)")
            if set(record["b_fraction"]) - set(candidate_ids):
                raise ValueError("Forest10 coefficient references an unknown candidate")
            for value in [record["alpha_fraction"], *record["b_fraction"].values()]:
                Fraction(value)
            corrections = {edge: _fraction(value) for edge, value in record["b_fraction"].items()}
            if task_limit is None or len(rows) < task_limit:
                rows.append(_task(query_id, _fraction(record["alpha_fraction"]), corrections,
                                  "public.forest10"))
    if total != 10_000:
        raise ValueError(f"Forest10 expected 10000 valid tasks; got {total}")
    selection = frozen["selection"]["results"]
    order = candidate_ids
    request = _request("forest10-positive-preclamp-v1",
        "public.forest10", candidate_defs, rows, budget, calibration_id="issue64-forest10-valid-v1",
        research_commit="a7aa91e10dd199fd8eb6e5cbaaf1f6e05a607207",
        postgresql_source_commit="f1bf37b5dd3d3a7087fc0af5de550ca31035854c", nominal_order=order)
    request["input_provenance"]["frozen_reference_sha256"] = sha256(root / "forest10-valid-frozen-selection-v1.json")
    request["input_provenance"]["coefficient_artifact_sha256"] = sha256(coeff)
    request["input_provenance"]["truth_provenance"] = frozen["inputs"]["valid_truth_source_member"]
    request["input_provenance"]["valid_truth_values_sha256"] = frozen["inputs"]["valid_truth_values_sha256"]
    request["input_provenance"]["arecel_archive_sha256"] = frozen["inputs"]["arecel_archive_sha256"]
    request["input_provenance"]["model_source_commit"] = "76106024611ae91505f1f05bdc35aed44d9c38c4"
    request["_frozen_selection"] = selection
    request["_candidate_ids"] = candidate_ids
    return request


def _census_coefficients(root: Path) -> tuple[list[str], dict[str, tuple[str, dict[str, str]]], dict[str, list[str]]]:
    """Recreate the frozen clamped-log-v2 rational coefficients and verify its digest."""
    plan = _json(root / "census13-stage2b-plan-v1.json")
    frozen = _json(root / "census13-clamped-log-v2-schema-order-frozen-selection-v1.json")
    if sha256(root / "census13-stage2b-plan-v1.json") != frozen["plan_sha256"]:
        raise ValueError("Census13 frozen plan SHA-256 mismatch")
    candidate_rows = plan["candidate_policy"]["candidates"]
    candidate_ids = [r["id"] for r in candidate_rows]
    endpoints = {r["id"]: list(r["endpoints"]) for r in candidate_rows}
    eligible: dict[str, list[str]] = {}
    estimates: dict[str, dict[str, Decimal]] = {"Empty": {}}
    for i in (0, 1):
        path = root / f"census13-full-valid-worker{i}.jsonl.gz"
        expected = frozen["observation_sha256"][f"worker{i}"]
        if _sha256_gzip_payload(path) != expected:
            raise ValueError(f"Census13 worker{i} observation SHA-256 mismatch")
        with gzip.open(path, "rt", encoding="utf-8") as f:
            for line in f:
                row = json.loads(line)
                if row.get("status") != "SUCCESS" or row.get("diagnostics_status") != "complete":
                    raise ValueError("Census13 frozen row is not a complete successful observation")
                query_id, edge = row["query_id"], row["config_id"]
                value = Decimal(row["nrows_preclamp"])
                if not value.is_finite() or value < 0:
                    raise ValueError("Census13 frozen estimate is not finite/nonnegative")
                if edge == "Empty":
                    if query_id in estimates["Empty"]:
                        raise ValueError("duplicate Census13 Empty observation")
                    estimates["Empty"][query_id] = value
                else:
                    if edge not in endpoints:
                        raise ValueError(f"unknown Census13 singleton candidate {edge}")
                    if query_id in estimates.setdefault(edge, {}):
                        raise ValueError("duplicate Census13 singleton observation")
                    estimates[edge][query_id] = value
                    eligible.setdefault(query_id, []).append(edge)
    truth_path = root / "census13-valid-truth-counts.jsonl"
    if sha256(truth_path) != frozen["valid_truth_sha256"]:
        raise ValueError("Census13 valid-truth SHA-256 mismatch")
    truths: dict[str, int] = {}
    for line in truth_path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        truths[row["query_id"]] = row["true_cardinality"]
    if len(truths) != 10_000 or set(truths) != set(estimates["Empty"]):
        raise ValueError("Census13 valid truth and Empty observations do not cover the same 10000 tasks")

    def clamped(value: Decimal | int) -> Decimal:
        return max(Decimal(1), Decimal(value))

    def log_ratio(left: Decimal, right: Decimal) -> str:
        with localcontext() as ctx:
            ctx.prec = 80
            value = (left / right).ln().quantize(QUANTUM, rounding=ROUND_HALF_EVEN)
        return str(Fraction(str(value)))

    models: dict[str, tuple[str, dict[str, str]]] = {}
    digest_lines = []
    for query_id in sorted(truths):
        n0 = clamped(estimates["Empty"][query_id])
        available = [e for e in candidate_ids if query_id in estimates.get(e, {})]
        corrections = {e: log_ratio(clamped(estimates[e][query_id]), n0) for e in available}
        alpha = log_ratio(n0, clamped(truths[query_id]))
        models[query_id] = (alpha, corrections)
        digest_lines.append(json.dumps({"alpha": alpha, "b": corrections,
                                        "available_edges": available}, sort_keys=True,
                                       separators=(",", ":")))
    digest = hashlib.sha256("\n".join(digest_lines).encode()).hexdigest()
    if digest != frozen["model_coefficient_sha256"]:
        raise ValueError("reconstructed Census13 coefficient digest differs from frozen selection")
    expected_counts = {r["id"]: r["eligible_valid_query_count"] for r in candidate_rows}
    actual_counts = {edge: len(estimates.get(edge, {})) for edge in candidate_ids}
    if expected_counts != actual_counts:
        raise ValueError("Census13 observed singleton coverage differs from frozen static eligibility counts")
    return candidate_ids, models, endpoints


def census13_request(repo: Path, budget: int = 0, *, task_limit: int | None = None) -> dict[str, Any]:
    root = repo / CENSUS_ROOT
    candidate_ids, models, endpoints = _census_coefficients(root)
    order = _json(root / "census13-stage2b-plan-v1.json")["nominal_priority_orders"]["orders"][0]["candidate_ids"]
    ids = sorted(models)
    if task_limit is not None:
        ids = ids[:task_limit]
    tasks = [_task(qid, *models[qid], "public.census13") for qid in ids]
    frozen = _json(root / "census13-clamped-log-v2-schema-order-frozen-selection-v1.json")
    request = _request("census13-clamped-log-v2", "public.census13",
        [(edge, endpoints[edge]) for edge in candidate_ids], tasks, budget,
        calibration_id="issue71-census13-valid-schema-order-v1",
        research_commit="a7aa91e10dd199fd8eb6e5cbaaf1f6e05a607207",
        postgresql_source_commit="f1bf37b5dd3d3a7087fc0af5de550ca31035854c",
        nominal_order=order)
    request["input_provenance"]["frozen_reference_sha256"] = sha256(root / "census13-clamped-log-v2-schema-order-frozen-selection-v1.json")
    request["input_provenance"]["observation_sha256"] = frozen["observation_sha256"]
    request["input_provenance"]["valid_truth_sha256"] = frozen["valid_truth_sha256"]
    request["input_provenance"]["truth_provenance"] = frozen["valid_truth_method"]
    request["input_provenance"]["coefficient_sha256"] = frozen["model_coefficient_sha256"]
    request["input_provenance"]["arecel_archive_sha256"] = frozen["arecel_archive_sha256"]
    request["input_provenance"]["plan_sha256"] = frozen["plan_sha256"]
    request["input_provenance"]["model_source_commit"] = "27677a17b7455d89e92d5028d9585418550a8ff8"
    request["_frozen_selection"] = {"Nominal": frozen["nominal_by_order"][0]["budgets"],
                                    "PESS": frozen["pess_global"]}
    request["_candidate_ids"] = candidate_ids
    return request


def advisor_request_payload(request: dict[str, Any], objective: str, *, priority_order: list[str] | None = None) -> dict[str, Any]:
    """Return the exact schema-v1 JSON sent to the advisor CLI."""
    payload = {k: v for k, v in request.items() if not k.startswith("_")}
    payload["objective"] = objective
    if objective == "nominal":
        payload.pop("backend", None)
        payload["priority_order"] = priority_order or request["_nominal_priority_order"]
    else:
        payload["backend"] = "master_oracle"
    return payload
