"""Summarize immutable Stage 2C JSONL and write raw-artifact hashes."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from statistics import median

ROOT = Path(__file__).resolve().parent
PROFILE = ROOT / "runs" / "20261020-profile-v1" / "raw"
MATCHED = ROOT / "runs" / "20261020-matched-v1" / "raw"

HARD = {
    "large_cycle_3922",
    "large_mixed_parallel_3923",
    "large_sharing_cycle_3924",
    "shared_cycle_4905",
    "conflicting_cycles_4907",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def base_name(path: Path) -> str:
    name = path.stem
    for suffix in ("-r2", "-r3"):
        if name.endswith(suffix):
            return name[: -len(suffix)]
    return name


def protocol_key(call: dict) -> str:
    payload = dict(call["key_payload"])
    payload.pop("selected_global_labels", None)
    return json.dumps(payload, sort_keys=True, separators=(",", ":"))


def profile_row(path: Path) -> dict:
    row = load(path)
    groups: dict[str, list[dict]] = defaultdict(list)
    for call in row["calls"]:
        groups[protocol_key(call)].append(call)
    repeats = [call for group in groups.values() for call in group[1:]]
    total = row["task_oracle_wall_seconds"]
    repeated_seconds = sum(call["duration_seconds"] for call in repeats)
    return {
        "file": str(path.relative_to(ROOT)),
        "case": base_name(path),
        "outcome": row["outcome"],
        "input_sha256": row["input_sha256"],
        "task_oracle_call_count": len(row["calls"]),
        "strict_full_key_duplicate_calls": row["full_key_duplicate_call_count"],
        "strict_full_key_duplicate_fraction": row["full_key_duplicate_fraction_of_task_oracle_wall"],
        "protocol_key_unique_count": len(groups),
        "protocol_key_duplicate_calls": len(repeats),
        "protocol_key_duplicate_wall_seconds": repeated_seconds,
        "protocol_key_duplicate_fraction": repeated_seconds / total if total else 0.0,
        "task_oracle_wall_seconds": total,
        "full_invocation_wall_seconds": row["full_invocation_wall_seconds"],
        "solver_status": (row.get("solver_result") or {}).get("status"),
        "solver_validated_feasible": (row.get("solver_result") or {}).get("validated_feasible"),
    }


def matched_summary(paths: list[Path]) -> dict[str, dict]:
    grouped: dict[str, dict[str, list[dict]]] = defaultdict(lambda: defaultdict(list))
    for path in paths:
        row = load(path)
        for method in row["methods"]:
            grouped[base_name(path)][method["method"]].append(method)
    result: dict[str, dict] = {}
    for case, methods in sorted(grouped.items()):
        result[case] = {}
        for method, rows in sorted(methods.items()):
            statuses = [(row.get("solver_result") or {}).get("status") for row in rows]
            hits = [(row.get("solver_result") or {}).get("cache_hits", 0) for row in rows]
            result[case][method] = {
                "repetitions": len(rows),
                "wall_seconds": [row["wall_seconds"] for row in rows],
                "median_wall_seconds": median(row["wall_seconds"] for row in rows),
                "statuses": statuses,
                "cache_hits": hits,
                "independent_verification_statuses": [
                    (row.get("independent_verification") or {}).get("status") for row in rows
                ],
            }
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_hashes(directory: Path, output: Path) -> None:
    rows = [
        f"{sha256(path)}  {path.relative_to(directory.parent.parent)}\n"
        for path in sorted(directory.glob("*.jsonl"))
    ]
    output.write_text("".join(rows), encoding="utf-8", newline="\n")


def main() -> None:
    profile_paths = sorted(PROFILE.glob("*.jsonl"))
    matched_paths = sorted(MATCHED.glob("*.jsonl"))
    profile_rows = [profile_row(path) for path in profile_paths]
    profile_by_case: dict[str, list[dict]] = defaultdict(list)
    for row in profile_rows:
        profile_by_case[row["case"]].append(row)
    profile_cases = {}
    for case, rows in sorted(profile_by_case.items()):
        profile_cases[case] = {
            "repetitions": len(rows),
            "protocol_duplicate_fraction": [row["protocol_key_duplicate_fraction"] for row in rows],
            "median_protocol_duplicate_fraction": median(row["protocol_key_duplicate_fraction"] for row in rows),
            "protocol_duplicate_calls": [row["protocol_key_duplicate_calls"] for row in rows],
            "hard_case": case in HARD,
            "all_repetitions_below_10_percent": all(row["protocol_key_duplicate_fraction"] < 0.10 for row in rows),
        }
    profile_summary = {
        "raw_record_count": len(profile_rows),
        "case_count": len(profile_cases),
        "hard_cases": sorted(HARD),
        "no_op_stop_triggered": all(
            profile_cases[case]["all_repetitions_below_10_percent"] for case in HARD
        ),
        "records": profile_rows,
        "cases": profile_cases,
    }
    (ROOT / "profile-summary-v1.json").write_text(json.dumps(profile_summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    matched = {
        "raw_record_count": len(matched_paths),
        "case_count": len({base_name(path) for path in matched_paths}),
        "cases": matched_summary(matched_paths),
    }
    (ROOT / "matched-summary-v1.json").write_text(json.dumps(matched, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_hashes(PROFILE, ROOT / "runs" / "20261020-profile-v1" / "SHA256SUMS-raw")
    write_hashes(MATCHED, ROOT / "runs" / "20261020-matched-v1" / "SHA256SUMS-raw")
    print(json.dumps({"profile_records": len(profile_rows), "matched_records": len(matched_paths), "no_op_stop_triggered": profile_summary["no_op_stop_triggered"]}, sort_keys=True))


if __name__ == "__main__":
    main()
