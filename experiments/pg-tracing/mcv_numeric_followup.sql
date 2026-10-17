\set ON_ERROR_STOP on
\pset pager off

SET client_min_messages = debug1;
SET default_statistics_target = 10;

-- This script contains two independent fixtures.  Each fixture has one
-- ANALYZE snapshot, and all availability variants are obtained by
-- transactional DROP STATISTICS + ROLLBACK.  The fixtures deliberately use
-- different tables so factors are never combined across snapshots.

\echo '=== fixture:partial ==='
DROP TABLE IF EXISTS ess_mcv_partial_t;
CREATE TABLE ess_mcv_partial_t (a int, b int, c int, d int);

-- The diagonal pairs are frequent but the ten-entry MCV list covers only a
-- strict subset of the relation.  The second branch supplies positive,
-- non-MCV pair mass for the remainder check.
INSERT INTO ess_mcv_partial_t
SELECT (g % 20)::int AS a,
       CASE WHEN (g % 5) < 4 THEN (g % 20)::int
            ELSE ((g / 5) % 20)::int END AS b,
       (g % 20)::int AS c,
       (g % 20)::int AS d
FROM generate_series(1, 100000) AS g;
ALTER TABLE ess_mcv_partial_t ALTER COLUMN a SET STATISTICS 10;
ALTER TABLE ess_mcv_partial_t ALTER COLUMN b SET STATISTICS 10;
ALTER TABLE ess_mcv_partial_t ALTER COLUMN c SET STATISTICS 10;
ALTER TABLE ess_mcv_partial_t ALTER COLUMN d SET STATISTICS 10;
CREATE STATISTICS ess_partial_ab (mcv) ON a, b FROM ess_mcv_partial_t;
CREATE STATISTICS ess_partial_bc (mcv) ON b, c FROM ess_mcv_partial_t;
CREATE STATISTICS ess_partial_cd (mcv) ON c, d FROM ess_mcv_partial_t;
ALTER STATISTICS ess_partial_ab SET STATISTICS 10;
ALTER STATISTICS ess_partial_bc SET STATISTICS 10;
ALTER STATISTICS ess_partial_cd SET STATISTICS 10;
ANALYZE ess_mcv_partial_t;

\echo '=== partial:snapshot ==='
SELECT 'partial_table' AS object,
       'ess_mcv_partial_t'::regclass::oid AS relation_oid,
       c.reltuples,
       count(*) AS actual_rows
FROM ess_mcv_partial_t t
JOIN pg_class c ON c.oid = 'ess_mcv_partial_t'::regclass
GROUP BY c.reltuples;
SELECT e.stxname, e.oid AS statistic_oid, e.stxkeys, e.stxkind,
       e.stxstattarget, d.stxdmcv IS NOT NULL AS built_mcv,
       pg_column_size(d.stxdmcv) AS mcv_bytes
FROM pg_statistic_ext e
LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid
WHERE e.stxrelid = 'ess_mcv_partial_t'::regclass
ORDER BY e.stxname;

\echo '=== partial:single_a ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_single_a */
SELECT * FROM ess_mcv_partial_t WHERE a = 3;
\echo '=== partial:single_b ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_single_b */
SELECT * FROM ess_mcv_partial_t WHERE b = 3;
\echo '=== partial:single_c ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_single_c */
SELECT * FROM ess_mcv_partial_t WHERE c = 3;
\echo '=== partial:single_d ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_single_d */
SELECT * FROM ess_mcv_partial_t WHERE d = 3;
\echo '=== partial:pair_ab_mcv ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_pair_ab_mcv */
SELECT * FROM ess_mcv_partial_t WHERE a = 3 AND b = 3;
\echo '=== partial:pair_ab_nonmcv ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_pair_ab_nonmcv */
SELECT * FROM ess_mcv_partial_t WHERE a = 4 AND b = 0;
\echo '=== partial:pair_bc ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_pair_bc */
SELECT * FROM ess_mcv_partial_t WHERE b = 3 AND c = 3;
\echo '=== partial:pair_cd ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_pair_cd */
SELECT * FROM ess_mcv_partial_t WHERE c = 3 AND d = 3;
\echo '=== partial:full_all ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_full_all */
SELECT * FROM ess_mcv_partial_t
WHERE a = 3 AND b = 3 AND c = 3 AND d = 3;

