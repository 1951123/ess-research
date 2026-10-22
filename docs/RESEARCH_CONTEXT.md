# ESS Research — persistent research context

**Last reviewed:** 2026-10-17  
**Purpose:** Stable, compact research background for a human researcher, a new ChatGPT conversation, and Codex. This is **not** a substitute for checking the cited paper, proofs, code, or experiment outputs.

## 1. Read order / sources of truth

1. Read **this file** for goals and terminology.
2. Read [DECISIONS.md](DECISIONS.md) for *why* the current direction was chosen.
3. Read [STATUS.md](STATUS.md) for active work, evidence status, and outstanding PRs.
4. Read [../AGENTS.md](../AGENTS.md) when implementing tasks with Codex or other agents.
5. For a technical claim, read the **primary source** (paper, note, code, experiment data or upstream PG source), rather than relying solely on a summary.

Authority by subject: mathematical definitions and assumptions: [paper/main.tex](../paper/main.tex); proofs: [notes/](../notes/); implementation: the relevant code repository; experimental results: recorded scripts/raw results/reports; workflow state: [STATUS.md](STATUS.md). If they disagree, surface the disagreement rather than silently harmonizing it. A chat transcript is *not* the canonical research record.

## 2. Research question and intended paper

**Central question:** Under a maintenance budget, how should we select estimation/statistics resources when the cardinality estimator's **scheme-selection policy is unknown or inaccessible**?

We prescribe an admissibility rule for **complete estimation schemes**, potentially close to—but not identical to—a DBMS's actual behavior. We minimize the sum of task-wise worst-case estimation losses permitted by this rule.

**Agreed first-paper strategy (2026-10-17):**

- General estimator-agnostic formulation and its essential structural properties.
- A well-defined structured instantiation motivated by PostgreSQL two-column MCV statistics, using maximal matchings.
- Exact/structured optimization algorithms and independent validation.
- Source-grounded and, where possible, runtime-verified PostgreSQL model adequacy, numerical calibration, and maintenance-cost measurements.
- Rule misspecification is an explicit limitation/theoretical avenue; do **not** claim coverage of unknown real DBMS policies without assumptions.

Provisional positioning: an *optimization-oriented database research paper*, not solely a PG-specific advisor and not an unrestricted generic robust-optimization paper.

### Research architecture agreed 2026-10-22

The enduring project has **two independently publishable research tracks**, without requiring every optimization formulation to have a novel solver or every solver to introduce a new objective:

- **Optimization Modeling:** specify information and uncertainty assumptions, feasible decisions, objectives (currently Nominal, task-wise PESS, and Joint-Robust), and compare decisions under common held-out evaluation conditions.
- **Optimization Algorithms:** for a fixed, explicitly defined problem, study exact references, scalable exact optimization, and bounded/approximate solvers with their correctness, runtime, and solution-quality evidence.

PostgreSQL is the **primary empirical instantiation**, supplying versioned cardinality-estimation behavior, statistics-maintenance measurements and workload evidence. It does not define the general estimator-agnostic model. In a controlled comparison, pin PG source, data, calibration, evaluation and cost assumptions; any changed calibration/loss convention is a separately identified model version.

**Separate model from solver from evaluator.** Adopt minimal shared semantics for a *Problem Instance* (objective, resources, constraints, assumptions and input provenance), *Solver Result* (selected resource set, feasibility, objective, status, trustworthy bounds/certificates and resources consumed), and *Evaluation Result* (independent held-out measurements). These are conceptual contracts, **not authorization to implement a new framework**. A solver may support only a restricted problem class and must state it. Keep independently proven optima separate from solver-reported floating-point optimality and from feasible solutions lacking a global certificate. The latter can support clearly labeled auxiliary comparisons, not unqualified claims about differences between true model optima.

Earlier first-paper positioning above is a historical target, not a requirement that one paper combine both tracks. See [D-008](DECISIONS.md) and the phase plan in [STATUS.md](STATUS.md).

## 3. Generic mathematical model

- Tasks: finite set \(\mathcal I\), task weights \(w_i>0\), true cardinalities \(N_i\ge0\), reference \(T_i=\max\{1,N_i\}\).
- Candidate resources: finite set \(\mathcal E\); choose one **unordered global resource set** \(M\subseteq\mathcal E\).
- Complete task-\(i\) schemes: finite \(\Omega_i\) with \(\operatorname{used}(\sigma)\subseteq\mathcal E\).
- **Prescribed** admissibility \(\varnothing\ne\Gamma_i(M)\subseteq\Omega_i\) and \(\sigma\in\Gamma_i(M)\Rightarrow\operatorname{used}(\sigma)\subseteq M\).
- Estimator \(\operatorname{Est}_i(\sigma)>0\), task loss \(\ell_i(\sigma)\ge0\); leading choice \(|\log(\operatorname{Est}_i(\sigma)/T_i)|\).
- Maintenance \(\operatorname{Maint}(M)\le B\), \(\operatorname{Maint}(\varnothing)=0\). **No generic additivity or monotonicity** assumption.

