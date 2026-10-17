# Issue #7 v5 target-300 environment

This run was executed on the existing clean PostgreSQL 16.14 upstream build,
source commit `0d1c00c624fa7367d4a895f44381887757289682`, installed at
`/tmp/extstats-advisor-stock-pg16.14`.  The experiment used the private
database `ess_issue7_v5_target300`, Unix socket under
`/tmp/ess-issue7-v5-target300-20261017/socket`, and port `55451`.

The exact command was:

```text
python3 experiments/pg-maintenance/run_isolated_experiment.py \
  --prefix /tmp/extstats-advisor-stock-pg16.14 \
  --source-commit 0d1c00c624fa7367d4a895f44381887757289682 \
  --root /tmp/ess-issue7-v5-target300-20261017 \
  --output-dir experiments/pg-maintenance/runs/20261017-issue7-v5-target300-20rep \
  --fixture experiments/pg-maintenance/fixture.sql \
  --database ess_issue7_v5_target300 --port 55451 \
  --seed 20261018 --repetitions 20
```

The fixture creates two 200,000-row tables.  The `weakassoc` table uses four
independent deterministic MD5-derived marginal streams with a 30% zero
hotspot; the `correlated` table retains the controlled correlated/skewed
construction.  Exact pair counts and Cramer's V values are retained in
`fixture-metrics/fixture-metrics.json`.  The requested target-300 minimum is
90,000 rows for a 200,000-row table, derived from the pinned source rule; the
realized sample size was not observed.

The timed schedule has 80 conditions (two regimes, five target modes, eight
subsets) and 20 randomized repetition blocks, for 1,600 timed `ANALYZE`
observations.  DDL, connection setup, metadata queries, and warm-ups are
outside the `psql \\timing` interval.  `cleanup-status.json` records database
absence while the server was running, a clean server stop, and removal of the
temporary data root.
