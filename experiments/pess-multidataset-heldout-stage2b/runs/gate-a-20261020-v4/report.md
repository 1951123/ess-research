# Stage 2B Gate A audit — 2026-10-20

Evidence label: **experimentally observed input availability only**.

This is a read-only audit after the input-only protocol freeze commit
`7d3871a`.  It did not deserialize pickles, create a PostgreSQL cluster, select
test IDs, inspect test outcomes, or run a query measurement.

## Command and provenance

```text
python3 experiments/pess-multidataset-heldout-stage2b/gate_audit.py \
  --data-root /home/wqts/ess-data \
  --pg-source /home/wqts/projects/ess-postgresql \
  --output experiments/pess-multidataset-heldout-stage2b/runs/gate-a-20261020-v4/gate-audit.json
```

The explicit data root was `/home/wqts/ess-data`.  The PostgreSQL checkout was
read-only at `23c7c2fdd4bfb561f3257d947fee956a2999fdb6`, with the required
`ESS_MCV_TRACE` and `ESS_MCV_NUMERIC_TRACE` markers in the inspected source
files.  The machine-local Issue-owned runtime root and a Stage 2B build/sample
manifest were not supplied, so runtime readiness remains blocked.

The executed audit script SHA256 was
`f707128e9b453ba0eea6e0c1ae07acac3016ea9f2cd64423ad9a1227d77c33de`.
The frozen protocol SHA256 recorded in the JSON result is
`62780cd536994472364096c22d7e5d07cd91f4456d80cf66fd5a911aef5cfb90`.

## Result

| Dataset / prerequisite | Status | Evidence |
|---|---|---|
| Forest10 | AVAILABLE | CSV hash `3484f303…9a73c`; 581,012 rows; derived canonical hash `a38646ea…e15ea3`; 10,000 valid + 10,000 test; 20,000 unique IDs and source-SQL hashes checked; pinned pickles hash-checked without deserialization |
| Census13 | MISSING | `/home/wqts/ess-data/arecel/raw/data/census13/original.csv` absent |
| DMV11 | MISSING | `/home/wqts/ess-data/arecel/raw/data/dmv11/original.csv` absent |
| Power7 | MISSING | `/home/wqts/ess-data/arecel/raw/data/power7/original.csv` absent |
| PostgreSQL source/trace checkout | AVAILABLE | exact expected HEAD and source markers present |
| Stage 2B runtime root / fixed samples | BLOCKED | no Issue-owned runtime root or per-dataset sample/build manifest supplied |

Overall Gate A status is **BLOCKED**.  Only one dataset has verified source
inputs, and there is no authorized runtime root for matched PostgreSQL
measurement.  The prior ETL pairwise counts are source-shape diagnostics only;
they are not substituted for this gate.

## Limitations and next validation

This report establishes neither MCV payload availability nor actual statistic
selection, model adequacy, maintenance cost, latency, or a physical PESS
guarantee.  The next valid step is to provide a researcher-approved explicit
root containing the pinned Census13/DMV11/Power7 inputs (or narrow the issue
with an explicit follow-up), then rerun Gate A with a dedicated source-pinned
PG build, fixed-sample manifests, and an Issue-owned disposable cluster.
