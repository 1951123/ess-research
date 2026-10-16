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
| medium_dense | `24341dafd5bca8f74af4b4bbac67b531b4142ca037283263b70f1197ef77819d` | 4096 | 584 | 25 | 0.061326 |
| parallel_zero_cost | `1e075f48adb8cb3969dc61798a3d0e8661379b8c9c5135e3ec4e9de670234ef3` | 256 | 146 | 21/2 | 0.009102 |
| positive_sign | `68814b40c9ddb5532f1f4b02ad07d8d9998fe5ebd881b3560c19d1c969ab3bcd` | 256 | 70 | 12 | 0.004149 |
| small_shared | `48c073cfda42005ac5dadad5031ee06fff80719b522f6b0b3716adf3dd5053fa` | 128 | 29 | 37/2 | 0.001285 |
| targeted_high_reuse | `9a545a055e273556e6495baf0a22b4467ab1091a3997fb1fb325d8f38273fe0b` | 256 | 128 | 22 | 0.010846 |
| targeted_low_reuse | `9a56871b7597374b3bcff98ae488621bec86b45896a432c704fbb3eb357f5bb5` | 256 | 128 | 43/2 | 0.007636 |
| tiny_mixed | `069ab5087da30b1d979a4bfb8738ad3d4e9a6a1ab289df6d6a23011574f88822` | 32 | 9 | 19/2 | 0.000299 |

## Repeated solver summaries

