# Forest10 ETL boundary v1

Issue #15 adds a small, dependency-free Forest10 vertical slice. It is a
benchmark-input boundary, not an optimizer, PostgreSQL integration, or
cardinality-estimation result.

## Explicit input contract

Every command requires `--data-root`. There is no environment-variable or
absolute-path default. Under the supplied root the validator expects:

```text
<root>/arecel/incoming/arecel-data.tar.gz
<root>/arecel/audit-v1/audit.json
<root>/arecel/audit-v1/forest10.canonical.jsonl.gz
<root>/arecel/raw/data/forest10/original.csv
<root>/arecel/raw/data/forest10/workload/base.pkl
<root>/arecel/raw/data/forest10/workload/base-original-label.pkl
```

The audit metadata must pin the AreCEL commit, archive URL and SHA256,
Forest10 CSV row count/hash, schema-contract ID, and canonical workload/hash
values. The archive is inspected without extraction: unsafe member paths and
missing required members are rejected. The CSV is checked for exact header
order, row width, parseable finite double values or empty NULL fields, row
count, and SHA256.

The two pickle files are treated as opaque bytes. The module hashes them but
never imports or deserializes them. The accepted workload input is the
independently produced, hash-checked canonical JSONL.gz artifact.

## Output contract

`build` produces three deterministic JSON artifacts in a new, non-overwritten
output directory:

- `workload.json` (`cardinality-workload-v1`) contains stable task IDs,
  source IDs, source SQL, adapted estimator SQL, source-query hashes, split,
  source order, and weights. It contains no truth cardinality.
- `truth.json` (`cardinality-truth-v1`) contains the exact nonnegative integer
  cardinality, the original COUNT SQL, source-label provenance, and the same
  source/task identities.
- `manifest.json` (`arecel-forest10-etl-manifest-v1`) binds the schema/CSV
  identity, source and producer hashes, transformation version, split and
  output hashes.

The source truth SQL and the adapted planner-estimation SQL are intentionally
distinct. Adaptation is restricted to `COUNT(*)` → `SELECT *`, the audited
`forest10_original` → `public.forest10` relation, and quoted source-column
identifiers → lowercase catalog identifiers. Literals, predicate values,
operators, and predicate order are not rewritten. Unsupported relations or
quoted identifiers fail closed.

The generated artifacts preserve source order and use IDs of the form
`arecel_forest10_<split>_<index>`. The general AreCEL workload is not silently
declared eligible for the pairwise maximal-matching study; later analysis must
apply its own structural query-scope validator.

## Commands

From the repository root:

```sh
PYTHONPATH=src .venv/bin/python -m ess_research.arecel.forest10 inspect \
  --data-root /absolute/path/to/explicit/arecel-root

PYTHONPATH=src .venv/bin/python -m ess_research.arecel.forest10 build \
  --data-root /absolute/path/to/explicit/arecel-root \
  --output-dir /absolute/path/to/ignored/etl-output/forest10-test-v1 \
  --split test
```

`inspect` returns exit status 2 with `BLOCKED_MISSING_INPUT` when the declared
root is incomplete. `build` refuses to overwrite an existing output directory.
There is no download command in this PR: acquisition must be a separately
authorized, pinned, hash-checked and license-reviewed action.
