# Stage 1B solver-scaling diagnosis — final v2

Evidence label: **experimentally observed** for the frozen synthetic PESS corpus and the recorded environment only. This report does not establish PostgreSQL runtime behavior, a universal DBMS claim, or a new algorithm.

## Provenance and protocol

- Protocol: `protocol-v1.json`; frozen inputs: `manifest-v1.json` and `SHA256SUMS-inputs`.
- Corpus: 4 small, 8 medium, 4 exploratory large; 16 inputs × 2 methods × 3 endpoint budgets (5/20/60 s) × 3 repetition seeds = 288 independent fresh-process endpoints.
- Baselines: unchanged public `solve_static` and `solve_master_oracle` APIs from ess-advisor SHA `1052ff4a46270c90414d76b32d6f6b37e5908f6a`; Master–Oracle used default options, `certification_tolerance=0.0`, `cut_tolerance=1e-6`, and inner limit `min(5,budget)`.
- Command: `python run_measurements.py --output-dir runs/20261020-issue39-final-v2 --budgets 5,20,60 --repetitions 7101,7102,7103 --tiers small,medium,large --per-instance-cap 65 --hard-total-budget 1800`.
- Environment: Python 3.12.3; NumPy 2.5.4; SciPy 1.18.1; NetworkX 3.7; SciPy-bundled HiGHS; one child process at a time; external memory cap **NOT ENFORCED**; peak RSS is the per-child Linux `ru_maxrss` high-water mark.
- Endpoint runs are endpoint-at-budget observations. They are not reconstructed continuous incumbent traces.

## Integrity and validation

- Raw rows: 288; completed child records: 288; wrapper timeouts/errors/not-run: 0.
- Independent original-PESS verifier: 288/288 selected incumbents passed Fraction feasibility/objective re-evaluation.
- Independent reference cross-check: `reference-crosscheck.json` reports PASS for all four small instances, matching the advisor Fraction exhaustive objective/optimal-set result and every feasible subset's labeled maximal-matching sets.
- Solver-reported objective present and matching independent re-evaluation: 280; unavailable on 8 non-optimal records. A missing solver objective is not treated as a failed independent check.
- Solver status: 267 `optimal`, 21 `not_optimal`.
- Numerical warning rows: 27; HiGHS non-JSON stdout retained on 6 rows.
- Exact tiny reference Gate A is separately recorded in `runs/20261020-issue39-gate-a-v1/`: all 8 small method records agreed with independent exhaustive Fraction optima. The final sweep independently verifies returned incumbents but does not claim exhaustive optimality for medium/large.

## Matched performance summary

