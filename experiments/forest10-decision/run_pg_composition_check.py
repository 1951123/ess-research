"""Measure a few multi-statistic Forest10 compositions under the fixed sample.

This is a bounded PostgreSQL behavior check for the single-statistic
calibration approximation. It records actual selection traces and compares
the measured pre-clamp result with the product of the single-statistic ratios;
it does not change the exact optimizer or claim the product is an identity.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import subprocess
import time
from decimal import Decimal, localcontext
from pathlib import Path
from typing import Any


CASES = (
    {"name": "e12_e34_on_e01", "candidates": ["e12", "e34"], "task": "e01"},
    {"name": "e12_e23_on_e01", "candidates": ["e12", "e23"], "task": "e01"},
    {"name": "e23_e34_on_e01", "candidates": ["e23", "e34"], "task": "e01"},
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
        str(args.pg_bin / "psql"), "-h", str(args.socket_dir), "-p", str(args.port),
        "-d", args.database, "-v", "ON_ERROR_STOP=1", "-X", "-At", "-F", "|", "-c", sql,
    ]
    result = subprocess.run(command, env=env, text=True, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"psql failed: {result.stderr}\nSQL: {sql}")
    return result.stdout


def task_records(root: Path, manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    path = root / "arecel" / "audit-v1" / "forest10.canonical.jsonl.gz"
    wanted = {item["candidate_id"]: item for item in manifest["selection_tasks"]["tasks"]}
    records = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            item = json.loads(line)
            for candidate, frozen in wanted.items():
                if item["query_id"] == frozen["query_id"]:
                    records[candidate] = item
    return records


def final_value(record: dict[str, Any]) -> Decimal:
    traces = [item for item in record["trace"]["numeric"] if "base_relation_oid" in item]
    if len(traces) != 1:
        raise RuntimeError("single-statistic calibration is missing one final pre-clamp trace")
    return Decimal(traces[0]["nrows_preclamp"])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-root", type=Path, default=None)
    parser.add_argument("--manifest", type=Path, default=Path(__file__).with_name("real-input-manifest.json"))
    parser.add_argument("--calibration", type=Path, required=True)
    parser.add_argument("--pg-bin", type=Path, required=True)
    parser.add_argument("--lib-dir", type=Path, required=True)
    parser.add_argument("--socket-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=55433)
    parser.add_argument("--database", default="postgres")
    parser.add_argument("--server-log", type=Path, required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    root = (args.data_root or Path(os.environ["ESS_DATA_ROOT"])).expanduser().resolve()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    calibration = json.loads(args.calibration.read_text(encoding="utf-8"))
    if calibration["manifest_sha256"] != sha256_file(args.manifest):
        raise RuntimeError("calibration does not match the frozen manifest")
    records = task_records(root, manifest)
    single: dict[tuple[str, str], Decimal] = {}
    for record in calibration["results"]:
        if record["repetition"] == 0:
            single[(record["candidate_id"], record["task"]["candidate_id"])] = final_value(record)
    candidates = {item["id"]: item for item in manifest["candidate_rule"]["candidates"]}
    all_names = [f"ess_forest10_{item['id']}" for item in candidates.values()]
    drop = "DROP STATISTICS IF EXISTS " + ", ".join(f"public.{name}" for name in all_names) + ";"
    results = []
    for case in CASES:
        setup = [drop]
        for candidate_id in case["candidates"]:
            columns = ", ".join(f'"{column}"' for column in candidates[candidate_id]["columns"])
            setup.append(
                f"CREATE STATISTICS public.ess_forest10_{candidate_id} (mcv) ON {columns} "
                "FROM public.forest10_original;"
            )
            setup.append(f"ALTER STATISTICS public.ess_forest10_{candidate_id} SET STATISTICS 300;")
        setup.append(
            "SET ess.analyze_sample_import='" + str(args.sample).replace("'", "''") + "'; "
            "ANALYZE public.forest10_original; RESET ess.analyze_sample_import;"
        )
        psql(args, " ".join(setup))
        catalog = psql(
            args,
            "SELECT oid, stxname FROM pg_statistic_ext "
            "WHERE stxname IN (" + ",".join(f"'ess_forest10_{item}'" for item in case["candidates"]) + ") ORDER BY oid;",
        ).splitlines()
        oid_to_candidate = {line.split("|", 1)[0]: line.split("|", 1)[1].removeprefix("ess_forest10_") for line in catalog}
        task = records[case["task"]]
        marker = f"ESS_MCV_NUMERIC_TRACE composition-{case['name']}"
        sql = task["sql"].replace("SELECT COUNT(*)", "EXPLAIN (FORMAT JSON) /* " + marker + " */ SELECT *", 1)
        offset = args.server_log.stat().st_size
        psql(args, sql)
        time.sleep(0.05)
        with args.server_log.open("rb") as stream:
            stream.seek(offset)
            lines = stream.read().decode("utf-8", errors="replace").splitlines()
        matching = [line for line in lines if marker in line]
        selected_oids = sorted(set(re.findall(r"selected_stat_oid=(\d+)", "\n".join(matching))))
        selected_candidates = [oid_to_candidate[oid] for oid in selected_oids if oid in oid_to_candidate]
        endpoints = [set(candidates[item]["columns"]) for item in selected_candidates]
        disjoint = all(not endpoints[i] & endpoints[j] for i in range(len(endpoints)) for j in range(i + 1, len(endpoints)))
        final_matches = re.findall(r"base_relation_oid=.*?nrows_preclamp=([^ ]+)", "\n".join(matching))
        if len(final_matches) != 1:
            raise RuntimeError(f"expected one final composition trace for {case['name']}, got {final_matches}")
        actual = Decimal(final_matches[0])
        baseline = single[("baseline", case["task"])]
        with localcontext() as context:
            context.prec = 50
            predicted = baseline
            for candidate_id in case["candidates"]:
                predicted *= single[(candidate_id, case["task"])] / baseline
            difference = actual - predicted
            relative = difference / predicted if predicted else Decimal("NaN")
        results.append(
            {
                "case": case,
                "catalog": catalog,
                "selected_stat_oids": selected_oids,
                "selected_candidates": selected_candidates,
                "selected_candidates_have_disjoint_endpoints": disjoint,
                "trace_log_line_count": len(matching),
                "baseline_nrows_preclamp": str(baseline),
                "single_stat_product_prediction": str(predicted),
                "actual_multi_stat_nrows_preclamp": str(actual),
                "actual_minus_product": str(difference),
                "relative_difference": str(relative),
                "query_id": task["query_id"],
                "truth": task["source_label"]["cardinality"],
            }
        )
    output = {
        "format": "ess-issue23-forest10-pg-composition-check-v1",
        "evidence_label": "author_reported_locally_observed_postgresql_measurement",
        "manifest_sha256": sha256_file(args.manifest),
        "calibration_sha256": sha256_file(args.calibration),
        "sample_sha256": sha256_file(args.sample),
        "cases": results,
        "interpretation": "single-statistic log corrections are an approximation; actual multi-statistic selection and pre-clamp values are measured here and may differ from the product prediction",
    }
    args.output.write_text(json.dumps(output, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output), "sha256": sha256_file(args.output), "cases": len(results)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
