# Issue #105 — official OID-order stress test

**Evidence label: Experimentally observed**, conditional on the frozen AreCEL Test split, the four Nominal B=5 selections, the two prespecified creation orders, and PostgreSQL 16.14 at the pinned source.

## Result

Run `20261025T130222Z-issue105-official-v2` completed all 8 configurations and 80,000 EXPLAIN calls. Each arm returned valid Plan Rows for all 10,000 Test queries; all 80,000 ESS diagnostics had status `complete`. There were no missing plans or unresolved paired queries.

| Dataset | Order | Valid / total | P50 | P95 | P99 | Max | Mean | Zero truth, positive estimate |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Forest10 | canonical | 10,000 / 10,000 | 1.194504 | 13.584167 | 62.128800 | 9,364 | 6.444075 | 624 |
| Forest10 | reverse | 10,000 / 10,000 | 1.185909 | 14.000000 | 63.000000 | 9,364 | 6.461628 | 624 |
| Census13 | canonical | 10,000 / 10,000 | 1.198148 | 6.250000 | 16.000769 | 103 | 2.293018 | 745 |
| Census13 | reverse | 10,000 / 10,000 | 1.201450 | 8.000000 | 20.000000 | 103 | 2.559858 | 745 |
| DMV11 | canonical | 10,000 / 10,000 | 1.104279 | 22.225957 | 274.549355 | 3,263 | 14.313765 | 799 |
| DMV11 | reverse | 10,000 / 10,000 | 1.116584 | 36.004444 | 984.075000 | 14,673 | 32.764387 | 799 |
| Power7 | canonical | 10,000 / 10,000 | 1.048675 | 9.844947 | 134.529488 | 158,693 | 61.295030 | 372 |
| Power7 | reverse | 10,000 / 10,000 | 1.051796 | 9.806852 | 125.522947 | 158,693 | 59.457455 | 372 |

For every arm, both-zero cases and estimate-zero/truth-positive cases were 0. The remaining queries had positive estimates and positive truths. The table reports the truth-zero/positive-estimate count; full per-query statuses and zero-case counts are in the external raw observations and manifest.

| Dataset | P95 reverse − canonical | P95 ratio | P50 Δ | P99 Δ | Max Δ | Mean Δ | Reverse lower / higher / tied | MCV selection / estimate sequence changed |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Forest10 | +0.415833 | 1.030612 | −0.008595 | +0.871200 | 0 | +0.017553 | 984 / 863 / 8,153 | 4,813 / 4,813 |
| Census13 | +1.750000 | 1.280000 | +0.003302 | +3.999231 | 0 | +0.266840 | 214 / 1,057 / 8,729 | 4,474 / 4,474 |
| DMV11 | +13.778487 | 1.619928 | +0.012305 | +709.525645 | +11,410 | +18.450622 | 506 / 1,703 / 7,791 | 4,596 / 4,596 |
| Power7 | −0.038096 | 0.996130 | +0.003121 | −9.006541 | 0 | −1.837575 | 873 / 924 / 8,203 | 4,898 / 4,898 |

The reverse order increased P95 by 28% on Census13 and about 62% on DMV11, increased it slightly on Forest10, and decreased it slightly on Power7. On DMV11, the reverse P99 and maximum were also higher. This is a mixed, order-specific result; reverse is not established as the worst permutation.

All 10,000 query pairs per dataset had complete diagnostics. The Q-error direction among pairs with a changed MCV-estimate sequence was:

| Dataset | Reverse higher | Reverse lower | Q-error tied despite changed sequence | Sequence unchanged and Q-error tied |
|---|---:|---:|---:|---:|
| Forest10 | 863 | 984 | 2,966 | 5,187 |
| Census13 | 1,057 | 214 | 3,203 | 5,526 |
| DMV11 | 1,703 | 506 | 2,387 | 5,404 |
| Power7 | 924 | 873 | 3,101 | 5,102 |

