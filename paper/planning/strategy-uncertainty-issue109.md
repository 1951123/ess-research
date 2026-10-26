# Paper argument outline — estimator strategy uncertainty (Issue #109)

**Status:** standalone research-paper planning memo for review; not an amendment to, or replacement of, [paper/main.tex](../main.tex).
**Evidence status:** synthesis of frozen train models, source-derived conditional propositions, and completed PostgreSQL experiments; no new measurements or resource selection.
**Research question:** Under a resource-maintenance budget, how should extended statistics be selected when the estimator's application/selection policy among overlapping candidates is uncertain?
**Proposed framing:** optimization modeling with a scoped PostgreSQL instantiation, not a claim of a novel global-optimum solver or unconditional PESS superiority.

## 1. One-page thesis and narrative arc

**Thesis.** The decision to install an *unordered* set of extended statistics does not, by itself, determine which overlapping candidates a cardinality estimator will apply to a query. The resulting *estimator-strategy uncertainty* is an optimization-relevant information gap, distinct both from variation in the statistical sample/data and from train-to-test workload generalization. Nominal and PESS are different responses to what is known about that choice policy. A restricted PostgreSQL 16.14 MCV selector provides a concrete, source-grounded mechanism through which order can matter; held-out physical results show consequential, dataset-dependent trade-offs, not universal dominance by either objective.

**Motivating path.** Suppose the selected, unordered pairwise MCV objects cover attribute pairs AB, BC, and CD. The conflict/path graph admits two *inclusion-maximal* matchings: {AB, CD} and {BC}. They may yield different cardinality estimates even though the installed set and the underlying data/sample are unchanged. A greedy application policy prioritizing BC induces the latter; prioritizing AB or CD induces the former. The resource-selection decision therefore needs an explicit model of admissible *complete estimation schemes* rather than silently treating each created object as independently applied.

**Chronology and causal discipline.** The project's original motivation was unknown/inaccessible scheme selection among overlapping estimator resources, leading to a budgeted pessimistic selection formulation; it was **not** inferred retrospectively from the later PostgreSQL OID experiments. First define the model and its information assumptions; next contrast fixed-policy Nominal with task-wise PESS; only then introduce PostgreSQL's OID-ordered tie behavior as one subsequently validated instance. A hypothetical uniform relative-OID permutation distribution is an *evaluation counterfactual*, not a stochastic mechanism claimed for production PostgreSQL and not the origin of the PESS objective.

**Scope of contribution.** (C1) Make estimator-application uncertainty explicit while preserving a general estimator-agnostic formulation. (C2) Explain the pointwise relationships among fixed-policy, shared-global-priority, and task-wise-adversarial losses, including incompatible taskwise worst cases. (C3) Establish a conditional mapping to pairwise MCV maximal matchings using PostgreSQL 16.14 source and scoped runtime evidence. (C4) Synthesize frozen training selection, exact offline permutation-model calculations, and held-out physical Test results to quantify the accuracy/robustness trade-off. These are *modeling and evidence* contributions; do not claim globally optimal selected sets, all-query PostgreSQL model equivalence, actual latency gains, or a new algorithmic complexity result in this memo.

**Narrative sequence for a reader:** (i) an unordered set can support competing applications; (ii) characterize the uncertainty by admissible schemes; (iii) define selection objectives according to policy knowledge; (iv) specify how the same greedy procedure selects sets on Train only; (v) inspect PostgreSQL's scoped OID tie mechanism; (vi) compare model-level priority risks with real held-out Plan Rows/Q-error; (vii) interpret mixed findings and boundary conditions.

## 2. Title and abstract skeleton

**Preferred title:** *Extended Statistics Selection under Estimator Strategy Uncertainty*.

**Alternatives:** *Beyond Resource Selection: Strategy Uncertainty in Extended Statistics Optimization*; *Budgeted Robust Extended Statistics Selection: Models and PostgreSQL Evidence*.

