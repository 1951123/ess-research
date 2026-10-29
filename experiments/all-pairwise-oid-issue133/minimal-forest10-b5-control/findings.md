# Forest10 ALL versus matched Nominal B5

**Comparison status:** `QERROR_COMPARISON_COMPLETE_WITH_DIAGNOSTIC_STATUS_LIMIT`.

This is a fixed-workload installed-set comparison. It uses the frozen ALL random-01 configuration as the primary comparator and the Issue #99 Nominal B5 set created in random-01's shared-candidate relative order. The five shared candidates' relative priority is matched; the 40 extra ALL candidates can still precede and interact with them. This is not an all-order average and does not prove that a particular object blocked another.

## Frozen selection and order

- B5 candidate IDs: `e01_06, e02_07, e02_08, e03_04, e06_08`.
- B5 CREATE/OID order: `e02_08, e03_04, e02_07, e01_06, e06_08`.
- B5 order SHA-256: `6aba403c6bd839e0f20059f0793f11322886dc0fcf3af811d1a8b4fc04d9b088`.
- ALL random-01 projection: `e02_08, e03_04, e02_07, e01_06, e06_08`; ALL random-02 projection: `e02_07, e03_04, e06_08, e02_08, e01_06` (unmatched secondary comparison).

## Physical configuration and integrity

- PostgreSQL 16.14 source: `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`.
- B5 CREATE / target / ANALYZE: 5 / 5 / 1.
- Five-object catalog and actual OID order: `PASS`.
- Fixed sample SHA-256: `95670277a138f577a7e21eb1567e0f6e1bce1ac489c10907c4a5662577d1aff8`; ordinary-column stats match both ALL arms.
- All five candidate-ID keyed MCV payload states, counts, and fingerprints match both ALL arms: `True`.
- B5 payload states: {"POPULATED": 5}.
- Run cost: 5.935 s wall time; peak run-directory allocation 197906432 bytes; minimum free space 53147361280 bytes; 6 EXPLAIN clients.

## Test Q-error

All three configurations use the same 10,000 official query IDs/truths and Issue #101 zero-aware Q-error/NumPy quantiles. The B5 run produced 10,000 valid Plan Rows and Q-errors.

| Configuration | P50 | P95 | P99 | Mean |
|---|---:|---:|---:|---:|
| ALL random-01 (primary) | 1.1804512559972935 | 15.0 | 65.01000000000022 | 6.687501968656185 |
| ALL random-02 (unmatched secondary) | 1.1794969657076213 | 15.0 | 63.01000000000022 | 6.708283813517734 |
| Nominal B5 matched to random-01 | 1.1904948609896286 | 14.0 | 61.506200000000135 | 6.490653490329585 |

Primary contrast: `P95(ALL random-01) - P95(B5) = 1.0`. Positive means ALL has higher/worse P95 Q-error.

## Paired query comparison (ALL random-01 minus B5)

- Plan Rows differed on 4539/10,000 queries.
- ALL Q-error was lower on 2124, higher on 2415, and unchanged on 5461 queries.
- Per-query Q-error delta (ALL−B5): n=10000, mean=0.19684847832660063, min=-256.0, P05=-0.40019387519196237, median=0.0, P95=1.0733830816665046, max=201.0.
- Observed MCV selection/estimate sequences differed on 7766/7766 queries.
- P95 rank-window union: 283 queries; 134 Plan Rows changes and 134 Q-error changes.

### Shared B5 object use (observed events)

| Candidate ID | ALL random-01: queries selected / estimated | B5: queries selected / estimated |
|---|---:|---:|
| e01_06 | 101 / 101 | 3684 / 3684 |
| e02_07 | 56 / 56 | 880 / 880 |
| e02_08 | 377 / 377 | 3748 / 3748 |
| e03_04 | 369 / 369 | 3653 / 3653 |
| e06_08 | 148 / 148 | 350 / 350 |

ALL-only candidates appeared in selected MCV events for 7766 queries and in estimation events for 7766 queries (union 7766).

### Largest Q-error changes in the predeclared P95 neighborhood

