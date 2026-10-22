# Census13 serial / two-worker JSON smoke — v1

**Result: PASS for this 20-query valid-only smoke.** The test establishes equivalence for the frozen cohort and observed configurations only; it is not a full calibration or a performance guarantee.

## Frozen input and execution

- Plan: `census13-stage2b-plan-v1.json`, SHA-256 `51842c6981936d9a5be39342eb5caee23b35f3137e5876064b0b1a649906d5e1`.
- Cohort: official Census13 valid source indices 0–19; 20 queries; 501 calls per mode (20 Empty + 481 statically eligible singleton calls). Serial and two-worker modes each covered all 501 query/config pairs.
- PostgreSQL source: `1951123/ess-postgresql` commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; built and installed once per run as PostgreSQL 16.14. Both parallel workers shared the same installed binaries, with separate PGDATA, socket and logs. Installed binary SHA-256: `postgres` `c6ff7585e02de906b1a10c02c7abce07a6192bc7abdb01139e82e03ebe543597`; `psql` `0b6ed516ce849e76cb7b27aba4148e15e8ca9f6be669e2a85fad7e526baaadbc`; `pg_ctl` `e7b2d48110c96e4bca8a981128e0016b9eae393746babfcf2e06424570e78f44`; `initdb` `ad4b7b7785d8c1ac6e40f7fe602d2c3387b72f513a7fd25a6a674e334941fd82`. The installation hashes were unchanged after all three clusters stopped.
- PR #58 helpers: commit `76106024611ae91505f1f05bdc35aed44d9c38c4`; `run_formal.py` SHA-256 `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322`; `gate_audit_v2.py` SHA-256 `03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4`.
- JSON adapter source: the reviewed PR #65 commit `27677a17b7455d89e92d5028d9585418550a8ff8`; the exact adapter file hashes are recorded in the runtime summary. Only its structured `EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF)` path was used.
- Acquisition runner source SHA-256: `bf1047157d9457b818d304de07267bb1dfc50d9cb563e8688be9e1b82a9e3d8b` (committed byte-identically after the run in commit `58d492ab0cc072cd48a19eeb380090828e7b0302`). The acquisition-time schedule module SHA-256 was `db2452765fd083e445ddbd709a85ff8b3c3e1c605089908d722d69a7131e27c1`; the later post-hoc verifier strengthened MCV numeric parity checking before producing this report.
- One fresh fixed ANALYZE sample was exported from the serial reference `public.census13` table and replayed byte-for-byte in both worker clusters. Sample SHA-256: `0ff61bcce532a8af07f9319365c28d6fb07e373fc4b8049bae7c72c349baba26` (8,144,782 bytes; PostgreSQL 16.14; 13 attributes; 48,842 tuples; target 90,000). Each cluster independently validated the sample header and relation identity. The base relation OID happened to be 16384 in all three clusters; cross-cluster equality was not a comparison requirement.
- The smoke uses genuinely concurrent configuration workers; each worker processes its owned configurations and queries serially. Empty is assigned once. The same sample is used for all configurations.

## Observed result

| Mode | Calls | Measurement interval | Throughput |
|---|---:|---:|---:|
| Serial, one cluster | 501 | 13.747 s | 36.44 calls/s |
| Concurrent, two clusters | 501 | 7.150 s | 70.07 calls/s |

Observed smoke speedup: **1.923×**. These intervals include configuration/sample-replay ANALYZE and EXPLAIN work, but exclude build and initial cluster/table bootstrap. End-to-end elapsed time, including source export/build/install and setup, was **118.144 s**. Aggregate run-directory peak allocated disk was **413,667,328 bytes (about 394.5 MiB)**, below the 3-GiB early-stop and 4-GiB hard limits; the 7.5-hour/8-hour limits were not approached. The watchdog included the shared build/install, all three PGDATA/log trees, outputs, sample, and the temporary socket directories.

The independently reconstructed schedule and raw observations passed exact coverage and parity checks for all 501 pairs:

- Every pre-clamp estimate was finite, positive and exactly equal as a `Decimal`.
- Diagnostic status and normalized MCV candidate/clause associations matched.
- All five MCV numeric fields (`simple_sel`, `mcv_sel`, `mcv_basesel`, `mcv_totalsel`, `stat_sel`) matched exactly as finite Decimals for each event.
- OIDs were retained and mapped to each worker's candidate ledger independently; numeric OID equality was not required.
- Each mode reported 481 `VERIFIED` singleton MCV diagnostic events and 20 Empty `NO_MCV_EVENTS` observations. This is diagnostic coverage, not evidence of an accuracy benefit.
- All three clusters reported stopped after cleanup; installed PostgreSQL binary hashes remained unchanged.

Compressed query-level observations are retained as `serial-smoke.jsonl.gz` and `parallel-smoke.jsonl.gz`; their hashes and the independent verification summary are in `verification.json`. The two files have different row order because concurrent workers finish configurations in different orders; parity is keyed by `(query_id, config_id)`, not file order.

## Failed implementation attempts retained, not pooled

Earlier same-task runs are not included in the result above: one stopped before cluster creation on a candidate-support mapping `KeyError`; another exposed the Unix socket path-length limit and its server log confirmed shutdown; a third produced serial and two-cluster observations but its coordinator accidentally ran worker loops sequentially, so it is not evidence of parallel throughput. The successful run uses the corrected short private socket paths and concurrent coordinator. No failed run was silently overwritten.

## Limits

Only the fixed first 20 valid queries and singleton configurations were exercised. This smoke does not establish full-valid throughput, full 288,849-call collection success, model fitting, resource selection, or performance on other datasets. No truth or test workload outcome was loaded; no model was fit and no resource set was selected. Do not infer any Nominal/PESS or test-performance conclusion from this smoke.
