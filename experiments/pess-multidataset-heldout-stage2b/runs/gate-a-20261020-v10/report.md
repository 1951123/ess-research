# Gate A review-response report: archive-first v10

Evidence label: **Experimentally observed — blocked Gate A readiness.** The
archive-first data and PG runtime checks ran, but the frozen claimed-clause
trace requirement is unmet. This report does not authorize or report
Empty/Nominal/PESS/Joint-Robust held-out outcomes, a PESS theorem, PostgreSQL
scheme containment, latency, or a generic maintenance-cost result.

## Contract and execution order

- Issue: `1951123/ess-research#48`
- Contract: `protocol-v2.json`, SHA-256
  `94791c70f7ed2e1c3efc56beba758da4a851afd19fdee1517b0849619e1f094b`
- Review-response code is based on PR #55 commit `c454c40`.
- Archive-first implementation: merge commit
  `68fcd5cc9900f798f503edeeb9e79669beebee92`
- AreCEL upstream commit:
  `aa52da7768023270bad884232972e0b77ec6534a`
- Whole archive SHA-256:
  `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`
- Environment roots: `ESS_DATA_ROOT=/home/wqts/ess-data` and
  `ESS_RUNTIME_PARENT=/home/wqts/ess-runtime`
- Entry point: `from ess_research.arecel import prepare`; Forest10 and
  Census13 were prepared independently. No CLI data-root bypass or old
  materialized input path was used.

PG source and binary provenance are now audited before `prepare` can launch a
runtime probe or create a cluster. A provenance failure therefore produces no
PG runtime probe.

The v10 command was the same explicit archive-first command as v9, with a new
exclusive output directory:

```text
ESS_DATA_ROOT=/home/wqts/ess-data ESS_RUNTIME_PARENT=/home/wqts/ess-runtime \
ESS_WORKTREE_PARENT=/home/wqts/ess-worktrees PYTHONPATH=src \
.venv/bin/python experiments/pess-multidataset-heldout-stage2b/gate_audit.py \
  --pg-source /home/wqts/ess-runtime/issue38/pg-src \
  --pg-prefix /home/wqts/ess-runtime/issue38/pg-prefix \
  --pg-build-manifest /home/wqts/ess-runtime/issue38/results/heldout-v1/runtime-manifest.json \
  --output experiments/pess-multidataset-heldout-stage2b/runs/gate-a-20261020-v10/gate-audit.json
```

## Data and runtime checks

Forest10 and Census13 independently passed archive/schema/workload/truth-ID
validation, including 100,000 train, 10,000 valid, and 10,000 test records,
unique IDs, aligned workload/truth records, and truth-free probe selection.
The source was clean at PG commit
`23c7c2fdd4bfb561f3257d947fee956a2999fdb6`; all required source markers were
present. The actual five PG binary SHA-256 values matched the supplied clean
build manifest and all binaries reported PostgreSQL `16.14`.

| dataset | fixed sample SHA-256 | bytes | sample target | tuple count |
| --- | --- | ---: | ---: | ---: |
| Forest10 | `525f72e08f974c569cc00beca1ad0a4030ec79343aaa384c2555b460574a5b99` | 10,620,460 | 90,000 | 90,000 |
| Census13 | `0ff61bcce532a8af07f9319365c28d6fb07e373fc4b8049bae7c72c349baba26` | 8,144,782 | 90,000 | 48,842 |

Each dataset used a fresh Issue-48-owned cluster and replayed its new fixed
sample before statistics `ANALYZE`. The complete OID/name/stxkeys/target/MCV
ledger is in `gate-audit.json`.

## Probe coverage and blocker

The frozen validation rules retain a source-order shape-control query and add a
source-order query for the first predeclared candidate with a positive MCV
payload and both source columns present. Selection uses workload shape and
catalog payload presence only; no truth or estimate is used.

| dataset | control query | positive-MCV probe | selected statistic(s) | positive pre-clamp |
| --- | --- | --- | --- | ---: |
| Forest10 | `arecel:forest10:valid:000000` | `arecel:forest10:valid:000003` / `e12` | OID 16394 / `ess2b_forest10_e12` | `0.069499843588091886` |
| Census13 | `arecel:census13:valid:000000` | `arecel:census13:valid:000000` / `c01` | OIDs 16389, 16394 / `ess2b_census13_c01`, `ess2b_census13_c56` | `0.0041369459237719439` |

Numeric pre-clamp tracing is `VERIFIED` for both datasets. Selected OID
mapping is `VERIFIED` and no selected OID is unmapped. Forest10’s new probe
demonstrates effective selection of a positive-payload MCV object; its original
shape-control remains an empty-selection control.

The independent claimed-clause check is `UNVERIFIED` for both datasets:
`selected_trace_records` and `claimed_clause_indices` are empty because this
approved build emits no independent `claimed_clause_index` records. The
numeric `stat_clause_count` field is retained as raw evidence but is not
converted into claimed-clause indices. Since the frozen contract requires this
evidence independently, the v10 overall status is **`BLOCKED`**. Addressing
the missing instrumentation would require a separately authorized PostgreSQL
source task; no cross-repository instrumentation was performed here.

## Negative-contract coverage and next boundary

The expanded offline suite covers provenance-before-probe gating, cluster
identity mismatch, missing/corrupt samples, absent or nonpositive numeric
traces, unmapped selected OIDs, selected statistics without positive MCV
payload, deterministic truth-free probe selection, exclusive evidence writes,
and the claimed-clause fail-closed status.

Before any held-out outcome protocol, the frozen contract now records the open
requirements to define stricter edge/equality eligibility, measure SQL
fingerprint/group overlap across splits, demonstrate actual Stage 1A Forest10
cohort exclusion, and separate requested/payload-present/selected ledgers.
