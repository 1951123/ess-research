# Issue #64 scope reset — outcome-free protocol review

**Status:** `OUTCOME_FREE_DRAFT_REQUIRES_RESEARCHER_REVIEW`. This is the minimal revised design requested by the 2026-10-21 Issue update. It replaces the self-generated-cohort route for this scientific question; it does not alter or delete the earlier protocols, v7 identity ledger, or blocked cohort-feasibility evidence.

**Minimum experiment:** use all official AreCEL valid queries to select one Empty/Nominal/PESS resource set per dataset/budget, then all official test queries to compare their PostgreSQL Plan Rows using Q1, with one pinned/replayed sample per dataset. Report the official-split result as benchmark generalization, not unseen-template generalization.

## Outcome-free assessment

The source-level interfaces carry stable source indices, query IDs, SQL text, and split names. `run_formal.py`'s `load_workload()` and `verify_protocol_records()` can map arbitrary full-split query records by ID and SQL hash; its model functions can consume a list of calibration tasks and preserve per-dataset candidates/budgets. Thus identity and model mapping are reusable without constructing a new workload or generator. This is a source-derived interface assessment only; no official workload pickle was deserialized and no test labels were read.

The current path is not execution-ready without a small adapter:

1. AreCEL `archive.prepare()` currently deserializes the workload and one all-split label pickle, then writes train/valid/test truth files together. The label pickle itself contains every split, so merely suppressing `test/truth.json` is not enough to prove a valid-only firewall. Before selection, establish a valid-only extraction that does not expose/materialize test labels; if the pinned format cannot support that, treat it as a genuine data-format/firewall blocker. Test labels remain unavailable until the frozen selection artifact and separate researcher approval.
2. PR #58 currently selects from a small fixed calibration/test cohort, requires positive pre-clamp trace estimates, emits no Plan Rows metric value, and has an 1,800-measurement-per-dataset cap. It cannot stand in for 10,000 validation plus 10,000 test queries per dataset. Reuse only its corrected-log/model/matching functions after pin verification; add full-split iteration and the Q1 Plan Rows extractor/analysis.
3. Use the top-level `Plan Rows` for AreCEL's single-table `SELECT *` output cardinality; a focused synthetic JSON test should ensure parsing is unambiguous and rejects malformed/missing values. No per-query trace is necessary unless the claim concerns which statistic PostgreSQL selected.
4. At one observation per query/treatment, the full-split upper bound is 600,000 query plans: 320,000 validation calibration plans plus at most 280,000 test plans (the shared budget-0 Empty plus two possibly distinct selected sets at each of budgets 2, 3, and 5). Per-dataset upper bounds are 140,000 / 140,000 / 180,000 / 140,000 for Forest10 / Census13 / DMV11 / Power7. This is a deterministic count, not a runtime estimate. The existing per-dataset cap of 1,800 is insufficient; an execution cap and runtime/disk allocation need researcher approval.

The test set contains previously exposed Issue #48 identities for Forest10/Census13. Keep them in the official test evaluation, identify them from frozen identity-only protocols, and report an exposed/unexposed identity stratum. Because Issue #59 documents train/valid/test template overlap, do not present the unexposed subset or the full split as an untouched confirmation or unseen-template result. Do not use prior test metrics to choose resources, queries, or parameters.

## Minimal future file plan

- In the Issue #65 branch, keep `official-arecel-protocol-v1.json` as the single authoritative outcome-free config and this short review memo. Existing cohort-generation files remain immutable historical artifacts and are not part of the new route.
- After researcher review/authorization, adapt the PR #58 runner in its owning implementation branch: outcome-blind workload loading and valid-only label access; full valid calibration; freeze selected sets; only then test-label access; full test Plan Rows; compact per-query output and Q1 analysis.
- Add focused tests for the split firewall and synthetic `EXPLAIN` node extraction. Do not create another generator, ledger, generic validation framework, per-query trace system, or copied AreCEL data.

Pins to verify before selection/execution are enumerated in `official-arecel-protocol-v1.json`. The PostgreSQL version/source/binary entries from Gate A are only candidate infrastructure pins; they do not establish this study's runtime. No outcomes, PostgreSQL, EXPLAIN, or ANALYZE were accessed/run for this review.
