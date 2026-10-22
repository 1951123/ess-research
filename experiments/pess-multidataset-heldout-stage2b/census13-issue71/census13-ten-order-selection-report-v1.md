# Census13 ten-order exact selection

**Result:** For this Census13 valid-only `clamped-log-v2` model, the unique Nominal global optimum is independent of the ten frozen candidate orders at budgets 0, 2, and 3. The selected sets also equal the frozen PESS global optima, with zero exact PESS regret. This is model-internal validation evidence, not a PostgreSQL or test-split result.

## Frozen inputs and execution

- Census13 plan SHA-256: `51842c6981936d9a5be39342eb5caee23b35f3137e5876064b0b1a649906d5e1`; 78 candidates, 10,000 valid tasks, complete valid observations from the existing run.
- Valid-only coefficients were deterministically rebuilt from the retained raw observations and exact valid truth with the pinned corrected-log builder; resulting coefficient SHA-256 exactly matches the existing frozen baseline: `7671c4d8837c4f63423bb4a0cf1a132923301ef4f6d04cdf5ee380dfe6cbc0a5`. No PostgreSQL operation or test data access occurred.
- The exact reference selector is from PR65 helper commit `27677a17b7455d89e92d5028d9585418550a8ff8`; its `forest10_exact_selection.py` SHA-256 is `75265ea7d256eb62ec17bd1c8c46dd670e52ad4ecd8ebac64cc7c0953bbfe97a`.
- PESS global results were reused from the frozen schema-order result. The run enumerated all feasible subsets for Nominal only; no PESS global optimization was repeated.
- All ten predeclared orders ran as independent processes, each enumerating 1, 3,082, and 79,158 feasible sets for B=0,2,3. The Nominal-only execution specialization was regression-tested against the pinned combined exact selector on small instances; arithmetic remains exact integer/Fraction with its original enumeration and tie order.
- Ten workers ran on the 12-core VM. Preflight MemAvailable was 14,402,138,112 bytes; minimum during execution was 12,766,089,216 bytes. Per-process peak RSS was 205.0–205.3 MiB. Overall selection wall time was 871.905 s; per-order times and RSS are in the machine-readable result.
- Frozen plan labels are `schema_order`, `complete_reverse`, and `python_random_seed_0`…`python_random_seed_7`; these correspond to the task's aliases `schema_order`, `reverse_order`, and `seed_0`…`seed_7`. Full permutations and SHA-256 are recorded for every order.

## Findings

| Budget | Unique Nominal optimum across 10 orders | Nominal objective (all orders) | PESS optimum | PESS regret |
|---:|---|---|---|---:|
| 0 | Empty | `4069678531214269000459/500000000000000000` | Empty | 0 |
| 2 | `e02_03, e04_06` | `733156246462852301047/125000000000000000` | `e02_03, e04_06` | 0 |
| 3 | `e01_05, e02_03, e04_06` | `5486660099511517437079/1000000000000000000` | `e01_05, e02_03, e04_06` | 0 |

There is one distinct optimum set at each budget and one distinct Nominal objective value at each budget across all orders: three distinct sets across all budget rows. No budget shows order sensitivity, and no optimal set contains overlapping column pairs. Nominal and PESS optima agree at every budget; no tested Nominal optimum has positive PESS regret. Thus this experiment finds no OID-order sensitivity or model-level PESS robustness advantage for the frozen Census13 valid workload and these budgets. It does not establish order invariance outside these inputs, nor any actual PostgreSQL behavior or test-set benefit.

The machine-readable exact result is `census13-clamped-log-v2-ten-order-selection-v1.json`; SHA-256 checks are recorded in `census13-ten-order-selection-v1.sha256`. The earlier single-order result and all observation/failure evidence remain unchanged.

Offline checks: 12 unit tests passed, including exact equality with the pinned selector on small fixtures; Python compilation and `git diff --check` passed. All ten order processes completed successfully and the main process validated schema-order equality, model hash, budgets, feasible-set counts, unique permutation identities, PESS reuse, and nonnegative regret.
