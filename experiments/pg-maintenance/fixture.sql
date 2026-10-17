\set ON_ERROR_STOP on
SET synchronous_commit = on;
SET client_min_messages = warning;

DROP TABLE IF EXISTS ess_mcv_lowcorr;
DROP TABLE IF EXISTS ess_mcv_correlated;

CREATE TABLE ess_mcv_lowcorr (
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

-- Four independent-looking deterministic modular streams.  The row count,
-- schema, and fixed-width integer representation match the correlated table.
INSERT INTO ess_mcv_lowcorr (id, a, b, c, d)
SELECT g,
       ((g * 2654435761::bigint + 17) % 100)::integer,
       ((g * 2246822519::bigint + 31) % 100)::integer,
       ((g * 3266489917::bigint + 47) % 100)::integer,
       ((g * 668265263::bigint + 73) % 100)::integer
FROM generate_series(1, 200000) AS s(g);

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
ALTER TABLE ess_mcv_lowcorr
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

ANALYZE ess_mcv_lowcorr;
ANALYZE ess_mcv_correlated;
