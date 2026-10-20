# Gate A review-response report: archive-first v11-r2

Evidence label: **Experimentally observed — `GATE_A_READY` infrastructure
readiness.** This run does not collect or report Empty/Nominal/PESS/Joint-Robust
held-out outcomes, a PESS theorem, PostgreSQL scheme containment, latency, or a
generic maintenance-cost result.

## Scope and corrected implementation

Issue #56 repaired the Gate A trace collector in
`experiments/pess-multidataset-heldout-stage2b/gate_audit_v2.py`.

- Capture is bounded by the pre-probe log offset and a post-marker quiet
  interval for asynchronous PostgreSQL log writes.
- The query-specific marker identifies exactly one backend PID. Marker lines
  from multiple PIDs, missing PID prefixes, prior-query markers, absent raw
  logs, and malformed trace records fail closed.
- Marker-free `ESS_MCV_TRACE` records are retained as raw MCV records and are
  associated only when their `[%p]` PID matches the marker's PID. Interleaved
  foreign-backend records remain raw evidence but are not evaluated.
- Numeric and MCV raw records are retained separately. Selected OIDs and
  `claimed_clause_index` records are parsed separately; `stat_clause_count` is
  never treated as a clause-index list.
- Claimed-clause status is **OID-level claim presence only**. It is not proof
  of full clause-set completeness.

The first v11 attempt is preserved in `../gate-a-20261020-v11/` with its
fail-closed parser diagnostic. It was not overwritten. This `v11-r2` directory
is the corrected, exclusive rerun.

## Frozen contract and provenance

- Protocol: `protocol-v3.json`, SHA-256
  `f4feb957a6f1618b1d346ff4415d06a859eba2af5bf7ee080db2f175f044746e`.
- Corrected collector/test code commit: `8a75fc5`
  (`fix(stage2b): attribute traces by backend pid`).
- PostgreSQL source: clean HEAD
  `23c7c2fdd4bfb561f3257d947fee956a2999fdb6`; both
  `ESS_MCV_TRACE` and `ESS_MCV_NUMERIC_TRACE` markers plus the numeric
  configure flag were present.
- PostgreSQL binaries: verified PostgreSQL 16.14 from the supplied clean
  build manifest, source commit `23c7c2fdd4bfb561f3257d947fee956a2999fdb6`.
  SHA-256 values were recorded in `gate-audit.json` for `postgres`, `initdb`,
  `pg_ctl`, `psql`, and `pg_config`.
- Archive SHA-256:
  `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`.
- Runtime inputs: `ESS_DATA_ROOT=/home/wqts/ess-data`,
  `ESS_RUNTIME_PARENT=/home/wqts/ess-runtime`; each dataset used a fresh
  Issue-owned cluster and fixed sample.

Exact command, using the existing dependency-complete local interpreter:

```text
ESS_DATA_ROOT=/home/wqts/ess-data ESS_RUNTIME_PARENT=/home/wqts/ess-runtime ESS_WORKTREE_PARENT=/home/wqts/ess-worktrees PYTHONPATH=src /home/wqts/projects/ess-advisor/.venv/bin/python experiments/pess-multidataset-heldout-stage2b/gate_audit.py \
  --pg-source /home/wqts/ess-runtime/issue38/pg-src \
  --pg-prefix /home/wqts/ess-runtime/issue38/pg-prefix \
  --pg-build-manifest /home/wqts/ess-runtime/issue38/results/heldout-v1/runtime-manifest.json \
  --output experiments/pess-multidataset-heldout-stage2b/runs/gate-a-20261020-v11-r2/gate-audit.json
```

## Results

All four validation probes were independently attributed to one backend PID;
all foreign trace counts were zero in this run.

| dataset / probe | backend PID | raw numeric / MCV | associated numeric / MCV | selected OIDs | claimed indices | result |
| --- | ---: | ---: | ---: | --- | --- | --- |
| Forest10 shape control | 155155 | 1 / 1 | 1 / 1 | none | N/A | `VERIFIED` |
| Forest10 positive-MCV | 155157 | 2 / 4 | 2 / 4 | 16394 | 0, 1 | `VERIFIED` |
| Census13 shape control | 155268 | 3 / 7 | 3 / 7 | 16389, 16394 | 0, 5, 6, 7 | `VERIFIED` |
| Census13 positive-MCV | 155270 | 3 / 7 | 3 / 7 | 16389, 16394 | 0, 5, 6, 7 | `VERIFIED` |

Forest10 selected `16394` mapped to `ess2b_forest10_e12`. Census13 selected
`16389` and `16394`, mapped to `ess2b_census13_c01` and
`ess2b_census13_c56`. Positive pre-clamp numeric traces were present for both
datasets. The shape control was `NOT_APPLICABLE` for clause coverage only when
no MCV OID was selected; Census13's shape control selected MCV objects and
therefore had an applicable clause-coverage obligation.

The machine-readable result is `gate-audit.json`, SHA-256
`6db70364bd0986c9c520863b562b9d2d257271b7db615cabc028b35af788038b`.
Its overall status is **`GATE_A_READY`**, meaning only that the frozen input,
source/binary, cluster, numeric-trace, selected-OID, and OID-level
claimed-clause readiness checks passed. The next held-out outcome protocol
remains outside this run.

## Tests and limitations

Executed after the repair:

```text
PYTHONPATH=src /home/wqts/projects/ess-advisor/.venv/bin/python -m unittest discover -s experiments/pess-multidataset-heldout-stage2b -p 'test_*.py' -v
```

Result: **16 tests passed**. `git diff --check` and Python byte-compilation
also passed. The offline fixtures cover the v10-style marker mismatch,
foreign backend interleaving, disjoint same-PID probes, missing/ambiguous PID,
absent raw log, duplicate claims, mismatched claims, partial claims,
unmapped OIDs, no-selected-OID controls, and missing/nonpositive numeric
traces.

This remains validation-only evidence. It does not establish that the
prescribed admissible scheme family contains all real PostgreSQL schemes, nor
does OID-level trace coverage prove that every clause in a selected MCV
object's full clause set was claimed.
