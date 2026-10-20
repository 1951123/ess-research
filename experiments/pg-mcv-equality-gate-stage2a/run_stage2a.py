#!/usr/bin/env python3
"""Run the frozen Issue #47 synthetic PostgreSQL fixture."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import time
from pathlib import Path

from matching_verifier import MatchingVerificationError, verify_maximal_matching
from source_ledger import (
    LedgerError,
    build_source_ledger,
    parse_equality_clauses,
    verify_trace_against_ledger,
)


TRACE_SELECTED = re.compile(r"selected_stat_oid=(\d+) keys=\d+")
TRACE_CLAIMED = re.compile(r"selected_stat_oid=(\d+) claimed_clause_index=(\d+)")
TRACE_NONE = re.compile(r"candidate=none; iteration terminated")


def run_command(command: list[str], env: dict[str, str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(command, env=env, text=True, capture_output=True)
    if check and result.returncode != 0:
        raise RuntimeError(
            f"command failed ({result.returncode}): {' '.join(command)}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class Stage2ARunner:
    def __init__(self, root: Path, pg_bin: Path, manifest_path: Path, repetitions: int | None, smoke: bool = False) -> None:
        self.root = root
        self.pg_bin = pg_bin
        self.manifest_path = manifest_path
        self.manifest = json.loads(manifest_path.read_text())
        self.repetitions = repetitions or int(self.manifest["execution"]["repetitions_per_setup_order"])
        self.smoke = smoke
        self.data = root / "pgdata"
        self.socket = root / "socket"
        self.logs = root / "logs"
        self.raw = root / "raw"
        self.results = root / "results"
        for directory in (self.logs, self.raw, self.results):
            directory.mkdir(parents=True, exist_ok=True)
        self.log_path = self.logs / "server.log"
        self.env = os.environ.copy()
        self.env["LD_LIBRARY_PATH"] = str(pg_bin / "lib")
        self.psql_bin = pg_bin / "bin" / "psql"
        self.pg_ctl = pg_bin / "bin" / "pg_ctl"
        self.initdb = pg_bin / "bin" / "initdb"
        self.database = self.manifest["execution"]["database"]
        self.table = self.manifest["fixture"]["table"]
        self.candidates = {item["id"]: item for item in self.manifest["fixture"]["candidate_definitions"]}
        self.queries = {item["id"]: item for item in self.manifest["fixture"]["queries"]}

    def psql(
        self,
        sql: str,
        *,
        check: bool = True,
        output_name: str | None = None,
        database: str | None = None,
        tuples_only: bool = False,
        field_separator: str | None = None,
    ) -> subprocess.CompletedProcess[str]:
        target_database = database or self.database
        command = [
            str(self.psql_bin), "-X", "-v", "ON_ERROR_STOP=1", "-h", str(self.socket),
            "-p", str(self.manifest["execution"]["port"]), "-d", target_database, "-c", sql,
        ]
        if tuples_only:
            command.insert(2, "-At")
        if field_separator is not None:
            command.insert(3, "-F")
            command.insert(4, field_separator)
        result = run_command(command, self.env, check=check)
        if output_name:
            (self.raw / f"{output_name}.stdout").write_text(result.stdout)
            (self.raw / f"{output_name}.stderr").write_text(result.stderr)
        return result

    def psql_file(self, path: Path) -> None:
        command = [
            str(self.psql_bin), "-X", "-v", "ON_ERROR_STOP=1", "-h", str(self.socket),
            "-p", str(self.manifest["execution"]["port"]), "-d", self.database, "-f", str(path),
        ]
        run_command(command, self.env)

    def start(self) -> None:
        if self.data.exists():
            raise RuntimeError(f"refusing to reuse existing runtime data directory: {self.data}")
        self.data.mkdir(parents=True)
        run_command([
            str(self.initdb), "-D", str(self.data), "--no-locale", "--encoding=UTF8", "-U", "wqts",
        ], self.env)
        options = (
            f"-p {self.manifest['execution']['port']} -k {self.socket} "
            "-c log_min_messages=debug1 "
            "-c log_line_prefix='%m [%p] %u@%d app=%a '"
        )
        self.socket.mkdir(parents=True)
        run_command([str(self.pg_ctl), "-D", str(self.data), "-l", str(self.log_path), "-o", options, "start"], self.env)
        for _ in range(50):
            if self.log_path.exists():
                try:
                    self.psql("SELECT 1;", database="postgres")
                    self.psql(f"CREATE DATABASE {self.database};", database="postgres")
                    return
                except RuntimeError:
                    time.sleep(0.1)
        raise RuntimeError("server did not become ready")

    def stop(self) -> None:
        if self.data.exists():
            run_command([str(self.pg_ctl), "-D", str(self.data), "-m", "fast", "stop"], self.env, check=False)

    def setup_table(self) -> None:
        self.psql_file(self.manifest_path.parent / "fixture.sql")

    def drop_statistics(self) -> None:
        names = ", ".join(f"ess2a_{candidate_id}" for candidate_id in self.candidates)
        self.psql("DROP STATISTICS IF EXISTS " + ", ".join(f"ess2a_{candidate_id}" for candidate_id in self.candidates) + ";")

    def create_statistics(self, resource_order: list[str]) -> None:
        for candidate_id in resource_order:
            columns = ", ".join(self.candidates[candidate_id]["columns"])
            self.psql(f"CREATE STATISTICS ess2a_{candidate_id} (mcv) ON {columns} FROM {self.table};")
            if "statistics_target" in self.candidates[candidate_id]:
                target = int(self.candidates[candidate_id]["statistics_target"])
                self.psql(f"ALTER STATISTICS ess2a_{candidate_id} SET STATISTICS {target};")
        self.psql(f"ANALYZE {self.table};")

    def catalog_rows(self) -> list[dict[str, object]]:
        sql = f"""
