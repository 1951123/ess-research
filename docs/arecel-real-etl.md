# AreCEL real-data ETL for Census13, DMV11 and Power7

This document describes the reusable ETL boundary added for Issue #19.  It is
an input-preparation workflow, not a PostgreSQL experiment or a claim about
cardinality-estimator fidelity.

## Frozen source contract

The producer is AreCELearnedYet at commit
`aa52da7768023270bad884232972e0b77ec6534a`.  Its code is MIT licensed.  The
pinned README supplies the Dropbox archive URL, but does not state a separate
data-redistribution license; the archive was therefore used for local,
research-authorized validation only.  Raw data, pickles, canonical workloads,
and built JSON artifacts are not committed.

The archive SHA256 is
`5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`.
The source schemas audited from the pinned historical adapters are:

| Dataset | Relation | Rows | Columns | Nullability |
|---|---|---:|---:|---|
| Census13 | `public.census13` | 48,842 | 13; 8 `DOUBLE PRECISION`, 5 `VARCHAR(64)` | not-null contract; observed CSV has no empty cells |
| DMV11 | `public.dmv11` | 11,591,877 | 10 `VARCHAR(64)`, 1 `DOUBLE PRECISION` | nullable; observed CSV has no empty cells |
| Power7 | `public.power7` | 2,075,259 | 7 `DOUBLE PRECISION` | nullable; observed CSV has no empty cells |

The exact source column order, all frozen input hashes, derived hashes, and
observed null counts are in
[`issue19-acquisition-manifest.json`](../experiments/arecel/issue19-acquisition-manifest.json).

## Input and output layout

Every command requires an explicit `--data-root`; no environment or historical
global path is consulted:

```text
<root>/arecel/incoming/arecel-data.tar.gz
<root>/arecel/raw/data/{census13,dmv11,power7}/original.csv
<root>/arecel/raw/data/{dataset}/workload/base.pkl
<root>/arecel/raw/data/{dataset}/workload/base-original-label.pkl
<root>/arecel/audit-v1/audit.json
<root>/arecel/audit-v1/{dataset}.canonical.jsonl.gz
```

`real.py audit` creates the small audit manifest only after complete CSV and
canonical validation.  `inspect` validates the archive, CSV, opaque pickle
hashes, audit, canonical record identity, source-query self-hashes, exact
nonnegative labels, and all observed splits.  `build` writes a new,
non-overwriting directory under `etl-output/` or `experiment-data/` containing
separate `workload.json`, `truth.json`, and `manifest.json` artifacts.

The three pinned pickle roots actually contain `train=100000`, `valid=10000`,
and `test=10000` records.  All three splits are preserved and were built for
all three datasets; the ETL does not silently discard `train`.

## Controlled conversion boundary

`experiments/arecel/convert_verified_pickles.py` is not imported by normal ETL
or CI.  It requires `--allow-pinned-pickle-conversion`, checks the exact
dataset-specific workload and label SHA256 values before deserialization, and
allows only the pinned `Query`/`Label`, ordered mapping, set/frozenset, and
NumPy scalar/dtype constructors.  The executed service used:

- Python 3.12.3 and NumPy 2.5.4;
- `PrivateNetwork=yes`, `NoNewPrivileges=yes`, `RestrictAddressFamilies=AF_UNIX`;
- `MemoryMax=2G`, `LimitCPU=120s`;
- only the three exact workload/label files as inputs and a temporary output.

The current converter script SHA256 at the final replay was
`398e969faaa37e49a5cf65189c678662839797fd4ae4155fdcc2e6cbe9017c77`.  A
current-script replay for each dataset reproduced the derived canonical bytes
byte-for-byte.  The derived canonical SHA is deliberately distinct from the
historical canonical reference SHA; no historical byte identity is claimed.

The Query objects do not contain raw SQL.  The converter reconstructs a
deterministic COUNT SQL record while preserving predicate values, operators,
and mapping order.  The ETL then adapts only the audited projection, relation,
and schema identifiers.  Thus `source_sql` is an auditable reconstruction,
not a claim to preserve unavailable original SQL bytes.

## Pairwise scope diagnostic

`experiments/arecel/classify_pairwise_scope_real.py` checks only canonical
source shape: one declared table, a conjunctive predicate list, supported
operators, and at least two distinct constrained attributes.  The resulting
counts are syntax diagnostics only.  They do not demonstrate PostgreSQL
statistic selection, maximal matching, or runtime applicability.

The full execution record, commands, environment, hashes, and limitations are
in [`issue19-real-data-validation.md`](../experiments/arecel/issue19-real-data-validation.md).
