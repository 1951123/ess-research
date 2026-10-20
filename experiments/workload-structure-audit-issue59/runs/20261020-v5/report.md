# Issue #59 workload structure and PESS/MCV matching opportunity audit

Evidence label: **Experimentally observed descriptive workload/data characterization; no PostgreSQL runtime assertion.**

## Boundary and protocol

Protocol SHA-256: `8e8d25bc9d2847936d2c45f51a3f870a8c44e632938e30db19cfe8aaf0d9063a`. The audit used only the archive-first `prepare(issue=59, dataset=...)` path, read workload/schema/table artifacts, and did not open `truth.json`, run PostgreSQL, create statistics, or run ANALYZE. Candidate universes and all eligibility rules were frozen before the audit.

Raw column co-occurrence, calibration eligibility, and strict Stage 2B pairwise eligibility are separate measures. None proves MCV payload existence, actual PostgreSQL selection, maximal-matching containment, or PESS/Nominal decision divergence.

## Dataset comparison

| Dataset | split | queries | strict eligible | calibration edge | raw >=2 edges | conflicting | >=2 maximal matchings | table rows measured/stated |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| forest10 | train | 100000 | 1358 (1.358000%) | 68150 (68.150000%) | 51611 (51.611000%) | 47333 (47.333000%) | 47333 (47.333000%) | 581012/581012 |
| forest10 | valid | 10000 | 135 (1.350000%) | 6790 (67.900000%) | 5178 (51.780000%) | 4749 (47.490000%) | 4749 (47.490000%) | 581012/581012 |
| forest10 | test | 10000 | 146 (1.460000%) | 6910 (69.100000%) | 5224 (52.240000%) | 4814 (48.140000%) | 4814 (48.140000%) | 581012/581012 |
| census13 | train | 100000 | 609 (0.609000%) | 66942 (66.942000%) | 50894 (50.894000%) | 46634 (46.634000%) | 46634 (46.634000%) | 48842/48842 |
| census13 | valid | 10000 | 58 (0.580000%) | 6676 (66.760000%) | 5065 (50.650000%) | 4627 (46.270000%) | 4627 (46.270000%) | 48842/48842 |
| census13 | test | 10000 | 52 (0.520000%) | 6715 (67.150000%) | 5058 (50.580000%) | 4611 (46.110000%) | 4611 (46.110000%) | 48842/48842 |
| dmv11 | train | 100000 | 1685 (1.685000%) | 76543 (76.543000%) | 62946 (62.946000%) | 56970 (56.970000%) | 56970 (56.970000%) | 11591877/11591877 |
| dmv11 | valid | 10000 | 164 (1.640000%) | 7646 (76.460000%) | 6250 (62.500000%) | 5650 (56.500000%) | 5650 (56.500000%) | 11591877/11591877 |
| dmv11 | test | 10000 | 151 (1.510000%) | 7661 (76.610000%) | 6297 (62.970000%) | 5706 (57.060000%) | 5706 (57.060000%) | 11591877/11591877 |
| power7 | train | 100000 | 3998 (3.998000%) | 71069 (71.069000%) | 53980 (53.980000%) | 49505 (49.505000%) | 49505 (49.505000%) | 2075259/2075259 |
| power7 | valid | 10000 | 416 (4.160000%) | 7098 (70.980000%) | 5350 (53.500000%) | 4898 (48.980000%) | 4898 (48.980000%) | 2075259/2075259 |
| power7 | test | 10000 | 403 (4.030000%) | 7069 (70.690000%) | 5369 (53.690000%) | 4941 (49.410000%) | 4941 (49.410000%) | 2075259/2075259 |

The table's row count is an independent CSV scan; the stated count comes from the pinned schema/source contract. Empty CSV cells are not asserted to be SQL NULL. Distinctness is reported per column in the dataset JSON files and is not a PostgreSQL catalog statistic.

## Stage 2B cohort impact

- **forest10**: reference cohort IDs 60, found 60; the cohort summary is shape-only and does not change membership. Missing IDs: 0.
- **census13**: reference cohort IDs 52, found 52; the cohort summary is shape-only and does not change membership. Missing IDs: 0.
- DMV11 and Power7 have no Stage 2B frozen cohort; their prospective adjacent-pair candidate policy is outcome-blind and the cohort comparison is `NOT_APPLICABLE`.

Forest10 additionally records the Stage 1A legacy IDs seen in its test workload and their strict-eligibility overlap. Exclusion is reported as a historical filter; no Stage 1A test truth or estimate is read.

## Fingerprint overlap and physical cross-reference

Canonical ordered-predicate, source-SQL-text, and normalized-template fingerprint overlap is reported per dataset with group and record percentages in the dataset JSON files. The source-SQL-text metric hashes stripped source SQL bytes; it is not the canonical predicate fingerprint. Shared groups across splits mean query IDs cannot be treated as group-independent evidence.

For Forest10/Census13, the optional historical cross-reference contains only already observed PR #58 validation ledger fields (requested resources, catalog MCV payload presence, and trace-selected resources). It is not used to construct candidates or eligibility. DMV11/Power7 physical payload and trace status is **NOT MEASURED**.

## Interpretation

This audit establishes descriptive structural opportunity under the frozen candidate graphs. Multiple maximal matchings are a graph property of the prescribed candidate universe; they do not establish that a fixed PostgreSQL catalog realizes all of them, that PESS and Nominal differ on held-out estimates, or that either policy is physically beneficial. The DMV11/Power7 adjacent-pair universe is a bounded prospective structural policy, not an exhaustive pairwise universe.

Representative operator/column shapes are stored without literal values in the per-dataset summaries. No raw SQL, table rows, truth values, estimates, or large derived artifacts are committed.

Decision type: **descriptive feasibility assessment only**. Any future prospective nontrivial PESS-versus-Nominal study requires its own outcome-free protocol and independent held-out design; this report does not amend Stage 2B protocol-v4.