| Instance | Solver | Statuses | Objective(s) | Median s | IQR s | Cuts | Task computations | Cache hits | Hit rate | Inner MIP solves |
|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| medium_dense | master_oracle_baseline | {'optimal': 7} | ['25'] | 0.721835 | 0.014671 | 96.0 | 150.0 | 0.0 | 0.000 | 186.0 |
| medium_dense | master_oracle_cache | {'optimal': 7} | ['25'] | 0.690356 | 0.020264 | 96.0 | 105.0 | 45.0 | 0.300 | 136.0 |
| medium_dense | master_oracle_combined | {'optimal': 7} | ['25'] | 0.670433 | 0.009971 | 96.0 | 105.0 | 45.0 | 0.300 | 136.0 |
| medium_dense | master_oracle_precompute | {'optimal': 7} | ['25'] | 0.694737 | 0.013822 | 96.0 | 150.0 | 0.0 | 0.000 | 186.0 |
| medium_dense | static_full_conditional | {'optimal': 7} | ['25'] | 0.057513 | 0.000927 | 120.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| parallel_zero_cost | master_oracle_baseline | {'optimal': 7} | ['21/2'] | 0.083861 | 0.002881 | 24.0 | 36.0 | 0.0 | 0.000 | 36.0 |
| parallel_zero_cost | master_oracle_cache | {'optimal': 7} | ['21/2'] | 0.075706 | 0.002254 | 24.0 | 29.0 | 7.0 | 0.194 | 26.0 |
| parallel_zero_cost | master_oracle_combined | {'optimal': 7} | ['21/2'] | 0.072291 | 0.004294 | 24.0 | 29.0 | 7.0 | 0.194 | 26.0 |
| parallel_zero_cost | master_oracle_precompute | {'optimal': 7} | ['21/2'] | 0.077439 | 0.002960 | 24.0 | 36.0 | 0.0 | 0.000 | 36.0 |
| parallel_zero_cost | static_full_conditional | {'optimal': 7} | ['21/2'] | 0.011269 | 0.000426 | 37.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| positive_sign | master_oracle_baseline | {'optimal': 7} | ['12'] | 0.001415 | 0.000053 | 0.0 | 4.0 | 0.0 | 0.000 | 0.0 |
| positive_sign | master_oracle_cache | {'optimal': 7} | ['12'] | 0.001388 | 0.000060 | 0.0 | 4.0 | 0.0 | 0.000 | 0.0 |
| positive_sign | master_oracle_combined | {'optimal': 7} | ['12'] | 0.001391 | 0.000092 | 0.0 | 4.0 | 0.0 | 0.000 | 0.0 |
| positive_sign | master_oracle_precompute | {'optimal': 7} | ['12'] | 0.001341 | 0.000109 | 0.0 | 4.0 | 0.0 | 0.000 | 0.0 |
| positive_sign | static_full_conditional | {'optimal': 7} | ['12'] | 0.004852 | 0.000206 | 55.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| small_shared | master_oracle_baseline | {'optimal': 7} | ['37/2'] | 0.047711 | 0.001843 | 17.0 | 36.0 | 0.0 | 0.000 | 12.0 |
| small_shared | master_oracle_cache | {'optimal': 7} | ['37/2'] | 0.045301 | 0.001267 | 17.0 | 22.0 | 14.0 | 0.389 | 10.0 |
| small_shared | master_oracle_combined | {'optimal': 7} | ['37/2'] | 0.042656 | 0.002099 | 17.0 | 22.0 | 14.0 | 0.389 | 10.0 |
| small_shared | master_oracle_precompute | {'optimal': 7} | ['37/2'] | 0.042734 | 0.001566 | 17.0 | 36.0 | 0.0 | 0.000 | 12.0 |
| small_shared | static_full_conditional | {'optimal': 7} | ['37/2'] | 0.005827 | 0.000332 | 26.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| targeted_high_reuse | master_oracle_baseline | {'optimal': 7} | ['22'] | 0.113505 | 0.008319 | 38.0 | 64.0 | 0.0 | 0.000 | 54.0 |
| targeted_high_reuse | master_oracle_cache | {'optimal': 7} | ['22'] | 0.094703 | 0.002251 | 38.0 | 48.0 | 16.0 | 0.250 | 36.0 |
| targeted_high_reuse | master_oracle_combined | {'optimal': 7} | ['22'] | 0.086614 | 0.001949 | 38.0 | 48.0 | 16.0 | 0.250 | 36.0 |
| targeted_high_reuse | master_oracle_precompute | {'optimal': 7} | ['22'] | 0.101124 | 0.003607 | 38.0 | 64.0 | 0.0 | 0.000 | 54.0 |
| targeted_high_reuse | static_full_conditional | {'optimal': 7} | ['22'] | 0.019631 | 0.000562 | 50.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| targeted_low_reuse | master_oracle_baseline | {'optimal': 7} | ['43/2'] | 0.033477 | 0.000404 | 13.0 | 32.0 | 0.0 | 0.000 | 18.0 |
| targeted_low_reuse | master_oracle_cache | {'optimal': 7} | ['43/2'] | 0.026564 | 0.000219 | 13.0 | 19.0 | 13.0 | 0.406 | 10.0 |
| targeted_low_reuse | master_oracle_combined | {'optimal': 7} | ['43/2'] | 0.023665 | 0.000255 | 13.0 | 19.0 | 13.0 | 0.406 | 10.0 |
| targeted_low_reuse | master_oracle_precompute | {'optimal': 7} | ['43/2'] | 0.029788 | 0.000177 | 13.0 | 32.0 | 0.0 | 0.000 | 18.0 |
| targeted_low_reuse | static_full_conditional | {'optimal': 7} | ['43/2'] | 0.005428 | 0.000237 | 26.0 | 0.0 | 0.0 | 0.000 | 0.0 |
| tiny_mixed | master_oracle_baseline | {'optimal': 7} | ['19/2'] | 0.019930 | 0.000397 | 8.0 | 15.0 | 0.0 | 0.000 | 10.0 |
| tiny_mixed | master_oracle_cache | {'optimal': 7} | ['19/2'] | 0.018442 | 0.000179 | 8.0 | 11.0 | 4.0 | 0.267 | 8.0 |
| tiny_mixed | master_oracle_combined | {'optimal': 7} | ['19/2'] | 0.016790 | 0.000289 | 8.0 | 11.0 | 4.0 | 0.267 | 8.0 |
| tiny_mixed | master_oracle_precompute | {'optimal': 7} | ['19/2'] | 0.018013 | 0.000110 | 8.0 | 15.0 | 0.0 | 0.000 | 10.0 |
| tiny_mixed | static_full_conditional | {'optimal': 7} | ['19/2'] | 0.005034 | 0.000063 | 13.0 | 0.0 | 0.0 | 0.000 | 0.0 |

## Interpretation

The references certify the exact objective for every listed small instance, including `medium_dense` (12 candidates, 4096 possible subsets). Each solver record also retains its solver status, primal and dual information, validation flags, witnesses, and fallback diagnostics. A cache hit reuses a completed task-local result and does not increment inner MIP or HiGHS invocation counters.

Runtime differences are descriptive measurements only. In particular, fewer inner solves do not by themselves establish lower end-to-end runtime; cache management and repeated master solves remain part of the measured invocation interval.
