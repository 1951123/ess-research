# Stage 0A pilot report

This report is an experimentally observed result from the frozen Issue #30
pilot, not a theorem or a novelty claim.

## Scope and provenance

- Manifest: pilot-manifest.json (SHA-256 83a26e8c818652a0b07d54ff2efeedcb4aca482cfc3ea634bc17f52877cd04a8).
- Instances: 8 (four deterministic strata and four frozen seeds).
- Evaluated feasible branch states: 1708; rejected forced-infeasible states: 200.
- Arithmetic: exact Fraction for objectives, matching extrema, bounds and feasibility; timings are diagnostic floating-point measurements only.
- Branch optimum: exhaustive completions, cross-checked by the definition reference and a separate bitmask implementation in the follow-up validation; this qualifies graph-enumeration independence, not every arithmetic subroutine.
- Sampling limitation: v1 uses the first 300 lexicographically enumerated ternary states after root. For larger instances this strongly overrepresents early excluded-resource statuses and does not include balanced forced-selected/depth strata. Its comparison counts are descriptive only and are not generalized empirical claims.
- Integrity reconciliation: the first PR publication used a large-file API transport that changed the raw blob bytes, causing CI to reject the committed SHA. A corrective commit restored the exact local raw blob and retained the original v1 observations; v1 was not silently rerun or changed.
- Run status: **PASS**; counterexamples: 0.

## Correctness

The exact reference enumerates labeled ordinary matchings and filters maximal
matchings directly from the definitions. The runner checked both witness
bounds pointwise for every feasible completion and against the exact branch
optimum. A rejected forced set is recorded as rejected, never assigned a
fictitious objective. See counterexamples.json for any preserved failures.
The formalized statement and proof under the tested assumptions are in
../../lemma.md.

## Bound comparison

| Bound | Nodes | Exact branch optimum | Positive gap | Prunable by fixed exact incumbent |
|---|---:|---:|---:|---:|
| A_global_floor | 1708 | 19 | 1689 | 313 |
| B_exact_sensitivity | 1708 | 479 | 1229 | 970 |
| B_fractional_sensitivity | 1708 | 459 | 1249 | 966 |
| C_greedy_witness | 1708 | 1068 | 640 | 1485 |
| C_exact_witness | 1708 | 1351 | 357 | 1491 |

The fixed incumbent is the exact minimum over all feasible resource subsets
of each frozen instance. Pruning counts therefore mean only that the bound
certifies a node cannot beat that common incumbent; they are not end-to-end
branch-and-bound speed measurements.

Pairwise nonzero-strength counts were: greedy witness > A floor =
1558, greedy witness > B exact sensitivity =
1153, and exact-prefix witness > greedy witness =
297.

## Cost observations

The runner separately accumulated exact F(M) time (0.028906s),
greedy witness/q-extrema time (0.052075s), exact
worst-prefix witness/q-extrema time (0.077270s),
and q-extrema calls (4020 greedy,
4609 exact). These are tiny-instance local
measurements, not a system performance claim.

The v1 run did not time exact/fractional knapsack separately and did not
report pruned nodes per second. Its results therefore establish bounded
tightness diagnostics only. The predeclared v2 follow-up adds balanced
sampling and complete method-cost accounting without replacing v1.

Ordinary-matching extrema calls were separated into 18
global-floor precomputation calls, 8629 per-node
q-extrema calls, and 8647
total. Every reported witness was independently checked to be maximal in its
forced selected task graph.

## Comparator D

The existing restricted-master comparator was not executed. Issue #30 requires
the same node restrictions and a solver-proven or explicitly qualified bound,
while its authorized scope forbids modifying ess-advisor or building a new
solver. It is a separately scoped follow-up, not silently approximated here.

## Recommendation

**INCONCLUSIVE.** The exact reference passed, but the tiny corpus and lack of a fair restricted-master comparator cannot establish end-to-end value.

The result supports only the bounded mathematical diagnostic. It does not
prove theorem novelty, PostgreSQL behavior, or end-to-end optimizer speedup.
