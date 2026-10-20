# Gate A readiness report: archive-first v9

Evidence label: **Experimentally observed — Gate A readiness only.** This
report does not authorize or report Empty/Nominal/PESS/Joint-Robust held-out
outcomes, a PESS theorem, PostgreSQL scheme containment, latency, or a generic
maintenance-cost result.

## Frozen contract and command

- Issue: `1951123/ess-research#48`
- Contract: `protocol-v2.json`, SHA-256
  `80ea2bfbdbb2a1b2a8e13c2d540c9afe9114cadd55c53a05ddfc9fd9d0476281`
- Outcome-free contract commit: `8d2abf3`
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

Command executed from the Issue-48 worktree:

```text
ESS_DATA_ROOT=/home/wqts/ess-data ESS_RUNTIME_PARENT=/home/wqts/ess-runtime \
ESS_WORKTREE_PARENT=/home/wqts/ess-worktrees PYTHONPATH=src \
.venv/bin/python experiments/pess-multidataset-heldout-stage2b/gate_audit.py \
  --pg-source /home/wqts/ess-runtime/issue38/pg-src \
  --pg-prefix /home/wqts/ess-runtime/issue38/pg-prefix \
  --pg-build-manifest /home/wqts/ess-runtime/issue38/results/heldout-v1/runtime-manifest.json \
  --output experiments/pess-multidataset-heldout-stage2b/runs/gate-a-20261020-v9/gate-audit.json
```

The compact machine-readable evidence is [`gate-audit.json`](gate-audit.json).
The run completed with `overall_status: GATE_A_READY`.

## Data verification

Both datasets were independently verified from the pinned archive, with
100,000 train, 10,000 validation, and 10,000 test IDs; unique IDs; aligned
workload/truth records; shape-only smoke-query choice; and no truth use for
selection.

| dataset | source rows | table SHA-256 | shape-eligible train/valid/test |
| --- | ---: | --- | ---: |
| Forest10 | 581,012 | `3484f3037f890f6bae46ae51fb387ee883351119667139c5894654276789a73c` | 90,026 / 8,995 / 9,016 |
| Census13 | 48,842 | `f751fc7ecd5bd5e62acd9868a0bbe36413528b6eb2de9c2fc8fcf71d9ef2c13a` | 92,360 / 9,239 / 9,203 |

## PostgreSQL readiness

The source was clean at commit
`23c7c2fdd4bfb561f3257d947fee956a2999fdb6`, with
`ESS_MCV_TRACE`, `ESS_MCV_NUMERIC_TRACE`, and the numeric configure flag
present. The supplied binary manifest matched the actual SHA-256 values for
`postgres`, `initdb`, `pg_ctl`, `psql`, and `pg_config`; all reported
PostgreSQL `16.14`.

Each dataset used a fresh Issue-48-owned cluster, socket, port, and server
log. A new `ESSANL01` fixed sample was exported and replayed before the
statistics `ANALYZE`; the old Issue #38 sample was not reused.

| dataset | fixed sample SHA-256 | bytes | sample target | tuple count | smoke query | positive pre-clamp |
| --- | --- | ---: | ---: | ---: | --- | ---: |
| Forest10 | `9dbfcd8ee9157413d8da7732f8a9b5675fbaf65a7311f1a42a495d0c509f4a65` | 10,620,460 | 90,000 | 90,000 | `arecel:forest10:valid:000000` | `38610.439564843822` |
| Census13 | `0ff61bcce532a8af07f9319365c28d6fb07e373fc4b8049bae7c72c349baba26` | 8,144,782 | 90,000 | 48,842 | `arecel:census13:valid:000000` | `0.0041369459237719439` |

The catalog ledger recorded all six predeclared candidate statistics per
dataset, their OIDs, `stxkeys`, target 300, MCV-payload presence, and item
counts. The Census13 smoke trace selected OIDs `16389` and `16394`, mapped to
`ess2b_census13_c01` and `ess2b_census13_c56`; no selected OID was unmapped.
The Forest10 smoke trace selected no MCV statistic and still produced the
required positive numeric pre-clamp trace. The raw numeric trace records
`stat_clause_count` where emitted. This build emitted no independent
`claimed_clause_index` field, so `claimed_clause_indices` is recorded as an
empty list rather than inferred.

## Boundary and next step

`GATE_A_READY` means that archive-first inputs and PostgreSQL readiness are
available for the next separately authorized stage. It is not an outcome
result. The next validation step is to obtain explicit approval for a new
outcome protocol, then collect held-out results under that frozen protocol.
