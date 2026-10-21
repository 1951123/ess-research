# Forest10 JSON-only integration pilot v1

**Outcome: FAILED at structured JSON parsing; PostgreSQL setup passed.** This is one authorized run only. The strict adapter rejected the output of the one requested `EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF)` call as invalid JSON. No pre-clamp estimate, diagnostic status, or MCV event was accepted. The run stopped; no retry and no Phase C smoke were performed.

## Frozen execution identity

- Run ID: `f10-ohrhuem2`; execution code commit: `204ad730534d4cff314782dd982c2d9e54ae3fc2`.
- PostgreSQL source: independently exported from local Git object store at `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; source file `src/backend/commands/analyze_sample_cache.c` SHA-256 `661c03c59a2a4ca1273a205d3e0c1ae2f2dc9c1fdf8c39076cd0085be6880e68`.
- Private out-of-tree build and install succeeded. Installed versions: PostgreSQL 16.14 (`postgres`, `pg_config`). Binary SHA-256: `postgres` `b331f60162e130040cd02b1d7d4704ea5fb05dcd2079e55095d7df302416b81b`; `initdb` `0482a40a1bb26d6791851562f72ddf7f1a554e6c6832302152c8c954bca04772`; `pg_ctl` `6a4b0dfbfed123b8eb2eb8571521ca3f380de65c3aea4a35c61d82a2a2828aab`; `psql` `cd26fe855bb718921ab514fd8179e34ec4864ce437787ebc7ba4b5a4d45787dd`; `pg_config` `238cf4e057f44c4c92170dfec1ab291d8d578679c6e3705932b8eaf4aac318b5`.
- PR #58 model/setup helper commit and file hashes passed: commit `76106024611ae91505f1f05bdc35aed44d9c38c4`, `run_formal.py` `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322`, `gate_audit_v2.py` `03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4`.
- The fixed sample was exported from this run's `public.forest10`: relation identity `6:public8:forest10`, relation OID/filenode `16384`/`16384`, 10 attributes, server 16.14, 10,620,460 bytes, SHA-256 `96a3827b30a3a495dc5c55358192b27b8fcb6c8ce153e5ab432204f616309dd0`. Empty and `e00_01` replay ANALYZE passed on this same sample. The `e00_01` MCV object was verified at OID `16399`, relation `public.forest10`, keys `1 2`, target `300`.
- The only requested query was `arecel:forest10:valid:000005` (source index 5), statically eligible for `e00_01`. Structured EXPLAIN attempts: **1**; accepted/completed diagnostic records: **0**. No legacy EXPLAIN was run. No truth, objective, selection, test query, or test outcome was accessed.

## Failure and resources

The run summary records `ValueError: structured EXPLAIN output is not valid JSON` at phase `structured_valid_explain`. The raw psql output was intentionally not retained, so the underlying output bytes and precise formatting cause are **unresolved**. Static source inspection confirms the pinned helper returns psql stdout verbatim and the adapter parses it as one JSON document; this localizes the failure to the transport/serialization boundary but does not establish whether command-tag text or another format detail caused it. The estimate and MCV state are therefore **unknown**, not zero and not `NO_MCV_EVENTS`.

| Phase | Seconds | Result |
|---|---:|---|
| PR #58 helper fetch/hash/import | 4.036 | PASS |
| Valid query resolution | 2.246 | PASS |
| PostgreSQL configure / compile / install | 8.150 / 82.378 / 1.590 | PASS |
| Fresh table bootstrap, sample export and initial ANALYZE | 0.757 | PASS |
| Empty / `e00_01` sample replay ANALYZE | 0.154 / 0.177 | PASS |
| Structured EXPLAIN call / parse | 0.004 / failed | FAIL |
| Total supervisor elapsed | **102.971** | below limits |

Watchdog status: no monitor error or stop reason; measured peak allocated run-directory space **447,614,976 bytes** (below the 1.5-GiB early stop and 2-GiB hard cap). PostgreSQL shutdown check passed; no live run PostgreSQL process remained on read-only post-run inspection.

## Interpretation and stop

The run experimentally verifies the isolated PG source build/install, fresh same-cluster sample export, both treatment replays, and the statistics catalog setup. It does **not** verify successful structured diagnostics, positive pre-clamp extraction, or MCV event reporting. Phase B did not meet its success gate, so the conditional 20-query Phase C calibration-observation smoke was **NOT RUN**. Full calibration, model fitting/resource selection, and test evaluation remain unperformed. The parser/transport defect needs code-only diagnosis before any separately approved future run; this report does not authorize another PostgreSQL attempt.