Per-query comparison confirmed that the selected-object and MCV-estimate sequences changed on the same query pairs in these four arms. This is query-level diagnostic association under this controlled setup; it does not establish a universal causal mechanism or predict another workload or PostgreSQL version.

## Physical-state and execution checks

- The runner recomputed the frozen endpoint-overlap counts: Forest10 3 pairs / 3 endpoints; Census13 3 / 3; DMV11 3 / 3; Power7 4 / 4.
- The actual OID-sorted IDs matched each requested CREATE sequence. Catalog OID ranges were Forest10 canonical 16387–16391 / reverse 16403–16407; Census13 16389–16393 / 16395–16399; DMV11 16389–16393 / 16399–16403; Power7 16387–16391 / 16401–16405. Full per-object mappings are in the manifest.
- All four full source tables matched their pinned CSV row counts and schema; their relation OID, file node, and descriptor stayed fixed between arms. The fixed Issue #99 sample hash/header and replay identity passed in all eight arms.
- Each arm had exactly the five selected two-column MCV statistics, target 300, populated MCV lists, and the intended OID-sorted candidate sequence. OID-to-candidate mappings and per-object hashes are in the manifest. Ordinary-column-statistics fingerprints and candidate MCV-content fingerprints matched across each dataset's two arms.
- The pinned Issue #101 planner settings (`client_min_messages=warning`, `plan_cache_mode=force_custom_plan`, `max_parallel_workers_per_gather=0`) and Q-error implementation were used, including Plan Rows rounding with `r=1` and the zero-aware rule. The complete per-query observations allow recomputation of all summaries.
- Standard trusted pickle deserialization materialized the AreCEL split containers; the adapter explicitly indexed and used only Test queries/labels. Train/valid label values were not indexed, serialized, or used.
- Six planner clients ran per configuration. Peak allocated run storage was 2,931,474,432 bytes (about 2.73 GiB), below the frozen early-stop limit of 20,401,094,656 bytes and hard limit of 21,474,836,480 bytes. No wall-time limit was set.

## Provenance and attempt history

- Successful run: `20261025T130222Z-issue105-official-v2`; source commit `5fb8053e1d9717a543a45a2bf19d4adc2c6bdb65`.
- PostgreSQL 16.14 source commit: `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; Python 3.12.3; NumPy 2.3.4. Issue #101 protocol SHA-256 `7bd11b3743c5ca0467b4268cf47e8328f2bbe500fd53cea45a8efe3eab415787`; Issue #101 runner SHA-256 `894b8276f58d36d7d513138e574a9832aa03b8e8a21f3dd84494dbc0367b9244`; frozen Issue #99 resources SHA-256 `2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca`.
- Raw query observations remain outside Git at `$ESS_RUNTIME_PARENT/ess-research/issue105/runs/20261025T130222Z-issue105-official-v2/raw-observations.jsonl.gz` (6,516,233 bytes; SHA-256 `ca2ada0f057f7b439eaee98900f0ae57883adebc84f98d184ec437c1defea9c2`). The run manifest, summary, and full worker/server logs are in that same run directory.
- Attempt `20261025T130003Z-issue105-official-v1` stopped before the first EXPLAIN because its sample relation OID was an integer while the JSONB table OID was a string. It is retained as `INCOMPLETE` with 0 EXPLAIN calls. The comparison was normalized in the runner and the full frozen schedule then completed under a new run ID; no outcomes from v1 were substituted.
- After verifying their hashes, run-local CSV and fixed-sample copies were removed; their pinned source hashes, Issue #99 sample source-run IDs, and sample headers remain in the manifests. The AreCEL source archive itself was not retained.

## Scope limits

This experiment addresses only the four frozen Nominal B=5 sets and canonical-versus-exact-reverse creation order on the pinned AreCEL Test split and PostgreSQL build. It does not test PESS, other budgets, other permutations, or a general distribution of OID orders. The estimate and diagnostics results are scoped observations, not a claim of universal PostgreSQL behavior or parity with AreCEL's published learned-estimator environment.
