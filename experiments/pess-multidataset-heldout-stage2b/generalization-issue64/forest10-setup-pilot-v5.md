# Forest10 setup-only pilot — fifth attempt, successful

**Experimentally observed: SUCCESS for the bounded setup pilot.** With researcher authorization to diagnose, fix and repeat the setup pilot, one further attempt was needed. Fresh sample export, identical-sample replay for Empty and fixed `e00_01`, statistics-object verification, and both fixed valid-query EXPLAIN calls passed. This resolves the setup/sample-replay blocker and supports review of a full valid-calibration execution request; it is not calibration or held-out decision-quality evidence.

## Startup defect and repair

The old directory layout produced a 108-byte Unix socket pathname, including `cluster/socket/.s.PGSQL.65535`. The pinned PostgreSQL source (`src/backend/libpq/pqcomm.c`, `StreamServerPort`, and `src/include/libpq/pqcomm.h`) rejects paths at least as long as Linux `sockaddr_un.sun_path[108]`; the usable maximum is 107 bytes. This is a source-derived startup defect consistent with the previous `pg_ctl_start` failures. Their deleted logs cannot be recovered, so no historical server error text is claimed.

The pilot now uses the shorter `f10-` temporary-directory prefix under the same configured Issue #64 runtime parent, and checks the encoded byte length before any PG process starts. This attempt's maximum socket path length was 91 bytes. Failed `pg_ctl start` calls can additionally classify at most 64 KiB of their startup log into a fixed safe error category before log cleanup; raw log/SQL/output text is not retained. No PG helper source, protocol, model, candidate or query was changed. The successful new run is runtime evidence that this layout works with the pinned build.

## Reproduction and observed checks

- Worktree: `/home/wqts/projects/ess-research/.worktrees/ess-research-issue64`; branch `research/issue64-stage2b-generalization-protocol`.
- Run code commit: `2bf2a619bcad44b17d699a8611b9a2231483b995`; runner SHA-256: `28f0e4a76adf209594c9a0eb448e7ef756056729b9d4acb72c5540011684cda8`.
- Command, after sourcing `~/.bashrc` and verifying the three ESS variables: `.venv/bin/python experiments/pess-multidataset-heldout-stage2b/generalization-issue64/run_forest10_setup_pilot.py --researcher-approved`. Worktree Python: 3.12.3.
- PostgreSQL 16.14 source/binary audit passed (source pin `23c7c2fdd4bfb561f3257d947fee956a2999fdb6`); pinned PR #58 `run_formal.py` SHA-256 `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322` passed.
- One independent fresh cluster in `$ESS_RUNTIME_PARENT/ess-research/issue64/runs/f10-v8toxvh1`; the runtime worker/supervisor summaries and sample remain local. The runtime directory is not committed.
- The fixed query was `arecel:forest10:valid:000005`, source index 5, with static `e00_01` eligibility confirmed. Two EXPLAIN calls completed, one per configuration using the same SQL; no Plan Rows or pre-clamp values were retained.
- One initial export ANALYZE produced a 10,620,460-byte sample from this cluster's `public.forest10`. Verified header: relation identity `6:public8:forest10`, relation OID/filenode `16384`/`16384`, pages `7792`, attributes `10`, server version `16.14`.
- Sample SHA-256: `846850b756515a34912c667007c101c8da4977070d5dc072b1171a6e481cb26d`. Both replay ANALYZE calls succeeded using that same file; the post-run hash was independently checked and unchanged. Binary location: the runtime directory's `results/forest10.fixed-sample`, local only.
- Empty had no selected object. `e00_01` catalog verification passed: name `ess_issue64_forest10_e00_01`, OID `16399`, relation `public.forest10`, kind `mcv`, keys `1 2` (Elevation/Aspect), statistics target `300`. This proves configuration/existence, not actual planner choice or estimator quality.
- Runner shutdown passed; a separate `pg_ctl status` on this exact PGDATA returned exit 3, “no server running.” No monitoring or cleanup error was recorded.

| Measured phase | Seconds |
|---|---:|
| Official valid query resolution | 2.231 |
| Pinned CSV verification/extraction | 1.129 |
| Table bootstrap plus one initial export ANALYZE | 0.660 |
| Empty sample-replay ANALYZE | 0.150 |
| Empty one-query EXPLAIN | 0.004 |
| `e00_01` sample-replay ANALYZE | 0.174 |
| `e00_01` one-query EXPLAIN | 0.004 |
| Cluster lifecycle including shutdown (includes bootstrap/replays above) | 1.570 |
| Worker total | 4.988 |
| Supervisor total | **5.112** |

Peak allocated disk sampled by the 100-ms watchdog: **188,309,504 bytes (179.6 MiB), MEASURED**. The monitor reported no error; this is the sampled peak, not a guarantee of the instantaneous maximum between scans. The run stayed below the existing 1.5-GiB/28-minute abort thresholds and 2-GiB/30-minute hard limits.

## Verification and next decision

Actual static checks before execution: **34 synthetic tests passed** (15 pilot/watchdog/diagnostic, 19 existing Forest10 implementation tests), runner `py_compile`, and `git diff --check`. New regression coverage checks the old overlong layout, the 107-byte boundary including multibyte paths, the shortened layout, startup-log redaction, and missing-log fallback. Historical v1–v4 reports remain unchanged.

No test labels/outcomes, calibration objective or resource selection were read/computed. There was one export ANALYZE, two replay ANALYZE calls, and two valid-only EXPLAIN calls. Full valid calibration remains 174,088 plans across 46 configurations; two pilot EXPLAIN timings cannot establish its total runtime. The setup checks now support requesting that separately scoped execution decision. No full calibration or test evaluation was started.
