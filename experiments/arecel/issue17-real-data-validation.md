# Issue #17 Forest10 acquisition and ETL validation

**Status: BLOCKED / NOT COMPLETE.**

This report records an actual local acquisition attempt for Issue #17. It does
not claim that the complete Forest10 workload was built. Raw files and pickle
bytes were kept outside Git in a temporary, experiment-owned staging root and
are not redistributed by this repository.

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
| `forest10.canonical.jsonl.gz` | unavailable | expected hash not validated |

The CSV was scanned by the existing strict validator. It has the frozen
ordered ten-column schema, 581,012 rows, finite numeric values or NULL fields,
and zero NULL cells in this source copy. The two pickle files were hashed but
never imported, loaded, or deserialized.

## Canonical-workload blocker

The downloaded archive contains the opaque workload and label pickles but does
not contain the required independently audited canonical JSONL.gz. No such
artifact is present in the permitted `ess-research` checkout. Because normal
ETL must not deserialize untrusted pickle data, the canonical workload cannot
be reconstructed by the current pipeline.

The staged audit metadata declared the frozen canonical hash, but did not
invent a file for it. The commands below therefore fail closed:

```sh
PYTHONPATH=src .venv/bin/python -m ess_research.arecel.forest10 inspect \
  --data-root "$DATA_ROOT"
# status: BLOCKED_MISSING_INPUT
# missing: arecel/audit-v1/forest10.canonical.jsonl.gz

PYTHONPATH=src .venv/bin/python -m ess_research.arecel.forest10 build \
  --data-root "$DATA_ROOT" \
  --output-dir "$DATA_ROOT/etl-output/forest10-valid-v1" \
  --split valid
# exit status 2: missing required canonical JSONL.gz

PYTHONPATH=src .venv/bin/python -m ess_research.arecel.forest10 build \
  --data-root "$DATA_ROOT" \
  --output-dir "$DATA_ROOT/etl-output/forest10-test-v1" \
  --split test
# exit status 2: missing required canonical JSONL.gz
```

Neither output directory was created. The valid/test split counts, stable
query IDs, truth/source separation, and output manifests were consequently not
claimed. Pairwise-MCV eligibility was also not assessed: that requires the
canonical query predicates and labels, not just the base CSV.

## Safety and evidence boundary

- No PostgreSQL process, database, catalog, or benchmark was accessed.
- No other project checkout, hidden legacy path, global benchmark directory,
  credential, or DSN was inspected.
- No pickle conversion was attempted; pickle opcodes were not executed.
- The machine-local staging root is intentionally not recorded as a repository
  dependency. `issue17-acquisition-manifest.json` is the durable summary of
  hashes, checks, blockers, and safety status.

## Single next action

Supply the independently audited canonical JSONL.gz artifact with SHA256
`a922d87660b2dec431a77c2e4a054c4f5528b0f25040859d76d0148a9ed73e74` under the
declared data root. Then rerun `inspect` and the two non-overwriting split
builds without changing the transformation contract.
