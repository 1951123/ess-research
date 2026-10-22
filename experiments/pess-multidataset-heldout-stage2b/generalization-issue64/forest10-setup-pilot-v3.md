# Forest10 setup-only pilot — third authorized attempt

**Disposition: `FAILED / INCOMPLETE`.** The one-shot attempt failed during the runner's combined cluster-start/bootstrap/replay phase. It did not verify export or replay of the fixed ANALYZE sample and does **not** support approval of full valid calibration. This record is independent of and does not replace `forest10-setup-pilot-v1.md` or `forest10-setup-pilot-v2.md`.

## Scope and execution

- Worktree: `/home/wqts/projects/ess-research/.worktrees/ess-research-issue64`; branch `research/issue64-stage2b-generalization-protocol`; source HEAD at launch: `53eaae601124a005d1360e590cce8bd740270ef6`.
- Runner SHA-256: `6196a775b6e7d9fd889ce7fccb995da7d75e9ae6a0d274433b176d7561f563c4`; Python 3.12.3, worktree `.venv`, NumPy 2.3.4.
- Scope was one isolated temporary Forest10 cluster, one initial sample-export/ANALYZE attempt, Empty and fixed `e00_01`, at most one replay ANALYZE per configuration, and at most one EXPLAIN per configuration for the single preselected valid query. No retry or substitution was made.
- Runtime directory: `$ESS_RUNTIME_PARENT/ess-research/issue64/runs/forest10-setup-pilot-mvxjg3jv`; sample and cluster artifacts remain local there and are not committed.
- PostgreSQL source/binary and pinned PR #58 source checks passed. Pinned Forest10 CSV verification/extraction took **1.116 s**; resolution of the official query took **2.138 s**. The query was `arecel:forest10:valid:000005` (source index 5), and static `e00_01` eligibility passed. The same SQL had been reserved for both configurations.
- Total supervisor elapsed time: **3.841 s** (worker: **3.725 s**; cluster lifecycle including cleanup: **0.416 s**), below the 1,800-s hard limit.
- Allocated-disk monitor remained operational and measured a peak of **63,139,840 bytes** (about **60.2 MiB**), below the 2-GiB hard limit and 1.5-GiB abort threshold. This is the monitor's measured peak, not a sentinel or post-run estimate.

## Outcome and limits

The worker returned a sanitized `RuntimeError` in phase `cluster_start_bootstrap_and_replays`: “PostgreSQL command failed; SQL and command output omitted”; the recorded cause was `nonzero_exit`, with no exit code. The worker console was empty and no server log was retained, so the underlying PostgreSQL command and root cause cannot be determined from the preserved evidence. This is a **diagnostic gap**, not evidence that a particular PG operation or configuration failed. A read-only `pg_ctl status` against this attempt's exact data directory reported `no server running`.

| Check / operation | Result |
|---|---|
| Source/binary and pinned helper checks | PASS |
| Fixed valid query resolution and static `e00_01` eligibility | PASS |
| Independent cluster identity / bootstrap | NOT VERIFIED; combined phase returned a command failure before its identity check was recorded |
| Fresh `public.forest10` sample relation identity, header and SHA-256 | NOT VERIFIED; no sample record was returned |
| Initial export ANALYZE | NOT VERIFIED as completed |
| Empty and `e00_01` replay ANALYZE on the identical sample | NOT RUN / NOT VERIFIED |
| `e00_01` MCV object, relation, columns and target | NOT VERIFIED |
| Valid-query EXPLAIN attempts / completed | **0 / 0**; no Plan Rows or estimate values retained |
| Elapsed / peak allocated disk | **3.841 s / 63,139,840 bytes (MEASURED)** |
| Test truths, estimates, outcomes; calibration objective/resource selection | Not accessed / not performed |

No fourth attempt is authorized or made. The pilot confirms the pinned input/query checks and demonstrates functioning disk monitoring under this short run, but the required sample export/replay and treatment checks remain unresolved. **The evidence is insufficient to request or approve the 174,088-plan valid calibration.** Any further pilot requires separate researcher authorization and should first address preservation of a suitably sanitized bootstrap failure diagnostic; this report does not modify the runner or protocol.
