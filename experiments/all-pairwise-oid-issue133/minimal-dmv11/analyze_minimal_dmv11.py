"""Verify the runtime archive and summarize the frozen DMV11 three-arm run."""
from __future__ import annotations

import argparse
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

import run_minimal_dmv11 as runner


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def read_member(archive: Path, descriptor: dict[str, Any]) -> list[dict[str, Any]]:
    with archive.open("rb") as stream:
        stream.seek(int(descriptor["offset"]))
        member = stream.read(int(descriptor["bytes"]))
    if sha256_bytes(member) != descriptor["sha256"]:
        raise ValueError("raw archive member hash mismatch")
    raw = gzip.decompress(member)
    rows = [json.loads(line) for line in raw.splitlines() if line]
    if len(rows) != int(descriptor["rows"]):
        raise ValueError("raw archive member row count mismatch")
    return rows


def load_run(run_root: Path) -> tuple[dict[str, Any], dict[str, list[dict[str, Any]]]]:
    manifest_path = run_root / "run-manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("status") != "COMPLETE":
        raise ValueError(f"physical run is {manifest.get('status')}, not COMPLETE")
    archive = run_root / "raw-observations.jsonl.gz"
    archive_meta = manifest["raw_archive"]
    if sha256_bytes(archive.read_bytes()) != archive_meta["sha256"]:
        raise ValueError("whole raw archive hash mismatch")
    arms: dict[str, list[dict[str, Any]]] = {}
    for audit, member in zip(manifest["arms"], archive_meta["members"], strict=True):
        config_id = audit["configuration_id"]
        if member != audit["raw_member"]:
            raise ValueError(f"{config_id}: manifest member identity mismatch")
        rows = read_member(archive, member)
        if len(rows) != 10_000 or any(row["configuration_id"] != config_id for row in rows):
            raise ValueError(f"{config_id}: incomplete or misattributed Test rows")
        if len({row["query_id"] for row in rows}) != 10_000:
            raise ValueError(f"{config_id}: duplicate query IDs")
        if any(row["status"] != "VALID" or row["qerror"] is None for row in rows):
            raise ValueError(f"{config_id}: invalid Plan Rows/Q-error in raw rows")
        if any(row["candidate_id_attribution_status"] not in {"PASS", "PASS_EMPTY"}
               for row in rows):
            raise ValueError(f"{config_id}: incomplete candidate attribution")
        arms[config_id] = rows
    if len(arms) != 3:
        raise ValueError("expected exactly three complete arms")
    reference_ids = [row["query_id"] for row in arms[runner.ALL01]]
    for config_id, rows in arms.items():
        if [row["query_id"] for row in rows] != reference_ids:
            raise ValueError(f"{config_id}: query order differs from frozen Test input")
    return manifest, arms


def metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    q = np.asarray([row["qerror"] for row in rows], dtype=np.float64)
    return {
        "query_count": len(rows),
        "p50": float(np.percentile(q, 50)),
        "p95": float(np.percentile(q, 95)),
        "p99": float(np.percentile(q, 99)),
        "mean": float(np.mean(q)),
        "valid_plan_rows": sum(row["plan_rows_integrity_status"] == "VALID" for row in rows),
        "extension_status_counts": dict(sorted(Counter(
            str(row["extension_diagnostics_status"]) for row in rows
        ).items())),
        "diagnostics_integrity_counts": dict(sorted(Counter(
            row["diagnostics_integrity_status"] for row in rows
        ).items())),
        "candidate_attribution_counts": dict(sorted(Counter(
            row["candidate_id_attribution_status"] for row in rows
        ).items())),
    }


def sequence(row: dict[str, Any]) -> list[str | None]:
    return row["mcv_selection_ids"]


