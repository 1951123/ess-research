# Forest10 first-milestone preflight (outcome-free)

Status: **implementation checks passed; actual Forest10 resource decisions and PostgreSQL execution remain NOT RUN**. This preflight did not open the AreCEL archive, truth files, test estimates, or any held-out outcome, and did not run PostgreSQL, `EXPLAIN`, or `ANALYZE`.

## Workload and exact-search counts

Source: the already-published Issue #67 / merged PR #68 workload-only report, pinned in `forest10-first-implementation-v1.json`. Its 45 Forest10 candidate support counts sum to **164,088 eligible query-candidate pairs**. Applying the approved rule gives:

- Calibration: 10,000 Empty plans + 164,088 eligible singleton plans = **174,088 EXPLAIN plans**.
- Test evaluation: at most 10,000 queries × 5 distinct sets (Empty plus up to four Nominal/PESS selections for B=2 and B=3) = **50,000 plans**.
- Combined upper bound: **224,088 plan attempts**. This is a count, not a time or storage estimate.
- Feasible resource subsets: B=0 **1**, B=2 **1,036**, B=3 **15,226**. Complete scoring through B=3 evaluates at most 15,226 sets × 10,000 valid task models × 2 methods = **304,520,000 task-set objective evaluations** (the B=0 and B=2 results are read from the same nested complete enumeration).

The exact enumerator is implemented using combinations up to the cardinality bound and exact common-denominator integer arithmetic equivalent to `Fraction`. Matching schemes are cached by selected set and eligible-edge pattern; all exact global ties are retained. A small synthetic independent oracle checks complete objectives. At B=0, both methods necessarily select Empty because it is the only feasible set; its model objective is not computed. **No B=2 or B=3 Forest10 selection can yet be reported:** the full-split Empty/singleton positive pre-clamp trace estimates needed to construct the 10,000 valid-query model inputs have not been measured, and this phase expressly prohibits calibration `EXPLAIN`.

The synthetic performance probe used 45 generated candidates and 100 generated task models, and scored all six method/budget combinations through B=3 in **2.233 seconds** on this machine. Linear scaling projects about **223.3 seconds** for 10,000 task models for selector-only work. This is a synthetic projection, not a workload benchmark or runtime guarantee; it excludes calibration I/O, PostgreSQL plans, serialization and other orchestration.

## Local environment snapshot

Observed in the assigned Issue #64 Worktree on 2026-10-21:

- Python: 3.12.3; available CPU workers: 8.
- Available space at configured `ESS_RUNTIME_PARENT`: 18,810,880,000 bytes (filesystem total 52,518,420,480 bytes).
- `ESS_DATA_ROOT/arecel-data.tar.gz`: present, 118,265,504 bytes by metadata only; archive contents were not read.
- This Worktree has no `.venv/`; this implementation and its tests use only the Python standard library, so no package installation was needed.
- The installed PostgreSQL runtime was located through the documented `$ESS_RUNTIME_PARENT/issue38/pg-prefix` and `results/heldout-v1/runtime-manifest.json`, not PATH. PR #58's read-only binary audit verified source commit `23c7c2fdd4bfb561f3257d947fee956a2999fdb6`, manifest-pinned hashes, and PostgreSQL 16.14 for `postgres`, `initdb`, `pg_ctl`, `psql`, and `pg_config`. No server was started.
- The PR #58 sample-header parser accepted the existing `$ESS_RUNTIME_PARENT/issue38/results/replay-sample.bin` (3,540,470 bytes; SHA-256 recorded in the config; PG 16.14; 10 attributes). Its catalog identity is `public.forest10_original`; reuse against a fresh Stage 2B table was **not verified**, and the sample was not replayed.
- Runtime and disposable-storage needs for 174,088 calibration plans plus up to 50,000 evaluation plans remain **NOT MEASURED / NOT APPROVED**. Available filesystem space alone does not establish that the experiment fits.

## Boundary and next gate

`forest10_runner.py` wires valid-only Empty/eligible-singleton calibration to the corrected PR #58 positive pre-clamp estimates, constructs alpha/b, and calls exact selection. Its PR #58 backend delegates to the pinned statistics setup, trace query and psql helpers. The evaluation path requires exactly 10,000 supplied test queries, deduplicates frozen sets, applies each once, parses top-level Plan Rows for every query, and emits compact Q1 observations and summaries. Tests use a synthetic backend only. No official split/truth was loaded, no PostgreSQL operation occurred, and no resource selection was made. Actual resource selection remains pending separately approved valid-split calibration. Test evaluation remains blocked pending protocol/selection freeze and separate researcher execution approval. No result here supports a Nominal/PESS performance comparison.
