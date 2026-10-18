# Model-level decision value experiment

This directory contains the self-contained Issue #14 experiment. It uses the
pairwise labeled-edge maximal-matching instantiation with exact `Fraction`
inputs and an additive maintenance proxy. It does not use PostgreSQL, real
data, `EXPLAIN`, or physical maintenance measurements.

The runner compares four decisions on the same candidate universe, task set,
weights, corrections, budgets, and external policy evaluations:

* `pessimistic`: exact exhaustive minimization of
  `F_Gamma(M) = sum_i w_i max_{P in Gamma_i^MM(M)} L_i(P)`;
* `nominal`: exact minimization of the prespecified sorted-ID order;
* `greedy_nominal`: deterministic positive nominal marginal-benefit-per-cost
  selection, with nonpositive gains rejected;
* `empty`: the empty resource set.

For every fixture and budget, all permutations of the global candidate order
are evaluated. These are shared orders: the same order is restricted to each
task, rather than choosing an independent order per task. The raw JSON keeps
the per-order observations for every method, plus the independently solved
per-order optimum used for scenario regret.

Run from the repository root:

```text
python3 experiments/decision-value/run_experiment.py
python3 -m pytest -q experiments/decision-value/test_decision_value.py
```

The experiment is deliberately standard-library-only so the research
repository's offline CI can execute its tests without installing the separate
`ess-advisor` package. The instance JSON schema follows the existing
`ess-advisor` synthetic model: candidate endpoints are labeled edges,
`alpha` and `corrections` are exact log-space model inputs, and costs are an
additive proxy only.

The results are model-internal and experimentally observed for this executed
matrix. They do not establish PostgreSQL behavior, real-policy coverage,
physical cost additivity, or query-latency benefit.
