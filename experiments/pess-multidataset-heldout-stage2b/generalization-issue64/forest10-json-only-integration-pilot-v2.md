# Forest10 JSON-only integration pilot v2

**Outcome: Phase B PASS, with `NO_MCV_EVENTS`.** On 2026-10-22 (Asia/Shanghai), one separately authorized rerun accepted the single fixed query's complete JSON diagnostic and finite positive pre-clamp estimate. The cluster stopped normally. This is an interface/setup observation, not a cardinality-accuracy or resource-selection result. The earlier JSON-only v1 and legacy integration v1/v2 reports remain unchanged.

## Execution identity and limits

- Run ID: `f10-q_1y5zld`; execution commit: `76318ee8f59a3142ba1757f595e9dfc2a9f18e0c`; config: `forest10-json-only-v2.json`.
- All source exports, build/install, PGDATA, socket, sample and outputs were private to `$ESS_RUNTIME_PARENT/ess-research/issue64/runs/f10-q_1y5zld/`. No other run's installation, cluster or sample was reused.
- PostgreSQL source: local Git object-store export from `/home/wqts/projects/ess-postgresql`, commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; private out-of-tree configure, `make -j2` and `make install` passed. Installed `postgres` and `pg_config` both reported **16.14**. The sample-import source `src/backend/commands/analyze_sample_cache.c` SHA-256 was `661c03c59a2a4ca1273a205d3e0c1ae2f2dc9c1fdf8c39076cd0085be6880e68`.
- Run-local PR #58 helper acquisition/import passed: commit `76106024611ae91505f1f05bdc35aed44d9c38c4`; `run_formal.py` SHA-256 `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322`; `gate_audit_v2.py` SHA-256 `03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4`.
- Environment: worktree-local `.venv`, Python 3.12.3, NumPy 2.3.4; Linux 7.0.0-38-generic, x86_64.
- One cluster; one initial sample-export ANALYZE; two sample-replay ANALYZE calls (Empty and `e00_01`); **one structured EXPLAIN attempted and completed**, zero legacy EXPLAIN calls, zero retries. The whole-run watchdog covered acquisition, compilation and execution: 1,800-second / 2,147,483,648-byte hard limits, 1,680-second / 1,610,612,736-byte early stops, 0.1-second monitoring interval.

Command executed once from the original Issue #64 worktree:

```bash
source ~/.bashrc
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B experiments/pess-multidataset-heldout-stage2b/generalization-issue64/run_forest10_setup_pilot.py --researcher-approved
```

The adapter passed the existing `client_min_messages=warning`, `plan_cache_mode=force_custom_plan` and `max_parallel_workers_per_gather=0` through startup `PGOPTIONS` to the connection issuing the single `EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF)`. This records the executed client's configuration; no extra GUC-readback or diagnostic query was issued.

Installed executable SHA-256 values:

| Binary | SHA-256 |
|---|---|
| postgres | `c7b645f25387255b778fc94ce0ea299a20cd805988599fc9dad1aea08ca22887` |
| initdb | `375a2c8afa6257303ccda3d62613c71111eb17b420858db8848be7e1946aeda3` |
| pg_ctl | `6f2c79d3641a0a51eca634f8ab00a71d1aa96d82c83defac263068c164e9a1da` |
| psql | `322538e5713b124b12f08b384b5a5cd1b1fb89f00f6db90bbb8899408e64dadc` |
| pg_config | `6e8385b27f01eab301ffad823da94b94cb10ddfd06891e5bc2c086a61f20652c` |

## Sample, configurations and accepted observation

The fresh sample came from this cluster's `public.forest10`: relation identity `6:public8:forest10`, relation OID/filenode `16384`/`16384`, 10 attributes, 7,792 relation pages, server 16.14. It contains 10,620,460 bytes with SHA-256 `e8ddc377853ba8956266665894fca993e2c72574a2c7435274115480970da855`. Export/header/hash checks and Empty/`e00_01` replay of those same bytes all passed. The binary remains local at `results/forest10.fixed-sample` under this run; it is not committed.

