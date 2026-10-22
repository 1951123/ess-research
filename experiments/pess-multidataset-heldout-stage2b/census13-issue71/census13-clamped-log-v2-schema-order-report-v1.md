# Census13 valid-only fit and schema-order selection

**Scope:** `clamped-log-v2`, valid-only; one predeclared Nominal order (`schema_order`). The requested ten-order search was interrupted before producing results and was not resumed. The other nine orders are unevaluated. This is not a test evaluation.

## Inputs and method

- Frozen Census13 plan SHA-256: `51842c6981936d9a5be39342eb5caee23b35f3137e5876064b0b1a649906d5e1`.
- AreCEL archive SHA-256: `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`.
- PostgreSQL: 16.14, source commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`.
- Collection: 10,000 valid queries; 78 candidates; 288,849 JSON observations (10,000 Empty + 278,849 singleton), independently verified complete. Collection elapsed 659.028 s; peak run-directory size 718,430,208 bytes; both clusters shut down normally.
- Raw observations retain the unmodified finite nonnegative `nrows_preclamp`. Counts: Empty 0 zero / 3,143 in `(0,1)`; singleton 625 zero / 154,213 in `(0,1)`. Fitting alone applies `g(x)=max(1,x)` to Empty, singleton, and valid truth.
- Valid cardinalities were reconstructed by exact `COUNT(*)` for the official valid SQL against the run-local pinned Census13 table. Only the valid workload was loaded (`labels_loaded=false`); no packaged label pickle, test truth, test estimates, or test outcomes were read.
- Corrected-log coefficients use pinned helper commit `27677a17b7455d89e92d5028d9585418550a8ff8`; Decimal `ln` at precision 80, `1e-18` half-even quantization, then exact Fraction selection. Coefficient SHA-256: `7671c4d8837c4f63423bb4a0cf1a132923301ef4f6d04cdf5ee380dfe6cbc0a5`.

## Exact selection

Every feasible set of size at most each budget was enumerated once for `schema_order`; PESS was solved globally in that same exact pass. The unique optimum at every listed method/budget has one tied set. Objective values are exact Fractions.

| Budget | Nominal (`schema_order`) set | Nominal objective | PESS set | PESS objective | Nominal set PESS loss / regret |
|---:|---|---|---|---|---|
| 0 | Empty | `4069678531214269000459/500000000000000000` | Empty | same | same / 0 |
| 2 | `e02_03, e04_06` | `733156246462852301047/125000000000000000` | `e02_03, e04_06` | same | same / 0 |
| 3 | `e01_05, e02_03, e04_06` | `5486660099511517437079/1000000000000000000` | `e01_05, e02_03, e04_06` | same | same / 0 |

Nominal and PESS agree for this one order and these budgets. This does **not** establish order stability or a method advantage; no other Nominal order was evaluated. No PostgreSQL measurement or test evaluation was run in this fitting stage.

## Reproduction and evidence

Frozen result: `census13-clamped-log-v2-schema-order-frozen-selection-v1.json`. The two compressed worker observation files and valid-only truth rows are retained beside it; each file is below 10 MB. SHA-256 values are in `census13-clamped-log-v2-evidence.sha256`. The original run directory remains intact outside the repository.

Offline checks: 10 unit tests passed (`test_census13_zero_policy`, `test_census13_schedule`, `test_census13_parallel_workers`); Python bytecode compilation and `git diff --check` passed. The exact selection ran once for the single requested order; its wall time was not separately instrumented.
