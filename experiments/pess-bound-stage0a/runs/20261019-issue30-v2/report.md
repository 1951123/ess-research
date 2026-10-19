# Stage 0A pilot report

This report is an experimentally observed result from the frozen Issue #30
pilot, not a theorem or a novelty claim.

## Scope and provenance

- Manifest: pilot-manifest-v2.json (SHA-256 8b776eaa83bd3dd6bab8fc4bf37ed0833eb9f1abc07c0226c8530d5508e4c650).
- Instances: 8 (four deterministic strata and four frozen seeds).
- Evaluated feasible branch states: 1552; rejected forced-infeasible states: 356.
- Arithmetic: exact Fraction for objectives, matching extrema, bounds and feasibility; timings are diagnostic floating-point measurements only.
- Branch optimum: exhaustive completions, cross-checked by the definition reference and a separate bitmask implementation; this validates graph enumeration independently, not every arithmetic subroutine.
- Sampling: This v2 run uses the predeclared balanced round-robin sampler over first-resource status, assigned depth, and forced-selected count.
- Sampling counts: first-resource status {'excluded': 659, 'undecided': 650, 'forced_selected': 599}; assigned-depth counts {'0': 8, '1': 78, '2': 227, '3': 321, '4': 372, '5': 401, '6': 327, '7': 140, '8': 34}.
- Integrity: The balanced v2 artifact was generated and hashed in this run.
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
| A_global_floor | 1552 | 42 | 1510 | 303 |
| B_exact_sensitivity | 1552 | 472 | 1080 | 878 |
| B_fractional_sensitivity | 1552 | 448 | 1104 | 870 |
| C_greedy_witness | 1552 | 906 | 646 | 1355 |
| C_exact_witness | 1552 | 1183 | 369 | 1361 |

The fixed incumbent is the exact minimum over all feasible resource subsets
of each frozen instance. Pruning counts therefore mean only that the bound
certifies a node cannot beat that common incumbent; they are not end-to-end
branch-and-bound speed measurements.

Pairwise nonzero-strength counts were: greedy witness > A floor =
1320, greedy witness > B exact sensitivity =
959, and exact-prefix witness > greedy witness =
319.

## Cost observations

The runner separately accumulated exact F(M) time (0.032352s),
greedy witness/q-extrema time (0.047471s), exact
worst-prefix witness/q-extrema time (0.073625s),
and q-extrema calls (3595 greedy,
4186 exact). These are tiny-instance local
measurements, not a system performance claim.

| Method | Total bound time (seconds) | Pruned nodes / second |
|---|---:|---:|
| A_global_floor | 0.000385 | 786096.2139777001 |
| B_exact_sensitivity | 0.074894 | 11723.161623591517 |
| B_fractional_sensitivity | 0.043374 | 20058.218638445396 |
| C_greedy_witness | 0.047471 | 28543.647490585827 |
| C_exact_witness | 0.073625 | 18485.603402133096 |

B totals include the exact F(M) acquisition cost, as required by the fair
comparison contract. C exact includes both greedy and exhaustive worst-prefix
witness work. These costs are diagnostic tiny-instance measurements only;
they do not establish end-to-end branch-and-bound speed.

Ordinary-matching extrema calls were separated into 18
global-floor precomputation calls, 7781 per-node
q-extrema calls, and 7799
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
