"""Render the bounded Issue #38 summary as a reviewable Markdown report."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def selected(value: list[str]) -> str:
    return "Empty" if not value else "{" + ",".join(value) + "}"


def aliases(value: list[dict[str, object]]) -> str:
    if not value:
        return "—"
    return ", ".join(f"{item['method']}@B{item['budget']}" for item in value)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--summary", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    summary = json.loads(args.summary.read_text(encoding="utf-8"))
    rows = summary["set_summaries"]
    paired = summary["paired_vs_empty"]
    nominal = summary["paired_vs_nominal_e12_e23_e34"]
    model = summary["issue23_model_layer_separate"]["results"]
    pess_nominal = next(
        item for item in nominal if item["selected"] == ["e01", "e34"]
    )
    nominal_empty = next(item for item in paired if item["selected"] == ["e12", "e23", "e34"])
    query_level_pess_nominal = pess_nominal["query_level_paired_delta_vs_nominal"]
    nominal_mean = next(
        row["absolute_log_error"]["mean"]
        for row in rows
        if row["selected"] == ["e12", "e23", "e34"]
    )

    lines: list[str] = []
    lines.extend(
        [
            "# Issue #38 Stage 1A held-out Forest10 evidence",
            "",
            "Snapshot: 2026-10-20 (Asia/Shanghai). This is an author-reported local measurement bundle produced in the dedicated Issue #38 Worktree/runtime.",
            "",
            "## Gate A and protocol",
            "",
            "**Gate A: PASS for this descriptive run.** The approved Forest10 archive/CSV/pickles/canonical/audit hashes matched the frozen Issue #23 records; the pinned PostgreSQL 16.14 source commit was clean; the pre-frozen sample relation identity and physical page count matched; all 1,200 planned measurements had a positive pre-clamp final numeric trace; and all 20 set/repetition catalog snapshots were matched.",
            "",
            f"The held-out cohort contains {summary['cohort']['selected_query_count']} deterministic test queries, {summary['cohort']['measurement_count']} measurements, and {summary['cohort']['repetitions']} repetitions. Selection was frozen before outcome collection using query IDs, source-query hashes, syntax eligibility, and candidate coverage only. The cohort selection SHA is recorded in `protocol.json`; the raw measurements SHA is `{summary['raw_files']['measurements_sha256']}`.",
            "",
            "The primary metric is absolute log error from the positive pre-clamp trace, `|ln(estimate/T)|`, with `T=max(1,N)`. Plan Rows are secondary; latency and physical maintenance cost were not measured. P90 is nearest-rank with ceiling rank. The six tail queries are the largest true `N` values, with query-ID tie ordering. There are three zero-truth query IDs, measured twice per set, and they remain a separate stratum.",
            "",
            "## Actual PostgreSQL held-out results",
            "",
            "The table reports pooled repetition-level metrics (`n=120` per set); these are repeated measurements on the same 60 query IDs, not 120 independent test queries. `MCV payload` is based on catalog inspection, while `trace selected` is based on the instrumented PostgreSQL trace, not EXPLAIN alone.",
            "",
            "| Set | Issue #23 aliases | MCV payloads present | Trace-selected query count | Mean | Median | P90 | Max |",
            "|---|---|---|---:|---:|---:|---:|---:|",
        ]
    )
    for row in rows:
        snapshots = row["catalog_snapshots"]
        payloads = sorted({
            stat["name"].removeprefix("ess_forest10_")
            for snapshot in snapshots
            for stat in snapshot["statistics"]
            if stat["mcv_payload_present"]
        })
        error = row["absolute_log_error"]
        lines.append(
            f"| `{selected(row['selected'])}` | {aliases(row['issue23_aliases'])} | {','.join(payloads) or 'none'} | {row['trace_selected_query_count']} | {error['mean']} | {error['median']} | {error['p90_nearest_rank_ceiling']} | {error['max']} |"
        )
    lines.extend(
        [
            "",
            "Observed effective behavior is narrower than the requested resource sets: `e01`, `e45`, and `e56` had no MCV payload in these fixed-sample snapshots. Adding those objects therefore did not change the measured estimate summaries. The nominal set `{e12,e23,e34}` had three 300-item MCV payloads; the PESS-selected set `{e01,e34}` had only `e34` with a 300-item payload.",
            "",
            "Against Empty, `{e01,e34}` had mean paired delta `-0.0689834357240779695` (54 benefits, 50 ties, 16 harms over 120 paired repetition/query rows); `{e12,e23,e34}` had mean delta `-0.0932064402728823113` (78 benefits, 30 ties, 12 harms). These are descriptive paired differences, not a dominance claim.",
            "",
            f"Against the nominal selected set `{selected(['e12','e23','e34'])}`, the PESS-selected `{selected(['e01','e34'])}` was worse on pooled mean absolute log error by `{pess_nominal['delta_abs_log_error_vs_nominal']['mean']}`; it had {pess_nominal['delta_abs_log_error_vs_nominal']['benefit_negative_delta']} benefits, {pess_nominal['delta_abs_log_error_vs_nominal']['tie_zero_delta']} ties, and {pess_nominal['delta_abs_log_error_vs_nominal']['harm_positive_delta']} harms over the 120 query×repetition pairs. Its largest per-row adverse delta was `{pess_nominal['delta_abs_log_error_vs_nominal']['max']}`. This is a descriptive harmful-overconservatism observation under the frozen construction order, while the nominal set itself improves over Empty by pooled mean `{nominal_empty['delta_abs_log_error_vs_empty']['mean']}`.",
            "",
            f"At the query-ID level, averaging the two paired repetitions first gives `n={query_level_pess_nominal['independent_query_count']}` query IDs: PESS−Nominal mean delta `{query_level_pess_nominal['delta_abs_log_error']['mean']}`, with {query_level_pess_nominal['delta_abs_log_error']['benefit_negative_delta']} benefits, {query_level_pess_nominal['delta_abs_log_error']['tie_zero_delta']} ties, and {query_level_pess_nominal['delta_abs_log_error']['harm_positive_delta']} harms. The within-query two-repetition delta spread has mean `{query_level_pess_nominal['within_query_repeat_delta_spread']['mean']}` and maximum `{query_level_pess_nominal['within_query_repeat_delta_spread']['max']}`. The pooled `+0.0242` difference is small relative to the nominal set's mean absolute loss `{nominal_mean}`; this bounded descriptive result does not support a significance or population-level generalization claim, and the query-level distribution may be driven by a limited group of IDs.",
            "",
            "Repetition instability was reported in the bounded JSON summary for every set. The raw trace also records which statistics were selected per query; no claim is made that the abstract maximal-matching family contains every real PG choice.",
            "",
            "## Issue #23 model layer (separate)",
            "",
            "The following are the original Issue #23 rationalized measured-input model certificates on its six valid selection tasks. They are not test-query PostgreSQL outcomes and were not refit from the held-out cohort.",
            "",
            "| Budget | Method | Selected | Exact model objective | Task-wise PESS bound |",
            "|---:|---|---|---:|---:|",
        ]
    )
    for item in model:
        lines.append(
            f"| {item['budget']} | {item['method']} | `{selected(item['selected'])}` | `{item['exact_objective']}` | `{item['pessimistic_taskwise_bound']}` |"
        )
    lines.extend(
        [
            "",
            "The model layer is exact for its recorded rationalized instance/reference calculation; the PostgreSQL trace layer is floating-point solver/server output observed in this run. The two layers must not be merged into one calibration or guarantee.",
            "",
            "At budget 3, both layers select different resource sets in the same direction of nominal-vs-PESS comparison: the Issue #23 model reports PESS `{e01,e34}` versus nominal `{e12,e23,e34}`, while held-out PG means are 4.9520556 versus 4.9278326. The magnitude is not directly comparable because the model sums six valid-task losses and the held-out table averages 120 test observations; the measured catalog payload gap is a concrete model-vs-real semantic discrepancy.",
            "",
            "## Judgment",
            "",
            "**Recommendation: GO for broader real-decision evaluation, not as evidence that PESS wins.** The frozen held-out cohort produced a reproducible, nontrivial paired difference and a meaningful adverse PESS-versus-nominal case with valid trace fidelity. The sharper follow-up hypothesis is that resource-selection decisions can be dominated by whether requested statistics actually acquire MCV payloads and by PG's realized candidate-selection behavior; this needs a broader, independently audited cohort.",
            "",
            "This recommendation is bounded. The cohort is only 60 deterministic syntax/coverage-selected test queries, not population-level generalization. The instrumented PostgreSQL build is not pristine upstream. The additive one-unit budget is a proxy, not physical maintenance cost. Stage 1C remains the gate for any stronger multi-statistic composition, real-scheme containment, or PESS-guarantee claim. No latency, universal PostgreSQL, or universal PESS-dominance conclusion follows.",
            "",
            "## Provenance and preserved negative result",
            "",
            f"- Protocol SHA: `{summary['protocol_sha256']}`; raw run summary SHA: `{summary['raw_run_summary']['measurements_sha256']}` for measurements, setup SHA `{summary['raw_run_summary']['setups_sha256']}`.",
            "- Raw Forest10 rows, sample, PGDATA, server logs, full traces, and EXPLAIN text remain outside Git under the Issue-owned runtime root.",
            "- Runtime isolation: PGDATA `/home/wqts/ess-runtime/issue38/pgdata-replay`, PGHOST `/home/wqts/ess-runtime/issue38/socket-replay`, port `55639`, database `postgres`; the cluster was shut down after collection.",
            "- An earlier harness attempt is preserved externally: it collected 120 valid Empty rows, then stopped on a catalog-name parser bug before non-empty-set outcomes. It was not combined with the final run.",
            "- Evidence labels: the source/build and trace format are source-derived conditional facts; the 1,200 rows and summaries are experimentally observed; the Issue #23 model certificates are exact/rationalized reference results; no universal or physical-cost claim is asserted.",
        ]
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(args.output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
