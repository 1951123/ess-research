# Stage 2A: equality-only PostgreSQL MCV eligibility gate

This directory is the sole scope for Issue #47. It contains a separately
preregistered, synthetic PostgreSQL 16.14 fixture for the restricted
pairwise-MCV/labeled-maximal-matching correspondence.

The experiment distinguishes three claims:

1. **Observed matching membership:** the selected statistic OIDs in one
   isolated run map to a matching that is inclusion-wise maximal in the
   ledger's genuinely usable graph.
2. **Abstract order completeness:** all maximal matchings are realizable by a
   freely varying abstract tie order. This is a model-internal proposition,
   not a claim that one PostgreSQL catalog realizes every order.
3. **Shared cross-task policy:** no cross-task completeness claim is made.

The selected-only `ESS_MCV_TRACE` is not treated as a complete eligibility
certificate. The runner must construct a source-indexed candidate ledger from
the pinned catalog, query crosswalk, and PostgreSQL 16.14 selector premises.
If that ledger cannot be independently reconciled with the catalog and trace,
the corresponding result is `INCONCLUSIVE` or `BLOCKED`.

The first commit containing this directory is protocol/input-only. Results,
reports, hashes, and executable runner changes belong in later commits and
must not alter the frozen manifest or fixture SQL.

## Evidence boundary

- The table and rows are generated locally from the fixed seed in
  `protocol-manifest.json`; no external dataset is required.
- Equality-only queries have one `=` predicate per distinct relevant column;
  unsupported SQL forms are negative controls and fail closed.
- A statistic is an available edge only when its catalog row is the expected
  two-key MCV object, its MCV payload is present and non-empty, and both
  endpoint clauses are present in the query crosswalk.
- A selected OID, built statistic, or `EXPLAIN` row count alone does not prove
  candidate eligibility or provide a pre-clamp numeric value.
- Maximality means inclusion-wise maximality, not maximum cardinality.

## Planned execution

Use only an Issue-owned disposable cluster and runtime root, for example:

```text
ESS_ISSUE_ROOT=/tmp/ess-issue47-stage2a-v1
PGDATA=$ESS_ISSUE_ROOT/pgdata
PGHOST=$ESS_ISSUE_ROOT/socket
PGPORT=55447
```

The pinned existing PostgreSQL build is read-only at
`/home/wqts/ess-runtime/issue38/pg-prefix`; the source repository is not
modified by this experiment. Raw PGDATA and logs remain outside Git and are
hash-recorded only.