\echo '=== partial:scenario_only_bc ==='
BEGIN;
DROP STATISTICS ess_partial_ab, ess_partial_cd;
SELECT 'partial_only_bc_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext WHERE stxrelid = 'ess_mcv_partial_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_full_only_bc */
SELECT * FROM ess_mcv_partial_t
WHERE a = 3 AND b = 3 AND c = 3 AND d = 3;
ROLLBACK;
DISCARD PLANS;

\echo '=== partial:scenario_only_ab ==='
BEGIN;
DROP STATISTICS ess_partial_bc, ess_partial_cd;
SELECT 'partial_only_ab_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext WHERE stxrelid = 'ess_mcv_partial_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_full_only_ab */
SELECT * FROM ess_mcv_partial_t
WHERE a = 3 AND b = 3 AND c = 3 AND d = 3;
ROLLBACK;
DISCARD PLANS;

\echo '=== partial:scenario_only_cd ==='
BEGIN;
DROP STATISTICS ess_partial_ab, ess_partial_bc;
SELECT 'partial_only_cd_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext WHERE stxrelid = 'ess_mcv_partial_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_full_only_cd */
SELECT * FROM ess_mcv_partial_t
WHERE a = 3 AND b = 3 AND c = 3 AND d = 3;
ROLLBACK;
DISCARD PLANS;

\echo '=== partial:scenario_none ==='
BEGIN;
DROP STATISTICS ess_partial_ab, ess_partial_bc, ess_partial_cd;
SELECT 'partial_none_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext WHERE stxrelid = 'ess_mcv_partial_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:partial_full_none */
SELECT * FROM ess_mcv_partial_t
WHERE a = 3 AND b = 3 AND c = 3 AND d = 3;
ROLLBACK;
DISCARD PLANS;

\echo '=== fixture:heterogeneous ==='
DROP TABLE IF EXISTS ess_mcv_heterogeneous_t;
CREATE TABLE ess_mcv_heterogeneous_t (a int, b int, c int, d int);

-- The first 420 rows of each 1000-row block contain the common all-zero
-- tuple and four marginally different zero-valued groups.  The remaining
-- rows avoid zero, so the three pair corrections for (0,0), (0,0), (0,0)
-- are driven by different singleton marginals.
INSERT INTO ess_mcv_heterogeneous_t
SELECT CASE
         WHEN r < 40 THEN 0
         WHEN r < 200 THEN 0
         WHEN r < 260 THEN 5
         WHEN r < 270 THEN 8
         WHEN r < 420 THEN 11
         ELSE 1 + ((r + 3) % 19)
       END AS a,
       CASE
         WHEN r < 40 THEN 0
         WHEN r < 200 THEN 2
         WHEN r < 260 THEN 0
         WHEN r < 270 THEN 9
         WHEN r < 420 THEN 12
         ELSE 1 + ((r + 7) % 19)
       END AS b,
       CASE
         WHEN r < 40 THEN 0
         WHEN r < 200 THEN 3
         WHEN r < 260 THEN 6
         WHEN r < 270 THEN 0
         WHEN r < 420 THEN 13
         ELSE 1 + ((r + 11) % 19)
       END AS c,
       CASE
         WHEN r < 40 THEN 0
         WHEN r < 200 THEN 4
         WHEN r < 260 THEN 7
         WHEN r < 270 THEN 10
         WHEN r < 420 THEN 0
         ELSE 1 + ((r + 17) % 19)
       END AS d
FROM (SELECT g, g % 1000 AS r FROM generate_series(1, 100000) AS g) AS s;
ALTER TABLE ess_mcv_heterogeneous_t ALTER COLUMN a SET STATISTICS 10;
ALTER TABLE ess_mcv_heterogeneous_t ALTER COLUMN b SET STATISTICS 10;
ALTER TABLE ess_mcv_heterogeneous_t ALTER COLUMN c SET STATISTICS 10;
ALTER TABLE ess_mcv_heterogeneous_t ALTER COLUMN d SET STATISTICS 10;
CREATE STATISTICS ess_hetero_ab (mcv) ON a, b FROM ess_mcv_heterogeneous_t;
CREATE STATISTICS ess_hetero_bc (mcv) ON b, c FROM ess_mcv_heterogeneous_t;
CREATE STATISTICS ess_hetero_cd (mcv) ON c, d FROM ess_mcv_heterogeneous_t;
ALTER STATISTICS ess_hetero_ab SET STATISTICS 10;
ALTER STATISTICS ess_hetero_bc SET STATISTICS 10;
ALTER STATISTICS ess_hetero_cd SET STATISTICS 10;
ANALYZE ess_mcv_heterogeneous_t;

