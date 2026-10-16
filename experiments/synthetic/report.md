# Synthetic PESS-ESS benchmark integrity rerun

This report is generated from the repeated fixed-seed benchmark. Historical exhaustive-reference runtimes were invalid because the old runner started its timer before an empty wrapper rather than around solve_exhaustive; they are replaced by the measurements below.

- Python: 3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]
- Platform: Linux-7.0.0-38-generic-x86_64-with-glibc2.39
- Libraries: {'numpy': '2.5.4', 'scipy': '1.18.1', 'networkx': '3.7'}
- Backend: SciPy optimize.milp with HiGHS
- Repetitions: 5; warm-up: none; all recorded runs are cold-start benchmark observations
- Timing: external monotonic interval around one solver invocation; serialization and report generation are excluded.
- Limits: master 10.0 s; inner 5.0 s; the same total wall-clock limit is applied to each outer invocation.

## Repeated runtime summaries

| Instance | Solver | Reps | Median (s) | Min (s) | Max (s) | IQR (s) | Status counts | Median iterations | Median cuts | Median inner MIP calls | Median early exits | Fallbacks |
|---|---|---:|---:|---:|---:|---:|---|---:|---:|---:|---:|---:|
| medium_dense | master_oracle | 5 | 0.714770 | 0.706026 | 0.727075 | 0.013410 | {'optimal': 5} | 25.0 | 96.0 | 186.0 | 57.0 | 0.0 |
| medium_dense | static_full_conditional | 5 | 0.055300 | 0.054038 | 0.056529 | 0.000823 | {'optimal': 5} | 1.0 | 120.0 | 0.0 | 0.0 | 0.0 |
| parallel_zero_cost | exhaustive_reference | 5 | 0.008846 | 0.008675 | 0.011940 | 0.000412 | {'optimal': 5} | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| parallel_zero_cost | master_oracle | 5 | 0.083843 | 0.080444 | 0.089983 | 0.005376 | {'optimal': 5} | 9.0 | 24.0 | 36.0 | 18.0 | 0.0 |
| parallel_zero_cost | static_full_conditional | 5 | 0.010812 | 0.010748 | 0.012396 | 0.000414 | {'optimal': 5} | 1.0 | 37.0 | 0.0 | 0.0 | 0.0 |
| positive_sign | exhaustive_reference | 5 | 0.004177 | 0.004026 | 0.004301 | 0.000237 | {'optimal': 5} | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| positive_sign | master_oracle | 5 | 0.001438 | 0.001409 | 0.001515 | 0.000011 | {'optimal': 5} | 1.0 | 0.0 | 0.0 | 4.0 | 0.0 |
| positive_sign | static_full_conditional | 5 | 0.004871 | 0.004767 | 0.004953 | 0.000025 | {'optimal': 5} | 1.0 | 55.0 | 0.0 | 0.0 | 0.0 |
| small_shared | exhaustive_reference | 5 | 0.001311 | 0.001247 | 0.001342 | 0.000012 | {'optimal': 5} | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| small_shared | master_oracle | 5 | 0.046160 | 0.045519 | 0.046752 | 0.000182 | {'optimal': 5} | 9.0 | 17.0 | 12.0 | 30.0 | 0.0 |
| small_shared | static_full_conditional | 5 | 0.005394 | 0.005388 | 0.005505 | 0.000006 | {'optimal': 5} | 1.0 | 26.0 | 0.0 | 0.0 | 0.0 |
| tiny_mixed | exhaustive_reference | 5 | 0.000273 | 0.000254 | 0.000364 | 0.000016 | {'optimal': 5} | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 |
| tiny_mixed | master_oracle | 5 | 0.019920 | 0.019370 | 0.020213 | 0.000398 | {'optimal': 5} | 5.0 | 8.0 | 10.0 | 10.0 | 0.0 |
| tiny_mixed | static_full_conditional | 5 | 0.005028 | 0.004933 | 0.006599 | 0.000095 | {'optimal': 5} | 1.0 | 13.0 | 0.0 | 0.0 | 0.0 |

## Correctness and certification

- **medium_dense** (12 candidates, 6 tasks): no exhaustive reference; MIP results are not independently globally certified.
- **parallel_zero_cost** reference objective: '21/2'.
  - static_full_conditional: reference agreement 'True' over 5 repetitions; numerical warnings '0'.
  - master_oracle: reference agreement 'True' over 5 repetitions; numerical warnings '5'.
- **positive_sign** reference objective: '12'.
  - static_full_conditional: reference agreement 'True' over 5 repetitions; numerical warnings '0'.
  - master_oracle: reference agreement 'True' over 5 repetitions; numerical warnings '0'.
- **small_shared** reference objective: '37/2'.
  - static_full_conditional: reference agreement 'True' over 5 repetitions; numerical warnings '0'.
  - master_oracle: reference agreement 'True' over 5 repetitions; numerical warnings '15'.
- **tiny_mixed** reference objective: '19/2'.
  - static_full_conditional: reference agreement 'True' over 5 repetitions; numerical warnings '0'.
  - master_oracle: reference agreement 'True' over 5 repetitions; numerical warnings '0'.

## Phase and numerical interpretation

The static formulation enumerates all matching scenarios; its scenario count is a formulation-size diagnostic. Master--Oracle cut counts are generated conditional scenarios, not a proof of runtime superiority. Exact inner-oracle invocations and inner MIP solves are separate counters; one exact oracle may use two MIP solves. Ordinary matching bounds and witness construction are timed separately from exact inner MIP work.

The result schema records a MIP primal incumbent separately from the HiGHS dual bound. A solver-reported optimal status is not treated as an exact-arithmetic proof. Near-tolerance violations are retained as warnings. A failed validation, unresolved inner solve, or global deadline is not interpreted as an optimum.

These are synthetic measurements only. They do not establish PostgreSQL behavior, asymptotic guarantees, or algorithmic superiority. Small runtimes can be dominated by process and backend noise; medians and ranges should be interpreted accordingly.
