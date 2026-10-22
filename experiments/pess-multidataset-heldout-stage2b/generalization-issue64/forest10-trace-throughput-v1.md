# Forest10 valid trace-throughput probe v1

**Status: experimentally observed bounded valid-only feasibility probe. This is not a completed calibration, resource-selection result, or test evaluation.**

## Frozen scope and inputs

- Worktree branch: `research/issue64-stage2b-generalization-protocol`.
- Probe implementation frozen before execution: commit `39bd62c0bbfc3d71edcad747e447502d78b54417`; probe SHA-256 `219defc40f72fa70740d5f3ffcf954828dbb5cdb45b422dcb19fca4e510d2940`.
- Watchdog/supervisor SHA-256: `11b9c53a946cc1923ab84faeabd06846544d110ae7b6d7b7f6e5db12e6db4808`; execution command: `.venv/bin/python experiments/pess-multidataset-heldout-stage2b/generalization-issue64/run_forest10_trace_probe.py --researcher-approved`.
- Runtime: Python 3.12.3; PostgreSQL 16.14 pinned build.
- Issue #64 protocol SHA-256: `7116403e1fba83200951e0c470ff419934e5e2b77b5353f8066d7b3698412363`.
- AreCEL archive SHA-256: `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`; workload-only preparation reported `labels_loaded=false`.
- PR #58 `run_formal.py` SHA-256: `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322`; trace helper SHA-256: `03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4`.
- PostgreSQL source commit: `23c7c2fdd4bfb561f3257d947fee956a2999fdb6`; source/binary audits passed.
- Candidate preflight: 10,000 official valid queries, 45 frozen candidates, support sum 164,088; therefore the full planned calibration count is `10,000 + 164,088 = 174,088` trace-backed plans.
- Probe sample was fixed to valid source indices `0, 500, ..., 9500` (20 queries). It ran Empty on all 20 and each eligible singleton on the same sample; 46 configurations each replayed the identical exported sample. Actual trace-call count was 299 (20 Empty + 279 eligible singleton calls), bounded by 920.
- Hard limits: 10 minutes and 512 MiB allocated runtime data; supervisor soft-abort at 8 minutes / 384 MiB. No automatic retry or candidate/query replacement.

## Execution record

There were two invocations under the same predeclared workload/call/cap settings:

1. **Attempt 1 — implementation failure, not a PostgreSQL failure.** The isolated cluster and sample bootstrap succeeded; the probe then failed before issuing any trace call because it addressed `configure_statistics` on the helper module instead of the pinned `run_formal` module. Elapsed 5.812 s; peak allocated disk 188,133,376 bytes (measured); shutdown passed. Sanitized local worker-summary SHA-256 `72b8f3a68c7be101841848e114e100edcb27d6f50cbe5cb94dee0a8b53615012`; supervisor-summary SHA-256 `b4ffe0c2483af026a5294a917541028f68fd29c4784bce591632e7f05dc6cf67`. Fix was committed as `39bd62c`; no trace or estimate was retained.
2. **Attempt 2 — bounded probe successful.** Total elapsed 77.417 s; peak allocated disk 189,698,048 bytes (measured); disk monitor healthy; PostgreSQL shutdown passed and a subsequent `pg_ctl status` confirmed no server running. The exported sample was 10,620,460 bytes, SHA-256 `850b610adfec7455ed1089afd5ece6a702665b066d7f9febd5c13d97216aa110`; its sample binary was removed from the local runtime directory after the run. All 46 Empty/singleton configurations completed; all 299 planned trace calls completed and passed the pinned `run_query` trace-completeness path.

Measured `run_query` aggregate: 62.389836 s / 299 calls = **0.208662 s mean per call**, 0.310857 s maximum, 4.792447 calls/s. The 46 sample-replay ANALYZE calls took 9.307579 s total (maximum 1.177373 s). The PostgreSQL log grew by 868,944 bytes during the 46 configurations and 299 calls. No per-query Plan Rows, pre-clamp estimate, OID, SQL, or trace lines were retained in the report or worker summary. Local compact summary hashes: worker `e2138a172cc31f44bb1ffaa4f276ed3a6f5784b21b8d5655d9ba32cbbbf7a365`; supervisor `aacb72935727d8ee1a6454f6a29734afb385c0f1f2d79ff2d4eaed7749e04391`.

## Runtime and storage implications

Linear extrapolation from the 299 sampled calls gives **36,325.5 s (10.09 h)** for 174,088 `run_query` calls. Adding the observed 14.8 s of non-trace work—including the 46 replay ANALYZEs and setup—gives **36,340.3 s (10.09 h)**. The mathematical quiet-window floor alone is 34,817.6 s (9.67 h). This projection is an engineering extrapolation from 20 systematic valid queries, not a runtime guarantee; query-specific trace volume, host load, errors, and long-tail latency can change it.

The same linear calculation projects about **505,928,840 bytes (~482 MiB)** of PostgreSQL log growth for the configuration-plus-trace interval. Since this includes replay/configuration logging as well as sampled traces, and the sample spans only 20 queries, it is approximate. Combining it with the observed probe peak suggests sub-GiB order of magnitude under linear scaling, not a hard upper bound. The current Issue #64 proposal of a 24-hour wall cap and 100-GiB disposable-runtime cap is therefore not contradicted by this probe; execution must still enforce those caps, monitor allocated disk, and stop fail-closed if monitoring fails. A narrower log-growth cap must not be asserted from this small sample.

## Boundary and decision

This probe establishes that the exact PR #58 trace path is materially slower than ordinary EXPLAIN: the observed mean is dominated by its 0.20-second quiet window. It supports planning a future valid calibration within the Issue's proposed 24-hour/100-GiB envelope, subject to a separate execution authorization and a fresh preflight. It does **not** authorize or perform the 174,088-plan calibration, read valid truth for model coefficients, compute calibration objectives, choose Nominal/PESS resources, or access any test truth, estimates, traces, or outcomes. No conclusion about PESS versus Nominal is possible.
