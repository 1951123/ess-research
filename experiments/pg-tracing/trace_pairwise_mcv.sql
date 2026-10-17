-- Execute only on a disposable PostgreSQL development database.
-- Requires a PostgreSQL build containing ESS_MCV_TRACE instrumentation (merged into ess-postgresql/main via PR #1; not present in pristine upstream PostgreSQL).
-- DEBUG1 messages with prefix ESS_MCV_TRACE expose actual selected OIDs
-- and claimed zero-based clause indices. Do not interpret Plan Rows as a trace.
\set ON_ERROR_STOP on
SET client_min_messages = debug1;
SET default_statistics_target = 100;
DROP TABLE IF EXISTS ess_trace_t;
CREATE TABLE ess_trace_t (a int, b int, c int, d int);
INSERT INTO ess_trace_t
SELECT (g % 101), (g % 101), (g % 101), (g % 101)
FROM generate_series(1, 100000) AS g;
ALTER TABLE ess_trace_t ALTER COLUMN a SET STATISTICS 100;
ALTER TABLE ess_trace_t ALTER COLUMN b SET STATISTICS 100;
ALTER TABLE ess_trace_t ALTER COLUMN c SET STATISTICS 100;
ALTER TABLE ess_trace_t ALTER COLUMN d SET STATISTICS 100;

-- Phase A: OID order ab, bc, cd. Expected selected set: ab + cd.
\echo '=== ESS phase A: ab,bc,cd ==='
CREATE STATISTICS ess_ab (mcv) ON a, b FROM ess_trace_t;
CREATE STATISTICS ess_bc (mcv) ON b, c FROM ess_trace_t;
CREATE STATISTICS ess_cd (mcv) ON c, d FROM ess_trace_t;
ANALYZE ess_trace_t;
SELECT s.stxname, s.oid, s.stxkeys::text AS keys,
       d.stxdmcv IS NOT NULL AS built_mcv
FROM pg_statistic_ext AS s
LEFT JOIN pg_statistic_ext_data AS d ON d.stxoid = s.oid AND NOT d.stxdinherit
WHERE s.stxrelid = 'ess_trace_t'::regclass
ORDER BY s.oid;
EXPLAIN (COSTS OFF)
SELECT * FROM ess_trace_t WHERE a = 7 AND b = 7 AND c = 7 AND d = 7;
DROP STATISTICS ess_ab, ess_bc, ess_cd;

-- Phase B: OID order bc, ab, cd. Expected selected set: bc alone.
-- ANALYZE refreshes sample contents, so this experiment tests choice structure,
-- NOT equality of numeric corrections across phases.
\echo '=== ESS phase B: bc,ab,cd ==='
CREATE STATISTICS ess_bc (mcv) ON b, c FROM ess_trace_t;
CREATE STATISTICS ess_ab (mcv) ON a, b FROM ess_trace_t;
CREATE STATISTICS ess_cd (mcv) ON c, d FROM ess_trace_t;
ANALYZE ess_trace_t;
SELECT s.stxname, s.oid, s.stxkeys::text AS keys,
       d.stxdmcv IS NOT NULL AS built_mcv
FROM pg_statistic_ext AS s
LEFT JOIN pg_statistic_ext_data AS d ON d.stxoid = s.oid AND NOT d.stxdinherit
WHERE s.stxrelid = 'ess_trace_t'::regclass
ORDER BY s.oid;
EXPLAIN (COSTS OFF)
SELECT * FROM ess_trace_t WHERE a = 7 AND b = 7 AND c = 7 AND d = 7;
\echo '=== ESS tracing done ==='
