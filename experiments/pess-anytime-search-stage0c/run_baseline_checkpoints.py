"""Budget-sweep endpoint traces for advisor references.

The advisor API does not expose an incumbent callback.  Each row is therefore
explicitly labeled an independent endpoint-at-budget invocation, not a claim
of a continuous within-invocation incumbent trace.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from advisor_adapter import run_solver
from protocol import input_paths, write_json_once
from reference import load, verify_selected

CHECKPOINTS = (0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
METHODS = ("static", "master_oracle")
SEEDS = (3501, 3502, 3503)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).parent)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--protocol", default="stage0c-v3")
    args = parser.parse_args()
    rows: list[dict[str, object]] = []
    for path in input_paths(args.root, args.protocol):
        instance = load(path)
        for seed in SEEDS:
            for method in METHODS:
                endpoints: list[dict[str, object]] = []
                for checkpoint in CHECKPOINTS:
                    record = run_solver(path, method, checkpoint, inner_time_limit=checkpoint)
                    result = record["result"]
                    check = None
                    if result.get("selected") is not None and result.get("objective") is not None:
                        try:
                            check = verify_selected(instance, result["selected"], result["objective"])
                        except AssertionError as exc:
                            check = {"status": "FAIL", "error": str(exc)}
                    endpoints.append({"checkpoint_seconds": checkpoint, "record": record, "independent_check": check})
                rows.append({"instance": path.name, "instance_sha256": sha256(path), "seed": seed, "method": method, "trace_type": "independent_endpoint_at_budget", "endpoints": endpoints})
                print(path.name, seed, method, flush=True)
    payload = {"protocol": args.protocol, "checkpoints": CHECKPOINTS, "rows": rows}
    write_json_once(args.output, payload)
    print(json.dumps({"rows": len(rows), "output": str(args.output)}, sort_keys=True))


if __name__ == "__main__":
    main()
