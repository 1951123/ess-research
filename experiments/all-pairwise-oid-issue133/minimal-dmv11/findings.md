# DMV11 ALL MCV vs matched Nominal B5: findings

Status: **COMPLETE**. This is a fixed-workload physical comparison of three prespecified configurations, not an estimate over all OID permutations.

## Integrity and execution

- Run ID: `20261029T0300Z-issue133-dmv11-three-arm`; source commit: `45f55a02244294a8cb6c1b25ba8b3c01b9676c02`.
- Raw query archive SHA-256: `69a2202d815c1db991ffdfbfc431d2fa447ddeffc31de898d4ae87d3f5101dbe`; bytes: 6,502,206.
- Configurations: 3; EXPLAIN calls: 30,000 / 30,000.
- Execution used one isolated PostgreSQL cluster, one arm at a time, with 6 query clients.
- The full DMV11 source had 11,591,877 rows; ordinary column targets and all extended-statistics targets were 300. Fixed sample: 90,000 rows.
- PostgreSQL 16.14; source commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`. Input CSV SHA-256 `ae310972b7ac08629d135a1da7c580e3fe603bfc2e665e1969005bd481d4605a`, fixed sample SHA-256 `fc1013bb57547aaed5e15bab4de0f126ce21d0e781b5a66d7eabe21423fee249`, rendered Test SQL SHA-256 `491a665cdb080c5d5ae11456abcf308918eb7eb85c4f70c5f73999d4094becae`.
- Frozen ALL order SHA-256: random-01 `3e18988a5e28b6fedf88486ff113863780280f5d93e6a523bf6a2d29de7a3e13`, random-02 `c8aeac03b9e2e9f9b9bf90ed1e147ae85e4ba70b8744290c21731f322ef49e53`. ALL01/ALL02/B5 object counts: 55/55/5; CREATE and target-setting totals 115 each; ANALYZE runs 3.
- All configurations have 10,000 valid Plan Rows, complete diagnostics, and complete candidate-ID attribution. Catalog, OID order, table, fixed sample, ordinary stats, and shared-object MCV state checks passed.
- MCV payload states (populated / NULL) by arm: `{"dmv11-all-random-01": {"POPULATED": 55}, "dmv11-all-random-02": {"POPULATED": 55}, "dmv11-b5-nominal-matched": {"POPULATED": 5}}`. Candidate-ID-keyed payload hashes and item counts matched for all shared candidates across all three relevant comparisons.
- B5 objects in random-01 projected order: `e04_07, e00_05, e01_07, e02_03, e01_04`. The random-02 projection is `e04_07, e01_04, e02_03, e00_05, e01_07`; it differs from the matched B5 order.

## Per-configuration Q-error

| Configuration | n | P50 | P95 | P99 | Mean |
|---|---:|---:|---:|---:|---:|
| `dmv11-all-random-01` | 10,000 | 1.15109555 | 57.6052273 | 1367.53833 | 107.108946 |
| `dmv11-all-random-02` | 10,000 | 1.16320096 | 67.525 | 2085.47 | 187.157344 |
| `dmv11-b5-nominal-matched` | 10,000 | 1.11658386 | 36.0044444 | 984.075 | 32.7643871 |

## H1 — same 55-object set, two OID orders

`P95(random-02) - P95(random-01) = 9.91977273`; P99 difference = 717.931667; mean difference = 80.0483981. Plan Rows changed for 6,246 queries, Q-error changed for 6,246, selection sequence changed for 7,663; 0 had different Plan Rows but unchanged Q-error. Paired mean Q-error difference (random-02 minus random-01) was 80.0483981.

## H2 — ALL random-01 vs matched B5

`P95(ALL random-01) - P95(B5) = 21.6007828`; P99 difference = 383.463333; mean difference = 74.344559. ALL was worse on 5,074 paired queries, better on 2,384, and equal on 2,542. Plan Rows changed for 7,458; selection sequence changed for 8,846. ALL-only candidates were selected in 8,846 queries (22,711 selection events).

As a secondary descriptive contrast, `P95(random-02) - P95(B5) = 31.5205556`; random-02's projection onto the five shared candidates is not the B5 creation order, so this is not a matched-priority set comparison.

The sign of this fixed P95 contrast is consistent with ALL being worse than B5 under the matched shared-object order and audited states. It does not isolate every mechanism contributing to the set effect.

## Interpretation limits

- Random-02's B5 projection does not match the primary B5 order; interpret its ALL-vs-B5 contrast accordingly.
- Different selection sequences are descriptive evidence. This run does not record candidate ranking, predicate consumption, or blocker eligibility, so it does not prove that a worse object suppressed a better one.
- These are three fixed arms and one 10,000-query workload; no inference is made about all 55! orders or other datasets.
- Runtime: 32.4s wall; peak run-directory allocation 2.433 GiB; runner CPU 14.0s (PostgreSQL backend CPU is not separately attributed).

Query-level observations remain in the external runtime archive; the repository contains only compact summaries and the catalog audit.

## H1 query-level examples

Examples are ranked by absolute paired Q-error difference among queries with changed MCV selection sequences; descriptive only.

| Query ID | Left / right Plan Rows | Left / right Q-error | Left / right selected candidate IDs |
|---|---:|---:|---|
| `arecel:dmv11:test:008580` | 1 / 6 | 79775 / 13295.8 | `['e00_08', 'e04_10', 'e02_05']` / `['e00_05', 'e04_10', 'e01_02']` |
| `arecel:dmv11:test:004884` | 1 / 43 | 50995 / 1185.93 | `['e00_09', 'e06_07', 'e04_08', 'e05_10', 'e02_03']` / `['e04_07', 'e00_09', 'e01_06', 'e03_05', 'e02_10']` |
| `arecel:dmv11:test:008295` | 1 / 43 | 50995 / 1185.93 | `['e00_09', 'e06_07', 'e04_08', 'e05_10', 'e02_03']` / `['e04_07', 'e00_09', 'e01_06', 'e03_05', 'e02_10']` |
| `arecel:dmv11:test:001409` | 1 / 42 | 36803 / 876.262 | `['e00_09', 'e06_07', 'e04_08', 'e05_10', 'e02_03']` / `['e04_07', 'e00_09', 'e01_06', 'e03_05', 'e02_10']` |
| `arecel:dmv11:test:003411` | 1 / 14 | 31234 / 2231 | `['e00_09', 'e06_07', 'e04_08', 'e02_05', 'e01_03']` / `['e04_07', 'e00_09', 'e01_06', 'e03_05', 'e02_08']` |

## H2 query-level examples

Examples are ranked by absolute paired Q-error difference among queries with changed MCV selection sequences; descriptive only.

| Query ID | Left / right Plan Rows | Left / right Q-error | Left / right selected candidate IDs |
|---|---:|---:|---|
| `arecel:dmv11:test:000192` | 1 / 780 | 79770 / 102.269 | `['e00_09', 'e01_06', 'e04_10', 'e05_08']` / `['e00_05', 'e01_04']` |
| `arecel:dmv11:test:004516` | 1 / 773 | 79770 / 103.195 | `['e00_09', 'e01_06', 'e04_10', 'e05_08']` / `['e00_05', 'e01_04']` |
| `arecel:dmv11:test:009189` | 2 / 2703 | 56005 / 41.4391 | `['e00_09', 'e01_06', 'e04_10', 'e02_05']` / `['e00_05', 'e01_04']` |
| `arecel:dmv11:test:006609` | 1 / 26 | 51194 / 1969 | `['e04_07', 'e00_09', 'e01_06', 'e05_08']` / `['e04_07', 'e00_05']` |
| `arecel:dmv11:test:000145` | 2 / 42 | 32232 / 1534.86 | `['e04_07', 'e00_09', 'e01_02', 'e05_10']` / `['e04_07', 'e00_05']` |