**Abstract skeleton (claims remain scoped):**
Extended-statistics selection is typically expressed as choosing resources under a maintenance budget. Yet when candidate statistics overlap, an unordered installed set may permit multiple estimation schemes, and a fixed resource decision need not uniquely determine the resulting estimates. We formalize this estimator-strategy uncertainty using task-dependent admissible schemes and compare a fixed-priority nominal objective with a task-wise pessimistic objective. For a pairwise-MCV instantiation, we relate inclusion-maximal matchings to priority-induced schemes and establish pointwise bounds between expected, globally worst, and task-wise worst training-model losses. Source analysis and controlled experiments in PostgreSQL 16.14 confirm that statistics application order can change selected objects and held-out cardinality estimates under stated conditions. Across four frozen AreCEL workloads, training-model and physical Test analyses show dataset-dependent differences between the resource choices, including a trade-off between fixed-policy accuracy and counterfactual order sensitivity. These findings motivate policy-aware ESS optimization without asserting universal superiority of pessimistic selection.

## 3. Formal problem, assumptions, and four risks

### 3.1 General interface versus structured instance

- **Tasks:** a finite Train index set \(\mathcal T\), task weights \(w_q>0\), true cardinalities \(n_q\geq0\), positive references \(T_q=\max\{1,n_q\}\). A general task is an *estimation context*, not necessarily a whole SQL statement or an arbitrary plan node.
- **Decision:** finite candidate resource universe \(\mathcal E\), one *unordered global* selected set \(M\subseteq\mathcal E\), and budget \(\operatorname{Maint}(M)\leq B\), \(\operatorname{Maint}(\varnothing)=0\). In the **generic** model, maintenance cost is not presumed additive/monotone. The actual frozen structured experiment uses an explicitly additive *proxy* \(\sum_{e\in M}\bar m_e\leq B\); this is not a physical ANALYZE-runtime identity.
- **Admissible schemes:** \(\Omega_q\) is a universe of complete estimation schemes, with prescribed nonempty \(\Gamma_q(M)\subseteq\Omega_q\); every admitted scheme uses resources from \(M\). \(\Gamma_q(M)\) is not presumed nested as \(M\) grows. The real possible scheme family \(\mathcal R_q(M)\) need not equal, or even be contained in, the prescribed family without additional evidence.
- **Structured instance:** a candidate pairwise MCV resource \(e\) is a *labeled edge* joining its two attributes. A task \(q\) has statically applicable candidates \(\mathcal E_q\subseteq\mathcal E\), graph \(H_q[M]=(V_q,M\cap\mathcal E_q)\), and
  \[
  \Gamma_q(M)=\operatorname{MaximalMatchings}(H_q[M]).
  \]
  Different labeled objects may share endpoints (and even an endpoint pair). A matching uses no attribute twice; **maximal** means that no further available edge can be added, **not** maximum-cardinality. For an edgeless graph, the empty matching is admissible.
- **Loss:** for the frozen structured *Train* model, an illustrative positive pre-clamp estimate is \(\widehat n_q(\gamma)=n_q^0\prod_{e\in\gamma}r_{q,e}>0\), with \(\alpha_q=\log(n_q^0/T_q)\) and \(b_{q,e}=\log r_{q,e}\), yielding
  \[
  L_q(\gamma)=w_q\left|\alpha_q+\sum_{e\in\gamma}b_{q,e}\right|.
  \]
  Use the **already-frozen** coefficients, transforms, quantization, applicability and exact-Fraction evaluation semantics from #99/#103 rather than recomputing a new loss. For brevity, \(L_q\) includes the task weight. This *model loss* is not PostgreSQL rounded/clamped Plan Rows Q-error.

### 3.2 Priority-induced matching and objectives

Let \(\Pi(M)\) be all \(|M|!\) strict total orders of labeled resources in \(M\) (one order is used **globally across all tasks**). For each task, \(\gamma_q(M,\pi)\) is the deterministic greedy inclusion-maximal matching obtained by scanning applicable resources in the restriction of global order \(\pi\), admitting an edge iff both endpoints are still free. Let
\[
L(M,\pi)=\sum_{q\in\mathcal T}L_q(\gamma_q(M,\pi)).
\]
The frozen *Nominal* priority \(\pi_0\) is a deterministic candidate-ID order, not an observed physical PostgreSQL OID order. Define, **for the same fixed \(M\)**:
\[
\begin{aligned}
N_{\pi_0}(M)&=L(M,\pi_0),\\
P(M)&=\sum_{q\in\mathcal T}\max_{\gamma\in\Gamma_q(M)}L_q(\gamma),\\
A(M)&=\mathbb E_{\pi\sim U(\Pi(M))}L(M,\pi),\\
G(M)&=\max_{\pi\in\Pi(M)}L(M,\pi).
\end{aligned}
\]

