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
