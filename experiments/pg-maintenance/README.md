# PostgreSQL 16.14 MCV maintenance-cost benchmark

This directory contains the controlled experiment for Issue #7.  It measures
refresh-only `ANALYZE` latency for all eight subsets of three two-column MCV
statistics, in two deterministic data regimes and five target regimes.  The
historical v4 `lowcorr` fixture is functionally dependent/modular and is
retained only as historical evidence; the current corrected run uses
`weakassoc` and `correlated`:

* `uniform10`: every enabled MCV object has target 10;
* `uniform100`: every enabled MCV object has target 100;
* `mixed_10_100_10`: `ab=10`, `bc=100`, `cd=10`;
* `uniform300`: every enabled MCV object has target 300;
* `mixed_10_300_10`: `ab=10`, `bc=300`, `cd=10`.

The target-300 requested sample minimum is source-derived as 90,000 rows for
the 200,000-row table.  The benchmark does not observe or claim that this is
the realized sample size.  The corrected run uses 20 separately timed,
post-warm-up refreshes per condition in randomized blocks (1,600 timed
observations total).  `fixture_metrics.py` retains exact pair counts and
Cramer's V association diagnostics; it runs outside the timing interval.

The benchmark creates and drops statistics outside the timed interval.  A
persistent `psql` session runs one untimed warm-up and one timed `ANALYZE` per
condition and repetition.  PostgreSQL's `psql \timing` uses the pinned
source's monotonic high-resolution `instr_time` clock.  The runner retains the
complete generated schedule and raw stdout/stderr; it does not claim to
observe the realized sample size.

The experiment is intentionally a wall-time measurement of an isolated,
single-user PostgreSQL instance.  It is not a claim about CPU additivity,
cold-cache behavior, or other PostgreSQL versions.

Typical execution is documented in the generated run directory and follows
this sequence:

1. initialize and start a disposable PostgreSQL 16.14 cluster;
2. create a disposable database and load `fixture.sql`;
3. run `run_benchmark.py` with the isolated socket and port;
4. run `analyze_benchmark.py` on the resulting raw JSON; its additive-error
   analysis resamples complete randomized repetition blocks and recomputes
   the median-based discrepancy
   `D(M)=sum_e T({e})-T(M)-(k-1)T(empty)`;
5. stop the cluster and record that the data directory and server are gone.
