# Task-local cache and invariant-precomputation ablation

This report is generated from `cache-ablation-results.json`. It is a synthetic study of the Advisor implementation; it is not evidence about PostgreSQL estimation quality.

- Python: 3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]
- Platform: Linux-7.0.0-38-generic-x86_64-with-glibc2.39
- Libraries: {'numpy': '2.5.4', 'scipy': '1.18.1', 'networkx': '3.7'}
- Repetitions per solver/instance: 7
- Limits: 10.0s complete invocation, 5.0s per inner solve
- Static baseline: unchanged full conditional MILP.
- Master variants: baseline, precompute-only, cache-only, and combined.
- The fixed-seed instance files are loaded without regeneration.
- Targeted instances are deterministic and their hashes are recorded below.

## Independent Fraction references

| Instance | SHA-256 | Evaluated subsets | Feasible subsets | Objective | Runtime (s) |
|---|---|---:|---:|---:|---:|
| medium_dense | `24341dafd5bca8f74af4b4bbac67b531b4142ca037283263b70f1197ef77819d` | 4096 | 584 | 25 | 0.059742 |
| parallel_zero_cost | `1e075f48adb8cb3969dc61798a3d0e8661379b8c9c5135e3ec4e9de670234ef3` | 256 | 146 | 21/2 | 0.008686 |
| positive_sign | `68814b40c9ddb5532f1f4b02ad07d8d9998fe5ebd881b3560c19d1c969ab3bcd` | 256 | 70 | 12 | 0.004585 |
| small_shared | `48c073cfda42005ac5dadad5031ee06fff80719b522f6b0b3716adf3dd5053fa` | 128 | 29 | 37/2 | 0.001234 |
| targeted_high_reuse | `9a545a055e273556e6495baf0a22b4467ab1091a3997fb1fb325d8f38273fe0b` | 256 | 128 | 22 | 0.010165 |
| targeted_low_reuse | `9a56871b7597374b3bcff98ae488621bec86b45896a432c704fbb3eb357f5bb5` | 256 | 128 | 43/2 | 0.007506 |
| tiny_mixed | `069ab5087da30b1d979a4bfb8738ad3d4e9a6a1ab289df6d6a23011574f88822` | 32 | 9 | 19/2 | 0.000299 |

## Repeated solver summaries

