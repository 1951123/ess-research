# Runtime validation of the pairwise MCV maximal-matching correspondence

Date: 2026-10-17 (Asia/Shanghai)

Status vocabulary follows `docs/RESEARCH_CONTEXT.md`: source-derived claims
are separated from experimentally observed results.

## Scope and source instrumentation

The experiment uses the restricted four-attribute path fixture in
`experiments/pg-tracing/trace_pairwise_mcv.sql`. The table has attributes
`a,b,c,d`, and the three candidate MCV objects cover `ab`, `bc`, and `cd`.
The fixture creates and analyzes the objects in two orders, then runs an
`EXPLAIN` whose four simple predicates are `a=7`, `b=7`, `c=7`, and `d=7`.

The PostgreSQL branch is `research/ess-mcv-trace-20261017` at
`e17bfdf0c871bec02bea8c979b29d7603772b14d`, whose parent is the official
`REL_16_14` commit
`0d1c00c624fa7367d4a895f44381887757289682`. Relative to that parent, the
branch adds only the reviewed `ESS_MCV_TRACE` `DEBUG1` calls in
`src/backend/statistics/extended_stats.c`:

1. the selected statistics-object OID and number of keys;
2. every consumed zero-based clause-list index;
3. the `candidate=none; iteration terminated` event.

The source loop initializes clause indices by iterating the planner clause
list, marks consumed clauses as unavailable, and repeats until
`choose_best_statistics` returns `NULL`. The trace therefore observes the
selector's actual selected object and claimed clauses; `EXPLAIN` output is not
used to infer the selection set.

## Experimental preconditions

The run satisfies the fixture's intended restricted assumptions as follows:

- each relevant predicate is a supported simple single-attribute equality;
- the four attributes are distinct and each has one relevant clause;
- all three candidates are two-column MCV objects on the same table;
- the catalog query reports built MCV data for all three objects in both phases;
- no additional candidate or estimator is introduced by the fixture;
- the tracing branch and isolated server are PostgreSQL 16.14;
- the actual candidate-list order differs between phases through fresh object
  OIDs, while the three endpoint pairs remain the same.

The experiment does not establish multiplicative selectivity, maintenance-cost
additivity, or order-completeness over every possible PostgreSQL query. It
tests the concrete fixed-order selector on this scoped fixture.

## Phase A: creation order `ab, bc, cd`

The catalog output in `psql.stdout.log` reports:

| name | OID | keys | MCV built |
|---|---:|---|---|
| `ess_ab` | 16387 | `1 2` | `t` |
| `ess_bc` | 16388 | `2 3` | `t` |
| `ess_cd` | 16389 | `3 4` | `t` |

The `ESS_MCV_TRACE` lines at fixture line 31 report, in order:

```text
selected_stat_oid=16387 claimed_clause_index=0
selected_stat_oid=16387 claimed_clause_index=1
selected_stat_oid=16389 claimed_clause_index=2
selected_stat_oid=16389 claimed_clause_index=3
candidate=none; iteration terminated
```

Thus the actual selected set is `{ess_ab, ess_cd}`. The claimed indices are
the four distinct simple clauses in their fixture order. The unselected
`ess_bc` object is not selected after clauses 1 and 2 have been consumed.

Graph check: `{ab,cd}` is a matching because the endpoint sets are disjoint.
It is maximal because the only remaining edge `bc` intersects both selected
edges. The trace therefore agrees with the predicted maximal matching.

## Phase B: creation order `bc, ab, cd`

The catalog output reports:

| name | OID | keys | MCV built |
|---|---:|---|---|
| `ess_bc` | 16390 | `2 3` | `t` |
| `ess_ab` | 16391 | `1 2` | `t` |
| `ess_cd` | 16392 | `3 4` | `t` |

The `ESS_MCV_TRACE` lines at fixture line 49 report:

```text
selected_stat_oid=16390 claimed_clause_index=1
selected_stat_oid=16390 claimed_clause_index=2
candidate=none; iteration terminated
```

Thus the actual selected set is `{ess_bc}`. Its endpoint set is a matching.
Both remaining edges `ab` and `cd` intersect `bc`, so no additional available
edge can be added; `{bc}` is maximal. The trace agrees with the second
predicted maximal matching.

## Result and interpretation

Both phases satisfy the scoped Proposition 1 claim in
`notes/pg-mcv-maximal-matching-correspondence.md`: the fixed selector returns
a maximal matching under the stated restricted assumptions. The observed OID
sets are exactly the expected `{ab,cd}` and `{bc}` outcomes.

The result is **experimentally observed for this fixture and environment**;
the proposition itself remains a conditional source-derived statement. The
experiment does not show that every PostgreSQL query, every statistic kind,
every predicate form, or every multicolumn statistic follows the same
matching rule. It also does not show that arbitrary abstract priority orders
are all realizable by physical object creation without changing other state.

No discrepancy was found, so no tracing or fixture correction was needed.

## Evidence files

- [`psql.stdout.log`](psql.stdout.log): SQL status, catalog OIDs, built flags,
  and `EXPLAIN` output.
- [`psql.stderr.log`](psql.stderr.log): client-visible `DEBUG1` trace lines.
- [`server.log`](server.log): server startup and complete server-side trace.
- [`environment.md`](environment.md): exact versions, isolated paths,
  commands, lifecycle result, and SHA-256 digests.

The raw files are retained as evidence and are not a substitute for the
formal assumptions in the correspondence note.
