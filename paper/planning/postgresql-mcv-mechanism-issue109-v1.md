# Section 4 draft — A Scoped PostgreSQL MCV Mechanism (Issue #109)

**Status:** independent English review draft following merged Sections 1–3; do not replace `paper/main.tex` yet. **Claim hierarchy:** general strategy uncertainty is the original modeling motivation; this section gives a **conditional PostgreSQL 16.14 instantiation** and previously observed evidence, not the motivation's origin. No new PG execution or measurement.

## 4. A Scoped PostgreSQL MCV Mechanism

### 4.1 Why inspect a real estimator?

Our formulation in Sections 2 and 3 is deliberately estimator-agnostic: it distinguishes an installed set \(M\), prescribed complete admissible schemes \(\Gamma_i(M)\), and any strategy choosing among them. It does not require a particular DBMS or the existence of a random runtime decision. Nevertheless, it is important to establish that overlapping-resource choice is more than a mathematical possibility. We therefore examine a restricted, version-pinned application path for multivariate most-common-value (MCV) extended statistics in PostgreSQL 16.14. The goal is to show when a *fixed* source-level selector induces a maximal matching and how changing the fixed priority order can alter the selected objects. We do not claim that this mechanism describes arbitrary queries, joins, other statistic kinds, or every component of PostgreSQL cardinality estimation.

### 4.2 Source-level choice and claim boundaries

For the scoped simple single-relation AND selectivity path, `clauselist_selectivity_ext` can invoke the multivariate MCV estimator with a list of clauses not yet estimated. Within that path, `statext_mcv_clauselist_selectivity` repeatedly calls `choose_best_statistics`, chooses a suitable built MCV object, estimates covered clauses, and marks them as consumed before considering the next object. In `choose_best_statistics`, candidates are ranked by their coverage of currently usable clauses and the number of statistical keys; if these criteria tie, iteration order determines which tied candidate is visited first. For the relevant catalog, `RelationGetStatExtList` provides a list ordered by statistics-object OID. Thus, under the prerequisites stated below, this OID order can act as the deterministic priority among overlapping two-column MCV candidates. This is **source-derived**, not an assertion that PostgreSQL randomly changes order between executions.

