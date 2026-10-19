# ESS Research — current status

**Snapshot date:** 2026-10-19 (Asia/Shanghai)
**Owner of research decisions:** human researcher  
**Scope of this file:** actionable state at the snapshot date, not a continuously updated GitHub dashboard. **Recheck PR/Issue state when resuming.**

For long-lived premises, see [RESEARCH_CONTEXT.md](RESEARCH_CONTEXT.md); for justifications, [DECISIONS.md](DECISIONS.md). This file is the *handoff checkpoint* for new ChatGPT/Codex sessions.

## 1. Executive checkpoint

**Chosen paper direction:** a general, estimator-agnostic pessimistic admissibility-aware resource-selection framework; a pairwise labeled maximal-matching instantiation; exact/structured algorithms; PostgreSQL model/estimation/cost validation.

**Completed milestones:** the scoped PostgreSQL 16.14 MCV-selector \(\to\) maximal-matching correspondence is source-grounded and experimentally observed on the controlled path fixture (ess-research PR #4); the fixed-snapshot two-column MCV numeric validation is merged into `main` (ess-research PR #6, paired ess-postgresql PR #2); Issue #7 / PR #8 is merged as a scoped whole-`ANALYZE` wall-time study; and Issue #9 / PR #10 is merged as a separate fixed-target backend-CPU study. These are **fixture-scoped observations**, not universal PG behavior or real cardinality accuracy. **Recent milestones:** theory PR #12 (restricted NP-completeness), theory PR #13 (exact signed inner oracle for selected paths/cycles/stars), and Forest10 ETL PR #16 have all merged into `main` on 2026-10-18. Issue #17 / PR #18 has a verified, versioned derived canonical workload from the two researcher-authorized pinned pickles, strict valid/test ETL builds, and a read-only pairwise scope screen. **Issue #19 local validation is complete:** Census13, DMV11 and Power7 source hashes/schema/row checks passed; current-script replay reproduced all three derived canonical streams; train/valid/test ETL builds passed for each dataset; and pairwise source-shape diagnostics were recorded in [Draft PR #21](https://github.com/1951123/ess-research/pull/21). The historical canonical byte streams remain unavailable and their SHAs are retained only as references. Issue #23 now has verified real Forest10 acquisition/ETL, fixed-sample PostgreSQL calibration, a bounded multi-statistic composition check, and a measured-input exact model comparison documented in [real-stage-report.md](../experiments/forest10-decision/real-stage-report.md). The zero-truth task is retained with the prescribed `T=max(1,N)` floor; the result remains author-reported/local, not a universal PostgreSQL claim or a physical maintenance-cost result.

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
| Additive maintenance cost proxy vs actual ANALYZE cost ([Issue #7](https://github.com/1951123/ess-research/issues/7)) | **Merged scoped wall-time evidence** | Historical v1–v4 raw evidence is retained. Corrected v5: `experiments/pg-maintenance/runs/20261017-issue7-v5-target300-20rep/report.md`, two regimes × eight subsets × five target modes, 1,600 timed refreshes, 20 randomized blocks, exact pair/Cramér's-V diagnostics, target/payload/OID validation, block-bootstrap D(M) intervals, and verified disposable-database cleanup. This remains whole-`ANALYZE` wall-time evidence, not a CPU law or universal PostgreSQL result. |
| Fixed-target extstats phase CPU additivity ([Issue #9](https://github.com/1951123/ess-research/issues/9)) | **Measured and merged in [PR #10](https://github.com/1951123/ess-research/pull/10)** | `experiments/pg-maintenance/fixed-target-cpu/runs/20261018-issue9-v1/` retains 640 backend CPU observations: two regimes × two uniform targets × eight subsets × 20 randomized blocks. The primary trace covers `BuildRelationExtStatistics()` including object build, serialization and catalog persistence. Independent singleton-median predictions are within a descriptive 10% relative error for 15/16 comparisons; six of 16 block-bootstrap D intervals exclude zero. This is scoped validation evidence, not an exact additive law or a paper conclusion. |
| Legacy AreCEL Forest10 ETL boundary ([Issue #15](https://github.com/1951123/ess-research/issues/15)) | **Completed offline in merged [PR #16](https://github.com/1951123/ess-research/pull/16); optional full-data verification BLOCKED / NOT RUN** | `src/ess_research/arecel/forest10.py` implements an explicit-root, hash-checked Forest10 source contract, strict SQL adaptation, canonical JSONL-to-workload/truth artifacts, and fail-closed missing-input behavior. The asset inventory and validation report are in `docs/arecel-asset-inventory.md`, `docs/arecel-forest10-etl.md`, and `experiments/arecel/forest10-validation.md`. No historical repository, hidden data root, pickle deserialization, network acquisition, or database was used. |
| Real Forest10 acquisition and end-to-end ETL ([Issue #17](https://github.com/1951123/ess-research/issues/17)) | **Derived canonical and split ETL verified; historical canonical unavailable; PR #18 review follow-up complete** | `experiments/arecel/issue17-real-data-validation.md` and `issue17-acquisition-manifest.json` record the exact archive/CSV/pickle hashes, the one-time gated conversion, derived canonical SHA `a38646ea…e15ea3`, 20,000 checked records, successful valid/test builds, the committed-script replay (byte-identical output and split artifacts), converter-boundary negative tests, and the read-only syntactic pairwise screen (18,011/20,000). The result is not byte-identical to the historical canonical SHA and is not PostgreSQL runtime evidence. |
| Real Census13/DMV11/Power7 acquisition and end-to-end ETL ([Issue #19](https://github.com/1951123/ess-research/issues/19)) | **Experimentally observed locally; Draft PR pending; historical canonical streams unavailable** | `src/ess_research/arecel/real.py`, `experiments/arecel/convert_verified_pickles.py`, `docs/arecel-real-etl.md`, and `experiments/arecel/issue19-real-data-validation.md` record archive re-verification, exact source hashes/schema/row/null checks, one-time gated conversion, current-script byte replay, all observed `train/valid/test` builds, separate truth artifacts, and read-only pairwise screens. Derived canonical SHA: Census13 `fc31f94d…e83788035`, DMV11 `f4e6f57…f449850632`, Power7 `332f645…b2df64c`; latest review follow-up reconciles Census13's 5 numeric/8 string partition and adds pinned-renderer SQL regression coverage; no PostgreSQL runtime evidence. |
| Restricted outer-selection hardness | **Model-internal theorem in merged [PR #12](https://github.com/1951123/ess-research/pull/12)** | Zero-loss decision NP-complete even for two-edge star tasks and fixed rational corrections; no complexity membership claim for the unrestricted full problem. |
| Exact signed inner maximal-matching oracle on paths, cycles and stars | **Model-internal algorithm and offline tests in merged [PR #13](https://github.com/1951123/ess-research/pull/13)** | Linear arithmetic/graph operation bound for fixed selected task graphs of the specified types; not a general graph result, new classical algorithm claim, or PG runtime speedup. |
| Decision quality under admissibility-rule misspecification ([Issue #14](https://github.com/1951123/ess-research/issues/14)) | **Model-level evidence merged in [PR #20](https://github.com/1951123/ess-research/pull/20); issue remains open for follow-up** | `experiments/decision-value/` runs an exact Fraction, standard-library-only comparison of pessimistic, nominal, greedy and empty decisions on five fixed hand cases × 14 budget rows. All 6/120/720 shared global orders are enumerated exactly per fixture; 5,058 per-order records are retained in deterministic compressed JSONL with checksums, while optimizer runtimes are isolated. In 3/14 budget rows PESS and nominal sets differ; the mixed-sign stress case has nominal price `4` at budgets `2` and `4`, while PESS has lower max-tested shared-order loss (`43/2` vs `25`). Eleven rows coincide, PESS selects empty in 9/14, and all optimizer-selected independent-vs-joint gaps are exactly zero. A separate three-edge conflict probe has independent bound `5`, max shared-order loss `4`, and gap `1`, showing the general tightness question is nontrivial. This is **experimentally observed model-level evidence**, not PostgreSQL or physical-cost evidence. |
| Issue #23 Forest10 PESS/Nominal/Joint-Robust comparison | **Real source/ETL, fixed-sample PG measurement, bounded composition check, and exact measured-input model comparison complete; review follow-up in progress** | `experiments/forest10-decision/real-stage-report.md` records the exact archive/CSV/pickle/canonical/audit hashes, valid/test query IDs and truths, fixed sample SHA, 84 PG calibration records, three multi-statistic composition cases, and the external measured-input artifacts. The existing exact runner enumerated 720 shared orders and the independent reference verified all 12 objective certificates with `T=max(1,N)`. The six valid tasks are a narrow construction sample, not a representative or test-split robustness study; the PG/calibration findings are author-reported local observations. |

## 3. PR and branch status

### Issue #30 Stage 0A (current research/issue30 branch)

The standalone exact reference and frozen pilot are implemented under
`experiments/pess-bound-stage0a/`. The committed manifest fixes four
deterministic strata, seeds 3019–3022, 4–8 resources, 1–4 tasks, a 300-node
per-instance cap, exact `Fraction` arithmetic, and a 120-second wall cap before
comparison results. The 2026-10-19 run evaluated 1,708 feasible branch states
across eight tiny instances, explicitly rejected 200 infeasible forced states,
checked all feasible completions pointwise, and recorded zero counterexamples.
The evidence bundle is hash-verified in
`experiments/pess-bound-stage0a/runs/20261019-issue30-v1/`; the report records
the exact formalized lemma, A/B/C results, witness costs, and D as not executed
because the issue forbids modifying `ess-advisor` or building a new solver.
This is **experimentally observed bounded evidence**, not a theorem novelty or
end-to-end speed claim. The current recommendation is **INCONCLUSIVE**.

Review follow-up in the same Draft PR: the original v1 raw blob was restored
byte-for-byte after a large-file API publication mismatch, with the cause and
non-rerun preservation documented in the v1 report. A predeclared balanced v2
manifest/run adds separate bitmask completion checks, balanced first-resource
status/depth strata, complete B/C timing, and pruned-nodes-per-second metrics.
The v2 run passed with 1,552 feasible nodes, 356 rejected forced-infeasible
states, and zero counterexamples. This remains bounded tightness/cost evidence,
not an end-to-end speed result; comparator D remains out of scope.

1. [ess-research #1](https://github.com/1951123/ess-research/pull/1) — restricted theorem note and `trace_pairwise_mcv.sql`; **merged**.
2. [ess-postgresql #1](https://github.com/1951123/ess-postgresql/pull/1) — DEBUG1 instrumentation; **merged 2026-10-17** into `ess-postgresql/main`, after the controlled branch build/trace.
3. [ess-research #2](https://github.com/1951123/ess-research/pull/2) — context, decision log, status, Codex instructions, README entry; **merged**.
4. [ess-research #4](https://github.com/1951123/ess-research/pull/4) — runtime trace evidence and report; **merged 2026-10-17** into `ess-research/main`.
5. [ess-research #3](https://github.com/1951123/ess-research/pull/3) — correct Git local/remote synchronization description in `AGENTS.md`; **merged 2026-10-17**.
6. [ess-postgresql #2](https://github.com/1951123/ess-postgresql/pull/2) — opt-in pre-clamp MCV numeric tracing for Issue #5; **merged 2026-10-17** into `ess-postgresql/main`.
7. [ess-research #6](https://github.com/1951123/ess-research/pull/6) — fixed-snapshot SQL, offline reconstruction, updated strict checker, negative tests and raw evidence; **merged 2026-10-17** into `ess-research/main`.
8. [ess-research Issue #5](https://github.com/1951123/ess-research/issues/5) — numeric validation task; **closed 2026-10-17 (completed)**.
9. [ess-research Issue #7](https://github.com/1951123/ess-research/issues/7) — physical PG maintenance cost / additive proxy measurement; **completed in merged PR #8, with scoped wall-time limitations**.
10. [ess-research #8](https://github.com/1951123/ess-research/pull/8) — Issue #7 maintenance-cost matrix and additive-proxy analysis; **merged**.
11. [ess-research Issue #9](https://github.com/1951123/ess-research/issues/9) — fixed-target backend CPU additivity; **640-cell run complete and merged in [PR #10](https://github.com/1951123/ess-research/pull/10)**.
12. [ess-research PR #12](https://github.com/1951123/ess-research/pull/12) — restricted star-task outer-selection NP-completeness theorem and sanity checks; **merged 2026-10-18**.
13. [ess-research PR #13](https://github.com/1951123/ess-research/pull/13) — exact signed inner oracle for selected paths, cycles and stars; **merged 2026-10-18**.
14. [ess-research PR #16](https://github.com/1951123/ess-research/pull/16) — bounded Forest10 offline ETL and CI; **merged 2026-10-18**. [Issue #15](https://github.com/1951123/ess-research/issues/15) acceptance allows explicit missing-input blocker; optional full-data check remains **BLOCKED / NOT RUN**.
15. [ess-research PR #18](https://github.com/1951123/ess-research/pull/18) — Issue #17 real Forest10 acquisition and ETL validation; **Draft, derived canonical and strict split ETL verified, latest review follow-up implemented on the original branch**.
16. [ess-research PR #20](https://github.com/1951123/ess-research/pull/20) — Issue #14 model-level decision value matrix and exact shared-order evaluation; **merged 2026-10-18** into `ess-research/main`.
17. [ess-research PR #21](https://github.com/1951123/ess-research/pull/21) — Issue #19 Census13/DMV11/Power7 real-data ETL; **Draft, local evidence complete, researcher review/merge pending**.
18. [ess-research Issue #14](https://github.com/1951123/ess-research/issues/14) — decision value and price of pessimism; **open**.
19. [ess-research PR #24](https://github.com/1951123/ess-research/pull/24) — Issue #23 model-only exact decision comparison; **merged**.
20. Issue #23 real-stage continuation — verified source/ETL, fixed-sample PG calibration, and measured-input exact comparison are implemented on this branch; **new Draft PR pending creation; do not merge or close Issue #23 from this session**.

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
- **Maintenance ([completed Issue #7](https://github.com/1951123/ess-research/issues/7), [merged PR #8](https://github.com/1951123/ess-research/pull/8)):** historical v4 raw evidence remains immutable, but its `lowcorr` label is treated as functionally dependent/modular. The v5 run adds independent weak-association marginals, target 300, 20 randomized blocks, exact pair association diagnostics, and a D(M)-specific block bootstrap. The result is a scoped wall-time additivity diagnostic; it does not measure CPU/catalog-write components.
- **Issue #9 CPU follow-up / [merged PR #10](https://github.com/1951123/ess-research/pull/10):** `experiments/pg-maintenance/fixed-target-cpu/` uses the same weakassoc/correlated fixtures, equal ordinary/MCV targets 100 and 300, all eight subsets including empty, and 20 randomized blocks (640 timed refreshes). The opt-in `ess.mcv_cpu_trace` phase trace was supplied by [merged PostgreSQL PR #3](https://github.com/1951123/ess-postgresql/pull/3). Requested sample minima are source-derived (30,000/90,000), not realized sample observations. The complete run and cleanup are recorded in `runs/20261018-issue9-v1/`; singleton-median additivity is close in this bounded experiment but not exact or universal.
- **Issue #15 / merged PR #16 Forest10 ETL:** the historical four-dataset inventory records the pinned AreCEL source, archive and dataset artifact identities without importing the legacy code or reading hidden historical paths. The new Forest10 adapter accepts the normalized audit-v1 layout and the pinned historical audit layouts, while requiring an explicit caller-provided data root and rejecting unsafe paths. Its original offline test result (`45 passed`) and fail-closed missing-input boundary remain historical evidence; Issue #17 separately acquired the source outside Git and produced the derived canonical/build evidence documented below.
- **Issue #17 / PR #18 follow-up:** the verified archive did not contain the historical canonical JSONL.gz. The researcher-authorized converter loaded only the two exact pinned pickle files in a network-disabled, resource-limited user service and produced a separately versioned canonical artifact. A replay of the committed converter on the same pinned inputs reproduced the derived bytes and both split outputs byte-for-byte. Converter-boundary tests cover allowlist rejection, hash refusal, alignment/truth validation, and deterministic gzip (`26 passed`; full offline selection `57 passed`). The pinned Query objects contain no raw SQL; the report now distinguishes upstream renderer semantics from the adapted canonical SQL contract. Strict inspection and both 10,000-record builds passed; the derived hash differs from the historical reference and is recorded honestly. The pairwise count is a syntactic source-shape diagnostic only. Raw/derived data remain outside Git.
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
