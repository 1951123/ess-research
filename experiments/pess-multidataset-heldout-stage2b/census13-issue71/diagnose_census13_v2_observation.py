"""Reproduce one failed Census13 valid observation and retain its rejected JSON diagnostics."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sys
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(HERE))

import run_census13_smoke as smoke
from ess_research.arecel.archive import prepare_valid_workload
from ess_research.task_paths import runtime_runs

RUN_ID = "20261022-census13-q42-e01_05-diagnostic-v1"
V2_RUN_ID = "20261022-080045-census13-full-valid"
SAMPLE_SHA256 = "0ff61bcce532a8af07f9319365c28d6fb07e373fc4b8049bae7c72c349baba26"
QUERY_ID = "arecel:census13:valid:000042"
QUERY_SQL_SHA256 = "14d8fbb8f75d03ff9f56cd53de9bbf87f4f7b2708c3fadfbfec12cef87dc7369"
CONFIG_ID = "e01_05"


class JsonNumber(str):
    """Preserve the exact lexical spelling of a JSON number for forensics."""


class JsonConstant(str):
    """Preserve non-standard JSON constants if a server emits one."""


def _json_value(value: Any) -> Any:
    if isinstance(value, JsonNumber):
        return str(value)
    if isinstance(value, JsonConstant):
        return {"json_constant": str(value)}
    if isinstance(value, list):
        return [_json_value(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_value(item) for key, item in value.items()}
    return value


def _capture_rejected_json(output: str, destination: Path) -> dict[str, Any]:
    document = json.loads(
        output, parse_float=JsonNumber, parse_int=JsonNumber,
        parse_constant=JsonConstant
    )
    result = document[0]
    diagnostics = result["ESS Diagnostics"]
    events = diagnostics["Events"]
    bases = [(index, event) for index, event in enumerate(events)
             if event.get("type") == "base_estimate"]
    if len(bases) != 1:
        raise RuntimeError(f"expected exactly one base_estimate event, found {len(bases)}")
    index, base = bases[0]
    path = f'$[0]["ESS Diagnostics"]["Events"][{index}]["nrows_preclamp"]'
    value = base.get("nrows_preclamp", "<missing>")
    if isinstance(value, JsonNumber):
        value_kind, raw_value = "json-number", str(value)
    elif isinstance(value, JsonConstant):
        value_kind, raw_value = "json-constant", str(value)
    elif isinstance(value, str):
        value_kind, raw_value = "json-string", value
    elif value is None:
        value_kind, raw_value = "json-null", None
    elif isinstance(value, bool):
        value_kind, raw_value = "json-boolean", value
    else:
        value_kind, raw_value = type(value).__name__, str(value)
    evidence = {
        "query_id": QUERY_ID,
        "config_id": CONFIG_ID,
        "response_sha256": hashlib.sha256(output.encode()).hexdigest(),
        "response_characters": len(output),
        "diagnostics_status": diagnostics.get("Status"),
        "event_count": diagnostics.get("Event Count"),
        "base_estimate_event_index": index,
        "nrows_preclamp_json_path": path,
        "nrows_preclamp_json_type": value_kind,
        "nrows_preclamp_raw": raw_value,
        "base_estimate_event": _json_value(base),
        "mcv_events": _json_value([
            event for event in events
            if event.get("type") in {"mcv_selection", "mcv_clause", "mcv_estimate"}
        ]),
        "diagnostic_events": _json_value(events),
    }
    with destination.open("x", encoding="utf-8") as stream:
        json.dump(evidence, stream, indent=2, sort_keys=True, allow_nan=False)
        stream.write("\n")
        stream.flush()
        os.fsync(stream.fileno())
    return evidence


def execute(root: Path) -> dict[str, Any]:
    root.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    guard = smoke.AggregateGuard(root)
    summary: dict[str, Any] = {
        "run_id": root.name,
        "status": "INCOMPLETE",
        "query_id": QUERY_ID,
        "config_id": CONFIG_ID,
        "truth_loaded": False,
        "test_accessed": False,
        "explain_calls_allowed": 1,
    }
    try:
        with guard:
            csv_path = smoke.extract_csv(root)
            input_dir = csv_path.parent
            v2_sample = runtime_runs("ess-research", 71) / V2_RUN_ID / "clusters/results/census13.fixed-sample"
            if smoke.sha256_file(v2_sample) != SAMPLE_SHA256:
                raise RuntimeError("preserved v2 fixed ANALYZE sample SHA-256 mismatch")
            sample = input_dir / "census13.fixed-sample"
            shutil.copyfile(v2_sample, sample)
            if smoke.sha256_file(sample) != SAMPLE_SHA256:
                raise RuntimeError("run-local copy of the frozen sample failed SHA-256 check")
            schema, _source_columns, columns = smoke.schema_file(root)
            with prepare_valid_workload(issue=71, dataset="census13") as prepared:
                if prepared.manifest.get("labels_loaded") is not False:
                    raise RuntimeError("valid workload loader unexpectedly opened labels")
                workload = json.loads(prepared.workload_path.read_text())
            query = workload["queries"][42]
            if query["query_id"] != QUERY_ID or query["source_index"] != 42:
                raise RuntimeError("source-index-42 valid query identity mismatch")
            sql_sha = hashlib.sha256(query["sql"].encode()).hexdigest()
            if sql_sha != QUERY_SQL_SHA256:
                raise RuntimeError("fixed valid-query SQL SHA-256 mismatch")
            plan_path = HERE / "census13-stage2b-plan-v1.json"
            if smoke.sha256_file(plan_path) != smoke.PLAN_SHA256:
                raise RuntimeError("frozen Census13 plan SHA-256 mismatch")
            plan = json.loads(plan_path.read_text())
            candidate_spec = next(
                candidate for candidate in plan["candidate_policy"]["candidates"]
                if candidate["id"] == CONFIG_ID
            )
            candidate = {
                "id": CONFIG_ID,
                "statistic_name": f"ess_issue71_census13_{CONFIG_ID}",
                "catalog_columns": candidate_spec["endpoints"],
                "eligible_valid_query_count": candidate_spec["eligible_valid_query_count"],
            }
            query_columns = {predicate["column"] for predicate in query["predicates"]}
            if not set(candidate["catalog_columns"]).issubset(query_columns):
                raise RuntimeError("the frozen candidate is not statically eligible for query 42")

            prefix, build = smoke.build_pg(root)
            helpers, run_formal, forest10_runner, helper_hashes = smoke.load_helpers(root)
            summary.update({
                "postgresql": build,
                "helper_commits": {"pr58": smoke.PR58_COMMIT, "pr65": smoke.PR65_COMMIT},
                "helper_sha256": helper_hashes,
                "plan_sha256": smoke.PLAN_SHA256,
                "valid_archive_sha256": prepared.manifest["archive_sha256"],
                "query_sql_sha256": sql_sha,
                "sample_sha256": SAMPLE_SHA256,
                "sample_bytes": sample.stat().st_size,
                "sample_header": helpers.sample_header(sample),
                "csv_sha256": smoke.sha256_file(csv_path),
                "csv_bytes": csv_path.stat().st_size,
            })
            if summary["sample_header"].get("server_version") != "16.14":
                raise RuntimeError("frozen sample is not from PostgreSQL 16.14")

            cluster_root = root / "cluster"
            with smoke.owned_cluster(helpers, prefix, cluster_root, os.environ.copy(), guard) as cluster:
                relation_oid = smoke.populate_replay_cluster(
                    helpers, prefix, cluster, schema, csv_path, sample, columns
                )
                candidates = {CONFIG_ID: candidate}
                ledger = run_formal.configure_statistics(
                    prefix, cluster, "census13", candidates, (CONFIG_ID,), sample
                )
                catalog = ledger[0]
                if catalog["statistics_target"] != 300 or not catalog["mcv_payload_present"]:
                    raise RuntimeError("e01_05 catalog target/MCV payload verification failed")
                expected_keys = {str(i) for i, (name, _type) in enumerate(columns, start=1)
                                 if name in candidate["catalog_columns"]}
                if set(catalog["stxkeys"].split()) != expected_keys:
                    raise RuntimeError("e01_05 catalog key columns do not match frozen candidate")
                summary.update({"relation_oid": relation_oid, "statistic_catalog": catalog})
                name_to_id = {candidate["statistic_name"]: CONFIG_ID}
                adapter = forest10_runner.PR7StructuredExplainAdapter(
                    helpers, prefix, cluster, relation_oid, ledger, name_to_id
                )
                original_psql = helpers.psql
                evidence_path = root / "diagnostic-evidence.json"
                explain_count = 0

                def capture_before_adapter_reject(*args, **kwargs):
                    nonlocal explain_count
                    output = original_psql(*args, **kwargs)
                    sql_text = args[3] if len(args) > 3 else kwargs.get("sql", "")
                    if str(sql_text).startswith("EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF)"):
                        explain_count += 1
                        if explain_count != 1:
                            raise RuntimeError("diagnostic EXPLAIN call limit exceeded")
                        evidence = _capture_rejected_json(output, evidence_path)
                        summary["captured_diagnostics_status"] = evidence["diagnostics_status"]
                        summary["captured_base_event_count"] = 1
                    return output

                helpers.psql = capture_before_adapter_reject
                try:
                    observation = adapter.explain(query)
                    summary["adapter_status"] = "ACCEPTED"
                    summary["accepted_nrows_preclamp"] = observation["estimate_preclamp"]
                except ValueError as exc:
                    summary["adapter_status"] = "REJECTED"
                    summary["adapter_error"] = str(exc)
                finally:
                    helpers.psql = original_psql
                summary["explain_calls_actual"] = explain_count
                if explain_count != 1 or not evidence_path.is_file():
                    raise RuntimeError("did not capture exactly one diagnostic EXPLAIN response")
                summary["status"] = "DIAGNOSTIC_CAPTURED"
                summary["cluster_shutdown"] = "PASS"
    except BaseException as exc:
        summary.update({"status": "BLOCKED", "error_class": type(exc).__name__,
                       "error": str(exc)[:700]})
    finally:
        summary["elapsed_seconds"] = round(time.monotonic() - started, 3)
        summary["run_directory_peak_bytes"] = guard.peak
        summary["resource_guard"] = {"hard_bytes": smoke.HARD_BYTES,
                                      "early_bytes": smoke.EARLY_BYTES,
                                      "stop_reason": guard.stop_reason}
        (root / "run-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
    return summary


def main() -> int:
    root = runtime_runs("ess-research", 71) / RUN_ID
    result = execute(root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result.get("status") == "DIAGNOSTIC_CAPTURED" else 2


if __name__ == "__main__":
    raise SystemExit(main())
