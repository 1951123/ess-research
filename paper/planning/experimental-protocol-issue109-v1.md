# Section 5 — Experimental Protocol (Issue #109, v1)

**Status:** standalone English manuscript draft for review. This is a synthesis of frozen evidence, not a proposal for further execution. [Sections 1–4](strategy-uncertainty-issue109.md) establish the modeling-first question; this section separates how resource decisions were obtained from what subsequent model and physical measurements mean. Do not overwrite `paper/main.tex` before manuscript integration review.

## 5. Experimental Protocol

### 5.1 Research questions and evidence layers

Our experiments address three complementary questions. **RQ1:** Can priority changes alter the statistics actually applied by PostgreSQL and the resulting physical estimates? **RQ2:** What overlapping resource structures and model-level priority sensitivity result from fixed-policy Nominal versus task-wise PESS optimization? **RQ3:** Under a *counterfactual* uniform global relative-OID ordering, how do these frozen selections compare in expected physical held-out estimation error?

The experimental stages intentionally measure distinct objects:

| Stage | Frozen object/input | Reported observable | Status/role |
|---|---|---|---|
| **#99 Train-only selection** | Original official AreCEL Train workload/labels and a fixed PostgreSQL-derived model | Nominal and PESS heuristic-selected unordered \(M(B)\) | Construct decisions; **no Test selection** |
| **#101 fixed-order physical Test** | Original official Test split, frozen #99 resources, controlled PG | PostgreSQL top-level `Plan Rows` and zero-aware Q-error | Held-out fixed-policy outcomes |
| **#103 exact offline priority analysis** | Frozen Train loss tables and #99 selected sets | \(N_{\pi_0},A,G,P\), overlap and sensitivity over global priority permutations | Model-internal counterfactual; results associated with **Draft PR #104** at writing time |
| **#105 paired physical order stress** | Four Nominal \(B=5\) sets; canonical/reversed object creation | Actual PG selected-object/estimated sequences and Test Q-error | Controlled two-order mechanism/outcome intervention |
| **#107 sampled physical order population** | Eight \(B=5\) Nominal/PESS sets and frozen relative-order sample | Estimated \(\mathbb E_{\pi}[\operatorname{P95}_{q\in Test}Q]\) and permutation sampling error | Counterfactual order-risk estimate; **not a full 732-arm census** |

The chronological evidence does not redefine the original uncertainty problem. In particular, OID-sensitive behavior was studied after the task-wise-admissibility motivation and should be presented as a scoped system instance, not as the reason the problem was invented. We do not pool *Train* absolute-log model loss with physical *Test* Q-error.

### 5.2 Workloads, statistics and fixed environment

We use the four original AreCEL datasets/workloads: Forest10, Census13, DMV11 and Power7. Each has **100,000 official Train tasks/queries** for the frozen selection study and **10,000 original official Test queries** for physical evaluation. Train and Test have distinct roles: Train is the sole source of task labels used to calibrate the structured selection model and choose resource sets, whereas Test is the sole query/truth source for the official physical generalization results. The split containers were materialized via the documented trusted-pickle boundary; the #99 code indexed only Train task/label values and the #101/#105/#107 physical Test code indexed only Test workload/labels. Merely materializing a split container should not be misrepresented as never deserializing its other members.

Candidates in the studied instance are labeled **two-column MCV extended-statistics objects**. The #99 selected objects are frozen in `experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json` (SHA-256 `2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca`). The selection budget is an additive **per-object proxy**, not physical maintenance CPU time; the general model of Section 2 makes no additivity assumption. All physical comparisons fix the PostgreSQL **16.14** instrumented source build (source commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c` for the #105/#107 evidence), full source relations, and the fixed #99 ANALYZE sample/replay inputs. Ordinary per-column and selected extended-statistics objects have target **300**. The physical replay used the same controlled settings, including `plan_cache_mode=force_custom_plan`, `max_parallel_workers_per_gather=0` and `client_min_messages=warning`. A controlled replay sample and matching object fingerprints support comparisons that vary creation order without unintentionally changing the underlying data or MCV content. This setup does **not** reproduce the published AreCEL learned-estimator environment exactly; its public statistical target also differs.

### 5.3 Resource selection: same heuristic, different model objectives

For each dataset, the frozen budgets are \(B\in\{0,2,3,4,5\}\). The two trained objectives are **Nominal** loss under one specified candidate-ID priority and **task-wise PESS** loss over prescribed inclusion-maximal matchings. Both use the same deterministic **strictly improving, add-only greedy** procedure. Beginning with \(M=\varnothing\), it evaluates feasible one-object additions, selects the one giving the greatest strictly positive reduction in the objective (resolving ties by candidate ID), and stops if no feasible improving addition exists. It does not force-fill the budget, exchange or delete resources, restart from alternative initial sets, or certify global optimality. In particular, a nominal \(B=5\) cap can yield a three-object PESS set. The fixed 4 × 5 × 2 = **40 labeled selection cases** were all completed; deduplication produces **25 distinct physical configurations** over the dataset-specific resource sets.

