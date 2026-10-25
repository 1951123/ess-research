# Issue #99 resource and parallelism revision v4

## Authorized execution envelope

On 2026-10-25 the researcher selected six workers for the remaining DMV11 and Power7 collections and raised the per-dataset hard disk ceiling to 20 GiB. Protocol v4 caps selectable worker parallelism at six, uses a 19-GiB early stop and a 20-GiB hard stop, and retains the existing 7.5-hour early and 8-hour hard wall limits. The one-GiB cushion exceeds the roughly 0.28-GiB stop overshoot observed in v3. At authorization time, the runtime filesystem had 54,033,010,688 bytes free and the host reported 14,297,587,712 bytes of MemAvailable.

Completed Forest10 and Census13 runs remain pinned to v2 and are not rerun. All prior DMV11 v2/v3 attempts remain separately preserved. The scientific inputs, train-only boundary, model fitting, candidate schedule, PostgreSQL measurement, and selection limits are unchanged; v4 changes the worker ceiling and resource envelope only.

## Sizing basis and limits

The v3 12-worker DMV11 setup attempts motivated a low-confidence 22–24-GiB full-run estimate. Halving the estimated per-worker cluster copies while retaining the shared run footprint gives a six-worker setup estimate of about 12.4 GB decimal (11.5 GiB); adding the historical DMV11 compressed-observation estimate gives about 11.6 GiB. Allow roughly **12–14 GiB** for planning. This is a linear extrapolation from a partial setup, not an observed six-worker result; no six-worker DMV11 run has completed setup. Historical sizing estimated DMV11 measurement at 8,624 seconds (about 2.4 hours) before setup; this is based on a previous valid-only collection and does not assume six-worker linear speedup. Protocol v4 retains 7.5/8-hour stop limits and 19/20-GiB disk limits.

The selected command for the next DMV11 acquisition is `run_issue99.py collect dmv11 --parallelism 6`. Dataset runs remain serial. If DMV11 completes, Power7 is collected at six workers under the same v4 envelope. Any resource-stopped run remains INCOMPLETE with its own run ID and raw evidence; no subsampling is allowed.

