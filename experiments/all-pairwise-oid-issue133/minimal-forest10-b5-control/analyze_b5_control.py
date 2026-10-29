"""Recompute the matched B5 comparison from frozen ALL and saved B5 observations.

This is read-only with respect to PostgreSQL and raw archives. It repairs only
candidate-ID attribution in memory by matching saved integer stat_oid values to
the catalog audit from the same B5 cluster. It preserves the parser's original
diagnostics_status field and reports that its pre-override extension status was
not retained.
"""
from __future__ import annotations

from collections import Counter
import gzip
import hashlib
import json
import os
from pathlib import Path
import sys
from typing import Any

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import run_b5_control as runner  # noqa: E402

RUN_ID = "20261029Tissue133-forest10-b5-nominal-matched"
ATTEMPT = HERE / "attempts" / RUN_ID


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while block := stream.read(1024 * 1024):
            digest.update(block)
    return digest.hexdigest()


def safe_runtime_path(relative: str) -> Path:
    value = Path(relative)
    if value.is_absolute() or ".." in value.parts:
        raise runner.Inconclusive("runtime artifact pin is not a safe relative path")
    return runner.issue101.configured_root("ESS_RUNTIME_PARENT") / value


def load_and_verify_b5(protocol: dict[str, Any], all_evidence: dict[str, Any]):
    saved_manifest_path = ATTEMPT / "run-manifest.json"
    saved_manifest = json.loads(saved_manifest_path.read_text(encoding="utf-8"))
    if (saved_manifest.get("run_id") != RUN_ID
            or saved_manifest.get("status") != "INCOMPLETE"
            or saved_manifest.get("actual_explain_calls") != 10_000
            or saved_manifest.get("source_commit_before_test") != "537f88073587535018dc84e38456c2608e491b7f"
            or saved_manifest.get("protocol_sha256") != sha256_file(runner.PROTOCOL_PATH)
            or saved_manifest.get("catalog_audit_status") != "PASS"):
        raise runner.Inconclusive("saved B5 attempt identity/status differs from the diagnosed arm")

    archive_record = saved_manifest["raw_query_archive"]
    raw_path = safe_runtime_path(archive_record["path_under_ess_runtime_parent"])
    raw_bytes = raw_path.read_bytes()
    raw_sha = hashlib.sha256(raw_bytes).hexdigest()
    if (raw_sha != archive_record["sha256"] or len(raw_bytes) != archive_record["bytes"]):
        raise runner.Inconclusive("B5 runtime raw archive hash/size mismatch")
    runtime_root = raw_path.parent
    runtime_manifest = json.loads((runtime_root / "run-manifest.json").read_text(encoding="utf-8"))
    if (runtime_manifest.get("run_id") != RUN_ID
            or runtime_manifest.get("raw_query_archive", {}).get("sha256") != raw_sha
            or runtime_manifest.get("status") != "INCOMPLETE"):
        raise runner.Inconclusive("B5 runtime manifest does not identify the preserved attempt")

    catalog_path = ATTEMPT / "catalog-audit.json"
    runtime_catalog_path = runtime_root / "catalog-audit.json"
    if (sha256_file(catalog_path) != sha256_file(runtime_catalog_path)
            or sha256_file(catalog_path) != "56eedc5b22b819a69497ab2f384f0c1d7ab33d7c9a4bdc75f147613740114618"):
        raise runner.Inconclusive("versioned and runtime B5 catalog audit identities differ")
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    if (catalog.get("status") != "PASS"
            or catalog.get("configuration_id") != runner.B5_CONFIG
            or catalog.get("catalog_oid_order_candidate_ids") != list(runner.B5_ORDER)
            or catalog.get("create_statement_candidate_ids") != list(runner.B5_ORDER)
            or catalog.get("issue135_shared_candidate_content_match") is not True
            or catalog.get("issue135_ordinary_stats_match") is not True
            or catalog.get("issue135_sample_match") is not True):
        raise runner.Inconclusive("saved B5 physical-state audit failed its matched-control checks")
    signatures = runner.signature_for_candidate_rows(catalog["catalog"])
    if signatures != all_evidence["b5_reference_metrics"]["selected_mcv_signatures"]:
        raise runner.Inconclusive("B5 MCV payload state/content differs from archived ALL by candidate ID")
    catalog_fingerprint = runner.json_sha256(signatures)
    if catalog_fingerprint != saved_manifest.get("catalog_fingerprint_sha256"):
        raise runner.Inconclusive("B5 candidate-ID catalog fingerprint does not match its run manifest")
    if (catalog["ordinary_column_stats"]["sha256"]
            != all_evidence["b5_reference_metrics"]["ordinary_stats_sha256"]
            or catalog["sample_sha256"] != protocol["inputs_and_environment"]["issue99_fixed_analyze_sample_sha256"]):
        raise runner.Inconclusive("B5 ordinary statistics or fixed sample differs from archived ALL")
    b5_input = saved_manifest.get("input_identity", {})
    all_input = all_evidence["input_identity"]
    if any(b5_input.get(key) != all_input.get(key) for key in (
            "query_ids_sha256", "rendered_test_sql_sha256", "test_truth_canonical_sha256")):
        raise runner.Inconclusive("B5 Test query/SQL/truth hashes differ from archived ALL")

    try:
        rows = [json.loads(line) for line in gzip.decompress(raw_bytes).splitlines()]
    except (OSError, EOFError, json.JSONDecodeError) as exc:
        raise runner.Inconclusive(f"B5 raw archive is unreadable: {exc}") from exc
    if len(rows) != 10_000:
        raise runner.Inconclusive("B5 raw archive does not have exactly 10,000 query rows")
    all_rows = all_evidence["all_rows_by_config"][runner.ALL_CONFIGS[0]]
    if len(all_rows) != 10_000:
        raise runner.Inconclusive("primary ALL reference does not have exactly 10,000 rows")
    for row in rows:
        if (row.get("configuration_id") != runner.B5_CONFIG
                or row.get("order") != "b5-nominal-matched-random01"
                or row.get("dataset") != "forest10"
                or row.get("selected_ids") != list(runner.B5_ORDER)
                or row.get("status") != "VALID"
                or row.get("query_id") != f"arecel:forest10:test:{int(row['source_index']):06d}"):
            raise runner.Inconclusive("B5 raw row identity/configuration is inconsistent")
        error, rounded = runner.issue101.qerror_for_plan_rows(
            row["estimate_plan_rows"], row["true_cardinality"])
        if error != row["qerror"] or rounded != row["estimate_rounded_r1"]:
            raise runner.Inconclusive("B5 raw Q-error or rounded Plan Rows does not recompute")
    if ([(row["query_id"], row["source_index"], row["true_cardinality"]) for row in rows]
            != [(row["query_id"], row["source_index"], row["true_cardinality"]) for row in all_rows]):
        raise runner.Inconclusive("B5 raw Test query/truth identities differ from primary ALL")

    metrics_before_remap = runner.qerror_metrics(rows)
    if (metrics_before_remap.get("valid_count") != 10_000
            or metrics_before_remap != saved_manifest.get("config_metrics")):
        raise runner.Inconclusive("B5 saved Q-error summary does not recompute from raw rows")
    remapped, remap_audit = runner.recover_event_ids_from_catalog(rows, catalog["catalog"])
    if (remap_audit["observed_mcv_event_count"]
            != sum(len(row.get("mcv_events", [])) for row in rows)):
        raise runner.Inconclusive("B5 post-hoc OID attribution did not resolve every saved MCV event")
    if any(row["diagnostics_status"] not in {"complete", "UNKNOWN_SELECTED_STAT_OID"}
           for row in rows):
        raise runner.Inconclusive("B5 raw diagnostics contain an unreviewed status beyond the OID-map issue")
    return saved_manifest, catalog, rows, remapped, metrics_before_remap, remap_audit, raw_sha