SELECT s.oid,
       s.stxname,
       s.stxkeys::text,
       s.stxkind::text,
       COALESCE(d.stxdinherit, false),
       CASE WHEN d.stxdmcv IS NULL THEN -1
            ELSE (SELECT count(*) FROM pg_mcv_list_items(d.stxdmcv)) END,
       (d.stxdmcv IS NOT NULL)::int
FROM pg_statistic_ext AS s
LEFT JOIN pg_statistic_ext_data AS d ON d.stxoid = s.oid AND d.stxdinherit = false
WHERE s.stxrelid = '{self.table}'::regclass
ORDER BY s.oid;
"""
        result = self.psql(sql, tuples_only=True, field_separator="\t")
        rows: list[dict[str, object]] = []
        attributes_result = self.psql(
            f"SELECT attnum, attname FROM pg_attribute WHERE attrelid = '{self.table}'::regclass AND attnum > 0 ORDER BY attnum;",
            tuples_only=True,
            field_separator="\t",
        )
        attnum_to_column = {
            int(raw.split("\t")[0]): raw.split("\t")[1]
            for raw in attributes_result.stdout.splitlines()
            if raw.strip()
        }
        for raw in result.stdout.splitlines():
            if not raw.strip():
                continue
            oid, name, keys_text, kind, inherit, item_count, payload_present = raw.split("\t")
            resource_id = name.removeprefix("ess2a_")
            if resource_id not in self.candidates:
                raise RuntimeError(f"unexpected statistics object in fresh fixture: {name}")
            keys = [int(item) for item in re.findall(r"-?\d+", keys_text)]
            rows.append({
                "id": resource_id,
                "oid": int(oid),
                "name": name,
                "keys": keys,
                "columns": [attnum_to_column[key] for key in keys if key in attnum_to_column],
                "kind": kind,
                "inherit": inherit.lower() in {"t", "true", "1"},
                "mcv_item_count": int(item_count),
                "mcv_payload_present": payload_present == "1",
                "source_loaded": payload_present == "1",
            })
        expected_names = {f"ess2a_{item}" for item in self.current_resources}
        if {str(row["name"]) for row in rows} != expected_names:
            raise RuntimeError(f"catalog/resource mismatch: rows={rows}, expected={expected_names}")
        return rows

    def query_trace(self, query_id: str, setup_id: str, order_index: int, repetition: int) -> tuple[dict[str, object], str]:
        query = self.queries[query_id]
        query_sql = query["sql"].strip().rstrip(";") + f" /* ESS_STAGE2A_QUERY:{query_id} ESS_MCV_NUMERIC_TRACE */;"
        statement = f"EXPLAIN (COSTS OFF) {query_sql}"
        before = self.log_path.stat().st_size if self.log_path.exists() else 0
        output_name = f"{setup_id}-order{order_index}-rep{repetition}-{query_id}"
        result = self.psql(statement, check=False, output_name=output_name)
        with self.log_path.open("rb") as stream:
            stream.seek(before)
            log_delta = stream.read().decode("utf-8", errors="replace")
        (self.raw / f"{output_name}.trace.log").write_text(log_delta)
        selected_oids = [int(match.group(1)) for match in TRACE_SELECTED.finditer(log_delta)]
        claimed = [int(match.group(2)) for match in TRACE_CLAIMED.finditer(log_delta)]
        trace = {
            "selected_stat_oids": selected_oids,
            "claimed_clause_indices": claimed,
            "candidate_none": bool(TRACE_NONE.search(log_delta)),
            "query_returncode": result.returncode,
            "query_error": result.stderr.strip() if result.returncode else None,
            "log_bytes": len(log_delta.encode("utf-8")),
        }
        return trace, statement

    def one_observation(self, setup: dict[str, object], order_index: int, resource_order: list[str], repetition: int, query_id: str) -> dict[str, object]:
        self.current_resources = resource_order
        rows = self.catalog_rows()
        query = self.queries[query_id]
        clauses = parse_equality_clauses(query["sql"], query["expected_columns"])
        ledger = build_source_ledger(rows, clauses)
        trace, statement = self.query_trace(query_id, str(setup["id"]), order_index, repetition)
        gate = verify_trace_against_ledger(ledger, rows, trace)
        graph_result: dict[str, object] | None = None
        if gate["status"] == "WITHIN_GATE_PASS":
            try:
                graph_result = verify_maximal_matching(
                    self.manifest["fixture"]["candidate_definitions"],
                    ledger["usable_ids"],
                    gate["selected_candidate_ids"],
                )
                if not graph_result["is_inclusion_wise_maximal"]:
                    gate["status"] = "WITHIN_GATE_COUNTEREXAMPLE"
            except MatchingVerificationError as error:
                gate["status"] = "WITHIN_GATE_COUNTEREXAMPLE"
                gate["matching_error"] = str(error)
        return {
            "setup_id": setup["id"],
            "resource_order": resource_order,
            "order_index": order_index,
            "repetition": repetition,
            "query_id": query_id,
            "query_sql": query["sql"],
            "executed_statement": statement,
            "clauses": clauses,
            "catalog_rows": rows,
            "source_ledger": ledger,
            "trace": trace,
            "gate": gate,
            "matching": graph_result,
        }

    def run(self) -> dict[str, object]:
        records: list[dict[str, object]] = []
        self.start()
        try:
            self.setup_table()
            setups = self.manifest["setups"]
            if self.smoke:
                smoke = self.manifest["smoke"]
                setups = [setup for setup in setups if setup["id"] == smoke["setup_id"]]
            for setup in setups:
                order_items = list(enumerate(setup["orders"]))
                if self.smoke:
                    order_items = [item for item in order_items if item[0] == int(self.manifest["smoke"]["order_index"])]
                for order_index, resource_order in order_items:
                    for repetition in range(1, self.repetitions + 1):
                        if self.smoke and repetition != int(self.manifest["smoke"]["repetition"]):
                            continue
                        self.drop_statistics()
                        self.current_resources = list(resource_order)
                        self.create_statistics(resource_order)
                        query_ids = setup["queries"]
                        if self.smoke:
                            query_ids = self.manifest["smoke"]["queries"]
                        for query_id in query_ids:
                            records.append(self.one_observation(setup, order_index, list(resource_order), repetition, query_id))
            output = self.results / "observations.jsonl"
            with output.open("x", encoding="utf-8") as stream:
                for record in records:
                    stream.write(json.dumps(record, sort_keys=True) + "\n")
            counts: dict[str, int] = {}
            for record in records:
                status = str(record["gate"]["status"])
                counts[status] = counts.get(status, 0) + 1
            summary = {
                "format": "ess-issue47-stage2a-result-summary-v1",
                "observation_count": len(records),
                "status_counts": counts,
                "observations_sha256": sha256(output),
                "source_commit": self.manifest["source"]["commit"],
                "runtime_root": str(self.root),
                "pg_version": run_command([str(self.pg_bin / "bin" / "postgres"), "--version"], self.env).stdout.strip(),
            }
            (self.results / "result-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n")
            return summary
        finally:
            self.stop()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--issue-root", type=Path, required=True)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("protocol-manifest.json"))
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    runner = Stage2ARunner(args.issue_root, args.pg_bin, args.manifest, args.repetitions, args.smoke)
    summary = runner.run()
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
