# Forest10 setup-only pilot — execution record

**Status: `FAILED_PRE_PG_SETUP / INCOMPLETE`.** This authorized one-shot attempt did not reach PostgreSQL. It provides no evidence that fresh sample export/replay works and is **not sufficient to approve full valid calibration**.

## Attempt and cap accounting

- Scope: one pinned Forest10 valid-workload query statically eligible for fixed candidate `e00_01`; Empty and `e00_01` were the only permitted treatment configurations. No resource selection, calibration objective, test truth, test estimates, or test outcomes were accessed.
- Runner: `run_forest10_setup_pilot.py`, SHA-256 `a5aa01a457dfdee682097eff508833427847df9c1fcf11e47ee7d0aa1510de53` (commit `b2003d300a1d1938f824f7bcb64326d76346a521`). The runner used a 100-ms disk watchdog, 1.5-GiB safety abort threshold, 28-minute soft wall stop, and the approved hard limits of 2 GiB / 30 minutes.
- Runtime directory: `$ESS_RUNTIME_PARENT/ess-research/issue64/runs/forest10-setup-pilot-1svl8vbe`. Peak observed allocated storage: **8,192 bytes**. Supervisor elapsed time: **0.302 s** (hard limit 1,800 s).
- Read-only prechecks passed: PR #58 `run_formal.py` SHA pin; PostgreSQL source commit `23c7c2fdd4bfb561f3257d947fee956a2999fdb6`; PostgreSQL 16.14 binary manifest/hash audit; pinned sample-import source SHA. The verified AreCEL archive was opened for the workload member only; its workload pickle was deserialized, but the label pickle was not opened.

## Failure and operations actually reached

Valid-query adaptation stopped with `ModuleNotFoundError: No module named 'numpy'` in phase `valid_workload_and_query_resolution` (0.183 s). No eligible query ID was resolved. The local runtime directory contains only the supervisor/worker summaries and an empty console log; it has no cluster directory or sample binary.

| Check / operation | Result |
|---|---|
| PG source/binary and PR #58 code pins | PASS (read-only) |
| Resolve the predeclared minimum-source-index valid query supporting `e00_01` | FAILED before query resolution: missing NumPy |
| Create isolated PostgreSQL cluster / load `public.forest10` | NOT RUN |
| Initial sample-export ANALYZE and header/SHA verification | NOT RUN; no sample produced |
| Empty sample-replay ANALYZE | NOT RUN |
| `e00_01` object creation/configuration and sample-replay ANALYZE | NOT RUN |
| Ordinary EXPLAIN attempts / completed | **0 / 0**; no Plan Rows or pre-clamp values retained |
| PostgreSQL shutdown | NOT APPLICABLE; no server started |

No retry, dependency installation, candidate/query substitution, or further PostgreSQL operation was attempted. The exact blocker affects future execution: this runtime lacks NumPy required by the pinned AreCEL scalar adapter. Because the authorized pilot did not verify sample replay or estimate runtime/storage, its result cannot support a decision to approve 174,088 calibration plans. A new attempt after environment repair requires a separate researcher authorization; this report does not request or imply that authorization.
