"""Run the frozen v1 approximate-search corpus after Gate A."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from fractions import Fraction
from pathlib import Path

from protocol import input_paths, write_json_once
from reference import exhaustive, load, verify_selected
from search_timed import run_method

METHODS = ("empty", "singleton", "greedy", "basic", "cache_only", "pess_order", "pess_order_cache")
SEEDS = (3501, 3502, 3503)


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def add_reference_fields(result: dict[str, object], truth: dict[str, object] | None) -> None:
    if truth is None:
        result["reference_optimum"] = None
        result["regret"] = None
        result["optimal"] = None
        return
    result["reference_optimum"] = str(truth["objective"])
    if result["objective"] is None:
        result["regret"] = None
        result["optimal"] = None
    else:
        result["regret"] = str(Fraction(result["objective"]) - truth["objective"])
        result["optimal"] = result["objective"] == str(truth["objective"])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).parent)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wall-cap", type=float, default=10.0)
    parser.add_argument("--protocol", default="stage0c-v3")
    args = parser.parse_args()
    root = args.root
    paths = input_paths(root, args.protocol)
    records: list[dict[str, object]] = []
    for path in paths:
        instance = load(path)
        truth = exhaustive(instance) if len(instance["candidates"]) <= 12 else None
        for seed in SEEDS:
            for method in METHODS:
                result = run_method(instance, method, args.wall_cap)
                if result["selected"] is not None and result["objective"] is not None:
                    check = verify_selected(instance, result["selected"], result["objective"])
                    if check["objective"] != result["objective"]:
                        raise AssertionError(f"independent check mismatch for {path.name}/{seed}/{method}")
                else:
                    check = {"status": "NO_VALID_INCUMBENT", "objective": None}
                result["independent_original_pess_check"] = check
                add_reference_fields(result, truth)
                records.append({
                    "instance": path.name,
                    "instance_sha256": sha256(path),
                    "seed": seed,
                    "method": method,
                    "result": result,
                })
    payload = {
        "protocol": args.protocol,
        "code_sha": git_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "wall_cap_seconds": args.wall_cap,
        "methods": METHODS,
        "seeds": SEEDS,
        "records": records,
    }
    write_json_once(args.output, payload)
    print(json.dumps({"records": len(records), "output": str(args.output), "code_sha": payload["code_sha"]}, sort_keys=True))


if __name__ == "__main__":
    main()
