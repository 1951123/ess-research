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

Verify the committed evidence before re-executing either pilot:

```sh
(cd experiments/pess-bound-stage0a/runs/20261019-issue30-v1 && sha256sum -c SHA256SUMS)
(cd experiments/pess-bound-stage0a/runs/20261019-issue30-v2 && sha256sum -c SHA256SUMS)
```

Re-run into new scratch directories; never pass either committed historical
directory as `--run-dir`:

```sh
scratch_v1="$(mktemp -d /tmp/ess-stage0a-v1.XXXXXX)"
python3 experiments/pess-bound-stage0a/run_stage0a.py \
  --run-dir "$scratch_v1"
(cd "$scratch_v1" && sha256sum -c SHA256SUMS)

scratch_v2="$(mktemp -d /tmp/ess-stage0a-v2.XXXXXX)"
python3 experiments/pess-bound-stage0a/run_stage0a.py \
  --manifest experiments/pess-bound-stage0a/pilot-manifest-v2.json \
  --run-dir "$scratch_v2"
(cd "$scratch_v2" && sha256sum -c SHA256SUMS)
```

The runner refuses the preserved v1/v2 directories. Across environments,
the exact observations, objectives, and failure counts should agree, while
wall-clock timings and raw-output bytes/hashes may differ; keep any new
scratch output separately instead of replacing the committed evidence.

The restricted-master comparator D is intentionally recorded as not executed:
the issue forbids modifying `ess-advisor` or building a new solver for this
bounded child task.

The exact assumptions and proof of the tested completion lemma are recorded in
`lemma.md`.