\echo '=== heterogeneous:snapshot ==='
SELECT 'heterogeneous_table' AS object,
       'ess_mcv_heterogeneous_t'::regclass::oid AS relation_oid,
       c.reltuples,
       count(*) AS actual_rows
FROM ess_mcv_heterogeneous_t t
JOIN pg_class c ON c.oid = 'ess_mcv_heterogeneous_t'::regclass
GROUP BY c.reltuples;
SELECT e.stxname, e.oid AS statistic_oid, e.stxkeys, e.stxkind,
       e.stxstattarget, d.stxdmcv IS NOT NULL AS built_mcv,
       pg_column_size(d.stxdmcv) AS mcv_bytes
FROM pg_statistic_ext e
LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid
WHERE e.stxrelid = 'ess_mcv_heterogeneous_t'::regclass
ORDER BY e.stxname;

\echo '=== heterogeneous:single_a ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_single_a */
SELECT * FROM ess_mcv_heterogeneous_t WHERE a = 0;
\echo '=== heterogeneous:single_b ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_single_b */
SELECT * FROM ess_mcv_heterogeneous_t WHERE b = 0;
\echo '=== heterogeneous:single_c ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_single_c */
SELECT * FROM ess_mcv_heterogeneous_t WHERE c = 0;
\echo '=== heterogeneous:single_d ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_single_d */
SELECT * FROM ess_mcv_heterogeneous_t WHERE d = 0;
\echo '=== heterogeneous:pair_ab ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_pair_ab */
SELECT * FROM ess_mcv_heterogeneous_t WHERE a = 0 AND b = 0;
\echo '=== heterogeneous:pair_bc ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_pair_bc */
SELECT * FROM ess_mcv_heterogeneous_t WHERE b = 0 AND c = 0;
\echo '=== heterogeneous:pair_cd ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_pair_cd */
SELECT * FROM ess_mcv_heterogeneous_t WHERE c = 0 AND d = 0;
\echo '=== heterogeneous:full_all ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_full_all */
SELECT * FROM ess_mcv_heterogeneous_t
WHERE a = 0 AND b = 0 AND c = 0 AND d = 0;

\echo '=== heterogeneous:scenario_only_bc ==='
BEGIN;
DROP STATISTICS ess_hetero_ab, ess_hetero_cd;
SELECT 'hetero_only_bc_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext WHERE stxrelid = 'ess_mcv_heterogeneous_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_full_only_bc */
SELECT * FROM ess_mcv_heterogeneous_t
WHERE a = 0 AND b = 0 AND c = 0 AND d = 0;
ROLLBACK;
DISCARD PLANS;

\echo '=== heterogeneous:scenario_only_ab ==='
BEGIN;
DROP STATISTICS ess_hetero_bc, ess_hetero_cd;
SELECT 'hetero_only_ab_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext WHERE stxrelid = 'ess_mcv_heterogeneous_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_full_only_ab */
SELECT * FROM ess_mcv_heterogeneous_t
WHERE a = 0 AND b = 0 AND c = 0 AND d = 0;
ROLLBACK;
DISCARD PLANS;

\echo '=== heterogeneous:scenario_only_cd ==='
BEGIN;
DROP STATISTICS ess_hetero_ab, ess_hetero_bc;
SELECT 'hetero_only_cd_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext WHERE stxrelid = 'ess_mcv_heterogeneous_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_full_only_cd */
SELECT * FROM ess_mcv_heterogeneous_t
WHERE a = 0 AND b = 0 AND c = 0 AND d = 0;
ROLLBACK;
DISCARD PLANS;

\echo '=== heterogeneous:scenario_none ==='
BEGIN;
DROP STATISTICS ess_hetero_ab, ess_hetero_bc, ess_hetero_cd;
SELECT 'hetero_none_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext WHERE stxrelid = 'ess_mcv_heterogeneous_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:hetero_full_none */
SELECT * FROM ess_mcv_heterogeneous_t
WHERE a = 0 AND b = 0 AND c = 0 AND d = 0;
ROLLBACK;
DISCARD PLANS;

\echo '=== followup fixtures complete ==='