def write_outputs(protocol: dict[str, Any], all_evidence: dict[str, Any]) -> dict[str, Any]:
    (saved_manifest, catalog, raw_rows, b5_rows, b5_metrics,
     remap_audit, raw_sha) = load_and_verify_b5(protocol, all_evidence)
    secondary_rows = all_evidence["all_rows_by_config"][runner.ALL_CONFIGS[1]]
    secondary_metrics = all_evidence["all_metrics_recomputed"][runner.ALL_CONFIGS[1]]
    all01_metrics = all_evidence["all_metrics_recomputed"][runner.ALL_CONFIGS[0]]
    paired = runner._paired_comparison(
        all_evidence["all_rows_by_config"][runner.ALL_CONFIGS[0]], b5_rows,
        secondary_rows, all01_metrics, b5_metrics, secondary_metrics,
    )
    original_status_counts = dict(sorted(Counter(
        row["diagnostics_status"] for row in raw_rows).items()))
    expected_delta = (all01_metrics["qerror"]["p95"] - b5_metrics["qerror"]["p95"])
    if (paired["paired_query_count"] != 10_000
            or paired["all_minus_b5_p95"] != expected_delta):
        raise runner.Inconclusive("paired comparison count or P95 difference does not recompute")

    summary = {
        "format": "ess-issue133-forest10-all-vs-nominal-b5-comparison-v1",
        "status": "QERROR_COMPARISON_COMPLETE_WITH_DIAGNOSTIC_STATUS_LIMIT",
        "interpretation_scope": "one fixed Forest10 workload/configuration contrast; no permutation expectation",
        "primary_comparison": "P95(ALL random-01) - P95(B5 matched priority)",
        "source_run_id": RUN_ID,
        "source_run_manifest_status": saved_manifest["status"],
        "source_commit_before_test": saved_manifest["source_commit_before_test"],
        "protocol_sha256": saved_manifest["protocol_sha256"],
        "b5_raw_archive_path_under_ess_runtime_parent": saved_manifest["raw_query_archive"]["path_under_ess_runtime_parent"],
        "b5_raw_archive_sha256": raw_sha,
        "b5_catalog_audit_sha256": sha256_file(ATTEMPT / "catalog-audit.json"),
        "all_raw_archive_sha256": all_evidence["raw_archive_sha256"],
        "actual_test_explain_calls": saved_manifest["actual_explain_calls"],
        "valid_plan_rows": len([row for row in raw_rows if row["status"] == "VALID"]),
        "metrics_by_configuration": {
            runner.ALL_CONFIGS[0]: all01_metrics,
            runner.ALL_CONFIGS[1]: secondary_metrics,
            runner.B5_CONFIG: b5_metrics,
        },
        "paired_comparison": paired,
        "diagnostic_remap": remap_audit,
        "source_diagnostics_status_counts": original_status_counts,
        "resource_usage": saved_manifest["resource_usage"],
        "parallel_explain_clients": saved_manifest["environment"]["concurrent_explain_clients"],
        "diagnostic_status_limit": (
            "The original ESS Diagnostics.Status for 6,648 rows was overwritten by the runner's "
            "UNKNOWN_SELECTED_STAT_OID attribution error. The saved numeric event OIDs were mapped "
            "to the same-arm catalog, but the overwritten extension status is not inferred."
        ),
    }
    runner.base.atomic_json(HERE / "comparison-summary.json", summary)
    runner.base.atomic_json(HERE / "posthoc-diagnostic-remap.json", remap_audit)
    write_findings(summary, saved_manifest, catalog)
    return summary


