# Independent PVLDB review triage — A/B/C/D (2026-10-28)

**Status:** verification queue, not an acceptance prediction or a statement that reviewer demands have been satisfied.
**Scope:** four independent uploaded review reports: r1=A PostgreSQL systems, r2=B proofs/algorithms, r3=C experiments/statistics, r4=D novelty/meta. Based on manuscript `main(5).pdf` (12 total pages). **No change to paper/main.tex and no new measurement in this commit.**

## Status legend
- **TEXT-SUPPORTED:** manuscript explicitly states a bounded claim; independent truth or external reproducibility remains unverified.
- **REPO-LEAD:** a named repository artifact is confirmed to exist, but its adequacy for the requested claim is not established.
- **PROOF/IMPLEMENTATION-CHECK:** requires detailed independent verification or an executable check.
- **NEW-ANALYSIS:** may use saved records if available, but no output is yet verified.
- **NEW-EXPERIMENT:** additional data collection or implementation would be required if not already archived.
- **POSITIONING:** research novelty/scope judgment; cannot be cleared solely by a wording edit.

## Cross-review issue register (ordered by publication risk)

| ID | Review mapping | Reviewer concern / falsifiable question | Current evidence status | Verification action and acceptance criterion |
|---|---|---|---|---|
| T01 | A-M1; D-W3 | Does each selector round preserve the A1–A4 eligible-edge ↔ currently usable object correspondence and the termination condition? | REPO-LEAD: `notes/pg-mcv-maximal-matching-correspondence.md` and linked `experiments/pg-tracing/runs/20261017/report.md`; not yet independently audited | Trace four PG functions, branch predicates, and clause consumption; create a source-location/invariant table; list conditions not covered |
| T02 | A-M1/M2; D-W3 | What fraction of actual frozen Test estimations satisfy each A1–A4 condition, and can theoretical matching predict observed chosen IDs? | NEW-ANALYSIS or NEW-EXPERIMENT; manuscript fixture alone is not a population coverage audit | Audit instrumented task records per condition, plus discordance counts; if missing, qualify scope rather than invent prevalence |
| T03 | A-M2; D-W3/W8 | Are requested relative OID orders, observed catalog OIDs, and selector priorities consistent for all arms? Which permutations are physically attainable? | TEXT-SUPPORTED controls; underlying per-arm data unverified | Inventory physical-order manifests and diagnostics, validate triplets and document catalog operations; compare small-set physical census where records exist |
| T04 | A-M3; C-M3; D-W9 | Does frozen multiplicative modeled loss rank or predict physical Q-error on matched task/scheme observations? | NEW-ANALYSIS / potentially NEW-EXPERIMENT; the manuscript **does not** claim equivalence | Locate task-level join keys and paired prediction/observation records; compute rank agreement, direction agreement and failure cases on frozen arms, never train on Test |
| T05 | A-M4; D-W1/W3/W8 | Is scheme-choice uncertainty plausible for a deployed advisor unable to read/call the actual policy, as distinct from constructed alternative OID orders? | POSITIONING + possibly NEW-EXPERIMENT; present paper explicitly labels uniform orders counterfactual | Specify a concrete advisor information boundary and practical deployment scenario; do not infer production order probabilities from fixture interventions |
| T06 | A-M5; C-M1; D-W4/W5 | Can we train selectors directly for common-order mean A or worst G, not merely evaluate frozen N/P sets? | NEW-EXPERIMENT; current A/G enumeration is read-only | Feasible candidate sizes and runtime first; evaluate A/G selectors under a declared common objective and holdout protocol |
| T07 | A-M7; C-M2; D-W5/W6 | How far from globally optimal are add-only greedy N/P choices? | NEW-ANALYSIS / NEW-EXPERIMENT; manuscript explicitly disclaims optimality | Exhaustive budget-feasible search or certified bounds on tractable candidate subsets; local 1-swap checks, runtime, gap |
| T08 | A-M6; D-W7 | Are measured maintenance cost and downstream plan/runtime effects sufficient for statistics-advisor practical utility? | NEW-EXPERIMENT; current budget is proxy cost and outcome is Plan Rows Q-error | Scope an honest runtime/storage/refresh measurement plan or retain a narrower estimation-risk positioning |
| T09 | C-M4/M5; A-M8; D-W8 | Are the exact finite-population samples, certainty strata, seeds, resampling decisions and approximate intervals independently auditable? | TEXT-SUPPORTED estimators; primary order-level logs need discovery | Verify all 156 arms, sample frames, SRSWOR records and fpc variance; calculate simultaneous intervals or provide clearly exploratory comparisons |
| T10 | C-M6; A-M2 | Does changing relative order identify only the aggregate order effect, not individual-object mediation? | TEXT-SUPPORTED caveat; no individual causal result | Keep causal language at order-intervention level unless isolated swaps are measured |
| T11 | B-M1 | Does fixed-set MAS hardness have a finite-encoding decision language despite ln 2 in the objective? | PROOF/IMPLEMENTATION-CHECK; normalized forward-arc identity is given but machine-model language absent | Define integer threshold input K and rational factors {1,2}; prove equivalence without requiring arbitrary real arithmetic; separate NP-hardness from membership |
| T12 | B-M2 | Is shared-priority feasibility polynomial under *explicitly encoded* task graphs and target matchings, and what happens with invalid targets? | PROOF/IMPLEMENTATION-CHECK | Specify m,t, incidence input length, validate each S_i maximal, derive polynomial time bound; check edge-ID consistency |
| T13 | B-M3; A-M3 | Under what verifiable coverage and loss-alignment assumptions does modeled scheme risk bound actual physical risk? | POSITIONING / PROOF; current manuscript explicitly denies unconditional transfer | State sufficient conditional proposition only if true, otherwise add a verification recipe and preserve non-guarantee |
| T14 | B-M4; D-W2/W9 | Are general ESS lemmas overemphasized compared with matching-coupled contributions? | POSITIONING | Rebalance abstract/concrete contributions after deciding on technical additions; do not represent elementary envelope/SLLN facts as novel |
| T15 | D-W1/W2 | What exactly is new beyond established statistics-advisors, conditional selectivity, CEG, robust decision-dependent uncertainty? | POSITIONING + LITERATURE CHECK | Build claim-level comparison with direct citations; distinguish known-policy oracle extension from unavailable policy; evaluate shared-priority reasoning as incremental contribution |
| T16 | D-W4 | Does large P/G gap translate to a useful computable tighter alternative, rather than pessimism only? | NEW-ANALYSIS / potentially NEW-ALGORITHM | Test structural special cases, low-cost bounds, or shared-priority aware selection; do not claim a guarantee without proof |
| T17 | C-M1; A-M7 | At B5 some PESS selections use only 3 objects while N uses 5: what is attributable to count vs identity? | NEW-ANALYSIS | Compare budget utilization, identity-controlled contrasts, and alternative feasible set diagnostics without post hoc causal attribution |
| T18 | C-M5 | Do four per-dataset comparisons require joint multiplicity treatment? | NEW-ANALYSIS | Determine predeclared hypothesis family, compute simultaneous intervals from frozen order-level values when available, retain effect sizes |
| T19 | A-M1; B-M3 | Is the matching source correspondence claimed as universally physical? | TEXT-SUPPORTED: Section 3 already restricts to A1–A4 and abstract freely varied priorities | Verify introduction/abstract/results wording stays scoped; distinct from proving A1–A4 commonly hold |
| T20 | B proof audit | Are structural bounds/tightness/proposition statements internally sound? | Reviewer B reports no fatal counterexample; **not independently certified** | Independent finite graph enumeration/property tests and targeted proof audit; preserve proposition boundaries |

