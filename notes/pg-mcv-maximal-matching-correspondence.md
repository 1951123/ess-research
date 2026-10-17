# Restricted PostgreSQL MCV selection as maximal matching

Status (updated 2026-10-17): **source-grounded conditional propositions, with fixture-level PostgreSQL 16.14 runtime confirmation for two creation orders**. See [2026-10-17 experiment report](../experiments/pg-tracing/runs/20261017/report.md) and merged [research PR #4](https://github.com/1951123/ess-research/pull/4).
Scope: upstream PostgreSQL **REL_16_14**, *not* a claim about all PostgreSQL estimates or other RDBMSs.

## 1. Why this note exists

The general PESS-ESS model in [paper/main.tex](../paper/main.tex) deliberately treats the
estimator's choice of estimation scheme as unknown. The mapping
\(\Gamma_i(M)\) is a *prescribed admissibility model*, not necessarily a complete
description of the behavior of a deployed estimator.

This note proves a restricted correspondence between a source-observed greedy
MCV-selection mechanism and maximal matchings. It separates:

1. A fixed PostgreSQL execution with a fixed catalog / OID order.
2. A family of hypothetical greedy executions with *arbitrary* candidate orders.
3. The mathematical uncertainty model that admits all maximal matchings.

Only (2) and (3) are set-equal under the assumptions below. The actual
PostgreSQL choice in (1) is one member of that set.

## 2. Scoped assumptions

Fix one cardinality-estimation task from a single base relation \(t\) for
which the normal, implicitly ANDed, single-relation restriction-selectivity
path invokes the extended-statistics MCV selector. Assume:

- **A1 (simple predicate / attribute bijection).** Each relevant clause is a
  supported, non-pseudoconstant, MCV-compatible predicate referring to exactly
  one *distinct* user attribute of \(t\). There is exactly one such clause per
  relevant attribute. No OR, expression predicates, multiple clauses per
  attribute, or multi-attribute clause.
- **A2 (candidate eligibility).** Each candidate \(e\in\mathcal E_i\) is a
  successfully *built* two-attribute MCV statistics object on \(t\); its two
  attribute clauses are in the same compatible, initially unestimated clause
  list. Candidates have no expression keys. Distinct objects may have equal
  endpoint pairs, and remain distinct edges.
- **A3 (uninterfered MCV path).** No other estimator consumes the relevant
  clauses before the MCV loop. The relevant relations, inheritance flags and
  privilege checks permit all candidate MCV objects; the applicable list is
  exactly \(M\cap\mathcal E_i\). Any other clauses or statistics are excluded
  from this isolated model.
- **A4 (greedy tie order).** Within this scoped set, all eligible objects have
  two keys and, when both remain uncovered, match two attributes. Thus the
  source's ranking by remaining covered attributes and then by number of
  keys ties among all currently eligible objects. The selector resolves ties
  by the candidate-list order, which is fixed during one execution.

These conditions are intentionally stronger than "any PostgreSQL query with
two-column MCV statistics". They are sufficient conditions, not a claim that
all other instances violate maximal-matching semantics.

Let \(H_i[M]=(V_i,E_i[M])\) be the edge-labeled multigraph of available
candidate statistics, with endpoints equal to covered attributes. A matching
is a set of edges with pairwise disjoint endpoints. A matching is *maximal*
when no further available edge can be added to it; it need not have maximum
cardinality.

## 3. Proposition: the fixed selector returns a maximal matching

**Proposition 1 (soundness of the restricted greedy selector).**
Under A1–A4, if \(P_i(M;\prec_{\rm cat})\) is the set of MCV statistics selected
by the PostgreSQL 16.14 MCV loop under its fixed candidate-list order, then

\[
P_i(M;\prec_{\rm cat})\in
\operatorname{MaximalMatchings}(H_i[M]).
\]

**Proof.** Initially each eligible edge corresponds to two unestimated,
distinct single-attribute clauses. Selecting an edge marks *both* covered
clauses estimated and removes them from subsequent MCV matching consideration.
An edge can therefore be selected at a later iteration only if neither of
its endpoints has already been covered by another selected edge. Hence the
selected edges form a matching.

By A1–A4, an available edge whose endpoints both remain uncovered scores
exactly two matched keys and can be selected, whereas an edge with fewer than
two uncovered endpoints is not selectable. The loop stops only when the
selector returns no such object. If some available edge were disjoint from
the selected matching at termination, both of its endpoint clauses would
still be unestimated, contradicting termination. Therefore the matching is
maximal. \(\square\)

This proposition is about **selected statistics objects**, not about the
numeric loss assigned to the resulting scheme, the query plan, or the
maintenance cost.

## 4. Proposition: varying the order recovers all maximal matchings

Let \(P_i(M;\prec)\) denote the same scoped greedy selection algorithm with
an arbitrary strict total order \(\prec\) on the available labeled candidates
used to break its ties.

**Proposition 2 (order-completeness).** Under A1–A4, if every such total
order is allowed,

\[
\{P_i(M;\prec):\prec\text{ a total order on }E_i[M]\}
=
\operatorname{MaximalMatchings}(H_i[M]).
\]

**Proof.** Proposition 1 proves containment from left to right. Conversely,
fix any maximal matching \(P\). Order all of its edges before all edges outside
\(P\), arbitrarily ordering within those two groups. Every edge of \(P\)
remains eligible until selected, since its endpoints are disjoint from those
of the previously selected edges of \(P\). After selecting all edges of \(P\),
every remaining edge meets an already covered endpoint, by maximality.
Therefore the greedy algorithm terminates with exactly \(P\). \(\square\)

**Important qualifications.**

- The order-completeness statement uses a freely varying abstract priority
  order. In PostgreSQL 16.14, the statistics list is normally sorted by
  statistics-object OID, so a fixed catalog gives a fixed tie order.
  Recreating objects may alter OIDs; this is not a guarantee that arbitrary
  priority orders can be realized without also affecting the system state.
- There is **no global-policy completeness claim across tasks**: several
  desired task-wise maximal matchings may require mutually incompatible
  orders of shared statistics objects. Hence
  \(\sum_i w_i\max_{P\in\Gamma_i(M)}\ell_i(P)\) can strictly exceed the worst
  aggregate loss of a single global ordering.
- Changing the query form, mixing statistic kinds, allowing compound or
  repeated-attribute clauses, skipping unbuilt candidates, or encountering
  permission restrictions can invalidate A1–A4. No result for arbitrary
  PostgreSQL selectivity calculations follows.

## 5. Supporting PostgreSQL source (REL_16_14)

1. \`src/backend/optimizer/path/clausesel.c\`,
   \`clauselist_selectivity_ext\`: single-relation extended-statistics
   invocation and handling of clauses not yet estimated.
   https://github.com/postgres/postgres/blob/REL_16_14/src/backend/optimizer/path/clausesel.c#L119-L188
2. \`src/backend/statistics/extended_stats.c\`,
   \`choose_best_statistics\`: candidate scan, coverage count,
   width tie-breaker and first-in-list tie resolution.
   https://github.com/postgres/postgres/blob/REL_16_14/src/backend/statistics/extended_stats.c#L1225-L1321
3. \`src/backend/statistics/extended_stats.c\`,
   \`statext_mcv_clauselist_selectivity\`: greedy repeat-until-none selection
   and marking covered clauses as estimated.
   https://github.com/postgres/postgres/blob/REL_16_14/src/backend/statistics/extended_stats.c#L1696-L1879
4. \`src/backend/utils/cache/relcache.c\`,
   \`RelationGetStatExtList\`: list of statistics-object OIDs sorted by OID.
   https://github.com/postgres/postgres/blob/REL_16_14/src/backend/utils/cache/relcache.c#L4857-L4934
5. \`src/backend/optimizer/util/plancat.c\`,
   \`get_relation_statistics\`: reads successfully built statistics objects
   into planner metadata.
   https://github.com/postgres/postgres/blob/REL_16_14/src/backend/optimizer/util/plancat.c#L1439-L1535

## 6. Falsification-oriented tracing plan and completed fixture check

Use a controlled 4-attribute path with statistics
\(\{s_{ab},s_{bc},s_{cd}\}\). Its maximal matchings are precisely
\(\{s_{ab},s_{cd}\}\) and \(\{s_{bc}\}\).

1. On a development PostgreSQL build with DEBUG1 tracing enabled, create the
   same three two-column MCV statistics in order **ab, bc, cd**, ANALYZE,
   record catalog OIDs and trace the selected statistic OIDs / claimed
   clause indices during EXPLAIN.
2. Drop the three statistics, recreate in order **bc, ab, cd**, ANALYZE and
   repeat. Compare outcomes with the two predicted maximal matchings.
3. Check preconditions from trace: each selected object claims exactly two
   *distinct* unestimated simple clause indices; all available candidates
   are built; no separate estimator preconsumed the relevant clauses.
4. Check selected sets are a matching and maximal in the instantiated graph.
   If not, record the exact violated precondition or counterexample.
5. Keep cardinality estimates and ANALYZE costs as **separate** experiments:
   rebuilding statistics changes OIDs and potentially samples. This trace
   alone does not prove fixed multiplicative correction factors or additive
   physical maintenance cost.

Runnable SQL fixture: [experiments/pg-tracing/trace_pairwise_mcv.sql](../experiments/pg-tracing/trace_pairwise_mcv.sql).
Instrumentation was tested on an **isolated development branch** of
`ess-postgresql`, then merged to `ess-postgresql/main` via [PR #1](https://github.com/1951123/ess-postgresql/pull/1). It must not be confused with unmodified upstream behavior.

**Observed fixture result (2026-10-17):** Phase A created ab, bc, cd (OIDs 16387–16389) and selected `{ab,cd}` with consumed clause indices 0,1,2,3; Phase B created bc, ab, cd (OIDs 16390–16392) and selected `{bc}` with indices 1,2. Both traces terminated with `candidate=none`. All six per-phase MCV object observations reported built data. Raw client and server logs are retained in [experiments/pg-tracing/runs/20261017/](../experiments/pg-tracing/runs/20261017/). This validates only the specific fixture, not universal PG behavior.

## 7. Paper claim and evidence status

- **Established from control flow under A1–A4:** Propositions 1–2.
- **Experimentally observed on one scoped PG 16.14 fixture:** two OID-dependent path outcomes and the corresponding DEBUG1 selection / clause traces; see the [recorded report](../experiments/pg-tracing/runs/20261017/report.md).
- **Not established by these propositions:** accuracy of the numeric
  estimator, empirical realism of unknown policy families, independence
  across tasks, log-loss positivity, maintenance-cost additivity,
  or optimization speedups.