| Instance | Solver | Statuses | Objective(s) | Median s | IQR s | Cuts | Task computations | Cache hits | Hit rate | Inner MIP solves |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| medium_dense | master_oracle_baseline | {'optimal': 7} | ['25'] | 0.728555 | 0.012433 | 96.0 | 150.0 | 0.0 | 0.000 | 186.0 |
| medium_dense | master_oracle_cache | {'optimal': 7} | ['25'] | 0.679381 | 0.008325 | 96.0 | 105.0 | 45.0 | 0.300 | 136.0 |
| medium_dense | master_oracle_combined | {'optimal': 7} | ['25'] | 0.653654 | 0.011217 | 96.0 | 105.0 | 45.0 | 0.300 | 136.0 |
| medium_dense | master_oracle_precompute | {'optimal': 7} | ['25'] | 0.691448 | 0.007905 | 96.0 | 150.0 | 0.0 | 0.000 | 186.0 |
| medium_dense | static_full_conditional | {'optimal': 7} | ['25'] | 0.056109 | 0.000367 | 120.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| parallel_zero_cost | master_oracle_baseline | {'optimal': 7} | ['21/2'] | 0.082737 | 0.001457 | 24.0 | 36.0 | 0.0 | 0.000 | 36.0 |
| parallel_zero_cost | master_oracle_cache | {'optimal': 7} | ['21/2'] | 0.075160 | 0.001029 | 24.0 | 29.0 | 7.0 | 0.194 | 26.0 |
| parallel_zero_cost | master_oracle_combined | {'optimal': 7} | ['21/2'] | 0.069023 | 0.003102 | 24.0 | 29.0 | 7.0 | 0.194 | 26.0 |
| parallel_zero_cost | master_oracle_precompute | {'optimal': 7} | ['21/2'] | 0.075378 | 0.001334 | 24.0 | 36.0 | 0.0 | 0.000 | 36.0 |
| parallel_zero_cost | static_full_conditional | {'optimal': 7} | ['21/2'] | 0.010894 | 0.000299 | 37.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| positive_sign | master_oracle_baseline | {'optimal': 7} | ['12'] | 0.001368 | 0.000050 | 0.0 | 4.0 | 0.0 | 0.000 | 0.0 |
| positive_sign | master_oracle_cache | {'optimal': 7} | ['12'] | 0.001407 | 0.000080 | 0.0 | 4.0 | 0.0 | 0.000 | 0.0 |
| positive_sign | master_oracle_combined | {'optimal': 7} | ['12'] | 0.001411 | 0.000069 | 0.0 | 4.0 | 0.0 | 0.000 | 0.0 |
| positive_sign | master_oracle_precompute | {'optimal': 7} | ['12'] | 0.001365 | 0.000140 | 0.0 | 4.0 | 0.0 | 0.000 | 0.0 |
| positive_sign | static_full_conditional | {'optimal': 7} | ['12'] | 0.004952 | 0.000126 | 55.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| small_shared | master_oracle_baseline | {'optimal': 7} | ['37/2'] | 0.046772 | 0.000967 | 17.0 | 36.0 | 0.0 | 0.000 | 12.0 |
| small_shared | master_oracle_cache | {'optimal': 7} | ['37/2'] | 0.044504 | 0.000724 | 17.0 | 22.0 | 14.0 | 0.389 | 10.0 |
| small_shared | master_oracle_combined | {'optimal': 7} | ['37/2'] | 0.039936 | 0.000824 | 17.0 | 22.0 | 14.0 | 0.389 | 10.0 |
| small_shared | master_oracle_precompute | {'optimal': 7} | ['37/2'] | 0.041677 | 0.000427 | 17.0 | 36.0 | 0.0 | 0.000 | 12.0 |
| small_shared | static_full_conditional | {'optimal': 7} | ['37/2'] | 0.005539 | 0.000164 | 26.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| targeted_high_reuse | master_oracle_baseline | {'optimal': 7} | ['22'] | 0.112716 | 0.000553 | 38.0 | 64.0 | 0.0 | 0.000 | 54.0 |
| targeted_high_reuse | master_oracle_cache | {'optimal': 7} | ['22'] | 0.097365 | 0.001255 | 38.0 | 48.0 | 16.0 | 0.250 | 36.0 |
| targeted_high_reuse | master_oracle_combined | {'optimal': 7} | ['22'] | 0.088351 | 0.001864 | 38.0 | 48.0 | 16.0 | 0.250 | 36.0 |
| targeted_high_reuse | master_oracle_precompute | {'optimal': 7} | ['22'] | 0.102186 | 0.001405 | 38.0 | 64.0 | 0.0 | 0.000 | 54.0 |
| targeted_high_reuse | static_full_conditional | {'optimal': 7} | ['22'] | 0.020293 | 0.000563 | 50.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| targeted_low_reuse | master_oracle_baseline | {'optimal': 7} | ['43/2'] | 0.033026 | 0.000310 | 13.0 | 32.0 | 0.0 | 0.000 | 18.0 |
| targeted_low_reuse | master_oracle_cache | {'optimal': 7} | ['43/2'] | 0.026504 | 0.000372 | 13.0 | 19.0 | 13.0 | 0.406 | 10.0 |
| targeted_low_reuse | master_oracle_combined | {'optimal': 7} | ['43/2'] | 0.023445 | 0.000414 | 13.0 | 19.0 | 13.0 | 0.406 | 10.0 |
| targeted_low_reuse | master_oracle_precompute | {'optimal': 7} | ['43/2'] | 0.029527 | 0.000478 | 13.0 | 32.0 | 0.0 | 0.000 | 18.0 |
| targeted_low_reuse | static_full_conditional | {'optimal': 7} | ['43/2'] | 0.005412 | 0.000066 | 26.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| tiny_mixed | master_oracle_baseline | {'optimal': 7} | ['19/2'] | 0.019910 | 0.000593 | 8.0 | 15.0 | 0.0 | 0.000 | 10.0 |
| tiny_mixed | master_oracle_cache | {'optimal': 7} | ['19/2'] | 0.018657 | 0.000394 | 8.0 | 11.0 | 4.0 | 0.267 | 8.0 |
| tiny_mixed | master_oracle_combined | {'optimal': 7} | ['19/2'] | 0.016762 | 0.000250 | 8.0 | 11.0 | 4.0 | 0.267 | 8.0 |
| tiny_mixed | master_oracle_precompute | {'optimal': 7} | ['19/2'] | 0.018161 | 0.000506 | 8.0 | 15.0 | 0.0 | 0.000 | 10.0 |
| tiny_mixed | static_full_conditional | {'optimal': 7} | ['19/2'] | 0.004954 | 0.000438 | 13.0 | 0.0 | 0.0 | 0.000 | 0.0 |

## Interpretation

The references certify the exact objective for every listed small instance, including `medium_dense` (12 candidates, 4096 possible subsets). Each solver record also retains its solver status, primal and dual information, validation flags, witnesses, and fallback diagnostics. A cache hit reuses a completed task-local result and does not increment inner MIP or HiGHS invocation counters.

Runtime differences are descriptive measurements only. In particular, fewer inner solves do not by themselves establish lower end-to-end runtime; cache management and repeated master solves remain part of the measured invocation interval.
