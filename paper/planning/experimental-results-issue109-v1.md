# Section 6 — Results (Issue #109, v1)

**Status:** standalone English manuscript draft for review; follows the merged Sections 1–4 and the in-review Section 5. This synthesis uses only frozen evidence, including the merged Issue #116 Train case study. Do not interpret model loss as physical Test Q-error or uniform permutations as ordinary PostgreSQL deployment.

## 6. Results

We report results in the order dictated by the modeling question. First, we make the map from a chosen resource set to multiple admissible complete estimation schemes explicit on an actual frozen training task (RQ2). We then examine the selected sets and full-workload abstract priority sensitivity (RQ2), test whether changing a physical PostgreSQL order affects real estimation (RQ1), and finally compare frozen choices under the specified counterfactual uniform global-OID-order Test metric (RQ3). The last two outcomes do not establish that the abstract admissibility model exactly characterizes all PostgreSQL behaviors.

### 6.1 From an unordered set to distinct scheme losses: Census13 Train witness (RQ2)

The [Issue #116 read-only case study](../../experiments/ess-scheme-space-case-study-issue116/findings.md), merged by [PR #117](https://github.com/1951123/ess-research/pull/117), provides a complete task-local illustration drawn from the original Census13 **Train** population of 100,000 tasks. The selected stable task is `arecel:census13:train:000000`, chosen deterministically as the first task satisfying the frozen structural, positive-risk and small-scheme-family conditions described in Section 5. It is a **mechanistic example, not a random task and not a causal attribution of whole-workload greedy choices**.

Three task-applicable pairwise statistics resources form a triangle over the attributes `marital_status`, `relationship` and `sex`:

| Statistic | Attributes covered |
|---|---|
| `e04_06` | `marital_status` — `relationship` |
| `e04_08` | `marital_status` — `sex` |
| `e06_08` | `relationship` — `sex` |

All three candidate edges intersect pairwise. Consequently, when all three are present the inclusion-maximal matching family consists of **three singleton schemes**, not a matching containing all three objects.

The five frozen resource choices are the shared \(B=3\) selection and the separate Nominal and PESS choices at \(B=4,5\). Only task-applicable members appear below; the full installed sets include additional resources that are inapplicable to this particular task.

| Frozen set | Task-local maximal schemes \(\Gamma_i(M)\) | Frozen Nominal task loss | Frozen PESS task loss | Positive task risk? |
|---|---|---:|---:|---|
| \(M_{3,\mathrm{shared}}\) | \(\{\{\mathrm{e04\_06}\}\}\) | 0.077898 | 0.077898 | No |
| \(M_{4,\mathrm{Nom}}\) | \(\{\{\mathrm{e04\_06}\},\{\mathrm{e06\_08}\}\}\) | 0.077898 | 0.686091 | Yes |
| \(M_{4,\mathrm{PESS}}\) | \(\{\{\mathrm{e04\_06}\}\}\) | 0.077898 | 0.077898 | No |
| \(M_{5,\mathrm{Nom}}\) | \(\{\{\mathrm{e04\_06}\},\{\mathrm{e04\_08}\},\{\mathrm{e06\_08}\}\}\) | 0.077898 | 0.686091 | Yes |
| \(M_{5,\mathrm{PESS}}\) | \(\{\{\mathrm{e04\_06}\}\}\) | 0.077898 | 0.077898 | No |

For the B5 Nominal selection, exhaustive scheme losses are approximately **0.077898** for \(\{\mathrm{e04\_06}\}\), **0.651726** for \(\{\mathrm{e04\_08}\}\), and **0.686091** for \(\{\mathrm{e06\_08}\}\). The frozen Nominal priority selects the first; the unique PESS maximizing scheme is the third, giving taskwise excess modeled loss \(r_i=P_i-N_i\approx0.608193\). The taskwise loss is absolute-log error evaluated from the exact-`Fraction` reference using the **frozen `census13-clamped-log-v2` coefficient transform**. It is *not* a PostgreSQL Plan Rows Q-error measurement, and no physical OID selection is inferred from this table.

The \(B3\to B4\to B5\) sequence of **Nominal set additions** grows the number of this task's schemes from 1 to 2 to 3, **without removing its earlier scheme**. This particular observed task thus does not demonstrate the general mathematical **nonnestedness** of maximal-matching families. The \(B5\) Nominal–PESS comparison changes the installed resource set by **substitution**, not by adding a single object to the same set. The nonnestedness property is established separately, e.g. adding an entirely disjoint edge can render an old maximal matching non-maximal.

To connect the witness to the task population, under the frozen B5 Nominal Census13 set **26,998 of 100,000 Train tasks** have multiple admissible schemes. Only **10,764** have a *strictly positive* Nominal-to-PESS task-loss gap; the remaining **16,234 ambiguous tasks have zero gap**. Ambiguity is thus not synonymous with increased risk. The corresponding numbers in the B4 Nominal case are 26,998 ambiguous and 10,262 risk-positive. In the frozen B3 shared and B4/B5 PESS sets, no Train tasks have more than one task-local maximal scheme, according to this study. These descriptive counts arise from one frozen model and should not be generalized to arbitrary workloads.

| Census13 frozen set | Ambiguous Train tasks | Positive-risk Train tasks | \(\sum_i N_i\) | \(\sum_i P_i\) |
|---|---:|---:|---:|---:|
| B3 shared | 0 | 0 | 52,865.905 | 52,865.905 |
| B4 Nominal | 26,998 | 10,262 | 51,409.134 | 56,485.624 |
| B4 PESS | 0 | 0 | 52,163.364 | 52,163.364 |
| B5 Nominal | 26,998 | 10,764 | 50,347.356 | 56,821.283 |
| B5 PESS | 0 | 0 | 51,718.705 | 51,718.705 |

The whole-Train objective totals are sums of **model absolute-log losses** and correspond exactly to the preserved frozen reference fractions. The reproduction checks against #99 and #103 are agreement between pinned artifacts, not a fresh independent sample or an independent replay of raw Train inputs. These totals also make the **information trade-off** concrete: on this frozen Census13 Train collection, the B5 Nominal selection has lower *Nominal* loss (50,347.356 versus 51,718.705) but higher *PESS* loss (56,821.283 versus 51,718.705) than the B5 PESS selection. This is the intended comparison of objectives, not proof of the globally best resource set or the physical Test ranking.

### 6.2 Frozen resource selections and offline global-priority sensitivity (RQ2)

The #99 Train-only sweep evaluated both selection objectives for \(B\in\{0,2,3,4,5\}\) across all four datasets, completing **40/40 labeled cases**. All \(B=0\) and \(B=2\) Nominal/PESS selected sets coincide, and at \(B=3\) they also coincide on Forest10, Census13 and Power7. At higher budgets, several sets differ in membership and size: for example Forest10 and Power7 PESS stop at three resources for B4/B5 whereas their B5 Nominal selections use five. The greedy procedure only adds a feasible resource when it gives a strict improvement; the selected count need not equal the budget cap and the procedure does not claim global optimality.

The completed [#103 offline analysis, Draft PR #104](https://github.com/1951123/ess-research/pull/104) enumerated **906 global resource-priority permutations** across the **25 unique frozen sets**, using frozen Train-model losses and exact reference checks. **Nine of the 25** had nonzero aggregate modeled sensitivity to priority. The following B5 contrasts are differences in **expected global-permutation Train-model loss** \(A(M_{\rm PESS})-A(M_{\rm Nom})\), not Plan Rows Q-error and not cross-dataset normalized measurements:

| Dataset | B5 modeled expected Train loss: PESS − Nominal | Lower is better within this frozen model |
|---|---:|---|
| Forest10 | +1,335.154 | Nominal |
| Census13 | −1,956.368 | PESS |
| DMV11 | −5,135.649 | PESS |
| Power7 | +905.457 | Nominal |

Because \(A(M)\leq G(M)\leq P(M)\) compares **one fixed \(M\)** under the *same model*, it cannot imply a uniform ordering between separately trained \(M_{\rm Nom}\) and \(M_{\rm PESS}\). Nor does a model-global priority order specify physical OID distributions or guarantee loss values after PostgreSQL rounding/clamping. #103 remains a draft/unmerged research artifact as checked at the time this section was prepared; manuscript references should use its branch evidence until merged.

### 6.3 Fixed-priority physical held-out estimates (#101)

The frozen #101 evaluation used the original official Test split and actual PostgreSQL 16.14 top-level `Plan Rows`, applying the benchmark's zero-aware Q-error. All **25 distinct configurations** completed, giving **250,000 valid Test EXPLAINs**. Under the original fixed/canonical configuration, B5 P95 values were:

| Dataset | B5 Nominal Test P95 | B5 PESS Test P95 | Lower P95 at this fixed configuration |
|---|---:|---:|---|
| Forest10 | 13.5842 | 14.0000 | Nominal |
| Census13 | 6.2500 | 6.2837 | Nominal |
| DMV11 | 22.2260 | 26.8561 | Nominal |
| Power7 | 9.8449 | 9.9576 | Nominal |

These values are **descriptive for one fixed physical configuration** and should not be generalized to arbitrary OID orders. Results across the other budgets and metrics are mixed, and several selected sets coincide exactly. The B5 slice illustrates that resource choices minimizing a conservative **Train-model** criterion need not minimize **physical Test P95 under the particular canonical deployment order**. It does not contradict the modeled \(P(M)\) comparison or imply that Nominal always outperforms PESS.

### 6.4 Controlled PostgreSQL order changes (#105; RQ1)

To establish whether priority has a measurable physical effect, #105 rebuilt each of the four **Nominal B5 unordered sets** in canonical and exact-reverse creation/OID order. Data, fixed sample replay, settings and MCV-content fingerprints were checked to match across each pair; all **80,000 Test EXPLAINs** and selected-object/MCV-estimate diagnostics were complete.

| Dataset | Canonical Test P95 | Reverse Test P95 | Relative reverse change | Changed MCV sequence / 10,000 |
|---|---:|---:|---:|---:|
| Forest10 | 13.5842 | 14.0000 | +3.06% | 4,813 |
| Census13 | 6.2500 | 8.0000 | +28.00% | 4,474 |
| DMV11 | 22.2260 | 36.0044 | +61.99% | 4,596 |
| Power7 | 9.8449 | 9.8069 | −0.39% | 4,898 |

For the same fixed selected objects and frozen Test queries, changes in the catalog-priority intervention coincide with different applied-object/MCV-estimate sequences on thousands of query pairs. The effect on Q-error is nonuniform: even a changed selected-object sequence need not worsen a query's error, and some pairs remain tied despite changed diagnostics. Reverse is **not** established as the global worst order, nor does #105 establish equal risk under all other orders.

### 6.5 Expected physical Test P95 under a counterfactual uniform order (RQ3)

Issue #107 evaluates the frozen \(B=5\) resource sets over a prespecified **hypothetical uniform distribution on global relative-OID orders**, keeping one order shared by all 10,000 Test queries in each physical configuration. It estimates
\[
\mu(M)=\mathbb E_{\pi\sim U(\Pi(M))}
\left[\operatorname{P95}_{q\in\mathrm{Test}} Q(q,M,\pi)\right],
\]
which differs from taking the query P95 **after** averaging each query's error across orders.

The complete design contains **156 physical configurations and 1,560,000 valid Test EXPLAINs**, not the proposed 732-arm census. The four five-object Nominal sets each contribute two fixed/certainty #105 orders and 22 SRSWOR draws from their remaining 118 orders; Census13/DMV11 five-object PESS sets each contribute 24 SRSWOR draws of 120; Forest10/Power7 three-object PESS sets are complete six-order censuses. The reported intervals account only for this random *permutation sampling*, not workload/dataset/sampling variability.

| Dataset | Estimated Nominal \(\mu\) | Estimated PESS \(\mu\) | Estimated PESS − Nominal | Approx. 95% permutation-only interval |
|---|---:|---:|---:|---|
| Forest10 | 13.8901 | 14.0000 | +0.1099 | [+0.0360, +0.1838] |
| Census13 | 7.4813 | 6.2837 | −1.1976 | [−1.5793, −0.8160] |
| DMV11 | 33.1024 | 26.8561 | −6.2463 | [−8.6379, −3.8546] |
| Power7 | 9.9283 | 9.9576 | +0.0293 | [−0.1735, +0.2322] |

Negative differences favor the PESS-selected set for this **particular counterfactual estimand** on Census13 and DMV11; the positive Forest10 difference favors Nominal, while Power7's interval includes zero. Because the frozen physical outcomes refer to separately selected, not necessarily same-size sets, these comparisons describe the whole selection-and-deployment decision under a common budget cap—not an isolated causal effect of choosing a different objective while holding \(M\) fixed.

A zero PESS permutation-sampling SE on Forest10/Power7 is supported by the six-order census, conditional on the fixed Test set. Census13's five-object PESS set has zero observed variation in its **24 sampled orders**, giving a degenerate interval that does **not** demonstrate invariance over all 120. The sampled study was designed after examining earlier #101/#105 reports and should not be described as untouched confirmatory evidence. Neither the estimated expected Test P95 nor its interval is a bound derived from the abstract \(P(M)\) objective.

### 6.6 Synthesis and answer to the research questions

**RQ1:** PostgreSQL 16.14 has a source-grounded order-sensitive two-column MCV selection mechanism under explicit eligibility assumptions; controlled frozen physical comparisons show that order can change applied-object/estimated sequences and Test Q-error. The claim is conditional, not universal across arbitrary PostgreSQL estimation paths.

**RQ2:** Frozen Train-model analysis demonstrates that installing overlapping statistics can create multiple complete schemes with different losses. The actual Census13 task witness exposes the full scheme family and confirms that overlap is **not sufficient** for positive taskwise risk. Objective-specific selection changes the resources chosen, while exact offline priority enumeration yields different dataset-dependent expected modeled losses.

**RQ3:** Under an explicitly counterfactual uniform shared global relative-OID order, the sampled physical expected Test P95 comparison favors PESS on Census13 and DMV11, Nominal on Forest10, and has an inconclusive interval for Power7. This does not imply PESS consistently improves the fixed canonical configuration, arbitrary deployment policies, or future workloads.

**Overall:** The evidence supports estimator application strategy as an optimization-relevant uncertainty dimension, not a universal empirical superiority claim. The mathematical problem is formulated independently of PostgreSQL; the constrained source connection and physical observations provide practical motivation and falsifiable boundaries for the model.

---

## Review anchors (not manuscript prose)

- **Mechanism:** [Issue #116 findings](../../experiments/ess-scheme-space-case-study-issue116/findings.md) and [summary](../../experiments/ess-scheme-space-case-study-issue116/summary.json) are authoritative. The first task is chosen by a nonrandom criterion. Never claim it proves general nonnestedness; the observed B3→B4→B5 Nominal family is nested. Model coefficient transform is frozen `census13-clamped-log-v2`.
- **Comparators:** #103 is offline Train model, #101 fixed physical Test, #105 two-order physical Test, #107 sampled counterfactual physical Test; keep axes and labels separate. The exact model gap and physical P95 values cannot be divided/pooled to infer an accuracy law.
- **No overclaim:** Greedy-selected sets are not global optima; case study is not an independent Test sample; no physical worst-case coverage is established; 156 is not 732; zero sampled variance on Census13 does not imply an all-order theorem.
- **Provenance:** [#99 Train report](../../experiments/add-only-greedy-issue99/train-sweep-report-v2.md); [#101 physical findings](../../experiments/arecel-test-generalization-issue101/findings-v1.md); [#103 Draft PR](https://github.com/1951123/ess-research/pull/104); [#105 physical order findings](../../experiments/oid-order-stress-test-issue105/findings-v2.md); [#107 sampled uniform-order findings](../../experiments/oid-uniform-priority-issue107/findings-v2.md).