**Roles:** The #99 selection algorithms respectively minimize \(N_{\pi_0}\) and \(P\) within their common add-only greedy search. \(A\) (risk-neutral expectation) and \(G\) (shared-global-priority worst case) are *counterfactual, read-only analytical comparators* in #103, not newly trained selection objectives in these experiments. An actual stochastic priority distribution has not been established.

**Proposition (model-internal, fixed-set bound).** If every priority-induced \(\gamma_q(M,\pi)\) belongs to the *same* frozen admissible \(\Gamma_q(M)\), and all quantities use compatible \(L_q\), then
\[
\boxed{A(M)\leq G(M)\leq P(M).}
\]
**Proof.** The mean of finitely many real losses cannot exceed their maximum, giving \(A(M)\leq G(M)\). For every global \(\pi\) and each task \(q\), membership implies \(L_q(\gamma_q(M,\pi))\leq\max_{\gamma\in\Gamma_q(M)}L_q(\gamma)\). Sum over \(q\), then maximize over \(\pi\), obtaining \(G(M)\leq P(M)\). \(\square\) If \(\pi_0\in\Pi(M)\), also \(N_{\pi_0}(M)\leq G(M)\), but there is no general ordering of \(N_{\pi_0}(M)\) and \(A(M)\).

**Nonconcurrency example.** For two tasks on the same AB–BC–CD path, suppose task 1 incurs loss 1 only under matching {AB, CD} and task 2 incurs loss 1 only under {BC}, with 0 otherwise. Task-wise \(P(M)=2\), but any *one* global order induces the same path matching for both tasks, so \(G(M)=1\). In general, PESS's independent maxima are not simultaneously realizable under one global policy.

**Permutation multiplicity.** On the path, 2 of 6 orders put BC first and induce {BC}; the other 4 induce {AB, CD}. Thus **uniform permutations are not uniform matchings**. Do not enumerate each distinct matching once and give it equal probability when computing \(A\).

**Non-implications.** The bounds concern *one fixed set*, the *same modeled losses*, and a *specified admissibility rule*. They do **not** compare \(M_N\) and \(M_P\) chosen by non-optimal greedy, imply any ranking of actual Test Q-error, or guarantee that \(\mathcal R_q(M)\subseteq\Gamma_q(M)\). A genuine physical worst-case upper bound would require that containment and aligned estimates/losses.

### 3.3 Frozen optimizer and train/deployment split

