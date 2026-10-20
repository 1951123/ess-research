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

## Executed Issue #53 validation — 2026-10-20

**Experimentally observed engineering evidence.** Worktree:
`/home/wqts/ess-worktrees/ess-research-issue53`, branch
`fix/issue53-archive-first-etl`. The clean implementation revision used for the
final real-data replay was `78f1321cb8454d76e33006c38bbd1ed2183f1b18`.
The subsequent report-only commit does not change executable files.

Environment: Linux `7.0.0-38-generic`, x86_64, glibc 2.39; Worktree `.venv/bin/python`
3.12.3 (GCC 13.3.0); NumPy 2.3.4, pytest 8.4.2, Ruff 0.14.1.
Other installed test dependencies: iniconfig 2.3.1, packaging 26.3, pluggy 1.7.0,
Pygments 2.21.0. No random workload sampling or experiment seed was used.

The initial root inspection observed `/home/wqts/ess-data` did not exist. The
first CLI attempt in the new Worktree failed immediately because that process
had not inherited `ESS_RUNTIME_PARENT`; no acquisition occurred. Passing the
previously verified roots explicitly succeeded with this exact command:

```sh
ESS_DATA_ROOT=/home/wqts/ess-data ESS_RUNTIME_PARENT=/home/wqts/ess-runtime PYTHONPATH=src .venv/bin/python -m ess_research.arecel prepare --issue 53 --dataset census13 --keep-scratch
```

This **actual network zero-start run** downloaded 118,265,504 bytes, passed the
pinned archive hash gate, and produced `train=100000`, `valid=10000`, `test=10000`
at `ess-research/issue53/runs/arecel-h2pb5vsu/derived` under the runtime parent.
That explicitly retained debug run was executed before the implementation commit
and its manifest honestly records the base revision with a dirty Worktree. It is
not presented as a clean-revision download test. Only `arecel-data.tar.gz` was
left in the shared cache; no manual extraction, prior derived input, or backup
was used.

A subsequent four-dataset CLI consumption pass succeeded (logs under
`ess-research/issue53/runs/integration-ohsrs0ty/`). After committing the final
implementation, a separate **clean-revision, offline-guarded API replay** checked
all four datasets. The exact invocation was the following; the paths were
explicitly supplied for this execution, not built-in defaults:

```sh
ESS_DATA_ROOT=/home/wqts/ess-data ESS_RUNTIME_PARENT=/home/wqts/ess-runtime PYTHONPATH=src .venv/bin/python - <<'PY'
import json, os, pathlib, platform, subprocess, sys, tempfile
from ess_research.arecel import prepare
from ess_research.arecel import archive

def offline(*args, **kwargs):
 raise AssertionError('network access on an existing archive cache')
archive.urlopen = offline
suite = pathlib.Path(tempfile.mkdtemp(prefix='verified-integration-', dir=pathlib.Path(os.environ['ESS_RUNTIME_PARENT'])/'ess-research/issue53/runs'))
print('suite:', suite, flush=True)
results=[]
for dataset in archive.DATASETS:
 with prepare(issue=53, dataset=dataset) as data:
  assert data.manifest['etl'] == {'git_commit': '78f1321cb8454d76e33006c38bbd1ed2183f1b18', 'worktree_dirty': False}
  env=dict(os.environ, ESS_ISSUE_ROOT=str(data.run_root), ESS_ARECEL_DATASET_ROOT=str(data.dataset_root))
  command=[sys.executable,'tests/arecel_consumer.py']
  result=subprocess.run(command,env=env,text=True,capture_output=True)
  (suite/f'{dataset}.log').write_text(result.stdout+result.stderr)
  result.check_returncode()
 assert not data.dataset_root.exists()
 status=json.loads((data.run_root/'logs/status.json').read_text())
 assert status['status']=='success' and status['derived_removed']
 record={'run_root':str(data.run_root),'consumer':json.loads(result.stdout),'lifecycle':status,'etl':data.manifest['etl']}
 results.append(record)
 print(json.dumps(record),flush=True)
cache=pathlib.Path(os.environ['ESS_DATA_ROOT'])
assert sorted(p.name for p in cache.iterdir()) == ['arecel-data.tar.gz']
report={'environment':{'python':sys.version,'platform':platform.platform(),'executable':sys.executable},'archive_bytes':(cache/'arecel-data.tar.gz').stat().st_size,'offline_guard':True,'results':results}
(suite/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS',suite/'report.json',flush=True)
PY
```

Observed output summary (each consumer `PASS`, each context `success`,
`derived_removed=true`, and `keep_scratch=false`):

| Dataset | CSV rows checked | Columns | Train / valid / test | Run ID |
|---|---:|---:|---|---|
| Forest10 | 581,012 | 10 | 100,000 / 10,000 / 10,000 | `arecel-lzrvjvro` |
| Census13 | 48,842 | 13 | 100,000 / 10,000 / 10,000 | `arecel-ep7mmt4c` |
| DMV11 | 11,591,877 | 11 | 100,000 / 10,000 / 10,000 | `arecel-g99609ep` |
| Power7 | 2,075,259 | 7 | 100,000 / 10,000 / 10,000 | `arecel-8vlreao3` |

In particular, Forest10's source also contains train records; the new API
preserves these instead of limiting output to the historical valid/test view.
The four clean-run manifests recorded the stated commit with
`worktree_dirty=false`. The local external log bundle is
`$ESS_RUNTIME_PARENT/ess-research/issue53/runs/verified-integration-dx0t9fc9/`
(`report.json` and four consumer stdout logs). These are local execution records,
not assumed to exist on another machine; the command above reproduces the checks.

The final affected CI selection was also executed locally:

```sh
.venv/bin/python -m pytest -q ci/test_check_evidence.py ci/test_theory_star_reductions.py experiments/pg-maintenance/test_analyze_benchmark.py experiments/pg-maintenance/fixed-target-cpu/test_fixed_target_cpu.py experiments/pg-tracing/test_analyze_mcv_numeric_followup.py experiments/theory/test_degree_two_oracle.py tests
.venv/bin/python ci/check_evidence.py
.venv/bin/ruff check src/ess_research/task_paths.py src/ess_research/arecel/archive.py src/ess_research/arecel/__main__.py src/ess_research/arecel/__init__.py tests/test_arecel_prepare.py tests/arecel_consumer.py
.venv/bin/ruff format --check src/ess_research/task_paths.py src/ess_research/arecel/archive.py src/ess_research/arecel/__main__.py src/ess_research/arecel/__init__.py tests/test_arecel_prepare.py tests/arecel_consumer.py
git diff --check
```

Results: **108 passed** (8.62 s); evidence checker **16 manifests / 186 committed
files verified**; Ruff **all checks passed**, **6 files already formatted**;
whitespace check passed. The focused `tests/` selection separately reported
**77 passed**, including 36 new archive/root/lifecycle cases. These are measured
local results; remote CI has its own status.

**Limitations / next validation:** No PG server, COPY, ANALYZE, planner trace,
query accuracy, maintenance cost, or Stage 2B outcome was measured. CSV validation
checks shape/count and workload/truth alignment, not recomputed database truth.
Offline fixtures exercise failure/race paths; no actual interrupted 118 MB network
transfer was forced. The first download was a working-tree test; the final clean
replay was a cache hit. Source/whole-archive authenticity relies on the pinned hash
and the issue's explicit pickle trust assumption. The next integration belongs to
Issue #48: consume this API while retaining every science-side PG gate. Existing
Stage 0/1/2 scripts, reports and frozen outcomes, `docs/STATUS.md`,
`docs/DECISIONS.md`, and `paper/main.tex` were not modified.