| tier | stratum | method | budget s | n | solver optimal | median full s | IQR s | median RSS MB | median scenarios/cuts | median oracle calls |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| large | cycle | master_oracle | 5 | 3 | 0 | 5.066 | 0.006 | 99.3 | 861.0 | 609.0 |
| large | cycle | master_oracle | 20 | 3 | 0 | 20.148 | 0.012 | 117.4 | 1942.0 | 1464.0 |
| large | cycle | master_oracle | 60 | 3 | 0 | 60.219 | 0.045 | 144.3 | 3322.0 | 2639.0 |
| large | cycle | static | 5 | 3 | 3 | 4.199 | 0.094 | 147.4 | 6545.0 | 0.0 |
| large | cycle | static | 20 | 3 | 3 | 4.161 | 0.069 | 147.3 | 6545.0 | 0.0 |
| large | cycle | static | 60 | 3 | 3 | 4.111 | 0.080 | 147.0 | 6545.0 | 0.0 |
| large | mixed_parallel | master_oracle | 5 | 3 | 0 | 5.110 | 0.007 | 99.7 | 852.0 | 532.0 |
| large | mixed_parallel | master_oracle | 20 | 3 | 0 | 20.166 | 0.016 | 108.7 | 2088.0 | 1357.0 |
| large | mixed_parallel | master_oracle | 60 | 3 | 3 | 38.149 | 0.748 | 116.7 | 3055.0 | 2032.0 |
| large | mixed_parallel | static | 5 | 3 | 3 | 0.777 | 0.012 | 140.9 | 13846.0 | 0.0 |
| large | mixed_parallel | static | 20 | 3 | 3 | 0.803 | 0.059 | 140.9 | 13846.0 | 0.0 |
| large | mixed_parallel | static | 60 | 3 | 3 | 0.831 | 0.023 | 140.8 | 13846.0 | 0.0 |
| large | sharing_cycle | master_oracle | 5 | 3 | 3 | 0.262 | 0.004 | 91.9 | 70.0 | 44.0 |
| large | sharing_cycle | master_oracle | 20 | 3 | 3 | 0.269 | 0.023 | 91.9 | 70.0 | 44.0 |
| large | sharing_cycle | master_oracle | 60 | 3 | 3 | 0.271 | 0.005 | 93.0 | 70.0 | 44.0 |
| large | sharing_cycle | static | 5 | 3 | 3 | 0.780 | 0.045 | 157.4 | 18012.0 | 0.0 |
| large | sharing_cycle | static | 20 | 3 | 3 | 0.835 | 0.023 | 157.3 | 18012.0 | 0.0 |
| large | sharing_cycle | static | 60 | 3 | 3 | 0.884 | 0.061 | 157.2 | 18012.0 | 0.0 |
| large | star_forest | master_oracle | 5 | 3 | 3 | 0.064 | 0.002 | 88.4 | 23.0 | 16.0 |
| large | star_forest | master_oracle | 20 | 3 | 3 | 0.078 | 0.013 | 88.4 | 23.0 | 16.0 |
| large | star_forest | master_oracle | 60 | 3 | 3 | 0.062 | 0.003 | 88.4 | 23.0 | 16.0 |
| large | star_forest | static | 5 | 3 | 3 | 0.032 | 0.006 | 91.1 | 676.0 | 0.0 |
| large | star_forest | static | 20 | 3 | 3 | 0.033 | 0.001 | 91.1 | 676.0 | 0.0 |
| large | star_forest | static | 60 | 3 | 3 | 0.035 | 0.002 | 91.1 | 676.0 | 0.0 |
| medium | cycle | master_oracle | 5 | 3 | 0 | 5.028 | 0.001 | 101.4 | 650.0 | 340.0 |
| medium | cycle | master_oracle | 20 | 3 | 3 | 9.736 | 0.705 | 102.5 | 701.0 | 416.0 |
| medium | cycle | master_oracle | 60 | 3 | 3 | 9.689 | 0.231 | 102.4 | 701.0 | 416.0 |
| medium | cycle | static | 5 | 3 | 3 | 0.308 | 0.004 | 99.2 | 979.0 | 0.0 |
| medium | cycle | static | 20 | 3 | 3 | 0.308 | 0.001 | 98.9 | 979.0 | 0.0 |
| medium | cycle | static | 60 | 3 | 3 | 0.297 | 0.005 | 99.2 | 979.0 | 0.0 |
| medium | mixed_general | master_oracle | 5 | 3 | 3 | 0.788 | 0.068 | 92.5 | 268.0 | 139.0 |
| medium | mixed_general | master_oracle | 20 | 3 | 3 | 0.758 | 0.030 | 92.6 | 268.0 | 139.0 |
| medium | mixed_general | master_oracle | 60 | 3 | 3 | 0.817 | 0.036 | 92.7 | 268.0 | 139.0 |
| medium | mixed_general | static | 5 | 3 | 3 | 0.043 | 0.001 | 92.2 | 982.0 | 0.0 |
| medium | mixed_general | static | 20 | 3 | 3 | 0.042 | 0.005 | 92.2 | 982.0 | 0.0 |
| medium | mixed_general | static | 60 | 3 | 3 | 0.040 | 0.001 | 92.2 | 982.0 | 0.0 |
| medium | mixed_parallel | master_oracle | 5 | 3 | 3 | 0.163 | 0.003 | 89.3 | 68.0 | 32.0 |
| medium | mixed_parallel | master_oracle | 20 | 3 | 3 | 0.165 | 0.009 | 90.2 | 68.0 | 32.0 |
| medium | mixed_parallel | master_oracle | 60 | 3 | 3 | 0.164 | 0.002 | 90.2 | 68.0 | 32.0 |
| medium | mixed_parallel | static | 5 | 3 | 3 | 0.048 | 0.008 | 92.4 | 1032.0 | 0.0 |
| medium | mixed_parallel | static | 20 | 3 | 3 | 0.043 | 0.003 | 92.4 | 1032.0 | 0.0 |
| medium | mixed_parallel | static | 60 | 3 | 3 | 0.041 | 0.002 | 92.4 | 1032.0 | 0.0 |
| medium | path | master_oracle | 5 | 3 | 0 | 5.027 | 0.001 | 101.3 | 622.0 | 349.0 |
| medium | path | master_oracle | 20 | 3 | 3 | 8.648 | 0.081 | 101.7 | 671.0 | 414.0 |
| medium | path | master_oracle | 60 | 3 | 3 | 8.568 | 0.035 | 101.9 | 671.0 | 414.0 |
| medium | path | static | 5 | 3 | 3 | 0.269 | 0.018 | 98.7 | 938.0 | 0.0 |
| medium | path | static | 20 | 3 | 3 | 0.261 | 0.016 | 98.8 | 938.0 | 0.0 |
| medium | path | static | 60 | 3 | 3 | 0.259 | 0.006 | 98.7 | 938.0 | 0.0 |
| medium | sharing_cycle | master_oracle | 5 | 3 | 3 | 0.045 | 0.001 | 88.5 | 15.0 | 12.0 |
| medium | sharing_cycle | master_oracle | 20 | 3 | 3 | 0.044 | 0.001 | 88.4 | 15.0 | 12.0 |
| medium | sharing_cycle | master_oracle | 60 | 3 | 3 | 0.044 | 0.001 | 88.4 | 15.0 | 12.0 |
| medium | sharing_cycle | static | 5 | 3 | 3 | 0.024 | 0.001 | 90.6 | 550.0 | 0.0 |
| medium | sharing_cycle | static | 20 | 3 | 3 | 0.024 | 0.001 | 89.4 | 550.0 | 0.0 |
| medium | sharing_cycle | static | 60 | 3 | 3 | 0.023 | 0.001 | 90.5 | 550.0 | 0.0 |
| medium | sharing_low | master_oracle | 5 | 3 | 3 | 0.302 | 0.007 | 92.4 | 83.0 | 67.0 |
| medium | sharing_low | master_oracle | 20 | 3 | 3 | 0.301 | 0.014 | 92.4 | 83.0 | 67.0 |
| medium | sharing_low | master_oracle | 60 | 3 | 3 | 0.307 | 0.003 | 92.5 | 83.0 | 67.0 |
| medium | sharing_low | static | 5 | 3 | 3 | 0.022 | 0.001 | 90.5 | 166.0 | 0.0 |
| medium | sharing_low | static | 20 | 3 | 3 | 0.022 | 0.002 | 90.5 | 166.0 | 0.0 |
| medium | sharing_low | static | 60 | 3 | 3 | 0.022 | 0.001 | 90.6 | 166.0 | 0.0 |
| medium | star_forest | master_oracle | 5 | 3 | 3 | 0.045 | 0.001 | 88.5 | 21.0 | 14.0 |
| medium | star_forest | master_oracle | 20 | 3 | 3 | 0.044 | 0.000 | 88.5 | 21.0 | 14.0 |
| medium | star_forest | master_oracle | 60 | 3 | 3 | 0.045 | 0.001 | 88.4 | 21.0 | 14.0 |
| medium | star_forest | static | 5 | 3 | 3 | 0.010 | 0.001 | 89.4 | 112.0 | 0.0 |
| medium | star_forest | static | 20 | 3 | 3 | 0.010 | 0.001 | 89.2 | 112.0 | 0.0 |
| medium | star_forest | static | 60 | 3 | 3 | 0.010 | 0.000 | 89.5 | 112.0 | 0.0 |
| medium | star_single | master_oracle | 5 | 3 | 3 | 0.047 | 0.001 | 89.5 | 21.0 | 10.0 |
| medium | star_single | master_oracle | 20 | 3 | 3 | 0.046 | 0.002 | 89.6 | 21.0 | 10.0 |
| medium | star_single | master_oracle | 60 | 3 | 3 | 0.051 | 0.003 | 89.4 | 21.0 | 10.0 |
| medium | star_single | static | 5 | 3 | 3 | 0.023 | 0.000 | 89.6 | 624.0 | 0.0 |
| medium | star_single | static | 20 | 3 | 3 | 0.023 | 0.002 | 89.6 | 624.0 | 0.0 |
| medium | star_single | static | 60 | 3 | 3 | 0.024 | 0.002 | 90.8 | 624.0 | 0.0 |
| small | mixed_parallel | master_oracle | 5 | 3 | 3 | 0.031 | 0.001 | 89.3 | 10.0 | 5.0 |
| small | mixed_parallel | master_oracle | 20 | 3 | 3 | 0.030 | 0.002 | 89.4 | 10.0 | 5.0 |
| small | mixed_parallel | master_oracle | 60 | 3 | 3 | 0.031 | 0.001 | 89.2 | 10.0 | 5.0 |
| small | mixed_parallel | static | 5 | 3 | 3 | 0.008 | 0.000 | 89.4 | 52.0 | 0.0 |
| small | mixed_parallel | static | 20 | 3 | 3 | 0.009 | 0.000 | 89.2 | 52.0 | 0.0 |
| small | mixed_parallel | static | 60 | 3 | 3 | 0.009 | 0.000 | 89.3 | 52.0 | 0.0 |
| small | path_cycle | master_oracle | 5 | 3 | 3 | 0.015 | 0.000 | 88.3 | 5.0 | 1.0 |
| small | path_cycle | master_oracle | 20 | 3 | 3 | 0.015 | 0.000 | 88.3 | 5.0 | 1.0 |
| small | path_cycle | master_oracle | 60 | 3 | 3 | 0.015 | 0.000 | 88.3 | 5.0 | 1.0 |
| small | path_cycle | static | 5 | 3 | 3 | 0.008 | 0.000 | 89.5 | 32.0 | 0.0 |
| small | path_cycle | static | 20 | 3 | 3 | 0.008 | 0.000 | 89.4 | 32.0 | 0.0 |
| small | path_cycle | static | 60 | 3 | 3 | 0.008 | 0.000 | 89.4 | 32.0 | 0.0 |
| small | sharing_cycle | master_oracle | 5 | 3 | 3 | 0.035 | 0.005 | 89.8 | 11.0 | 9.0 |
| small | sharing_cycle | master_oracle | 20 | 3 | 3 | 0.033 | 0.000 | 89.9 | 11.0 | 9.0 |
| small | sharing_cycle | master_oracle | 60 | 3 | 3 | 0.035 | 0.001 | 89.5 | 11.0 | 9.0 |
| small | sharing_cycle | static | 5 | 3 | 3 | 0.009 | 0.000 | 89.8 | 32.0 | 0.0 |
| small | sharing_cycle | static | 20 | 3 | 3 | 0.009 | 0.001 | 89.8 | 32.0 | 0.0 |
| small | sharing_cycle | static | 60 | 3 | 3 | 0.009 | 0.000 | 89.9 | 32.0 | 0.0 |
| small | star_single | master_oracle | 5 | 3 | 3 | 0.009 | 0.000 | 88.0 | 3.0 | 1.0 |
| small | star_single | master_oracle | 20 | 3 | 3 | 0.009 | 0.001 | 88.1 | 3.0 | 1.0 |
| small | star_single | master_oracle | 60 | 3 | 3 | 0.010 | 0.000 | 88.0 | 3.0 | 1.0 |
| small | star_single | static | 5 | 3 | 3 | 0.008 | 0.001 | 89.3 | 36.0 | 0.0 |
| small | star_single | static | 20 | 3 | 3 | 0.009 | 0.000 | 89.2 | 36.0 | 0.0 |
| small | star_single | static | 60 | 3 | 3 | 0.008 | 0.000 | 89.3 | 36.0 | 0.0 |

