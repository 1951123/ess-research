# Issue #14 model-level decision value study

Evidence label: **Experimentally observed** for the executed fixed JSON matrix below; the mathematical definitions and exact Fraction computations are model-internal. This study does not use PostgreSQL or real data.

- Arithmetic: exact `Fraction` inputs and objective calculations; no MILP solver was used.
- Policy scenarios: exact enumeration of every permutation of the full candidate universe, with one shared order restricted to every task.
- Nominal order: sorted candidate IDs.
- Maintenance: additive proxy from the instance JSON; no claim about generic nonadditive `Maint(M)` or physical ANALYZE cost.
- Canonical summary: `decision-value-summary.json`, 44216 bytes, SHA-256 `ad488b487940239eb9142280f8dc843438fa12ea692143cbc4bc320f107644ee`.
- Canonical raw JSONL: 3815758 bytes before compression, logical SHA-256 `0a0bd7573164c038b4cb3d739e0faee96a4cef9485ffe1107bf2f1328ce42e4f`.
- Canonical compressed raw JSONL: `decision-value-observations.jsonl.gz`, 48604 bytes, SHA-256 `9b4ac3e6e8bacd29f6a7c12897fbd8a7d2c10e86cb2f155ebdc4c1a95727c798`.
- Optimizer runtimes are isolated in the nondeterministic `decision-value-runtime.json` artifact and are not part of canonical evidence.

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
| conflict_shared_order | 0 | [] | [] | [] | 8 | 8 | 8 | 8 | 0 | 0 | 0 |
| conflict_shared_order | 3 | ['e0', 'e2'] | ['e0', 'e1', 'e2'] | ['e0', 'e2'] | 8 | 3 | 4 | 3 | 0 | 0 | 0 |

## Controlled outcome counts

The matrix has one row per fixture/budget. A nontrivial decision difference means the PESS and nominal selected sets differ. A large conservatism gap is predefined as at least 1 exact loss unit.

| Quantity | Count | Denominator |
|---|---:|---:|
| PESS and nominal sets coincide | 11 | 14 |
| PESS and nominal sets differ | 3 | 14 |
| Empty set selected by PESS | 9 | 14 |
| PESS improves worst tested loss vs empty | 5 | 14 |
| Conservatism gap at least 1 | 0 | 14 |

## Interpretation and limits

The compressed raw JSONL preserves each shared-order observation, selected set, task scheme, tested loss, and scenario regret. Scenario regret is certified here because the comparator is exhaustively solved for each tested order and budget. The PESS bound is the independent task-wise maximum over all maximal matchings; it is not asserted to be achievable by one shared policy. The observed gap therefore measures conservatism of this model-level aggregation over the enumerated shared orders.

For the optimizer-selected rows, every independent-task versus shared-order gap is exactly zero in this matrix; this is a property of these selected sets, not a general tightness result. The separate `conflict_shared_order` probe has independent bound 5, maximum shared-order loss 4, and gap 1: task `i0`'s worst witness is `{e0,e2}` while task `i1`'s is `{e1}`, and no one global order realizes both. Thus the general conservatism question is demonstrated as nontrivial but remains open beyond this controlled probe.

The hand cases intentionally include a PESS/nominal decision difference, a coincidence case, positive-sign and negative-sign controls, and multiple budgets. They are stress cases, not PostgreSQL-calibrated measurements. In particular, a lower modeled loss is not evidence of query-latency benefit, real PostgreSQL policy coverage, or physical maintenance-cost additivity. The next validation step is independent review of the instance matrix and, only if warranted, a separately scoped coupling to already recorded PostgreSQL snapshots.
