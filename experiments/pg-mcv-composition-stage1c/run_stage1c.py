"""Execute the frozen Issue #40 PostgreSQL audit in an issue-owned cluster."""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, localcontext
from pathlib import Path
from typing import Any

from matching_verifier import MatchingVerificationError, verify_maximal_matching


TRACE_SELECTED = re.compile(r"ESS_MCV_TRACE: .*selected_stat_oid=(\d+) keys=")
TRACE_CLAIMED = re.compile(r"ESS_MCV_TRACE: .*selected_stat_oid=(\d+) claimed_clause_index=(\d+)")
TRACE_NONE = re.compile(r"ESS_MCV_TRACE: .*candidate=none; iteration terminated")
TRACE_NUMERIC = re.compile(
    r"ESS_MCV_NUMERIC_TRACE: .*selected_stat_oid=(\d+) .*?"
    r"simple_sel=([^ ]+) mcv_sel=([^ ]+) mcv_basesel=([^ ]+) "
    r"mcv_totalsel=([^ ]+) stat_sel=([^ ]+)"
)
TRACE_FINAL = re.compile(
    r"ESS_MCV_NUMERIC_TRACE: base_relation_oid=(\d+) .*?"
    r"selectivity_preclamp=([^ ]+) nrows_preclamp=([^ ]+) rows_postclamp=([^ ]+)"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def run_command(command: list[str], *, env: dict[str, str], input_text: str | None = None, timeout: int = 180) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        input=input_text,
        env=env,
        text=True,
        capture_output=True,
        timeout=timeout,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout={result.stdout[-4000:]}\nstderr={result.stderr[-4000:]}"
        )
    return result