Across 144 matched instance/budget/repetition pairs, Static was faster on 134, Master–Oracle on 10, and ties on 0; median Master/Static full-invocation ratio was 3.712. This is a timing comparison of the returned endpoint invocations, not a quality-normalized dominance claim.
The independent objective delta (Master–Oracle minus Static on the same endpoint) had median 0.000 over 144 matched rows; nonzero deltas reflect endpoint solution quality and/or termination, not a theorem about either method.

## Structural paired diagnosis (H1)

H1 predicted that Static expansion would track task-local graph scenario complexity, while Master–Oracle would expose repeated task evaluations/oracle calls under sharing. The operational Static `scenario_count` is the number of all matchings enumerated by the unchanged implementation; the manifest also records independent maximal-matching counts as a structural signature. Therefore `scenario_count` must not be described as a maximal-matching count.

| pair | variant | method | budget s | mean max-matchings | median full s | median scenarios/cuts | median oracle calls | median task comps | optimal n/3 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| pair-parallel | mixed_general | master_oracle | 20.0 | 151.0 | 0.758 | 268.0 | 139.0 | 295.0 | 3/3 |
| pair-parallel | mixed_general | master_oracle | 5.0 | 151.0 | 0.788 | 268.0 | 139.0 | 295.0 | 3/3 |
| pair-parallel | mixed_general | master_oracle | 60.0 | 151.0 | 0.817 | 268.0 | 139.0 | 295.0 | 3/3 |
| pair-parallel | mixed_general | static | 20.0 | 151.0 | 0.042 | 982.0 | 0.0 | 0.0 | 3/3 |
| pair-parallel | mixed_general | static | 5.0 | 151.0 | 0.043 | 982.0 | 0.0 | 0.0 | 3/3 |
| pair-parallel | mixed_general | static | 60.0 | 151.0 | 0.040 | 982.0 | 0.0 | 0.0 | 3/3 |
| pair-parallel | mixed_parallel | master_oracle | 20.0 | 150.0 | 0.165 | 68.0 | 32.0 | 85.0 | 3/3 |
| pair-parallel | mixed_parallel | master_oracle | 5.0 | 150.0 | 0.163 | 68.0 | 32.0 | 85.0 | 3/3 |
| pair-parallel | mixed_parallel | master_oracle | 60.0 | 150.0 | 0.164 | 68.0 | 32.0 | 85.0 | 3/3 |
| pair-parallel | mixed_parallel | static | 20.0 | 150.0 | 0.043 | 1032.0 | 0.0 | 0.0 | 3/3 |
| pair-parallel | mixed_parallel | static | 5.0 | 150.0 | 0.048 | 1032.0 | 0.0 | 0.0 | 3/3 |
| pair-parallel | mixed_parallel | static | 60.0 | 150.0 | 0.041 | 1032.0 | 0.0 | 0.0 | 3/3 |
| pair-path | cycle | master_oracle | 20.0 | 112.0 | 9.736 | 701.0 | 416.0 | 820.0 | 3/3 |
| pair-path | cycle | master_oracle | 5.0 | 112.0 | 5.028 | 650.0 | 340.0 | 710.0 | 0/3 |
| pair-path | cycle | master_oracle | 60.0 | 112.0 | 9.689 | 701.0 | 416.0 | 820.0 | 3/3 |
| pair-path | cycle | static | 20.0 | 112.0 | 0.308 | 979.0 | 0.0 | 0.0 | 3/3 |
| pair-path | cycle | static | 5.0 | 112.0 | 0.308 | 979.0 | 0.0 | 0.0 | 3/3 |
| pair-path | cycle | static | 60.0 | 112.0 | 0.297 | 979.0 | 0.0 | 0.0 | 3/3 |
| pair-path | path | master_oracle | 20.0 | 114.0 | 8.648 | 671.0 | 414.0 | 785.0 | 3/3 |
| pair-path | path | master_oracle | 5.0 | 114.0 | 5.027 | 622.0 | 349.0 | 695.0 | 0/3 |
| pair-path | path | master_oracle | 60.0 | 114.0 | 8.568 | 671.0 | 414.0 | 785.0 | 3/3 |
| pair-path | path | static | 20.0 | 114.0 | 0.261 | 938.0 | 0.0 | 0.0 | 3/3 |
| pair-path | path | static | 5.0 | 114.0 | 0.269 | 938.0 | 0.0 | 0.0 | 3/3 |
| pair-path | path | static | 60.0 | 114.0 | 0.259 | 938.0 | 0.0 | 0.0 | 3/3 |
| pair-sharing | sharing_cycle | master_oracle | 20.0 | 108.0 | 0.044 | 15.0 | 12.0 | 30.0 | 3/3 |
| pair-sharing | sharing_cycle | master_oracle | 5.0 | 108.0 | 0.045 | 15.0 | 12.0 | 30.0 | 3/3 |
| pair-sharing | sharing_cycle | master_oracle | 60.0 | 108.0 | 0.044 | 15.0 | 12.0 | 30.0 | 3/3 |
| pair-sharing | sharing_cycle | static | 20.0 | 108.0 | 0.024 | 550.0 | 0.0 | 0.0 | 3/3 |
| pair-sharing | sharing_cycle | static | 5.0 | 108.0 | 0.024 | 550.0 | 0.0 | 0.0 | 3/3 |
| pair-sharing | sharing_cycle | static | 60.0 | 108.0 | 0.023 | 550.0 | 0.0 | 0.0 | 3/3 |
| pair-sharing | sharing_low | master_oracle | 20.0 | 33.0 | 0.301 | 83.0 | 67.0 | 156.0 | 3/3 |
| pair-sharing | sharing_low | master_oracle | 5.0 | 33.0 | 0.302 | 83.0 | 67.0 | 156.0 | 3/3 |
| pair-sharing | sharing_low | master_oracle | 60.0 | 33.0 | 0.307 | 83.0 | 67.0 | 156.0 | 3/3 |
| pair-sharing | sharing_low | static | 20.0 | 33.0 | 0.022 | 166.0 | 0.0 | 0.0 | 3/3 |
| pair-sharing | sharing_low | static | 5.0 | 33.0 | 0.022 | 166.0 | 0.0 | 0.0 | 3/3 |
| pair-sharing | sharing_low | static | 60.0 | 33.0 | 0.022 | 166.0 | 0.0 | 0.0 | 3/3 |
| pair-star | star_forest | master_oracle | 20.0 | 16.0 | 0.044 | 21.0 | 14.0 | 28.0 | 3/3 |
| pair-star | star_forest | master_oracle | 5.0 | 16.0 | 0.045 | 21.0 | 14.0 | 28.0 | 3/3 |
| pair-star | star_forest | master_oracle | 60.0 | 16.0 | 0.045 | 21.0 | 14.0 | 28.0 | 3/3 |
| pair-star | star_forest | static | 20.0 | 16.0 | 0.010 | 112.0 | 0.0 | 0.0 | 3/3 |
| pair-star | star_forest | static | 5.0 | 16.0 | 0.010 | 112.0 | 0.0 | 0.0 | 3/3 |
| pair-star | star_forest | static | 60.0 | 16.0 | 0.010 | 112.0 | 0.0 | 0.0 | 3/3 |
| pair-star | star_single | master_oracle | 20.0 | 112.0 | 0.046 | 21.0 | 10.0 | 28.0 | 3/3 |
| pair-star | star_single | master_oracle | 5.0 | 112.0 | 0.047 | 21.0 | 10.0 | 28.0 | 3/3 |
| pair-star | star_single | master_oracle | 60.0 | 112.0 | 0.051 | 21.0 | 10.0 | 28.0 | 3/3 |
| pair-star | star_single | static | 20.0 | 112.0 | 0.023 | 624.0 | 0.0 | 0.0 | 3/3 |
| pair-star | star_single | static | 5.0 | 112.0 | 0.023 | 624.0 | 0.0 | 0.0 | 3/3 |
| pair-star | star_single | static | 60.0 | 112.0 | 0.024 | 624.0 | 0.0 | 0.0 | 3/3 |

