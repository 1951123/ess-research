# Issue #7 environment and provenance

Date: 2026-10-17 (Asia/Shanghai)

## PostgreSQL build

The benchmark used the clean local PostgreSQL source repository
`/home/wqts/projects/postgresql-src` at official `REL_16_14`, commit
`0d1c00c624fa7367d4a895f44381887757289682`.  The source worktree was clean.
The already-built source tree was installed into the disposable prefix
`/tmp/extstats-advisor-stock-pg16.14` with:

```text
make -C /home/wqts/projects/postgresql-src -j2 install
```

The installed binary SHA256 values were:

```text
postgres 5810ae37bb014b08b4ac0332f6d19273b74a8bbe441f094f367f5faa1a0f6c98
psql     eddb35e5385fe72938765f7857c822b9d111caacbb1f73c61c1428845dd244ce
```

PostgreSQL reported version `16.14`.  The executable is clean upstream; no
`ess-postgresql` source or instrumentation was used or changed for this
experiment.  The research source commit at experiment start was
`b2e543bbf990ed4d80a4312ec6a7511a0fda808f`.

Platform: Ubuntu 24.04, Linux kernel `7.0.0-38-generic`, x86-64, GCC
`13.3.0-6ubuntu2~24.04.1`, Python `3.12.3`.

## Isolated lifecycle

The final run used database `ess_issue7_v4`, Unix socket
`/tmp/ess-issue7-20261017-v4/socket`, port `55450`, and a private data
directory under `/tmp/ess-issue7-20261017-v4`.  The server was started with
`autovacuum=off`; both benchmark tables also set `autovacuum_enabled=false`.
No concurrent client workload was used.  The database was dropped while the
server was still running, absence was checked by a separate `psql` query, the
server was stopped with `pg_ctl -m fast stop -w`, and the temporary root was
removed.  The machine-readable evidence is in `cleanup-status.json` and
`cleanup-before-stop.json`.

The two tables each contain exactly 200,000 inserted rows, the same schema,
and the same measured relation sizes: `pg_relation_size=10,436,608`,
`pg_table_size=10,461,184`, and `pg_total_relation_size=10,461,184` bytes.
The retained `reltuples=200018` value is an estimate and is not substituted for
the exact inserted count.  `fixture.sql` fixes ordinary column targets to 1.

## Timing and source-grounded sampling rule

The benchmark keeps one persistent `psql` connection.  DDL and setup are
executed with timing disabled; each condition first receives one untimed
warm-up `ANALYZE`, followed by one timed `ANALYZE`.  The `psql \\timing`
measurement is the command round-trip and excludes connection establishment
and DDL.  In the pinned PostgreSQL source, `src/include/portability/instr_time.h`
lines 90--104 select `CLOCK_MONOTONIC` when available, and lines 116--126
convert the high-resolution timestamp to the reported interval.

In `src/backend/statistics/extended_stats.c` lines 290--326,
`ComputeExtStatisticsRows` takes the largest buildable extended-statistics
target and returns `300 * result`.  In `src/backend/commands/analyze.c` lines
492--528, `ANALYZE` takes the maximum of ordinary/index minima and that extended
minimum before acquiring rows.  With ordinary target 1, the source-derived
requested minima are 300 rows for an empty subset, 3,000 for effective target
10, and 30,000 for effective target 100.  These are requested minima only; the
experiment does **not** observe or claim the realized sample size.

## Exact command

```text
python3 experiments/pg-maintenance/run_isolated_experiment.py \\
  --prefix /tmp/extstats-advisor-stock-pg16.14 \\
  --source-commit 0d1c00c624fa7367d4a895f44381887757289682 \\
  --root /tmp/ess-issue7-20261017-v4 \\
  --output-dir experiments/pg-maintenance/runs/20261017-issue7-v4 \\
  --fixture experiments/pg-maintenance/fixture.sql \\
  --database ess_issue7_v4 --port 55450 \\
  --seed 20261017 --repetitions 7
```

The generated `measurement/raw/schedule.sql` is the exact randomized schedule
used by the persistent connection.  Each of the 48 conditions appears once
per round for seven rounds; condition order is shuffled by Python's
`random.Random(20261017)`.
