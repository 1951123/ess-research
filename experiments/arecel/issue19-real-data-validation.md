# Issue #19 real-data validation

**Evidence label: experimentally observed.** This report records commands
actually executed on 2026-10-18 (Asia/Shanghai), with raw and large derived
files kept outside Git. The durable hash summary is
[`issue19-acquisition-manifest.json`](issue19-acquisition-manifest.json).

## Source and environment

The source was the pinned AreCELearnedYet archive at commit
`aa52da7768023270bad884232972e0b77ec6534a`.  The archive was reused from the
explicit Issue #17 staging root, copied to a new explicit Issue #19 temporary
root, then independently hashed as
`5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`.
All twelve required CSV/pickle members for the three datasets were present;
archive member inspection rejected traversal/absolute paths and non-regular
members.  The raw CSV and pickle hashes match the frozen historical adapter
identities; see the manifest for all values.

The final replay used Python 3.12.3, NumPy 2.5.4, and the converter script
SHA256 `398e969faaa37e49a5cf65189c678662839797fd4ae4155fdcc2e6cbe9017c77`.
Each conversion ran in a systemd user service with `PrivateNetwork=yes`,
`NoNewPrivileges=yes`, `RestrictAddressFamilies=AF_UNIX`, `MemoryMax=2G`, and
`LimitCPU=120s`.  The normal ETL module never deserializes pickle files.

## Conversion and canonical identity

The actual pickle roots contained three splits, not only valid/test:

| Dataset | train | valid | test | derived canonical SHA256 |
|---|---:|---:|---:|---|
| Census13 | 100,000 | 10,000 | 10,000 | `fc31f94d1deb83ba67cc1144d2628f0f8fe9d1f17597d766e2829f0e83788035` |
| DMV11 | 100,000 | 10,000 | 10,000 | `f4e6f5747248b0ead853fa71c7f9931c8db79a16dea219c44e53ddf449850632` |
| Power7 | 100,000 | 10,000 | 10,000 | `332f645d9aafaf1e1068c79898bec690446aeb484f59099d1d0b8109db2df64c` |

The current-script replay command was, for each dataset:

```sh
systemd-run --user --wait --pipe --quiet \
  --property=PrivateNetwork=yes --property=NoNewPrivileges=yes \
  --property=MemoryMax=2G --property=LimitCPU=120s \
  --property=RestrictAddressFamilies=AF_UNIX \
  --setenv=PYTHONNOUSERSITE=1 --setenv=PYTHONPATH=/home/wqts/projects/ess-research-issue19/src \
  /tmp/ess-research-issue19-venv/bin/python \
  experiments/arecel/convert_verified_pickles.py \
  --dataset DATASET --workload-pickle ROOT/arecel/raw/data/DATASET/workload/base.pkl \
  --label-pickle ROOT/arecel/raw/data/DATASET/workload/base-original-label.pkl \
  --output ROOT/arecel/replay-formatted/DATASET.canonical.jsonl.gz \
  --allow-pinned-pickle-conversion
```

`cmp` passed between each replay output and the corresponding canonical file
used by ETL.  The historical canonical references are retained but are not
claimed to match: Census13 `9bcfc8…`, DMV11 `71bb6e…`, Power7 `9f1b11…`.

Development boundary results were also recorded: the initial converter
rejected the observed `train/valid/test` roots under its earlier valid/test
assumption; after the split correction, the final current-script replay above
completed successfully.  A no-flag negative invocation returned exit status 2
and created no output.  No failed intermediate output is used as evidence.

## Full source validation and ETL

The following commands were run with `PYTHONPATH=src` and the explicit
temporary root:

```sh
python -m ess_research.arecel.real audit --data-root ROOT
python -m ess_research.arecel.real inspect --data-root ROOT --dataset DATASET
python -m ess_research.arecel.real build --data-root ROOT --dataset DATASET \
  --output-dir ROOT/etl-output/DATASET-SPLIT-derived-v1 --split SPLIT
```

`audit` completed with manifest SHA256
`51be8e2bc6782af5facf726cc292d46ad82a2063d1a195dfa535373f7b1b1a68`.
All three `inspect` commands returned 0 with `source_present=true`, exact
row counts, zero observed empty cells, and the three observed split counts.
All nine non-overwriting builds returned 0:

- Census13: train 100,000; valid 10,000; test 10,000.
- DMV11: train 100,000; valid 10,000; test 10,000.
- Power7: train 100,000; valid 10,000; test 10,000.

Each build wrote separate workload/truth/manifest files. Their SHA256 values
are recorded per split in the acquisition manifest; no truth cardinality is
present in workload rows.

## Pairwise-MCV source-shape screen

The command below was run once per dataset:

```sh
python experiments/arecel/classify_pairwise_scope_real.py \
  --dataset DATASET --canonical ROOT/arecel/audit-v1/DATASET.canonical.jsonl.gz \
  --output ROOT/pairwise/DATASET.json
```

Results:

| Dataset | Single-table/conjunctive/supported | At least two attributes / eligible |
|---|---:|---:|
| Census13 | 120,000 / 120,000 | 110,802 / 120,000 |
| DMV11 | 120,000 / 120,000 | 109,129 / 120,000 |
| Power7 | 120,000 / 120,000 | 102,967 / 120,000 |

This is a read-only syntax screen over the derived source-query records.  It
does not establish which PostgreSQL statistic objects are selected, whether a
query is executable on a particular catalog, or any maximal-matching/runtime
claim.

## Tests actually run

```sh
PYTHONPATH=src python -m pytest -q \
  tests/test_arecel_real_etl.py tests/test_forest10_etl.py \
  tests/test_verified_pickle_converter.py
# 38 passed in 0.13s

ruff check ...
# All checks passed
ruff format --check ...
# 4 files already formatted
git diff --check
# exit 0
```

The new tests cover all three schemas, SQL adaptation, missing-input failure,
canonical truth/order checks, observed split preservation, restricted-global
and wrong-hash rejection, deterministic gzip, and no-overwrite behavior.

## Limitations

This result is trustworthy benchmark-input preparation only.  It does not
validate database-recomputed truth, PostgreSQL planner behavior, MCV selection,
maintenance cost, or estimator accuracy.  The historical Query objects did
not carry raw SQL text, so `source_sql` is a deterministic reconstructed
contract that preserves predicate semantics/order; it is not byte-identical
historical SQL.  The source code is MIT licensed, but the pinned upstream does
not state a separate data license, so no raw or large derived data is included
in this PR.
