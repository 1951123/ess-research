# Forest10 Nominal priority-order sensitivity (exploratory)

**Evidence class:** exploratory, valid-only, model-internal; not held-out evidence. No PostgreSQL was run and no test input was read. The previously frozen Forest10 selection and test reports are unchanged.

## Question and method

Does changing Nominal's greedy candidate priority alter the exact resource optimum, and how do those Nominal optima score under the frozen PESS criterion? The analysis reuses the frozen 10,000-task corrected-log `alpha_fraction`/`b_fraction` rows and the existing `Fraction` exact selector; it does not refit coefficients. It enumerates all 1, 1,036, and 15,226 feasible sets for budgets 0, 2, and 3, respectively.

The ten priority sequences are the frozen 45-candidate order, its full reverse, and `random.Random(seed).shuffle` for seeds 0–7. They are all distinct; no collision was rerolled. The complete vectors are in the machine-readable result. Objectives, tie comparisons, and PESS losses use exact rational arithmetic.

## Findings

All ten orders have the same exact Nominal optimum and the same unique optimal **resource set** at each budget. The ordered presentation of a multi-edge representative follows the supplied priority, so the list order can differ even when the chosen set does not.

| Budget | Unique resource set under all 10 orders | Exact Nominal optimum (all orders) | Objective range | PESS worst-case loss of each Nominal optimum | Gap to frozen PESS global optimum |
|---:|---|---|---:|---|---:|
| 0 | `{}` | `23326825631265146269149/1000000000000000000` | `0` | `23326825631265146269149/1000000000000000000` | `0` |
| 2 | `{e01_06, e02_07}` | `4374828918765339127297/200000000000000000` | `0` | `4374828918765339127297/200000000000000000` | `0` |
| 3 | `{e01_06, e02_07, e03_04}` | `21512755121155336377967/1000000000000000000` | `0` | `21512755121155336377967/1000000000000000000` | `0` |

Across the ten orders there is **one distinct optimal resource set** at B=2 and one at B=3. Every representative's edges are pairwise vertex-disjoint. Consequently, each task's selected-edge subgraph for these winning sets has only one maximal matching, and its Nominal and PESS losses coincide. No Nominal-optimal set in this analysis has a higher PESS worst-case loss than the frozen PESS global optimum; there is no observed “lower Nominal score, higher PESS risk” case among the selected optima.

By definition, PESS maximizes over the complete set of maximal matchings, which is independent of a greedy priority order; therefore its objective and optimal resource-set family do not depend on Nominal's ordering. The PESS values below are the previously frozen exact results, not ten new PESS optimizations.

This does not say that the objectives coincide for every feasible set. Nominal self-objective and PESS worst-case objective are different criteria; their numerical difference must not be interpreted as a PostgreSQL accuracy or performance gain. The fixed-order exercise also does not establish that PostgreSQL realizes any of the hypothetical priorities.

## PostgreSQL 16.14 source mapping

Source-derived from `ess-postgresql` commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`:

- `src/backend/utils/cache/relcache.c`, `RelationGetStatExtList()` gathers the relation's extended-statistics OIDs and explicitly sorts the returned list by OID.
- `src/backend/optimizer/util/plancat.c`, `get_relation_statistics()` walks that list in order and appends the corresponding built statistic metadata, preserving the input order.
- `src/backend/statistics/extended_stats.c`, `choose_best_statistics()` first maximizes newly matched attributes/expressions, then prefers fewer total keys. It replaces the current best only on a strict improvement; if both criteria tie, the first item in the list remains selected.
- `src/backend/commands/statscmds.c`, `CreateStatistics()` obtains each catalog OID with `GetNewOidWithIndex()` at object creation. Creation order can therefore affect the assigned OIDs, but the resulting catalog OIDs must be queried and verified; DDL order or object names are not evidence of OID order.

Thus OID priority corresponds to the model's priority only among candidates tied on coverage and key-count criteria, after PostgreSQL's compatibility/type/inheritance filtering. The model's greedy maximal-matching abstraction is conditional and is not a complete emulator of planner behavior for arbitrary queries/catalogs.

## Future minimal dynamic validation design (not run)

If separately authorized, use two fresh isolated clusters built from the same pinned source and initialized from identical table bytes. Replay the same fixed ANALYZE sample, define the same two overlapping two-key MCV objects in opposite creation orders, and analyze only after both objects exist. Select one official **valid** query by static structure only: three distinct supported predicate attributes, both candidate objects cover exactly two still-unestimated attributes, and equal key counts. In each cluster, record the actual `pg_statistic_ext` OIDs, keys/kind/target and the structured MCV selected-OID/clause-index diagnostics for the same query. Require the observed OID order to be reversed before interpreting the comparison. Missing/invalid MCV payload or absent selection means the dynamic tie case was not exercised; do not replace the query based on test outcomes. This design has not been executed and is not PostgreSQL evidence.

## Reproducibility

- Analysis: `forest10_nominal_order_sensitivity.py`
- Synthetic tests: `test_forest10_nominal_order_sensitivity.py`
- Machine-readable full permutations, all exact minimizers, per-minimizer PESS losses, source/candidate metadata and SHA-256 inputs: `forest10-nominal-order-sensitivity-v1.json`
- Frozen input identities: selection JSON SHA-256 `10bcf1f6026aa4de025cbef360c8302aafb2f082d49138c4c5da2d1331f4c798`; coefficient gzip SHA-256 `b1f0e6521804cc0e77f0616271d94b10a3602bde6eb677591ee040e14c7dbd04`.
- Run command: `.venv/bin/python experiments/pess-multidataset-heldout-stage2b/generalization-issue64/forest10_nominal_order_sensitivity.py --output experiments/pess-multidataset-heldout-stage2b/generalization-issue64/forest10-nominal-order-sensitivity-v1.json`.