The original official AreCEL *Train* evidence for Forest10, Census13, DMV11 and Power7 selected \(M_N,M_P\) independently for budgets \(B\in\{0,2,3,4,5\}\) using the **same** add-only greedy: empty start; choose the feasible single addition with greatest *strictly positive* objective improvement; resolve ties by common resource ID; stop when no strict improvement/feasible addition remains; never swap, restart or force-fill. Equal budget *caps* do not imply equal selected counts; all 40 labeled cases completed, mapping to 25 unique within-dataset physical sets (#99 / merged #100). Neither the train losses nor the greedy method certify global optimum.

After selection, evaluate *frozen* sets on the original official AreCEL Test (10,000 queries per dataset) using **actual PostgreSQL top-level nonaggregate JSON Plan Rows**, with static \(r=1\) rounding and AreCEL's original zero-aware Q-error:
\[
Q(t,\hat t)=
\begin{cases}
1 & t=\hat t=0,\\
t & \hat t=0,\ t>0,\\
\hat t & t=0,\ \hat t>0,\\
\max(\hat t/t,t/\hat t) & t>0,\ \hat t>0.
\end{cases}
\]
Here \(t\) and \(\hat t\) use the frozen official Test truth and rounded Plan Rows, respectively. Report P50/P95/P99/Max with NumPy conventions. Hold PostgreSQL 16.14, full relation, sample replay, column/extstats target 300, and relevant planner settings fixed within comparisons. **No official Test outcome was used to choose/train resources**, refit coefficients, change budget or retune objective. Sample/data variability is controlled by replaying the same frozen ANALYZE sample; unseen-workload generalization is observed on Test, not identified with priority uncertainty. The physical setup is not represented as exact parity with AreCEL's published learned-estimator baseline.

## 4. Research questions and evidence matrix

| Question | Evidence and design | Supported claim | What it does **not** show |
|---|---|---|---|
| **RQ1.** Can order change applied statistics and physical cardinality estimates? | Conditional PostgreSQL 16.14 source analysis and scoped MCV trace; #105/merged #106, four *Nominal B5* canonical vs exact-reverse CREATE/OID orders, same MCV content/sample and 80,000 official Test EXPLAINs. | The controlled order intervention changes which MCV objects/estimate sequences are used and can materially change Plan Rows/Q-error. | Not arbitrary PostgreSQL clauses, all versions, all order pairs, or reverse being the universal worst case. |
| **RQ2.** How do fixed-policy and taskwise-pessimistic selection affect overlap and abstract priority sensitivity? | #99/merged #100 frozen Train-only resource sets; #103/[Draft PR #104](https://github.com/1951123/ess-research/pull/104) full *offline* permutation enumeration of 25 unique sets, 906 permutations, 100,000 frozen Train tasks per dataset, exact Fraction reference checks. | Some selections have nonzero priority sensitivity; two objectives create different selected structures and dataset-dependent modeled expected-loss contrasts; \(A\leq G\leq P\) holds in the model. | Not a physical PG OID probability model, not Test Q-error, not a merged #103 artifact yet. |
| **RQ3.** Under a counterfactual uniform *global relative OID* order, how do frozen sets compare in expected physical Test P95 and order sensitivity? | #107/merged #108: B5 only, 156 physical configurations (96 Nominal, 60 PESS), including fixed certainty units, simple random samples without replacement, and two six-order censuses; 1,560,000 EXPLAINs including separately authorized continuation of 12 previously pre-EXPLAIN failed arms. | Design-based estimates of mean *per-order* Test P95 and permutation spread show mixed, dataset-dependent contrasts. | Not a 732-arm/full-five-object-permutation census; not random OIDs in actual deployment, an exact confidence guarantee, or sampling uncertainty over new Test workloads. |

**Evidence taxonomy:** The fixed-\(M\) inequality and abstract matching statements are *proven/model-internal*; restricted PG selector correspondence is *source-derived, conditional*, with fixture-level trace; #101, #105 and #107 contain *experimentally observed* PG outcomes. Statements about true policy-family coverage or general deployment distributions remain *open/assumption-scoped*.

## 5. Numbers to carry into Results (all comparisons are within dataset)

### 5.1 Fixed-configuration official Test (#101; merged #102)

All 25 unique configurations (250,000 Test EXPLAINs) were completed and mapped to the 40 frozen budget/objective cases. Results are **mixed by dataset and budget**. At B5, nominal versus PESS canonical/fixed-configuration Test P95 is Forest10 **13.5842 vs 14.0000**; Census13 **6.2500 vs 6.2837**; DMV11 **22.2260 vs 26.8561**; Power7 **9.8449 vs 9.9576**. Several lower-budget selections are identical, and other budgets/metrics behave differently. Use the complete P50/P95/P99/Max tables and paired query counts in the primary report, not only the illustrative B5 slice. Do not compare unnormalized Train losses across datasets.

### 5.2 Exact offline Train-model permutations (#103)

All 25 unique sets were evaluated over a total of **906 global order permutations**; **9/25** showed nonzero modeled priority variance. The calculation reports exact mean, variance, min/max *global* loss, \(N_{\pi_0}\), PESS bound \(P\), and gaps. At B5, the difference \(\mathbb E_\pi L(M_P,\pi)-\mathbb E_\pi L(M_N,\pi)\) (not a physical Q-error difference) is approximately **+1335.15 Forest10; −1956.37 Census13; −5135.65 DMV11; +905.46 Power7**. No universally better selected set in modeled expected Train loss; these totals have different scales and must not be pooled unnormalized. The result lives in Draft PR #104 (verified *open/unmerged* at planning time), not necessarily on main.

### 5.3 Physical fixed-order stress test (#105)

B5 Nominal, *same unordered set*, canonical \(\rightarrow\) exact reverse Test P95:

| Dataset | Canonical | Reverse | Relative change |
|---|---:|---:|---:|
| Forest10 | 13.5842 | 14.0000 | +3.06% |
| Census13 | 6.2500 | 8.0000 | +28.00% |
| DMV11 | 22.2260 | 36.0044 | +61.99% |
| Power7 | 9.8449 | 9.8069 | −0.39% |

These are two prespecified orders only. Reversal is *not* claimed to be the worst order. The physical report additionally verifies matching ordinary-statistics/MCV-content fingerprints across compared arms and records changed selected/estimated MCV sequences.

### 5.4 Counterfactual uniform global relative-OID Test risk (#107)

Target estimand for a fixed \(M\):
\[
Y_\pi(M)=\operatorname{P95}_{q\in\mathrm{Test}} Q(q,M,\pi),
\quad \mu(M)=\mathbb E_{\pi\sim U(\Pi(M))}[Y_\pi(M)].
\]
The estimand is \(\mathbb E_\pi[\mathrm{P95}_q Q]\), **not** \(\mathrm{P95}_q[\mathbb E_\pi Q]\). An entire set of 10,000 Test queries experiences **one** shared global order.

For five-object Nominal, two preexisting #105 orders are fixed *certainty* units and 22 of the remaining 118 are sampled without replacement: \(\widehat\mu_N=(2/120)\overline Y_{\mathrm{fixed}}+(118/120)\overline Y_{\mathrm{sample}}\). Five-object PESS uses 24/120 SRSWOR; Forest10/Power7 three-object PESS uses *all six* orders. The original proposed 732-arm exact full evaluation was **not run**. Final evidence contains 156 complete arms after remeasuring all eight nominal certainty orders and completing the original 12 zero-EXPLAIN PESS precheck failures as a separately authorized continuation. No new order was added or redrawn.

| Dataset | Estimated Nominal \(\mu_N\) P95 | Estimated PESS \(\mu_P\) P95 | \(\widehat\mu_P-\widehat\mu_N\) | Approx. 95% interval for difference |
|---|---:|---:|---:|---|
| Forest10 | 13.8901 | 14.0000 | +0.1099 | [+0.0360,+0.1838] |
| Census13 | 7.4813 | 6.2837 | −1.1976 | [−1.5793,−0.8160] |
| DMV11 | 33.1024 | 26.8561 | −6.2463 | [−8.6379,−3.8546] |
| Power7 | 9.9283 | 9.9576 | +0.0293 | [−0.1735,+0.2322] |

Negative differences favor PESS *for this estimand*, not universally. These are design-based approximate t intervals reflecting **permutation sampling only**, not Test-query/workload uncertainty; coverage is not exact. Power7's interval includes zero. Census13 five-object PESS's 24 observed permutations all had the same P95 (zero sample variance), **not** proof that all 120 orders are invariant. Forest10/Power7 three-object PESS values are exact over their six-order permutation populations, conditional on the fixed Test workload. No significance or general-population claim follows solely from these intervals. The #107 design was specified after investigators had seen the earlier #101/#105 summaries; it is not a pristine pre-exposure confirmatory study.

## 6. Section-by-section paper-ready outline: claim / evidence / prohibition

| Section | Primary section claim and contents | Evidence to cite | Must not assert |
|---|---|---|---|
| **1 Introduction** | The unordered resource decision leaves estimation-scheme application uncertain; AB–BC–CD example; three uncertainties; RQ1–RQ3; scoped contributions and chronology. | Original [research context](../../docs/RESEARCH_CONTEXT.md), [decisions D-002/D-007](../../docs/DECISIONS.md), #109. | That the OID artifact was the original motivation; that PESS always wins. |
| **2 Problem & Formal Model** | Generic tasks/resources/admissibility/maintenance; pairwise labeled conflict graphs; inclusion-maximal matching and model loss. | Existing [formal manuscript](../main.tex), [structural notes](../../notes/structural-foundations.md). | Generic maintenance is additive; maximal means maximum cardinality; \(\Gamma\) necessarily matches real PG possibilities. |
| **3 Objectives & Algorithm** | \(N_{\pi_0},P,A,G\); bound proof, global-vs-taskwise gap, permutation multiplicity; same strict-improvement Train greedy and budgets. | D-007; #99 frozen protocol/report; #103 exact offline calculation. | Global optima, A/G were trained optimizers, or fixed-set inequalities rank selected sets. |
| **4 PostgreSQL Mechanism** | Conditional MCV ranking/consumption, OID tie behavior, fixed selector gives maximal matching; source-plus-tracing illustration. | [Correspondence proof](../../notes/pg-mcv-maximal-matching-correspondence.md), [trace report](../../experiments/pg-tracing/runs/20261017/report.md), PG REL_16_14 source; #105. | Identical behavior for unrestricted clauses, versions, or all physical plan estimates. |
| **5 Experimental Protocol** | Frozen Train selection, Test isolation, sample replay, targets/build, diagnostics/Q-error and four evaluation modes. | #99, #101, #103, #105 and #107 protocols and manifests. | New Test-guided tuning; uniform-OID as actual production randomness; equivalence to published AreCEL setup. |
| **6 Results** | Fixed-policy Test vs order perturbation vs abstract model and sampled physical expected Test risk; explain positive, negative and null comparisons. | #101/103/105/107 reports and frozen hashes. | PESS universal superiority or physical model-loss equality. |
| **7 Threats to Validity** | Policy-family misspecification; restricted task/MCV applicability; proxy budget; greedy gap; Train-vs-Test metric mismatch; distribution and interval limits; one PG version/four datasets. | Assumptions and checks in cited sources. | An unproved physical worst-case guarantee or broad cross-DBMS external validity. |
| **8 Related Work** | Automatic/statistics physical design, cardinality estimation, robust resource selection, uncertainty in estimator application. Add verified primary-source citations during manuscript drafting. | Original literature **TO VERIFY**. | Unverified “first ever” claims or conflating sampling uncertainty with policy uncertainty. |
| **9 Conclusion** | Uncertainty in estimator strategy materially affects ESS choices; objectives reflect different policy knowledge; physical results are conditional and mixed. | Mathematical model and completed experiments. | Guaranteed query runtime wins, best universal policy, or algorithmic novelty unsupported here. |

**Suggested paper visuals:** Fig. 1 AB–BC–CD conflict graph with two admissible matchings; Fig. 2 three nested/different risk definitions (fixed global, global worst, taskwise worst, with precise fixed-M captions); Table 1 notation/terminology; Table 2 Train-selected sets and overlap; Table 3 #105 physical order perturbation; Table 4 #107 expected Test P95 and intervals. Do not plot across-dataset raw Train-loss totals as though they share a calibrated unit.

## 7. Terminology to lock before drafting

| Term | Meaning | Contrast |
|---|---|---|
| **Policy/strategy uncertainty** | Which *complete scheme* among admissible options a particular estimator applies, for given installed \(M\). | Not random data/ANALYZE sampling or workload shift. |
| **Sample/data uncertainty** | Variability due to data and sampled statistics contents. | Held fixed by source data and ANALYZE replay in the physical comparisons. |
| **Train-to-Test generalization** | Accuracy of Train-selected sets on original untouched-at-selection Test queries. | Not a distribution over application orders. |
| **Resource set \(M\)** | Unordered, globally installed collection of candidate objects. | Not the ordered creation sequence or the per-query applied objects. |
| **Maximal matching \(\Gamma_q(M)\)** | Inclusion-maximal nonconflicting set of applicable edges in the *prescribed model*. | Not maximum-cardinality; not necessarily identical to PG's complete numeric estimation path. |
| **PG applied object sequence** | Source/trace-observed MCV objects actually chosen in a physical planner invocation. | Not simply the abstract matching or all created objects. |
| **Nominal \(N\)** | Loss under frozen known/assumed fixed candidate-ID priority. | Not necessarily observed OID order. |
| **Risk-neutral \(A\)** | Expected *Train-model* loss over a counterfactual global permutation distribution. | Uniform orders do not give uniform matching probabilities. |
| **Global worst \(G\)** | Largest aggregate *Train-model* loss under one shared global order. | Not independent worst order per task. |
| **Task-wise PESS \(P\)** | Sum of each task's largest admissible *Train-model* loss. | May be unattainable under one common global priority. |
| **Physical Test risk \(\mu\)** | Expected *per-order* PostgreSQL Test P95 under the chosen counterfactual OID distribution. | Different units, rounding, and estimand from \(A\) or \(P\). |

## 8. Material correctness/review questions (no new experiments authorized)

1. **Proof review — model-internal:** Confirm the manuscript's positive estimate/pre-clamp loss, labeled multigraph eligibility, exact frozen coefficients and \(\Gamma_q(M)\) are identical to the #99/#103 implementation. The fixed-set bound needs only membership and compatible losses; all-orders completeness for *individual* matchings needs the scope in the correspondence note, and does not yield a shared-global completeness proposition.
2. **Source citation — conditional:** Cite the exact PostgreSQL 16.14 control flow at [extended_stats.c](https://github.com/postgres/postgres/blob/REL_16_14/src/backend/statistics/extended_stats.c) for candidate choice and clause consumption, [relcache.c](https://github.com/postgres/postgres/blob/REL_16_14/src/backend/utils/cache/relcache.c) for OID ordering, and [clausesel.c](https://github.com/postgres/postgres/blob/REL_16_14/src/backend/optimizer/path/clausesel.c) for invoking the MCV path. Check A1–A4 in the [correspondence note](../../notes/pg-mcv-maximal-matching-correspondence.md) before upgrading any claim beyond those conditions.
3. **Evidence/implementation — observed:** Keep #105's source/OID mapping and MCV fingerprint controls distinct from #103's entirely offline model enumeration. Do not use #103 results as evidence that PG samples orders uniformly.
4. **Statistical specification — observed:** Report #107's actual no-replacement sampling design, fixed/census arms, weighted estimator and conditional approximate intervals. Document the completed 12-arm continuation and the eight fixed-arm reuse eligibility failures without diagnosing their unretained row-level exception. Zero observed PESS variance for Census13 is not universal invariance.
5. **Maintenance and evaluation validity:** Confirm budget units/proxy and the original AreCEL zero-aware metric are copied exactly when turning this outline into manuscript text. Do not silently substitute physical maintenance time, Q-error for log loss, or a new metric/split.
6. **Repository status:** As verified 2026-10-26, #100, #102, #106, #108 were merged, while #103's [PR #104](https://github.com/1951123/ess-research/pull/104) remains **Draft/unmerged** despite its completed analysis. Recheck live state at manuscript submission. Keep this proposal isolated from previous draft issues and do not merge automatically.
7. **Prior art — open citation work:** Verify original papers' assumptions and novelty comparison in Related Work before claiming any first-of-kind uncertainty model or optimizer result. This does **not** require new benchmark/PG measurements.

## 9. Primary evidence links and provenance

- [Issue #109 paper synthesis scope](https://github.com/1951123/ess-research/issues/109).
- [Research context](../../docs/RESEARCH_CONTEXT.md), [accepted decisions](../../docs/DECISIONS.md), [existing formal model](../main.tex).
- [#99 frozen selections](../../experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json), [#99 Train report](../../experiments/add-only-greedy-issue99/train-sweep-report-v2.md), [merged PR #100](https://github.com/1951123/ess-research/pull/100).
- [#101 full physical Test findings](../../experiments/arecel-test-generalization-issue101/findings-v1.md), [merged PR #102](https://github.com/1951123/ess-research/pull/102).
- [#103 offline exact Train permutation analysis, Draft PR #104](https://github.com/1951123/ess-research/pull/104) (do not link its report via main before merger).
- [#105 physical OID reversal findings](../../experiments/oid-order-stress-test-issue105/findings-v2.md), [merged PR #106](https://github.com/1951123/ess-research/pull/106).
- [#107 sampled physical permutation findings v2](../../experiments/oid-uniform-priority-issue107/findings-v2.md), [protocol v2](../../experiments/oid-uniform-priority-issue107/protocol-v2.md), [merged PR #108](https://github.com/1951123/ess-research/pull/108).
- [PG maximal matching correspondence / scoped proofs](../../notes/pg-mcv-maximal-matching-correspondence.md) and [runtime tracing](../../experiments/pg-tracing/runs/20261017/report.md).

**Change boundary:** This file is paper planning only. No Test/Train remeasurement, permutation rerun, data-dependent order choice, frozen-evidence edit, solver modification, or implied review/merge approval.