Interpretation of H1 is deliberately limited: the paired inputs do expose measurable changes in scenario counts, task-local maximal-matching signatures, and Master–Oracle oracle work. Whether those changes consistently explain wall time must be judged from the table and raw repetitions; no stable causal effect is asserted without a separate controlled statistical model. Any pair/endpoint with a non-optimal Master–Oracle result remains a censored/quality-limited observation for solver superiority.

## Negative results and limitations

- The corpus did not produce wrapper timeouts, but 21 Master–Oracle endpoints were `not_optimal`, including time-limit, global-deadline, and inner-MIP-not-proven termination reasons. They remain in the raw matrix and are not filtered.
- The default Master–Oracle incurred numerical warnings on some medium path/cycle/sharing runs at the configured `1e-6` cut tolerance. These are recorded as solver diagnostics; they do not become exact Fraction certificates.
- Peak RSS was measured but no external memory cap was enforced. Large static runs reached materially higher RSS than the small/medium pilot; this is an observed resource signal, not a controlled memory-failure threshold.
- All independent incumbent checks passed, but a verified feasible objective is not an independently certified global optimum. Solver-reported primal/dual/MIP-gap fields remain floating-point HiGHS assertions.
- The synthetic additive maintenance field is an instance proxy. It does not validate generic nonadditive maintenance cost or physical PostgreSQL ANALYZE behavior.
- No timing row is a PostgreSQL runtime claim, and no claim is made for all PostgreSQL queries, all cardinality estimators, or arbitrary real possible-scheme sets.

