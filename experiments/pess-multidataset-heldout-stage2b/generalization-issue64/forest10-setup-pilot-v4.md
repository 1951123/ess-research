# Forest10 setup-only pilot — fourth separately authorized attempt

**Disposition: `FAILED / INCOMPLETE`.** This single attempt reached PostgreSQL startup and failed at `pg_ctl_start` with sanitized cause `server_start_failure` and exit code `1`. The exact temporary cluster is confirmed stopped. No retry was made. Sample export/replay, statistics-object checks, and EXPLAIN remain unverified; this result does not support approval of full valid calibration.

## Scope and execution

- Worktree: `/home/wqts/projects/ess-research/.worktrees/ess-research-issue64`; branch: `research/issue64-stage2b-generalization-protocol`; source HEAD: `efc4328f275b43bd1e76b91958a2eae440c3252c`.
- Runner: `run_forest10_setup_pilot.py`, SHA-256 `1858ffd6da1588496757b845525e4473c4e96c2347af49e7a889154bdb3d9e2a`; Python 3.12.3 from the Worktree `.venv`.
- One fresh, isolated runtime directory was used: `$ESS_RUNTIME_PARENT/ess-research/issue64/runs/forest10-setup-pilot-12558xp0`. No prior pilot directory or experiment cluster was reused.
- PostgreSQL source/binary audit and pinned PR #58 source SHA (`61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322`) passed. Pinned Forest10 CSV verification/extraction took **1.133 s**. The fixed official valid query `arecel:forest10:valid:000005` (source index 5) resolved in **2.093 s** and static eligibility for fixed `e00_01` passed.
- The runner reached `pg_ctl_start`; the captured failure is specifically `program=pg_ctl`, `phase=pg_ctl_start`, `cause=server_start_failure`, `exit_code=1`. The runtime contains initialized `PGDATA` configuration artifacts. `pg_ctl status` against this exact directory returned “no server running” (exit 3); no stop command was needed. The worker console is empty and no server log was retained, so the underlying startup cause remains **unknown**.
- Supervisor elapsed time: **3.848 s** (worker: **3.707 s**; cluster lifecycle including shutdown: **0.426 s**). Disk monitor reported a measured peak of **63,139,840 bytes**; monitor error was null. Both are below the authorized 30-minute / 2-GiB limits.

## Checks and boundaries

| Check / operation | Result |
|---|---|
| Source/binary and pinned helper checks | PASS |
| Official valid query resolution and static `e00_01` eligibility | PASS |
| `initdb` / PostgreSQL startup | PGDATA initialization artifacts present; `pg_ctl_start` failed as classified above |
| Fresh `public.forest10` sample export, header, relation identity and SHA-256 | NOT REACHED / NOT VERIFIED |
| Initial export ANALYZE and Empty / `e00_01` replay ANALYZE | NOT RUN |
| `e00_01` MCV catalog/table/column/target verification | NOT RUN |
| Same-query valid EXPLAIN attempts / completed | **0 / 0** |
| Elapsed / peak allocated disk | **3.848 s / 63,139,840 bytes (MEASURED)** |
| Test truth, estimates, outcomes, calibration objective/resource selection | Not accessed / not performed |

The extracted source CSV was removed by the runner; no fixed ANALYZE sample was exported or retained. No calibration or test evaluation occurred. The pilot is insufficient to approve the 174,088-plan valid calibration. Any further PostgreSQL attempt requires separate authorization; this report does not diagnose the underlying `pg_ctl_start` failure beyond the safe category and exit code.
