# Stage 2C profiler and existing-cache result — corrected matched evidence

**Issue:** #49
**Decision:** **NO-GO** for a separate novel algorithm-development issue
**Run date:** 2026-10-20 (Asia/Shanghai)
**Evidence label:** experimentally observed on the frozen synthetic corpus;
source-derived for the pinned advisor cache implementation.

## Correction to v1

The original matched evidence in `runs/20261020-matched-v1/` is retained as
historical evidence. Its `wall_seconds` values measured the solver call only,
and its fixed in-process method order is not used for the final timing claim.
This v2 rerun uses the same frozen eight inputs, three repetitions, 5-second
endpoint, and pinned advisor source, but runs each method in a fresh process
and uses a balanced deterministic permutation of method order across
repetitions. It records both `solver_call_wall_seconds` and
`full_verified_wall_seconds`; the latter includes the independent Fraction
objective check and witness extraction.

The v2 raw evidence contains 24 JSONL records and is hashed by
`runs/20261020-matched-v2/SHA256SUMS-raw`. The derived summary is
`matched-summary-v2.json`.

## Scope and environment

The preregistration-only commit is `65950fc`; the input-only freeze commit is
`6fd2186`. The experiment used advisor source SHA
`1052ff4a46270c90414d76b32d6f6b37e5908f6a`, the public
`solve_master_oracle`, `solve_static`, and `MasterOracleOptions` APIs, and the
frozen positive pre-clamp signed maximal-matching objective. No source in
`ess-advisor` or `ess-postgresql` was changed.

The isolated runtime was Python 3.12.3 with numpy 2.5.4, scipy 1.18.1,
networkx 3.7, pandas 2.3.3, pytest 8.4.2, and ruff 0.17.1. A separate memory
cgroup was not configured, so peak RSS remains diagnostic only.

## Matched comparison

The treatment is the advisor's existing `TaskLocalOracleCache`, enabled by
`MasterOracleOptions(task_local_cache=True)`. The table reports median
`full_verified_wall_seconds` over three fresh-process repetitions. “Match” means
the solver-reported objective agrees with the independent Fraction objective;
“missing” means an independently evaluated selected set exists but the solver
objective field is absent, so no solver-objective agreement is claimed.

| Case | Static | Uncached Master | Existing cache | Verification classification |
|---|---:|---:|---:|---|
| `large_sharing_cycle_3924` | 0.6849 s | 0.1811 s | 0.1730 s | all Match |
| `conflicting_cycles_4907` | 0.3954 s | 4.3395 s | 4.3266 s | all Match |
| `shared_cycle_4905` | 0.0280 s | 0.0560 s | 0.0565 s | all Match |
| `large_cycle_3922` | 4.0168 s | 5.0385 s | 5.0408 s | cache: 2 Match, 1 missing |
| `large_mixed_parallel_3923` | 0.6978 s | 5.0401 s | 5.0352 s | both Master variants: all missing |

The three retained controls are included in `matched-summary-v2.json`; all
their rows have `SOLVER_OBJECTIVE_MATCH`. The cache has 7 hits per repetition
on `large_sharing_cycle_3924`, but the timing result remains descriptive: it
is an already implemented invocation-scoped memoization path, not a new
algorithm, and Static is faster on the conflicting-cycle and shared-cycle
cases. The timeout-adjacent Master rows are not treated as exact global
certificates.

## Correctness and provenance

The independent checker enumerates labeled inclusion-wise maximal matchings
with exact `Fraction` arithmetic and preserves parallel labels, empty
selections, mixed-sign cancellation, equal extrema, zero-cost resources, and
changed selected-graph maximality. In v2, the selected-set check is reported
separately from solver-objective agreement; no missing or mismatching solver
objective is labeled PASS.

The no-op profile and its preregistered stop rule are unchanged from v1: the
10% stop condition did not trigger on every hard case. Its raw profile remains
in `runs/20261020-profile-v1/` and is not overwritten by this correction.

## Prior art and decision

The targeted audit is in
[`notes/oracle-reuse-stage2c-prior-art.md`](../../notes/oracle-reuse-stage2c-prior-art.md).
The exact treatment is ordinary invocation-scoped memoization and is already
implemented in the pinned advisor. The corrected matched evidence does not
establish a new PESS-specific algorithmic distinction or a robust causal
performance improvement.

Therefore this work remains **NO-GO**. No oracle-reuse treatment was added,
no source repository was modified, and no 20/60-second causal performance or
publication-novelty claim is made. A future incremental solver-state or
structure-aware method requires a separate bounded issue and researcher
authorization.
