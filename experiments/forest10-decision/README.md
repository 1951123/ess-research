# Issue #23 Forest10 decision comparison

This directory contains the bounded, independently checkable fallback for
Issue #23.  It is a model-level exact experiment, not a PostgreSQL result.

The repository's explicit Forest10 data root was not present in the execution
environment.  The committed ETL and acquisition records therefore could not
provide real query IDs, truth cardinalities, selected MCV contents, or
PostgreSQL-calibrated coefficients.  The instance below is intentionally
labelled `forest10-schema-shaped-model-v1`: it uses the ten-column Forest10
schema identity and a precommitted set of six two-column candidate shapes, but
its task IDs, coefficients, weights, and maintenance costs are controlled
rational inputs.  They must not be described as measurements from Forest10 or
PostgreSQL.

The runner is standard-library-only and uses exact `Fraction` arithmetic.  For
each budget it enumerates every feasible subset for each of three objectives:

* PESS: sum of task-wise maxima over all admissible maximal matchings;
* Nominal: loss under the precommitted lexicographic candidate order;
* Joint-Robust: maximum total loss over every permutation of the full
  candidate universe, with one shared permutation restricted for every task.

Empty is fixed as a reference.  Ties are retained and the lexicographically
smallest selected set is reported.  The raw compressed JSONL keeps every
common-order observation for the four reported choices and is losslessly
checked by the tests.

Run from the repository root:

```text
python3 experiments/forest10-decision/run_experiment.py
python3 -m pytest -q experiments/forest10-decision/test_forest10_decision.py
```

The canonical summary, raw observations, instance, and report are deterministic
and checked by SHA-256.  Execution metadata and elapsed time are kept in the
separate `results/execution.json` artifact.  No `ess-advisor` or
`ess-postgresql` source is modified by this experiment.  The additive resource
cost is an explicit experimental proxy; it is not generic maintenance cost or
physical `ANALYZE` time.
