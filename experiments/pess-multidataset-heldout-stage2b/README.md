# Stage 2B: multi-dataset held-out PG decision quality

This directory is the Issue #48 experiment boundary.  Its first commit freezes
the input identities, candidate universes, selection rules, metrics, and
PostgreSQL measurement contract before any Stage 2B outcome is collected.

The frozen protocol is [`protocol.json`](protocol.json).  It is an input-only
contract, not a result report.  The prior Stage 1A Forest10 60-query cohort is
explicitly excluded from the new independent test cohort; its six-resource
manifest is retained only as a separately labelled legacy reference.

## Gate A and execution boundary

The caller must provide an explicit `--data-root` (or the already approved
`ESS_DATA_ROOT`).  No historical path, arbitrary pickle, network download,
synthetic substitute, or other project checkout is inferred.  The protocol
records exact expected source and derived-artifact hashes, but their presence
and current compatibility must be rechecked in a later Gate A audit.

Gate A is `PASS` only for a dataset whose source CSV, canonical workload,
truths, split provenance, fixed-sample contract, PostgreSQL 16.14 source
build, and trace prerequisites all validate.  A syntax-screen count from the
prior ETL reports is not runtime evidence.  If fewer than two datasets pass,
the final decision is `INCONCLUSIVE` or `BLOCKED` with the available partial
result; no second dataset may be fabricated.

Only a dedicated disposable PostgreSQL cluster may be used.  Raw data,
PGDATA, logs, and large traces stay outside Git under an Issue-owned runtime
root.  Observation directories must be newly versioned and exclusive-created;
they must never overwrite Stage 1A or Stage 1C evidence.

## Evidence boundary

The planned outputs distinguish:

- model-level exact/Fraction reference calculations;
- solver-reported floating-point status, without silently calling it an exact
  global certificate;
- actual PostgreSQL pre-clamp traces and catalog payload/selection evidence;
- physical maintenance observations, which remain separate from the additive
  proxy budget.

No result in this directory can establish a universal PESS ranking, universal
PostgreSQL scheme containment, additive maintenance cost, or latency benefit.
