# Forest10 PR #7 integration pilot v2

**Outcome: `INCONCLUSIVE` for diagnostic parity; infrastructure/source-export portion passed.** This is the single researcher-authorized rerun. It stopped after the legacy trace call failed to produce its expected marker; the structured EXPLAIN was not attempted. Pilot v1 remains unchanged.

## Pins and run

- Run: `f10-h6ibjj_g`; execution code HEAD: `3671d61b5efcca510dde5ef760be3b70f7c428c5`.
- PostgreSQL source: local Git object store `/home/wqts/projects/ess-postgresql`, commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`. The commit object resolved exactly; source was exported with `git archive` into this run's private `postgresql/source` (no `.git`, worktree files, or build/runtime assets reused). `src/backend/commands/analyze_sample_cache.c` SHA-256: `661c03c59a2a4ca1273a205d3e0c1ae2f2dc9c1fdf8c39076cd0085be6880e68`.
- Out-of-tree build/install: **PASS**, PostgreSQL 16.14. Binary SHA-256:

  | Binary | SHA-256 |
  |---|---|
  | `postgres` | `e86dc639e3e2a11f53af23edaa7482edf376720d617f0dcf6a05b904f2b01bfc` |
  | `initdb` | `83af0edafaca385e75ff988b33694b795982fc66b63c3092ab561f5c54c2d28f` |
  | `pg_ctl` | `5c71afa1a98b6a24deb1e9766c76be3fc1b0045a61358fa06839cb32142fecec` |
  | `psql` | `5f478cbe0d5d4234e35f00372fe59d71e7a4e431223ae7a55d5f29f2a3316d0a` |
  | `pg_config` | `fc7b01f877a8d930dd4602425974d4589e7c52aeffc217737b3818f16f425b1e` |
- PR #58 helpers: **PASS**, commit `76106024611ae91505f1f05bdc35aed44d9c38c4`; both pinned helper hashes matched.

## Pilot checks

- Private cluster, identity check, `public.forest10` bootstrap, one fresh sample export/ANALYZE, and sample identity/header/SHA-256: **PASS**. Relation identity `6:public8:forest10`, OID/filenode `16384`; sample size 10,620,460 bytes; SHA-256 `65978218c8f88c6584cb6f4e8bf8cfc89cb481352f74dd62ac454f0faa38ab55`.
- Same-sample replays: Empty **PASS**; `e00_01` **PASS**. Catalog verification **PASS**: MCV object `ess_issue64_forest10_e00_01`, OID `16399`, `public.forest10`, keys `1 2`, target `300`.
- Fixed query was `arecel:forest10:valid:000005`, statically eligible; no replacement query was used.
- Diagnostic calls: legacy PR #58 path **1 attempted / 0 completed**; its trace marker did not appear before the helper timeout (`legacy_pr58_server_log_trace_explain` phase 15.041 s). PR #7 structured path **0 attempted** because the first failure stopped the worker. The pilot therefore executed one legacy-path attempt, not the requested pair.
- Pre-clamp comparison: **not available**; the adapter captured/accepted no finite positive `nrows_preclamp`. MCV event/OID/clause/five-term comparison: **not performed**. Do **not** assign `BASE_MATCH_MCV_NOT_VERIFIED`: base parity was not established. MCV-hit parity remains unverified.
- Intended planner settings recorded by the runner were `plan_cache_mode=force_custom_plan` and `max_parallel_workers_per_gather=0` for both paths. `client_min_messages` was `debug1` for legacy trace visibility and `warning` for structured diagnostics (not a planner GUC). Since the structured call never ran, paired runtime GUC equivalence was not empirically established.

## Time, disk, cleanup, and scope

- Total supervisor time: **137.989 s** (worker: 137.645 s). Key phases: helper fetch/hash/import 6.507 s; valid query resolution 2.764 s; CSV verification/extraction 1.231 s; PostgreSQL source export/configure/compile/install 110.176 s (configure 9.132 s, compile 97.239 s, install 1.886 s); table/bootstrap/sample export 0.907 s; Empty replay 0.164 s; `e00_01` replay 0.200 s; failed legacy trace stage 15.041 s.
- Watchdog: **PASS / no abort**. Peak allocated run-directory size **447,696,896 bytes (MEASURED; about 426.96 MiB)**. Neither early-stop threshold (28 min / 1.5 GiB) nor hard cap (30 min / 2 GiB) was approached. Disk monitor reported no error.
- Cluster shutdown: worker check **PASS**; run-local `pg_ctl status` afterward reported no server running (exit 3, expected stopped state). No cleanup failure was recorded.
- Scope: one new run, one cluster, one sample export, only Empty/`e00_01`, fixed valid query, one legacy EXPLAIN attempt, no structured retry. No truth, calibration objective, resource selection, official test query, or test outcome was read or computed. No raw trace, plan rows, sample, source archive, binaries, PGDATA, or build logs are committed.

**Interpretation / next decision:** local pinned-source export and independent PostgreSQL 16.14 build/install are experimentally verified. The pilot does not validate either diagnostic's numeric parity because the legacy trace marker was missing; it is not evidence of estimator disagreement. No further pilot or calibration is authorized by this result.
