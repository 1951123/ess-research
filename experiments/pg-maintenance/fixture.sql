\set ON_ERROR_STOP on
SET synchronous_commit = on;
SET client_min_messages = warning;

DROP TABLE IF EXISTS ess_mcv_weakassoc;
DROP TABLE IF EXISTS ess_mcv_correlated;

CREATE TABLE ess_mcv_weakassoc (
    id bigint NOT NULL,
    a integer NOT NULL,
    b integer NOT NULL,
    c integer NOT NULL,
    d integer NOT NULL
) WITH (autovacuum_enabled = false);

CREATE TABLE ess_mcv_correlated (
    id bigint NOT NULL,
    a integer NOT NULL,
    b integer NOT NULL,
    c integer NOT NULL,
    d integer NOT NULL
) WITH (autovacuum_enabled = false);

-- Deterministic weak-association regime.  Each marginal is generated from a
-- different MD5-derived stream, with an independent 30% hotspot at zero and
-- 70 nonzero categories.  The streams are deterministic for reproducibility,
-- but unlike the historical modular fixture no column is a function of a
-- common g mod 100.  The skew supplies repeated pairs for MCV construction.
WITH hashes AS (
    SELECT g,
           (get_byte(decode(md5(g::text || ':a'), 'hex'), 0)::bigint << 24 |
            get_byte(decode(md5(g::text || ':a'), 'hex'), 1)::bigint << 16 |
            get_byte(decode(md5(g::text || ':a'), 'hex'), 2)::bigint << 8 |
            get_byte(decode(md5(g::text || ':a'), 'hex'), 3)::bigint) AS ha,
           (get_byte(decode(md5(g::text || ':b'), 'hex'), 0)::bigint << 24 |
            get_byte(decode(md5(g::text || ':b'), 'hex'), 1)::bigint << 16 |
            get_byte(decode(md5(g::text || ':b'), 'hex'), 2)::bigint << 8 |
            get_byte(decode(md5(g::text || ':b'), 'hex'), 3)::bigint) AS hb,
           (get_byte(decode(md5(g::text || ':c'), 'hex'), 0)::bigint << 24 |
            get_byte(decode(md5(g::text || ':c'), 'hex'), 1)::bigint << 16 |
            get_byte(decode(md5(g::text || ':c'), 'hex'), 2)::bigint << 8 |
            get_byte(decode(md5(g::text || ':c'), 'hex'), 3)::bigint) AS hc,
           (get_byte(decode(md5(g::text || ':d'), 'hex'), 0)::bigint << 24 |
            get_byte(decode(md5(g::text || ':d'), 'hex'), 1)::bigint << 16 |
            get_byte(decode(md5(g::text || ':d'), 'hex'), 2)::bigint << 8 |
            get_byte(decode(md5(g::text || ':d'), 'hex'), 3)::bigint) AS hd
    FROM generate_series(1, 200000) AS s(g)
), mapped AS (
    SELECT g,
           ha % 100 AS va,
           hb % 100 AS vb,
           hc % 100 AS vc,
           hd % 100 AS vd
    FROM hashes
)
INSERT INTO ess_mcv_weakassoc (id, a, b, c, d)
SELECT g,
       CASE WHEN va < 30 THEN 0 ELSE va - 29 END,
       CASE WHEN vb < 30 THEN 0 ELSE vb - 29 END,
       CASE WHEN vc < 30 THEN 0 ELSE vc - 29 END,
       CASE WHEN vd < 30 THEN 0 ELSE vd - 29 END
FROM mapped;

-- Deterministic correlation and skew.  The same four attributes and row count
-- are retained so that the regime changes the data distribution rather than
-- the relation shape.
INSERT INTO ess_mcv_correlated (id, a, b, c, d)
SELECT g,
       CASE WHEN g % 100 < 70 THEN 1
            WHEN g % 100 < 90 THEN 2
            ELSE ((g * 17) % 98 + 3)::integer END,
       CASE WHEN g % 100 < 70 THEN 1
            WHEN g % 100 < 90 THEN 2
            ELSE ((g * 31) % 98 + 3)::integer END,
       CASE WHEN g % 10 < 8 THEN
                 CASE WHEN g % 100 < 70 THEN 1 ELSE 2 END
            ELSE ((g * 47) % 98 + 3)::integer END,
       CASE WHEN g % 20 < 15 THEN 1
            WHEN g % 20 < 18 THEN 2
            ELSE ((g * 73) % 98 + 3)::integer END
FROM generate_series(1, 200000) AS s(g);

-- Make ordinary column sampling non-dominant relative to the extended-stat
-- targets (ordinary minrows is then 300, versus 3000 or 30000 for MCV).
ALTER TABLE ess_mcv_weakassoc
    ALTER COLUMN id SET STATISTICS 1,
    ALTER COLUMN a SET STATISTICS 1,
    ALTER COLUMN b SET STATISTICS 1,
    ALTER COLUMN c SET STATISTICS 1,
    ALTER COLUMN d SET STATISTICS 1;

ALTER TABLE ess_mcv_correlated
    ALTER COLUMN id SET STATISTICS 1,
    ALTER COLUMN a SET STATISTICS 1,
    ALTER COLUMN b SET STATISTICS 1,
    ALTER COLUMN c SET STATISTICS 1,
    ALTER COLUMN d SET STATISTICS 1;

ANALYZE ess_mcv_weakassoc;
ANALYZE ess_mcv_correlated;
