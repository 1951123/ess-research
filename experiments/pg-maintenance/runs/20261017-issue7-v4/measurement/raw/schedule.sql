\set ON_ERROR_STOP on
\pset pager off
\pset format unaligned
\pset tuples_only on
\set VERBOSITY terse
SET client_min_messages = warning;
SET synchronous_commit = on;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform100|1|1
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc_cd__uniform100|1|1
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform100|1|1
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_cd__mixed_10_100_10|1|2
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__mixed_10_100_10|1|2
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__mixed_10_100_10|1|2
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__cd__mixed_10_100_10|1|3
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__mixed_10_100_10|1|3
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__mixed_10_100_10|1|3
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__cd__mixed_10_100_10|1|4
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__mixed_10_100_10|1|4
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__mixed_10_100_10|1|4
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform100|1|5
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_cd__uniform100|1|5
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform100|1|5
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__uniform100|1|6
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
\echo WARMUP|lowcorr__ab__uniform100|1|6
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform100|1|6
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__uniform10|1|7
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__uniform10|1|7
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform10|1|7
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__uniform100|1|8
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__bc_cd__uniform100|1|8
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform100|1|8
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc__uniform100|1|9
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__uniform100|1|9
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform100|1|9
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform10|1|10
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__uniform10|1|10
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform10|1|10
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc__uniform100|1|11
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__uniform100|1|11
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform100|1|11
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__mixed_10_100_10|1|12
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__mixed_10_100_10|1|12
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__mixed_10_100_10|1|12
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform100|1|13
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__uniform100|1|13
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform100|1|13
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__mixed_10_100_10|1|14
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__mixed_10_100_10|1|14
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__mixed_10_100_10|1|14
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__mixed_10_100_10|1|15
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__mixed_10_100_10|1|15
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__mixed_10_100_10|1|15
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc__mixed_10_100_10|1|16
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__mixed_10_100_10|1|16
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__mixed_10_100_10|1|16
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform10|1|17
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform10|1|17
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform10|1|17
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__uniform10|1|18
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__bc__uniform10|1|18
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform10|1|18
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__uniform10|1|19
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform10|1|19
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform10|1|19
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform10|1|20
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc__uniform10|1|20
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform10|1|20
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_cd__uniform10|1|21
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__uniform10|1|21
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform10|1|21
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform100|1|22
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__bc_cd__uniform100|1|22
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform100|1|22
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__uniform100|1|23
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__uniform100|1|23
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform100|1|23
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__none__uniform100|1|24
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform100|1|24
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform100|1|24
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab__mixed_10_100_10|1|25
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__mixed_10_100_10|1|25
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__mixed_10_100_10|1|25
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__cd__uniform10|1|26
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__uniform10|1|26
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform10|1|26
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__mixed_10_100_10|1|27
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__mixed_10_100_10|1|27
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__mixed_10_100_10|1|27
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform10|1|28
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__uniform10|1|28
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform10|1|28
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__uniform10|1|29
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__bc__uniform10|1|29
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform10|1|29
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__mixed_10_100_10|1|30
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__mixed_10_100_10|1|30
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__mixed_10_100_10|1|30
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc_cd__mixed_10_100_10|1|31
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__mixed_10_100_10|1|31
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__mixed_10_100_10|1|31
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__uniform10|1|32
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__uniform10|1|32
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform10|1|32
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__none__uniform100|1|33
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform100|1|33
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform100|1|33
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc_cd__uniform10|1|34
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__uniform10|1|34
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform10|1|34
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc__mixed_10_100_10|1|35
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__mixed_10_100_10|1|35
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__mixed_10_100_10|1|35
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_cd__mixed_10_100_10|1|36
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__mixed_10_100_10|1|36
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__mixed_10_100_10|1|36
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_cd__uniform100|1|37
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_cd__uniform100|1|37
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform100|1|37
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__cd__uniform100|1|38
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__cd__uniform100|1|38
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform100|1|38
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform100|1|39
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc_cd__uniform100|1|39
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform100|1|39
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__none__mixed_10_100_10|1|40
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__mixed_10_100_10|1|40
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__mixed_10_100_10|1|40
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__uniform100|1|41
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
\echo WARMUP|correlated__ab__uniform100|1|41
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform100|1|41
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform10|1|42
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__uniform10|1|42
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform10|1|42
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform10|1|43
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__uniform10|1|43
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform10|1|43
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc__mixed_10_100_10|1|44
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__mixed_10_100_10|1|44
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__mixed_10_100_10|1|44
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__cd__uniform100|1|45
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__cd__uniform100|1|45
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform100|1|45
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__uniform10|1|46
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc__uniform10|1|46
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform10|1|46
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab__uniform10|1|47
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__uniform10|1|47
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform10|1|47
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__mixed_10_100_10|1|48
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__mixed_10_100_10|1|48
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__mixed_10_100_10|1|48
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__mixed_10_100_10|2|49
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__mixed_10_100_10|2|49
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__mixed_10_100_10|2|49
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__uniform10|2|50
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__uniform10|2|50
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform10|2|50
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__uniform100|2|51
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__uniform100|2|51
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform100|2|51
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__mixed_10_100_10|2|52
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__mixed_10_100_10|2|52
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__mixed_10_100_10|2|52
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__mixed_10_100_10|2|53
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__mixed_10_100_10|2|53
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__mixed_10_100_10|2|53
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__none__mixed_10_100_10|2|54
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__mixed_10_100_10|2|54
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__mixed_10_100_10|2|54
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__mixed_10_100_10|2|55
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__mixed_10_100_10|2|55
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__mixed_10_100_10|2|55
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform10|2|56
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__uniform10|2|56
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform10|2|56
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__mixed_10_100_10|2|57
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__mixed_10_100_10|2|57
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__mixed_10_100_10|2|57
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__uniform10|2|58
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__uniform10|2|58
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform10|2|58
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__mixed_10_100_10|2|59
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__mixed_10_100_10|2|59
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__mixed_10_100_10|2|59
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform10|2|60
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__uniform10|2|60
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform10|2|60
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__uniform100|2|61
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__cd__uniform100|2|61
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform100|2|61
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform100|2|62
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__uniform100|2|62
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform100|2|62
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__uniform10|2|63
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__uniform10|2|63
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform10|2|63
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_cd__uniform100|2|64
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_cd__uniform100|2|64
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform100|2|64
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc_cd__uniform100|2|65
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__bc_cd__uniform100|2|65
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform100|2|65
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform10|2|66
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__uniform10|2|66
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform10|2|66
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform100|2|67
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc_cd__uniform100|2|67
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform100|2|67
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__uniform10|2|68
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc__uniform10|2|68
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform10|2|68
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__uniform10|2|69
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform10|2|69
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform10|2|69
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__mixed_10_100_10|2|70
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__mixed_10_100_10|2|70
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__mixed_10_100_10|2|70
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__mixed_10_100_10|2|71
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__mixed_10_100_10|2|71
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__mixed_10_100_10|2|71
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__uniform100|2|72
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
\echo WARMUP|correlated__ab__uniform100|2|72
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform100|2|72
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform100|2|73
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__bc_cd__uniform100|2|73
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform100|2|73
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__mixed_10_100_10|2|74
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__mixed_10_100_10|2|74
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__mixed_10_100_10|2|74
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc__uniform100|2|75
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__uniform100|2|75
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform100|2|75
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform100|2|76
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_cd__uniform100|2|76
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform100|2|76
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__uniform10|2|77
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__uniform10|2|77
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform10|2|77
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform10|2|78
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__uniform10|2|78
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform10|2|78
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__uniform100|2|79
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
\echo WARMUP|lowcorr__ab__uniform100|2|79
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform100|2|79
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform100|2|80
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform100|2|80
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform100|2|80
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc__mixed_10_100_10|2|81
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__mixed_10_100_10|2|81
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__mixed_10_100_10|2|81
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__uniform10|2|82
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__bc__uniform10|2|82
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform10|2|82
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform10|2|83
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform10|2|83
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform10|2|83
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__uniform10|2|84
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__bc__uniform10|2|84
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform10|2|84
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__mixed_10_100_10|2|85
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__mixed_10_100_10|2|85
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__mixed_10_100_10|2|85
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform100|2|86
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc_cd__uniform100|2|86
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform100|2|86
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__cd__uniform100|2|87
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__cd__uniform100|2|87
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform100|2|87
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__uniform100|2|88
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__uniform100|2|88
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform100|2|88
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__uniform100|2|89
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform100|2|89
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform100|2|89
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform10|2|90
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc__uniform10|2|90
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform10|2|90
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__mixed_10_100_10|2|91
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__mixed_10_100_10|2|91
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__mixed_10_100_10|2|91
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__mixed_10_100_10|2|92
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__mixed_10_100_10|2|92
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__mixed_10_100_10|2|92
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__uniform10|2|93
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__uniform10|2|93
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform10|2|93
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__mixed_10_100_10|2|94
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__mixed_10_100_10|2|94
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__mixed_10_100_10|2|94
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab__uniform10|2|95
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__uniform10|2|95
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform10|2|95
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__mixed_10_100_10|2|96
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__mixed_10_100_10|2|96
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__mixed_10_100_10|2|96
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab__uniform100|3|97
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
\echo WARMUP|correlated__ab__uniform100|3|97
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform100|3|97
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc__uniform100|3|98
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__uniform100|3|98
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform100|3|98
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__uniform10|3|99
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__bc__uniform10|3|99
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform10|3|99
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_cd__mixed_10_100_10|3|100
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__mixed_10_100_10|3|100
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__mixed_10_100_10|3|100
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__uniform100|3|101
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform100|3|101
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform100|3|101
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__mixed_10_100_10|3|102
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__mixed_10_100_10|3|102
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__mixed_10_100_10|3|102
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__uniform10|3|103
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__uniform10|3|103
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform10|3|103
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__uniform100|3|104
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_cd__uniform100|3|104
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform100|3|104
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform100|3|105
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_cd__uniform100|3|105
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform100|3|105
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform10|3|106
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__uniform10|3|106
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform10|3|106
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform100|3|107
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc_cd__uniform100|3|107
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform100|3|107
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__cd__mixed_10_100_10|3|108
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__mixed_10_100_10|3|108
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__mixed_10_100_10|3|108
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc__uniform10|3|109
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__bc__uniform10|3|109
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform10|3|109
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__none__mixed_10_100_10|3|110
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__mixed_10_100_10|3|110
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__mixed_10_100_10|3|110
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform100|3|111
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__uniform100|3|111
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform100|3|111
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__mixed_10_100_10|3|112
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__mixed_10_100_10|3|112
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__mixed_10_100_10|3|112
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform100|3|113
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc_cd__uniform100|3|113
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform100|3|113
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab__mixed_10_100_10|3|114
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__mixed_10_100_10|3|114
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__mixed_10_100_10|3|114
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__mixed_10_100_10|3|115
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__mixed_10_100_10|3|115
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__mixed_10_100_10|3|115
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__uniform100|3|116
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__uniform100|3|116
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform100|3|116
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__mixed_10_100_10|3|117
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__mixed_10_100_10|3|117
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__mixed_10_100_10|3|117
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__mixed_10_100_10|3|118
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__mixed_10_100_10|3|118
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__mixed_10_100_10|3|118
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__mixed_10_100_10|3|119
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__mixed_10_100_10|3|119
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__mixed_10_100_10|3|119
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__mixed_10_100_10|3|120
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__mixed_10_100_10|3|120
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__mixed_10_100_10|3|120
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__uniform10|3|121
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__uniform10|3|121
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform10|3|121
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__uniform100|3|122
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__uniform100|3|122
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform100|3|122
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform10|3|123
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__uniform10|3|123
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform10|3|123
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__uniform10|3|124
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__uniform10|3|124
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform10|3|124
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform10|3|125
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__uniform10|3|125
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform10|3|125
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__mixed_10_100_10|3|126
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__mixed_10_100_10|3|126
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__mixed_10_100_10|3|126
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__mixed_10_100_10|3|127
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__mixed_10_100_10|3|127
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__mixed_10_100_10|3|127
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__none__uniform10|3|128
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform10|3|128
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform10|3|128
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__uniform10|3|129
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__uniform10|3|129
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform10|3|129
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__uniform100|3|130
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__bc_cd__uniform100|3|130
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform100|3|130
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc__mixed_10_100_10|3|131
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__mixed_10_100_10|3|131
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__mixed_10_100_10|3|131
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform100|3|132
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__bc_cd__uniform100|3|132
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform100|3|132
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform10|3|133
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__uniform10|3|133
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform10|3|133
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc__mixed_10_100_10|3|134
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__mixed_10_100_10|3|134
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__mixed_10_100_10|3|134
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__none__uniform100|3|135
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform100|3|135
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform100|3|135
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__uniform10|3|136
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__uniform10|3|136
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform10|3|136
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc__uniform10|3|137
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc__uniform10|3|137
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform10|3|137
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__cd__uniform100|3|138
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__cd__uniform100|3|138
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform100|3|138
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__mixed_10_100_10|3|139
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__mixed_10_100_10|3|139
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__mixed_10_100_10|3|139
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__cd__uniform100|3|140
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__cd__uniform100|3|140
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform100|3|140
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform10|3|141
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc__uniform10|3|141
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform10|3|141
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform10|3|142
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform10|3|142
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform10|3|142
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__cd__uniform10|3|143
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__uniform10|3|143
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform10|3|143
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__uniform100|3|144
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
\echo WARMUP|lowcorr__ab__uniform100|3|144
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform100|3|144
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__uniform100|4|145
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__uniform100|4|145
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform100|4|145
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform10|4|146
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__uniform10|4|146
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform10|4|146
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__uniform10|4|147
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__uniform10|4|147
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform10|4|147
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc_cd__mixed_10_100_10|4|148
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__mixed_10_100_10|4|148
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__mixed_10_100_10|4|148
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__uniform10|4|149
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__bc__uniform10|4|149
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform10|4|149
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform100|4|150
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__bc_cd__uniform100|4|150
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform100|4|150
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__none__mixed_10_100_10|4|151
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__mixed_10_100_10|4|151
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__mixed_10_100_10|4|151
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__mixed_10_100_10|4|152
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__mixed_10_100_10|4|152
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__mixed_10_100_10|4|152
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__uniform100|4|153
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__uniform100|4|153
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform100|4|153
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__mixed_10_100_10|4|154
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__mixed_10_100_10|4|154
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__mixed_10_100_10|4|154
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc_cd__mixed_10_100_10|4|155
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__mixed_10_100_10|4|155
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__mixed_10_100_10|4|155
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform100|4|156
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_cd__uniform100|4|156
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform100|4|156
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__none__uniform100|4|157
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform100|4|157
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform100|4|157
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform10|4|158
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__uniform10|4|158
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform10|4|158
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__uniform10|4|159
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__uniform10|4|159
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform10|4|159
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc_cd__uniform100|4|160
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__bc_cd__uniform100|4|160
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform100|4|160
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__mixed_10_100_10|4|161
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__mixed_10_100_10|4|161
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__mixed_10_100_10|4|161
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform10|4|162
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__uniform10|4|162
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform10|4|162
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform100|4|163
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform100|4|163
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform100|4|163
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform10|4|164
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__uniform10|4|164
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform10|4|164
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform100|4|165
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc_cd__uniform100|4|165
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform100|4|165
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__uniform100|4|166
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__cd__uniform100|4|166
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform100|4|166
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__mixed_10_100_10|4|167
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__mixed_10_100_10|4|167
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__mixed_10_100_10|4|167
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc__mixed_10_100_10|4|168
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__mixed_10_100_10|4|168
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__mixed_10_100_10|4|168
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__uniform10|4|169
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__uniform10|4|169
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform10|4|169
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__uniform100|4|170
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
\echo WARMUP|correlated__ab__uniform100|4|170
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform100|4|170
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform10|4|171
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc__uniform10|4|171
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform10|4|171
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform10|4|172
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform10|4|172
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform10|4|172
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__uniform10|4|173
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform10|4|173
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform10|4|173
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab__uniform10|4|174
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__uniform10|4|174
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform10|4|174
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__cd__mixed_10_100_10|4|175
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__mixed_10_100_10|4|175
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__mixed_10_100_10|4|175
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__uniform100|4|176
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__uniform100|4|176
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform100|4|176
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__none__mixed_10_100_10|4|177
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__mixed_10_100_10|4|177
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__mixed_10_100_10|4|177
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform100|4|178
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc_cd__uniform100|4|178
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform100|4|178
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__mixed_10_100_10|4|179
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__mixed_10_100_10|4|179
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__mixed_10_100_10|4|179
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc__mixed_10_100_10|4|180
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__mixed_10_100_10|4|180
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__mixed_10_100_10|4|180
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc__uniform10|4|181
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__bc__uniform10|4|181
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform10|4|181
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__uniform10|4|182
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__uniform10|4|182
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform10|4|182
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_cd__mixed_10_100_10|4|183
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__mixed_10_100_10|4|183
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__mixed_10_100_10|4|183
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab__uniform10|4|184
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__uniform10|4|184
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform10|4|184
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__mixed_10_100_10|4|185
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__mixed_10_100_10|4|185
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__mixed_10_100_10|4|185
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab__mixed_10_100_10|4|186
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__mixed_10_100_10|4|186
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__mixed_10_100_10|4|186
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc__uniform10|4|187
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc__uniform10|4|187
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform10|4|187
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform100|4|188
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__uniform100|4|188
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform100|4|188
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__uniform100|4|189
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__cd__uniform100|4|189
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform100|4|189
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__uniform100|4|190
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_cd__uniform100|4|190
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform100|4|190
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__mixed_10_100_10|4|191
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__mixed_10_100_10|4|191
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__mixed_10_100_10|4|191
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab__uniform100|4|192
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
\echo WARMUP|lowcorr__ab__uniform100|4|192
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform100|4|192
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__mixed_10_100_10|5|193
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__mixed_10_100_10|5|193
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__mixed_10_100_10|5|193
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__uniform10|5|194
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__uniform10|5|194
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform10|5|194
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc__uniform100|5|195
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__uniform100|5|195
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform100|5|195
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__mixed_10_100_10|5|196
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__mixed_10_100_10|5|196
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__mixed_10_100_10|5|196
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform100|5|197
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_cd__uniform100|5|197
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform100|5|197
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab__mixed_10_100_10|5|198
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__mixed_10_100_10|5|198
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__mixed_10_100_10|5|198
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc__uniform10|5|199
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__bc__uniform10|5|199
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform10|5|199
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform10|5|200
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__uniform10|5|200
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform10|5|200
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__mixed_10_100_10|5|201
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__mixed_10_100_10|5|201
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__mixed_10_100_10|5|201
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__uniform100|5|202
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_cd__uniform100|5|202
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform100|5|202
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_cd__mixed_10_100_10|5|203
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__mixed_10_100_10|5|203
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__mixed_10_100_10|5|203
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform10|5|204
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform10|5|204
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform10|5|204
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc_cd__uniform10|5|205
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__uniform10|5|205
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform10|5|205
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__uniform100|5|206
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform100|5|206
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform100|5|206
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__uniform100|5|207
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__uniform100|5|207
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform100|5|207
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__mixed_10_100_10|5|208
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__mixed_10_100_10|5|208
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__mixed_10_100_10|5|208
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc__uniform10|5|209
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__bc__uniform10|5|209
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform10|5|209
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab__uniform100|5|210
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
\echo WARMUP|lowcorr__ab__uniform100|5|210
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform100|5|210
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform10|5|211
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__uniform10|5|211
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform10|5|211
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform10|5|212
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc__uniform10|5|212
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform10|5|212
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__uniform10|5|213
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__uniform10|5|213
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform10|5|213
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_cd__uniform10|5|214
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__uniform10|5|214
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform10|5|214
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform100|5|215
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc_cd__uniform100|5|215
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform100|5|215
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__mixed_10_100_10|5|216
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__mixed_10_100_10|5|216
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__mixed_10_100_10|5|216
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform100|5|217
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc_cd__uniform100|5|217
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform100|5|217
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform100|5|218
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__uniform100|5|218
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform100|5|218
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__none__mixed_10_100_10|5|219
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__mixed_10_100_10|5|219
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__mixed_10_100_10|5|219
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform100|5|220
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__bc_cd__uniform100|5|220
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform100|5|220
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab__uniform10|5|221
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__uniform10|5|221
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform10|5|221
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__cd__uniform100|5|222
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__cd__uniform100|5|222
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform100|5|222
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__mixed_10_100_10|5|223
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__mixed_10_100_10|5|223
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__mixed_10_100_10|5|223
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__uniform100|5|224
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__cd__uniform100|5|224
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform100|5|224
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc_cd__uniform100|5|225
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__bc_cd__uniform100|5|225
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform100|5|225
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc_cd__mixed_10_100_10|5|226
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__mixed_10_100_10|5|226
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__mixed_10_100_10|5|226
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform10|5|227
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__uniform10|5|227
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform10|5|227
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__mixed_10_100_10|5|228
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__mixed_10_100_10|5|228
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__mixed_10_100_10|5|228
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab__uniform10|5|229
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__uniform10|5|229
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform10|5|229
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform10|5|230
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__uniform10|5|230
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform10|5|230
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__mixed_10_100_10|5|231
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__mixed_10_100_10|5|231
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__mixed_10_100_10|5|231
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc_cd__mixed_10_100_10|5|232
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__mixed_10_100_10|5|232
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__mixed_10_100_10|5|232
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__cd__mixed_10_100_10|5|233
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__mixed_10_100_10|5|233
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__mixed_10_100_10|5|233
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__uniform10|5|234
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform10|5|234
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform10|5|234
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_cd__mixed_10_100_10|5|235
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__mixed_10_100_10|5|235
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__mixed_10_100_10|5|235
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc__uniform10|5|236
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc__uniform10|5|236
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform10|5|236
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__uniform100|5|237
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__uniform100|5|237
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform100|5|237
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__uniform100|5|238
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
\echo WARMUP|correlated__ab__uniform100|5|238
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform100|5|238
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__mixed_10_100_10|5|239
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__mixed_10_100_10|5|239
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__mixed_10_100_10|5|239
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform100|5|240
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform100|5|240
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform100|5|240
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__mixed_10_100_10|6|241
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__mixed_10_100_10|6|241
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__mixed_10_100_10|6|241
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform100|6|242
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform100|6|242
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform100|6|242
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc__uniform10|6|243
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__bc__uniform10|6|243
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform10|6|243
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__mixed_10_100_10|6|244
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__mixed_10_100_10|6|244
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__mixed_10_100_10|6|244
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc__uniform100|6|245
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__uniform100|6|245
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform100|6|245
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__uniform10|6|246
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform10|6|246
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform10|6|246
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__uniform10|6|247
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__uniform10|6|247
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform10|6|247
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__none__uniform100|6|248
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform100|6|248
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform100|6|248
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform10|6|249
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__uniform10|6|249
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform10|6|249
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__uniform100|6|250
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__uniform100|6|250
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform100|6|250
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform10|6|251
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc__uniform10|6|251
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform10|6|251
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc__mixed_10_100_10|6|252
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__mixed_10_100_10|6|252
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__mixed_10_100_10|6|252
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__uniform10|6|253
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__uniform10|6|253
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform10|6|253
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__mixed_10_100_10|6|254
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__mixed_10_100_10|6|254
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__mixed_10_100_10|6|254
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__none__mixed_10_100_10|6|255
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__mixed_10_100_10|6|255
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__mixed_10_100_10|6|255
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__cd__mixed_10_100_10|6|256
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__mixed_10_100_10|6|256
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__mixed_10_100_10|6|256
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__uniform100|6|257
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__uniform100|6|257
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform100|6|257
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__mixed_10_100_10|6|258
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__mixed_10_100_10|6|258
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__mixed_10_100_10|6|258
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__mixed_10_100_10|6|259
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__mixed_10_100_10|6|259
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__mixed_10_100_10|6|259
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc__uniform10|6|260
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc__uniform10|6|260
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform10|6|260
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__mixed_10_100_10|6|261
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__mixed_10_100_10|6|261
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__mixed_10_100_10|6|261
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform10|6|262
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__uniform10|6|262
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform10|6|262
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform100|6|263
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_cd__uniform100|6|263
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform100|6|263
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform100|6|264
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__uniform100|6|264
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform100|6|264
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform10|6|265
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__uniform10|6|265
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform10|6|265
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__uniform100|6|266
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
\echo WARMUP|lowcorr__ab__uniform100|6|266
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform100|6|266
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__mixed_10_100_10|6|267
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__mixed_10_100_10|6|267
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__mixed_10_100_10|6|267
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform10|6|268
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform10|6|268
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform10|6|268
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc__mixed_10_100_10|6|269
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__mixed_10_100_10|6|269
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__mixed_10_100_10|6|269
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__uniform100|6|270
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_cd__uniform100|6|270
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform100|6|270
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__mixed_10_100_10|6|271
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__mixed_10_100_10|6|271
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__mixed_10_100_10|6|271
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc__uniform10|6|272
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__bc__uniform10|6|272
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform10|6|272
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__uniform100|6|273
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
\echo WARMUP|correlated__ab__uniform100|6|273
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform100|6|273
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform100|6|274
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc_cd__uniform100|6|274
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform100|6|274
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__uniform10|6|275
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__uniform10|6|275
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform10|6|275
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__cd__uniform100|6|276
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__cd__uniform100|6|276
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform100|6|276
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform100|6|277
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc_cd__uniform100|6|277
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform100|6|277
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__mixed_10_100_10|6|278
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__mixed_10_100_10|6|278
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__mixed_10_100_10|6|278
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform10|6|279
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__uniform10|6|279
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform10|6|279
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform100|6|280
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__bc_cd__uniform100|6|280
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform100|6|280
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc__mixed_10_100_10|6|281
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__mixed_10_100_10|6|281
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__mixed_10_100_10|6|281
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__cd__uniform100|6|282
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__cd__uniform100|6|282
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform100|6|282
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__uniform10|6|283
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__uniform10|6|283
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform10|6|283
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab__mixed_10_100_10|6|284
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__mixed_10_100_10|6|284
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__mixed_10_100_10|6|284
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__uniform10|6|285
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__uniform10|6|285
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform10|6|285
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc_cd__uniform100|6|286
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__bc_cd__uniform100|6|286
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform100|6|286
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__mixed_10_100_10|6|287
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__mixed_10_100_10|6|287
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__mixed_10_100_10|6|287
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__uniform10|6|288
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__uniform10|6|288
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform10|6|288
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__cd__uniform100|7|289
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__cd__uniform100|7|289
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform100|7|289
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform100|7|290
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc_cd__uniform100|7|290
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform100|7|290
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc__uniform100|7|291
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__uniform100|7|291
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform100|7|291
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_bc_cd__uniform10|7|292
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__uniform10|7|292
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__uniform10|7|292
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__none__uniform10|7|293
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform10|7|293
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform10|7|293
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab__uniform100|7|294
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
\echo WARMUP|lowcorr__ab__uniform100|7|294
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform100|7|294
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__mixed_10_100_10|7|295
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__mixed_10_100_10|7|295
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__mixed_10_100_10|7|295
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__none__mixed_10_100_10|7|296
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__mixed_10_100_10|7|296
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__mixed_10_100_10|7|296
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__mixed_10_100_10|7|297
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__mixed_10_100_10|7|297
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__mixed_10_100_10|7|297
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__none__uniform100|7|298
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
\echo WARMUP|lowcorr__none__uniform100|7|298
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__none__uniform100|7|298
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform100|7|299
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__uniform100|7|299
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform100|7|299
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__cd__uniform10|7|300
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__cd__uniform10|7|300
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__cd__uniform10|7|300
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc__mixed_10_100_10|7|301
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__mixed_10_100_10|7|301
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__mixed_10_100_10|7|301
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__uniform10|7|302
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc__uniform10|7|302
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__uniform10|7|302
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__uniform100|7|303
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__bc_cd__uniform100|7|303
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform100|7|303
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__mixed_10_100_10|7|304
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__mixed_10_100_10|7|304
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__mixed_10_100_10|7|304
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__mixed_10_100_10|7|305
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__mixed_10_100_10|7|305
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__mixed_10_100_10|7|305
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__uniform10|7|306
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc__uniform10|7|306
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__uniform10|7|306
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab__mixed_10_100_10|7|307
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__mixed_10_100_10|7|307
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__mixed_10_100_10|7|307
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__uniform10|7|308
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__uniform10|7|308
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__uniform10|7|308
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc__mixed_10_100_10|7|309
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc__mixed_10_100_10|7|309
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc__mixed_10_100_10|7|309
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__bc_cd__mixed_10_100_10|7|310
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__bc_cd__mixed_10_100_10|7|310
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc_cd__mixed_10_100_10|7|310
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform100|7|311
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__bc_cd__uniform100|7|311
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform100|7|311
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__bc__uniform100|7|312
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
\echo WARMUP|lowcorr__bc__uniform100|7|312
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform100|7|312
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__mixed_10_100_10|7|313
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__mixed_10_100_10|7|313
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__mixed_10_100_10|7|313
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_cd__uniform100|7|314
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__ab_cd__uniform100|7|314
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform100|7|314
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__none__uniform100|7|315
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform100|7|315
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform100|7|315
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__uniform10|7|316
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 10;
\echo WARMUP|correlated__bc__uniform10|7|316
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform10|7|316
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab__uniform10|7|317
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
\echo WARMUP|correlated__ab__uniform10|7|317
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform10|7|317
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform10|7|318
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_bc_cd__uniform10|7|318
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform10|7|318
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform10|7|319
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__ab_cd__uniform10|7|319
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform10|7|319
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__mixed_10_100_10|7|320
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__mixed_10_100_10|7|320
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__mixed_10_100_10|7|320
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__bc__uniform100|7|321
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__bc__uniform100|7|321
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__bc__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__bc__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__bc__uniform100|7|321
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__uniform10|7|322
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__uniform10|7|322
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__uniform10|7|322
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__cd__mixed_10_100_10|7|323
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__mixed_10_100_10|7|323
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__mixed_10_100_10|7|323
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__ab_cd__mixed_10_100_10|7|324
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__mixed_10_100_10|7|324
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__mixed_10_100_10|7|324
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__cd__uniform100|7|325
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 100;
\echo WARMUP|correlated__cd__uniform100|7|325
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform100|7|325
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_cd__uniform100|7|326
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_cd__uniform100|7|326
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_cd__uniform100|7|326
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc__mixed_10_100_10|7|327
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
\echo WARMUP|correlated__ab_bc__mixed_10_100_10|7|327
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc__mixed_10_100_10|7|327
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab_bc_cd__uniform100|7|328
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 100;
\echo WARMUP|lowcorr__ab_bc_cd__uniform100|7|328
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab_bc_cd__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab_bc_cd__uniform100|7|328
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab__uniform100|7|329
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 100;
\echo WARMUP|correlated__ab__uniform100|7|329
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab__uniform100' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab__uniform100' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab__uniform100|7|329
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc_cd__mixed_10_100_10|7|330
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_lowcorr_cd (mcv) ON c,d FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_cd SET STATISTICS 10;
\echo WARMUP|lowcorr__bc_cd__mixed_10_100_10|7|330
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc_cd__mixed_10_100_10|7|330
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_bc_cd__mixed_10_100_10|7|331
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_bc (mcv) ON b,c FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_bc SET STATISTICS 100;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_bc_cd__mixed_10_100_10|7|331
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_bc_cd__mixed_10_100_10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_bc_cd__mixed_10_100_10|7|331
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|correlated__cd__uniform10|7|332
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__cd__uniform10|7|332
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__cd__uniform10|7|332
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__ab__uniform10|7|333
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_ab (mcv) ON a,b FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_ab SET STATISTICS 10;
\echo WARMUP|lowcorr__ab__uniform10|7|333
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__ab__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__ab__uniform10|7|333
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__none__uniform10|7|334
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
\echo WARMUP|correlated__none__uniform10|7|334
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__none__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__none__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__none__uniform10|7|334
ANALYZE ess_mcv_correlated;
\timing off
\echo SETUP|lowcorr__bc__uniform10|7|335
\timing off
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_ab;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_bc;
DROP STATISTICS IF EXISTS ess_mcv_lowcorr_cd;
CREATE STATISTICS ess_mcv_lowcorr_bc (mcv) ON b,c FROM ess_mcv_lowcorr;
ALTER STATISTICS ess_mcv_lowcorr_bc SET STATISTICS 10;
\echo WARMUP|lowcorr__bc__uniform10|7|335
ANALYZE ess_mcv_lowcorr;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd') ORDER BY e.stxname;
SELECT 'META|' || 'lowcorr__bc__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_lowcorr'::regclass AND e.stxname IN ('ess_mcv_lowcorr_ab', 'ess_mcv_lowcorr_bc', 'ess_mcv_lowcorr_cd'));
\timing on
\echo RUN|lowcorr__bc__uniform10|7|335
ANALYZE ess_mcv_lowcorr;
\timing off
\echo SETUP|correlated__ab_cd__uniform10|7|336
\timing off
DROP STATISTICS IF EXISTS ess_mcv_correlated_ab;
DROP STATISTICS IF EXISTS ess_mcv_correlated_bc;
DROP STATISTICS IF EXISTS ess_mcv_correlated_cd;
CREATE STATISTICS ess_mcv_correlated_ab (mcv) ON a,b FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_ab SET STATISTICS 10;
CREATE STATISTICS ess_mcv_correlated_cd (mcv) ON c,d FROM ess_mcv_correlated;
ALTER STATISTICS ess_mcv_correlated_cd SET STATISTICS 10;
\echo WARMUP|correlated__ab_cd__uniform10|7|336
ANALYZE ess_mcv_correlated;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|' || e.stxname || '|' || e.oid::text || '|' || COALESCE(e.stxstattarget::text, 'NULL') || '|' || (d.stxdmcv IS NOT NULL)::text FROM pg_statistic_ext e LEFT JOIN pg_statistic_ext_data d ON d.stxoid = e.oid WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd') ORDER BY e.stxname;
SELECT 'META|' || 'correlated__ab_cd__uniform10' || '|NONE' WHERE NOT EXISTS (SELECT 1 FROM pg_statistic_ext e WHERE e.stxrelid = 'ess_mcv_correlated'::regclass AND e.stxname IN ('ess_mcv_correlated_ab', 'ess_mcv_correlated_bc', 'ess_mcv_correlated_cd'));
\timing on
\echo RUN|correlated__ab_cd__uniform10|7|336
ANALYZE ess_mcv_correlated;
\timing off
