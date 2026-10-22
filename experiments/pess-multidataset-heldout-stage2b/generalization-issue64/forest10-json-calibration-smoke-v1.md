# Forest10 JSON-only calibration-observation smoke v1

**Experimentally observed: Phase C PASS within the fixed first-20-valid observation scope.** On 2026-10-22 (Asia/Shanghai), a single newly authorized run completed **212/212** predeclared structured EXPLAIN calls and **46/46** same-sample configurations, with no failed/missing observations, retry or safety stop. This is not full calibration, model fitting, resource selection, Q1 evaluation or evidence that PESS beats Nominal.

Scientific question: can the existing pinned setup and PR #7 adapter acquire complete positive pre-clamp and associated MCV diagnostics for the fixed first 20 official valid queries, using only Empty and statically eligible singleton measurements?

## Identity, pre-execution freeze and controls

- Run: `f10json-gy49u7l6`; execution code and committed call-plan SHA: `da5c547446b63231e2c7cb43ae39416069dc1867`.
- Config: [forest10-json-only-v2.json](forest10-json-only-v2.json), unchanged, SHA-256 `f6ae713b0597a2cd9eab96c9130c9f442e835b7bd7bd17511c26b85d6a277f51`.
- The [call plan](forest10-json-smoke-plan-v1.json) was committed and pushed before execution; local/live remote/PR heads agreed. SHA-256 `cb3c7748be98bf79a4e0e63ea4d35732e71f0ff0b2bb10e07a73507a4c1a136d`. Runtime recomputation had to match it exactly before PG build. It freezes IDs 000000–000019, SQL hashes, all 45 candidate IDs, eligibility and configuration order: **20 Empty + 192 singleton = 212 calls**, **Empty + 45 singleton configurations**.
- The workload-only loader checked the pinned AreCEL archive SHA-256 `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`, official valid count 10,000, full-universe static support sum 164,088, and `labels_loaded=false`. Only the first 20 valid queries were measured; no truth or test results were loaded.
- All source, build/install, PGDATA/socket and sample/output paths were private to `$ESS_RUNTIME_PARENT/ess-research/issue64/runs/f10json-gy49u7l6/`. No previous run's binaries/database/sample were reused. Socket path length was prechecked (95 bytes).
- PG source: local Git-object archive of `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; out-of-tree configure, `make -j2`, install, and both installed version checks passed (**16.14**). Sample-cache source SHA-256: `661c03c59a2a4ca1273a205d3e0c1ae2f2dc9c1fdf8c39076cd0085be6880e68`.
- Run-local PR #58 helper fetch/hash/import passed at `76106024611ae91505f1f05bdc35aed44d9c38c4`: `run_formal.py` SHA-256 `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322`; `gate_audit_v2.py` SHA-256 `03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4`.
- One private cluster, one fresh sample-export ANALYZE, 46 sample-replay ANALYZE operations, 212 JSON EXPLAIN calls, **zero legacy calls or retries**. All used the same exported sample. The inherited watcher covered helper/source acquisition, build, setup and observations: hard 1,800 s / 2,147,483,648 bytes; early stop 1,680 s / 1,610,612,736 bytes; 0.1 s sampling.

Executed once from the original Issue #64 worktree, using its existing isolated Python 3.12.3 / NumPy 2.3.4 environment:

```bash
source ~/.bashrc
PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B experiments/pess-multidataset-heldout-stage2b/generalization-issue64/run_forest10_trace_probe.py --researcher-approved
```

The historical filename does not select a legacy trace path. Each active call used `EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF)`; startup `PGOPTIONS` applied `client_min_messages=warning`, `plan_cache_mode=force_custom_plan` and `max_parallel_workers_per_gather=0`. No extra GUC-readback, probing query or plain EXPLAIN was added.

Installed binary SHA-256 values, independently rechecked after shutdown:

| Binary | SHA-256 |
|---|---|
| initdb | `3e03da30f3aa9a46b336e1bc317e768873769e5272a6500381190718a1efe1d7` |
| pg_config | `b55fafca6d21f86910c9d1100fd741348b1867fb04ef7550ea1440e3afdeac15` |
| pg_ctl | `0bac083facd2140fdf3377b6c183a3fca75d589204568aeb52c51c988ecc231b` |
| postgres | `dfcee5c54d31af2cd28a5e761133c29741c12477a36da88a2815b86ccf463bd7` |
| psql | `bd3987881cf86e7a5966599cb97c86890e80c41a854cace99df4108f878de947` |

## Fixed sample and compact observations

The fresh sample's table/header/hash validation passed for `public.forest10`: encoded identity `6:public8:forest10`, relation OID/filenode **16384/16384**, PG 16.14, 10 attributes, 7,792 relation pages, 90,000 tuples/sample target. It contained **10,620,460 bytes**, SHA-256 `0d67674d04581787b25dda6e71cf0ec53408a9b2690e203fcd1ab630bd9e8a53`. The pinned helper created each singleton MCV object with statistics target 300, requested sample import on every replay, and required the requested object's catalog name to be present. The same source/sample bytes were used throughout. No claim is made that catalog presence implies MCV use.

The retained [212 compact raw observations](forest10-json-calibration-smoke-v1.jsonl) are **86,713 bytes**, SHA-256 `44b6af801f501d2f078c92ee41d9e5c1a645f492e668d5f06258d862db981210`. They preserve query/configuration association, static eligibility, diagnostic status, finite positive `nrows_preclamp`, base relation OID, actual MCV records and errors (none). No SQL, rounded estimates, full plans or server logs are retained.

| Configuration class | Planned / complete | Complete MCV event observations | NO_MCV_EVENTS |
|---|---:|---:|---:|
| Empty | 20 / 20 | 0 | 20 |
| Eligible singletons | 192 / 192 | 102 | 90 |
| Total | 212 / 212 | 102 | 110 |

Every diagnostic had `Status=complete`, the correct base relation OID and a finite strictly positive pre-clamp estimate. Post-run comparison verified the **exact ordered query/configuration list**, zero duplicates, all eligibility flags, and the observation-file digest. No missing observation was dropped or filled from another interface.

The **102 actual MCV event records** cover 16 of the fixed 20 queries and 23 of the 45 singleton configurations. The adapter associated each event with its current configured statistic OID and candidate ID, and validated clause indexes plus `simple_sel`, `mcv_sel`, `mcv_basesel`, `mcv_totalsel`, `stat_sel`. These records are retained in full compact form. The other **90 statically eligible singleton calls had no MCV events**; no candidate or query was replaced to obtain a hit. `VERIFIED` denotes the parser's complete event association, not proof of estimate accuracy, MCV benefit or universal mechanism coverage.

Per-query counts are derived from the committed plan and retained observations (IDs have prefix `arecel:forest10:valid:` and six-digit source indexes):

| Source index | Planned / complete calls | Calls with MCV events |
|---|---:|---:|
| 0 | 2 / 2 | 1 |
| 1 | 7 / 7 | 6 |
| 2 | 1 / 1 | 0 |
| 3 | 4 / 4 | 3 |
| 4 | 2 / 2 | 0 |
| 5 | 29 / 29 | 12 |
| 6 | 2 / 2 | 0 |
| 7 | 4 / 4 | 1 |
| 8 | 4 / 4 | 1 |
| 9 | 16 / 16 | 8 |
| 10 | 22 / 22 | 12 |
| 11 | 29 / 29 | 12 |
| 12 | 16 / 16 | 5 |
| 13 | 1 / 1 | 0 |
| 14 | 16 / 16 | 10 |
| 15 | 37 / 37 | 17 |
| 16 | 2 / 2 | 1 |
| 17 | 4 / 4 | 3 |
| 18 | 7 / 7 | 4 |
| 19 | 7 / 7 | 6 |

## Time, disk and cleanup

| Stage | Seconds |
|---|---:|
| PR #58 helper fetch/hash/import | 3.874537 |
| Valid workload/eligibility preflight | 3.138132 |
| Pinned CSV extraction | 1.131075 |
| PG source export/build/install (aggregate) | 93.264639 |
| PG configure (included above) | 8.335000 |
| PG compile (included above) | 80.690000 |
| PG install (included above) | 1.561000 |
| Cluster init/start/identity | 0.431771 |
| Table load + initial sample-export ANALYZE | 0.662415 |
| Empty replay/configuration | 0.143829 |
| 45 singleton replays/configurations | 8.018942 |
| 212 structured EXPLAIN calls (aggregate) | 0.750827 |
| Cluster shutdown | 0.101263 |
| Whole supervised run | **111.796** |

Aggregate EXPLAIN client/parse time was **0.750827 s**, mean **0.003542 s/call** (about 282.36 calls/s over that aggregate only). Configuration/replay time was **8.162678 s**. These are timings of this fixed slice, not a guarantee for the complete valid workload, and not a controlled speed comparison against historical trace probes with different query schedules.

Peak allocated run-directory disk was **448,634,880 bytes**, measured by the existing polling watcher (not an exact continuous high-water mark). Monitor error and stop reason were both null; worker exit code was 0. No early-stop or hard limit was reached. Cluster shutdown returned PASS; independent post-run `pg_ctl status` returned **3, no server running**.

The worker removed its own temporary extracted CSV/schema, sample binary and server log after preserving the required identity/observations. The sample is not reconstructible byte-for-byte from its digest, but all costly accepted query observations are retained; no replay-reproducibility claim is made. No binary/source archive/PGDATA/log was submitted, and no other run was cleaned. Pre-existing ignored Python caches were left untouched; this execution/tests used `-B` and `PYTHONDONTWRITEBYTECODE=1`.

## Repairs and actually executed checks

Before this first Phase C run, offline inspection found two latent orchestration errors: sample validation was referenced before its local import, and the runner tried to recreate the results directory already created by bootstrap. Both were repaired before execution. The runner now checks the committed static plan, retains explicit failure rows/counts, preserves full compact MCV numeric records, and records initialization/shutdown timing. No scientific choice/config or historical evidence changed.

- Full offline command before and after execution: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s experiments/pess-multidataset-heldout-stage2b/generalization-issue64 -p 'test_*.py'` — **118 tests passed** each time.
- Three new focused synthetic worker tests cover the real orchestration/adapter success path (40 fake calls), malformed JSON stopping on the first call with an explicit error row, and changed query identity rejecting before PG build. They require no PostgreSQL.
- AST parsing of the changed runner/tests, `git diff --check`, raw-file digest/ordered-plan/count/positive-domain assertions, binary digest rechecks and independent stopped-status check passed. Existing `SHA256SUMS` covers the new report, plan and raw observations alongside historical entries.

## Interpretation and stopping point

The observed first-20 slice supports acquisition feasibility, complete diagnostic coverage and actual MCV association for the 102 reported singleton calls. It does not establish full-valid coverage, accuracy, corrected-log coefficient behavior, optimal resources, PESS/Nominal comparisons, held-out generalization or Q1. Static eligibility and actual MCV selection differ on this slice; zero-event observations are preserved rather than interpreted as missing data.

**Stopped after this single authorized Phase C run.** These results can inform the researcher's next approval decision, but do not authorize the full 174,088-call calibration, model fitting/selection or official test evaluation. PR #65 remains Draft; Issue #64 remains Open.
