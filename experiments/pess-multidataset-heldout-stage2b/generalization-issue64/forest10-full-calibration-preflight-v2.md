# Forest10 full-valid JSON collector readiness v2 — code only

**2026-10-22 (Asia/Shanghai).** Follow-up to PR #65 review `5608606130` at preflight HEAD `b343ee65bebc5e90602a0f4701f97df9cdd82a51`. This revision implements and synthetically tests the requested collection-only runner.

**Status: implementation ready for review; execution explicitly disabled.** The committed full-observation plan remains `CODE_ONLY_RESEARCHER_REVIEW_REQUIRED_BEFORE_EXECUTION`, limits remain `PROPOSED_ONLY_NOT_APPROVED`, and the CLI refuses to create a run directory even when passed `--researcher-approved`. No PostgreSQL process/query, valid/test truth, model fitting, objective, selection or test evaluation occurred in this follow-up.

Scientific question: what is the least additional machinery needed to collect all pinned Forest10 valid JSON diagnostics as a verifiable prefix, keep the 46 configurations on one sample, and make failure/incomplete status impossible to mistake for a complete cohort?

## Collection plan and implementation

The [full observation plan](forest10-json-full-observation-plan-v1.json) pins:

- Official Forest10 valid, all 10,000 queries in ascending source index.
- The 45 candidate IDs in the merged PR #68 order and 164,088 static eligible query/candidate pairs.
- 10,000 Empty + 164,088 eligible singleton calls = **174,088 structured EXPLAIN calls / 46 configurations**.
- Fixed PG commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`, PR #58 helper commit `76106024611ae91505f1f05bdc35aed44d9c38c4`, AreCEL archive SHA and JSON-only config.
- Proposed hard limits **8 h / 4 GiB** and early stop **7.5 h / 3 GiB**, all explicitly unapproved. They apply to one fresh private build, cluster, table, sample and output.

[The collector](run_forest10_full_calibration_collector.py) reuses the existing private PG setup, workload-only loader, static eligibility function and strict PR #7 adapter. Before PG build it recomputes the full schedule and checks query IDs/order, exact candidate order and pair/call/config counts against the plan. It never reads truth or imports model fitting/selection functions. It runs Empty then each singleton in candidate order, one configuration at a time, replaying the same sample. Each row retains query/config/sequence, eligibility, complete status, positive `nrows_preclamp`, relation OID, full compact MCV events or an error class. The returned parsed estimate is rechecked positive and finite.

### Evidence persistence and interruption

- Output uses **append-only gzip JSONL members** grouped into numbered `.jsonl.gz` parts. Each part is capped at 2,048 records and 8 MiB uncompressed, so its compressed size stays below the 10 MB per-file repository threshold.
- Every 256 rows, the collector writes a complete gzip member, flushes and `fsync`s its bytes, then atomically replaces and directory-`fsync`s the progress manifest. The manifest records block byte offsets, sequence/count ranges, compressed and uncompressed hashes, per-part hashes, attempted/completed/failed counts, current/completed/failed configurations, unattempted suffix, terminal error, source pins and sample identity.
- A complete gzip member per batch means a process stop does not leave the last durable checkpoint dependent on a gzip footer written only at normal shutdown. The active part's manifest byte offset/checkpoint hash distinguishes durable bytes from any trailing incomplete write.
- Invalid/missing/incomplete/nonpositive/nonfinite observations create an explicit failed row and stop. Configuration failures are recorded separately; they do not fabricate a failed EXPLAIN. `NO_MCV_EVENTS` remains a successful observation.
- The manifest stays `RUNNING` until all calls, configurations, evidence synchronization and cluster shutdown pass. Any worker/supervisor error leaves `INCOMPLETE` with the unattempted count. A nonzero worker exit cannot be left marked successful.
- Files open exclusively (`xb`). There is no append, automatic retry or resume path; each run receives a new directory and sample. Partial data is not accepted by the model/selection functions.
- A successful run retains its local sample with identity/header/hash until evidence review. Temporary CSV/schema are removed; nothing writes experimental output into the checkout. Compressed observation parts plus one manifest are the proposed durable Git evidence; they are not yet present because no measurements were run.

This is bounded batching with stop-and-preserve behavior, not general crash recovery. The synthetic tests exercise actual temporary-file writes, gzip decompression, SHA checks, fsync batches, manifest updates, handled failure/interruption and supervisor state. They do not simulate power loss, kernel panic or storage hardware failure.

## Budget choice and limits of the estimate

The higher caps are a concrete **proposal for review**, not authorization embedded in the plan. Phase C measured 111.796 s total and 0.750827 s for 212 EXPLAIN calls, but its first-20 sample is not representative. Sensitivity arithmetic at 120 s fixed overhead gives:

| Assumed mean per call | Approximate total |
|---:|---:|
| 10 ms | 31.0 min |
| 50 ms | 2.45 h |
| 100 ms | 4.87 h |
| 250 ms | 12.12 h |

Thus 8 h accommodates the 100 ms scenario with margin but would stop before completion around the 250 ms scenario. These are assumptions, not measured distributions or guarantees. The new 256-row `fsync` policy's time cost has not been measured on the actual workload. If runtime exceeds the proposed cap, the run stops incomplete; it is not resumed or concatenated with a second sample.

The 4 GiB cap leaves headroom over Phase C's 448,634,880-byte peak plus the 4 KiB/row raw planning allowance of about 713 MB, including unmeasured WAL/log/temp growth and allocation overhead. This is a planning margin, not a proven maximum. The watcher remains 0.1 s and applies to source acquisition, compile/install, setup and collection. Runtime memory is not bounded by this disk cap; the collector streams rows and retains only workload/schedule/backend state rather than 174,088 observation dictionaries.

## Executed offline checks

Actual command:

```bash
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover \
  -s experiments/pess-multidataset-heldout-stage2b/generalization-issue64 \
  -p 'test_*.py'
```

Result: **130 tests passed**. New tests include:

- A synthetic 10,000-query workload with 45 candidates that independently reproduces 164,088 eligible pairs and 174,088 total calls.
- Compressed-part record/byte rotation, per-member and per-part hashes, decompression, fsync and checkpoint counts.
- Handled incomplete-prefix/no-resume behavior and per-file-size bounds.
- Source-path guard against truth, selection and test evaluation.
- Current plan-status lock: worker refuses before PostgreSQL setup; CLI refuses without creating a runtime directory while the plan is review-only.
- Nonzero supervisor exit cannot leave a success manifest.

Also passed: Python AST parsing, `--help` import, `git diff --check`, and `sha256sum -c` for all existing historical manifest entries. No production model, JSON adapter, active protocol/config or old report changed.

## Approval boundary

The plan's exact run schedule is frozen for review, while its status and proposed limits deliberately do not permit execution. Review should decide whether to accept the 8 h / 4 GiB proposal and compressed-part retention. After that, the plan can be explicitly approved in a separate commit; until then the collector rejects the run before runtime allocation. No full-valid acquisition, model fitting, resource selection or test experiment is authorized by this code-only submission.
