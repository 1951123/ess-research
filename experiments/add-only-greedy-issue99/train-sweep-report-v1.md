# Issue #99: official train-only greedy sweep

**Status: PARTIAL.** All four PostgreSQL collection runs completed, but one of the 40 frozen selection cases did not complete within its predeclared advisor time limit. The other 39 cases completed.

## Question and scope

The question is: for the four pinned AreCEL datasets, what add-only greedy resource sets and train objectives does the existing runner produce for Nominal and PESS at budgets 0, 2, 3, 4, and 5? The minimal experiment reused each dataset's existing 100,000-query train workload and truth, collected the frozen PostgreSQL empty/singleton observations, and ran only the 40 predeclared selection cases.

No validation/test labels or test EXPLAIN observations were used. The train-label pickle stores split values in one container: standard pickle loading reconstructs that container, then the runner explicitly dereferences `train` only; valid/test values are not explicitly indexed, saved, or used. PostgreSQL execution is source-derived and experimentally observed for the pinned versions and inputs; it does not establish universal PostgreSQL behavior.

Each worker cluster imported the full source CSV and checked the resulting row count before replaying the same fixed PostgreSQL 16.14 `ANALYZE` sample. The 90,000-tuple sample is a statistics sample, not a replacement for the base table. All collection observations are train-only. Forest10, DMV11, and Power7 use the positive pre-clamp model, whose frozen checks require finite positive baseline estimates, singleton estimates, and truth before taking logs; Census13 retains its frozen `max(1,x)` clamped-log transform. Decimal log coefficients are quantized at 1e-18 before Fraction-based objective evaluation. Displayed objectives below are rounded to six decimals; exact stored fractions, greedy traces, and resource records remain in the external runtime manifests.

## Collection results

| Dataset | Full table rows × columns | Source CSV bytes | Workers | Observations | Collection wall seconds | Peak allocated disk bytes |
|---|---:|---:|---:|---:|---:|---:|
| Forest10 | 581,012 × 10 | 22,878,434 | 12 | 1,741,931 / 1,741,931 | 1,941.784 | 2,840,223,744 |
| Census13 | 48,842 × 13 | 4,662,791 | 12 | 2,901,893 / 2,901,893 | 3,282.381 | 2,880,544,768 |
| DMV11 | 11,591,877 × 11 | 695,149,262 | 6 | 2,094,044 / 2,094,044 | 2,849.856 | 14,428,110,848 |
| Power7 | 2,075,259 × 7 | 92,498,589 | 6 | 902,535 / 902,535 | 1,055.852 | 3,093,200,896 |

The DMV11 footprint is consistent with its much larger full source table: its CSV is about 7.5 times Power7's and the imported relation has about 5.6 times as many rows. The number of columns can contribute to row width, but this experiment does not isolate a column-count effect. In particular, Census13 has more columns than DMV11 but far fewer rows and a much smaller CSV. The six-worker DMV11 run peaked at about 13.43 GiB, while the six-worker Power7 run peaked at about 2.88 GiB. These are measured whole-run peaks that include PostgreSQL build/setup and six run-local clusters, not just table bytes.

Protocol v4 used six workers, a 19-GiB early-stop threshold, a 20-GiB hard disk cap, and 7.5/8-hour wall limits for DMV11 and Power7. Both completed below those limits. Forest10 and Census13 remain pinned to the earlier v2 protocol and were not rerun.

| Dataset | Collection run | Selection run | Protocol |
|---|---|---|---|
| Forest10 | `20261025T050116Z-issue99-forest10-fee458` (code `0117e0f588475458c89c98d40f15130c793be71d`) | `20261025T053515Z-issue99-forest10-selection-c3e5b2` (code `703c826022ad4261d2104dda91c4ed186102a8fb`) | v2, SHA-256 `099df075b2d80a772e46a00d4c8201dca30e20d928479b25d00a508eacbcc9c3` |
| Census13 | `20261025T055959Z-issue99-census13-591c9d` (code `703c826022ad4261d2104dda91c4ed186102a8fb`) | `20261025T065610Z-issue99-census13-selection-ec9248` (same code) | v2, SHA-256 `099df075b2d80a772e46a00d4c8201dca30e20d928479b25d00a508eacbcc9c3` |
| DMV11 | `20261025T083515Z-issue99-dmv11-16fd8a` (code `c4a161f74fb178526426b2e23f33cddd1f3ae8df`) | `20261025T092424Z-issue99-dmv11-selection-79f148` (same code) | v4, SHA-256 `2f40b265bacc96d965b59bcdccc25c9bb73e3a4d99481a82107db0542343a9e6` |
| Power7 | `20261025T100019Z-issue99-power7-5e2aad` (code `279f824ad731432785d322d3a88731cd61d90464`) | `20261025T101855Z-issue99-power7-selection-ac09df` (same code) | v4, SHA-256 `2f40b265bacc96d965b59bcdccc25c9bb73e3a4d99481a82107db0542343a9e6` |

