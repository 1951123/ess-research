# Census13 full-valid acquisition attempt v1 — BLOCKED

**Result:** `BLOCKED`; this was a setup failure before collection. The run made
zero EXPLAIN calls. The failed run directory and summary remain in the local
runtime area; this report does not turn it into a completed calibration.

## Frozen inputs and scope

- Plan: `census13-stage2b-plan-v1.json`, SHA-256
  `51842c6981936d9a5be39342eb5caee23b35f3137e5876064b0b1a649906d5e1`.
- Run ID: `20261022-074758-census13-full-valid`.
- Execution code at start: `9c712c2c8561a204a1599083d889c8484653c070`.
- Pinned PostgreSQL source: `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`;
  independently compiled and installed PostgreSQL 16.14 in this run.
- PR #58 helpers: `76106024611ae91505f1f05bdc35aed44d9c38c4`, with both
  pinned file hashes verified. JSON adapter helpers were loaded from pinned
  PR #65 commit `27677a17b7455d89e92d5028d9585418550a8ff8`.
- Outcome-free schedule reconstruction passed before PostgreSQL startup:
  10,000 valid queries, 78 candidates, 10,000 Empty plus 278,849 eligible
  singleton calls (288,849 total). No labels or truth were loaded.

## Failure and cleanup

PostgreSQL configure, build, and install succeeded (8.041 s, 78.422 s, and
1.643 s respectively). One run-local fixed sample was exported from the first
worker's `public.census13` after the initial sample-export ANALYZE. Setup then
queried `public.census13` on worker 1 before importing the table/sample there;
PostgreSQL correctly returned `relation "public.census13" does not exist`.
This runner ordering defect was fixed in commit
`eb8ef66b04631bf32d7aab0e500bbd6f6b8772de`, but the full run was not restarted.

- EXPLAIN calls: **0 / 288,849**; no observation or coverage file was produced.
- Elapsed: 96.899 s. Peak allocated run-directory bytes: 352,886,784
  (below the 3-GiB early-stop and 4-GiB hard limits); no watchdog stop fired.
- Both run-owned clusters were checked with their run-local `pg_ctl`: `no
  server running`. The local sample/source/build/logs remain preserved under
  `$ESS_RUNTIME_PARENT/ess-research/issue71/runs/20261022-074758-census13-full-valid/`.
- Test truth, estimates, and outcomes were not accessed. No fitting or
  resource selection was performed.

## Disposition

The frozen full acquisition is **not complete**, so the independent coverage
verifier and valid-only fit/selection were not run. Per the stop-after-failure
boundary, no further PostgreSQL run is started in this report. A new explicit
researcher decision is required before another full acquisition attempt.