Frozen Train losses use the specified positive pre-clamp multiplicative model and absolute logarithmic task error from Sections 2–3, with the implementation's exact-`Fraction` reference calculation. This is **model arithmetic**, not a claim of exact PostgreSQL floating-point outputs or exact optimizer optimality. No official Test outcome changed coefficients, resources, budget, tie-breaking, or stopping rules.

### 5.4 Physical Test metric and fixed-order evaluation

For every physical Test query, we take the actual top-level, nonaggregate PostgreSQL JSON `EXPLAIN` `Plan Rows` value in the frozen evaluation environment and compare it with its original Test truth using the frozen AreCEL zero-aware Q-error, with the specified \(r=1\) rounding convention. For nonnegative truth \(t\) and rounded estimate \(e\),
\[
Q(t,e)=
\begin{cases}
1,&t=0,\ e=0,\\
t,&t>0,\ e=0,\\
e,&t=0,\ e>0,\\
\max(e/t,t/e),&t>0,\ e>0 .
\end{cases}
\]
This piecewise rule must not be replaced by a logarithmic model loss or an invented epsilon correction for zero counts. Following the original analysis implementation, we report P50, P95, P99 and maximum Q-error using the same NumPy quantile conventions.

Issue #101 evaluated all **25 distinct configurations × 10,000 Test queries = 250,000 valid EXPLAIN outcomes**. Its comparison is conditional on the fixed object creation/setup policy and the frozen test workload. The physical `EXPLAIN` result is direct evidence about planner row estimates, not by itself proof that a particular MCV object was chosen; the separate source/tracing and ESS-diagnostic evidence supports claims about applied-object sequences. For configurations where Nominal and PESS choose identical sets, Test outcomes are identical under identical configurations; these are not independent victories for either model.

### 5.5 Exact offline model-level priority analysis

In #103, the 25 distinct selected sets are assessed **without PostgreSQL Test execution**: the frozen 100,000-task Train model is evaluated over every strict total priority permutation of each selected labeled resource set, **906 global permutations in aggregate**. One permutation is shared across tasks; the resulting task matchings are not resampled independently. Each order contributes according to its multiplicity, so a uniform distribution over permutations is **not** generally uniform over maximal matchings.

For each fixed \(M\), this yields modeled \(N_{\pi_0}(M)\), \(A(M)=\mathbb E_{\pi}L(M,\pi)\), \(G(M)=\max_{\pi}L(M,\pi)\), and \(P(M)=\sum_i\max_{\gamma\in\Gamma_i(M)}L_i(\gamma)\). These are read-only evaluations of previously selected sets: \(A\) and \(G\) were not newly optimized, and no resource choices were modified. #103 used exact-`Fraction` reference checks for modeled computations. The corresponding analysis resides in **open Draft PR #104** at the time of this draft; do not cite it as a merged `main` result without rechecking that PR.

### 5.6 Physical order perturbation with selected-object tracing

Issue #105 evaluates one directly observable effect of application strategy on physical estimates. For each of the **four Nominal \(B=5\)** sets, it runs two prespecified creation orders—canonical candidate-ID order and its exact reversal—while preserving the same unordered selected object set, data, fixed ANALYZE replay sample, and ordinary/MCV content fingerprints. Requested object creation order and actual OID-sorted candidate order are checked, rather than assumed. The study collected **8 configurations × 10,000 Test queries = 80,000 valid EXPLAINs** and complete per-query ESS diagnostics for selected-object and MCV-estimate sequences. It tests whether changing the priority changes choices or estimates and quantifies the paired Q-error consequences. It is not a full permutation enumeration and does not establish that reverse order is worst.

### 5.7 Counterfactual global relative-OID permutation evaluation

Issue #107 evaluates a different, explicitly **hypothetical deployment distribution**: choose one strict relative-OID order uniformly for an entire selected resource set and hold that *same order* for all **10,000 Test queries** in that physical configuration. PostgreSQL does **not** randomly draw a fresh relative-OID order per query in this experiment or by established production behavior. The primary estimand is
\[
Y_\pi(M)=\operatorname{P95}_{q\in Test}Q(q,M,\pi),
\qquad
\mu(M)=\mathbb E_{\pi\sim U(\Pi(M))}[Y_\pi(M)].
\]
This is the **mean of per-order Test P95 values**, not the P95 of per-query order-averaged Q-error.

The frozen \(B=5\) order design comprises exactly **156 selected configurations**:

| Resource-policy group | Per-set order population | Per-set selected orders | Design |
|---|---:|---:|---|
| Four 5-object Nominal sets | \(5!=120\) | \(2+22=24\) | Two #105 canonical/reverse **certainty units** plus SRSWOR 22 from residual 118, for each set |
| Two 5-object PESS sets (Census13, DMV11) | \(5!=120\) | 24 | SRSWOR 24 of 120, per set |
| Two 3-object PESS sets (Forest10, Power7) | \(3!=6\) | 6 | Full six-order census, per set |

