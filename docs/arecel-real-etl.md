# Archive-first AreCEL preparation

Issue #53 provides one entrypoint for `forest10`, `census13`, `dmv11`, and
`power7`. The shared input is only a network-origin raw archive. All derived
data is disposable and belongs to the invoking Issue/run. This is engineering
infrastructure, not PostgreSQL calibration or a Stage 2B result.

## Explicit configuration

Configure exactly three stable global roots yourself, for example in `~/.bashrc`:

```sh
# Illustrative values, not defaults. Choose your own directories.
export ESS_DATA_ROOT="$HOME/ess-data"
export ESS_WORKTREE_PARENT="$HOME/ess-worktrees"
export ESS_RUNTIME_PARENT="$HOME/ess-runtime"
```

The ETL checks only `ESS_DATA_ROOT` and `ESS_RUNTIME_PARENT`. Worktree path
resolution checks only `ESS_WORKTREE_PARENT`. Imports and offline tests require
none of these variables. Unset, empty, relative, non-directory, or overlapping
ETL roots fail before acquisition. Valid nonexistent roots are created by the
owning workflow. There is no `--data-root` override, search of old roots, or
automatic shell-profile edit. `ESS_ISSUE_ROOT` is an optional **process-local**
value resolved for a consuming run, never a fourth global setting.

Install into this Worktree's own virtual environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-arecel.txt
```

## One CLI or context-managed API

From the repository root, an explicit retained preparation is:

```sh
PYTHONPATH=src .venv/bin/python -m ess_research.arecel prepare \
  --issue 48 --dataset census13 --keep-scratch
```

The JSON stdout identifies the unique run and dataset paths. This debug option
retains only this invocation's outputs; it does not establish a shared derived
cache. For normal execution, supply the consuming command after `--`:

```sh
PYTHONPATH=src .venv/bin/python -m ess_research.arecel prepare \
  --issue 53 --dataset census13 -- .venv/bin/python tests/arecel_consumer.py
```

The consumer receives `ESS_ISSUE_ROOT` (the unique run directory) and
`ESS_ARECEL_DATASET_ROOT` (its `derived/` directory) in its process environment.
The ETL waits for it to finish and removes its own derived directory by default.
A nonzero consumer exit fails the command and leaves an error diagnostic. Without
a consumer, `--keep-scratch` is required, so successful preparation does not
silently return paths that have already been removed.

The equivalent Python API is:

```python
from ess_research.arecel import prepare

with prepare(issue=48, dataset="census13") as data:
    table_csv = data.csv
    workload = data.dataset_root / "valid" / "workload.json"
    truth = data.dataset_root / "valid" / "truth.json"
    # Import/measure while inside this block, using the caller's owned PG cluster.
    # Save the caller's scientific evidence outside data.dataset_root.
```

No PostgreSQL cluster is created or removed by this API. The caller owns its
cluster lifecycle, scientific protocol, cohort freeze, and evidence retention.

## Files and semantics

```text
$ESS_DATA_ROOT/
  arecel-data.tar.gz                         # only persistent shared data
$ESS_RUNTIME_PARENT/ess-research/issue48/runs/arecel-<unique-id>/
  derived/
    table.csv                               # original source CSV, including header
    schema.sql                              # catalog names/types in CSV column order
    manifest.json
    valid/{workload,truth}.json
    test/{workload,truth}.json
    train/{workload,truth}.json              # when present in the source
  results/manifest.json                     # small preparation provenance
  logs/status.json                          # success/failure, cleanup outcome
  logs/error.json                           # concise diagnostic on failure
