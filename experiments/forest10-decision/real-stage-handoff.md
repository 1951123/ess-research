# Issue #23 real Forest10 handoff

Status: **completed on the continuation branch; review pending**. This file is
the protocol handoff; measured hashes and results are in
[real-stage-report.md](real-stage-report.md). Raw data and calibration output
remain outside Git under `ESS_DATA_ROOT=/home/wqts/ess-data`.

## Required input contract

The caller must provide one explicit absolute data root. The expected layout is
the validated Issue #17 `arecel` layout:

```text
<root>/arecel/incoming/arecel-data.tar.gz
<root>/arecel/audit-v1/audit.json
<root>/arecel/audit-v1/forest10.canonical.jsonl.gz
<root>/arecel/raw/data/forest10/original.csv
<root>/arecel/raw/data/forest10/workload/base.pkl
<root>/arecel/raw/data/forest10/workload/base-original-label.pkl
```

The pinned provenance to verify before using the data is:

| Artifact | Expected SHA-256 |
|---|---|
| upstream source commit | `aa52da7768023270bad884232972e0b77ec6534a` |
| `original.csv` | `3484f3037f890f6bae46ae51fb387ee883351119667139c5894654276789a73c` |
| historical canonical reference | `a922d87660b2dec431a77c2e4a054c4f5528b0f25040859d76d0148a9ed73e74` |
| derived canonical used by Issue #17 | `a38646ea371189a3fc637fa4851a2a8272ea5f0551d09e801a3b4cc433e15ea3` |
| workload `base.pkl` | `501a3dcfe82ec5742fce4c3dc3b298eabcf78b82dab3a8ff8ad2914a61f4eaea` |
| truth `base-original-label.pkl` | `34d830e6a30b48228ae41e6ae5643fb199e9794b3f36c915fb742af58fdfb974` |

The audit records and these exact values must be copied into the execution
manifest. The real candidate
rule, query selection, statistics target, budgets, and evaluation-order set
must be frozen before inspecting strategy outputs. Keep calibration/training
records separate from the held-out test split.

## Reproducible invocation

From the repository root, with `DATA_ROOT` supplied by the researcher:

```bash
DATA_ROOT=/home/wqts/ess-data
PYTHONPATH=src python3 -m ess_research.arecel.forest10 inspect \
  --data-root "$DATA_ROOT"
PYTHONPATH=src python3 -m ess_research.arecel.forest10 build \
  --data-root "$DATA_ROOT" \
  --output-dir "$DATA_ROOT/etl-output/forest10-valid-issue23" \
  --split valid
python3 experiments/arecel/classify_pairwise_scope.py \
  --canonical "$DATA_ROOT/arecel/audit-v1/forest10.canonical.jsonl.gz" \
  --output "$DATA_ROOT/experiment-data/forest10-pairwise-scope-issue23.json"
python3 experiments/forest10-decision/run_pg_calibration.py \
  --data-root "$DATA_ROOT" \
  --pg-bin /tmp/ess-pg-forest10-issue23-prefix/bin \
  --lib-dir /tmp/ess-postgresql-issue23-numeric/src/interfaces/libpq \
  --socket-dir /tmp/ess-pg-forest10-issue23-socket \
  --server-log "$DATA_ROOT/pg-calibration/issue23/server.log" \
  --sample "$DATA_ROOT/pg-calibration/issue23/forest10.sample" \
  --output-dir "$DATA_ROOT/pg-calibration/issue23"
python3 experiments/forest10-decision/build_real_instance.py \
  --data-root "$DATA_ROOT" \
  --calibration "$DATA_ROOT/pg-calibration/issue23/calibration.json" \
  --output "$DATA_ROOT/experiment-data/forest10-real-pg-instance.json"
python3 experiments/forest10-decision/run_experiment.py \
  --data-root "$DATA_ROOT" \
  --instance "$DATA_ROOT/experiment-data/forest10-real-pg-instance.json" \
  --output-dir "$DATA_ROOT/experiment-data/forest10-real-decision-results"
```

The `inspect` and `build` commands are fail-closed and require outputs under
the explicit root. The pairwise screen is syntactic source-shape evidence only;
it does not identify PostgreSQL-selected statistics or calibrate coefficients.
The run must record the canonical/source hashes, row counts, split, query IDs,
truth cardinalities, and the exact candidate manifest before optimization.

## PostgreSQL calibration gate

The PG stage is separate from the mathematical smoke pilot. Use the merged
`ess-postgresql` fixed-sample interface at commit
`23c7c2fdd4bfb561f3257d947fee956a2999fdb6` and the audited `ess-advisor`
interface at its recorded commit. Record the PostgreSQL server version,
repository commits, statistics target, fixed sample file SHA-256, sample export
and import commands, statistic-object identities/OIDs, actual MCV contents,
and representative cardinality estimates. Verify that fixed-sample replay
actually controls `ANALYZE`; do not use replay-mode `ANALYZE` wall time as
physical maintenance cost.

The real stage must distinguish three evidence layers: exact mathematical
optimization, PG calibration observations, and real PostgreSQL estimate
behavior. The completed run retained the zero-truth task with the prescribed
`T_i=max(1,N_i)=1` floor; its measured baseline and eligible candidate
pre-clamp estimates were positive, so no replacement or synthetic truth was
used.
If a future replay or source contract differs, leave the affected layer blocked
and do not substitute synthetic coefficients.
