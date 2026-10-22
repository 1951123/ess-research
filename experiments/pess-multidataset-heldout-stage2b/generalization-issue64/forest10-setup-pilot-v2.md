# Forest10 setup-only pilot — second authorized attempt

**Disposition: `FAILED / INCOMPLETE`.** This separately authorized attempt stopped during fresh-cluster bootstrap. It did not verify a sample export/replay and is **not sufficient to approve full valid calibration**. The first attempt's record remains unchanged in `forest10-setup-pilot-v1.md`.

## Scope and execution

- Worktree-local environment: `.venv`, Python 3.12.3, pinned `numpy==2.3.4` from `requirements-arecel.txt`.
- Runner: `run_forest10_setup_pilot.py`, SHA-256 `a5aa01a457dfdee682097eff508833427847df9c1fcf11e47ee7d0aa1510de53`; pinned PR #58 source SHA `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322`.
- Scope remained one isolated Forest10 cluster, Empty and fixed `e00_01`, one official valid query, the existing 30-minute / 2-GiB hard bounds, no retries or substitutions, and no test outcomes.
- Runtime directory: `$ESS_RUNTIME_PARENT/ess-research/issue64/runs/forest10-setup-pilot-76gjv_uk`.
- Predeclared query resolution passed: `arecel:forest10:valid:000005`, source index 5, static `e00_01` eligibility `PASS`; same SQL was reserved for both configurations.
- PostgreSQL source/binary and PR #58 code pin checks passed. Pinned Forest10 CSV verification/extraction took 1.148 s; valid workload/query resolution took 2.549 s. Supervisor elapsed time was 4.262 s. Cluster lifecycle/shutdown was recorded as 0.44 s, but cluster bootstrap did not return successfully.

## Failure and checks reached

The supervisor's 100-ms allocated-byte walker encountered an `OSError` while traversing the changing runtime tree. The runner maps any such error to a sentinel above the hard disk cap and aborts fail-closed. The summary reports `peak_allocated_disk_bytes=2,147,483,649`, which is that **monitoring sentinel, not a storage measurement**. The precise underlying `OSError` was not captured, so this record does not attribute it to permissions or a specific file race. Post-abort `du -s -B1` measured 40,259,584 allocated bytes in the runtime directory; the actual peak is unknown.

The worker summary reports an error in `local_cleanup` (`PostgreSQL command failed; SQL and raw diagnostics intentionally not retained`). A direct `pg_ctl status` against this attempt's exact data directory returned `no server running`. No sample file or completed sample identity record was present. The bootstrap phase was entered, but did not produce auditable evidence of a completed `public.forest10` sample export or initial export ANALYZE.

| Check / operation | Result |
|---|---|
| Pinned PostgreSQL source/binaries and PR #58 source | PASS |
| Resolve fixed official valid query and static `e00_01` eligibility | PASS |
| Create one isolated temporary PG cluster | Entered; initialization/bootstrap started; cluster is now confirmed stopped |
| Fresh sample relation identity/header/SHA-256 | NOT VERIFIED; no returned sample record/file |
| One initial export ANALYZE | NOT VERIFIED as completed |
| Empty replay ANALYZE / `e00_01` replay ANALYZE on identical sample | NOT RUN / NOT VERIFIED |
| Statistics object catalog/configuration | NOT VERIFIED |
| EXPLAIN attempts / completed | **0 / 0**; no Plan Rows or pre-clamp values retained |
| Runtime cap | 4.262 s, below 1,800 s; peak disk **UNKNOWN** because watchdog measurement failed (post-abort snapshot 40,259,584 bytes) |
| Test truths, estimates, outcomes | Not accessed |

No second retry, candidate/query substitution, dependency change, calibration objective, resource selection, or test evaluation was performed. The missing Python dependency was resolved, but this attempt uncovered a runner defect: an inability to walk a changing PG runtime tree is represented as a fictitious over-cap byte count, and cleanup also reported a sanitized PostgreSQL-command failure. Until those failures are understood and the monitor can demonstrate reliable peak accounting, this pilot does not support approval of the 174,088-plan valid calibration. Any further pilot attempt requires separate researcher authorization.
