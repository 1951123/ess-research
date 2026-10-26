# Issue #105 — execution amendment v1

This amendment records implementation details required by the official execution authorization in Issue comment 6397763178. It does not change datasets, frozen Nominal B=5 sets, treatment orders, query split, PostgreSQL source, planner settings, targets, metric, or stopping rules in protocol v1.

## Frozen overlap audit

For each set, an endpoint conflict is an unordered pair of selected statistics that share at least one column. A conflict endpoint is a column incident to at least two selected statistics.

| Dataset | Selected-statistic conflict pairs | Distinct conflict endpoints |
|---|---:|---:|
| Forest10 | 3 | 3 |
| Census13 | 3 | 3 |
| DMV11 | 3 | 3 |
| Power7 | 4 | 4 |

The runner recomputes these counts from the candidate map whose canonical digest is pinned by Issue #99; it stops before Test EXPLAINs if a count or B=5 selection differs.

## Per-arm physical-state gates

The Issue #101 pinned helper configures an arm by dropping the candidate extended statistics for that table, iterating the requested candidate-ID sequence to issue CREATE STATISTICS and target-300 statements, then replaying the supplied fixed sample through ANALYZE. Before that arm's Test EXPLAIN batch, the Issue #105 runner independently verifies:

- source CSV hash, full-table row count, relation OID, relation file node, and ordered column/type descriptor; the row count, OID, file node, and descriptor are re-read after the arm's sample replay;
- fixed sample bytes/hash and sample header (PostgreSQL 16.14, target 90,000, row count, natts, relation OID/identity);
- that all and only the five requested statistics exist on the relation, in the requested OID-sorted order, with the expected columns, MCV kind, target 300, populated payload, and nonempty MCV list;
- equality of ordinary-column-statistics SHA-256 fingerprints and each candidate's MCV values/frequencies/base-frequencies SHA-256 across canonical and reverse arms.

The second arm is not queried if its state fails these checks. A mismatch leaves the run incomplete; no Issue #101 estimates are substituted. The table is loaded once per dataset in one run-local cluster and remains read-only between the two configurations.

## Per-query instrumented selection evidence

The fixed source supports the existing EXPLAIN option ESS_DIAGNOSTICS with JSON format. The runner uses EXPLAIN (FORMAT JSON, SUMMARY OFF, ESS_DIAGNOSTICS true) while retaining the Issue #101 planner GUCs and the same top-level Plan Rows/Q-error procedure. It preserves the MCV selection, claimed-clause, and MCV-estimate event types, maps each event OID through that arm's verified catalog audit, and stores compact event fields (including the reported MCV selectivities) with the query-level raw record. It checks that the reported event count matches the JSON event array. The option is instrumentation in the pinned EXPLAIN path; it does not change planner settings or query text. Diagnostic status is retained independently from Plan Rows status, and worker stderr is retained outside Git when present.

Per-query interpretation distinguishes changed selected-object sequences from changed MCV-estimate event sequences. The report cross-tabulates Q-error changes against MCV-estimate sequence changes; this remains a scoped diagnostic association, not a general causal claim.

## Runtime envelope

Datasets and configurations run serially. Each stable configuration uses six read-only planner clients, with no DDL or data writes during query batches. The fresh PostgreSQL build uses the Issue #101 source and build flags. The run uses Issue #101's disk early-stop at 20,401,094,656 bytes and hard cap at 21,474,836,480 bytes; no wall-time limit is added. No individual query retries or outcome-driven filtering are performed. Raw per-query observations and worker logs remain under the external Issue #105 runtime run directory; Git retains the compact report and its provenance only.
