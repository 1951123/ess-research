"""Run the frozen Stage 0B reference/approximation pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
from time import perf_counter

from approx import solve_rounded
from quantization import certify_matching_errors, quantized_coefficients
from reference import Instance, exact_outer_optimum
from serialization import fraction_text, instance_from_json, read_json, write_json


ROOT = Path(__file__).resolve().parent
MANIFEST = ROOT / "pilot-manifest-v1.json"
INSTANCE_DIR = ROOT / "instances"


def git_sha() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def protocol_sha() -> str:
    repo_root = Path(subprocess.check_output(["git", "rev-parse", "--show-toplevel"], cwd=ROOT, text=True).strip())
    sha = subprocess.check_output(
        ["git", "log", "-1", "--format=%H", "--", str(MANIFEST.relative_to(repo_root))],
        cwd=repo_root,
        text=True,
    ).strip()
    if not sha:
        raise RuntimeError("cannot find the protocol commit")
    subprocess.run(["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=ROOT, check=True)
    return sha


def setup_deltas(instance: Instance, setup_id: str) -> dict[str, Fraction | None]:
    if setup_id == "unrounded":
        return {task.name: None for task in instance.tasks}
    if setup_id == "coarse_uniform_delta_1":
        return {task.name: Fraction(1) for task in instance.tasks}
    if setup_id not in {"matching_aware_eta_1_2", "matching_aware_eta_1_4"}:
        raise ValueError(setup_id)
    eta_budget = Fraction(1, 2) if setup_id.endswith("1_2") else Fraction(1, 4)
    from quantization import ordinary_matching_max_weight_recursive

    result: dict[str, Fraction | None] = {}
    for task in instance.tasks:
        nu, _ = ordinary_matching_max_weight_recursive(task.edges, {label: Fraction(1) for label in task.coefficients})
        denominator = len(instance.tasks) * max(Fraction(1), task.weight * nu)
        result[task.name] = min(Fraction(1), 2 * eta_budget / denominator)
    return result


def fraction_map(value):
    if isinstance(value, Fraction):
        return fraction_text(value)
    if isinstance(value, dict):
        return {key: fraction_map(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [fraction_map(item) for item in value]
    return value


def evaluate_instance(instance: Instance, setup_id: str, manifest: dict) -> dict:
    tier = instance.tier
    exact_tiny = tier == "small"
    if tier == "small":
        time_limit = float(manifest["resource_caps"]["small_wall_time_seconds"])
        state_cap = int(manifest["resource_caps"]["exact_outer_state_cap_small"])
        tau = Fraction(manifest["quality_targets"]["small_tau"])
    else:
        time_limit = float(manifest["resource_caps"]["stress_wall_time_seconds"])
        state_cap = int(manifest["resource_caps"]["approx_state_cap_stress"])
        tau = Fraction(manifest["quality_targets"]["stress_tau"])

    deltas = setup_deltas(instance, setup_id)
    rounded = quantized_coefficients(instance, deltas)
    cert_start = perf_counter()
    perturbation = certify_matching_errors(instance, rounded)
    cert_seconds = perf_counter() - cert_start
    approx = solve_rounded(
        instance,
        rounded,
        exact_tiny=exact_tiny,
        time_limit_seconds=time_limit,
        state_cap=state_cap,
    )
    original_value = None
    if approx.selection is not None:
        original_value = instance.objective(approx.selection)

    rounded_lower = approx.rounded_value if approx.complete_global_search else None
    rounded_upper = approx.rounded_value if approx.selection is not None else None
    eta = perturbation["eta"]
    if approx.complete_global_search and approx.rounded_value is not None and original_value is not None:
        lower = max(Fraction(0), rounded_lower - eta)
        upper = min(original_value, rounded_upper + eta)
        certified = lower <= upper
        gap = upper - lower if certified else None
        status = "CERTIFIED" if certified else "NO-GO_CERTIFICATE_VIOLATION"
    else:
        lower = Fraction(0) if original_value is not None else None
        upper = original_value
        certified = False
        gap = None
        status = "UNCERTIFIED_INCONCLUSIVE"
    return fraction_map({
        "instance": instance.name,
        "tier": tier,
        "setup": setup_id,
        "deltas": deltas,
        "rounded_coefficients": rounded,
        "perturbation": perturbation,
        "approximation": {
            "engine": approx.engine,
            "global_rounded_search_certified": approx.complete_global_search,
            "rounded_value": approx.rounded_value,
            "selection": sorted(approx.selection) if approx.selection is not None else None,
            "states": approx.states,
            "elapsed_seconds": approx.elapsed_seconds,
            "stop_reason": approx.stop_reason,
        },
        "original": {
            "incumbent_value": original_value,
            "lower": lower,
            "upper": upper,
            "gap": gap,
            "certified": certified,
            "status": status,
            "target_tau": tau,
            "target_reached": certified and gap <= tau,
        },
        "certificate_overhead_seconds": cert_seconds,
    })


def run(run_dir: Path) -> None:
    if run_dir.exists():
        raise SystemExit(f"refusing to overwrite existing run directory: {run_dir}")
    manifest = read_json(MANIFEST)
    if not manifest.get("committed_before_comparison_run"):
        raise RuntimeError("protocol is not marked frozen")
    run_dir.mkdir(parents=True)
    protocol = protocol_sha()
    current = git_sha()
    write_json(run_dir / "manifest-copy.json", manifest)
    environment = {
        "captured_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": sys.version,
        "platform": platform.platform(),
        "processor": platform.processor(),
        "git_sha_at_run": current,
        "protocol_commit": protocol,
        "command": " ".join(sys.argv),
        "dependencies": "stdlib-only correctness/pilot runner",
    }
    write_json(run_dir / "environment.json", environment)

    records = []
    for path in sorted(INSTANCE_DIR.glob("*.json")):
        instance = instance_from_json(read_json(path))
        for setup_id in ("unrounded", "coarse_uniform_delta_1", "matching_aware_eta_1_2", "matching_aware_eta_1_4"):
            record = evaluate_instance(instance, setup_id, manifest)
            if instance.tier == "small":
                truth = exact_outer_optimum(instance, time_limit_seconds=30, state_cap=4096)
                record["reference_a"] = fraction_map({
                    "truth_available": truth.complete,
                    "truth_value": truth.best_value,
                    "truth_selection": sorted(truth.best_selection) if truth.best_selection is not None else None,
                    "states": truth.states,
                    "elapsed_seconds": truth.elapsed_seconds,
                    "stop_reason": truth.stop_reason,
                })
            else:
                truth = exact_outer_optimum(instance, time_limit_seconds=5, state_cap=10000)
                record["reference_a"] = fraction_map({
                    "truth_available": truth.complete,
                    "truth_value": truth.best_value if truth.complete else None,
                    "truth_selection": sorted(truth.best_selection) if truth.complete and truth.best_selection is not None else None,
                    "states": truth.states,
                    "elapsed_seconds": truth.elapsed_seconds,
                    "stop_reason": truth.stop_reason,
                    "truth_policy": "TRUTH_UNAVAILABLE_OR_TIMEOUT is data; no heuristic is promoted to truth",
                })
            record["reference_b"] = {
                "status": "NOT_EXECUTED",
                "reason": "No unchanged reproducible external solver adapter was added; ess-advisor and production code are out of scope.",
            }
            records.append(record)
    with (run_dir / "observations.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    summary = {
        "instances": len({record["instance"] for record in records}),
        "runs": len(records),
        "certificate_violations": sum(record["original"]["status"] == "NO-GO_CERTIFICATE_VIOLATION" for record in records),
        "certified_runs": sum(record["original"]["certified"] for record in records),
        "target_reached_runs": sum(record["original"]["target_reached"] for record in records),
        "reference_b": "NOT_EXECUTED",
        "decision": "INCONCLUSIVE",
        "decision_reason": "The pilot has no equal-clock unchanged solver baseline; approximate stress results without a global rounded lower bound are not global optimality certificates.",
        "protocol_commit": protocol,
        "git_sha_at_run": current,
    }
    write_json(run_dir / "summary.json", summary)
    (run_dir / "report.md").write_text(
        "# Stage 0B pilot run\n\n"
        f"Protocol commit: `{protocol}`.\n\n"
        "Reference B is explicitly **NOT EXECUTED** because this child task does not modify `ess-advisor` or add production solver code. Small-tier exhaustive rounded searches produce valid scoped certificates; stress-tier greedy rows without a proven global rounded lower bound remain `UNCERTIFIED_INCONCLUSIVE`. No heuristic is labeled globally optimal.\n\n"
        "The decision is **INCONCLUSIVE**, not a solver-speedup claim. See `observations.jsonl` for original-model values, rounded values, eta, and failures/timeouts.\n",
        encoding="utf-8",
    )
    digest_lines = []
    for path in sorted(run_dir.iterdir()):
        if path.name == "SHA256SUMS":
            continue
        digest_lines.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}")
    (run_dir / "SHA256SUMS").write_text("\n".join(digest_lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.run_dir)


if __name__ == "__main__":
    main()
