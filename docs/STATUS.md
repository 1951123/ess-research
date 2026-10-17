# ESS Research — current status

**Snapshot date:** 2026-10-17 (Asia/Taipei)  
**Owner of research decisions:** human researcher  
**Scope of this file:** actionable state at the snapshot date, not a continuously updated GitHub dashboard. **Recheck PR/Issue state when resuming.**

For long-lived premises, see [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md); for justifications, [DECISIONS.md](DECISIONS.md). This file is the *handoff checkpoint* for new ChatGPT/Codex sessions.

## 1. Executive checkpoint

**Chosen paper direction:** a general, estimator-agnostic pessimistic admissibility-aware resource-selection framework; a pairwise labeled maximal-matching instantiation; exact/structured algorithms; PostgreSQL model/estimation/cost validation.

**Completed milestones:** the scoped PostgreSQL 16.14 MCV-selector \(\to\) maximal-matching correspondence is source-grounded and experimentally observed on the controlled path fixture (ess-research PR #4); and the fixed-snapshot two-column MCV numeric validation has been merged into `main` (ess-research PR #6, paired ess-postgresql PR #2). The [numeric Issue #5](https://github.com/1951123/ess-research/issues/5) was closed as completed on 2026-10-17. These are **fixture-scoped observations**, not universal PG behavior or real cardinality accuracy. **Next milestone:** measure physical PostgreSQL `ANALYZE` refresh costs and the error of an additive budget proxy ([Issue #7](https://github.com/1951123/ess-research/issues/7)); experiments have not started.

**Workflow:** GitHub is the durable research collaboration center; researcher uses VS Code + Codex for local code execution, ChatGPT for design and review. The local clone is not synchronized by creating GitHub commits: explicitly fetch/checkout branches or pull **after** review/merge.

## 2. Open work and evidence

| Work / claim | State | Evidence and next action |
|---|---|---|
| Generic \(\min_M\sum_iw_i\max_{\sigma\in\Gamma_i(M)}\ell_i(\sigma)\) framework | **Defined** | `paper/main.tex`; no generic efficiency claim for arbitrary black-box interfaces. |
| Non-nested admissibility and conditional maximal-matching constraints | **Model-internal analysis** | `notes/structural-foundations.md`, `notes/conditional-adversarial-constraints.md`, `notes/master-oracle-algorithm-design.md`. Proof details must be reviewed before paper claims. |
| Restricted PG 16.14 greedy MCV selection \(\Rightarrow\) a maximal matching | **Source-derived and experimentally observed for the scoped fixture** | [Correspondence note](../notes/pg-mcv-maximal-matching-correspondence.md) plus [2026-10-17 runtime report](../experiments/pg-tracing/runs/20261017/report.md). The run observed `{ab,cd}` and `{bc}` in the two creation-order phases under the stated hypotheses. |
| All maximal matchings obtainable under freely permuted *abstract* candidate priority order | **Model-internal proposition; only two physical orders experimentally checked** | [Correspondence note](../notes/pg-mcv-maximal-matching-correspondence.md); must **not** be restated as a guarantee about a fixed PG catalog or consistent cross-task global order. |
| DEBUG1 tracing of selected MCV OIDs and claimed clause indices | **Built, executed on an experimental branch, and merged into ess-postgresql/main** | [ess-postgresql PR #1](https://github.com/1951123/ess-postgresql/pull/1) **merged 2026-10-17**; instrumented source commit `e17bfdf0c871bec02bea8c979b29d7603772b14d`. The runtime test used the branch at that commit; no separate post-merge build is claimed. This is not unmodified upstream PostgreSQL. |
| Two-order path-graph SQL fixture | **Executed successfully in an isolated PostgreSQL 16.14 instance** | `experiments/pg-tracing/trace_pairwise_mcv.sql`; raw outputs and server trace are retained in `experiments/pg-tracing/runs/20261017/`. |
| Synthetic Advisor objective correctness | **Experimentally observed on recorded small instances** | `experiments/synthetic/cache-ablation-report.md` and checked-in results: exact Fraction exhaustive reference for `medium_dense` objective \(25\). Re-run is pending for new environments. |
| Master–Oracle scalability superiority | **Not established** | Recorded `medium_dense` medians: static full conditional MILP about \(0.0575\,s\), combined cache+precompute Master–Oracle about \(0.6704\,s\). |
| Positive, separable pre-clamp pairwise MCV correction factors | **Source-derived for the restricted path, experimentally observed on three controlled fixtures** | [Merged numeric report](../experiments/pg-tracing/runs/20261017-numeric/report.md) (ess-research PR #6); exact independent singleton/pair reconstruction to recorded FP precision under its assumptions. The log form requires positive factors; zeros and clamped Plan Rows remain distinct. |
| Fixed-snapshot positive MCV factor reconstruction ([closed Issue #5](https://github.com/1951123/ess-research/issues/5)) | **Completed and merged; experimentally observed for three controlled fixtures, not universal** | [Merged report](../experiments/pg-tracing/runs/20261017-numeric/report.md) and review follow-up. The original fixture had `mcv_totalsel=1`; the new fixtures observed `0.521333...`/`0.529` and `0.613`, positive non-MCV remainder and correction factors `2.1235`, `7.4513`, `3.9013`. The strict analyzer's previously uncovered assertions were fixed and four negative tests recorded. Tolerances: relative `1e-12`, absolute `1e-15`. The *upper remainder cap activation* was not observed; raw zeros are excluded from log-space. |
| Additive maintenance cost proxy vs actual ANALYZE cost ([Issue #7](https://github.com/1951123/ess-research/issues/7)) | **Experimentally observed on the Issue #7 Draft branch; not merged** | Final v4 evidence: `experiments/pg-maintenance/runs/20261017-issue7-v4/report.md`, 48 conditions (two deterministic regimes × eight subsets × three target modes), 336 timed refreshes, post-warm-up MCV payload validation, and verified disposable-database cleanup. Same-target singleton additivity substantially overpredicted multi-object wall time; mixed-target cases were closer but not exact. This is a scoped wall-time observation, not a CPU-cost law or universal PostgreSQL result. |
| Decision quality under admissibility-rule misspecification | **Open research direction** | Compare worst loss / regret across plausible policies, nominal choices and pessimistic choices; avoid real-policy coverage claims without evidence. |

## 3. PR and branch status

1. [ess-research #1](https://github.com/1951123/ess-research/pull/1) — restricted theorem note and `trace_pairwise_mcv.sql`; **merged**.
2. [ess-postgresql #1](https://github.com/1951123/ess-postgresql/pull/1) — DEBUG1 instrumentation; **merged 2026-10-17** into `ess-postgresql/main`, after the controlled branch build/trace.
3. [ess-research #2](https://github.com/1951123/ess-research/pull/2) — context, decision log, status, Codex instructions, README entry; **merged**.
4. [ess-research #4](https://github.com/1951123/ess-research/pull/4) — runtime trace evidence and report; **merged 2026-10-17** into `ess-research/main`.
5. [ess-research #3](https://github.com/1951123/ess-research/pull/3) — correct Git local/remote synchronization description in `AGENTS.md`; **merged 2026-10-17**.
6. [ess-postgresql #2](https://github.com/1951123/ess-postgresql/pull/2) — opt-in pre-clamp MCV numeric tracing for Issue #5; **merged 2026-10-17** into `ess-postgresql/main`.
7. [ess-research #6](https://github.com/1951123/ess-research/pull/6) — fixed-snapshot SQL, offline reconstruction, updated strict checker, negative tests and raw evidence; **merged 2026-10-17** into `ess-research/main`.
8. [ess-research Issue #5](https://github.com/1951123/ess-research/issues/5) — numeric validation task; **closed 2026-10-17 (completed)**.
9. [ess-research Issue #7](https://github.com/1951123/ess-research/issues/7) — physical PG maintenance cost / additive proxy measurement; **open, execution pending**.

The runtime evidence was originally committed on `experiment/pg-mcv-trace-20261017` and has since been merged into `ess-research/main`. The PostgreSQL instrumentation was likewise merged into `ess-postgresql/main`; local clones are independent and require fetching/integrating these updates. Recheck PR state when resuming.

## 4. Completed PG tracing checkpoint

**Target achieved:** PostgreSQL 16.14 development build of the former
`ess-postgresql` tracing branch (subsequently merged via PG PR #1) plus the SQL fixture from the
merged ess-research correspondence note. The recorded run preceded the PG PR merge.

The isolated run used port `55432`, a private Unix socket, and data directory
under `/tmp/ess-pg-trace-*`. The trace reported:

- Phase A (`ab,bc,cd`): built OIDs `16387,16388,16389`; selected `16387`
  (`ab`) and `16389` (`cd`); consumed clause indices `0,1,2,3`; terminated
  with no candidate.
- Phase B (`bc,ab,cd`): built OIDs `16390,16391,16392`; selected `16390`
  (`bc`); consumed clause indices `1,2`; terminated with no candidate.

**Acceptance criteria:** met for this scoped fixture: the actual `DEBUG1`
trace, not `EXPLAIN` Plan Rows, demonstrated the two predicted maximal
matchings. This remains a fixture-level runtime observation, not a universal
PostgreSQL claim.

## 5. Follow-up research after tracing

- **Estimator calibration ([completed Issue #5](https://github.com/1951123/ess-research/issues/5)):** three controlled snapshots and the strict-checker negative tests are merged via PR #6. Source-derived assumptions and observed pre-clamp products are separately documented; rare raw-zero controls stay outside log space. The upper non-MCV cap activation and broader query/statistics paths remain untested.
- **Estimator calibration review follow-up:** `experiments/pg-tracing/runs/20261017-numeric/review-followup-20261017/` contains two new fixed table snapshots, one `ANALYZE` per table, original stdout/stderr/server/cleanup logs, source/binary provenance, and a strict nonzero-on-failure checker. The partial fixture exercises `other_sel` with `0<mcv_totalsel<1`; the heterogeneous fixture measures three materially different positive correction factors. No PostgreSQL source change was needed beyond PR #2. Universal separability and real-cardinality accuracy remain unclaimed.
- **Maintenance ([Issue #7](https://github.com/1951123/ess-research/issues/7), Draft PR pending):** final v4 run completed the required 8-subset × two uniform-target × one mixed-target matrix for two deterministic tables, with seven timed refreshes per condition. The result is a wall-time additivity diagnostic; realized sample rows and CPU/catalog-write components remain unmeasured.
- **Optimization:** investigate bound-first master separation without invalidating exact objective evaluation; compare static MILP and Master–Oracle against independent references at larger scales.
- **Decision robustness:** explicit priority-order cases and cross-task consistency; benchmark worst-case loss vs nominal strategies and costs of conservatism.

## 6. Session handoff checklist

At the end of a meaningful research milestone, update this document with:

- **What changed?** PR/commit/file references.
- **What was actually executed?** Environment, commands, test data and outcomes.
- **Which statements are Proven / Source-derived / Experimentally observed / Conjecture / Open?**
- **What remains blocked or invalidated?** Include counterexamples.
- **What is the single next actionable task?**

Do not dump full chat transcripts. Summarize conclusions, rationale, evidence and open questions so another ChatGPT session can resume from GitHub alone.
