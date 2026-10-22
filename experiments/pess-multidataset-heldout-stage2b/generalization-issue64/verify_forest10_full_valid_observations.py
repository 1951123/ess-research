"""Read-only integrity check for the durable Forest10 valid JSON observations.

This module reads only the collection manifest, gzip observations and the
pinned official valid workload. It never opens labels, test splits, or PG.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import sys
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
ISSUE64_ROOT = HERE.parents[2]
sys.path.insert(0, str(ISSUE64_ROOT / "src"))
sys.path.insert(0, str(HERE))

from ess_research.arecel.archive import prepare_valid_workload
from ess_research.arecel.candidates import discover_candidates
from ess_research.arecel.forest10 import SOURCE_COLUMNS
import run_forest10_full_calibration_collector as collector


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _expected_rows(ordered: list[dict], per_candidate: dict[str, tuple[str, ...]]) -> Iterable[tuple[int, str, str, bool | None]]:
    sequence = 0
    configs = [("Empty", [q["query_id"] for q in ordered], None)]
    configs.extend((edge, list(ids), True) for edge, ids in per_candidate.items() if ids)
    for config_id, query_ids, eligible in configs:
        for query_id in query_ids:
            sequence += 1
            yield sequence, query_id, config_id, eligible


def verify(root: Path, workload: dict, discovery: dict) -> dict:
    """Verify a complete acquisition against outcome-free schedule and hashes."""
    manifest = json.loads((root / collector.MANIFEST).read_text(encoding="utf-8"))
    ordered, _candidates, per_candidate = collector.build_schedule(workload, discovery)
    expected_total = len(ordered) + sum(map(len, per_candidate.values()))
    if manifest.get("format") != "ess-issue64-forest10-json-full-collection-v1":
        raise ValueError("unexpected collection manifest format")
    if (manifest.get("status"), manifest.get("completion")) != (
        "SUCCESS", "ALL_174088_CALLS_AND_46_CONFIGURATIONS_COMPLETE"
    ):
        raise ValueError("collection manifest does not declare complete success")
    if manifest.get("truth_objective_selection_test_access") is not False:
        raise ValueError("manifest does not attest outcome-free acquisition")
    if any(manifest.get(key) != expected_total for key in (
        "expected_calls", "attempted_calls", "completed_calls", "committed_observation_count"
    )) or manifest.get("failed_calls") != 0 or manifest.get("unattempted_calls") != 0:
        raise ValueError("manifest call totals are incomplete or inconsistent")

    obs_dir = root / "observations"
    parts_by_name = {part["path"]: part for part in manifest.get("parts", [])}
    if len(parts_by_name) != len(manifest.get("parts", [])):
        raise ValueError("duplicate part path in manifest")
    for part_name, part in parts_by_name.items():
        blob = (obs_dir / part_name).read_bytes()
        if len(blob) != part["compressed_bytes"] or sha256(blob) != part["sha256"]:
            raise ValueError(f"part checksum/size mismatch: {part_name}")
    actual_names = {p.name for p in obs_dir.glob("*.jsonl.gz")}
    if actual_names != set(parts_by_name):
        raise ValueError("observation directory files differ from manifest")

    by_part: dict[str, list[dict]] = {}
    previous_end: dict[str, int] = {}
    for block in manifest.get("durable_blocks", []):
        name = block["part"]
        if name not in parts_by_name:
            raise ValueError("durable block refers to an unlisted part")
        start = block["byte_offset"]
        if start != previous_end.get(name, 0):
            raise ValueError("durable gzip member offsets are not contiguous")
        blob = (obs_dir / name).read_bytes()
        end = start + block["compressed_bytes"]
        member = blob[start:end]
        if len(member) != block["compressed_bytes"] or sha256(member) != block["gzip_member_sha256"]:
            raise ValueError("gzip member checksum mismatch")
        raw = gzip.decompress(member)
        if sha256(raw) != block["uncompressed_sha256"]:
            raise ValueError("gzip member payload checksum mismatch")
        lines = raw.splitlines()
        if len(lines) != block["rows"]:
            raise ValueError("gzip member row count mismatch")
        records = [json.loads(line) for line in lines]
        if records[0]["sequence"] != block["first_sequence"] or records[-1]["sequence"] != block["last_sequence"]:
            raise ValueError("gzip member sequence range mismatch")
        by_part.setdefault(name, []).extend(records)
        previous_end[name] = end
    for name, part in parts_by_name.items():
        if previous_end.get(name, 0) != part["compressed_bytes"]:
            raise ValueError(f"durable members do not cover complete part: {name}")

    expected_iter = iter(_expected_rows(ordered, per_candidate))
    counts = {"rows": 0, "mcv_events": 0, "no_mcv_events": 0}
    for name in sorted(by_part, key=lambda n: parts_by_name[n]["first_sequence"]):
        for row in by_part[name]:
            try:
                seq, query_id, config_id, eligible = next(expected_iter)
            except StopIteration as exc:
                raise ValueError("extra observation row") from exc
            if (row.get("sequence"), row.get("query_id"), row.get("config_id"), row.get("static_eligible")) != (
                seq, query_id, config_id, eligible
            ):
                raise ValueError(f"schedule/order mismatch at sequence {seq}")
            if row.get("status") != "SUCCESS" or row.get("diagnostics_status") != "complete":
                raise ValueError(f"failed/incomplete observation at sequence {seq}")
            try:
                estimate = Decimal(row["nrows_preclamp"])
            except (KeyError, InvalidOperation) as exc:
                raise ValueError(f"invalid pre-clamp estimate at sequence {seq}") from exc
            if not estimate.is_finite() or estimate <= 0:
                raise ValueError(f"nonpositive/nonfinite pre-clamp estimate at sequence {seq}")
            if not isinstance(row.get("relation_oid"), int) or row["relation_oid"] <= 0:
                raise ValueError(f"invalid relation OID at sequence {seq}")
            event_status = row.get("mcv_diagnostics_status")
            events = row.get("mcv_events")
            if not isinstance(events, list):
                raise ValueError(f"missing MCV event list at sequence {seq}")
            if event_status == "NO_MCV_EVENTS":
                if events:
                    raise ValueError(f"NO_MCV_EVENTS has event records at sequence {seq}")
                counts["no_mcv_events"] += 1
            elif event_status == "VERIFIED":
                if not events:
                    raise ValueError(f"MCV_EVENTS has no event records at sequence {seq}")
                counts["mcv_events"] += 1
            else:
                raise ValueError(f"unknown MCV diagnostic status at sequence {seq}")
            counts["rows"] += 1
    try:
        next(expected_iter)
    except StopIteration:
        pass
    else:
        raise ValueError("observations ended before the frozen schedule")
    if counts["rows"] != expected_total:
        raise ValueError("observation total differs from frozen schedule")
    return {"status": "PASS", "labels_loaded": False, "expected_rows": expected_total, **counts,
            "configurations": 1 + sum(bool(ids) for ids in per_candidate.values()),
            "parts": len(parts_by_name)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path, help="durable full-valid run directory")
    args = parser.parse_args()
    with prepare_valid_workload(issue=64, dataset="forest10") as prepared:
        if prepared.manifest.get("labels_loaded") is not False:
            raise RuntimeError("valid workload loader did not attest labels_loaded=false")
        workload = json.loads(prepared.workload_path.read_text(encoding="utf-8"))
        discovery = discover_candidates(workload["queries"], SOURCE_COLUMNS)
        report = verify(args.run, workload, discovery)
    print(json.dumps(report, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