The `e00_01` object `ess_issue64_forest10_e00_01` existed at OID `16399` on `public.forest10`, kind `mcv`, keys `1 2`, statistics target `300`; catalog verification passed.

The complete accepted query-level diagnostic is represented by these compact fields:

| Field | Observed value |
|---|---|
| Query / source index / split | `arecel:forest10:valid:000005` / `5` / official valid |
| Configuration / static eligibility | `e00_01` / PASS |
| Diagnostic status / event count | `complete` / `1` |
| Base relation OID | `16384` |
| `nrows_preclamp` | **`0.006841835733857649`** (finite and strictly positive) |
| MCV diagnostic status | `NO_MCV_EVENTS` |
| Selected statistic IDs / MCV records | `[]` / `[]` |
| Observation error | none |

The one event was the base estimate; query/relation association passed. No MCV selection OID, clause indices or five-term MCV values were observed. Catalog existence is verified, but actual MCV-hit diagnostics remain **unverified**. No `Plan Rows` value was used or retained.

## Timing, disk and shutdown

| Phase | Seconds | Result |
|---|---:|---|
| PR #58 helper fetch/hash/import | 4.227 | PASS |
| Fixed valid-query resolution | 2.864 | PASS |
| Pinned CSV verification/extraction | 1.154 | PASS |
| PG source export/build/install aggregate | 92.957 | PASS |
| Configure / compile / install | 8.164 / 81.325 / 1.596 | PASS |
| initdb / pg_ctl start / identity check | 0.315 / 0.106 / 0.007 | PASS |
| Schema creation / CSV import / import verification | 0.005 / 0.432 / 0.021 | PASS |
| Column statistics target setup | 0.044 | PASS |
| Initial sample-export ANALYZE | 0.206 | PASS |
| Empty / `e00_01` sample replay | 0.154 / 0.184 | PASS |
| Single JSON EXPLAIN plus parsing | 0.005 | PASS |
| pg_ctl stop | 0.103 | PASS |
| Cluster lifecycle aggregate, including shutdown | 1.632 | PASS |
| Total supervisor elapsed | **102.926** | PASS |

Aggregate rows overlap their component timings and must not be summed. Measured peak allocated run-directory space was **447,463,424 bytes** (about 426.7 MiB), including source/build/install, cluster, sample and logs. Watchdog stop reason and disk-monitor error were both null; no early-stop or hard limit was triggered. Worker exit code was 0 and the shutdown check passed. A subsequent read-only `pg_ctl -D <this-run>/cluster/pgdata status` returned **3**, `no server running`; it did not start PostgreSQL or issue SQL.

## Validation and stopping point

Post-run checks: the Issue #64 offline suite (`.venv/bin/python -B -m unittest discover -s experiments/pess-multidataset-heldout-stage2b/generalization-issue64 -p 'test_*.py'`, with `PYTHONDONTWRITEBYTECODE=1`) passed **115 tests**. AST parsing passed for the runner, pilot and focused adapter tests; `git diff --check` passed. Sample, sample-import source, `postgres` and `psql` digests were independently rechecked against the run summary. No execution-code repair was needed.

This establishes successful JSON acquisition for this one fixed query under the recorded build/setup. It is consistent with the transport repair, but cannot identify the missing raw bytes or prove the exact cause of v1's parse failure. It establishes neither MCV-hit coverage nor calibration-wide completeness, throughput or decision quality.

The latest authorization covered **Phase B only**. Phase C's 20-query smoke remains **NOT RUN**, and this success is ready for researcher review of that next step. No valid/test truth, test outcomes, model fitting, calibration objective, resource selection or Q1 evaluation was accessed or computed. No full calibration is authorized by this report. Essential evidence is retained here; source copies, binaries, PGDATA, sample, SQL and detailed logs are not uploaded. PR #65 remains Draft; Issue #64 remains Open.