def sql_ident(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sql_literal(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


class Runner:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.root = args.issue_root.resolve()
        self.manifest_path = args.manifest.resolve()
        self.manifest = json.loads(self.manifest_path.read_text(encoding="utf-8"))
        self.data_root = args.data_root.resolve()
        self.pg_bin = args.pg_bin.resolve()
        self.lib_dir = args.lib_dir.resolve()
        self.server_log = self.root / "logs" / "server.log"
        self.raw_dir = self.root / "results" / "raw"
        self.observation_path = self.root / "results" / "observations.jsonl"
        self.composition_path = self.root / "results" / "composition.json"
        self.env = os.environ.copy()
        self.env["LD_LIBRARY_PATH"] = str(self.lib_dir)
        self.tasks = self._load_tasks()
        self.candidates = {item["id"]: item for item in self.manifest["candidates"]}
        self.candidate_names = {key: f"ess_i40_{key}" for key in self.candidates}
        self.observations: list[dict[str, Any]] = []

    def _input_path(self, relative: str) -> Path:
        return self.data_root / relative

    def validate_inputs(self) -> None:
        expected = self.manifest["input_contract"]
        checks = [
            (expected["forest10_csv"]["relative_path"], expected["forest10_csv"]["sha256"]),
            (expected["canonical_queries"]["relative_path"], expected["canonical_queries"]["sha256"]),
            (expected["fixed_sample"]["relative_path"], expected["fixed_sample"]["sha256"]),
        ]
        for relative, digest in checks:
            path = self._input_path(relative)
            if not path.is_file():
                raise RuntimeError(f"missing immutable input: {path}")
            actual = sha256_file(path)
            if actual != digest:
                raise RuntimeError(f"input hash mismatch for {path}: {actual} != {digest}")

    def _load_tasks(self) -> dict[str, dict[str, Any]]:
        wanted = {item["query_id"]: item for item in self.manifest["tasks"]}
        found: dict[str, dict[str, Any]] = {}
        path = self._input_path(self.manifest["input_contract"]["canonical_queries"]["relative_path"])
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line in stream:
                item = json.loads(line)
                if item.get("query_id") in wanted:
                    expected = wanted[item["query_id"]]
                    if item.get("source_query_sha256") != expected["source_query_sha256"]:
                        raise RuntimeError(f"query hash mismatch: {item['query_id']}")
                    if item["source_label"]["cardinality"] != expected["truth"]:
                        raise RuntimeError(f"truth mismatch: {item['query_id']}")
                    found[expected["id"]] = {"manifest": expected, "record": item}
        if set(found) != set(wanted[item["query_id"]]["id"] for item in self.manifest["tasks"]):
            raise RuntimeError("not all frozen task IDs were found")
        return found

    def psql(self, sql: str, *, application: str, tuples: bool = False, timeout: int = 180) -> str:
        command = [
            str(self.pg_bin / "psql"),
            "-X",
            "-v", "ON_ERROR_STOP=1",
            "-h", str(self.root / "socket"),
            "-p", str(self.args.port),
            "-d", self.args.database,
        ]
        if tuples:
            command.extend(["-At", "-F", "\t"])
        body = f"SET application_name = {sql_literal(application)};\n{sql}\n"
        return run_command(command, env=self.env, input_text=body, timeout=timeout).stdout

    def init_cluster(self) -> None:
        pgdata = self.root / "pgdata"
        if pgdata.exists():
            raise RuntimeError(f"refusing to reuse existing PGDATA: {pgdata}")
        for path in (self.root / "logs", self.root / "results", self.root / "socket"):
            path.mkdir(parents=True, exist_ok=True)
        run_command(
            [str(self.pg_bin / "initdb"), "-D", str(pgdata), "--no-locale", "--encoding=UTF8", "-U", "wqts"],
            env=self.env,
            timeout=120,
        )
        self.start_server(binary_upgrade=False)
        run_command(
            [str(self.pg_bin / "createdb"), "-h", str(self.root / "socket"), "-p", str(self.args.port), self.args.database],
            env=self.env,
            timeout=30,
        )
        self.stop_cluster()
        self.start_server(binary_upgrade=True)
        self.load_table()
        self.stop_cluster()
        self.start_server(binary_upgrade=False)
        self.set_statistics_targets()

    def start_server(self, *, binary_upgrade: bool) -> None:
        pgdata = self.root / "pgdata"
        start_options = (
            f"{'-b ' if binary_upgrade else ''}-p {self.args.port} -k {self.root / 'socket'} "
            "-c log_min_messages=debug1 "
            "-c log_line_prefix='%m [%p] %u@%d app=%a '"
        )
        run_command(
            [str(self.pg_bin / "pg_ctl"), "-D", str(pgdata), "-l", str(self.server_log), "-o", start_options, "-w", "start"],
            env=self.env,
            timeout=60,
        )

    def stop_cluster(self) -> None:
        pgdata = self.root / "pgdata"
        if pgdata.exists():
            run_command(
                [str(self.pg_bin / "pg_ctl"), "-D", str(pgdata), "-m", "fast", "-w", "stop"],
                env=self.env,
                timeout=60,
            )

    def load_table(self) -> None:
        columns = self.manifest["input_contract"]["forest10_csv"]["columns"]
        column_type = self.manifest["input_contract"]["forest10_csv"]["column_type"]
        definitions = ", ".join(f"{sql_ident(column)} {column_type}" for column in columns)
        csv_path = self._input_path(self.manifest["input_contract"]["forest10_csv"]["relative_path"])
        identity = self.manifest["fixture"]["relation_identity"]
        sql = (
            f"SELECT binary_upgrade_set_next_heap_pg_class_oid({identity['relation_oid']});\n"
            f"SELECT binary_upgrade_set_next_heap_relfilenode({identity['relation_filenode']});\n"
            "SELECT binary_upgrade_set_next_pg_type_oid(20000);\n"
            "SELECT binary_upgrade_set_next_array_pg_type_oid(20001);\n"
            f"CREATE TABLE public.forest10_original ({definitions}) WITH (fillfactor={identity['fillfactor']});\n"
            f"\\copy public.forest10_original ({', '.join(sql_ident(c) for c in columns)}) "
            f"FROM {sql_literal(str(csv_path))} WITH (FORMAT csv, HEADER true);\n"
        )
        self.psql(sql, application="i40_load")

    def set_statistics_targets(self) -> None:
        columns = self.manifest["input_contract"]["forest10_csv"]["columns"]
        statements = [
            f"ALTER TABLE public.forest10_original ALTER COLUMN {sql_ident(column)} SET STATISTICS 300;"
            for column in columns
        ]
        self.psql("\n".join(statements), application="i40_set_targets")

        identity = self.manifest["fixture"]["relation_identity"]
        identity_output = self.psql(
            "SELECT c.oid, c.relfilenode, pg_relation_size(c.oid) / current_setting('block_size')::int "
            "FROM pg_class AS c WHERE c.oid = 'public.forest10_original'::regclass;",
            application="i40_identity",
            tuples=True,
        )
        rows = [line for line in identity_output.splitlines() if re.fullmatch(r"\d+\t\d+\t\d+", line)]
        if len(rows) != 1:
            raise RuntimeError(f"unexpected fixed sample identity output: {identity_output!r}")
        row = rows[0]
        expected = (
            f"{identity['relation_oid']}\t{identity['relation_filenode']}\t{identity['relation_pages']}"
        )
        if row != expected:
            raise RuntimeError(f"fixed sample relation identity mismatch: {row!r} != {expected!r}")

    def drop_statistics(self) -> None:
        names = ", ".join(f"public.{sql_ident(name)}" for name in self.candidate_names.values())
        if names:
            self.psql(f"DROP STATISTICS IF EXISTS {names};", application="i40_drop")

    def install_statistics(self, order: list[str]) -> None:
        statements = []
        for candidate_id in order:
            candidate = self.candidates[candidate_id]
            name = self.candidate_names[candidate_id]
            columns = ", ".join(sql_ident(column) for column in candidate["columns"])
            statements.append(
                f"CREATE STATISTICS public.{sql_ident(name)} (mcv) ON {columns} "
                "FROM public.forest10_original;"
            )
            statements.append(f"ALTER STATISTICS public.{sql_ident(name)} SET STATISTICS 300;")
        if statements:
            self.psql("\n".join(statements), application="i40_create")

    def analyze_fixed_sample(self) -> None:
        sample = self._input_path(self.manifest["input_contract"]["fixed_sample"]["relative_path"])
        sql = (
            f"SET ess.analyze_sample_import = {sql_literal(str(sample))};\n"
            "ANALYZE public.forest10_original;\n"
            "RESET ess.analyze_sample_import;"
        )
        self.psql(sql, application="i40_analyze", timeout=180)

    def catalog_ledger(self, scenario: str, repetition: int, order_index: int) -> list[dict[str, Any]]:
        names = ", ".join(sql_literal(self.candidate_names[item]) for item in self.candidates)
        sql = (
            "SELECT s.stxname, s.oid, s.stxkeys::text, s.stxstattarget, "
            "(d.stxdmcv IS NOT NULL)::int, "
            "CASE WHEN d.stxdmcv IS NULL THEN 0 ELSE "
            "(SELECT count(*) FROM pg_mcv_list_items(d.stxdmcv)) END "
            "FROM pg_statistic_ext AS s "
            "LEFT JOIN pg_statistic_ext_data AS d ON d.stxoid=s.oid AND NOT d.stxdinherit "
            f"WHERE s.stxname IN ({names}) ORDER BY s.oid;"
        )
        rows = []
        for line in self.psql(sql, application=f"i40_catalog_{scenario}_{repetition}_{order_index}", tuples=True).splitlines():
            if not line:
                continue
            fields = line.split("\t")
            if len(fields) != 6:
                continue
            name, oid, keys, target, built, count = fields
            candidate_id = next((key for key, value in self.candidate_names.items() if value == name), None)
            rows.append({
                "candidate_id": candidate_id,
                "statistic_name": name,
                "statistic_oid": int(oid),
                "stxkeys": keys,
                "statistics_target": int(target),
                "built_mcv": bool(int(built)),
                "mcv_item_count": int(count),
            })
        return rows

    def _query_sql(self, record: dict[str, Any], marker: str) -> str:
        source_sql = record["sql"]
        if not source_sql.startswith("SELECT COUNT(*)"):
            raise RuntimeError(f"unexpected source SQL for {record['query_id']}")
        query = source_sql.replace("SELECT COUNT(*)", "SELECT *", 1)
        return (
            "SET client_min_messages = debug1;\n"
            "SET default_statistics_target = 300;\n"
            "SET plan_cache_mode = force_custom_plan;\n"
            "SET max_parallel_workers_per_gather = 0;\n"
            f"EXPLAIN (FORMAT JSON, SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE {marker} */ {query};"
        )

    @staticmethod
    def _parse_trace(lines: list[str]) -> dict[str, Any]:
        selected = [int(match.group(1)) for line in lines if (match := TRACE_SELECTED.search(line))]
        claimed = [
            {"statistic_oid": int(match.group(1)), "clause_index": int(match.group(2))}
            for line in lines if (match := TRACE_CLAIMED.search(line))
        ]
        numeric = []
        for line in lines:
            match = TRACE_NUMERIC.search(line)
            if match:
                numeric.append({
                    "statistic_oid": int(match.group(1)),
                    "simple_sel": match.group(2),
                    "mcv_sel": match.group(3),
                    "mcv_basesel": match.group(4),
                    "mcv_totalsel": match.group(5),
                    "stat_sel": match.group(6),
                })
        final = []
        for line in lines:
            match = TRACE_FINAL.search(line)
            if match:
                final.append({
                    "base_relation_oid": int(match.group(1)),
                    "selectivity_preclamp": match.group(2),
                    "nrows_preclamp": match.group(3),
                    "rows_postclamp": match.group(4),
                })
        return {
            "selected_stat_oids": selected,
            "claimed_clauses": claimed,
            "candidate_none_seen": any(TRACE_NONE.search(line) for line in lines),
            "numeric_stat_traces": numeric,
            "numeric_final_traces": final,
            "trace_line_count": len(lines),
        }

    def run_query(self, task: dict[str, Any], marker: str, ledger: list[dict[str, Any]]) -> dict[str, Any]:
        before = self.server_log.stat().st_size if self.server_log.exists() else 0
        application = f"i40_{marker}"[:63]
        result = self.psql(self._query_sql(task["record"], marker), application=application, tuples=False)
        time.sleep(0.05)
        with self.server_log.open("rb") as stream:
            stream.seek(before)
            lines = stream.read().decode("utf-8", errors="replace").splitlines()
        trace = self._parse_trace(lines)
        plan_rows = re.findall(r'"Plan Rows":\s*(\d+)', result)
        oid_to_candidate = {str(item["statistic_oid"]): item["candidate_id"] for item in ledger}
        selected_ids = [oid_to_candidate.get(str(oid)) for oid in trace["selected_stat_oids"]]
        selected_ids = [item for item in selected_ids if item is not None]
        return {
            "marker": marker,
            "task_id": task["manifest"]["id"],
            "query_id": task["record"]["query_id"],
            "truth": task["manifest"]["truth"],
            "ledger": ledger,
            "trace": trace,
            "selected_candidate_ids": selected_ids,
            "plan_rows": plan_rows,
            "positive_preclamp_available": len(trace["numeric_final_traces"]) == 1,
            "psql_stdout_sha256": hashlib.sha256(result.encode()).hexdigest(),
        }

    def graph_checks(self, observation: dict[str, Any], resources: list[str]) -> list[dict[str, Any]]:
        ledger = {item["candidate_id"]: item for item in observation["ledger"]}
        selected = observation["selected_candidate_ids"]
        checks = []
        for task_id, task in self.tasks.items():
            required = set(task["manifest"]["required_columns"])
            requested = [item for item in resources if set(self.candidates[item]["columns"]) <= required]
            available = [item for item in requested if ledger.get(item, {}).get("built_mcv")]
            unusable = [item for item in requested if item not in available]
            task_selected = [item for item in selected if item in requested]
            record = {
                "task_id": task_id,
                "requested_candidate_ids": requested,
                "available_built_mcv_candidate_ids": available,
                "requested_without_mcv_payload": unusable,
                "selected_candidate_ids": task_selected,
            }
            try:
                record["matching_check"] = verify_maximal_matching(
                    self.candidates.values(), available, task_selected
                )
                record["status"] = "PASS"
            except MatchingVerificationError as exc:
                record["status"] = "FAIL"
                record["error"] = str(exc)
            checks.append(record)
        return checks

    def run_configuration(self, scenario: str, resources: list[str], order: list[str], repetition: int, order_index: int, task_ids: list[str] | None = None) -> dict[str, Any]:
        self.drop_statistics()
        self.install_statistics(order)
        self.analyze_fixed_sample()
        ledger = self.catalog_ledger(scenario, repetition, order_index)
        selected_tasks = task_ids or list(self.tasks)
        results = []
        for task_id in selected_tasks:
            marker = f"issue40-r{repetition}-{scenario}-o{order_index}-{task_id}"
            result = self.run_query(self.tasks[task_id], marker, ledger)
            result["scenario"] = scenario
            result["resources"] = resources
            result["creation_order"] = order
            result["repetition"] = repetition
            result["order_index"] = order_index
            result["graph_checks"] = self.graph_checks(result, resources)
            results.append(result)
            self.observations.append(result)
        return {"scenario": scenario, "resources": resources, "creation_order": order, "repetition": repetition, "order_index": order_index, "ledger": ledger, "results": results}

    @staticmethod
    def final_decimal(observation: dict[str, Any]) -> Decimal | None:
        traces = observation["trace"]["numeric_final_traces"]
        if len(traces) != 1:
            return None
        try:
            value = Decimal(traces[0]["nrows_preclamp"])
        except InvalidOperation:
            return None
        return value if value.is_finite() else None

    def compose(self, joint_results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        lookup: dict[tuple[int, str, tuple[str, ...], int], dict[str, Any]] = {}
        for observation in self.observations:
            key = (observation["repetition"], observation["task_id"], tuple(observation["resources"]), observation["order_index"])
            lookup[key] = observation
        output = []
        for case in self.manifest["composition_cases"]["joint_cases"]:
            resources = tuple(case["resources"])
            orders = self.manifest["composition_cases"]["joint_creation_orders"][case["id"]]
            for repetition in range(self.manifest["fixture"]["repetitions"]):
                baseline = lookup.get((repetition, case["task_id"], tuple(), 0))
                baseline_value = self.final_decimal(baseline) if baseline else None
                for order_index, order in enumerate(orders):
                    joint = lookup.get((repetition, case["task_id"], resources, order_index))
                    singles = [lookup.get((repetition, case["task_id"], (resource,), 0)) for resource in resources]
                    single_values = [self.final_decimal(item) if item else None for item in singles]
                    actual = self.final_decimal(joint) if joint else None
                    record: dict[str, Any] = {
                        "case_id": case["id"],
                        "task_id": case["task_id"],
                        "resources": list(resources),
                        "order_index": order_index,
                        "creation_order": order,
                        "repetition": repetition,
                        "baseline_nrows_preclamp": str(baseline_value) if baseline_value is not None else None,
                        "single_nrows_preclamp": [str(value) if value is not None else None for value in single_values],
                        "actual_nrows_preclamp": str(actual) if actual is not None else None,
                        "domain_status": "instrumentation_missing",
                    }
                    if baseline_value is not None and actual is not None and all(value is not None for value in single_values):
                        if baseline_value > 0 and actual > 0 and all(value > 0 for value in single_values):
                            with localcontext() as context:
                                context.prec = 60
                                predicted = baseline_value
                                for value in single_values:
                                    predicted *= value / baseline_value
                                relative = (actual - predicted) / predicted if predicted else None
                                log_residual = Decimal(str(math.log(float(actual / predicted)))) if predicted and actual else None
                            record.update({
                                "predicted_nrows_preclamp": str(predicted),
                                "absolute_residual": str(actual - predicted),
                                "relative_residual": str(relative),
                                "log_residual_float64": str(log_residual) if log_residual is not None else None,
                                "domain_status": "positive_preclamp",
                            })
                        else:
                            record["domain_status"] = "zero_or_nonpositive_preclamp"
                    output.append(record)
        return output

    def run(self) -> None:
        self.validate_inputs()
        self.raw_dir.mkdir(parents=True, exist_ok=True)
        self.init_cluster()
        try:
            scenarios = {item["id"]: item for item in self.manifest["selected_resource_sets"]}
            orders_by_scenario = {item["resource_set_id"]: item["orders"] for item in self.manifest["creation_orders"]}
            for repetition in range(self.manifest["fixture"]["repetitions"]):
                for scenario_id, scenario in scenarios.items():
                    for order_index, order in enumerate(orders_by_scenario[scenario_id]):
                        self.run_configuration(scenario_id, scenario["resources"], order, repetition, order_index)

                composition = self.manifest["composition_cases"]
                singleton_orders = {resource: [resource] for resource in composition["singletons"]}
                self.run_configuration("composition_baseline", [], [], repetition, 0)
                for resource, order in singleton_orders.items():
                    self.run_configuration(f"composition_single_{resource}", [resource], order, repetition, 0)
                for case in composition["joint_cases"]:
                    for order_index, order in enumerate(composition["joint_creation_orders"][case["id"]]):
                        self.run_configuration(case["id"], case["resources"], order, repetition, order_index, [case["task_id"]])

            self.observation_path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in self.observations), encoding="utf-8")
            composition = self.compose([])
            self.composition_path.write_text(json.dumps({"format": "ess-issue40-composition-v1", "records": composition}, indent=2, sort_keys=True) + "\n", encoding="utf-8")
            metadata = {
                "format": "ess-issue40-run-metadata-v1",
                "evidence_label": "experimentally_observed_if_and_only_if_trace_and_input_checks_pass",
                "started_at_utc": datetime.now(timezone.utc).isoformat(),
                "manifest_sha256": sha256_file(self.manifest_path),
                "input_hashes": {
                    "csv": sha256_file(self._input_path(self.manifest["input_contract"]["forest10_csv"]["relative_path"])),
                    "canonical": sha256_file(self._input_path(self.manifest["input_contract"]["canonical_queries"]["relative_path"])),
                    "sample": sha256_file(self._input_path(self.manifest["input_contract"]["fixed_sample"]["relative_path"])),
                },
                "pg_bin": str(self.pg_bin),
                "pg_version": run_command([str(self.pg_bin / "postgres"), "--version"], env=self.env, timeout=10).stdout.strip(),
                "port": self.args.port,
                "database": self.args.database,
                "observation_count": len(self.observations),
                "composition_count": len(composition),
                "raw_server_log_sha256": sha256_file(self.server_log),
            }
            (self.root / "results" / "run-metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        finally:
            self.stop_cluster()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("protocol-manifest.json"))
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--issue-root", type=Path, required=True)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--lib-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55440)
    parser.add_argument("--database", default="ess_issue40")
    args = parser.parse_args()
    Runner(args).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