def write_findings(summary: dict[str, Any], manifest: dict[str, Any], catalog: dict[str, Any]) -> None:
    metrics = summary["metrics_by_configuration"]
    pair = summary["paired_comparison"]
    usage = pair["mcv_usage_by_shared_candidate_id"]
    all_only = pair["all_new_candidate_usage"][runner.ALL_CONFIGS[0]]
    delta = pair["qerror_delta_all_minus_b5_distribution"]
    p95 = pair["p95_neighborhood"]
    lines = [
        "# Forest10 ALL versus matched Nominal B5",
        "",
        f"**Comparison status:** `{summary['status']}`.",
        "",
        "This is a fixed-workload installed-set comparison. It uses the frozen ALL random-01 configuration as the primary comparator and the Issue #99 Nominal B5 set created in random-01's shared-candidate relative order. The five shared candidates' relative priority is matched; the 40 extra ALL candidates can still precede and interact with them. This is not an all-order average and does not prove that a particular object blocked another.",
        "",
        "## Frozen selection and order",
        "",
        f"- B5 candidate IDs: `{', '.join(sorted(runner.B5_IDS))}`.",
        f"- B5 CREATE/OID order: `{', '.join(runner.B5_ORDER)}`.",
        f"- B5 order SHA-256: `{runner.sha256_order(runner.B5_ORDER)}`.",
        f"- ALL random-01 projection: `{', '.join(runner.B5_ORDER)}`; ALL random-02 projection: `{', '.join(manifest['random02_projection'])}` (unmatched secondary comparison).",
        "",
        "## Physical configuration and integrity",
        "",
        f"- PostgreSQL 16.14 source: `{manifest['postgresql_source_commit']}`.",
        f"- B5 CREATE / target / ANALYZE: {catalog['create_count']} / {catalog['target_count']} / {catalog['analyze_count']}.",
        f"- Five-object catalog and actual OID order: `{catalog['status']}`.",
        f"- Fixed sample SHA-256: `{catalog['sample_sha256']}`; ordinary-column stats match both ALL arms.",
        "- All five candidate-ID keyed MCV payload states, counts, and fingerprints match both ALL arms: `True`.",
        "- B5 payload states: " + json.dumps(catalog["candidate_payload_state_counts"], sort_keys=True) + ".",
        f"- Run cost: {summary['resource_usage']['elapsed_wall_seconds']} s wall time; peak run-directory allocation {summary['resource_usage']['peak_run_directory_allocated_bytes']} bytes; minimum free space {summary['resource_usage']['minimum_global_filesystem_free_bytes']} bytes; {summary['parallel_explain_clients']} EXPLAIN clients.",
        "",
        "## Test Q-error",
        "",
        "All three configurations use the same 10,000 official query IDs/truths and Issue #101 zero-aware Q-error/NumPy quantiles. The B5 run produced 10,000 valid Plan Rows and Q-errors.",
        "",
        "| Configuration | P50 | P95 | P99 | Mean |",
        "|---|---:|---:|---:|---:|",
    ]
    for config, label in ((runner.ALL_CONFIGS[0], "ALL random-01 (primary)"),
                          (runner.ALL_CONFIGS[1], "ALL random-02 (unmatched secondary)"),
                          (runner.B5_CONFIG, "Nominal B5 matched to random-01")):
        q = metrics[config]["qerror"]
        lines.append(f"| {label} | {q['p50']} | {q['p95']} | {q['p99']} | {q['mean']} |")
    lines.extend([
        "",
        f"Primary contrast: `P95(ALL random-01) - P95(B5) = {pair['all_minus_b5_p95']}`. Positive means ALL has higher/worse P95 Q-error.",
        "",
        "## Paired query comparison (ALL random-01 minus B5)",
        "",
        f"- Plan Rows differed on {pair['plan_rows_changed_count']}/10,000 queries.",
        f"- ALL Q-error was lower on {pair['qerror_improved_for_all_count']}, higher on {pair['qerror_degraded_for_all_count']}, and unchanged on {pair['qerror_unchanged_count']} queries.",
        f"- Per-query Q-error delta (ALL−B5): n={delta['count']}, mean={delta['mean']}, min={delta['min']}, P05={delta['p05']}, median={delta['p50']}, P95={delta['p95']}, max={delta['max']}.",
        f"- Observed MCV selection/estimate sequences differed on {pair['mcv_selection_sequence_changed_count']}/{pair['mcv_estimate_sequence_changed_count']} queries.",
        f"- P95 rank-window union: {p95['union_query_count']} queries; {p95['plan_rows_changed_in_union']} Plan Rows changes and {p95['qerror_changed_in_union']} Q-error changes.",
        "",
        "### Shared B5 object use (observed events)",
        "",
        "| Candidate ID | ALL random-01: queries selected / estimated | B5: queries selected / estimated |",
        "|---|---:|---:|",
    ])
    for candidate_id in sorted(runner.B5_IDS):
        a = usage[candidate_id][runner.ALL_CONFIGS[0]]
        b = usage[candidate_id][runner.B5_CONFIG]
        lines.append(f"| {candidate_id} | {a['queries_with_mcv_selection']} / {a['queries_with_mcv_estimate']} | {b['queries_with_mcv_selection']} / {b['queries_with_mcv_estimate']} |")
    lines.extend([
        "",
        f"ALL-only candidates appeared in selected MCV events for {all_only['queries_with_any_new_candidate_selected']} queries and in estimation events for {all_only['queries_with_any_new_candidate_estimated']} queries (union {all_only['queries_with_any_new_candidate_selected_or_estimated']}).",
        "",
        "### Largest Q-error changes in the predeclared P95 neighborhood",
        "",
        "| Query ID | ALL Plan Rows / Q-error / selected IDs | B5 Plan Rows / Q-error / selected IDs | Δ Q-error (ALL−B5) |",
        "|---|---|---|---:|",
    ])
    for row in p95["largest_absolute_qerror_differences"]:
        lines.append(
            f"| `{row['query_id']}` | {row['all_random01_plan_rows']} / {row['all_random01_qerror']} / `{', '.join(row['all_random01_mcv_selection_ids'])}` | "
            f"{row['b5_plan_rows']} / {row['b5_qerror']} / `{', '.join(row['b5_mcv_selection_ids'])}` | {row['qerror_delta_all_minus_b5']} |"
        )
    lines.extend([
        "",
        "## Attempt history and diagnostic limitation",
        "",
        f"The single authorized arm completed 10,000 EXPLAINs in run `{RUN_ID}`. The execution runner marked that run `INCOMPLETE` because its in-memory OID map used string keys, while the diagnostic parser looked up integer OIDs. The raw archive SHA-256 is `{summary['b5_raw_archive_sha256']}`. A deterministic offline remap used the saved same-arm catalog audit; it did not change raw data or rerun queries.",
        "",
        "The initial failure and its evidence are preserved in [attempt diagnosis](attempts/20261029Tissue133-forest10-b5-nominal-matched/attempt-diagnosis.md), [initial findings](attempts/20261029Tissue133-forest10-b5-nominal-matched/findings.md), [run manifest](attempts/20261029Tissue133-forest10-b5-nominal-matched/run-manifest.json), and [catalog audit](attempts/20261029Tissue133-forest10-b5-nominal-matched/catalog-audit.json). The original extension diagnostics status for 6,648 rows was overwritten by the parser error and was not separately retained. Candidate IDs are deterministically recovered for all stored numeric OIDs, but the original extension status is not inferred; event-sequence frequencies are therefore counts of retained/observed events.",
        "",
        "## Interpretation and limits",
        "",
        f"For this fixed Forest10 workload, ALL random-01 P95 was higher than matched B5 by {pair['all_minus_b5_p95']}. This supports the scoped claim that installing all 45 candidate definitions produced a higher Test P95 than the frozen five-object Nominal subset under the matched shared-object priority and verified physical states. It does not identify which extra object caused the difference or establish a blocking mechanism. ALL random-02 is descriptive only because its five-object projection differs.",
        "",
        "No confidence interval or significance test is reported for this fixed finite workload. The two ALL arms and B5 arm are fixed configurations, not a sample for estimating performance over all OID orders.",
        "",
    ])
    (HERE / "findings.md").write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    protocol = runner.read_frozen_protocol()
    all_evidence = runner.verify_saved_all(protocol)
    summary = write_outputs(protocol, all_evidence)
    print(json.dumps({
        "status": summary["status"],
        "b5_raw_archive_sha256": summary["b5_raw_archive_sha256"],
        "all_minus_b5_p95": summary["paired_comparison"]["all_minus_b5_p95"],
        "plan_rows_changed_count": summary["paired_comparison"]["plan_rows_changed_count"],
        "qerror_improved_for_all_count": summary["paired_comparison"]["qerror_improved_for_all_count"],
        "qerror_degraded_for_all_count": summary["paired_comparison"]["qerror_degraded_for_all_count"],
        "qerror_unchanged_count": summary["paired_comparison"]["qerror_unchanged_count"],
        "diagnostics_status_counts": summary["source_diagnostics_status_counts"],
    }, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
