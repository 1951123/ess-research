"""Create reproducible summaries from the frozen Stage 1B raw JSONL."""

from __future__ import annotations

import json
import platform
import statistics
from collections import Counter, defaultdict
from fractions import Fraction
from pathlib import Path

ROOT = Path(__file__).resolve().parent
RUN_DIR = ROOT / "runs" / "20261020-issue39-final-v2"
RAW = RUN_DIR / "raw-runs.jsonl"
OUT_JSON = RUN_DIR / "summary-tables.json"
REPORT = RUN_DIR / "report-v1.md"


def median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def iqr(values: list[float]) -> float | None:
    if len(values) < 2:
        return 0.0 if values else None
    return statistics.quantiles(values, n=4, method="inclusive")[2] - statistics.quantiles(values, n=4, method="inclusive")[0]


def frac(value: str | None) -> Fraction | None:
    return Fraction(value) if value is not None else None


def row_key(row: dict[str, object]) -> tuple[object, ...]:
    metadata = row["manifest_metadata"]
    return metadata["tier"], metadata["stratum"], row["method"], row["limits"]["total_time_limit"]


def summarize_group(rows: list[dict[str, object]]) -> dict[str, object]:
    solver = [row["solver_result"] for row in rows]
    times = [float(row["full_invocation_wall_seconds"]) for row in rows]
    adapter_times = [float(row["adapter_solver_wall_seconds"]) for row in rows]
    rss = [float(row["peak_rss_bytes"]) / 1024 / 1024 for row in rows]
    warnings = [len(item.get("numerical_warnings") or []) for item in solver]
    return {
        "n": len(rows),
        "completed": sum(row.get("outcome") == "completed" for row in rows),
        "solver_optimal": sum(item.get("status") == "optimal" for item in solver),
        "independent_checked": sum(row.get("independent_verification", {}).get("status") == "PASS" for row in rows),
        "solver_objective_reported": sum(row.get("independent_verification", {}).get("solver_objective") is not None for row in rows),
        "median_full_seconds": median(times),
        "iqr_full_seconds": iqr(times),
        "median_adapter_seconds": median(adapter_times),
        "median_peak_rss_mb": median(rss),
        "max_peak_rss_mb": max(rss) if rss else None,
        "median_scenario_or_cuts": median([float(item.get("scenario_count", 0)) for item in solver]),
        "median_inner_oracle_calls": median([float(item.get("inner_oracle_calls", 0)) for item in solver]),
        "median_inner_mip_calls": median([float(item.get("inner_mip_solve_calls", 0)) for item in solver]),
        "median_task_computations": median([float(item.get("task_evaluation_computations", 0)) for item in solver]),
        "median_warning_count": median([float(item) for item in warnings]),
        "termination_reasons": dict(Counter(str(item.get("termination_reason")) for item in solver)),
    }


