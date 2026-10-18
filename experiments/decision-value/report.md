# Issue #14 model-level decision value study

Evidence label: **Experimentally observed** for the executed fixed JSON matrix below; the mathematical definitions and exact Fraction computations are model-internal. This study does not use PostgreSQL or real data.

- Python: `3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]`
- Platform: `Linux-7.0.0-38-generic-x86_64-with-glibc2.39`
- Arithmetic: exact `Fraction` inputs and objective calculations; no MILP solver was used.
- Policy scenarios: exact enumeration of every permutation of the full candidate universe, with one shared order restricted to every task.
- Nominal order: sorted candidate IDs.
- Maintenance: additive proxy from the instance JSON; no claim about generic nonadditive `Maint(M)` or physical ANALYZE cost.

## Method definitions

`pessimistic` minimizes the exact task-wise maximal-matching objective. `nominal` minimizes the exact loss under the sorted-ID order. `greedy_nominal` starts from the empty set and repeatedly chooses the feasible positive nominal marginal-benefit-per-cost candidate; zero-cost positive gains have infinite ratio, and nonpositive gains are rejected. `empty` always selects the empty set. Ties are resolved lexicographically by candidate IDs.

## Budget-level results

| Fixture | B | PESS set | Nominal set | Greedy set | Empty max | PESS max | Nominal max | Greedy max | PESS max regret | Nominal price | PESS bound gap |
|---|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| hand_mixed_hurts | 0 | [] | [] | [] | 29 | 29 | 29 | 29 | 0 | 0 | 0 |
| hand_mixed_hurts | 2 | ['e0'] | ['e0', 'e2'] | ['e0', 'e2'] | 29 | 43/2 | 25 | 25 | 4 | 4 | 0 |
| hand_mixed_hurts | 4 | ['e0'] | ['e0', 'e2'] | ['e0', 'e2'] | 29 | 43/2 | 25 | 25 | 4 | 4 | 0 |
| hand_mixed_coincides | 0 | [] | [] | [] | 24 | 24 | 24 | 24 | 0 | 0 | 0 |
| hand_mixed_coincides | 2 | ['e0'] | ['e0'] | ['e0'] | 24 | 20 | 20 | 20 | 0 | 0 | 0 |
| hand_mixed_coincides | 5 | ['e0', 'e4'] | ['e0', 'e4'] | ['e0', 'e4'] | 24 | 35/2 | 35/2 | 35/2 | 1/2 | 0 | 0 |
| positive_sign | 0 | [] | [] | [] | 5 | 5 | 5 | 5 | 0 | 0 | 0 |
| positive_sign | 2 | [] | [] | [] | 5 | 5 | 5 | 5 | 0 | 0 | 0 |
| positive_sign | 4 | [] | [] | [] | 5 | 5 | 5 | 5 | 0 | 0 | 0 |
| negative_sign | 0 | [] | [] | [] | 16 | 16 | 16 | 16 | 0 | 0 | 0 |
| negative_sign | 2 | [] | [] | [] | 16 | 16 | 16 | 16 | 0 | 0 | 0 |
| negative_sign | 4 | [] | [] | [] | 16 | 16 | 16 | 16 | 0 | 0 | 0 |

## Controlled outcome counts

The matrix has one row per fixture/budget. A nontrivial decision difference means the PESS and nominal selected sets differ. A large conservatism gap is predefined as at least 1 exact loss unit.

| Quantity | Count | Denominator |
|---|---:|---:|
| PESS and nominal sets coincide | 10 | 12 |
| PESS and nominal sets differ | 2 | 12 |
| Empty set selected by PESS | 8 | 12 |
| PESS improves worst tested loss vs empty | 4 | 12 |
| Conservatism gap at least 1 | 0 | 12 |

## Interpretation and limits

The raw JSON preserves each shared-order observation, selected set, task scheme, tested loss, and scenario regret. Scenario regret is certified here because the comparator is exhaustively solved for each tested order and budget. The PESS bound is the independent task-wise maximum over all maximal matchings; it is not asserted to be achievable by one shared policy. The observed gap therefore measures conservatism of this model-level aggregation over the enumerated shared orders.

The hand cases intentionally include a PESS/nominal decision difference, a coincidence case, positive-sign and negative-sign controls, and multiple budgets. They are stress cases, not PostgreSQL-calibrated measurements. In particular, a lower modeled loss is not evidence of query-latency benefit, real PostgreSQL policy coverage, or physical maintenance-cost additivity. The next validation step is independent review of the instance matrix and, only if warranted, a separately scoped coupling to already recorded PostgreSQL snapshots.
