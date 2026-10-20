# Stage 1C: PG pairwise-MCV admissibility and composition

Status: **protocol frozen before PostgreSQL observations**.

This directory is the sole in-repository scope for Issue #40.  It audits a
bounded PostgreSQL 16.14 fixture against the prescribed pairwise labeled-edge
model.  It does not claim that every PostgreSQL query follows the model, that
all maximal matchings are physically realizable in one catalog, or that the
task-wise PESS objective is a shared-policy worst case.

The first commit containing this directory is input/protocol-only.  The
manifest fixes the candidate labels, task/query IDs, graph topologies,
creation orders, repetitions, source/build identity, GUCs, and numeric
tolerances before any new PG run.  Later commits may add measurement scripts,
scrubbed summaries, hashes, and a status report, but must not change the
frozen protocol after observing results.

## Evidence boundary

- The Forest10 CSV, canonical query stream, and fixed sample are immutable
  read-only inputs under `ESS_DATA_ROOT`; their hashes are in
  `protocol-manifest.json`.
- The fixture is real Forest10 data, but the selected candidate graph and
  query subset are a bounded construction, not representative workload
  evidence.  Results are labeled **experimentally observed** only for the
  recorded table, snapshot, source build, and query path.
- `ESS_MCV_TRACE` is the authority for selected statistic OIDs and claimed
  clause indices.  `EXPLAIN` Plan Rows are never treated as pre-clamp values.
- Positive log residuals are formed only when the recorded pre-clamp values
  are finite and strictly positive.  Zero, missing-MCV, clamp, and
  instrumentation failures remain separate outcomes.
- A failed prerequisite blocks the corresponding claim.  No proxy result is
  substituted for missing trace or numeric signal.

## Planned execution

The measurement run will use only the issue-owned runtime root, for example:

```text
ESS_ISSUE_ROOT=/tmp/ess-issue40-stage1c
ESS_DATA_ROOT=/home/wqts/ess-data
PGDATA=$ESS_ISSUE_ROOT/pgdata
PGHOST=$ESS_ISSUE_ROOT/socket
PGPORT=<manifest-selected-free-port>
```

The PostgreSQL fork is copied from the pinned `ess-postgresql` commit into the
issue runtime for an out-of-tree build with `ESS_MCV_NUMERIC_TRACE`; the
external source worktree is not edited.  The run will import the frozen sample
before each controlled `ANALYZE`, record the catalog/OID/source-identity
ledger, execute each frozen query in isolation, collect the trace by log
offset, and stop the owned cluster before handoff.

## Offline verifier

`matching_verifier.py` contains only labeled graph checks.  Its tests are
independent of PostgreSQL and distinguish inclusion-wise maximality from
maximum-cardinality matching.  It does not make a claim about which
statistics PostgreSQL can realize.