## What is already evidenced by currently inspected repository materials

- `notes/pg-mcv-maximal-matching-correspondence.md` exists on PR #131 and describes a **conditional**, source-grounded proposition with two fixture-level creation orders, not general operational coverage.
- `experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json` exists, with 40/40 completed selection cases and per-case candidate metadata (one inspected example records 45 candidates). **This is not an exhaustive optimality certificate.**
- `docs/RESEARCH_CONTEXT.md` explicitly directs validation of technical assertions against primary code, reports and data, rather than treating the research notes as proof.
- The manuscript reports controlled order interventions, 156 physical arms, the finite-population estimator, and several limitations. **A manuscript report is not independent replay or artifact validation.**

## Execution gates

**Gate 1 — correctness / low-cost formal work:** T11, T12 and theorem statement audit; create discrete decision specifications; verify against code or hand-checked small cases.

**Gate 2 — artifact inventory, no new measurement:** T01, T03, T04, T09, T17, T18. Record paths, hashes, what measurements exist, and missing inputs. Avoid re-running 1.56M EXPLAINs if frozen primary records suffice.

**Gate 3 — feasibility of additional selection experiments:** T06/T07/T16, including candidate-universe sizes, subset enumeration cost, A/G objective evaluation cost and fair holdout.

**Gate 4 — paper positioning:** T05/T08/T13/T14/T15/T19 after evidence audit. Choose whether to claim a scoped structural/empirical study or a stronger deployed-advisor result; do not try to solve missing data with rhetorical disclaimers.