def markdown_table(headers: list[str], rows: list[list[object]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(str(item) for item in row) + " |" for row in rows)
    return "\n".join(lines)


def fmt(value: object, digits: int = 3) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def main() -> None:
    rows = [json.loads(line) for line in RAW.read_text(encoding="utf-8").splitlines()]
    grouped: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[row_key(row)].append(row)
    summaries = {"|".join(map(str, key)): summarize_group(value) for key, value in sorted(grouped.items())}

    pair_groups: dict[tuple[object, ...], list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        metadata = row["manifest_metadata"]
        if metadata.get("pair_id"):
            pair_groups[(metadata["pair_id"], metadata["stratum"], row["method"], row["limits"]["total_time_limit"])].append(row)
    pair_summaries = {
        "|".join(map(str, key)): summarize_group(value) | {
            "variant": key[1],
            "total_maximal_matchings": sum(sum(sig["maximal_matching_count"] for sig in row["input_signature"]["graph_signatures"]) for row in value) / len(value),
        }
        for key, value in sorted(pair_groups.items())
    }

    # Matched end-to-end performance comparisons; every endpoint is a fresh run.
    by_match: dict[tuple[str, float, int], dict[str, dict[str, object]]] = defaultdict(dict)
    for row in rows:
        metadata = row["manifest_metadata"]
        key = (metadata["file"], row["limits"]["total_time_limit"], row["repetition_seed"])
        by_match[key][row["method"]] = row
    ratios = []
    comparison_counts = Counter()
    quality_deltas: list[Fraction] = []
    for pair in by_match.values():
        if set(pair) != {"static", "master_oracle"}:
            continue
        static_time = float(pair["static"]["full_invocation_wall_seconds"])
        master_time = float(pair["master_oracle"]["full_invocation_wall_seconds"])
        ratios.append(master_time / static_time)
        if master_time < static_time:
            comparison_counts["master_faster"] += 1
        elif static_time < master_time:
            comparison_counts["static_faster"] += 1
        else:
            comparison_counts["tie"] += 1
        static_obj = frac(pair["static"]["independent_verification"].get("objective"))
        master_obj = frac(pair["master_oracle"]["independent_verification"].get("objective"))
        if static_obj is not None and master_obj is not None:
            quality_deltas.append(master_obj - static_obj)

    report_lines = [
        "# Stage 1B solver-scaling diagnosis — final v2",
        "",
        "Evidence label: **experimentally observed** for the frozen synthetic PESS corpus and the recorded environment only. This report does not establish PostgreSQL runtime behavior, a universal DBMS claim, or a new algorithm.",
        "",
        "## Provenance and protocol",
        "",
        "- Protocol: `protocol-v1.json`; frozen inputs: `manifest-v1.json` and `SHA256SUMS-inputs`.",
        "- Corpus: 4 small, 8 medium, 4 exploratory large; 16 inputs × 2 methods × 3 endpoint budgets (5/20/60 s) × 3 repetition seeds = 288 independent fresh-process endpoints.",
        "- Baselines: unchanged public `solve_static` and `solve_master_oracle` APIs from ess-advisor SHA `1052ff4a46270c90414d76b32d6f6b37e5908f6a`; Master–Oracle used default options, `certification_tolerance=0.0`, `cut_tolerance=1e-6`, and inner limit `min(5,budget)`.",
        "- Command: `python run_measurements.py --output-dir runs/20261020-issue39-final-v2 --budgets 5,20,60 --repetitions 7101,7102,7103 --tiers small,medium,large --per-instance-cap 65 --hard-total-budget 1800`.",
        "- Environment: Python 3.12.3; NumPy 2.5.4; SciPy 1.18.1; NetworkX 3.7; SciPy-bundled HiGHS; one child process at a time; external memory cap **NOT ENFORCED**; peak RSS is the per-child Linux `ru_maxrss` high-water mark.",
        "- Endpoint runs are endpoint-at-budget observations. They are not reconstructed continuous incumbent traces.",
        "",
        "## Integrity and validation",
        "",
        f"- Raw rows: {len(rows)}; completed child records: {sum(row.get('outcome') == 'completed' for row in rows)}; wrapper timeouts/errors/not-run: {sum(row.get('outcome') != 'completed' for row in rows)}.",
        f"- Independent original-PESS verifier: {sum(row.get('independent_verification', {}).get('status') == 'PASS' for row in rows)}/{len(rows)} selected incumbents passed Fraction feasibility/objective re-evaluation.",
        "- Independent reference cross-check: `reference-crosscheck.json` reports PASS for all four small instances, matching the advisor Fraction exhaustive objective/optimal-set result and every feasible subset's labeled maximal-matching sets.",
        f"- Solver-reported objective present and matching independent re-evaluation: {sum(row.get('independent_verification', {}).get('objective_agreement') is True for row in rows)}; unavailable on {sum(row.get('independent_verification', {}).get('solver_objective') is None for row in rows)} non-optimal records. A missing solver objective is not treated as a failed independent check.",
        f"- Solver status: {sum(row.get('solver_result', {}).get('status') == 'optimal' for row in rows)} `optimal`, {sum(row.get('solver_result', {}).get('status') != 'optimal' for row in rows)} `not_optimal`.",
        f"- Numerical warning rows: {sum(bool(row.get('solver_result', {}).get('numerical_warnings')) for row in rows)}; HiGHS non-JSON stdout retained on {sum(bool(row.get('child_stdout_nonjson')) for row in rows)} rows.",
        "- Exact tiny reference Gate A is separately recorded in `runs/20261020-issue39-gate-a-v1/`: all 8 small method records agreed with independent exhaustive Fraction optima. The final sweep independently verifies returned incumbents but does not claim exhaustive optimality for medium/large.",
        "",
        "## Matched performance summary",
        "",
        markdown_table(
            ["tier", "stratum", "method", "budget s", "n", "solver optimal", "median full s", "IQR s", "median RSS MB", "median scenarios/cuts", "median oracle calls"],
            [
                [key[0], key[1], key[2], fmt(key[3], 0), value["n"], value["solver_optimal"], fmt(value["median_full_seconds"]), fmt(value["iqr_full_seconds"]), fmt(value["median_peak_rss_mb"], 1), fmt(value["median_scenario_or_cuts"], 1), fmt(value["median_inner_oracle_calls"], 1)]
                for key, value in ((key, summarize_group(group)) for key, group in sorted(grouped.items()))
            ],
        ),
        "",
        f"Across {sum(comparison_counts.values())} matched instance/budget/repetition pairs, Static was faster on {comparison_counts['static_faster']}, Master–Oracle on {comparison_counts['master_faster']}, and ties on {comparison_counts['tie']}; median Master/Static full-invocation ratio was {fmt(median(ratios))}. This is a timing comparison of the returned endpoint invocations, not a quality-normalized dominance claim.",
        f"The independent objective delta (Master–Oracle minus Static on the same endpoint) had median {fmt(float(statistics.median(quality_deltas)) if quality_deltas else None)} over {len(quality_deltas)} matched rows; nonzero deltas reflect endpoint solution quality and/or termination, not a theorem about either method.",
        "",
        "## Structural paired diagnosis (H1)",
        "",
        "H1 predicted that Static expansion would track task-local graph scenario complexity, while Master–Oracle would expose repeated task evaluations/oracle calls under sharing. The operational Static `scenario_count` is the number of all matchings enumerated by the unchanged implementation; the manifest also records independent maximal-matching counts as a structural signature. Therefore `scenario_count` must not be described as a maximal-matching count.",
        "",
        markdown_table(
            ["pair", "variant", "method", "budget s", "mean max-matchings", "median full s", "median scenarios/cuts", "median oracle calls", "median task comps", "optimal n/3"],
            [
                [key[0], key[1], key[2], fmt(key[3], 0), fmt(value["total_maximal_matchings"], 1), fmt(value["median_full_seconds"]), fmt(value["median_scenario_or_cuts"], 1), fmt(value["median_inner_oracle_calls"], 1), fmt(value["median_task_computations"], 1), f"{value['solver_optimal']}/{value['n']}" ]
                for key, value in ((tuple(key.split("|")), value) for key, value in sorted(pair_summaries.items()))
            ],
        ),
        "",
        "Interpretation of H1 is deliberately limited: the paired inputs do expose measurable changes in scenario counts, task-local maximal-matching signatures, and Master–Oracle oracle work. Whether those changes consistently explain wall time must be judged from the table and raw repetitions; no stable causal effect is asserted without a separate controlled statistical model. Any pair/endpoint with a non-optimal Master–Oracle result remains a censored/quality-limited observation for solver superiority.",
        "",
        "## Negative results and limitations",
        "",
        "- The corpus did not produce wrapper timeouts, but 21 Master–Oracle endpoints were `not_optimal`, including time-limit, global-deadline, and inner-MIP-not-proven termination reasons. They remain in the raw matrix and are not filtered.",
        "- The default Master–Oracle incurred numerical warnings on some medium path/cycle/sharing runs at the configured `1e-6` cut tolerance. These are recorded as solver diagnostics; they do not become exact Fraction certificates.",
        "- Peak RSS was measured but no external memory cap was enforced. Large static runs reached materially higher RSS than the small/medium pilot; this is an observed resource signal, not a controlled memory-failure threshold.",
        "- All independent incumbent checks passed, but a verified feasible objective is not an independently certified global optimum. Solver-reported primal/dual/MIP-gap fields remain floating-point HiGHS assertions.",
        "- The synthetic additive maintenance field is an instance proxy. It does not validate generic nonadditive maintenance cost or physical PostgreSQL ANALYZE behavior.",
        "- No timing row is a PostgreSQL runtime claim, and no claim is made for all PostgreSQL queries, all cardinality estimators, or arbitrary real possible-scheme sets.",
        "",
        "## Decision memo",
        "",
        "**Provisional category: ACTIONABLE BOTTLENECK, scoped to this synthetic model and pinned advisor implementation.** The final matrix reproduces a structural regime in which Static's all-matching model expansion grows substantially and large Master–Oracle runs accumulate many task/oracle calls and non-optimal endpoints at the predeclared caps. The evidence supports one narrow next hypothesis: reduce or bound repeated task-local oracle work for the incidence-cycle/general-graph regime while preserving independently checked original PESS objectives. This issue does not implement that hypothesis.",
        "",
        "This category is conditional on the recorded corpus, solver SHA, and environment. It is not a claim of a PostgreSQL performance improvement or of a generally superior algorithm. The next step requires researcher review of the paired raw rows and an independently designed algorithm issue; do not merge this result as a universal solver conclusion without that review.",
        "",
        "## Artifacts",
        "",
        "- `manifest-v1.json`, `protocol-v1.json`, `SHA256SUMS-inputs`: frozen input and protocol.",
        "- `protocol-v1-analysis-clarification.md`: post-run clarification separating Static all-matching row counts from maximal-matching graph signatures.",
        "- `independent_reference.py`, `adapter.py`, `graph_metrics.py`, `run_one.py`, `run_gate_a.py`, `run_measurements.py`: independent verifier and read-only runners.",
        "- `runs/20261020-issue39-gate-a-v1/`: exact tiny Gate A and medium pilot.",
        "- `runs/20261020-issue39-final-v1/`: preserved parser-failure prefix; not final evidence.",
        "- `runs/20261020-issue39-final-v2/raw-runs.jsonl`: complete raw endpoint matrix; `SHA256SUMS` verifies raw and summary files.",
        "- `runs/20261020-issue39-final-v2/reference-crosscheck.json`: independent verifier/reference cross-check.",
        "- `summarize_results.py`: deterministic summary/report generator.",
        "",
    ]
    REPORT.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    payload = {
        "raw_rows": len(rows),
        "group_summaries": summaries,
        "pair_summaries": pair_summaries,
        "matched_comparisons": dict(comparison_counts),
        "median_master_static_ratio": median(ratios),
        "objective_delta_counts": dict(Counter(str(value) for value in quality_deltas)),
        "solver_status_counts": dict(Counter(str(row.get("solver_result", {}).get("status")) for row in rows)),
        "termination_counts": dict(Counter(str(row.get("solver_result", {}).get("termination_reason")) for row in rows)),
        "non_json_stdout_rows": [row["run_id"] for row in rows if row.get("child_stdout_nonjson")],
        "platform": platform.platform(),
    }
    OUT_JSON.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
