# Issue #101 — official AreCEL test generalization

- Evidence label: **experimentally_observed_postgresql_measurements**.
- Frozen source commit: `c1ae2bad9851d870e02066e9e10934ae89735e7d`.
- Run ID: `20261025T-issue101-full-test-v1`; raw observations SHA-256: `9f899272213555e319c82576f795d4206779a215e97977eea6e124e128ae4e51`.
- PostgreSQL 16.14, Issue #99 fixed samples, full source tables, and per-column/per-extstats target 300 were used.
- AreCEL zero-aware Q-error with static `r=1`; P50/P95/P99 use NumPy median/percentile semantics; Max uses NumPy max.
- The results compare Plan Rows and do not establish parity with AreCEL's published learned-estimator environment.
- Runtime evidence: `/home/wqts/ess-runtime/ess-research/issue101/runs/20261025T-issue101-full-test-v1`; manifest `run-manifest.json`; compact raw observations `raw-observations.jsonl.gz` (3,284,286 bytes).
- Completed in 144 seconds; peak allocated bytes: 3,000,217,600 (2.79 GiB); the frozen hard cap was 20 GiB.
- Schedule: 25 unique configurations × 10,000 queries = 250,000 Plan Rows calls; all 250,000 rows are valid, with no unresolved result. Six concurrent read-only `psql` clients shared the one stable cluster for each dataset; configurations and datasets were serialized.
- Full source tables were imported: Forest10 581,012 rows; Census13 48,842; DMV11 11,591,877; Power7 2,075,259.
- Pickle boundary: trusted archive deserialization instantiated the split containers; the runner indexed only the `test` workload and labels. It did not index, serialize, or use `train`/`valid` label values.
- Zero accounting over unique configuration/query observations: both-zero 0; estimate-zero/truth-positive 0; truth-zero/positive-estimate 16,587; all other valid rows had both values positive. These cases use AreCEL's pinned zero rules.

## forest10

Status: **COMPLETE**

| Objective | Budget | Selected set | Valid / total | P50 | P95 | P99 | Max |
|---|---:|---|---:|---:|---:|---:|---:|
| nominal | 0 | `Empty` | 10000 / 10000 | 1.21595 | 17 | 71 | 9364 |
| pess | 0 | `Empty` | 10000 / 10000 | 1.21595 | 17 | 71 | 9364 |
| nominal | 2 | `e01_06,e02_07` | 10000 / 10000 | 1.18926 | 14.9208 | 63.01 | 9364 |
| pess | 2 | `e01_06,e02_07` | 10000 / 10000 | 1.18926 | 14.9208 | 63.01 | 9364 |
| nominal | 3 | `e01_06,e02_07,e03_04` | 10000 / 10000 | 1.19157 | 14 | 62.1288 | 9364 |
| pess | 3 | `e01_06,e02_07,e03_04` | 10000 / 10000 | 1.19157 | 14 | 62.1288 | 9364 |
| nominal | 4 | `e01_06,e02_07,e02_08,e03_04` | 10000 / 10000 | 1.1932 | 14 | 62.1288 | 9364 |
| pess | 4 | `e01_06,e02_07,e03_04` | 10000 / 10000 | 1.19157 | 14 | 62.1288 | 9364 |
| nominal | 5 | `e01_06,e02_07,e02_08,e03_04,e06_08` | 10000 / 10000 | 1.1945 | 13.5842 | 62.1288 | 9364 |
| pess | 5 | `e01_06,e02_07,e03_04` | 10000 / 10000 | 1.19157 | 14 | 62.1288 | 9364 |

Paired per-query PESS-versus-Nominal Q-error counts:

| Budget | Pair status | PESS lower | PESS higher | Tie | Unresolved |
|---:|---|---:|---:|---:|---:|
| 0 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 2 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 3 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 4 | COMPLETE | 222 | 361 | 9417 | 0 |
| 5 | COMPLETE | 413 | 636 | 8951 | 0 |

## census13

Status: **COMPLETE**

| Objective | Budget | Selected set | Valid / total | P50 | P95 | P99 | Max |
|---|---:|---|---:|---:|---:|---:|---:|
| nominal | 0 | `Empty` | 10000 / 10000 | 1.40252 | 18.5515 | 58 | 1635 |
| pess | 0 | `Empty` | 10000 / 10000 | 1.40252 | 18.5515 | 58 | 1635 |
| nominal | 2 | `e02_03,e04_06` | 10000 / 10000 | 1.25 | 8 | 24.181 | 1635 |
| pess | 2 | `e02_03,e04_06` | 10000 / 10000 | 1.25 | 8 | 24.181 | 1635 |
| nominal | 3 | `e01_05,e02_03,e04_06` | 10000 / 10000 | 1.23955 | 7 | 17.5014 | 103 |
| pess | 3 | `e01_05,e02_03,e04_06` | 10000 / 10000 | 1.23955 | 7 | 17.5014 | 103 |
| nominal | 4 | `e01_05,e02_03,e04_06,e06_08` | 10000 / 10000 | 1.21708 | 6.48989 | 17.0013 | 103 |
| pess | 4 | `e00_11,e01_05,e02_03,e04_06` | 10000 / 10000 | 1.23131 | 6.47755 | 16.0008 | 79 |
| nominal | 5 | `e01_05,e02_03,e04_06,e04_08,e06_08` | 10000 / 10000 | 1.19815 | 6.25 | 16.0008 | 103 |
| pess | 5 | `e00_11,e01_05,e02_03,e04_06,e07_12` | 10000 / 10000 | 1.23095 | 6.28369 | 16 | 79 |