## Decision rules

1. A reviewer requirement is a hypothesis to verify, not an automatically established failure. Mark it **resolved** only after attaching direct code/data/proof evidence.
2. Preserve frozen empirical results. If a new experiment is necessary, make it a separate preregistered protocol and clearly mark it new.
3. Do not infer a physical upper bound from abstract PESS absent coverage plus metric alignment.
4. Distinguish counterfactual relative-OID distributions from observed deployment uncertainty.
5. Keep review-specific IDs and evidence links stable; update this tracker as facts are checked, without silently rewriting review conclusions.

## Gate 1 verification memo — T11/T12 (2026-10-28)

### T11: MAS fixed-set hardness, checked in current manuscript

**Confirmed source-level typo:** the displayed normalized reduction formula currently contains `\nu\text{ precedes }v` rather than the intended vertex variable `u\text{ precedes }v`. This renders the mathematical equation incorrect as written even though the adjacent prose explains the intended reduction. Correct in a subsequent paper patch.

**Proof assessment:** the *combinatorial* mapping is valid under the freely ordered abstract model. Build a common star with one edge per vertex; one two-edge eligible task per oriented arc; choose factors 2 (tail) and 1 (head), with alpha zero and weight one. For any shared total order the task contributes exactly ln(2) iff the arc is forward. Thus normalized objective G/ln(2) equals maximum forward-arc count. This is a reduction of a *fixed-set evaluation* decision, not outer resource optimization and not physical PostgreSQL.

**Formal decision language to state:** input a finite edge-labeled star, explicitly listed two-edge task incidences, rational correction factors confined to {1,2}, alpha=0, unit task weights, and nonnegative integer K (all in binary or finite lists). Ask whether **there exists** a strict global edge order under which at least K task losses equal ln(2), equivalently whether G(M) >= K ln(2). The predicate is checked via integer counts; no oracle for evaluating arbitrary transcendental inputs is required. The star restricted language is in NP (order certificate + forward-arc count); the reduction establishes NP-hardness, in fact NP-completeness **of this restricted normalized threshold decision problem**. Do not transfer NP membership to general real-parameter optimization without an encoding model.

**Status:** COMBINATORIAL ARGUMENT VERIFIED AGAINST WRITTEN REDUCTION; TYPO CONFIRMED; ENCODING PATCH REQUIRED. Not externally verified against the original MAS source citation.

