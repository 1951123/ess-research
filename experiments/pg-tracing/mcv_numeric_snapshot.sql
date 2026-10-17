\set ON_ERROR_STOP on
\pset pager off

SET client_min_messages = debug1;
SET default_statistics_target = 100;

DROP TABLE IF EXISTS ess_mcv_numeric_t;
CREATE TABLE ess_mcv_numeric_t (a int, b int, c int, d int);

-- All four columns are identical, giving strong pairwise correlations while
-- keeping the data-generation and truth cardinalities deterministic.
INSERT INTO ess_mcv_numeric_t
SELECT (g % 10)::int, (g % 10)::int, (g % 10)::int, (g % 10)::int
FROM generate_series(1, 100000) AS g;

ALTER TABLE ess_mcv_numeric_t ALTER COLUMN a SET STATISTICS 100;
ALTER TABLE ess_mcv_numeric_t ALTER COLUMN b SET STATISTICS 100;
ALTER TABLE ess_mcv_numeric_t ALTER COLUMN c SET STATISTICS 100;
ALTER TABLE ess_mcv_numeric_t ALTER COLUMN d SET STATISTICS 100;

CREATE STATISTICS ess_num_ab (mcv) ON a, b FROM ess_mcv_numeric_t;
CREATE STATISTICS ess_num_bc (mcv) ON b, c FROM ess_mcv_numeric_t;
CREATE STATISTICS ess_num_cd (mcv) ON c, d FROM ess_mcv_numeric_t;
ALTER STATISTICS ess_num_ab SET STATISTICS 100;
ALTER STATISTICS ess_num_bc SET STATISTICS 100;
ALTER STATISTICS ess_num_cd SET STATISTICS 100;

-- This is the only ANALYZE in the fixture.  All later availability scenarios
-- use transactional DROP STATISTICS followed by ROLLBACK.
ANALYZE ess_mcv_numeric_t;

\echo '=== snapshot:settings-and-catalog ==='
SHOW server_version;
SHOW default_statistics_target;
SELECT 'table' AS object,
       'ess_mcv_numeric_t'::regclass::oid AS relation_oid,
       c.reltuples,
       c.relpages,
       count(*) AS actual_rows,
       min(a) AS min_a,
       max(a) AS max_a
FROM ess_mcv_numeric_t t
JOIN pg_class c ON c.oid = 'ess_mcv_numeric_t'::regclass
GROUP BY c.reltuples, c.relpages;

SELECT e.stxname,
       e.oid AS statistic_oid,
       e.stxkeys,
       e.stxkind,
       e.stxstattarget,
       d.stxdmcv IS NOT NULL AS built_mcv,
       pg_column_size(d.stxdmcv) AS mcv_bytes
FROM pg_statistic_ext e
LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid
WHERE e.stxrelid = 'ess_mcv_numeric_t'::regclass
ORDER BY e.stxname;

SELECT 'ordinary_stats_fingerprint' AS key,
       md5(string_agg(
           format('%s|%s|%s|%s|%s|%s|%s',
                  staattnum,
                  stanullfrac,
                  stawidth,
                  stadistinct,
                  coalesce(stavalues1::text, ''),
                  coalesce(stanumbers1::text, ''),
                  coalesce(stakind1::text, '')),
           ',' ORDER BY staattnum)) AS fingerprint
FROM pg_statistic
WHERE starelid = 'ess_mcv_numeric_t'::regclass;

\echo '=== measurement:single_a ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:single_a */
SELECT * FROM ess_mcv_numeric_t WHERE a = 3;
\echo '=== measurement:single_b ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:single_b */
SELECT * FROM ess_mcv_numeric_t WHERE b = 3;
\echo '=== measurement:single_c ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:single_c */
SELECT * FROM ess_mcv_numeric_t WHERE c = 3;
\echo '=== measurement:single_d ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:single_d */
SELECT * FROM ess_mcv_numeric_t WHERE d = 3;

