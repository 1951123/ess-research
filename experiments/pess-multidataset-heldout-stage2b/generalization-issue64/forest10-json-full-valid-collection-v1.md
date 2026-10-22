# Forest10 full-valid JSON observation collection v1

**Status: collection completed and integrity-verified; not model fitting or selection evidence.** Run `f10full-3z7q5_gy`, executed from Issue #64 code commit `439d7071f0b7dfd3c14663eae687d1783131ba8b` under the researcher decision at the top of Issue #64.

## Frozen scope and environment

- Forest10 official **valid** split; 10,000 queries in ascending `source_index`.
- Empty: 10,000 structured EXPLAIN observations. Singleton candidates: 164,088 statically eligible observations across the frozen 45 candidates. Total: **174,088 calls, 46 configurations**.
- PostgreSQL source commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`, independently archived/built/installed in this run; installed version **PostgreSQL 16.14**. PR #58 helper commit `76106024611ae91505f1f05bdc35aed44d9c38c4`; helper file hashes and binary hashes are retained in `collection-manifest.json`.
- Sole observation interface: `EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF)`. One new run-private cluster and one fixed sample were used throughout. Sample: `public.forest10`, relation OID 16384, 90,000 tuples, 10,620,460 bytes; SHA-256 `0c45a8c9aeb101543996f50de1bced80b278edb6a78c2e34fae29b6e1697f291`.

## Observations and verification

- **174,088 succeeded; 0 failed; 0 unattempted.** All 46 configurations completed in the frozen order. Every record is `Status=complete`, has a positive finite `nrows_preclamp` and a positive relation OID; no Plan Rows substitution was used.
- **87,404** singleton observation rows contain a verified MCV event (87,404 event records); **86,684** observations are explicitly `NO_MCV_EVENTS`. These are workload/configuration-specific observations, not an accuracy or PESS/Nominal advantage claim.
- A read-only verification recomputed the outcome-free valid workload's static eligibility/order and matched every `(query_id, config_id, static_eligible, sequence)` row. All part SHA-256 values, compressed block/member checksums, decompression checksums, row counts and sequence ranges passed. The fresh sample's size and SHA-256 matched the run manifest. The loader attested `labels_loaded=false` during the verification; no truth, test split, model objective, fitting, selection or test evaluation was used.
- A reusable read-only verifier is now provided at [`verify_forest10_full_valid_observations.py`](verify_forest10_full_valid_observations.py). Re-running it against the durable evidence reported `PASS`: 174,088 rows, 46 configurations, 86 parts, 87,404 `VERIFIED` MCV-event rows and 86,684 `NO_MCV_EVENTS`; its workload loader attested `labels_loaded=false`. Two synthetic regression tests pass, including tamper and schedule-mismatch rejection. This verifier checks collection integrity only and does not fit the model or select resources.

## Runtime, limits and durable evidence

- Wall time: **840.865 s** (14 min 0.9 s). PostgreSQL configure 8.667 s, compile 79.589 s, install 1.589 s; structured JSON calls 716.951 s; CSV extraction 9.086 s. Per-configuration timings are preserved in the run manifest.
- Watchdog-measured peak allocated run-directory disk: **534,147,072 bytes** (about 509.4 MiB), versus 3 GiB early-stop and 4 GiB hard-stop thresholds. No stop threshold or monitor error occurred. Worker exit code 0; PostgreSQL shutdown `PASS`.
- Durable evidence: [`runs/20261022-forest10-full-valid-v1/`](runs/20261022-forest10-full-valid-v1/) contains 86 gzip JSONL observation parts (6,408,799 bytes total; largest part 122,184 bytes), the original collection manifest, and supervisor summary (6,728,670 bytes total). Every part is below the 10 MB Git file limit. The supervisor-recorded collection-manifest SHA-256 is `a6972008f73f24ca3c1a456c96caf64e109895ef5b9525fa2b35791ca5bca99b`; supervisor-summary SHA-256 is `b15df056b24c5f15309e5a2a8d190b167a2bb009056ee1115f2c371acd40727c`. Copied part bytes were verified identical to the runtime outputs before cleanup.

This is a successful full-valid **observation acquisition only**. It does not fit the corrected-log model, compute calibration objectives, select Nominal/PESS statistics, compare decisions, access official test data/outcomes, or support any decision-quality conclusion. The next scientific step—valid-truth coefficient fitting and exact B=0/2/3 Nominal/PESS resource selection—requires separate researcher authorization because the current Issue decision authorized collection only and explicitly excluded fitting/selection.
