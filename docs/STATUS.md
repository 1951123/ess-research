# ESS Research — current status

**Snapshot date:** 2026-10-17 (Asia/Taipei)  
**Owner of research decisions:** human researcher  
**Scope of this file:** actionable state at the snapshot date, not a continuously updated GitHub dashboard. **Recheck PR/Issue state when resuming.**

For long-lived premises, see [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md); for justifications, [DECISIONS.md](DECISIONS.md). This file is the *handoff checkpoint* for new ChatGPT/Codex sessions.

## 1. Executive checkpoint

**Chosen paper direction:** a general, estimator-agnostic pessimistic admissibility-aware resource-selection framework; a pairwise labeled maximal-matching instantiation; exact/structured algorithms; PostgreSQL model/estimation/cost validation.

**Immediate milestone:** establish the scoped PostgreSQL 16.14 MCV-selector \(\to\) maximal-matching correspondence both as a source-grounded theorem and with actual instrumented runtime traces. The controlled runtime check is now complete on the dedicated experiment branch; raw evidence is retained under `experiments/pg-tracing/runs/20261017/`.

**Workflow:** GitHub is the durable research collaboration center; researcher uses VS Code + Codex for local code execution, ChatGPT for design and review. The local clone is not synchronized by creating GitHub commits: explicitly fetch/checkout branches or pull **after** review/merge.

## 2. Open work and evidence

| Work / claim | State | Evidence and next action |
|---|---|---|
| Generic \(\min_M\sum_iw_i\max_{\sigma\in\Gamma_i(M)}\ell_i(\sigma)\) framework | **Defined** | `paper/main.tex`; no generic efficiency claim for arbitrary black-box interfaces. |
| Non-nested admissibility and conditional maximal-matching constraints | **Model-internal analysis** | `notes/structural-foundations.md`, `notes/conditional-adversarial-constraints.md`, `notes/master-oracle-algorithm-design.md`. Proof details must be reviewed before paper claims. |
| Restricted PG 16.14 greedy MCV selection \(\Rightarrow\) a maximal matching | **Source-derived and experimentally observed for the scoped fixture** | [Correspondence note](../notes/pg-mcv-maximal-matching-correspondence.md) plus [2026-10-17 runtime report](../experiments/pg-tracing/runs/20261017/report.md). The run observed `{ab,cd}` and `{bc}` in the two creation-order phases under the stated hypotheses. |
| All maximal matchings obtainable under freely permuted *abstract* candidate priority order | **Model-internal proposition, runtime scope limited** | Same PR #1; must **not** be restated as a guarantee about a fixed PG catalog or consistent cross-task global order. |
| DEBUG1 tracing of selected MCV OIDs and claimed clause indices | **Built and experimentally observed on the separate PostgreSQL branch** | [ess-postgresql Draft PR #1](https://github.com/1951123/ess-postgresql/pull/1) remains open and unmerged; source commit `e17bfdf0c871bec02bea8c979b29d7603772b14d`. |
| Two-order path-graph SQL fixture | **Executed successfully in an isolated PostgreSQL 16.14 instance** | `experiments/pg-tracing/trace_pairwise_mcv.sql`; raw outputs and server trace are retained in `experiments/pg-tracing/runs/20261017/`. |
| Synthetic Advisor objective correctness | **Experimentally observed on recorded small instances** | `experiments/synthetic/cache-ablation-report.md` and checked-in results: exact Fraction exhaustive reference for `medium_dense` objective \(25\). Re-run is pending for new environments. |
| Master–Oracle scalability superiority | **Not established** | Recorded `medium_dense` medians: static full conditional MILP about \(0.0575\,s\), combined cache+precompute Master–Oracle about \(0.6704\,s\). |
| Positive, separable pre-clamp pairwise MCV correction factors | **Restricted source-derived argument; calibration pending** | Source in `extended_stats.c`, `mcv.c`, `clausesel.c`; scope, positivity, effect of clamping and rounding require testing. |
| Additive maintenance cost proxy vs actual ANALYZE cost | **Model assumption; real validation pending** | Sample size can depend on the maximum extended-statistics target; measure actual refresh costs rather than asserting additivity. |
| Decision quality under admissibility-rule misspecification | **Open research direction** | Compare worst loss / regret across plausible policies, nominal choices and pessimistic choices; avoid real-policy coverage claims without evidence. |

## 3. PR and branch status

1. [ess-research #1](https://github.com/1951123/ess-research/pull/1) — restricted theorem note and `trace_pairwise_mcv.sql`; **merged**.
2. [ess-postgresql #1](https://github.com/1951123/ess-postgresql/pull/1) — DEBUG1 instrumentation; **open draft, unmerged**. The branch has now been built and executed, but the instrumentation remains separate from `main`.
3. [ess-research #2](https://github.com/1951123/ess-research/pull/2) — context, decision log, status, Codex instructions, README entry; **merged**.
4. [ess-research #4](https://github.com/1951123/ess-research/pull/4) — runtime trace evidence and report; **open draft, unmerged**.

The new runtime evidence is on branch `experiment/pg-mcv-trace-20261017`; no
merge is performed by the experiment runner. Recheck PR state when resuming.

## 4. Completed PG tracing checkpoint

**Target achieved:** PostgreSQL 16.14 development build of the
`ess-postgresql` tracing branch plus the matching SQL fixture from the merged
ess-research correspondence note.

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

- **Estimator calibration:** test positive raw-selectivity factors and log-loss against PG internals and/or controlled estimates, including zero selectivity and output clamping.
- **Maintenance:** vary target, objects, sample size and refresh runs; measure CPU time and possible nonadditivity.
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
