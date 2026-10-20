"""Gate A: exact tiny references plus one bounded medium pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

from pess_ess.model import read_instance

from independent_reference import exhaustive

ROOT = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_one(instance: Path, method: str, budget: float, repetition_seed: int, run_id: str, timeout: float) -> dict[str, object]:
    command = [
        sys.executable,
        str(ROOT / "run_one.py"),
        "--instance", str(instance),
        "--method", method,
        "--budget-seconds", str(budget),
        "--inner-budget-seconds", str(min(5.0, budget)),
        "--repetition-seed", str(repetition_seed),
        "--run-id", run_id,
    ]
    started = time.perf_counter()
    try:
        completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout, check=False)
        record = json.loads(completed.stdout.strip().splitlines()[-1])
        record["wrapper_wall_seconds"] = time.perf_counter() - started
        record["command"] = command
        record["returncode"] = completed.returncode
        if completed.stderr:
            record["stderr"] = completed.stderr
        return record
    except subprocess.TimeoutExpired as exc:
        return {
            "outcome": "timeout",
            "run_id": run_id,
            "instance": str(instance),
            "method": method,
            "budget_seconds": budget,
            "command": command,
            "timeout_seconds": timeout,
            "stdout_tail": (exc.stdout or "")[-2000:],
            "stderr_tail": (exc.stderr or "")[-2000:],
        }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--pilot-medium", action="store_true")
    args = parser.parse_args()
    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=False)
    manifest = json.loads((ROOT / "manifest-v1.json").read_text(encoding="utf-8"))
    records: list[dict[str, object]] = []
    exact_by_file: dict[str, object] = {}
    for item in manifest["instances"]:
        path = ROOT / item["file"]
        if sha256(path) != item["sha256"]:
            raise SystemExit(f"manifest hash mismatch: {path}")
        if item["tier"] == "small":
            exact = exhaustive(read_instance(path))
            exact_by_file[item["file"]] = exact
            for method in ("static", "master_oracle"):
                record = run_one(path, method, 5.0, 7101, f"gate-a-{path.stem}-{method}", 10.0)
                record["exact_reference"] = {
                    "objective": str(exact.objective),
                    "evaluated_subsets": exact.evaluated_subsets,
                    "feasible_subsets": exact.feasible_subsets,
                }
                verification = record.get("independent_verification", {})
                record["gate_a_pass"] = (
                    record.get("outcome") == "completed"
                    and isinstance(verification, dict)
                    and verification.get("status") == "PASS"
                    and verification.get("objective") == str(exact.objective)
                )
                records.append(record)
    if args.pilot_medium:
        for item in manifest["instances"]:
            if item["file"] in {"instances/medium_star_single_3911.json", "instances/medium_star_forest_3911.json"}:
                path = ROOT / item["file"]
                for method in ("static", "master_oracle"):
                    records.append(run_one(path, method, 5.0, 7101, f"medium-pilot-{path.stem}-{method}", 10.0))
    (output_dir / "gate-a.jsonl").write_text("".join(json.dumps(record, sort_keys=True) + "\n" for record in records), encoding="utf-8")
    summary = {
        "protocol": "protocol-v1.json",
        "manifest": "manifest-v1.json",
        "records": len(records),
        "tiny_reference_instances": len(exact_by_file),
        "tiny_gate_a_passes": sum(bool(record.get("gate_a_pass")) for record in records),
        "tiny_gate_a_failures": [record.get("run_id") for record in records if "gate_a_pass" in record and not record["gate_a_pass"]],
        "medium_pilot_requested": args.pilot_medium,
        "medium_pilot_records": sum(1 for record in records if str(record.get("run_id", "")).startswith("medium-pilot-")),
        "environment_python": sys.version,
    }
    (output_dir / "gate-a-summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(summary, sort_keys=True))
    return 0 if not summary["tiny_gate_a_failures"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
