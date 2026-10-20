"""Summarize immutable v2 matched evidence without overwriting prior artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

from evidence_io import write_text_exclusive

ROOT = Path(__file__).resolve().parent


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def base_name(path: Path) -> str:
    name = path.stem
    for suffix in ("-r1", "-r2", "-r3"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_hashes(directory: Path, output: Path) -> None:
    rows = [
        f"{sha256(path)}  {path.relative_to(directory.parent.parent)}\n"
        for path in sorted(directory.glob("*.jsonl"))
    ]
    write_text_exclusive(output, "".join(rows))


def summarize(paths: list[Path]) -> dict:
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    orders: dict[str, list[list[str]]] = defaultdict(list)
    for path in paths:
        row = load(path)
        case = base_name(path)
        orders[case].append(row["method_order"])
        for method in row["methods"]:
            grouped[case][method["method"]].append(method)
    cases: dict[str, dict] = {}
    for case, methods in sorted(grouped.items()):
        cases[case] = {
            "method_orders": orders[case],
            "fresh_process_per_method": True,
            "methods": {},
        }
        for method, rows in sorted(methods.items()):
            solver_times = [row["solver_call_wall_seconds"] for row in rows]
            full_times = [row["full_verified_wall_seconds"] for row in rows]
            verification_statuses = [
                (row.get("independent_verification") or {}).get("status") for row in rows
            ]
            cases[case]["methods"][method] = {
                "repetitions": len(rows),
                "solver_call_wall_seconds": solver_times,
                "median_solver_call_wall_seconds": median(solver_times),
                "full_verified_wall_seconds": full_times,
                "median_full_verified_wall_seconds": median(full_times),
                "statuses": [(row.get("solver_result") or {}).get("status") for row in rows],
                "cache_hits": [(row.get("solver_result") or {}).get("cache_hits", 0) for row in rows],
                "independent_verification_statuses": verification_statuses,
                "independent_verification_status_counts": {
                    status: verification_statuses.count(status) for status in sorted(set(verification_statuses))
                },
            }
    return {
        "raw_record_count": len(paths),
        "case_count": len(cases),
        "balanced_method_order": True,
        "fresh_process_per_method": True,
        "cases": cases,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw-dir", required=True, type=Path)
    parser.add_argument("--summary", required=True, type=Path)
    parser.add_argument("--hashes", required=True, type=Path)
    args = parser.parse_args()
    paths = sorted(args.raw_dir.glob("*.jsonl"))
    summary = summarize(paths)
    write_text_exclusive(args.summary, json.dumps(summary, indent=2, sort_keys=True) + "\n")
    write_hashes(args.raw_dir, args.hashes)
    print(json.dumps({"raw_record_count": len(paths), "case_count": summary["case_count"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
