# Issue #17 Forest10 acquisition, controlled conversion, and ETL validation

**Status: VERIFIED DERIVED CANONICAL ETL; historical canonical bytes were not available.**

This report records the original fail-closed blocker and the subsequent
researcher-authorized one-time conversion of the two exact pinned pickle
files. Raw files, pickles, the derived canonical file, and ETL output remain
outside Git in an experiment-owned temporary root.

## Frozen provenance

- Producer: [AreCELearnedYet](https://github.com/sfu-db/AreCELearnedYet) at
  commit `aa52da7768023270bad884232972e0b77ec6534a`.
- Code license at that commit: MIT, from the pinned repository `LICENSE`.
- Download reference in the pinned README:
  `https://www.dropbox.com/s/5bmvc1si5hysapf/data.tar.gz?dl=0`.
- Expected archive SHA256:
  `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`.

The pinned README instructs users to download the datasets, but neither that
README nor the repository `LICENSE` specifies a separate data-redistribution
license. The archive was therefore used only for this local, task-authorized
validation attempt; no raw data, pickle, or derived canonical workload is
committed or redistributed.

## Acquisition and independent checks

The archive was fetched on 2026-10-18 into a new temporary root outside the
repository. The response delivered 118,265,504 bytes and the computed SHA256
matched the frozen value exactly. The existing archive inspector found no
absolute or traversal member paths. A separate extraction check found no
symlink, hardlink, or other non-regular member. Only these Forest10 members
were extracted:

```text
data/forest10/original.csv
data/forest10/workload/base.pkl
data/forest10/workload/base-original-label.pkl
```

The verified file results are:

| Artifact | Observed SHA256 | Result |
|---|---|---|
| `original.csv` | `3484f3037f890f6bae46ae51fb387ee883351119667139c5894654276789a73c` | exact match; 581,012 rows, 10 columns |
| `base.pkl` | `501a3dcfe82ec5742fce4c3dc3b298eabcf78b82dab3a8ff8ad2914a61f4eaea` | exact match; bytes only |
| `base-original-label.pkl` | `34d830e6a30b48228ae41e6ae5643fb199e9794b3f36c915fb742af58fdfb974` | exact match; bytes only |
| `forest10.canonical.jsonl.gz` | `a38646ea371189a3fc637fa4851a2a8272ea5f0551d09e801a3b4cc433e15ea3` | derived canonical; historical reference not byte-matched |

The CSV was scanned by the existing strict validator. It has the frozen
ordered ten-column schema, 581,012 rows, finite numeric values or NULL fields,
and zero NULL cells in this source copy. The two pickle files were initially
hashed without deserialization; the later controlled conversion is documented
below.

## Preserved canonical blocker

The downloaded archive contains the opaque workload and label pickles but does
not contain the historical independently audited canonical JSONL.gz. The first
strict `inspect`, `validate_source`, and both `build` commands therefore
failed closed. Those results remain in the `historical_blocker_record` field of
`issue17-acquisition-manifest.json` and are not overwritten by the later
derived result.

## Authorized derived canonical conversion

The researcher decision in Issue #17 authorized one conversion of only the two
hash-matching pickle files. The gated converter is
`experiments/arecel/convert_verified_pickle.py`; it is not imported by the
normal parser, ETL commands, or CI. It requires
`--allow-pinned-pickle-conversion`, verifies both hashes before loading, and
uses a restricted allowlist for `Query`, `Label`, `OrderedDict`, NumPy scalars
and NumPy dtypes. It refuses an existing output.

The conversion was run once using a network-disabled systemd user service with
no-new-privileges, `MemoryMax=2G`, `LimitCPU=120s`, and
`RestrictAddressFamilies=AF_UNIX`. The stronger mount-namespace configuration
was attempted but the host returned `status=226/NAMESPACE` before reading any
pickle. The successful service restricted the converter to the two exact
regular files by code, wrote no input, and atomically wrote only the temporary
output. No credentials, PostgreSQL process, database, or PostgreSQL socket was
accessed.

The executed command used the experiment-owned paths below:

```sh
systemd-run --user --wait --pipe --quiet \
  --property=PrivateNetwork=yes --property=NoNewPrivileges=yes \
  --property=MemoryMax=2G --property=LimitCPU=120s \
  --property=RestrictAddressFamilies=AF_UNIX \
  --setenv=HOME=/tmp --setenv=PYTHONNOUSERSITE=1 \
  /home/wqts/projects/ess-research/.venv/bin/python \
  /home/wqts/projects/ess-research/experiments/arecel/convert_verified_pickle.py \
  --workload-pickle /tmp/ess-research-issue17-data-20261018/arecel/raw/data/forest10/workload/base.pkl \
  --label-pickle /tmp/ess-research-issue17-data-20261018/arecel/raw/data/forest10/workload/base-original-label.pkl \
  --output /tmp/ess-research-issue17-data-20261018/arecel/derived/forest10.canonical.jsonl.gz \
  --allow-pinned-pickle-conversion
```

The converter produced format `arecel-forest10-derived-canonical-v1`, with
20,000 records (10,000 valid and 10,000 test), and SHA256
`a38646ea371189a3fc637fa4851a2a8272ea5f0551d09e801a3b4cc433e15ea3`.
The historical reference SHA is
`a922d87660b2dec431a77c2e4a054c4f5528b0f25040859d76d0148a9ed73e74`; it does
not match and is retained only as a reference. The new bytes use deterministic
JSONL/gzip serialization, an explicit source-query record contract, and unit
weights because the source pickles contain no task weights. The converter
script SHA256 at execution was
`62d762331f26e3bd3f8e976575c47b723a0da5221c093f659bd33cba3ff3af6d`.
After the one-time run, the checked-in script received Ruff formatting plus
type/invalid-record diagnostics; its current SHA256 is
`8bb894256124cb94c9695c3140963fedfeabf18ba8ae281ecbb6439cdf14fc45`. The
change did not affect valid-input conversion semantics, and the hashes are
recorded separately rather than pretending the post-run file was executed.

## Independent record checks

An independent read-only check verified:

| Check | Result |
|---|---:|
| Canonical records | 20,000 |
| Valid/test split | 10,000 / 10,000 |
| Unique stable IDs | 20,000 |
| Contiguous source order in each split | pass |
| Source-SQL SHA256 matches | 20,000 / 20,000 |
| Exact nonnegative truth cardinalities | 20,000 / 20,000 |
| Finite positive weights | 20,000 / 20,000 |

IDs are `arecel:forest10:{split}:{index:06d}` in the canonical source and
`arecel_forest10_{split}_{index:06d}` in ETL output. Predicate provenance,
reconstructed COUNT SQL, source-label cardinality/selectivity, split, source
order, and the unit-weight policy are retained. The pinned `Query` objects do
not contain SQL strings; therefore the COUNT SQL is a deterministic
reconstruction of their ordered predicate map under the documented source
renderer, and is then preserved and SHA256-bound as canonical provenance.

## Strict ETL execution

After updating audit metadata to the explicit derived format, the following
commands were run against the temporary root:

```sh
PYTHONPATH=src .venv/bin/python -m ess_research.arecel.forest10 inspect \
  --data-root <temporary-root>
# exit 0; source_present=true; missing_inputs=[]

PYTHONPATH=src .venv/bin/python -m ess_research.arecel.forest10 build \
  --data-root <temporary-root> \
  --output-dir <temporary-root>/etl-output/forest10-valid-derived-v1 \
  --split valid
# exit 0; record_count=10000

PYTHONPATH=src .venv/bin/python -m ess_research.arecel.forest10 build \
  --data-root <temporary-root> \
  --output-dir <temporary-root>/etl-output/forest10-test-derived-v1 \
  --split test
# exit 0; record_count=10000
```

The resulting manifest and artifact hashes are:

| Split | Manifest | Workload | Truth |
|---|---|---|---|
| valid | `62c14c7de8db1d1c7fa8a0b9a138951c7b28c1fac72a2bf30d1b0fde9d8adb20` | `803469c0de351211abd330fbfdb650f3805880605c8f38956a81f7e106085515` | `768fe20a91b8e140a08cbe421cbccc7c8ffe16144b4c02418982c81143383c4b` |
| test | `66a3744ad816b74d5c6282f0c8b5fdec22d2311d39541c44ba804dc927ce789f` | `4c059f5321491e34eb9b64a6e6636163071adda8bbef5036ca93f02e7d3b0180` | `a962f13c7163e698048428df42aea5c1ea80824409cf979accea726fe83e14ef` |

Both manifests record the derived canonical SHA and historical reference SHA;
truth remains separate from workload rows.

## Pairwise-MCV eligibility diagnostic

The read-only diagnostic `experiments/arecel/classify_pairwise_scope.py`
produced format `arecel-forest10-pairwise-scope-diagnostic-v1`, SHA256
`5bd612015d5c9c79d4c78ae9cb9b7a364d3bdef26138b72ecad9b263f7ec2396`.
Using a single `forest10_original` source table, a conjunctive predicate list,
supported operators (`=`, inequalities and `[]`), and at least two distinct
constrained attributes, it classified:

- 20,000/20,000 as single-table conjunctive with supported predicate syntax;
- 18,011/20,000 as syntactically eligible for the restricted pairwise-MCV
  study.

This is only a source-shape screen. It does not establish PostgreSQL statistic
selection, maximal-matching behavior, or runtime-model applicability.

## Safety and evidence boundary

- No PostgreSQL process, database, catalog, or benchmark was accessed.
- No other project checkout, hidden legacy path, global benchmark directory,
  credential, or DSN was inspected.
- The authorized conversion loaded only the two exact SHA256-pinned files in
  the controlled process described above; no arbitrary pickle is accepted by
  the converter or normal ETL.
- The machine-local staging root is intentionally not a repository dependency.
  `issue17-acquisition-manifest.json` is the durable summary of hashes, checks,
  prior blocker evidence, and the derived result.

## Tests and remaining limitation

The focused ETL suite, including positive and negative derived-audit tests,
passed: **20 passed**. The converter's no-flag negative gate returned exit 2
without creating output. The full CI-equivalent offline selection passed:
**51 passed**, and the standalone evidence checker verified **4 manifests / 131
committed evidence files**. Raw data, pickle inputs, and large derived outputs
remain outside Git. The result is a versioned derived canonical contract, not
the unavailable historical canonical byte stream. The eligibility count must
not be used as PostgreSQL runtime evidence without a separate controlled
experiment.
