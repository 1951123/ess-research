# Issue #105 — OID creation-order reversal protocol v1

**State:** frozen preflight protocol; official AreCEL Test execution is not yet authorized. No Test workload or Test labels were accessed for this protocol.

## Minimum experiment

The minimum question is whether reversing the catalog OID order of the four already-frozen Nominal B=5 two-column MCV resource sets changes PostgreSQL 16.14 Plan Rows and Q-error on the same official Test queries. Reuse the Issue #99 frozen selections and samples, the Issue #101 table/query/metric path, and retain the actual candidate-to-OID mapping plus query-level estimates, truths, and statuses needed to recompute the paired summaries.

## Source-derived mechanism

**Evidence label: Source-derived (conditional on the pinned PostgreSQL source and the query clauses satisfying the source's MCV eligibility checks).** The source pin is PostgreSQL 16.14 commit [`f1bf37b5dd3d3a7087fc0af5de550ca31035854c`](https://github.com/1951123/ess-postgresql/commit/f1bf37b5dd3d3a7087fc0af5de550ca31035854c).

1. `RelationGetStatExtList` sorts the relation's extended-statistics OIDs in ascending OID order (`src/backend/utils/cache/relcache.c`, lines 4877–4938; the explicit sort is at 4924–4925).
2. `get_relation_statistics` walks that returned list and appends the corresponding `StatisticExtInfo` entries without an intervening sort (`src/backend/optimizer/util/plancat.c`, lines 1446–1458 and the rest of that loop).
3. `choose_best_statistics` iterates the planner list. It first maximizes distinct matched attributes/expressions among still-unestimated compatible clauses, then minimizes the total number of keys. Its comparisons are strict, so an exact tie retains the first matching list entry (`src/backend/statistics/extended_stats.c`, lines 1263–1360, especially 1291 and 1351–1356).

Thus CREATE statement order, catalog OID order, and planner consideration order are separate observations. The intervention requests a CREATE order; each arm must query `pg_statistic_ext` and verify the actual OID order before any Test EXPLAINs. The source then predicts that the planner considers these objects in ascending OID order. The tiny fixture below checks the actual CREATE → OID → selected-OID chain with the narrow `ESS_MCV_TRACE` diagnostic. No claim is made that every query has a tied pair or that every query's estimate changes.

For the planned B=5 sets, every statistic is two-column MCV. On a query with three eligible predicates spanning a shared endpoint, two applicable pair statistics can each cover two distinct predicate attributes and have the same two-key width. Only when these source criteria tie can their relative planner-list order decide which one is selected first.

## Frozen official comparison

Use exactly the four Issue #99 frozen **Nominal, B=5** sets below. Canonical order is ascending candidate ID; reverse order is its exact reversal. The candidate-map digest was checked against the frozen Issue #99 manifest. No reselection, new budget, PESS arm, or additional permutation is in scope.

| Dataset | Candidate IDs in canonical CREATE order | Exact reverse CREATE order | Frozen candidate-map SHA-256 |
|---|---|---|---|
| Forest10 | `e01_06, e02_07, e02_08, e03_04, e06_08` | `e06_08, e03_04, e02_08, e02_07, e01_06` | `8fd28b72e4b071dc2ca491502bb61b4652fe9b68269f1db2eef1f6f1f7ffc76b` |
| Census13 | `e01_05, e02_03, e04_06, e04_08, e06_08` | `e06_08, e04_08, e04_06, e02_03, e01_05` | `c661e07db8be24050417014bb5e280dd6cc1d856b26700075638a175e0dc8c64` |
| DMV11 | `e00_05, e01_04, e01_07, e02_03, e04_07` | `e04_07, e02_03, e01_07, e01_04, e00_05` | `8feab245abc557251d7446ff25d25ead1f43bdf0f39fbc591b19228a8e9d0f5d` |
| Power7 | `e00_01, e00_03, e01_02, e02_04, e03_06` | `e03_06, e02_04, e01_02, e00_03, e00_01` | `0c17d1bced2f1ed9b48cb6867982b0938d180c996b3617cb36383d1851c8dfb4` |

The frozen candidate maps (ID → columns) are: Forest10 `e01_06=(Aspect,Hillshade_9am)`, `e02_07=(Slope,Hillshade_Noon)`, `e02_08=(Slope,Hillshade_3pm)`, `e03_04=(Horizontal_Distance_To_Hydrology,Vertical_Distance_To_Hydrology)`, `e06_08=(Hillshade_9am,Hillshade_3pm)`; Census13 `e01_05=(workclass,occupation)`, `e02_03=(education,education_num)`, `e04_06=(marital_status,relationship)`, `e04_08=(marital_status,sex)`, `e06_08=(relationship,sex)`; DMV11 `e00_05=(Record_Type,Fuel_Type)`, `e01_04=(Registration_Class,Body_Type)`, `e01_07=(Registration_Class,Color)`, `e02_03=(State,County)`, `e04_07=(Body_Type,Color)`; Power7 `e00_01=(Global_active_power,Global_reactive_power)`, `e00_03=(Global_active_power,Global_intensity)`, `e01_02=(Global_reactive_power,Voltage)`, `e02_04=(Voltage,Sub_metering_1)`, `e03_06=(Global_intensity,Sub_metering_3)`. The official check must also verify that each catalog object's columns match this frozen mapping.

For each dataset, use the Issue #101 pinned full source table, exact Issue #99 fixed ANALYZE sample, column-statistics target 300, extended-statistics target 300, PostgreSQL build/settings, official 10,000-query Test split, query conversion, and Q-error implementation. Reuse its six read-only planner clients per fixed configuration and its disk early-stop (`20,401,094,656` bytes) and hard cap (`21,474,836,480` bytes); the Issue #101 protocol has no wall-time limit. Run two configurations per dataset (four datasets × two orders = eight configurations; 80,000 EXPLAIN calls maximum), with no retries or outcome-based filtering.

Within each dataset's one run-local cluster, prepare each arm from the same table and frozen sample: drop the previous five B=5 objects, create the five named objects in that arm's explicit sequence, replay the same fixed sample and ANALYZE using the Issue #101 path, then verify the five catalog names/OIDs in `ORDER BY oid`. If the observed catalog sequence does not match the requested candidate-ID sequence, mark the arm invalid and stop that dataset before Test EXPLAINs. Execute the frozen Test qids only after both arms' order checks pass. Do not reuse a prepared plan across arms.

The eight configurations are paired by `(dataset, query_id)`. Report per dataset and arm: P50, P95, P99, maximum, mean, valid count, and unresolved statuses. Also report reverse-minus-canonical P95, the P95 ratio, and per-query lower/higher/tie Q-error counts. Preserve compact query-level `dataset, order, query_id, source_index, Plan Rows, truth, status` records so all summaries can be recomputed. Keep Issue #101's Q-error and rounding code unchanged. Claims will be limited to this fixed PostgreSQL build, workload, four resource sets, and these two OID orders.

## Outcome-blind synthetic preflight

`oid-order-smoke.sql` is a tiny non-AreCEL fixture. It creates a 3-column table where `a=b`, while `c` varies independently over the four `(b,c)` combinations. It builds `ab` and `bc` MCV statistics at target 300. Both objects cover two of the three equality predicates in the same query and have equal key width, while their MCV lists differ. The script runs the identical EXPLAIN after forward and reverse CREATE order, printing (a) statement order, (b) actual catalog names/OIDs and MCV summaries, and (c) `ESS_MCV_TRACE` selected OIDs. The success criterion is that actual catalog OID order follows the requested order in each phase and that the selected statistic follows that reversed tie order. This preflight does not touch AreCEL data or held-out results.

## Execution boundary and provenance

- This protocol reuses Issue #101 protocol/runner code from repository commit `3cec433cf2ac54cb5980ae96de9efcc32617c54b` (protocol SHA-256 `7bd11b3743c5ca0467b4268cf47e8328f2bbe500fd53cea45a8efe3eab415787`; runner SHA-256 `894b8276f58d36d7d513138e574a9832aa03b8e8a21f3dd84494dbc0367b9244`) and Issue #99 frozen train manifest `experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json` (SHA-256 `2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca`).
- The only execution in this task is the tiny synthetic preflight against a fresh Issue #105-owned build of the pinned PostgreSQL commit. The official eight-configuration Test comparison remains pending separate researcher authorization after review of this frozen protocol.
- Repository `docs/STATUS.md` was read as mandatory context and contains a high-level Issue #101 outcome summary. The detailed Issue #101 findings and raw Test observations were not opened or used to select the Issue #105 resources, order pair, metrics, or claims.
- No PostgreSQL source patch, new workload, data generator, general-purpose runner, or persistent copy of AreCEL data is added.
