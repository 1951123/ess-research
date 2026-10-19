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

The original v1 run is preserved. Because its first GitHub API publication
used a large-file transport that changed the raw blob, the corrective PR
commit restores the exact local bytes and records that reconciliation in the
v1 report. The predeclared `pilot-manifest-v2.json` adds a balanced follow-up
sample across resource-status, assigned-depth, and forced-selected strata;
v2 does not replace v1.

Run the unit tests:

```sh
python3 -m unittest discover -s experiments/pess-bound-stage0a -p 'test_*.py' -v
```

Re-run the frozen pilot:

```sh
python3 experiments/pess-bound-stage0a/run_stage0a.py
(cd experiments/pess-bound-stage0a/runs/20261019-issue30-v1 && sha256sum -c SHA256SUMS)
python3 experiments/pess-bound-stage0a/run_stage0a.py \
  --manifest experiments/pess-bound-stage0a/pilot-manifest-v2.json \
  --run-dir experiments/pess-bound-stage0a/runs/20261019-issue30-v2
(cd experiments/pess-bound-stage0a/runs/20261019-issue30-v2 && sha256sum -c SHA256SUMS)
```

The restricted-master comparator D is intentionally recorded as not executed:
the issue forbids modifying `ess-advisor` or building a new solver for this
bounded child task.

The exact assumptions and proof of the tested completion lemma are recorded in
`lemma.md`.
