# Stage 0B: certified approximate task-wise PESS pilot

This directory implements Issue #33 in a new, stdlib-first scope. It preserves
the original task-wise PESS objective, labeled parallel edges, independent
task-wise adversaries, maximal (not maximum-cardinality) matchings, and the
additive maintenance proxy. It does not modify `ess-advisor`,
`ess-postgresql`, PostgreSQL state, historical Stage 0A evidence, or
`paper/main.tex`.

The protocol was frozen before comparisons in `pilot-manifest-v1.json`; the
first commit on the Issue branch is the protocol commit. Frozen inputs are in
`instances/`. `reference.py` is definition-driven and Fraction-only. The
rounded solver is separate: tiny cases use exhaustive rounded search only as a
certificate proof-of-concept, while stress cases use a deterministic bounded
greedy search. A heuristic result is never called globally optimal.

Run the unit and exhaustive checks:

```sh
python3 -m unittest discover -s experiments/pess-certified-approx-stage0b -p 'test_*.py' -v
```

Run the pilot into a new directory (the runner refuses to overwrite one):

```sh
scratch_dir="$(mktemp -d /tmp/ess-stage0b.XXXXXX)"
python3 experiments/pess-certified-approx-stage0b/run_pilot.py --run-dir "$scratch_dir"
(cd "$scratch_dir" && sha256sum -c SHA256SUMS)
```

The committed evidence run is created only after the protocol and code are
committed. Verify committed evidence before rerunning; use a new scratch
directory and never overwrite a preserved run.

Reference B is explicitly **NOT EXECUTED** because no unchanged reproducible
solver adapter can be added within this Issue without touching `ess-advisor` or
adding production code. Therefore the scoped outcome is expected to be
**INCONCLUSIVE** even when all tiny certificates pass: this pilot cannot claim
an equal-clock same-objective computational benefit.

See `proof.md` for the uniform perturbation and LB/UB transfer argument and
`counterexamples.json` for preserved failures of tempting incorrect variants.
