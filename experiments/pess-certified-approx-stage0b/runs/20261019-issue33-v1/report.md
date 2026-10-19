# Stage 0B pilot run

Protocol commit: `b57bfc2c5f16ecdb42a6ee28d82e4f3855ab6da7`. Code/input commit: `8547cfa56105b8db9e6a6a6e20c43ef58794d388`.

## Decision and scope

Reference B is explicitly **NOT EXECUTED** because this child task does not modify `ess-advisor` or add production solver code. Small-tier exhaustive rounded searches produce valid scoped certificates; stress-tier greedy rows without a proven global rounded lower bound remain `UNCERTIFIED_INCONCLUSIVE`. No heuristic is labeled globally optimal.

The decision is **INCONCLUSIVE**, not a solver-speedup claim: the required equal-clock unchanged same-objective baseline is unavailable. This is model-internal evidence only, not PostgreSQL maintenance or physical ANALYZE evidence.

## Deterministic summary

| setup | runs | certified | tau reached | max eta | max actual perturbation | no global rounded LB |
|---|---:|---:|---:|---:|---:|---:|
| `unrounded` | 15 | 12 | 12 | 0 | 0 | 3 |
| `coarse_uniform_delta_1` | 15 | 12 | 8 | 11/4 | 2/3 | 3 |
| `matching_aware_eta_1_2` | 15 | 12 | 11 | 1/2 | 1/3 | 3 |
| `matching_aware_eta_1_4` | 15 | 12 | 12 | 1/4 | 1/6 | 3 |

Across 60 rows, 48 had original-model certificates, 0 certificate violations occurred, and 43 reached the predeclared tau. Eight stress rows report `TRUTH_UNAVAILABLE` at the declared state cap; the remaining stress exact references completed. Timing variance is marked not estimated because each row has one diagnostic run.

See `observations.jsonl` for per-instance original-model values, rounded values, eta, actual perturbation error, state counts, and failure/timeout statuses.
