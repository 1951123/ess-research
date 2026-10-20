# Stage 2C profiler and existing-cache result

**Issue:** #49  
**Decision:** **NO-GO** for a separate novel algorithm-development issue  
**Run date:** 2026-10-20 (Asia/Shanghai)  
**Evidence label:** experimentally observed on the frozen synthetic corpus;
source-derived for the pinned advisor cache implementation.

## Scope and freeze

The preregistration-only commit is `65950fc`; the input-only freeze commit is
`6fd2186`. The experiment used advisor source SHA
`1052ff4a46270c90414d76b32d6f6b37e5908f6a`, the public
`solve_master_oracle`, `solve_static`, and `MasterOracleOptions` APIs, and the
frozen positive pre-clamp signed maximal-matching objective. No source in
`ess-advisor` or `ess-postgresql` was changed. The seven copied Stage 1B
inputs and eight independent inputs are listed in
`input-freeze-v1.json` and checked by `SHA256SUMS-inputs`.

The isolated runtime was Python 3.12.3 with numpy 2.5.4, scipy 1.18.1,
networkx 3.7, pandas 2.3.3, pytest 8.4.2, and ruff 0.17.1. The profiler ran
one process per endpoint with a 5-second total and inner limit. The matched
comparison used three repetitions on five preregistered hard structures and
three controls. No concurrent solver processes were used; a separate memory
cgroup was not configured, so peak RSS is diagnostic only.

## Gate A — opportunity profile

The no-op wrapper delegated every `evaluate_task` call to the pinned advisor
and recorded the complete canonical task-local identity. The summary applies
the preregistered key: task identity, full labeled selected task graph,
endpoints, signed coefficients, alpha, admissibility/objective meaning,
explicit limits/tolerances, fresh solver-state contract, and implementation
pin. A conservative auxiliary digest also retained global selected labels;
the gate summary removes only that irrelevant outside-task field, so the
opportunity audit is not inflated by an under-specified key.

The frozen no-op stop rule was “stop if repeated equivalent calls consume
less than 10% of task-oracle wall time on every hard case.” It did **not**
trigger. The three repeated fractions for the material hard case
`large_sharing_cycle_3924` were 10.64%, 10.88%, and 11.21%, with seven
repeated calls each. The other hard-case medians were 0.37% for
`large_cycle_3922`, 1.24% for `large_mixed_parallel_3923`, 0% for
`shared_cycle_4905`, and 3.77% for `conflicting_cycles_4907`.

The first profile also found larger fractions in some non-hard controls,
including 40.13% on `small_sharing_cycle_3904`; these controls were retained,
not filtered. The raw profile contains 25 JSONL records across 15 cases,
including three repetitions for each hard case. See
`profile-summary-v1.json` and
`runs/20261020-profile-v1/SHA256SUMS-raw`.

## Gate B — correctness

The independent Fraction reference enumerates labeled inclusion-wise maximal
matchings and preserves parallel labels, empty selections, mixed-sign
cancellation, equal extrema, zero-cost resources, changed selected-graph
maximality, and shared task resources. It intentionally rejects a naive key
collision across changed coefficients. The cache-on/cache-off comparison on
the tiny controls and the no-op delegation test passed:

```
5 passed in 9.72s
```

This verifies the original feasible objective for those regressions. It is not
an exact global certificate for floating-point MILP status.

## Matched existing-cache comparison

The candidate treatment was not newly invented: the pinned advisor already
contains `TaskLocalOracleCache`, enabled by
`MasterOracleOptions(task_local_cache=True)`. Three 5-second repetitions were
run for unchanged Static, unchanged uncached Master–Oracle, and this existing
cache option. All returned feasible incumbents passed the independent
objective/witness checker; timeout rows are explicitly censored.

| Case | Static median s | Uncached Master median s | Existing cache median s | Cache hits/repetition | Status limitation |
|---|---:|---:|---:|---:|---|
| `large_sharing_cycle_3924` | 0.7325 | 0.1737 | 0.1655 | 7 | all three optimal |
| `conflicting_cycles_4907` | 0.4310 | 4.4196 | 4.3755 | 40 | all three optimal |
| `shared_cycle_4905` | 0.0271 | 0.0559 | 0.0569 | 0 | all three optimal |
| `large_cycle_3922` | 4.1068 | censored at 5.0 | censored at 5.0 | 9 | Master rows not optimal |
| `large_mixed_parallel_3923` | 0.7300 | censored at 5.0 | censored at 5.0 | 20 | Master rows not optimal |

The cache reduces Master–Oracle time by about 4.7% on the one material hard
case, but the same operation is already in the advisor, loses to Static on
the conflicting-cycle case, and gives no benefit on the shared-cycle control.
The three controls were also retained in `matched-summary-v1.json`; Static
was faster than both Master variants on the sharing-cycle control, while the
cache improvement on the small sharing control did not reverse that ranking.

The matched raw evidence contains 24 JSONL records and is hashed by
`runs/20261020-matched-v1/SHA256SUMS-raw`.

## Prior-art and decision

The targeted audit is in
[`notes/oracle-reuse-stage2c-prior-art.md`](../../notes/oracle-reuse-stage2c-prior-art.md).
It compares memoized oracle results, reusable separation subproblems, cut
aggregation, incremental branch-and-cut/branch-and-check, and graph-DP
caching. The exact treatment is ordinary invocation-scoped memoization and
is already implemented in the pinned advisor. The audit found no unresolved
PESS-specific research distinction that would justify relabeling it as a new
algorithm.

Therefore this work stops at **NO-GO**. No oracle-reuse treatment was added,
no source repository was modified, and no 20/60-second causal performance
claim or publication-novelty claim is made. A future incremental solver-state
or structure-aware method would require a separate bounded issue and
researcher authorization.
