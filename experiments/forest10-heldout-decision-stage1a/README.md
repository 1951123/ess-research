# Stage 1A: held-out Forest10 decision-value validation

This directory owns Issue #38 only. It evaluates the already frozen Issue #23
Forest10 candidate/resource decisions on a deterministic held-out `test`
cohort using actual PostgreSQL 16.14 estimates. It does not retrain, select
resources, alter PostgreSQL source, or overwrite Issue #23 evidence.

The disposable cluster is initialized separately for this Issue. The verified
CSV is loaded in source order, and candidate statistics are dropped/recreated
in frozen candidate-ID order for each set. The approved Issue #23 fixed sample
is accepted only when PostgreSQL's relation identity and physical page count
match its header; the runner does not weaken this check or silently generate a
replacement sample.

## Phase 0 protocol freeze

`freeze_protocol.py` reads the researcher-approved external Forest10 source
under an explicit `--data-root`, verifies the Issue #23 hashes, and writes
`protocol.json`. Selection uses only test query IDs, source-query hashes,
syntax eligibility, and candidate endpoint coverage. It never reads source
truths, PostgreSQL estimates, model losses, or timing while choosing the
held-out IDs. The protocol retains every tied Issue #23 optimal set and records
that no legitimate greedy set was defined in the frozen reference.

The first commit for this directory must be the protocol-only freeze. No
PostgreSQL held-out outcomes may be collected before that commit.

Example protocol freeze command (the external root is not inferred):

```text
python3 experiments/forest10-heldout-decision-stage1a/freeze_protocol.py \
  --data-root /home/wqts/ess-data \
  --manifest experiments/forest10-decision/real-input-manifest.json \
  --evidence experiments/forest10-decision/real-model-evidence.json \
  --output experiments/forest10-heldout-decision-stage1a/protocol.json
```

## Measurement and analysis replay

The completed run used the pinned PostgreSQL source at commit
`23c7c2fdd4bfb561f3257d947fee956a2999fdb6`, built privately with
`-DESS_MCV_NUMERIC_TRACE`, and an Issue-owned cluster at
`/home/wqts/ess-runtime/issue38/pgdata-replay` / socket
`/home/wqts/ess-runtime/issue38/socket-replay` / port `55639`. The cluster was
bootstrapped with next OID `16384`, loaded from the verified CSV in source
order, and shut down after collection. The exact run command and hashes are in
the external runtime manifest and committed report; raw data are intentionally
not copied into Git.

After rebuilding/starting an equivalent private cluster, the measurement
entrypoint is:

```text
python3 experiments/forest10-heldout-decision-stage1a/run_heldout.py \
  --data-root /home/wqts/ess-data \
  --protocol experiments/forest10-heldout-decision-stage1a/protocol.json \
  --pg-bin /home/wqts/ess-runtime/issue38/pg-prefix/bin \
  --lib-dir /home/wqts/ess-runtime/issue38/pg-prefix/lib \
  --pg-source /home/wqts/ess-runtime/issue38/pg-src \
  --socket-dir /home/wqts/ess-runtime/issue38/socket-replay \
  --port 55639 --database postgres \
  --server-log /home/wqts/ess-runtime/issue38/logs/server-replay.log \
  --sample /home/wqts/ess-data/pg-calibration/issue23/forest10.sample \
  --output-dir /home/wqts/ess-runtime/issue38/results/heldout-v1-rerun
```

Then run `analyze_heldout.py` against that raw directory and
`render_report.py` against its bounded summary. The analyzer refuses incomplete
or invalid raw runs.

## Evidence boundary

The primary result, if Gate A passes, is descriptive paired pre-clamp
PostgreSQL behavior on the frozen cohort. It is not a universal PostgreSQL
claim, a proof that real choices equal the maximal-matching family, a runtime
or latency benchmark, or a physical maintenance-cost result. Raw Forest10
rows, pickles, PGDATA, traces, and large logs remain outside Git under the
Issue-owned runtime root; only bounded hashed summaries and reproducibility
metadata belong here.