def paired(left: list[dict[str, Any]], right: list[dict[str, Any]],
           left_name: str, right_name: str, all_only_ids: set[str] | None = None,
           shared_ids: set[str] | None = None) -> dict[str, Any]:
    left_by_id = {row["query_id"]: row for row in left}
    right_by_id = {row["query_id"]: row for row in right}
    if left_by_id.keys() != right_by_id.keys():
        raise ValueError("paired comparison query IDs differ")
    plan_changed = q_changed = sequence_changed = q_better = q_worse = q_same = 0
    plan_changed_q_same = 0
    delta: list[float] = []
    all_only_events = 0
    all_only_queries = 0
    shared_usage = {candidate_id: {left_name: 0, right_name: 0}
                    for candidate_id in sorted(shared_ids or set())}
    examples: list[dict[str, Any]] = []
    for query_id in left_by_id:
        a, b = left_by_id[query_id], right_by_id[query_id]
        pa = a["estimate_plan_rows"] != b["estimate_plan_rows"]
        qa, qb = float(a["qerror"]), float(b["qerror"])
        qc = qa != qb
        sc = sequence(a) != sequence(b)
        plan_changed += pa
        q_changed += qc
        sequence_changed += sc
        if pa and not qc:
            plan_changed_q_same += 1
        q_better += qa < qb
        q_worse += qa > qb
        q_same += qa == qb
        delta.append(qa - qb)
        if all_only_ids:
            used = set(sequence(a)) & all_only_ids
            all_only_events += sum(sequence(a).count(candidate_id) for candidate_id in used)
            all_only_queries += bool(used)
        for row, name in ((a, left_name), (b, right_name)):
            if shared_ids:
                for candidate_id in set(sequence(row)) & shared_ids:
                    shared_usage[candidate_id][name] += 1
        if sc and (pa or qc) and len(examples) < 12:
            examples.append({
                "query_id": query_id,
                f"{left_name}_plan_rows": a["estimate_plan_rows"],
                f"{right_name}_plan_rows": b["estimate_plan_rows"],
                f"{left_name}_qerror": qa,
                f"{right_name}_qerror": qb,
                f"{left_name}_mcv_selection_ids": sequence(a),
                f"{right_name}_mcv_selection_ids": sequence(b),
            })
    d = np.asarray(delta, dtype=np.float64)
    return {
        "left_minus_right": f"{left_name} - {right_name}",
        "query_count": len(delta),
        "plan_rows_changed_count": int(plan_changed),
        "qerror_changed_count": int(q_changed),
        "mcv_selection_sequence_changed_count": int(sequence_changed),
        "plan_rows_changed_qerror_unchanged_count": int(plan_changed_q_same),
        "left_qerror_better_count": int(q_better),
        "left_qerror_worse_count": int(q_worse),
        "qerror_equal_count": int(q_same),
        "paired_qerror_delta_left_minus_right": {
            "mean": float(np.mean(d)),
            "median": float(np.percentile(d, 50)),
            "p05": float(np.percentile(d, 5)),
            "p95": float(np.percentile(d, 95)),
            "min": float(np.min(d)),
            "max": float(np.max(d)),
        },
        "left_all_only_candidate_event_count": all_only_events,
        "left_queries_using_any_all_only_candidate_count": int(all_only_queries),
        "shared_candidate_query_usage_counts": shared_usage,
        "sequence_change_examples": examples,
    }