## Decision memo

**Provisional category: ACTIONABLE BOTTLENECK, scoped to this synthetic model and pinned advisor implementation.** The final matrix reproduces a structural regime in which Static's all-matching model expansion grows substantially and large Master–Oracle runs accumulate many task/oracle calls and non-optimal endpoints at the predeclared caps. The evidence supports one narrow next hypothesis: reduce or bound repeated task-local oracle work for the incidence-cycle/general-graph regime while preserving independently checked original PESS objectives. This issue does not implement that hypothesis.

This category is conditional on the recorded corpus, solver SHA, and environment. It is not a claim of a PostgreSQL performance improvement or of a generally superior algorithm. The next step requires researcher review of the paired raw rows and an independently designed algorithm issue; do not merge this result as a universal solver conclusion without that review.

## Artifacts

- `manifest-v1.json`, `protocol-v1.json`, `SHA256SUMS-inputs`: frozen input and protocol.
- `protocol-v1-analysis-clarification.md`: post-run clarification separating Static all-matching row counts from maximal-matching graph signatures.
- `independent_reference.py`, `adapter.py`, `graph_metrics.py`, `run_one.py`, `run_gate_a.py`, `run_measurements.py`: independent verifier and read-only runners.
- `runs/20261020-issue39-gate-a-v1/`: exact tiny Gate A and medium pilot.
- `runs/20261020-issue39-final-v1/`: preserved parser-failure prefix; not final evidence.
- `runs/20261020-issue39-final-v2/raw-runs.jsonl`: complete raw endpoint matrix; `SHA256SUMS` verifies raw and summary files.
- `runs/20261020-issue39-final-v2/reference-crosscheck.json`: independent verifier/reference cross-check.
- `summarize_results.py`: deterministic summary/report generator.

