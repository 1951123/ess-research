"""Fit and exact-select Census13 from verified valid-only observations."""

from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[2] / "src"))

import run_census13_smoke as smoke
from ess_research.arecel.archive import prepare_valid_workload
from verify_census13_full_valid import verify

PLAN = HERE / "census13-stage2b-plan-v1.json"
EXPECTED_RUN = "20261022-084335-census13-full-valid"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def clamp_fit_estimate(value: Decimal | int | str) -> Decimal:
    return max(Decimal(1), Decimal(value))


def clamp_fit_truth(value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("valid truth must be a nonnegative integer")
    return max(1, value)


def _valid_truth_from_official_sql(run: Path, queries: list[dict[str, Any]]) -> dict[str, int]:
    """Reconstruct exact valid cardinalities from official valid COUNT SQL only."""
    sql_path = run / "valid-truth-counts.sql"
    output_path = run / "valid-truth-counts.jsonl"
    expected_ids = [query["query_id"] for query in queries]
    if output_path.exists():
        if sql_path.exists():
            raise FileExistsError("both reconstructed valid truth and transient SQL exist")
        truth: dict[str, int] = {}
        with output_path.open(encoding="utf-8") as stream:
            for line_no, line in enumerate(stream, 1):
                row = json.loads(line)
                query_id, value = row.get("query_id"), row.get("true_cardinality")
                if (not isinstance(query_id, str) or query_id in truth
                        or isinstance(value, bool) or not isinstance(value, int) or value < 0):
                    raise ValueError(f"invalid reconstructed valid truth row {line_no}")
                truth[query_id] = value
        if list(truth) != expected_ids:
            raise ValueError("existing reconstructed valid truth does not exactly match frozen query order")
        return truth
    if sql_path.exists():
        raise FileExistsError("transient valid truth SQL exists without its output")
    statements = []
    for query in queries:
        source_sql = query.get("source_sql")
        if not isinstance(source_sql, str) or not source_sql.startswith("SELECT COUNT(*) FROM "):
            raise ValueError(f"unexpected official valid source SQL: {query['query_id']}")
        statements.append(f"SELECT '{query['query_id']}', ({source_sql.rstrip().removesuffix(';')});")
    sql_path.write_text("\n".join(statements) + "\n", encoding="utf-8")

    pg = run / "postgresql" / "install"
    pgdata = run / "clusters" / "worker0" / "pgdata"
    log = run / "valid-truth-postgres.log"
    opts_path = pgdata / "postmaster.opts"
    if not opts_path.is_file():
        raise FileNotFoundError("run-local PostgreSQL postmaster options are unavailable")
    opts = opts_path.read_text(encoding="utf-8")
    match = re.search(r'"-p"\s+"([0-9]+)"', opts)
    if not match:
        raise ValueError("cannot recover run-local worker-0 port")
    port = int(match.group(1))
    env = dict(os.environ, LD_LIBRARY_PATH=str(pg / "lib"))
    truth: dict[str, int] = {}
    with tempfile.TemporaryDirectory(prefix="e71-vtruth-") as socket_name:
        socket_dir = Path(socket_name)
        started = False
        try:
            smoke._run([str(pg / "bin/pg_ctl"), "-D", str(pgdata), "-l", str(log),
                        "-o", f"-p {port} -k {socket_dir} -c log_min_messages=warning",
                        "-w", "start"], cwd=run, env=env, timeout=120)
            started = True
            psql_cmd = [str(pg / "bin/psql"), "-X", "-v", "ON_ERROR_STOP=1",
                        "-h", str(socket_dir), "-p", str(port), "-d", "postgres",
                        "-A", "-t", "-F", "|", "-f", str(sql_path)]
            completed = subprocess.run(psql_cmd, cwd=run, env=env, capture_output=True,
                                       text=True, timeout=3 * 3600, check=False)
            if completed.returncode:
                raise RuntimeError(f"valid-only exact COUNT SQL failed ({completed.returncode}): "
                                   f"{(completed.stderr or completed.stdout)[-500:]}")
            for line_no, line in enumerate(completed.stdout.splitlines(), 1):
                parts = line.split("|")
                if len(parts) != 2 or parts[0] in truth:
                    raise ValueError(f"malformed/duplicate valid truth row at {line_no}")
                query_id, raw_count = parts
                if not raw_count.isdecimal():
                    raise ValueError(f"invalid exact cardinality at valid truth row {line_no}")
                truth[query_id] = int(raw_count)
            if list(truth) != expected_ids:
                raise ValueError("reconstructed valid truth does not cover exactly 10,000 queries")
            with output_path.open("x", encoding="utf-8") as stream:
                for query in queries:
                    query_id = query["query_id"]
                    stream.write(json.dumps({"query_id": query_id,
                                             "true_cardinality": truth[query_id]},
                                            sort_keys=True, separators=(",", ":")) + "\n")
        finally:
            if started:
                smoke._run([str(pg / "bin/pg_ctl"), "-D", str(pgdata), "-m", "fast",
                            "-w", "stop"], cwd=run, env=env, timeout=120)
    sql_path.unlink()
    return truth


def _load_observations(run: Path) -> tuple[dict[str, Decimal], dict[str, dict[str, Decimal]]]:
    empty: dict[str, Decimal] = {}
    singleton: dict[str, dict[str, Decimal]] = {}
    for worker_id in (0, 1):
        path = run / "observations" / f"worker{worker_id}.jsonl"
        with path.open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                if row.get("status") != "SUCCESS":
                    raise ValueError("non-success observation encountered after verification")
                query_id, config_id = row["query_id"], row["config_id"]
                raw = Decimal(row["nrows_preclamp"])
                if config_id == "Empty":
                    if query_id in empty:
                        raise ValueError(f"duplicate Empty observation: {query_id}")
                    empty[query_id] = raw
                else:
                    rows = singleton.setdefault(config_id, {})
                    if query_id in rows:
                        raise ValueError(f"duplicate singleton observation: {query_id}/{config_id}")
                    rows[query_id] = raw
    return empty, singleton


def fit_and_select(run: Path) -> dict[str, Any]:
    if run.name != EXPECTED_RUN:
        raise ValueError("this frozen fit is bound to the verified independent run ID")
    verification = verify(run)
    if verification["status"] != "PASS" or verification["total_calls"] != 288_849:
        raise ValueError("full-valid independent verification did not pass")
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    with prepare_valid_workload(issue=71, dataset="census13") as prepared:
        if prepared.manifest.get("labels_loaded") is not False:
            raise ValueError("valid workload preparation unexpectedly loaded labels")
        workload = json.loads(prepared.workload_path.read_text(encoding="utf-8"))
    queries = workload["queries"]
    truth = _valid_truth_from_official_sql(run, queries)
    empty_raw, singleton_raw = _load_observations(run)
    if len(empty_raw) != 10_000:
        raise ValueError("Empty input coverage differs from 10,000")
    candidates = [(row["id"], tuple(row["endpoints"])) for row in plan["candidate_policy"]["candidates"]]
    candidate_ids = [candidate[0] for candidate in candidates]
    available: dict[str, tuple[str, ...]] = {query["query_id"]: () for query in queries}
    coverage_path = run / "coverage.jsonl"
    with coverage_path.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            available[row["query_id"]] = tuple(row["eligible_config_ids"])
    if set(available) != set(truth):
        raise ValueError("valid truth and static eligibility IDs differ")
    if set(singleton_raw) != set(candidate_ids):
        raise ValueError("singleton input candidate set differs from frozen 78 candidates")

    # The frozen clamped-log-v2 transform is applied only to fitting inputs.
    empty_fit = {query_id: clamp_fit_estimate(value) for query_id, value in empty_raw.items()}
    singleton_fit = {edge: {query_id: clamp_fit_estimate(value) for query_id, value in rows.items()}
                     for edge, rows in singleton_raw.items()}
    truth_fit = {query_id: clamp_fit_truth(value) for query_id, value in truth.items()}

    helper_dir = run / "pinned-helpers"
    if sha256_file(helper_dir / "forest10_runner.py") != "44d628108da4ca4e65c67fc4016891a99e35662067b1a9b381593ebb9d124e86":
        raise ValueError("run-local Census13 adapter helper checksum mismatch")
    sys.path.insert(0, str(helper_dir))
    import forest10_runner
    import forest10_exact_selection
    models = forest10_runner.build_task_models(
        tuple(query["query_id"] for query in queries), truth_fit, empty_fit,
        singleton_fit, available)
    model_digest = hashlib.sha256("\n".join(
        json.dumps({"alpha": str(model.alpha), "b": {edge: str(value) for edge, value in sorted(model.b.items())},
                    "available_edges": model.available_edges}, sort_keys=True, separators=(",", ":"))
        for model in models).encode()).hexdigest()

    orders = plan["nominal_priority_orders"]["orders"]
    if len(orders) != 10 or orders[0].get("label") != "schema_order":
        raise ValueError("frozen Nominal order list is missing its predeclared schema_order")
    budgets = tuple(plan["selection"]["budgets_at_most"])
    if budgets != (0, 2, 3):
        raise ValueError("frozen budgets changed")
    # Researcher narrowed this exploratory analysis to the first, predeclared
    # schema order. One exact solve computes Nominal(schema_order) and PESS.
    schema_order = orders[0]
    combined = forest10_exact_selection.exact_select_many(models, candidates, budgets)
    pess = combined["PESS"]
    pess_endpoints = {edge: endpoints for edge, endpoints in candidates}
    nominal_results = []
    order = schema_order
    nominal = combined["Nominal"]
    if order["candidate_ids"] != candidate_ids:
        raise ValueError("predeclared schema_order differs from the frozen candidate order")
    budget_results = {}
    for budget in budgets:
        selected = nominal[str(budget)]
        selected_set = selected["selected"]
        worst = sum((forest10_exact_selection.model_loss(
            model, selected_set, "PESS", pess_endpoints, candidate_ids)
            for model in models), Fraction(0))
        budget_results[str(budget)] = {
            **selected,
            "selected_set_pess_worst_case_fraction": str(worst),
            "regret_vs_pess_global_fraction": str(worst - Fraction(pess[str(budget)]["objective_fraction"])),
            "all_optimal_sets_pess_worst_case_fractions": [
                {"set": tied, "loss": str(sum((forest10_exact_selection.model_loss(
                    model, tied, "PESS", pess_endpoints, candidate_ids)
                    for model in models), Fraction(0)))}
                for tied in selected["all_optimal_sets"]
            ],
        }
    nominal_results.append({"order_label": order["label"], "seed": order["seed"],
                            "candidate_ids": order["candidate_ids"], "budgets": budget_results})

    raw_counts = verification["raw_preclamp_counts_by_configuration_family"]
    result = {
        "format": "ess-issue71-census13-clamped-log-v2-schema-order-valid-selection-v1",
        "status": "FROZEN",
        "selection_scope": "single predeclared schema_order only; other nine frozen orders were not evaluated",
        "zero_policy": "clamped-log-v2",
        "run_id": run.name,
        "plan_sha256": smoke.PLAN_SHA256,
        "arecel_archive_sha256": prepared.manifest.get("archive_sha256", "pinned-archive-verified-by-loader"),
        "valid_truth_method": "exact COUNT(*) over each official valid source_sql against the pinned AreCEL source table in worker-0's run-local PostgreSQL cluster; test labels were never opened",
        "valid_truth_sha256": sha256_file(run / "valid-truth-counts.jsonl"),
        "observation_sha256": {f"worker{i}": smoke.sha256_file(run / "observations" / f"worker{i}.jsonl") for i in (0, 1)},
        "valid_source_sql_sha256": hashlib.sha256("\n".join(
            query["source_sql"] for query in queries).encode("utf-8")).hexdigest(),
        "sample_sha256": verification["sample_sha256"],
        "raw_counts": raw_counts,
        "fit_transform": "g(x)=max(1,x) applied uniformly to raw Empty preclamp, singleton preclamp, and valid truth only during coefficient construction",
        "raw_observations_clamped_during_acquisition": False,
        "model_coefficient_sha256": model_digest,
        "decimal_log_quantization": "pinned PR65 build_task_models: Decimal ln at precision 80, 1e-18 half-even, Fraction exact selection",
        "budgets": list(budgets),
        "candidate_ids": candidate_ids,
        "pess_global": pess,
        "nominal_by_order": nominal_results,
        "test_truth_or_outcomes_accessed": False,
    }
    destination = HERE / "census13-clamped-log-v2-schema-order-frozen-selection-v1.json"
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return result


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("usage: fit_census13_valid_and_freeze.py RUN_DIR")
    result = fit_and_select(Path(sys.argv[1]).resolve())
    print(json.dumps({"status": result["status"], "run_id": result["run_id"],
                      "model_coefficient_sha256": result["model_coefficient_sha256"]}, sort_keys=True))