def build_outputs(run_root: Path, output_dir: Path) -> None:
    manifest, arms = load_run(run_root)
    audit = json.loads((run_root / "catalog-audit.json").read_text(encoding="utf-8"))
    if audit.get("status") != "PASS":
        raise ValueError("catalog audit not PASS")
    arm_audits = {row["configuration_id"]: row for row in audit["arms"]}
    all01_ids = set(arm_audits[runner.ALL01]["catalog_oid_order_candidate_ids"])
    all02_ids = set(arm_audits[runner.ALL02]["catalog_oid_order_candidate_ids"])
    b5_ids = set(arm_audits[runner.B5]["catalog_oid_order_candidate_ids"])
    if all01_ids != all02_ids or len(all01_ids) != 55 or len(b5_ids) != 5 or not b5_ids <= all01_ids:
        raise ValueError("physical candidate universe/arm sizes do not match protocol")
    all_only_ids = all01_ids - b5_ids
    summaries = {config_id: metrics(rows) for config_id, rows in arms.items()}
    # Confirm the runner's primary Q-error implementation and the offline metrics agree.
    for config_id, rows in arms.items():
        official = runner.metrics_for_rows(rows)
        local = summaries[config_id]
        for key, metric_key in (("p50", "p50"), ("p95", "p95"), ("p99", "p99"), ("mean", "mean")):
            if local[key] != official["qerror"][metric_key]:
                raise ValueError(f"{config_id}: summary differs from Issue #101/#105 metric helper")
    h1 = paired(arms[runner.ALL02], arms[runner.ALL01], runner.ALL02, runner.ALL01)
    h2 = paired(arms[runner.ALL01], arms[runner.B5], runner.ALL01, runner.B5,
                all_only_ids=all_only_ids, shared_ids=b5_ids)
    h1["p95_delta_random02_minus_random01"] = summaries[runner.ALL02]["p95"] - summaries[runner.ALL01]["p95"]
    h1["p99_delta_random02_minus_random01"] = summaries[runner.ALL02]["p99"] - summaries[runner.ALL01]["p99"]
    h1["mean_delta_random02_minus_random01"] = summaries[runner.ALL02]["mean"] - summaries[runner.ALL01]["mean"]
    h2["p95_delta_all01_minus_b5"] = summaries[runner.ALL01]["p95"] - summaries[runner.B5]["p95"]
    h2["p99_delta_all01_minus_b5"] = summaries[runner.ALL01]["p99"] - summaries[runner.B5]["p99"]
    h2["mean_delta_all01_minus_b5"] = summaries[runner.ALL01]["mean"] - summaries[runner.B5]["mean"]
    near = {}
    for config_id, rows in arms.items():
        vals = np.asarray([row["qerror"] for row in rows], dtype=np.float64)
        threshold = summaries[config_id]["p95"]
        near[config_id] = {
            "p95_value": threshold,
            "count_at_or_above_p95": int(np.sum(vals >= threshold)),
            "query_ids_at_or_above_p95": [row["query_id"] for row in rows if row["qerror"] >= threshold],
        }
    protocol = json.loads(runner.PROTOCOL_PATH.read_text(encoding="utf-8"))
    summary = {
        "status": "COMPLETE",
        "run_id": manifest["run_id"],
        "source_commit": manifest["source_commit_before_test"],
        "protocol_sha256": manifest["protocol_sha256"],
        "raw_archive": manifest["raw_archive"],
        "configuration_count": 3,
        "expected_explain_calls": 30_000,
        "actual_explain_calls": manifest["actual_explain_calls"],
        "metrics_by_configuration": summaries,
        "H1_order_effect_all_random02_minus_random01": h1,
        "H2_set_effect_all_random01_minus_matched_b5": h2,
        "p95_tail_queries": near,
        "physical_state_comparisons": audit["pretest_state_comparisons"],
        "resource_usage": manifest["resource_usage"],
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_path = output_dir / "comparison-summary.json"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                            encoding="utf-8")

    compact_audit = {
        "status": audit["status"],
        "pretest_state_comparisons": audit["pretest_state_comparisons"],
        "arms": [],
    }
    for config_id in (runner.ALL01, runner.ALL02, runner.B5):
        arm = arm_audits[config_id]
        compact_audit["arms"].append({
            "configuration_id": config_id,
            "create_statement_candidate_ids": arm["create_statement_candidate_ids"],
            "catalog_oid_order_candidate_ids": arm["catalog_oid_order_candidate_ids"],
            "catalog_oid_order": arm["catalog_oid_order"],
            "table_identity": arm["table_identity"],
            "ordinary_column_stats_sha256": arm["ordinary_column_stats_sha256"],
            "sample_sha256": arm["sample_sha256"],
            "sample_header": arm["sample_header"],
            "payload_state_counts": arm["payload_state_counts"],
            "catalog_status": arm["catalog_status"],
            "plan_rows_integrity": arm["plan_rows_integrity"],
            "diagnostics_integrity": arm["diagnostics_integrity"],
            "candidate_id_attribution": arm["candidate_id_attribution"],
            "test_status": arm["test_status"],
            "catalog": [{key: row[key] for key in (
                "candidate_id", "statistic_name", "oid", "stxkind", "stxkeys", "attnames",
                "kinds", "statistics_target", "mcv_payload_present", "mcv_item_count",
                "mcv_content_sha256", "payload_state"
            )} for row in arm["catalog"]],
        })
    (output_dir / "catalog-audit.json").write_text(
        json.dumps(compact_audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    h2_p95 = summaries[runner.ALL01]["p95"] - summaries[runner.B5]["p95"]
    h1_p95 = summaries[runner.ALL02]["p95"] - summaries[runner.ALL01]["p95"]
    report = f"""# DMV11 ALL MCV vs matched Nominal B5: findings

Status: **COMPLETE**. This is a fixed-workload physical comparison of three prespecified configurations, not an estimate over all OID permutations.

## Integrity and execution

- Run ID: `{manifest['run_id']}`; source commit: `{manifest['source_commit_before_test']}`.
- Raw query archive SHA-256: `{manifest['raw_archive']['sha256']}`; bytes: {manifest['raw_archive']['bytes']:,}.
- Configurations: {summary['configuration_count']}; EXPLAIN calls: {manifest['actual_explain_calls']:,} / 30,000.
- All configurations have 10,000 valid Plan Rows, complete diagnostics, and complete candidate-ID attribution. Catalog, OID order, table, fixed sample, ordinary stats, and shared-object MCV state checks passed.
- B5 objects in random-01 projected order: `{', '.join(arm_audits[runner.B5]['catalog_oid_order_candidate_ids'])}`. The random-02 projection is `{', '.join(protocol['random02_b5_projection'])}`; it {'matches' if protocol['random02_b5_projection'] == arm_audits[runner.B5]['catalog_oid_order_candidate_ids'] else 'differs from'} the matched B5 order.

## Per-configuration Q-error

| Configuration | n | P50 | P95 | P99 | Mean |
|---|---:|---:|---:|---:|---:|
"""
    for config_id in (runner.ALL01, runner.ALL02, runner.B5):
        m = summaries[config_id]
        report += f"| `{config_id}` | {m['query_count']:,} | {m['p50']:.9g} | {m['p95']:.9g} | {m['p99']:.9g} | {m['mean']:.9g} |\n"
    report += f"""
## H1 — same 55-object set, two OID orders

`P95(random-02) - P95(random-01) = {h1_p95:.9g}`; P99 difference = {h1['p99_delta_random02_minus_random01']:.9g}; mean difference = {h1['mean_delta_random02_minus_random01']:.9g}. Plan Rows changed for {h1['plan_rows_changed_count']:,} queries, Q-error changed for {h1['qerror_changed_count']:,}, selection sequence changed for {h1['mcv_selection_sequence_changed_count']:,}; {h1['plan_rows_changed_qerror_unchanged_count']:,} had different Plan Rows but unchanged Q-error. Paired mean Q-error difference (random-02 minus random-01) was {h1['paired_qerror_delta_left_minus_right']['mean']:.9g}.

## H2 — ALL random-01 vs matched B5

`P95(ALL random-01) - P95(B5) = {h2_p95:.9g}`; P99 difference = {h2['p99_delta_all01_minus_b5']:.9g}; mean difference = {h2['mean_delta_all01_minus_b5']:.9g}. ALL was worse on {h2['left_qerror_worse_count']:,} paired queries, better on {h2['left_qerror_better_count']:,}, and equal on {h2['qerror_equal_count']:,}. Plan Rows changed for {h2['plan_rows_changed_count']:,}; selection sequence changed for {h2['mcv_selection_sequence_changed_count']:,}. ALL-only candidates were selected in {h2['left_queries_using_any_all_only_candidate_count']:,} queries ({h2['left_all_only_candidate_event_count']:,} selection events).

The sign of this fixed P95 contrast is {'consistent with ALL being worse than B5' if h2_p95 > 0 else 'consistent with ALL being better than B5' if h2_p95 < 0 else 'zero at P95'} under the matched shared-object order and audited states. It does not isolate every mechanism contributing to the set effect.

## Interpretation limits

- Random-02's B5 projection {'matches' if protocol['random02_b5_projection'] == arm_audits[runner.B5]['catalog_oid_order_candidate_ids'] else 'does not match'} the primary B5 order; interpret its ALL-vs-B5 contrast accordingly.
- Different selection sequences are descriptive evidence. This run does not record candidate ranking, predicate consumption, or blocker eligibility, so it does not prove that a worse object suppressed a better one.
- These are three fixed arms and one 10,000-query workload; no inference is made about all 55! orders or other datasets.
- Runtime: {manifest['resource_usage']['elapsed_wall_seconds']:.1f}s wall; peak run-directory allocation {manifest['resource_usage']['peak_run_directory_allocated_bytes'] / (1024**3):.3f} GiB; runner CPU {manifest['resource_usage']['runner_process_cpu_seconds']:.1f}s (PostgreSQL backend CPU is not separately attributed).

Query-level observations remain in the external runtime archive; the repository contains only compact summaries and the catalog audit.
"""
    (output_dir / "findings.md").write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run_root", type=Path)
    parser.add_argument("--output-dir", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    build_outputs(args.run_root, args.output_dir)
    print(f"analysis complete: {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
