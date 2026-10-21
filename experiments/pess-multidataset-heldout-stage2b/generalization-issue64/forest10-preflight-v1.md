# Forest10 first-milestone preflight (outcome-free)

Status: **implementation checks passed; actual Forest10 resource decisions and PostgreSQL execution remain NOT RUN**. This preflight did not open the AreCEL archive, truth files, test estimates, or any held-out outcome, and did not run PostgreSQL, `EXPLAIN`, or `ANALYZE`.

## Workload and exact-search counts

Source: the already-published Issue #67 / merged PR #68 workload-only report, pinned in `forest10-first-implementation-v1.json`. Its 45 Forest10 candidate support counts sum to **164,088 eligible query-candidate pairs**. Applying the approved rule gives:

- Calibration: 10,000 Empty plans + 164,088 eligible singleton plans = **174,088 EXPLAIN plans**.
- Test evaluation: at most 10,000 queries × 5 distinct sets (Empty plus up to four Nominal/PESS selections for B=2 and B=3) = **50,000 plans**.
- Combined upper bound: **224,088 plan attempts**. This is a count, not a time or storage estimate.
- Feasible resource subsets: B=0 **1**, B=2 **1,036**, B=3 **15,226**. Complete scoring through B=3 evaluates at most 15,226 sets × 10,000 valid task models × 2 methods = **304,520,000 task-set objective evaluations** (the B=0 and B=2 results are read from the same nested complete enumeration).

The exact enumerator is implemented using combinations up to the cardinality bound and `Fraction` objective arithmetic. Synthetic tests check subset counts, all maximal matchings for a small conflict graph, method-specific loss, exact ties, and deterministic tie selection. At B=0, both methods necessarily select Empty because it is the only feasible set; its model objective is not computed. **No B=2 or B=3 Forest10 selection can yet be reported:** the full-split Empty/singleton Plan Rows needed to construct the 10,000 valid-query model inputs have not been measured, and this phase expressly prohibits calibration `EXPLAIN`.

## Local environment snapshot

Observed in the assigned Issue #64 Worktree on 2026-10-21:

- Python: 3.12.3; available CPU workers: 8.
- Available space at configured `ESS_RUNTIME_PARENT`: 18,810,880,000 bytes (filesystem total 52,518,420,480 bytes).
- `ESS_DATA_ROOT/arecel-data.tar.gz`: present, 118,265,504 bytes by metadata only; archive contents were not read.
- This Worktree has no `.venv/`; this implementation and its tests use only the Python standard library, so no package installation was needed.
- `pg_config` and `psql` are not on `PATH`. The intended PostgreSQL build, binary hashes/version, runtime settings, sample identity, and actual run cap therefore remain **NOT VERIFIED**.
- Runtime and disposable-storage needs for 174,088 calibration plans plus up to 50,000 evaluation plans are **NOT MEASURED / NOT VERIFIED**. Available filesystem space alone does not establish that the experiment fits.

## Boundary and next gate

The approved code implements exact selection and a pure JSON Plan Rows/Q1 adapter; tests use synthetic fixtures only. It does not load official valid/test splits or truth and does not invoke a PG runner. Actual resource selection remains pending the separately authorized valid-split calibration, because substituting historical held-out data or inventing coefficients would not answer the approved model-selection question. Test split access/measurement remains blocked until protocol/source/selection freeze and separate researcher approval. No result here supports a Nominal/PESS performance comparison.
