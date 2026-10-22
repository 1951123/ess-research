# Forest10 PR #7 integration pilot v1

**Status: BLOCKED before PostgreSQL initialization.** This is the one researcher-authorized integration pilot; it was not retried.

## Scope and pins

- Run ID: `f10-g65v65h3` (runtime path was `$ESS_RUNTIME_PARENT/ess-research/issue64/runs/f10-g65v65h3`).
- Issue #64 execution code HEAD: `c48c44c8fabed547f1a7510a8e8e846f8f4f5584`.
- PostgreSQL source pin requested: `ess-postgresql` commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`.
- PR #58 helper pin: `ess-research` commit `76106024611ae91505f1f05bdc35aed44d9c38c4`; `run_formal.py` SHA-256 `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322` and `gate_audit_v2.py` SHA-256 `03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4` both verified in this run-local checkout.
- The official valid workload-only preflight resolved `arecel:forest10:valid:000005` (source index 5) as statically eligible for `e00_01`. No truth, calibration objective, resource selection, or test workload/outcome was read or used.

## Execution and outcome

The run-local PostgreSQL repository was initialized and its `origin` configured. Fetching the pinned PostgreSQL commit timed out. The runner recorded phase `postgresql_source_fetch`, program `git`, cause `timeout`, and no exit code (the subprocess timeout occurred at 300 seconds). Consequently the PostgreSQL commit was **not verified**; no configure/compile/install, PostgreSQL binary hash/version check, `initdb`, cluster startup, table load, sample export, ANALYZE, statistics configuration, or EXPLAIN occurred. The requested two-path diagnostic comparison therefore has **zero calls** and no MCV-hit result; pre-clamp and MCV parity remain untested.

| Stage | Result | Elapsed |
|---|---|---:|
| PR #58 helper fetch, hash verification, import | PASS | 5.364 s |
| Fixed valid workload resolution | PASS | 2.807 s |
| Pinned Forest10 CSV verification/extraction | PASS | 1.199 s |
| PostgreSQL local source repository initialization | PASS | 0.003 s |
| PostgreSQL remote pin configuration | PASS | 0.002 s |
| PostgreSQL pinned source fetch | **TIMEOUT** | 300.103 s |
| Compile/install, cluster, sample, ANALYZE, EXPLAIN | NOT REACHED | — |

Supervisor-measured total elapsed time was **309.592 s**. Peak allocated bytes under this run directory were **48,746,496 bytes** (`MEASURED`). The 30-minute / 2-GiB hard limits and the earlier 28-minute / 1.5-GiB watchdog thresholds were not reached. No PGDATA was created; supervisor cleanup reported no PostgreSQL cleanup action necessary. No PostgreSQL server was left running.

## Interpretation and boundary

This run does not establish independent PostgreSQL build/runtime feasibility or agreement between PR #58 server-log trace and PR #7 structured diagnostics. It identifies a network/source-fetch timeout as the blocking failure, not a PostgreSQL or estimator failure. The helper-source isolation and fixed valid-query preflight did pass. No source, sample, trace, Plan Rows, or outcome data from another Issue/run was used. The run-local temporary material is disposable and is removed after this concise failure record is captured; no raw logs or sample are included in Git.

No further pilot, valid calibration, or test evaluation is authorized by this result.
