-- Issue #47 Stage 2A frozen synthetic input fixture.
-- This file is protocol/input-only. It creates no statistics objects; the
-- runner creates them in the preregistered orders after the first protocol
-- commit.

DROP TABLE IF EXISTS ess_stage2a_t;

CREATE TABLE ess_stage2a_t (
    id bigint PRIMARY KEY,
    a integer NOT NULL,
    b integer NOT NULL,
    c integer NOT NULL,
    d integer NOT NULL,
    e integer NOT NULL,
    f bigint NOT NULL
);

INSERT INTO ess_stage2a_t (id, a, b, c, d, e, f)
SELECT
    g,
    (g % 3)::integer,
    ((g / 3) % 3)::integer,
    (g % 4)::integer,
    ((g / 4) % 4)::integer,
    (g % 5)::integer,
    g
FROM generate_series(1, 20000) AS generated(g);

ALTER TABLE ess_stage2a_t ALTER COLUMN a SET STATISTICS 1000;
ALTER TABLE ess_stage2a_t ALTER COLUMN b SET STATISTICS 1000;
ALTER TABLE ess_stage2a_t ALTER COLUMN c SET STATISTICS 1000;
ALTER TABLE ess_stage2a_t ALTER COLUMN d SET STATISTICS 1000;
ALTER TABLE ess_stage2a_t ALTER COLUMN e SET STATISTICS 1000;
ALTER TABLE ess_stage2a_t ALTER COLUMN f SET STATISTICS 1000;

ANALYZE ess_stage2a_t;
