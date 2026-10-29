# Attempt 1 diagnosis: OID-to-candidate attribution bug

**Run ID:** `20261029Tissue133-forest10-b5-nominal-matched`

**Recorded outcome:** `INCOMPLETE` for the runner's full-diagnostics gate.

The arm completed all 10,000 EXPLAIN calls. All 10,000 rows have valid Plan Rows and recomputable Issue #101 Q-errors. The physical pre-Test checks passed: exactly five B5 objects in the frozen random-01 projection order, one fixed-sample ANALYZE, matching ordinary-column statistics and matching candidate-ID-keyed MCV state/content against both saved ALL arms.

The diagnostic parser marked 6,648 rows `UNKNOWN_SELECTED_STAT_OID`. The defect was in the B5 runner: its live OID map used string keys, while Issue #105's parser looks up integer `stat_oid` values. The runtime raw archive retains those integer OIDs and event fields; it was not edited. The saved catalog audit maps the five B5 OIDs (`16387`–`16391`) to the five frozen candidate IDs, and every observed MCV event OID is present in that catalog map. This permits an offline candidate-ID remapping for the observed events and query-level comparison.

The original `ESS Diagnostics.Status` value was overwritten by `UNKNOWN_SELECTED_STAT_OID` in the parsed rows and was not separately retained. It cannot be reconstructed from the saved rows, so the repaired analysis will identify observed MCV events but will not claim that the original diagnostics status was complete on all 10,000 queries. The original run manifest, raw archive and initial findings remain preserved.

- Raw archive: `$ESS_RUNTIME_PARENT/ess-research/issue133/runs/20261029Tissue133-forest10-b5-nominal-matched/raw-observations.jsonl.gz`, 924,394 bytes, SHA-256 `43a4ee6e53106768cef26fefa2b797ed948199451f2ac431f9040cde881ef0b4`.
- Catalog audit SHA-256: `56eedc5b22b819a69497ab2f384f0c1d7ab33d7c9a4bdc75f147613740114618`.
- Resource record: 5.935 seconds wall time, 197,906,432 peak allocated bytes, 53,147,361,280 minimum free bytes. No other PostgreSQL instance was running or touched.

No retry was issued: the authorized maximum was 10,000 Test EXPLAIN calls, which this attempt consumed. The existing observations are being analyzed offline without changing the frozen arm, inputs, metrics or raw archive.