| Query ID | ALL Plan Rows / Q-error / selected IDs | B5 Plan Rows / Q-error / selected IDs | Δ Q-error (ALL−B5) |
|---|---|---|---:|
| `arecel:forest10:test:006667` | 1 / 71.0 / `e02_03, e04_07` | 5 / 14.2 / `e02_08, e03_04` | 56.8 |
| `arecel:forest10:test:005819` | 9 / 47.666666666666664 / `e02_06, e01_03` | 31 / 13.838709677419354 / `e02_08, e01_06` | 33.82795698924731 |
| `arecel:forest10:test:007681` | 3 / 14.666666666666666 / `e02_03, e04_07, e01_08` | 1 / 44.0 / `e02_08, e03_04` | -29.333333333333336 |
| `arecel:forest10:test:007807` | 12 / 13.833333333333334 / `e01_07` | 4 / 41.5 / `` | -27.666666666666664 |
| `arecel:forest10:test:009452` | 5 / 17.6 / `e01_07` | 2 / 44.0 / `` | -26.4 |
| `arecel:forest10:test:008719` | 1 / 37.0 / `e02_06, e01_07, e03_08` | 3 / 12.333333333333334 / `e02_08, e01_06` | 24.666666666666664 |
| `arecel:forest10:test:006113` | 30 / 37.8 / `e06_07, e01_04` | 83 / 13.662650602409638 / `e01_06` | 24.13734939759036 |
| `arecel:forest10:test:002128` | 1 / 35.0 / `e02_06, e04_07, e01_03` | 3 / 11.666666666666666 / `e02_08, e03_04, e01_06` | 23.333333333333336 |
| `arecel:forest10:test:002105` | 81 / 15.222222222222221 / `e02_06, e01_07` | 32 / 38.53125 / `e02_08, e01_06` | -23.30902777777778 |
| `arecel:forest10:test:006480` | 7 / 37.0 / `e06_07, e01_04, e03_08` | 18 / 14.38888888888889 / `e03_04, e01_06` | 22.61111111111111 |
| `arecel:forest10:test:000406` | 2 / 17.0 / `e02_06, e03_04` | 1 / 34.0 / `e02_08, e03_04` | -17.0 |
| `arecel:forest10:test:002584` | 7 / 28.571428571428573 / `e06_07, e01_04, e03_08` | 17 / 11.764705882352942 / `e03_04, e01_06` | 16.80672268907563 |

## Attempt history and diagnostic limitation

The single authorized arm completed 10,000 EXPLAINs in run `20261029Tissue133-forest10-b5-nominal-matched`. The execution runner marked that run `INCOMPLETE` because its in-memory OID map used string keys, while the diagnostic parser looked up integer OIDs. The raw archive SHA-256 is `43a4ee6e53106768cef26fefa2b797ed948199451f2ac431f9040cde881ef0b4`. A deterministic offline remap used the saved same-arm catalog audit; it did not change raw data or rerun queries.

The initial failure and its evidence are preserved in [attempt diagnosis](attempts/20261029Tissue133-forest10-b5-nominal-matched/attempt-diagnosis.md), [initial findings](attempts/20261029Tissue133-forest10-b5-nominal-matched/findings.md), [run manifest](attempts/20261029Tissue133-forest10-b5-nominal-matched/run-manifest.json), and [catalog audit](attempts/20261029Tissue133-forest10-b5-nominal-matched/catalog-audit.json). The original extension diagnostics status for 6,648 rows was overwritten by the parser error and was not separately retained. Candidate IDs are deterministically recovered for all stored numeric OIDs, but the original extension status is not inferred; event-sequence frequencies are therefore counts of retained/observed events.

## Interpretation and limits

For this fixed Forest10 workload, ALL random-01 P95 was higher than matched B5 by 1.0. This supports the scoped claim that installing all 45 candidate definitions produced a higher Test P95 than the frozen five-object Nominal subset under the matched shared-object priority and verified physical states. It does not identify which extra object caused the difference or establish a blocking mechanism. ALL random-02 is descriptive only because its five-object projection differs.

No confidence interval or significance test is reported for this fixed finite workload. The two ALL arms and B5 arm are fixed configurations, not a sample for estimating performance over all OID orders.