Paired per-query PESS-versus-Nominal Q-error counts:

| Budget | Pair status | PESS lower | PESS higher | Tie | Unresolved |
|---:|---|---:|---:|---:|---:|
| 0 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 2 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 3 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 4 | COMPLETE | 1086 | 710 | 8204 | 0 |
| 5 | COMPLETE | 1587 | 1271 | 7142 | 0 |

## dmv11

Status: **COMPLETE**

| Objective | Budget | Selected set | Valid / total | P50 | P95 | P99 | Max |
|---|---:|---|---:|---:|---:|---:|---:|
| nominal | 0 | `Empty` | 10000 / 10000 | 1.19907 | 83.4833 | 3230.25 | 79775 |
| pess | 0 | `Empty` | 10000 / 10000 | 1.19907 | 83.4833 | 3230.25 | 79775 |
| nominal | 2 | `e00_05,e01_04` | 10000 / 10000 | 1.11605 | 29.2684 | 669.943 | 8433 |
| pess | 2 | `e00_05,e01_04` | 10000 / 10000 | 1.11605 | 29.2684 | 669.943 | 8433 |
| nominal | 3 | `e00_05,e01_04,e04_07` | 10000 / 10000 | 1.10995 | 26.1825 | 576.04 | 8433 |
| pess | 3 | `e00_05,e01_04,e02_03` | 10000 / 10000 | 1.11417 | 27 | 531.025 | 3263 |
| nominal | 4 | `e00_05,e01_04,e01_07,e04_07` | 10000 / 10000 | 1.1062 | 23.6727 | 416.067 | 8433 |
| pess | 4 | `e00_05,e01_04,e02_03,e06_07` | 10000 / 10000 | 1.11137 | 26.8561 | 531.025 | 3263 |
| nominal | 5 | `e00_05,e01_04,e01_07,e02_03,e04_07` | 10000 / 10000 | 1.10428 | 22.226 | 274.549 | 3263 |
| pess | 5 | `e00_05,e01_04,e02_03,e06_07,e08_10` | 10000 / 10000 | 1.11137 | 26.8561 | 531.025 | 3263 |

Paired per-query PESS-versus-Nominal Q-error counts:

| Budget | Pair status | PESS lower | PESS higher | Tie | Unresolved |
|---:|---|---:|---:|---:|---:|
| 0 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 2 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 3 | COMPLETE | 2350 | 1084 | 6566 | 0 |
| 4 | COMPLETE | 2745 | 1729 | 5526 | 0 |
| 5 | COMPLETE | 1531 | 1774 | 6695 | 0 |

## power7

Status: **COMPLETE**

| Objective | Budget | Selected set | Valid / total | P50 | P95 | P99 | Max |
|---|---:|---|---:|---:|---:|---:|---:|
| nominal | 0 | `Empty` | 10000 / 10000 | 1.06706 | 15.0024 | 223.309 | 156427 |
| pess | 0 | `Empty` | 10000 / 10000 | 1.06706 | 15.0024 | 223.309 | 156427 |
| nominal | 2 | `e00_01,e03_06` | 10000 / 10000 | 1.04925 | 10.0002 | 154.03 | 156427 |
| pess | 2 | `e00_01,e03_06` | 10000 / 10000 | 1.04925 | 10.0002 | 154.03 | 156427 |
| nominal | 3 | `e00_01,e02_04,e03_06` | 10000 / 10000 | 1.04877 | 9.95763 | 136.052 | 158693 |
| pess | 3 | `e00_01,e02_04,e03_06` | 10000 / 10000 | 1.04877 | 9.95763 | 136.052 | 158693 |
| nominal | 4 | `e00_01,e00_03,e02_04,e03_06` | 10000 / 10000 | 1.04857 | 10 | 141.508 | 158693 |
| pess | 4 | `e00_01,e02_04,e03_06` | 10000 / 10000 | 1.04877 | 9.95763 | 136.052 | 158693 |
| nominal | 5 | `e00_01,e00_03,e01_02,e02_04,e03_06` | 10000 / 10000 | 1.04868 | 9.84495 | 134.529 | 158693 |
| pess | 5 | `e00_01,e02_04,e03_06` | 10000 / 10000 | 1.04877 | 9.95763 | 136.052 | 158693 |

Paired per-query PESS-versus-Nominal Q-error counts:

| Budget | Pair status | PESS lower | PESS higher | Tie | Unresolved |
|---:|---|---:|---:|---:|---:|
| 0 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 2 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 3 | IDENTICAL_FROZEN_SELECTIONS | 0 | 0 | 10000 | 0 |
| 4 | COMPLETE | 352 | 443 | 9205 | 0 |
| 5 | COMPLETE | 727 | 826 | 8447 | 0 |

## Scope limits

The comparison is conditional on the pinned AreCEL archive, PostgreSQL source/build, fixed samples and selected target. Statistics target 300 follows Issue #99 and the explicit researcher decision; AreCEL's public Justfile uses 10000, so exact published-environment parity is not claimed. The frozen selections remain train-only heuristic outputs; this evaluation does not retune resources or prove which statistics object a PostgreSQL plan used.

## Interpretation

The frozen train choices show mixed official-test behavior. B=0 and B=2 use identical Nominal/PESS sets in every dataset, and B=3 also uses identical sets for Forest10, Census13 and Power7; their paired observations are exact ties. Where the frozen sets differ, every paired comparison contains both lower and higher PESS Q-errors, with the full counts above. Dataset-level P50/P95/P99/Max patterns also vary by budget; no single policy is uniformly better across the four datasets. The results are descriptive for this fixed official split and do not establish statistical significance or an unseen-template claim.
