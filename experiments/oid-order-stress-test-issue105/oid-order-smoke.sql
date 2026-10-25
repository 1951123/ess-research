\set ON_ERROR_STOP on

DROP TABLE IF EXISTS public.issue105_oid_order_fixture CASCADE;
CREATE TABLE public.issue105_oid_order_fixture (a integer, b integer, c integer);
INSERT INTO public.issue105_oid_order_fixture (a, b, c)
SELECT (g % 2)::integer, (g % 2)::integer, ((g / 2) % 2)::integer
FROM generate_series(1, 1024) AS values(g);
ALTER TABLE public.issue105_oid_order_fixture
    ALTER COLUMN a SET STATISTICS 300;
ALTER TABLE public.issue105_oid_order_fixture
    ALTER COLUMN b SET STATISTICS 300;
ALTER TABLE public.issue105_oid_order_fixture
    ALTER COLUMN c SET STATISTICS 300;
SET default_statistics_target = 300;

\echo === FORWARD CREATE ORDER: ab, bc ===
CREATE STATISTICS public.issue105_ab (mcv)
    ON a, b FROM public.issue105_oid_order_fixture;
ALTER STATISTICS public.issue105_ab SET STATISTICS 300;
CREATE STATISTICS public.issue105_bc (mcv)
    ON b, c FROM public.issue105_oid_order_fixture;
ALTER STATISTICS public.issue105_bc SET STATISTICS 300;
ANALYZE public.issue105_oid_order_fixture;

SELECT stxname, oid AS stat_oid, stxkeys,
       (SELECT count(*) FROM pg_catalog.pg_mcv_list_items(d.stxdmcv)) AS mcv_items
FROM pg_catalog.pg_statistic_ext AS s
JOIN pg_catalog.pg_statistic_ext_data AS d
  ON d.stxoid = s.oid AND NOT d.stxdinherit
WHERE s.stxrelid = 'public.issue105_oid_order_fixture'::regclass
ORDER BY s.oid;
SELECT statistics_name, attnames, most_common_vals, most_common_freqs
FROM pg_catalog.pg_stats_ext
WHERE schemaname = 'public'
  AND tablename = 'issue105_oid_order_fixture'
ORDER BY statistics_name;

SET client_min_messages = debug1;
EXPLAIN (FORMAT JSON, SUMMARY OFF)
SELECT *
FROM public.issue105_oid_order_fixture
WHERE a = 1 AND b = 1 AND c = 1;
RESET client_min_messages;

\echo === REVERSE CREATE ORDER: bc, ab ===
DROP STATISTICS public.issue105_ab, public.issue105_bc;
CREATE STATISTICS public.issue105_bc (mcv)
    ON b, c FROM public.issue105_oid_order_fixture;
ALTER STATISTICS public.issue105_bc SET STATISTICS 300;
CREATE STATISTICS public.issue105_ab (mcv)
    ON a, b FROM public.issue105_oid_order_fixture;
ALTER STATISTICS public.issue105_ab SET STATISTICS 300;
ANALYZE public.issue105_oid_order_fixture;

SELECT stxname, oid AS stat_oid, stxkeys,
       (SELECT count(*) FROM pg_catalog.pg_mcv_list_items(d.stxdmcv)) AS mcv_items
FROM pg_catalog.pg_statistic_ext AS s
JOIN pg_catalog.pg_statistic_ext_data AS d
  ON d.stxoid = s.oid AND NOT d.stxdinherit
WHERE s.stxrelid = 'public.issue105_oid_order_fixture'::regclass
ORDER BY s.oid;
SELECT statistics_name, attnames, most_common_vals, most_common_freqs
FROM pg_catalog.pg_stats_ext
WHERE schemaname = 'public'
  AND tablename = 'issue105_oid_order_fixture'
ORDER BY statistics_name;

SET client_min_messages = debug1;
EXPLAIN (FORMAT JSON, SUMMARY OFF)
SELECT *
FROM public.issue105_oid_order_fixture
WHERE a = 1 AND b = 1 AND c = 1;
RESET client_min_messages;

DROP TABLE public.issue105_oid_order_fixture CASCADE;
