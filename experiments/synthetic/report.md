# First synthetic PESS-ESS study

This report is generated from suite-results.json; unresolved solver statuses are not interpreted as optimal results.

- Python: 3.12.3 (main, Aug 31 2026, 10:18:26) [GCC 13.3.0]
- Platform: Linux-7.0.0-38-generic-x86_64-with-glibc2.39
- Library versions: {'numpy': '2.5.4', 'scipy': '1.18.1', 'networkx': '3.7'}
- Solver backend: SciPy optimize.milp with HiGHS
- Master/inner limits: 10 s / 5 s
- Installation: python3 -m venv .venv; pip install -r requirements.txt; pip install -e /home/wqts/projects/ess-advisor

## Results

| Instance | Candidates | Tasks | Solver | Status | Objective | Runtime (s) | LB | UB | Scenarios/cuts | Inner calls | Early exits |
|---|---:|---:|---|---|---:|---:|---:|---:|---:|---:|---:|
| tiny_mixed | 5 | 3 | exhaustive_reference | optimal | 19/2 | 0.0000 | 9.5 | 9.5 | None | 0 | 0 |
| tiny_mixed | 5 | 3 | static_full_conditional | optimal | 19/2 | 0.0067 | 9.5 | 9.5 | 13 | 0 | 0 |
| tiny_mixed | 5 | 3 | master_oracle | optimal | 19/2 | 0.0199 | 9.5 | 9.5 | 8 | 10 | 10 |
| small_shared | 7 | 4 | exhaustive_reference | optimal | 37/2 | 0.0000 | 18.5 | 18.5 | None | 0 | 0 |
| small_shared | 7 | 4 | static_full_conditional | optimal | 37/2 | 0.0055 | 18.5 | 18.5 | 26 | 0 | 0 |
| small_shared | 7 | 4 | master_oracle | optimal | 37/2 | 0.0458 | 18.499999000000003 | 18.5 | 17 | 12 | 30 |
| parallel_zero_cost | 8 | 4 | exhaustive_reference | optimal | 21/2 | 0.0000 | 10.5 | 10.5 | None | 0 | 0 |
| parallel_zero_cost | 8 | 4 | static_full_conditional | optimal | 21/2 | 0.0108 | 10.5 | 10.5 | 37 | 0 | 0 |
| parallel_zero_cost | 8 | 4 | master_oracle | optimal | 21/2 | 0.0795 | 10.499999 | 10.5 | 24 | 36 | 18 |
| positive_sign | 8 | 4 | exhaustive_reference | optimal | 12 | 0.0000 | 12.0 | 12.0 | None | 0 | 0 |
| positive_sign | 8 | 4 | static_full_conditional | optimal | 12 | 0.0048 | 12.0 | 12.0 | 55 | 0 | 0 |
| positive_sign | 8 | 4 | master_oracle | optimal | 12 | 0.0013 | 12.0 | 12.0 | 0 | 0 | 4 |
| medium_dense | 12 | 6 | static_full_conditional | optimal | 25 | 0.0546 | 24.999999 | 25.0 | 120 | 0 | 0 |
| medium_dense | 12 | 6 | master_oracle | optimal | 25 | 0.7096 | 25.0 | 25.0 | 96 | 186 | 57 |

## Exhaustive agreement

- tiny_mixed: reference objective 19/2; static and Master--Oracle exact agreement: True.
- small_shared: reference objective 37/2; static and Master--Oracle exact agreement: True.
- parallel_zero_cost: reference objective 21/2; static and Master--Oracle exact agreement: True.
- positive_sign: reference objective 12; static and Master--Oracle exact agreement: True.
- medium_dense: no exhaustive reference; solver objectives are reported only with their MIP statuses.

## Interpretation

For exhaustive instances, the test suite compares both MIP-based outer methods against an independent Fraction-based reference. Static formulation scenario counts measure the complete matching index, while Master–Oracle cut counts measure only generated conditional scenarios. A non-optimal status, if present, is an unresolved computational result rather than evidence of an algorithmic failure.

These are synthetic measurements only. They do not establish PostgreSQL behavior, algorithmic superiority, or asymptotic performance guarantees.
