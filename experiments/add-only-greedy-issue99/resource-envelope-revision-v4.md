# Issue #99 resource and parallelism revision v4

## Authorized execution envelope

On 2026-10-25 the researcher selected six workers for the remaining DMV11 and Power7 collections and raised the per-dataset hard disk ceiling to 20 GiB. Protocol v4 caps selectable worker parallelism at six, uses a 19-GiB early stop and a 20-GiB hard stop, and retains the existing 7.5-hour early and 8-hour hard wall limits. The one-GiB cushion exceeds the roughly 0.28-GiB stop overshoot observed in v3. At authorization time, the runtime filesystem had 54,033,010,688 bytes free and the host reported 14,297,587,712 bytes of MemAvailable.

Completed Forest10 and Census13 runs remain pinned to v2 and are not rerun. All prior DMV11 v2/v3 attempts remain separately preserved. The scientific inputs, train-only boundary, model fitting, candidate schedule, PostgreSQL measurement, and selection limits are unchanged; v4 changes the worker ceiling and resource envelope only.

## Sizing basis and limits

The v3 12-worker DMV11 setup attempts motivated a low-confidence 22–24-GiB full-run estimate. Halving the estimated per-worker cluster copies while retaining the shared run footprint gives a six-worker setup estimate of about 12.4 GB decimal (11.5 GiB); adding the historical DMV11 compressed-observation estimate gives about 11.6 GiB. This was planning-only; the completed six-worker run below measured 14,428,110,848 bytes (about 13.43 GiB). Historical sizing estimated DMV11 measurement at 8,624 seconds (about 2.4 hours) before setup; the observed collection time was substantially shorter and is specific to this run, not a throughput guarantee. Protocol v4 retains 7.5/8-hour stop limits and 19/20-GiB disk limits.

## DMV11 six-worker result

**Experimentally observed:** Collection run `20261025T083515Z-issue99-dmv11-16fd8a`, pinned to research commit `c4a161f74fb178526426b2e23f33cddd1f3ae8df` and protocol-v4 SHA-256 `2f40b265bacc96d965b59bcdccc25c9bb73e3a4d99481a82107db0542343a9e6`, completed all 2,094,044/2,094,044 expected train observations with six workers. Collection elapsed time was 2,849.856 seconds; total wall time was 2,851.137 seconds. Peak allocated disk was 14,428,110,848 bytes (about 13.43 GiB), below the 19-GiB early stop. The identical 8,820,422-byte PostgreSQL 16.14 ANALYZE sample (90,000 tuples; SHA-256 `fc1013bb57547aaed5e15bab4de0f126ce21d0e781b5a66d7eabe21423fee249`) was replayed to all six worker clusters. The collection code imported the full source CSV and verified its table row count on each worker before replaying that sample. Stopped clusters, source/build directories, and input CSV were removed after shutdown; query-level observations and compact provenance remain in the external Issue #99 runtime root.

Selection run `20261025T092424Z-issue99-dmv11-selection-79f148` completed all 10/10 frozen Nominal/PESS cases for budgets 0/2/3/4/5; none hit the 600-second advisor limit. Every case completed with termination reason `no_feasible_candidate`. The run is pinned to the same research commit and protocol hash, consumed the train-only collection, and did not use non-train labels or test EXPLAIN observations. The selection manifest and case-level evidence remain under the external runtime root.

Power7 is the next dataset to collect at six workers under the same v4 limits. Dataset runs remain serial. Any resource-stopped run remains INCOMPLETE with its own run ID and raw evidence; no subsampling is allowed.