### T12: shared-priority prescribed-target feasibility

**Explicit input contract:** one finite global set M of m labeled edges, each with encoded endpoint pair; t explicitly listed task-eligible subsets E_i cap M, and one explicitly listed target edge-ID set S_i for each task. Require each S_i to be a subset of the relevant E_i and an inclusion-maximal matching; this validity condition is testable in polynomial time, and malformed inputs should be rejected. Edge IDs must denote one shared global edge across all tasks. Let N be total length of these explicit incidence and endpoint lists.

**Safe-edge algorithm:** start with empty prefix R and repeatedly append any remaining e satisfying, for every i with e in E_i, either e in S_i or an already appended target f in S_i conflicts with e. If no safe e exists before m edges are appended, reject; else return constructed order. Tasks in which e is ineligible impose no condition.

**Correctness invariant:** if a feasible full order extending the current prefix exists, moving any safe e to the start of a feasible suffix preserves each task's accepted target set (target case: disjoint from all other targets; non-target case: already rejected by a prefix target blocker). Hence arbitrary safe selection preserves extensibility; the first edge of every feasible suffix is safe. A completed safe order yields targets; a dead end implies no compatible total order.

**Complexity:** a deliberately loose bound O(m^2 N) time for m rounds, scanning up to m remaining edges each round and checking their explicit task incidences/target blockers in O(N) per candidate, with O(N+m) representation storage. Validating maximal matchings and the common edge labels is polynomial and absorbed into this bound for m>=1. Empty M returns the empty global order after validating empty task targets. No claim is made about succinctly encoded task families or unspecified targets.

**Status:** ARGUMENT CHECKED / EXPLICIT-INPUT FORMALIZATION READY; manuscript lacks detailed input contract and bound. Independent exhaustive small-instance implementation test not yet performed.

### Scope of this memo

This verification records an argument review, not machine-checked formal proof, PostgreSQL source audit, or new physical measurements. No experimental result is changed.

## Gate 1 executed checks and paper patch (2026-10-28)

Ran an independent local Python exhaustive-order cross-check (not a committed reproducibility test): 3,210 explicit target tuples from 570 seeded small synthetic graph/task instances, with 1–6 labeled edges (including possible parallel edge endpoints) and three task-eligible subsets. Each target came from an actual greedy total order. The safe-edge predicate agreed in **all 3,210** cases with exhaustive existence over every total order; no counterexample observed. This does not amount to a mathematical proof or a test of invalid-target rejection.

A separate 240 seeded small directed-graph checks (2–7 vertices) confirmed the MAS forward-arc count interpretation of the reduction. No PostgreSQL runtime was used.

Manuscript commit `3a5e569` now specifies explicit edge and task-incidence encoding, target maximal-matching validation, a conservative O(m^2 N) input-size bound, discrete integer-threshold MAS language with factors {1,2}, and fixes the printed forward-arc formula. **T11/T12 manuscript fixes complete at source level; LaTeX recompilation and independently retained test artifact remain outstanding.**

## Gate 2 primary-artifact inventory, pass 1 (2026-10-28)

The following files were **fetched and read directly from the PR branch**, not inferred from paper statements alone:

