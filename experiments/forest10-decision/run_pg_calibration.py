"""Run the frozen Forest10 PostgreSQL calibration protocol.

This script is deliberately a measurement harness, not a model solver.  It
uses the already-frozen real-input manifest and canonical workload, the
merged fixed-sample PostgreSQL interface, and the separately instrumented
pre-clamp trace build.  The output keeps PostgreSQL observations separate
from the exact model input generated later.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any


TRACE_NUMERIC = re.compile(
    r"ESS_MCV_NUMERIC_TRACE: (?P<body>.*)"
)
TRACE_SELECTED = re.compile(
    r"ESS_MCV_TRACE: (?P<body>.*)"
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def psql(args: argparse.Namespace, sql: str) -> str:
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(args.lib_dir)
    command = [
        str(args.pg_bin / "psql"),
        "-h",
        str(args.socket_dir),
        "-p",
        str(args.port),
        "-d",
        args.database,
        "-v",
        "ON_ERROR_STOP=1",
        "-X",
        "-At",
        "-F",
        "|",
        "-c",
        sql,
    ]
    completed = subprocess.run(
        command,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"psql failed ({completed.returncode}): {shlex.join(command)}\n"
            f"stdout={completed.stdout}\nstderr={completed.stderr}"
        )
    return completed.stdout


def load_tasks(root: Path, manifest: dict[str, Any]) -> list[dict[str, Any]]:
    wanted = {item["query_id"]: item for item in manifest["selection_tasks"]["tasks"]}
    canonical = root / "arecel" / "audit-v1" / "forest10.canonical.jsonl.gz"
    found: dict[str, dict[str, Any]] = {}
    with gzip.open(canonical, "rt", encoding="utf-8") as stream:
        for line in stream:
            record = json.loads(line)
            if record.get("query_id") in wanted:
                found[record["query_id"]] = record
    if set(found) != set(wanted):
        raise RuntimeError("frozen task IDs were not all found in the canonical workload")
    tasks = []
    for item in manifest["selection_tasks"]["tasks"]:
        record = found[item["query_id"]]
        if record["source_query_sha256"] != item["source_query_sha256"]:
            raise RuntimeError(f"source query hash changed for {item['query_id']}")
        if record["source_label"]["cardinality"] != item["truth"]:
            raise RuntimeError(f"truth cardinality changed for {item['query_id']}")
        source_sql = record["sql"]
        if not source_sql.startswith("SELECT COUNT(*)"):
            raise RuntimeError(f"unexpected source SQL for {item['query_id']}")
        tasks.append(
            {
                "candidate_id": item["candidate_id"],
                "query_id": item["query_id"],
                "truth": item["truth"],
                "source_query_sha256": item["source_query_sha256"],
                "sql": source_sql.replace("SELECT COUNT(*)", "SELECT *", 1),
                "predicates": record["source_query"]["predicates"],
            }
        )
    return tasks


def log_lines(path: Path, offset: int) -> tuple[int, list[str]]:
    with path.open("rb") as stream:
        stream.seek(offset)
        data = stream.read()
        new_offset = stream.tell()
    return new_offset, data.decode("utf-8", errors="replace").splitlines()


def key_values(body: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for match in re.finditer(r"(\w+)=((?:\"[^\"]*\")|(?:[^ ]+))", body):
        result[match.group(1)] = match.group(2).strip('"')
    return result


def collect_trace(lines: list[str], marker: str) -> dict[str, Any]:
    numeric: list[dict[str, str]] = []
    selected: list[dict[str, str]] = []
    for line in lines:
        if marker not in line:
            continue
        numeric_match = TRACE_NUMERIC.search(line)
        if numeric_match:
            numeric.append(key_values(numeric_match.group("body")))
        selected_match = TRACE_SELECTED.search(line)
        if selected_match:
            selected.append(key_values(selected_match.group("body")))
    return {"numeric": numeric, "selected": selected, "matching_log_lines": len(numeric) + len(selected)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("real-input-manifest.json"))
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--lib-dir", type=Path, required=True)
    parser.add_argument("--socket-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55433)
    parser.add_argument("--database", default="postgres")
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=2)
    args = parser.parse_args()
    data_root = (args.data_root or Path(os.environ["ESS_DATA_ROOT"])).expanduser().resolve()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    if manifest["data_root"] != str(data_root):
        raise RuntimeError("manifest data_root does not match the supplied data root")
    sample_sha = sha256_file(args.sample)
    tasks = load_tasks(data_root, manifest)
    candidates = manifest["candidate_rule"]["candidates"]
    args.output_dir.mkdir(parents=True, exist_ok=True)

    names = [f"ess_forest10_{item['id']}" for item in candidates]
    drop_sql = "DROP STATISTICS IF EXISTS " + ", ".join(f"public.{name}" for name in names) + ";"
    results: list[dict[str, Any]] = []
    log_offset = args.server_log.stat().st_size

    for repetition in range(args.repetitions):
        for candidate in [{"id": "baseline", "columns": []}, *candidates]:
            stat_name = f"ess_forest10_{candidate['id']}"
            setup = [drop_sql]
            if candidate["columns"]:
                columns = ", ".join('"' + column.replace('"', '""') + '"' for column in candidate["columns"])
                setup.append(
                    f"CREATE STATISTICS public.{stat_name} (mcv) ON {columns} "
                    "FROM public.forest10_original;"
                )
                setup.append(f"ALTER STATISTICS public.{stat_name} SET STATISTICS 300;")
            setup.append(
                "SET ess.analyze_sample_import='" + str(args.sample).replace("'", "''") + "'; "
                "ANALYZE public.forest10_original; RESET ess.analyze_sample_import;"
            )
            psql(args, " ".join(setup))
            stats_rows = psql(
                args,
                "SELECT s.oid, s.stxname, s.stxkeys, s.stxstattarget, "
                "d.stxdmcv IS NULL, COALESCE(pg_column_size(d.stxdmcv), 0) "
                "FROM pg_statistic_ext s JOIN pg_statistic_ext_data d ON d.stxoid=s.oid "
                f"WHERE s.stxname='{stat_name}';",
            ).splitlines()
            mcv_rows = psql(
                args,
                "SELECT m.index, m.values::text, m.frequency, m.base_frequency "
                "FROM pg_statistic_ext s JOIN pg_statistic_ext_data d ON d.stxoid=s.oid "
                "CROSS JOIN LATERAL pg_mcv_list_items(d.stxdmcv) m "
                f"WHERE s.stxname='{stat_name}' ORDER BY m.index;",
            ).splitlines()
            for task in tasks:
                marker = f"ESS_MCV_NUMERIC_TRACE issue23-{repetition}-{candidate['id']}-{task['query_id']}"
                sql = task["sql"].replace("/*", f"/* {marker} */ /*", 1) if "/*" in task["sql"] else (
                    f"EXPLAIN (FORMAT JSON) /* {marker} */ {task['sql']}"
                )
                if not sql.startswith("EXPLAIN"):
                    sql = f"EXPLAIN (FORMAT JSON) /* {marker} */ {sql}"
                plan = psql(args, sql)
                time.sleep(0.05)
                log_offset, lines = log_lines(args.server_log, log_offset)
                trace = collect_trace(lines, marker)
                if not trace["numeric"]:
                    raise RuntimeError(f"no numeric trace captured for {marker}")
                results.append(
                    {
                        "repetition": repetition,
                        "candidate_id": candidate["id"],
                        "statistic_name": stat_name,
                        "task": task,
                        "sample_sha256": sample_sha,
                        "statistics_catalog_rows": stats_rows,
                        "mcv_rows": mcv_rows,
                        "explain_json_text": plan,
                        "trace": trace,
                    }
                )

    output = {
        "format": "ess-issue23-forest10-pg-calibration-v1",
        "evidence_label": "experimentally_observed_postgresql_measurement",
        "manifest_sha256": sha256_file(args.manifest),
        "sample": {"path": str(args.sample), "sha256": sample_sha, "bytes": args.sample.stat().st_size},
        "server_log": str(args.server_log),
        "protocol": {
            "repetitions": args.repetitions,
            "candidate_count": len(candidates),
            "task_count": len(tasks),
            "fixed_sample_replayed_before_each_analyze": True,
            "plan_rows_not_used_as_preclamp": True,
        },
        "results": results,
    }
    target = args.output_dir / "calibration.json"
    target.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(target), "sha256": sha256_file(target), "records": len(results)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
