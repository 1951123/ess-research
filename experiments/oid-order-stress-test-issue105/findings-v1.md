# Issue #105 — source review and synthetic OID-order preflight

## Outcome

**Evidence labels:** source-derived (conditional) and experimentally observed in one synthetic PostgreSQL fixture.

The pinned PostgreSQL control flow confirms the suspected tie behavior. `RelationGetStatExtList` sorts extended-statistics OIDs ascending; `get_relation_statistics` builds the planner list in that order; `choose_best_statistics` maximizes covered remaining attributes/expressions, then minimizes key count, and preserves the first list entry on a tie. This is not a claim about every query: OID order matters only when multiple eligible MCV objects tie on both selection criteria.

The isolated fixture exhibited the predicted CREATE order → catalog OID order → planner selection chain:

| Phase | CREATE statements | `pg_statistic_ext` ordered by OID | `ESS_MCV_TRACE` selection | Top-level Plan Rows |
|---|---|---|---|---:|
| Forward | `issue105_ab`, then `issue105_bc` | `issue105_ab:16387`, `issue105_bc:16388` | OID `16387` (`issue105_ab`); claimed clause indices 0, 1 | 256 |
| Reverse | `issue105_bc`, then `issue105_ab` | `issue105_bc:16389`, `issue105_ab:16390` | OID `16389` (`issue105_bc`); claimed clause indices 1, 2 | 128 |

Both objects were built as MCV statistics with two keys. `issue105_ab` had two MCV items `{{0,0},{1,1}}` at frequencies `{0.5,0.5}`; `issue105_bc` had four items `{{0,0},{0,1},{1,0},{1,1}}` at frequencies `{0.25,0.25,0.25,0.25}`. The identical query had equality predicates on `a`, `b`, and `c`, so each object covered two eligible attributes and had equal key width. The selected object changed exactly with the measured OID order. Plan Rows also changed in this fixture; that observation only demonstrates that this synthetic table's estimate was sensitive to the selected MCV object.

## Source evidence

**Evidence label: Source-derived (conditional).** Reviewed the pinned commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c` in `ess-postgresql` without modifying that repository:

- [`extended_stats.c`](https://github.com/1951123/ess-postgresql/blob/f1bf37b5dd3d3a7087fc0af5de550ca31035854c/src/backend/statistics/extended_stats.c#L1263-L1360): `choose_best_statistics`; tie behavior is visible in the strict comparisons at lines 1351–1356.
- [`relcache.c`](https://github.com/1951123/ess-postgresql/blob/f1bf37b5dd3d3a7087fc0af5de550ca31035854c/src/backend/utils/cache/relcache.c#L4877-L4938): `RelationGetStatExtList`; explicit OID sort at lines 4924–4925.
- [`plancat.c`](https://github.com/1951123/ess-postgresql/blob/f1bf37b5dd3d3a7087fc0af5de550ca31035854c/src/backend/optimizer/util/plancat.c#L1446-L1458): `get_relation_statistics` walks the relcache OID list to build planner entries.
- [`extended_stats.c`](https://github.com/1951123/ess-postgresql/blob/f1bf37b5dd3d3a7087fc0af5de550ca31035854c/src/backend/statistics/extended_stats.c#L1827-L1857): MCV loop chooses from `rel->statlist` and emits `ESS_MCV_TRACE` with the selected OID.

## Experimental record

**Evidence label: Experimentally observed.** Run ID `20261025T122847Z-smoke-v1` used a fresh Issue #105-owned source checkout, build, install prefix, and cluster under `$ESS_RUNTIME_PARENT/ess-research/issue105/runs/`. The source checkout was clean at PostgreSQL commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; both `postgres` and `psql` reported PostgreSQL 16.14. Host/build environment: Linux `7.0.0-38-generic`, GCC `13.3.0`, GNU Make `4.3`.

Build commands: `configure --prefix=<run>/pg-install --without-readline --without-zlib`; `make -j2`; `make install`. The fixture command was `psql -X -v ON_ERROR_STOP=1 -h <run>/socket -p 55489 -d postgres -f experiments/oid-order-stress-test-issue105/oid-order-smoke.sql`, against a fresh `initdb --no-locale --encoding=UTF8` cluster with TCP listening disabled. `pg_ctl` reported a clean fast shutdown. The psql output containing catalog rows, MCV lists, trace lines, and both EXPLAINs is retained outside Git at `.../results/oid-order-smoke.log` (4,601 bytes; SHA-256 `3658d91f741612277371300884fb00f10c6b1fbbf2db0d0cb82299ea888d417d`). Fixture SHA-256: `b44f6e701b6a3ba3f570119306d5bb3744198144723ec7cf715cf5a8072c71cf`.

The fixture is `experiments/oid-order-stress-test-issue105/oid-order-smoke.sql`. It inserts 1,024 synthetic rows, runs the same three-predicate EXPLAIN in each phase, and drops its table. It accesses no AreCEL archive, Test workload, Test label, detailed Issue #101 findings/raw observations, or production database. The required repository `docs/STATUS.md` includes a high-level Issue #101 summary; that summary was not used to choose the Issue #105 resources, order pair, metrics, or claims. No PostgreSQL source was patched.

## Scope and limits

This is a successful mechanism preflight for the pinned source and this small fixture. It does not establish how often ties occur in AreCEL, quantify official Test Q-error sensitivity, or justify a general causal or universal claim. The frozen official comparison in [`protocol-v1.md`](protocol-v1.md) remains unrun: four Nominal B=5 sets, canonical order and exact reverse only, eight configurations and at most 80,000 official Test EXPLAINs. Separate researcher authorization is still required before that Test run.