\[
\min_{M\subseteq\mathcal E:\ \operatorname{Maint}(M)\le B}
F_\Gamma(M),\qquad
F_\Gamma(M)=\sum_{i\in\mathcal I}w_i
\max_{\sigma\in\Gamma_i(M)}\ell_i(\sigma).
\]

Crucial: \(\Gamma_i(M)\) is **not presumed nested** when \(M\) grows. If \(\Gamma_i(M)\subseteq\Gamma_i(M')\) whenever \(M\subseteq M'\), then the worst-case-min objective cannot improve on choosing no extra resources. A *complete scheme* may become inadmissible after resources are added; this is different from merely making a greater menu of optional schemes available.

The unknown **real** possible-scheme set \(\mathcal R_i(M)\) and prescribed \(\Gamma_i(M)\) may be equal, one may contain the other, or they may be incomparable. An upper-bound claim for true worst-case loss requires an appropriate inclusion \(\mathcal R_i(M)\subseteq\Gamma_i(M)\) (and matching losses); it is **not** automatically guaranteed, especially for a closed-source DBMS.

Task-wise robust aggregation is not necessarily an achievable worst case under *one shared global estimator policy*: the maxima across tasks may require incompatible internal choices or OID orders.

## 4. Structured instantiation

For each task \(i\), candidate two-column MCV objects are **labeled edges** \(e\in\mathcal E_i\) joining attributes in a task graph \(H_i=(V_i,\mathcal E_i)\). Duplicate endpoint pairs are permitted as distinct labeled edges.

\[
\Gamma_i^{\rm MM}(M)
=\operatorname{MaximalMatchings}(H_i[M]),
\quad H_i[M]=(V_i,M\cap\mathcal E_i).
\]

**Maximal** means no additional available edge can be added; do not confuse with *maximum-cardinality* matching. The empty matching is the only maximal matching when no edges are available.

Illustrative positive **pre-clamp** estimate:
\[
\operatorname{Est}_i(P)=n_i^0\prod_{e\in P}r_{e,i},\quad
\alpha_i=\log(n_i^0/T_i),\quad b_{e,i}=\log r_{e,i}.
\]
The matching loss becomes
\[
L_i(P)=\left|\alpha_i+\sum_{e\in P}b_{e,i}\right|.
\]
The *structured* budget uses a controlled, **additive proxy** \(\sum_{e\in M}\bar m_e\le B\); this is not a proven model of full physical ANALYZE time. PostgreSQL plan-row clamping/rounding is a **separate** metric, not interchangeable with raw pre-clamp loss. The current Advisor implementation uses exact rational *model inputs* and float-based numerical MILP, not exact rational MILP certification.

## 5. PostgreSQL semantics and rule adequacy

Source review targeted PostgreSQL **REL_16_14**:

- `choose_best_statistics` ranks remaining MCV candidates by newly covered attributes, then narrowness, then list order on a tie.
- `statext_mcv_clauselist_selectivity` repeatedly selects an object and excludes its consumed clauses.
- The statistics-object list is normally ordered by OID.
- The AND-path can multiply estimates from separate selected MCV objects; each MCV object's internal selectivity correction is more involved than blindly multiplying individual column factors.
- ANALYZE's sampling requirement depends on statistics targets across the set of objects, hence **physical maintenance is not generally additive**.

With narrowly scoped single-table, simple-AND, one-clause-per-distinct-attribute, already-built two-key MCV objects and no estimator interference, source control-flow supports the proposition that **a fixed PG run selects a maximal matching**. Under *arbitrary abstract candidate priority orders*, every maximal matching can be produced by a greedy selector. This is **not** a claim that a fixed PG database realizes all such matchings.

**Current evidence (2026-10-17):** the scoped [correspondence note](../notes/pg-mcv-maximal-matching-correspondence.md) and [SQL fixture](../experiments/pg-tracing/trace_pairwise_mcv.sql) were merged via [ess-research PR #1](https://github.com/1951123/ess-research/pull/1); the [instrumentation](https://github.com/1951123/ess-postgresql/pull/1) was built and exercised on its research branch before that PG PR was merged. The [runtime report and raw logs](../experiments/pg-tracing/runs/20261017/report.md) were merged via [ess-research PR #4](https://github.com/1951123/ess-research/pull/4). Two OID-order fixtures observed `{ab,cd}` and `{bc}` with actual `ESS_MCV_TRACE` logs. This is fixture-scoped empirical support, **not** a proof for unrestricted PostgreSQL queries or independent worst-case scheme choices across tasks.

Reference source paths:

- https://github.com/postgres/postgres/blob/REL_16_14/src/backend/statistics/extended_stats.c
- https://github.com/postgres/postgres/blob/REL_16_14/src/backend/statistics/mcv.c
- https://github.com/postgres/postgres/blob/REL_16_14/src/backend/commands/analyze.c
- https://github.com/postgres/postgres/blob/REL_16_14/src/backend/optimizer/path/clausesel.c
- https://github.com/postgres/postgres/blob/REL_16_14/src/backend/utils/cache/relcache.c

## 6. Technical results and project repositories

**Existing mathematical work** (model-internal unless stated otherwise):

- [Structural foundations](../notes/structural-foundations.md): empty-set degeneracy of nested \(\Gamma_i\), structural complexity, nonmonotonicity, and graph considerations.
- [Conditional adversarial constraints](../notes/conditional-adversarial-constraints.md): for full-graph matching \(P\) and selected-vector \(x\),
  \[
  \delta_i(P,x)=\sum_{e\in P}(1-x_e)+\sum_{f\in D_i(P)}x_f,
  \]
  where \(D_i(P)\) consists of candidate edges disjoint from every vertex saturated by \(P\). At binary \(x\), \(\delta_i(P,x)=0\) iff \(P\) is maximal in \(H_i[M]\). This underpins conditional scenario cuts.
- [Master–Oracle algorithm](../notes/master-oracle-algorithm-design.md): conditional epigraph constraints, matching-specific bounds, an exact *mathematical* oracle framework, and numerical implementation caveats.
- [Structured outer selection](../notes/structured-outer-selection.md): task/candidate incidence decomposition, integer-budget pseudo-polynomial DP, and bounded-treewidth formulations with explicit assumptions.

**Implementation / experimentation:**

- [ess-advisor](https://github.com/1951123/ess-advisor): synthetic model, matching enumeration, Fraction-based exhaustive reference, static conditional MILP, numerical HiGHS Master–Oracle. Code validation is not a physical PG validation.
- [ess-postgresql](https://github.com/1951123/ess-postgresql): PG source with DEBUG1 MCV research tracing instrumentation now merged into `main` (PR #1); not pristine upstream PG, and not evidence of end-to-end ESS integration.
- [ess-research](https://github.com/1951123/ess-research) (**this repo**): central research decisions, paper, notes, synthetic experimental records, cross-repo status and planned validation.

The [cache ablation report](../experiments/synthetic/cache-ablation-report.md) contains seeded synthetic and independent exhaustive references. For `medium_dense`, reference optimum is 25; report median runtimes are approximately 0.0575 s (static MILP) versus 0.6704 s (precompute+cache Master–Oracle). **Do not claim the Master–Oracle is faster on this benchmark** or that synthetic results establish real PG benefits.

## 7. Current research checkpoints

See [STATUS.md](STATUS.md) for up-to-date blocking items and [DECISIONS.md](DECISIONS.md) for choices/revisit conditions. High-priority agenda:

1. **Completed for the four-attribute path fixture:** validate scoped PG-to-maximal-matching behavior with runtime tracing; see the [2026-10-17 evidence report](../experiments/pg-tracing/runs/20261017/report.md). Extend the fixture suite only when new semantic boundaries require testing.
2. Separate the PG estimator's real values from positive pre-clamp multiplicative abstractions; calibrate and test their validity.
3. Benchmark and bound the additivity error of fixed-sample maintenance-cost proxies.
4. Improve and compare algorithms on independently certified larger instances; compare *robust resource selections* with nominal/greedy alternatives and evaluate the price of pessimism.

**Do not** infer an unobserved query plan or selected statistic solely from `EXPLAIN` row counts. **Do not** present unchecked compiler or test results as completed experiments.

## 8. New-chat resumption instruction

Suggested first message:

> We are continuing ESS Research. Read `docs/RESEARCH_CONTEXT.md`, `docs/DECISIONS.md`, `docs/STATUS.md`, and relevant open PRs in `1951123/ess-research`; use `1951123/ess-advisor` and `1951123/ess-postgresql` for implementations. Separate mathematical proofs, source-derived claims, tested observations, and open hypotheses. Summarize current blockers and continue from the recorded state. Do not infer changes that have not been merged or executed.

Update this document only for *durable* changes to the research's fundamentals; everyday task progress belongs in STATUS and related Issues/PRs.