| Track | Primary repository evidence | What it concretely shows | What it still cannot show |
|---|---|---|---|
| T01 | [Conditional PG source correspondence](pg-mcv-maximal-matching-correspondence.md); [2026-10-17 fixture report](../experiments/pg-tracing/runs/20261017/report.md) | Explicit A1–A4; a four-attribute path with creation orders `ab,bc,cd` and `bc,ab,cd`; traced chosen OIDs and consumed clause indices; outcomes `{ab,cd}` and `{bc}` match maximal-matching predictions. The report pins PG 16.14 instrumentation to `e17bfdf0c871bec02bea8c979b29d7603772b14d` against upstream `REL_16_14`. | No per-round *independent source re-audit* yet; no all-workload A1–A4 prevalence audit; no generic physical completeness theorem. **T01 remains OPEN/partial.** |
| T03 | [#105 physical order findings](../experiments/oid-order-stress-test-issue105/findings-v2.md); [#107 findings](../experiments/oid-uniform-priority-issue107/findings-v2.md) | #105 reports requested CREATE order matching actual OID-sorted candidate IDs in each of eight paired configurations; full-catalog/content/sample fingerprint controls and 80,000 valid diagnostics. #107 records 156 eventual complete arms at the same frozen schedule, but includes an initial 12-arm validator failure and 8 separately remeasured certainty arms. | Full per-arm independent replay of #107 identity/OID checks and physical realizability of arbitrary future orders; underlying raw data lives outside Git. **T03 remains OPEN/partial.** |
| T09 | [#107 findings v2](../experiments/oid-uniform-priority-issue107/findings-v2.md); [#125 read-only frozen-data revalidation](../experiments/oid-order-attribution-issue125/findings.md) | Reports sample hash `0b6b247445ab81589c5c5ea7991215fd25e5c60cddf990bf07e3867cda9baa73`, seed `17770611677888985956`, RNG `ess-splitmix64-fisher-yates-v1`; 156 final arm identities and 1,560,000 cumulative Test observations; #125 claims archive/member/row-level checks and independent recomputation of #107 estimands. | The Git-connected environment has not accessed the three external raw archives, so those claimed integrity checks cannot be independently rerun here. The eight historical #105 reuse-rejection reasons are not recoverable beyond generic catch labeling. **T09 has substantial documented evidence; raw independent replay remains OPEN.** |
| T04 | [#125 order attribution](../experiments/oid-order-attribution-issue125/findings.md); [#105 findings](../experiments/oid-order-stress-test-issue105/findings-v2.md) | Physical candidate-ID-aligned event sequences and Q-errors are described, with frozen raw records archived externally. | No matched task-level *model-prediction versus physical-Q-error* calibration dataset has yet been confirmed. Diagnostic attribution is not model calibration. **T04 OPEN.** |

**Important refinement versus the initial tracker:** r3/C's concern about missing sample provenance is partly answerable by the already recorded seed, RNG, sample hash, exact schedule and read-only revalidation report. The remaining problem is independent access/replay of archived source observations and validity of inferential intervals, not an absence of all sampling metadata.

**Do not claim closure:** a detailed findings report or a hash in Git is a *lead to verify*; it is not equivalent to the bytes of the externally archived JSONL and manifests being available through the current GitHub connector.

### Immediate follow-ups

1. Read the source correspondence note's exact file/line references and identify any gap between A4 scoring-tie argument and source logic.
2. Inspect #107 protocol and sample schedule artifacts within Git for per-arm requested priority lists and validation columns, without needing the external runtime archives.
3. Locate any already archived model/physical matched records; if none are present, write a scoped new-analysis requirement rather than claiming calibration can be computed from aggregated P95 alone.

## Gate 2 targeted T01/T04 evidence audit, pass 2 (2026-10-28)

**T01 source reference inventory:** The source correspondence note specifies these five PG 16.14 code segments:
- `clausesel.c#L119-L188` — `clauselist_selectivity_ext` single-relation entry / estimated clause bookkeeping;
- `extended_stats.c#L1225-L1321` — `choose_best_statistics` candidate scoring and tie resolution;
- `extended_stats.c#L1696-L1879` — `statext_mcv_clauselist_selectivity` greedy repetitions and consumed clauses;
- `relcache.c#L4857-L4934` — `RelationGetStatExtList` statistics-object OID sorting;
- `plancat.c#L1439-L1535` — `get_relation_statistics` built-stat metadata.
These are *locations furnished by the research note*, not a newly completed independent line-by-line inspection of PostgreSQL source. The recorded fixture includes chosen OIDs and consumed clause indices for both path orders; dynamic A1–A4 prevalence across all physical Test queries remains unmeasured in the materials inspected.

**T04 previously overlooked bounded calibration evidence:** `experiments/forest10-decision/real-stage-report.md` records a six-query **valid split** Forest10 study with 6 adjacent two-column MCV candidates, 720 *abstract* orders, 84 task/candidate/repetition calibration records, and separate measured pre-clamp estimates versus an exact arithmetic model. Its documented composition check for one disjoint `e12+e34` instance reports relative discrepancy `-1.84e-16` from the product of single-statistic ratios, whereas overlapping combinations `e12+e23` and `e23+e34` report relative discrepancies `0.1590` and `-0.4904`. This is **valuable negative/positive bounded evidence about the approximation**, not general multiplicative validity or Test Q-error calibration. The 84-record calibration JSON is stated to be in external local storage with SHA `636d363792d36f27d5b2ff6ea5f9311437ea4f8d04dd9646d7a6be12a8cffd3e`; its bytes have not been retrieved via this connector.

Another artifact, `experiments/pess-multidataset-heldout-stage2b/generalization-issue64/forest10-json-calibration-smoke-v1.md`, describes a 20-valid-query structured `nrows_preclamp` smoke (212 EXPLAIN calls, 46 configurations) with **no truth labels loaded**. Its 212 compact observations are retained *in Git* at `experiments/pess-multidataset-heldout-stage2b/generalization-issue64/forest10-json-calibration-smoke-v1.jsonl` (reported SHA `44b6af801f501d2f078c92ee41d9e5c1a645f492e668d5f06258d862db981210`). That material alone cannot compute physical Q-error, because truth was purposely excluded. Avoid conflating it with the six-query valid study or official Test.

**T04 refined status:** EXISTING BOUNDED MODEL/PG COMPOSITION CHECK FOUND; PRIMARY OFF-GIT RAW CALIBRATION UNINSPECTED; NO BROAD TASK/SCHEME MATCHED MODEL-versus-Test-QERROR CALIBRATION ESTABLISHED. The documented overlapping-edge discrepancies underline why a universal separable-correction claim must not be made.

**Next evidence tasks:** independently verify the exact upstream PostgreSQL code locations (not merely their presence in the note); inspect the in-Git 212-row JSONL schema and whether other paired valid records exist; assess feasibility of constructing an *additional* matched validation analysis from archived train/valid data without Test re-selection. No new experiments, measurements, source changes, or manuscript edits were made in this pass.

## Gate 2 T04 record-schema audit, pass 3 (2026-10-28)

Directly fetched the complete **86,713-byte, 212-row** in-Git `experiments/pess-multidataset-heldout-stage2b/generalization-issue64/forest10-json-calibration-smoke-v1.jsonl`. Its row schema contains `query_id`, `config_id`, `nrows_preclamp`, `mcv_events`, `static_eligible`, `relation_oid`, and diagnostic status fields. Representative row: query `arecel:forest10:valid:000000`, config `Empty`, `nrows_preclamp="38322.788056849124"`, no MCV events. This provides a within-valid-split key `(query_id,config_id)` for comparing numeric pre-clamp estimates across configurations. It does **not** include true cardinalities, the modeled per-scheme predicted estimates, or physical rounded `Plan Rows` Q-error. Thus correlation with Q-error and worst-scheme identification cannot be calculated from this file alone.

The independently fetched `experiments/forest10-decision/real-input-manifest.json` establishes the frozen Forest10 valid/test split and source labels' hash but does not itself provide row-level truths. The earlier six-valid-query calibration raw JSON is named, with SHA, by `real-stage-report.md` but its bytes are off Git. Do not join to official Test observations: this smoke uses `valid` query IDs and deliberately did not load truth.

**Analysis feasibility conditions:** (1) fetch authorized valid-split query truth records and verify dataset, query IDs and hashes; (2) locate exact frozen model coefficients or predicted per-scheme values for the *same* query IDs and config edge sets; (3) align preclamp/rounded observation semantics rather than equating them; (4) compare paired task/config predictions on validity-only data and report disagreement rates with a clear sample-selection caveat. If the available 212 rows were a fixed first-20-query smoke, infer nothing about random-query or full-workload calibration. The 84-record off-Git calibration run is a separate, noninterchangeable provenance layer.

**T04 status:** KEYED NUMERIC PG OBSERVATIONS CONFIRMED IN GIT; TRUTH/MODEL JOIN INCOMPLETE; NO NEW CALIBRATION ESTIMATE COMPUTED.

## Gate 2 T09 direct frozen-schedule structural validation (2026-10-28)

Fetched and parsed the authoritative in-Git `experiments/oid-uniform-priority-issue107/permutation-sample-v1.json` (24,793 UTF-8 characters). Verified **8 schedules / 156 arms**, with **no repeated permutations within any schedule**, all arms using their schedule's same set of resource IDs, and strictly sequential draw indices for all recorded SRSWOR units.

- Four Nominal five-object schedules: each 24 unique orders, exactly 2 fixed canonical/reverse orders (the pair is exact reverse), 22 SRSWOR orders, inclusion probabilities `1` and `11/59` respectively.
- Two five-object PESS schedules (Census13, DMV11): each 24 unique SRSWOR orders with inclusion probability `1/5`.
- Two three-object PESS schedules (Forest10, Power7): each 6 unique orders, probability `1`, matching 3!=6; the sample JSON uses a non-`census` selection label for these, so interpretation here depends on **six distinct permutations and size**, not a literal `census` label.
- Root seed is the exact decimal string `17770611677888985956`, read directly from the JSON text to avoid loss of precision in ordinary JavaScript numeric parsing. The declared RNG is `ess-splitmix64-fisher-yates-v1`.

**T09 partially resolved:** these checks establish correct frozen *schedule structure and inclusion probabilities*; they do not independently regenerate the sample using the versioned RNG, establish random sampling quality, access off-Git physical observation bytes, or calibrate approximate interval coverage. Next no-new-measurement task: independent deterministic RNG replay from `src/ess_research/arecel/oid_sampling.py` (or a separately written equivalent) against the exact frozen JSON SHA, and review of simultaneous inference from existing order-level data if accessible. Keep T09 OPEN for those separate checks.

No physical database execution, data resampling, or manuscript edits are part of this check.

## T18 aggregate-only four-way multiplicity sensitivity (2026-10-28)

The manuscript reports four separate approximate two-sided 95% per-dataset intervals using t_(.975,21)=2.0796138447. Without reading or resampling off-Git order-level outcomes, one can obtain a **rounded-summary sensitivity calculation** for family-wise 95% Bonferroni intervals across these same four fixed hypotheses: replace the per-dataset critical value with t_(1-0.05/(2*4),21)=2.7316324824. Infer each approximate SE as (reported upper minus reported lower)/(2*2.0796138447); since original intervals were rounded to 4 digits, the derived intervals below are *approximate*, not exact recomputations.

| Dataset | Reported difference | Approx. Bonferroni simultaneous 95% interval | Interpretation at this approximation |
|---|---:|---:|---|
| Forest10 | +0.1099 | [+0.0128,+0.2070] | Positive interval; estimated Nominal advantage under declared uniform-order estimand |
| Census13 | -1.1976 | [-1.6989,-0.6963] | Negative interval; estimated PESS advantage |
| DMV11 | -6.2463 | [-9.3878,-3.1048] | Negative interval; estimated PESS advantage |
| Power7 | +0.0293 | [-0.2371,+0.2957] | Inconclusive |

These results **do not** remove the manuscript's underlying approximate t-distribution/finite-sample coverage caveat, repeated-workload uncertainty, or the fact that the sampling design followed inspection of earlier outcomes. Bonferroni gives simultaneous control *only if* each constituent interval achieves its nominal marginal coverage and the fixed family is well-defined; no coverage guarantee is established here. Exact manuscript changes, if desired, should use full-precision frozen order-level standard errors and a predeclared four-contrast family. **T18: AGGREGATE-ONLY CHECK COMPLETED; exact artifact replay OPEN.**

## T09 deterministic RNG replay readiness (2026-10-28)

Directly read `src/ess_research/arecel/oid_sampling.py`; it defines `ROOT_SEED=17_770_611_677_888_985_956`, `SplitMix64` with rejection-based `randbelow`, SHA-256-derived per-stratum seeds, lexicographically enumerated residual orders, Fisher–Yates, and canonical JSON serialization with terminal LF. The 3-object PESS census records are correctly labeled `enumerated` in code (not `census`). The 8-stratum schedule was already structurally cross-checked against its JSON. **A byte-for-byte independent sample regeneration was NOT performed here**; that requires executing the Python code or writing an independent implementation with SHA-256 and checking against the pinned hash. The code is sufficient to prepare a local read-only replay without any PostgreSQL run.

## T15 targeted external prior-art comparison, pass 1 (2026-10-28)

External publication pages/abstracts checked (not a complete full-text prior-art or priority audit):

1. Chaudhuri & Narasayya, *Automating Statistics Management for Query Optimizers*, ICDE 2000. Microsoft Research: https://www.microsoft.com/en-us/research/publication/automating-statistics-management-for-query-optimizers/ . Already considers selecting which optimizer statistics to maintain, so ESS must not claim resource selection itself as novel.
2. Bruno & Chaudhuri, *Conditional Selectivity for Statistics on Query Expressions*, SIGMOD 2004. https://www.microsoft.com/en-us/research/publication/conditional-selectivity-for-statistics-on-query-expressions/ . Already reasons about alternative estimation decompositions/conditional selectivity; ESS cannot claim complete path alternatives are new.
3. Chen, Huang, Wang, Salihoglu & Salem, *Accurate Summary-based Cardinality Estimation Through the Lens of Cardinality Estimation Graphs*, PVLDB 15 (2022). https://www.vldb.org/pvldb/vol15/p1533-chen.pdf . Already represents estimation paths and their selection in graph summary estimation. ESS's upstream budgeted installation under uncertain path policy is a proposed distinction, not proof that an older advisor cannot be extended to express it.
4. Nohadani & Sharma, *Optimization under Decision-Dependent Uncertainty*, SIAM Journal on Optimization 28(2), 2018. https://doi.org/10.1137/17M1110560 . Decision-dependent uncertainty itself is established prior art; generic ESS `min_M rho(...)` is not a novelty claim on that mathematical motif.

**Provisional contribution positioning:** (a) ESS's advisor/estimator information boundary is a potentially useful problem framing; (b) the restricted cross-task shared-edge-priority feasibility structure, realizability criterion, factor-t PESS relaxation tightness, and fixed-set priority hardness are the most distinctive *specific* results; (c) controlled PG 16.14 OID interventions demonstrate a narrow physical mechanism. **Unverified novelty:** whether the safe-edge precedence-feasibility result or equivalent shared-priority representation already appears in weighted greedy matching / priority-ordering literature; whether existing advisor-oracle extensions can implement the same choice. Do not certify priority until a deeper theorem-level literature comparison is completed.

**Reviewer D's substantive critique remains OPEN:** no comparison establishes that a measurable real-world advisor information constraint forces the proposed uncertainty class, and no shared-policy-aware outer selection algorithm has yet been demonstrated. Editing Related Work prose alone cannot close that issue.

**T15 status: DIRECT PRIMARY PUBLICATION SUMMARIES CHECKED / NOVELTY PRIORITY NOT CERTIFIED / COMPARATIVE CLAIMS DELIMITED.** No paper-body edits made.
