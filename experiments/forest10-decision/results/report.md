# Issue #23 Forest10 decision comparison

Evidence label: **Experimentally observed model-level fallback**. The exact arithmetic and maximal-matching definitions are model-internal. This run is not a real Forest10 workload run and contains no PostgreSQL-calibrated coefficient.

## Scope gate

The explicit Forest10 data root was absent in this Worktree. The committed ETL records provide the expected hashes, but no raw/canonical input was loaded here. Consequently, the task IDs, weights, alpha values, corrections, and costs in `instance.json` are controlled synthetic rational inputs. The six candidate endpoints are Forest10 schema-position labels, not observed PostgreSQL statistics objects.

The merged `ess-postgresql` fixed-sample implementation was audited at commit `23c7c2fdd4bfb561f3257d947fee956a2999fdb6`, but no PG calibration was run because the required real input/database fixture was unavailable. The fixed-sample replay feature therefore remains a validated interface/source fact, not an Issue #23 measurement.

## Frozen design

- Candidate universe: six precommitted two-column labeled edges over schema positions `c0`–`c5`; all six are enumerated.
- Budgets: `0`, `2`, `3`, and `5` additive proxy units; no physical maintenance interpretation.
- Nominal order: `e01,e05,e12,e23,e34,e45`.
- Shared scenarios: all `6! = 720` permutations of the full candidate universe; one order is restricted for every task.
- Ties: all exact-optimal sets retained; lexicographically smallest sorted ID tuple selected for common evaluation.
- PESS: task-wise maxima over every admissible maximal matching; this is not a shared-order maximum.
- Joint-Robust: maximum total loss over the complete shared-order set.

## Common-order comparison

| B | Method | Selected | Proxy cost | Nominal | Mean shared | Max shared | PESS bound | Bound gap |
|---:|---|---|---:|---:|---:|---:|---:|---:|
| 0 | PESS | [] | 0 | 25 | 25 | 25 | 25 | 0 |
| 0 | Nominal | [] | 0 | 25 | 25 | 25 | 25 | 0 |
| 0 | Joint-Robust | [] | 0 | 25 | 25 | 25 | 25 | 0 |
| 0 | Empty | [] | 0 | 25 | 25 | 25 | 25 | 0 |
| 2 | PESS | ['e34'] | 2 | 18 | 18 | 18 | 18 | 0 |
| 2 | Nominal | ['e34'] | 2 | 18 | 18 | 18 | 18 | 0 |
| 2 | Joint-Robust | ['e34'] | 2 | 18 | 18 | 18 | 18 | 0 |
| 2 | Empty | [] | 0 | 25 | 25 | 25 | 25 | 0 |
| 3 | PESS | ['e01', 'e34'] | 3 | 15 | 15 | 15 | 15 | 0 |
| 3 | Nominal | ['e01', 'e34'] | 3 | 15 | 15 | 15 | 15 | 0 |
| 3 | Joint-Robust | ['e01', 'e34'] | 3 | 15 | 15 | 15 | 15 | 0 |
| 3 | Empty | [] | 0 | 25 | 25 | 25 | 25 | 0 |
| 5 | PESS | ['e01', 'e12', 'e34'] | 4 | 14 | 23/2 | 14 | 14 | 0 |
| 5 | Nominal | ['e01', 'e34', 'e45'] | 5 | 21/2 | 13 | 31/2 | 31/2 | 0 |
| 5 | Joint-Robust | ['e01', 'e12', 'e34'] | 4 | 14 | 23/2 | 14 | 14 | 0 |
| 5 | Empty | [] | 0 | 25 | 25 | 25 | 25 | 0 |

## Exactness and interpretation

Each PESS, Nominal, and Joint-Robust row was selected by independent exhaustive enumeration of every feasible subset. Model values are exact `Fraction`s; the recorded elapsed times are only execution metadata. The raw artifact retains one record per method, budget, and shared order, so the reported means, extrema, and histograms can be recomputed without floating-point conversion.

A nonzero `PESS bound minus shared-order max` is a model-level aggregation gap: task-wise worst witnesses need not be jointly realizable by one global order. A lower loss for any selected set is not evidence of lower PostgreSQL latency, better real cardinality estimates, or lower physical maintenance cost.

## Commands actually executed

- `python3 experiments/forest10-decision/run_experiment.py` — exit 0; 4 budgets, 720 shared orders, and 11,520 raw observations.
- `/home/wqts/projects/ess-advisor/.venv/bin/python -m pytest -q experiments/forest10-decision/test_forest10_decision.py` — exit 0; 7 passed.
- `python3 -m py_compile experiments/forest10-decision/run_experiment.py experiments/forest10-decision/test_forest10_decision.py` — exit 0.
- The initial `python3 -m pytest ...` invocation was not runnable because the Worktree's system Python has no pytest; the available local virtualenv was used without modifying the sibling repository.

The result supports only the narrow conclusion that the three exact objectives are independently implementable and comparable on this frozen controlled instance. The real-Forest10 decision-value question remains open until an explicit verified data root and a separate PG calibration run are supplied.

Canonical summary SHA-256: `06b3534bbd2c044f179f2e12fab55c8f29ec0a7533249e6ddf843d54e37b0b6f`
Canonical raw JSONL SHA-256: `5c3a0d78bd8f56e2959213031fecfd90ff2010520cd3578e95f9b01d07874279`
Canonical raw logical SHA-256: `4d30a789516545b9b82b83f351fcd7e515386165e4050721efc3c0d4d81df7ae`
