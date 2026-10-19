"""Run unchanged advisor references on the frozen corpus before search comparisons."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path

from advisor_adapter import run_solver
from protocol import input_paths, write_json_once
from reference import load, verify_selected

METHODS = ("static", "master_oracle")
SEEDS = (3501, 3502, 3503)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).parent)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=float, default=10.0)
    parser.add_argument("--protocol", default="stage0c-v3")
    args = parser.parse_args()
    records: list[dict[str, object]] = []
    for path in input_paths(args.root, args.protocol):
        instance = load(path)
        for seed in SEEDS:
            for method in METHODS:
                started = time.perf_counter()
                adapter = run_solver(path, method, args.limit, inner_time_limit=args.limit)
                adapter["seed"] = seed
                adapter["solver_adapter_wall_seconds"] = adapter["wall_seconds"]
                result = adapter["result"]
                check = None
                if result.get("selected") is not None and result.get("objective") is not None:
                    try:
                        check = verify_selected(instance, result["selected"], result["objective"])
                    except AssertionError as exc:
                        check = {"status": "FAIL", "error": str(exc)}
                adapter["independent_original_pess_check"] = check
                adapter["full_invocation_wall_seconds"] = time.perf_counter() - started
                records.append({
                    "instance": path.name,
                    "instance_sha256": sha256(path),
                    "seed": seed,
                    "method": method,
                    "record": adapter,
                })
                print(path.name, seed, method, result.get("status"), result.get("objective"), flush=True)
    payload = {
        "protocol": args.protocol,
        "baseline": "unchanged ess-advisor Static and default Master-Oracle",
        "limit_seconds": args.limit,
        "records": records,
        "source_head": subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
    }
    write_json_once(args.output, payload)
    print(json.dumps({"records": len(records), "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