Thus \(4(24)+2(24)+2(6)=156\). There was **no 732-arm exact physical enumeration**. The sample and seed were frozen before #107 Test measurements; the design was specified **after** investigators had observed the earlier #101/#105 summaries and should not be characterized as completely unaffected by prior exploratory exposure.

For each five-object Nominal set, let \(F\) be the mean outcome over its two fixed orders, and \(S\) the mean over the 22 randomly sampled residual orders. Its design-weighted population-mean estimator is
\[
\widehat\mu_N=\frac{2}{120}F+\frac{118}{120}S,\qquad
\widehat{\mathrm{Var}}(\widehat\mu_N)
=\left(\frac{118}{120}\right)^2\left(1-\frac{22}{118}\right)\frac{s_R^2}{22},
\]
where \(s_R^2\) is the ordinary sample variance of the 22 residual observations. For the two five-object PESS sets, \(\widehat\mu_P\) is the 24-sample arithmetic mean and its design variance estimate is \((1-24/120)s_P^2/24\). The two three-object PESS estimates are exact six-order finite-population means **conditional on the frozen Test queries**, and have zero *permutation-sampling error* by census. They may still have order-to-order dispersion.

The primary dataset contrast is \(\widehat\Delta=\widehat\mu_{\rm PESS}-\widehat\mu_{\rm Nominal}\); independent sampled designs use the sum of component design-variance estimates for the difference. Frozen intervals are approximate Student-t intervals with a \(t_{0.975,21}\) multiplier; their **95% nominal coverage is approximate, not exact**, and quantifies *only permutation selection uncertainty*. They do not include uncertainty from a new workload, dataset, ANALYZE sample, or PostgreSQL build. In particular, a zero sample variance across 24 of 120 Census13 PESS orders gives a **degenerate observed interval**, not a proof that all 120 orders yield identical results. The sampled minimum and maximum are observed sample extrema, not global bounds on all orders.

Execution was fully resolved at the fixed scientific scope: **156/156 configurations and 1,560,000 cumulative Test EXPLAIN calls**. Two distinct execution exceptions should remain transparent. **Event A:** the eight fixed #105 candidate reuses failed a retained generic raw-row identity/recomputation eligibility check, whose exact row-level failure was not preserved; the same eight frozen order arms were measured anew rather than substituted. It is incorrect to infer that the source archive was corrupted. **Event B:** 12 three-object PESS arms initially stopped **before EXPLAIN** because a validator incorrectly expected five selected objects; a separately authorized continuation completed only those 12 original arms (120,000 EXPLAINs), without replacing or adding orders. The other 144 arms had completed in the first run. These engineering events did not change the estimand, frozen order population or final 156-arm schedule.

### 5.8 Evidence limits and reproducibility

All scientific statements are conditioned on their declared data, queries, eligible statistics families, budget proxies, and PostgreSQL build. Mathematical relations such as \(A(M)\leq G(M)\leq P(M)\) are **model-internal and fixed-\(M\)**. The pairwise-maximal-matching correspondence is **source-derived conditional on A1–A4**, with a scoped instrumented fixture confirming specific application paths. #101/#105/#107 are **experimentally observed physical** Plan Rows and diagnostics. No inference is made about physical runtime speedups, additive measured maintenance time, complete coverage of arbitrary PostgreSQL behavior by \(\Gamma_i(M)\), statistical independence of taskwise worst cases, or universal PESS superiority. Test evaluation was not used to improve resource choices.

**Reproducibility boundary:** Exact code, experiment protocols, frozen resource IDs/seeds, data and sample checksums, source commits, per-arm status, and compact findings are maintained in the versioned experiment directories. Irreplaceable query-level raw observations and run manifests remain in the separately identified runtime archives **outside Git**, with SHA-256 identities documented in reports; the Git history alone does not contain those measurement bytes. This section synthesizes completed work and creates no additional experimental artifact.

---

## Editorial provenance and review questions (not paper prose)

Primary evidence: [#99 Train report](../../experiments/add-only-greedy-issue99/train-sweep-report-v2.md), [#99 frozen resources](../../experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json), [#101 Test findings](../../experiments/arecel-test-generalization-issue101/findings-v1.md), [#103 Draft PR #104](https://github.com/1951123/ess-research/pull/104), [#105 stress findings](../../experiments/oid-order-stress-test-issue105/findings-v2.md), [#107 protocol v2](../../experiments/oid-uniform-priority-issue107/protocol-v2.md), and [#107 completed findings v2](../../experiments/oid-uniform-priority-issue107/findings-v2.md).

Review before manuscript integration: (1) Are we sufficiently explicit that #103 and #107 estimate different things? (2) Are #107 order weights, finite-population correction and approximate interval interpretation preserved? (3) Are claims of reproducibility limited to the *actually retained* raw artifacts, with the reuse failure's unknown root cause left unresolved? (4) Does the narrative keep modeling as the principal contribution and never promote a fixed or randomized OID policy to the original motivation?
