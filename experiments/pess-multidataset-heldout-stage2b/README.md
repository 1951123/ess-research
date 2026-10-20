# Stage 2B: multi-dataset held-out PG decision quality

## Updated Gate A handoff

The archive-first input contract is frozen in [`protocol-v2.json`](protocol-v2.json).
It supersedes the old materialized-path representation for new work; the old
`protocol.json` and Gate A v1–v7 reports remain immutable historical evidence.
New verification consumes `from ess_research.arecel import prepare` for
Forest10 and Census13 independently. It uses only the whole pinned archive in
`ESS_DATA_ROOT`; each dataset's `table.csv`, `workload.json`, `truth.json`, and
`schema.sql` live only inside that invocation's derived runtime directory.

The executable `gate_audit.py` delegates to `gate_audit_v2.py` and requires
the user-set `ESS_DATA_ROOT` and `ESS_RUNTIME_PARENT`. PG readiness arguments
are explicit; no old Issue #38 cluster or sample is reused:

```text
PYTHONPATH=src python3 experiments/pess-multidataset-heldout-stage2b/gate_audit.py \
  --pg-source /ABSOLUTE/PINNED/PG-SOURCE \
  --pg-prefix /ABSOLUTE/ISSUE-48-APPROVED-PG-PREFIX \
  --pg-build-manifest /ABSOLUTE/BUILD-MANIFEST.json \
  --output experiments/pess-multidataset-heldout-stage2b/runs/gate-a-<version>/gate-audit.json
```

The command creates a fresh Issue-48 cluster per dataset, imports the prepared
table, exports and replays a new fixed sample, creates the predeclared MCV
objects, and runs one deterministic valid-split smoke probe. `GATE_A_READY`
means only that the two-dataset input and PG infrastructure gates passed; it is
not a held-out outcome PASS, a PESS guarantee, or evidence of latency benefit.

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