## Greedy selection results

`J` is the runner's summed train objective for the frozen dataset-specific model. Resource sets are the completed greedy selections. `∅` is the empty set. Unless noted otherwise, both cases in a row are COMPLETE. The cases are heuristic outputs; no global-optimum claim is made.

| Dataset | Budget | Nominal set; J | PESS set; J |
|---|---:|---|---|
| Forest10 | 0 | ∅; 237,064.729594 | ∅; 237,064.729594 |
| Forest10 | 2 | {e01_06, e02_07}; 222,467.056368 | {e01_06, e02_07}; 222,467.056368 |
| Forest10 | 3 | {e01_06, e02_07, e03_04}; 219,193.107585 | {e01_06, e02_07, e03_04}; 219,193.107585 |
| Forest10 | 4 | {e01_06, e02_07, e02_08, e03_04}; 217,839.124249 | {e01_06, e02_07, e03_04}; 219,193.107585 |
| Forest10 | 5 | {e01_06, e02_07, e02_08, e03_04, e06_08}; 217,031.863922 | {e01_06, e02_07, e03_04}; 219,193.107585 |
| Census13 | 0 | ∅; 79,483.703033 | ∅; 79,483.703033 |
| Census13 | 2 | {e02_03, e04_06}; 56,408.586262 | {e02_03, e04_06}; 56,408.586262 |
| Census13 | 3 | {e01_05, e02_03, e04_06}; 52,865.905116 | {e01_05, e02_03, e04_06}; 52,865.905116 |
| Census13 | 4 | {e01_05, e02_03, e04_06, e06_08}; 51,409.133564 | {e00_11, e01_05, e02_03, e04_06}; 52,163.364342 |
| Census13 | 5 | {e01_05, e02_03, e04_06, e04_08, e06_08}; 50,347.356473 | INCOMPLETE — advisor time cap; no completed selection/objective accepted |
| DMV11 | 0 | ∅; 268,850.366120 | ∅; 268,850.366120 |
| DMV11 | 2 | {e00_05, e01_04}; 235,810.292431 | {e00_05, e01_04}; 235,810.292431 |
| DMV11 | 3 | {e00_05, e01_04, e04_07}; 233,583.767083 | {e00_05, e01_04, e02_03}; 233,837.567748 |
| DMV11 | 4 | {e00_05, e01_04, e01_07, e04_07}; 231,416.582376 | {e00_05, e01_04, e02_03, e06_07}; 233,601.785523 |
| DMV11 | 5 | {e00_05, e01_04, e01_07, e02_03, e04_07}; 229,450.220509 | {e00_05, e01_04, e02_03, e06_07, e08_10}; 233,601.770500 |
| Power7 | 0 | ∅; 105,798.260627 | ∅; 105,798.260627 |
| Power7 | 2 | {e00_01, e03_06}; 94,039.871661 | {e00_01, e03_06}; 94,039.871661 |
| Power7 | 3 | {e00_01, e02_04, e03_06}; 93,372.374859 | {e00_01, e02_04, e03_06}; 93,372.374859 |
| Power7 | 4 | {e00_01, e00_03, e02_04, e03_06}; 92,908.128137 | {e00_01, e02_04, e03_06}; 93,372.374859 |
| Power7 | 5 | {e00_01, e00_03, e01_02, e02_04, e03_06}; 92,489.133554 | {e00_01, e02_04, e03_06}; 93,372.374859 |

PESS B=4 and B=5 completed after three additions on Forest10 and Power7 because the next greedy step had no strict objective improvement. These are complete heuristic outcomes below the requested budget, not timeouts. Census13 PESS B=5 is the sole incomplete case: its 600-second advisor limit was reached during a greedy evaluation round (outer wall 608.33 seconds), so no final selection or objective is reported for that case.

## Interpretation and limits

The two objectives agree at B=0 and B=2 on all four datasets. They first differ at B=3 on DMV11, at B=4 on Census13, and at B=4 on Forest10 and Power7 by PESS stopping with the same three-resource set it selected at B=3. This is a descriptive comparison of the frozen training objectives and these greedy runs. It does not establish held-out performance, actual PostgreSQL plan accuracy, physical maintenance savings, universal PESS dominance, or global optimality. Cross-objective reevaluation was outside the frozen case envelope and was not run.

The raw query-level observations, exact Fraction case records, coefficients, and resource measurements remain outside Git under `$ESS_RUNTIME_PARENT/ess-research/issue99/runs/`. The concise manifests' run IDs, source hashes, protocol hashes, and aggregate observation hashes identify those records. No test suite was run as part of this experiment; the executed evidence is the four collection runs and the 40 selection cases summarized above.
