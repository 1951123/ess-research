"""Run the frozen v1 approximate-search corpus after Gate A."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import subprocess
import sys
from pathlib import Path

from reference import exhaustive, load, verify_selected
from search import run_method


METHODS = ("empty", "singleton", "greedy", "basic", "cache_only", "pess_order", "pess_order_cache")
SEEDS = (3501, 3502, 3503)


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).parent)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--wall-cap", type=float, default=10.0)
    args = parser.parse_args()
    root = args.root
    paths = sorted((root / "instances").glob("*.json"))
    records: list[dict[str, object]] = []
    for path in paths:
        instance = load(path)
        truth = exhaustive(instance) if len(instance["candidates"]) <= 12 else None
        for seed in SEEDS:
            for method in METHODS:
                result = run_method(instance, method, args.wall_cap)
                check = verify_selected(instance, result["selected"], result["objective"])
                if check["objective"] != result["objective"]:
                    raise AssertionError(f"independent check mismatch for {path.name}/{seed}/{method}")
                if truth is not None:
                    result["reference_optimum"] = str(truth["objective"])
                    result["regret"] = str(__import__("fractions").Fraction(result["objective"]) - truth["objective"])
                    result["optimal"] = result["objective"] == str(truth["objective"])
                else:
                    result["reference_optimum"] = None
                    result["regret"] = None
                    result["optimal"] = None
                records.append({
                    "instance": path.name,
                    "instance_sha256": sha256(path),
                    "seed": seed,
                    "method": method,
                    "result": result,
                })
    payload = {
        "protocol": "stage0c-v1",
        "code_sha": git_sha(),
        "python": sys.version,
        "platform": platform.platform(),
        "wall_cap_seconds": args.wall_cap,
        "methods": METHODS,
        "seeds": SEEDS,
        "records": records,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"records": len(records), "output": str(args.output), "code_sha": payload["code_sha"]}, sort_keys=True))


if __name__ == "__main__":
    main()