```

The source schemas derive from the previously audited pinned AreCEL adapters:

| Dataset | PostgreSQL relation | Source rows | Columns |
|---|---|---:|---|
| Forest10 | `public.forest10` | 581,012 | 10 double precision |
| Census13 | `public.census13` | 48,842 | 5 double precision, 8 varchar(64) |
| DMV11 | `public.dmv11` | 11,591,877 | 1 double precision, 10 varchar(64) |
| Power7 | `public.power7` | 2,075,259 | 7 double precision |

`schema.sql` creates an empty table; import `table.csv` with PostgreSQL CSV HEADER
handling and the listed column order. The ETL copies CSV bytes directly and checks
the header; the standalone integration consumer additionally checks every row's
width and the source row count. This issue does not claim actual PG import tests.

Each workload file has `format`, `dataset`, `split`, and `queries`. Each query
contains a stable `query_id` (`arecel:<dataset>:<split>:<six-digit-source-index>`),
`source_index`, adapted `sql` (`SELECT *`), reconstructed `source_sql`
(`SELECT COUNT(*)`), ordered source `predicates`, and unit `weight`. Predicate
operators, inclusive `between` bounds, and string values are preserved; catalog
identifiers fold to the audited lowercase names. Apostrophes and backslashes are
escaped. Pickles contain structured Query objects, not original SQL text;
`source_sql` is a reconstruction, not preserved historical SQL bytes.

Truth is separate: its `queries` contain the same IDs/indices,
`true_cardinality` (nonnegative source integer) and `source_selectivity`.
No truth fields appear in workload records. All available train/valid/test splits
are prepared without resampling, reordering, or fitting. The downstream experiment
must enforce split isolation; preparing files does not authorize test-label use.

The small manifest records the whole-archive hash and source commit, dataset,
split counts, Issue/run identity, ETL Git revision and dirty flag, Python version,
and deterministic unit-weight/no-seed configuration. Derived files have no
historical hash acceptance requirement. Save scientific evidence to the owning
experiment's `results/` or versioned evidence location before leaving the context.

## Archive trust, concurrency, and cleanup

The producer is [AreCELearnedYet](https://github.com/sfu-db/AreCELearnedYet) at
`aa52da7768023270bad884232972e0b77ec6534a`; the original source URL is
`https://www.dropbox.com/s/5bmvc1si5hysapf/data.tar.gz?dl=0` (download uses `dl=1`).
The expected whole-archive SHA-256 is:

```text
5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79
```

A cache hit is verified and works without network access. A cache miss downloads
a temporary sibling, checks this hash, then publishes atomically with a hard link
that cannot replace another worker's file. A race winner is verified before reuse.
A wrong existing cache fails explicitly and is preserved. Failed downloads never
become the public cache file; handled failures remove the owned temporary file.
An uncatchable process termination may leave an unaccepted `.part` file; no later
run treats it as valid or automatically deletes it. The cache filesystem must
support atomic hard links within a directory.

**Only the exact whole-archive-pinned bytes are trusted.** The ETL deserializes
the desired dataset's pickles directly, supplying minimal upstream Query/Label
class adapters and NumPy scalar support. There is no manual converter or separate
sandbox step, nor a per-member/pickle/canonical authenticity chain. This explicit
trust tradeoff is not a claim that arbitrary pickle files are safe. Test fixtures
replace the digest only inside tests, before any deserialization; the public CLI
has no archive URL/hash override.

The tar stream is scanned internally; only the selected CSV and pickle members
are opened. Other datasets are not materialized or required. No archive paths are
extracted onto the filesystem. Duplicate/missing selected members and malformed
computed records fail clearly. The cache never receives CSV, pickle, canonical,
audit, workload, truth, manifests, logs, or PG files.

Successful and failed contexts remove only their newly created `derived/` tree
unless `keep_scratch=True`. Logs and the small manifest survive. An ownership
check avoids removing a replaced directory. Unrelated directories, external
symlink targets, `results/`, and separately owned PGDATA are not removed. A killed
process may leave its run for explicit human inspection; there is no sweeper.

## Transition and downstream boundary

The new entrypoint never reads historical `arecel/raw/data/`, `audit-v1/`,
canonical JSONL, or old ETL output directories. There is no migration or output
compatibility promise. Existing research reports, frozen scripts, and old ETL
modules used by those scripts are retained as historical reproducibility code;
they are not adapters used by this pipeline. New consumers must use this API.
The researcher backup, prior Issue trees, and previous Worktrees remain untouched.

Issue #48 must separately replace its materialized-path Gate A adapter with a
call to this API. Its PG source/binary, cluster, sample, trace, cohort-freeze,
no-test-leakage and held-out measurement gates remain required. In particular,
its `NOT_IMPLEMENTED_BLOCKED` PG-runtime validator does **not** become PASS here.

## Reproduction checks

```sh
.venv/bin/python -m pip install 'pytest==8.4.2' 'ruff==0.14.1'
.venv/bin/python -m pytest -q tests
.venv/bin/ruff check src/ess_research/task_paths.py \
  src/ess_research/arecel/archive.py src/ess_research/arecel/__main__.py \
  src/ess_research/arecel/__init__.py tests/test_arecel_prepare.py tests/arecel_consumer.py
```

Offline tests use a local HTTP server and a hash-pinned fixture containing only
the requested dataset. They cover zero-start acquisition, all four schemas/splits,
offline cache hits, wrong hashes, partial/failed/interrupted downloads, parallel
first downloads, missing roots, isolation, consumer failures and cleanup.
The real-archive consumer command above checks full CSV shape/count and every
workload/truth ID without depending on the ETL implementation. Repeat it with each
of the four dataset names. See the execution record below for what was actually run.
