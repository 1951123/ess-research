# Stage 1C: PG pairwise-MCV admissibility and composition

Status: **completed bounded audit; restricted-gate classification inconclusive**.

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

## Observed result (Issue-owned run v8)

The formal run used `/tmp/ess-issue40-stage1c-v8` as its private runtime root;
raw logs and PostgreSQL data remain outside Git.  It completed with 340 query
observations and 28 composition records.  All 340 observations had a finite,
strictly positive numeric pre-clamp trace and no missing trace lines.

The original matching ledger passed for 312 observations and reported 28
failures.  A post-run audit now derives task-specific candidate eligibility
from the exact executed SQL and the pinned PostgreSQL 16.14 selector source.
All 28 old failures are reclassified as
**INCONCLUSIVE_OUTSIDE_RESTRICTED_GATE**: they use `q_tail`/`e12`, but `e12`
requires `Aspect` and `Slope` while the exact `q_tail` SQL has no `Aspect`
predicate.  The built MCV payload therefore does not establish that `e12` was
an admissible edge for this task.  The original observations are preserved;
the 28 failures are not claimed as model-limitations counterexamples.

The audit found zero unmapped selected statistic OIDs.  It records the
clause-index crosswalk and per-candidate rejection reason in
`eligibility-reclassification-summary.json`.  The crosswalk is a conservative
syntactic eligibility check, not a replacement for planner candidate-
consideration traces; therefore it does not upgrade the 28 cases to a proven
restricted-gate violation.

The 340-row redacted classification ledger is committed as
`eligibility-reclassification-ledger.jsonl`; its SHA-256 and the SHA-256 values
of the preserved `observations.jsonl` and fresh v2 derived crosswalk are in the
summary.  The reclassification tool uses exclusive-create output paths and
refuses to overwrite an existing derived artifact.

All 28 composition records were in the positive pre-clamp domain.  The
single-resource product is retained only as a tested reconstruction heuristic:
it matched the disjoint pair and parallel cases to floating-point/decimal
residuals near zero in this run, while the overlap, star, and path cases were
not multiplicative.  The largest absolute relative residual was
`0.213781318891745591...` for `q_path_disjoint`.  These are **experimentally
observed** only for the pinned PG build, table/sample identity, inputs, GUCs,
and frozen query/resource set; they do not establish a general PostgreSQL
composition identity.

Protocol caveat: the manifest's preregistered `simple_clause_rule` used the
word "equality", but the immutable canonical SQL actually contains range and
inequality comparisons.  The runner executed those hash-pinned clauses
verbatim and made no equality-only inference; this report therefore does not
claim equality-only coverage.  The discrepancy is retained as a fixture
limitation rather than repaired after observation.

See `result-report.md`, `result-summary.json`, and `run-commands.txt` for the
scrubbed evidence summary and reproduction command.  The raw server log hash
and input hashes are recorded there; raw logs are not committed.

