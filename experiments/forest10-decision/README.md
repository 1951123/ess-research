# Issue #23 Forest10 decision comparison

This directory contains the bounded, independently checkable synthetic pilot
and the Issue #23 real-stage protocol. The synthetic instance remains a model
smoke test; the real-stage evidence is summarized in
[real-stage-report.md](real-stage-report.md) and keeps data acquisition,
PostgreSQL measurements, and exact model optimization separate.

The real Forest10 stage is gated by an explicit caller-provided data root; no
machine-specific path is inferred or probed. The committed ETL and acquisition
records therefore could not provide real query IDs, truth cardinalities,
selected MCV contents, or PostgreSQL-calibrated coefficients in this pilot. The
instance below is intentionally
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

An independent reference checker (`verify_reference.py`) recomputes all 12
PESS/Nominal/Joint-Robust objective certificates, optimal-set tie lists, and
selected-set evaluation values without importing the runner. This is an
independent optimality cross-check, not a claim that the synthetic parameters
are PostgreSQL measurements.

Run from the repository root:

```text
python3 experiments/forest10-decision/run_experiment.py
python3 -m pytest -q experiments/forest10-decision/test_forest10_decision.py
python3 experiments/forest10-decision/verify_reference.py \
  --instance experiments/forest10-decision/instance.json \
  --summary experiments/forest10-decision/results/forest10-decision-summary.json
```

The runner accepts `--instance PATH` for a separately generated model input and
`--data-root /ABSOLUTE/ROOT`; `--data-root` takes precedence over
`ESS_DATA_ROOT`. The exact real-stage inputs, hashes, and commands are in
[real-stage-report.md](real-stage-report.md) and
[real-stage-handoff.md](real-stage-handoff.md). The real runner reuses the
same exact optimizer and independent reference checker; it does not reimplement
the algorithm.

The frozen synthetic instance has no positive task-wise PESS-versus-shared-order
gap and no PESS-versus-Joint-Robust decision difference. This is a neutral
instance-level result, not evidence that per-task conservatism is free in
general.

The canonical summary, raw observations, instance, and report are deterministic
and checked by SHA-256.  Execution metadata and elapsed time are kept in the
separate `results/execution.json` artifact.  No `ess-advisor` or
`ess-postgresql` source is modified by this experiment.  The additive resource
cost is an explicit experimental proxy; it is not generic maintenance cost or
physical `ANALYZE` time.
