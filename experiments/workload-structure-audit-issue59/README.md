# Issue #59 workload structure audit

This is a read-only, outcome-free structural characterization of the native
AreCEL workload streams for Forest10, Census13, DMV11, and Power7. It does not
amend Stage 2B protocol-v4 and does not make PostgreSQL runtime, MCV payload,
PESS, or Nominal claims.

The first commit freezes [`protocol-v1.json`](protocol-v1.json). The
deterministic analyzer consumes only the archive-first API's workload/schema/
table artifacts and never opens `truth.json`:

```sh
source /home/wqts/.bashrc
PYTHONPATH=src .venv/bin/python \
  experiments/workload-structure-audit-issue59/audit_structure.py \
  --output-root experiments/workload-structure-audit-issue59/runs/<new-version>
```

An optional `--stage2b-v4-root` adds a clearly labelled read-only summary of
already observed Forest10/Census13 PR #58 validation ledgers. DMV11 and Power7
physical payload/trace status remains `NOT MEASURED`.

`runs/20261020-v4/` is the authoritative clean-worktree evidence. v1 is
invalidated by an aggregate reporting bug, v2 is the corrected-count replay,
and v3 is preserved but superseded because it lacked percentage fields.
Each retained run has an exclusive-create `SHA256SUMS` manifest; raw data and
large runtime artifacts remain outside Git. A subsequent replay after the
provenance-check implementation must use a new versioned run directory; it
must verify the archive/upstream/dataset/split/query identities and the
measured source CSV SHA-256 and row count before writing per-dataset success.

Fingerprint fields are explicitly named: `canonical_predicate` follows the
frozen ordered `(column, operator, literal value)` definition,
`source_sql_text` hashes stripped `source_sql` text, and `template` removes
literal values. Historical v1--v4 output is immutable.