\echo '=== measurement:pair_ab ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:pair_ab */
SELECT * FROM ess_mcv_numeric_t WHERE a = 3 AND b = 3;
\echo '=== measurement:pair_bc ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:pair_bc */
SELECT * FROM ess_mcv_numeric_t WHERE b = 3 AND c = 3;
\echo '=== measurement:pair_cd ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:pair_cd */
SELECT * FROM ess_mcv_numeric_t WHERE c = 3 AND d = 3;

\echo '=== measurement:full_all ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:full_all */
SELECT * FROM ess_mcv_numeric_t
WHERE a = 3 AND b = 3 AND c = 3 AND d = 3;

\echo '=== measurement:single_a_rare ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:single_a_rare */
SELECT * FROM ess_mcv_numeric_t WHERE a = 1000000;
\echo '=== measurement:pair_ab_rare ==='
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:pair_ab_rare */
SELECT * FROM ess_mcv_numeric_t WHERE a = 1000000 AND b = 1000000;

\echo '=== scenario:only_bc ==='
BEGIN;
DROP STATISTICS ess_num_ab, ess_num_cd;
SELECT 'only_bc_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext
WHERE stxrelid = 'ess_mcv_numeric_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:full_only_bc */
SELECT * FROM ess_mcv_numeric_t
WHERE a = 3 AND b = 3 AND c = 3 AND d = 3;
ROLLBACK;
DISCARD PLANS;

\echo '=== scenario:only_ab ==='
BEGIN;
DROP STATISTICS ess_num_bc, ess_num_cd;
SELECT 'only_ab_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext
WHERE stxrelid = 'ess_mcv_numeric_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:full_only_ab */
SELECT * FROM ess_mcv_numeric_t
WHERE a = 3 AND b = 3 AND c = 3 AND d = 3;
ROLLBACK;
DISCARD PLANS;

\echo '=== scenario:only_cd ==='
BEGIN;
DROP STATISTICS ess_num_ab, ess_num_bc;
SELECT 'only_cd_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext
WHERE stxrelid = 'ess_mcv_numeric_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:full_only_cd */
SELECT * FROM ess_mcv_numeric_t
WHERE a = 3 AND b = 3 AND c = 3 AND d = 3;
ROLLBACK;
DISCARD PLANS;

\echo '=== scenario:none ==='
BEGIN;
DROP STATISTICS ess_num_ab, ess_num_bc, ess_num_cd;
SELECT 'none_catalog_count' AS marker, count(*) AS visible_statistics
FROM pg_statistic_ext
WHERE stxrelid = 'ess_mcv_numeric_t'::regclass;
EXPLAIN (SUMMARY OFF) /* ESS_MCV_NUMERIC_TRACE:full_none */
SELECT * FROM ess_mcv_numeric_t
WHERE a = 3 AND b = 3 AND c = 3 AND d = 3;
ROLLBACK;
DISCARD PLANS;

\echo '=== snapshot:after-all-rollbacks ==='
SELECT e.stxname,
       e.oid AS statistic_oid,
       e.stxkeys,
       e.stxkind,
       e.stxstattarget,
       d.stxdmcv IS NOT NULL AS built_mcv,
       pg_column_size(d.stxdmcv) AS mcv_bytes
FROM pg_statistic_ext e
LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid
WHERE e.stxrelid = 'ess_mcv_numeric_t'::regclass
ORDER BY e.stxname;

SELECT 'ordinary_stats_fingerprint_after_rollbacks' AS key,
       md5(string_agg(
           format('%s|%s|%s|%s|%s|%s|%s',
                  staattnum,
                  stanullfrac,
                  stawidth,
                  stadistinct,
                  coalesce(stavalues1::text, ''),
                  coalesce(stanumbers1::text, ''),
                  coalesce(stakind1::text, '')),
           ',' ORDER BY staattnum)) AS fingerprint
FROM pg_statistic
WHERE starelid = 'ess_mcv_numeric_t'::regclass;

\echo '=== numeric snapshot fixture complete ==='
