# Gate A review-response report: archive-first v11-r3

Evidence label: **Experimentally observed — `GATE_A_READY` infrastructure
readiness.** This run does not collect or report Empty/Nominal/PESS/Joint-Robust
held-out outcomes, a PESS theorem, PostgreSQL scheme containment, latency, or a
generic maintenance-cost result.

This is the authoritative final v11 replay from committed code. The initial
v11 fail-closed parser checkpoint and the corrected pre-commit v11-r2 replay
remain preserved in their own exclusive directories; neither was overwritten.

## Contract, implementation, and provenance

Issue #56 changed only the `ess-research` audit collector and offline tests.
Commit `8a75fc5` (`fix(stage2b): attribute traces by backend pid`) now:

- captures from a bounded log offset through a post-marker quiet interval;
- requires the query-specific marker to identify exactly one backend PID;
- retains numeric and MCV raw records separately, associating marker-free MCV
  records only when their `[%p]` PID matches;
- fails closed on missing/ambiguous PID, prior-query markers, absent raw logs,
  malformed, duplicate, unmapped, or mismatched claims; and
- keeps `stat_clause_count` separate from `claimed_clause_index`.

Claimed-clause status is **OID-level claim presence only**. It does not prove
full clause-set completeness for a selected MCV object.

The run used the frozen `protocol-v3.json` (SHA-256
`f4feb957a6f1618b1d346ff4415d06a859eba2af5bf7ee080db2f175f044746e`), the
clean PostgreSQL source at
`23c7c2fdd4bfb561f3257d947fee956a2999fdb6`, and the supplied verified
PostgreSQL 16.14 binary manifest. `gate-audit.json` records the five binary
SHA-256 values, all version checks, the clean source state, and the source
trace markers. The pinned archive SHA-256 is
`5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`.

Runtime roots were `ESS_DATA_ROOT=/home/wqts/ess-data` and
`ESS_RUNTIME_PARENT=/home/wqts/ess-runtime`; each dataset used a fresh
Issue-owned cluster and fixed sample. The exact command was:

```text
ESS_DATA_ROOT=/home/wqts/ess-data ESS_RUNTIME_PARENT=/home/wqts/ess-runtime ESS_WORKTREE_PARENT=/home/wqts/ess-worktrees PYTHONPATH=src /home/wqts/projects/ess-advisor/.venv/bin/python experiments/pess-multidataset-heldout-stage2b/gate_audit.py \
  --pg-source /home/wqts/ess-runtime/issue38/pg-src \
  --pg-prefix /home/wqts/ess-runtime/issue38/pg-prefix \
  --pg-build-manifest /home/wqts/ess-runtime/issue38/results/heldout-v1/runtime-manifest.json \
  --output experiments/pess-multidataset-heldout-stage2b/runs/gate-a-20261020-v11-r3/gate-audit.json
```

## Results

| dataset / probe | backend PID | raw numeric / MCV | associated numeric / MCV | foreign numeric / MCV | selected OIDs | claimed indices | result |
| --- | ---: | ---: | ---: | ---: | --- | --- | --- |
| Forest10 shape control | 155755 | 1 / 1 | 1 / 1 | 0 / 0 | none | N/A | `VERIFIED` |
| Forest10 positive-MCV | 155760 | 2 / 4 | 2 / 4 | 0 / 0 | 16394 | 0, 1 | `VERIFIED` |
| Census13 shape control | 155866 | 3 / 7 | 3 / 7 | 0 / 0 | 16389, 16394 | 0, 5, 6, 7 | `VERIFIED` |
| Census13 positive-MCV | 155874 | 3 / 7 | 3 / 7 | 0 / 0 | 16389, 16394 | 0, 5, 6, 7 | `VERIFIED` |

Forest10 selected OID `16394` mapped to `ess2b_forest10_e12`. Census13 selected
OIDs `16389` and `16394` mapped to `ess2b_census13_c01` and
`ess2b_census13_c56`. Positive pre-clamp numeric traces were present for both
datasets. The Forest10 shape control selected no MCV OID and was therefore
`NOT_APPLICABLE` for clause coverage; both Census13 probes had selected OIDs
and passed the applicable OID-level claim check.

The machine-readable result is `gate-audit.json`, SHA-256
`62ad36316d3fb1c5f8bc792a6216301b95b5dbb5e129a9a6219098d4936fe6df`.
Its overall status is **`GATE_A_READY`**, meaning only that the frozen input,
source/binary, cluster, numeric-trace, selected-OID, and OID-level
claimed-clause readiness checks passed. The next held-out outcome protocol
remains outside this run.

## Tests and limitations

After the repair, the targeted offline suite ran with the existing
dependency-complete local interpreter:

```text
PYTHONPATH=src /home/wqts/projects/ess-advisor/.venv/bin/python -m unittest discover -s experiments/pess-multidataset-heldout-stage2b -p 'test_*.py' -v
```

Result: **16 tests passed**. `git diff --check` and Python byte-compilation
passed. Fixtures cover the v10-style marker mismatch, foreign-backend
interleaving, disjoint same-PID probes, missing/ambiguous PID, absent raw log,
duplicate and mismatched claims, partial claims, unmapped OIDs,
no-selected-OID controls, and missing/nonpositive numeric traces.

This remains validation-only evidence. It does not establish that the
prescribed admissible scheme family contains all real PostgreSQL schemes, nor
does OID-level trace coverage prove that every clause in a selected MCV
object's full clause set was claimed.
