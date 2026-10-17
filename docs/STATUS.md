# ESS Research — current status

**Snapshot date:** 2026-10-17 (Asia/Taipei)  
**Owner of research decisions:** human researcher  
**Scope of this file:** actionable state at the snapshot date, not a continuously updated GitHub dashboard. **Recheck PR/Issue state when resuming.**

For long-lived premises, see [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md); for justifications, [DECISIONS.md](DECISIONS.md). This file is the *handoff checkpoint* for new ChatGPT/Codex sessions.

## 1. Executive checkpoint

**Chosen paper direction:** a general, estimator-agnostic pessimistic admissibility-aware resource-selection framework; a pairwise labeled maximal-matching instantiation; exact/structured algorithms; PostgreSQL model/estimation/cost validation.

**Immediate milestone:** establish the scoped PostgreSQL 16.14 MCV-selector \(\to\) maximal-matching correspondence both as a source-grounded theorem and with actual instrumented runtime traces. This **has not yet been executed on a built PG server** in the reviewed work.

**Workflow:** GitHub is the durable research collaboration center; researcher uses VS Code + Codex for local code execution, ChatGPT for design and review. The local clone is not synchronized by creating GitHub commits: explicitly fetch/checkout branches or pull **after** review/merge.

## 2. Open work and evidence

| Work / claim | State | Evidence and next action |
|---|---|---|
| Generic \(\min_M\sum_iw_i\max_{\sigma\in\Gamma_i(M)}\ell_i(\sigma)\) framework | **Defined** | `paper/main.tex`; no generic efficiency claim for arbitrary black-box interfaces. |
| Non-nested admissibility and conditional maximal-matching constraints | **Model-internal analysis** | `notes/structural-foundations.md`, `notes/conditional-adversarial-constraints.md`, `notes/master-oracle-algorithm-design.md`. Proof details must be reviewed before paper claims. |
| Restricted PG 16.14 greedy MCV selection \(\Rightarrow\) a maximal matching | **Source-derived, runtime pending** | [ess-research Draft PR #1](https://github.com/1951123/ess-research/pull/1); exact hypotheses specified in the proposed note. |
| All maximal matchings obtainable under freely permuted *abstract* candidate priority order | **Model-internal proposition, runtime scope limited** | Same PR #1; must **not** be restated as a guarantee about a fixed PG catalog or consistent cross-task global order. |
| DEBUG1 tracing of selected MCV OIDs and claimed clause indices | **Proposed code, not built** | [ess-postgresql Draft PR #1](https://github.com/1951123/ess-postgresql/pull/1); instrumentation is on a separate development branch, not `main`. |
| Two-order path-graph SQL fixture | **Proposed, not executed** | In ess-research Draft PR #1: `experiments/pg-tracing/trace_pairwise_mcv.sql`; predicted matchings \(\{ab,cd\}\) and \(\{bc\}\). |
| Synthetic Advisor objective correctness | **Experimentally observed on recorded small instances** | `experiments/synthetic/cache-ablation-report.md` and checked-in results: exact Fraction exhaustive reference for `medium_dense` objective \(25\). Re-run is pending for new environments. |
| Master–Oracle scalability superiority | **Not established** | Recorded `medium_dense` medians: static full conditional MILP about \(0.0575\,s\), combined cache+precompute Master–Oracle about \(0.6704\,s\). |
| Positive, separable pre-clamp pairwise MCV correction factors | **Restricted source-derived argument; calibration pending** | Source in `extended_stats.c`, `mcv.c`, `clausesel.c`; scope, positivity, effect of clamping and rounding require testing. |
| Additive maintenance cost proxy vs actual ANALYZE cost | **Model assumption; real validation pending** | Sample size can depend on the maximum extended-statistics target; measure actual refresh costs rather than asserting additivity. |
| Decision quality under admissibility-rule misspecification | **Open research direction** | Compare worst loss / regret across plausible policies, nominal choices and pessimistic choices; avoid real-policy coverage claims without evidence. |

## 3. Draft PRs to review before doing PG experiments

1. [ess-research #1](https://github.com/1951123/ess-research/pull/1) — restricted theorem note and `trace_pairwise_mcv.sql`; remains separate from main.
2. [ess-postgresql #1](https://github.com/1951123/ess-postgresql/pull/1) — DEBUG1 instrumentation; remains separate from main.
3. [ess-research Draft PR #2](https://github.com/1951123/ess-research/pull/2) — context, decision log, status, Codex instructions, README entry. This is the **workflow-bootstrap PR**.

**Do not treat any Draft PR as merged or successfully compiled.** If a new session finds a changed state, update this table and link the evidence.

## 4. Next executable task: PG tracing

**Target:** PostgreSQL 16.14 development build of `ess-postgresql` tracing branch + matching SQL fixture from `ess-research` PR #1.

**Suggested sequence:**

1. In the local clones, `git fetch origin` and inspect the relevant remote research branches; do not overwrite uncommitted local work.
2. Review/build the instrumented PG branch and install/start a **disposable, isolated** development instance (never run the drop/create fixture against production).
3. Run the SQL fixture in `psql` with `client_min_messages=debug1`. Retain PG `--version`, Git commit IDs, database/settings, full `psql` output and `ESS_MCV_TRACE` messages.
4. For each run, map OIDs back to `pg_statistic_ext.stxname`; verify built MCV data, selected statistics, consumed clause indices and termination.
5. Independently verify that output sets are matching/maximal and compare with the two predicted outcomes. Record assumptions/counterexamples.
6. Add a dated, reproducible evidence report (commands, environment, raw log references, assertion outcomes, limitations) in `ess-research`. Report failures rather than force a pass.

**Acceptance criteria:** Actual trace demonstrates or falsifies scoped proposition on specified fixtures, raw evidence is kept, version and assumptions are documented. `EXPLAIN` Plan Rows by itself does not meet acceptance criteria.

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
