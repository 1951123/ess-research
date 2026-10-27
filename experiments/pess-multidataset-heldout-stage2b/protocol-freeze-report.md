# Stage 2B formal outcome protocol freeze

Evidence label: **Proven as a protocol artifact; experimentally observed only
for the input/workload scan.** This report and `protocol-v4.json` were created
before any formal Stage 2B PostgreSQL held-out outcome collection.

## Frozen boundary

`protocol-v4.json` is the formal outcome-free contract. It freezes the
archive-first source identity, dataset schemas and candidate/OID names, the
validation-only calibration task rule, the test eligibility rule, the cohort
IDs, resource budgets, methods, metric definitions, repetition count, run
limits, and fail-closed policy.

The protocol generator reads only the archive-first `workload.json` files. It
does not open `truth.json`; no test cardinality, test estimate, MCV payload,
latency, or held-out model loss is used in eligibility, grouping, or cohort
selection. Validation truth is permitted only after this commit, for the
predeclared calibration tasks.

## Eligibility and cohort

The formal test eligibility rule is exactly two predicates, on two distinct
source columns, using one of `=`, `<`, `<=`, `>`, `>=`, or `[]`, with the two
columns exactly matching one predeclared pairwise candidate. This is stricter
than the prior `>=2` shape screen. Equality-only is not imposed because the
Forest10 workload has no equality predicates in the prepared source; forcing
that rule would make Forest10 unavailable rather than provide a valid paired
study.

The frozen cohorts are:

| Dataset | strict eligible test records | frozen IDs | calibration IDs |
|---|---:|---:|---:|
| Forest10 | 146 | 60 (10 per candidate) | 6 |
| Census13 | 52 | 52 (all eligible) | 6 |

The Forest10 cohort is disjoint from the 60 unique Stage 1A test IDs. The
protocol records each selected ID, source index, source-SQL hash, candidate,
and normalized/exact fingerprint hashes, but no truth value.

## Group overlap limitation

Normalized SQL-template fingerprints are shared across train/valid/test in
both datasets. Among strict pairwise records, the audit reports 32 shared
template groups for Forest10 and 11 for Census13. Exact fingerprint overlap is
zero for Forest10 and present for Census13 (35 groups). These overlaps are
explicitly retained as leakage diagnostics. The selected query IDs are
therefore descriptive paired observations, not group-independent population
samples; no population-level or group-independent generalization claim is
allowed.

## Post-freeze execution boundary

Only after this protocol commit may the runner use validation truths and
validation-only PostgreSQL calibration to produce model inputs and select
Empty/Nominal/PESS sets. Test outcomes are then measured in the frozen ID
order. Every requested statistic, positive MCV payload, trace-selected OID,
claimed-clause record, sample identity, and positive pre-clamp estimate must be
retained in separate ledgers. Any missing or ambiguous item blocks that
dataset/run; hard cases are not silently dropped.

This remains a descriptive real-PostgreSQL study. The proxy budget is not a
generic maintenance cost, and the experiment cannot establish universal PESS
dominance, real-scheme containment, maximal-matching coverage for arbitrary
queries, latency benefit, or statistical significance.

## Reproduction

```text
source /home/wqts/.bashrc
PYTHONPATH=src .venv/bin/python \
  experiments/pess-multidataset-heldout-stage2b/freeze_outcome_protocol.py \
  --output experiments/pess-multidataset-heldout-stage2b/protocol-v4.json
```

Observed protocol SHA-256: `54867e0bf3ca116b044d77da14efe1b12d06851af522cfbeb49af14ae33733ad`.
