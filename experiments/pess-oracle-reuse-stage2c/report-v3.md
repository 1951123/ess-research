# Stage 2C matched comparison — preregistered cyclic-balanced rerun

**Issue:** #49
**Decision:** **NO-GO** for a separate novel algorithm-development issue
**Run date:** 2026-10-20 (Asia/Shanghai)
**Evidence label:** experimentally observed on the frozen synthetic corpus;
source-derived for the pinned advisor cache implementation.

## Why v3 exists

The v1 raw evidence is retained as historical evidence. The v2 rerun fixed
fresh-process isolation and separated solver-call from verification time, but
its actual method order was unbalanced: cached Master was first in 16 of 24
case/repetition blocks, Static in 8, and uncached Master in 0. The v2 raw
evidence and summary are preserved and explicitly marked exploratory.

Before collecting v3 results, `matched-v3-protocol.json` was committed with a
fixed cyclic schedule:

1. Static → uncached Master → existing cache
2. uncached Master → existing cache → Static
3. existing cache → Static → uncached Master

The same schedule is used for every frozen input, so each method occupies each
position once per case. Every method still runs in a fresh worker process, and
the order is selected only by repetition index, not by observed outcome.

## Scope, inputs, and environment

The preregistration-only commit is `65950fc`; the input-only freeze is
`6fd2186`; the v3 schedule protocol is committed in `2e1b403`; and the v3
harness is committed in `80a6ce4`. The experiment used advisor source SHA
`1052ff4a46270c90414d76b32d6f6b37e5908f6a`, the public
`solve_master_oracle`, `solve_static`, and `MasterOracleOptions` APIs, and the
same frozen eight matched inputs as v1/v2. No source in `ess-advisor` or
`ess-postgresql` was changed.

The isolated runtime was Python 3.12.3 with numpy 2.5.4, scipy 1.18.1,
networkx 3.7, pandas 2.3.3, pytest 8.4.2, and ruff 0.17.1. A separate memory
cgroup was not configured, so peak RSS remains diagnostic only.

The v3 raw evidence contains 24 JSONL records and is hashed by
`runs/20261020-matched-v3/SHA256SUMS-raw`. The derived summary is
`matched-summary-v3.json`; its method-position counts are `[8, 8, 8]` for
each method.

## Timing definition

`solver_call_wall_seconds` starts immediately before the solver call and ends
when the solver returns. `full_verified_wall_seconds` starts at the same point
and ends after the independent exact Fraction objective and witness check.
Both exclude subprocess launch/import, `read_instance`, parent JSON parsing,
and output writing. They are solver-plus-verifier times, not total
process-launch-to-verified-output time.

## Matched comparison

The treatment is the advisor's existing `TaskLocalOracleCache`, enabled by
`MasterOracleOptions(task_local_cache=True)`. The table reports median
`full_verified_wall_seconds` over three repetitions. “Match” means the solver
objective agrees with the independent Fraction objective. “Missing” means an
independently evaluated selected set exists but the solver objective is absent;
it is not a matched-solution-quality result or an exact global certificate.

| Case | Static | Uncached Master | Existing cache | Verification classification |
|---|---:|---:|---:|---|
| `large_sharing_cycle_3924` | 0.6945 s | 0.1739 s | 0.1656 s | all Match |
| `conflicting_cycles_4907` | 0.3889 s | 4.3274 s | 4.3028 s | all Match |
| `shared_cycle_4905` | 0.0278 s | 0.0570 s | 0.0569 s | all Match |
| `large_cycle_3922` | 3.9564 s | 5.0342 s | 5.0483 s | uncached: 2 Match/1 missing; cache: 1 Match/2 missing |
| `large_mixed_parallel_3923` | 0.6992 s | 5.0376 s | 5.0429 s | uncached: 1 Match/2 missing; cache: all missing |

The three retained controls are included in `matched-summary-v3.json`; all
their rows have `SOLVER_OBJECTIVE_MATCH`. The cache has 7 hits per repetition
on `large_sharing_cycle_3924`, but this remains a descriptive observation. It
is already implemented invocation-scoped memoization, and Static is faster on
the conflicting-cycle and shared-cycle cases. No causal cache-speedup claim is
made.

## Correctness and decision

The independent checker enumerates labeled inclusion-wise maximal matchings
with exact `Fraction` arithmetic and preserves parallel labels, empty
selections, mixed-sign cancellation, equal extrema, zero-cost resources, and
changed selected-graph maximality. Missing solver objectives and timeout
incumbents are classified separately from exact objective agreement.

The no-op profile and its preregistered stop rule are unchanged from v1: the
10% stop condition did not trigger on every hard case. Its raw profile remains
in `runs/20261020-profile-v1/`.

The prior-art audit is in
[`notes/oracle-reuse-stage2c-prior-art.md`](../../notes/oracle-reuse-stage2c-prior-art.md).
The exact treatment is routine existing advisor memoization, not a new PESS
algorithmic distinction. Therefore this work remains **NO-GO**. No oracle
reuse treatment was added, no universal caching claim is made, and no
publication-novelty claim is made. A future incremental solver-state or
structure-aware method requires a separate bounded issue and researcher
authorization.