Version-pinned source anchors:
- [`clausesel.c`: `clauselist_selectivity_ext`](https://github.com/postgres/postgres/blob/REL_16_14/src/backend/optimizer/path/clausesel.c#L119-L188)
- [`extended_stats.c`: `choose_best_statistics`](https://github.com/postgres/postgres/blob/REL_16_14/src/backend/statistics/extended_stats.c#L1225-L1321)
- [`extended_stats.c`: `statext_mcv_clauselist_selectivity`](https://github.com/postgres/postgres/blob/REL_16_14/src/backend/statistics/extended_stats.c#L1696-L1879)
- [`relcache.c`: `RelationGetStatExtList`](https://github.com/postgres/postgres/blob/REL_16_14/src/backend/utils/cache/relcache.c#L4857-L4934)
- [`plancat.c`: `get_relation_statistics`](https://github.com/postgres/postgres/blob/REL_16_14/src/backend/optimizer/util/plancat.c#L1439-L1535)

### 4.3 Conditions for a labeled maximal-matching correspondence

We state sufficient conditions, not a characterization of all valid PostgreSQL inputs. Fix one cardinality-estimation task for a single base relation:

- **A1 — clause/attribute correspondence.** Each relevant clause is a supported, non-pseudoconstant MCV-compatible predicate involving exactly one distinct ordinary table attribute; there is one such clause per relevant attribute. Exclude OR, expression predicates, multi-attribute predicates, and repeated-attribute clauses.
- **A2 — candidates and build state.** Each eligible resource is an already-built, two-key MCV statistics object covering two attributes of that relation, both represented in the same initially unestimated compatible clause list. Parallel resources covering the same attribute pair retain separate identities.
- **A3 — no upstream or external interference.** The required privilege, relation, inheritance and build checks pass; no other estimator has consumed the relevant clauses before the scoped MCV loop, and the eligible list is precisely \(M\cap\mathcal E_i\).
- **A4 — ranking and tie.** At every selection step, an eligible two-key object whose two endpoints remain free matches two distinct unestimated clauses. All such objects tie under the applicable source ranking, so their relative priority is the fixed candidate-list/OID order.

Represent every eligible MCV object by its own labeled edge between the two attributes it covers, obtaining the multigraph \(H_i[M]\). Let \(P_i(M;\prec_{\rm cat})\) be the set of selected objects in this restricted loop with fixed catalog priority \(\prec_{\rm cat}\).

**Proposition 3 (source-derived, conditional).** Under A1–A4, \(P_i(M;\prec_{\rm cat})\) is an **inclusion-maximal matching** of \(H_i[M]\).

*Proof sketch.* When the loop selects an object, both corresponding single-attribute clauses become consumed, precluding future selection of any overlapping two-key object. Consequently the selected edges are pairwise endpoint-disjoint. If a remaining edge were disjoint from the selected edges at termination, both clauses it covers would remain eligible and unconsumed, contradicting the loop's termination condition. Therefore no edge can be added and the matching is maximal. \(\square\)

For a single task, if the tie order can be varied over *all abstract strict total orders* of candidate edges, any maximal matching can be induced by placing its edges first: every such edge is selected, while maximality blocks the rest. Hence the collection of abstract priority-induced outputs equals \(\operatorname{MaximalMatchings}(H_i[M])\) under A1–A4. **Three essential restrictions:** (i) a fixed physical catalog induces only its current order, not a randomized set of possible outputs; (ii) all abstract permutations need not be physically available without changing a catalog; and (iii) different tasks' worst matchings may require incompatible global orders. Therefore this single-task order-completeness statement does *not* establish an exact cross-task physical uncertainty set or make \(P(M)\) a bound on arbitrary PostgreSQL outputs.

### 4.4 An observable path witness

Consider the four-attribute path with available objects \(s_{AB},s_{BC},s_{CD}\). Its two maximal matchings are \(\{s_{AB},s_{CD}\}\) and \(\{s_{BC}\}\). The frozen fixture-level PostgreSQL 16.14 trace tested two creation orders using DEBUG1 instrumentation on an isolated PostgreSQL development build. In phase A, object creation order AB, BC, CD gave catalog OIDs 16387–16389 and selected \(\{AB,CD\}\), consuming clause indices 0,1,2,3. Phase B created BC, AB, CD (OIDs 16390–16392) and selected \(\{BC\}\), consuming indices 1,2. Both executions terminated with no eligible candidate, and all six per-phase object observations had built MCV data. These observations corroborate the *scoped matching mechanism*, not estimator-loss factorization or equal sampling across rebuilding. The instrumentation itself was added to the project-specific PostgreSQL development build; it should not be presented as functionality of unmodified upstream PostgreSQL.

See [conditional proof and exact source scope](../../notes/pg-mcv-maximal-matching-correspondence.md), [fixture report and evidence](../../experiments/pg-tracing/runs/20261017/report.md), and the independently maintained PostgreSQL instrumentation provenance documented therein.

### 4.5 Controlled effects on physical cardinality estimates

A later official held-out order-stress experiment [#105] held each of the four **Nominal B=5 unordered resource sets** fixed while rebuilding the same five two-column MCV objects in the prespecified canonical or exact-reverse order. The physical experiment used PostgreSQL 16.14, 10,000 frozen official AreCEL Test queries per dataset and arm, and the same controlled data and replayed ANALYZE samples. It verified OID ordering, built objects, per-object MCV-content fingerprints and relevant settings across paired arms. The experiment completed **8 configurations and 80,000 EXPLAIN calls**, with complete MCV selection/estimate diagnostics.

| Dataset | Canonical Test P95 Q-error | Reverse Test P95 Q-error | Reverse relative change | Query pairs with changed MCV selection/estimate sequence |
|---|---:|---:|---:|---:|
| Forest10 | 13.584167 | 14.000000 | +3.06% | 4,813 / 10,000 |
| Census13 | 6.250000 | 8.000000 | +28.00% | 4,474 / 10,000 |
| DMV11 | 22.225957 | 36.004444 | +61.99% | 4,596 / 10,000 |
| Power7 | 9.844947 | 9.806852 | −0.39% | 4,898 / 10,000 |

The table shows a **controlled order-dependent physical effect**, not a universal improvement or harm from reversing the order. It does not show that the reverse is the worst permutation or that matching-level loss accurately predicts the size of the physical Q-error difference. These comparisons concern actual PostgreSQL top-level `Plan Rows` and the official benchmark's **zero-aware Q-error**, not the positive pre-clamp log loss used for selection. The specific full-order and resource-set distribution studied separately in [#107] is introduced in the experimental protocol, not inferred from this two-order stress test.

### 4.6 Implications for the general optimization model

The source-level path and controlled order contrasts establish a concrete mechanism through which *the same unordered collection of objects* can have more than one relevant application outcome when the priority relation differs. This supports treating scheme selection as a separate modeling dimension of ESS. It does **not** prove that the prescribed \(\Gamma_i^{\rm MM}(M)\) contains the real possible schemes for all PostgreSQL tasks; nor does it imply that the actual system draws OID permutations uniformly, that tasks choose matchings independently, or that a worst-case model loss bounds future physical Q-error. Under knowledge of a stable catalog and source behavior, a nominal policy may be appropriate; under weaker policy knowledge, a conservative admissibility-based objective poses a different optimization question. The choice between them is a modeling commitment whose empirical consequences are evaluated subsequently.

---

## Review notes (not manuscript prose)

1. **Claim classes:** Propositions from source **conditional on A1–A4**; tracing and the 80,000-EXPLAIN stress test **experimentally observed**; physical containment/algorithmic guarantees **unproved**.
2. **Evidence separation:** The early path fixture was instrumented and compared two creation orders, but did not isolate MCV sample contents across object rebuilds. The later #105 study controlled replayed sample and per-object MCV-content hashes; do not collapse them into one experiment.
3. **Model/physical separation:** Section 3's exact priority enumeration belongs to offline *Train-model* loss; #105 figures are *physical held-out* P95 Q-errors; #107's uniform global priority evaluation is a later explicit counterfactual, not actual PG production randomness.
4. **Source references:** The line anchors above are from the frozen [correspondence note](../../notes/pg-mcv-maximal-matching-correspondence.md) for PostgreSQL REL_16_14; verify exact citations/typesetting on manuscript integration. No new source-level theorem is claimed.
5. **Next manuscript integration step:** Keep the existing LaTeX formulation unchanged until consistency of Section 1–4 and verified literature citations is reviewed.
