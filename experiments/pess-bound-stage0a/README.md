# Stage 0A: witness-completion bound pilot

This directory is a standalone, stdlib-first reference and diagnostic suite
for Issue #30. The exact reference in `reference.py` is definition-driven and
does not import candidate-bound code. `bounds.py` implements the A/B/C
comparators separately. The runner writes frozen instances, raw node
observations, exact counterexample records, a report, environment metadata,
and SHA-256 checksums under `runs/`.

The committed `pilot-manifest.json` fixes the corpus strata, seeds, branch
state cap, arithmetic, and wall-time cap before comparison results are run.
The pilot uses only tiny synthetic instances; it does not require PostgreSQL,
`ess-advisor`, a solver, or real dataset roots.

Run the unit tests:

```sh
python3 -m unittest discover -s experiments/pess-bound-stage0a -p 'test_*.py' -v
```

Re-run the frozen pilot:

```sh
python3 experiments/pess-bound-stage0a/run_stage0a.py
sha256sum -c experiments/pess-bound-stage0a/runs/20261019-issue30-v1/SHA256SUMS
```

The restricted-master comparator D is intentionally recorded as not executed:
the issue forbids modifying `ess-advisor` or building a new solver for this
bounded child task.

The exact assumptions and proof of the tested completion lemma are recorded in
`lemma.md`.
