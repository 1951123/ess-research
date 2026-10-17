# Issue #7 v5 — corrected weak-association and target-300 measurements

## Scope and evidence

This immutable run extends the historical v4 evidence without modifying it.
It uses two deterministic 200,000-row tables, eight subsets of the three
two-column MCV objects (`ab`, `bc`, `cd`), five target modes, and 20 randomized
post-warm-up repetitions per condition:

* historical modes: `uniform10`, `uniform100`, and `mixed_10_100_10`;
* new modes: `uniform300` and `mixed_10_300_10`.

There are 80 conditions and **1,600 timed `ANALYZE` observations**.  The exact
schedule, raw stdout/stderr, and every observation are retained under
`measurement/raw/` and `measurement/raw-observations.json`.  All 2,400
nonempty metadata rows have the expected object name, requested target, a
non-null MCV payload, and a unique positive OID; the 200 empty-subset rows have
no candidate object.  The corrected analyzer also validates every unique
`(condition_id,repetition)` cell and per-repetition metadata cell.

The requested target-300 sample minimum is **90,000 rows** for a 200,000-row
table under the pinned PostgreSQL rule.  This is a requested minimum, not an
observed realized sample size.

## Data-regime identity

The new `weakassoc` table is not the historical modular fixture.  It uses
independent deterministic marginal streams with the same skewed marginal
construction for each attribute.  Exact pair diagnostics are:

| Regime | Pair | Distinct pairs | Cramer's V |
|---|---|---:|---:|
| weakassoc | ab | 5,041 | 0.01866 |
| weakassoc | bc | 5,041 | 0.01872 |
| weakassoc | cd | 5,041 | 0.01892 |
| correlated | ab | 100 | 1.00000 |
| correlated | bc | 394 | 0.16637 |
| correlated | cd | 200 | 0.70330 |

The historical v4 raw label `lowcorr` is therefore reclassified as a
functionally dependent/modular regime and is not used as weak-association
evidence.

## Median refresh times (ms)

The following are medians of the 20 timed command intervals; complete spreads
and raw values are in `analysis/analysis.json` and the raw JSON.

| Regime | Mode | Empty | ab | bc | cd | ab,bc | ab,cd | bc,cd | ab,bc,cd |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| weakassoc | uniform10 | 0.931 | 4.434 | 4.795 | 4.319 | 5.200 | 5.171 | 5.051 | 6.005 |
| weakassoc | uniform100 | 0.919 | 28.061 | 27.028 | 28.363 | 34.925 | 32.646 | 32.912 | 39.566 |
| weakassoc | uniform300 | 0.936 | 95.305 | 98.933 | 92.827 | 107.032 | 108.491 | 106.660 | 129.484 |
| weakassoc | mixed10/100/10 | 0.903 | 4.372 | 28.235 | 4.566 | 33.855 | 4.973 | 32.094 | 38.835 |
| weakassoc | mixed10/300/10 | 0.857 | 4.439 | 95.187 | 4.566 | 112.266 | 5.351 | 103.989 | 120.871 |
| correlated | uniform10 | 0.898 | 3.952 | 4.008 | 3.870 | 4.069 | 3.997 | 4.386 | 4.308 |
| correlated | uniform100 | 0.851 | 20.577 | 20.791 | 21.080 | 23.246 | 24.337 | 23.428 | 26.634 |
| correlated | uniform300 | 0.856 | 63.232 | 64.414 | 67.721 | 77.670 | 81.644 | 71.094 | 76.744 |
| correlated | mixed10/100/10 | 0.869 | 3.745 | 21.212 | 4.210 | 22.922 | 4.107 | 22.897 | 26.838 |
| correlated | mixed10/300/10 | 0.947 | 3.830 | 65.081 | 3.819 | 71.584 | 4.440 | 74.666 | 76.376 |

## Additivity error and uncertainty

For each fixed regime and target mode, the analysis computes

\[
C(M)=T(M)-T(\varnothing),\qquad
\widehat C(M)=\sum_{e\in M}C(\{e\}),\qquad
D(M)=\widehat C(M)-C(M).
\]

The block bootstrap resamples complete randomized repetition blocks and
recomputes all singleton medians, the current median, and the repeated baseline
term `(k-1)T(empty)` for every `D(M)`.  It is a descriptive interval under an
exchangeable-block assumption, not a formal significance test.

The aggregate table is regenerated from `analysis/analysis.json`; its
four-way summaries use the conventional median, including the arithmetic mean
of the two middle values.  The fixture metrics are independently rebuilt from
the preserved `fixture-metrics/psql.stdout.log`; the raw grouped output and raw
timing JSON are unchanged.

| Regime | Mode | Median absolute D (ms) | Max absolute D (ms) | Median error/uncertainty ratio | D intervals including zero |
|---|---|---:|---:|---:|---:|
| weakassoc | uniform10 | 3.115 | 5.681 | 5.09 | 0/4 |
| weakassoc | uniform100 | 22.209 | 42.048 | 4.09 | 0/4 |
| weakassoc | uniform300 | 85.217 | 155.709 | 4.75 | 0/4 |
| weakassoc | mixed10/100/10 | 2.606 | 3.470 | 0.52 | 3/4 |
| weakassoc | mixed10/300/10 | 9.295 | 18.392 | 1.24 | 1/4 |
| correlated | uniform10 | 2.959 | 5.726 | 5.91 | 0/4 |
| correlated | uniform100 | 17.432 | 34.112 | 6.71 | 0/4 |
| correlated | uniform300 | 54.652 | 116.910 | 6.16 | 0/4 |
| correlated | mixed10/100/10 | 1.411 | 2.979 | 0.61 | 2/4 |
| correlated | mixed10/300/10 | 4.580 | 6.714 | 0.35 | 3/4 |

Uniform-target additive overprediction increases in absolute milliseconds from
target 10 to 100 to 300 in both regimes, but this is an observed result of
these fixtures and timings, not a guarantee.  Mixed-target results are much
more variable: several D intervals include zero, while some weak-association
target-300 combinations exclude zero.  The report therefore does not infer a
universal target-scaling law or a universal additive-cost failure from every
condition.

## Provenance and cleanup

The source/build identity, exact command, private socket/port, and timing scope
are in `environment.md`.  The source is clean PostgreSQL `REL_16_14` commit
`0d1c00c624fa7367d4a895f44381887757289682`; no PostgreSQL or
`ess-postgresql` change was needed.  `cleanup-status.json` verifies that the
experiment-owned database was absent while the server was running, the server
stopped, and the temporary root was removed.

The raw observation SHA256 is recorded in `SHA256SUMS`; generated analysis and
provenance files are covered by the same manifest.  The physical measurement
remains scoped `ANALYZE` wall time.  It does not separate CPU, I/O, catalog
write, cache, or realized sample-row effects, and the additive proxy remains a
modeling approximation rather than a validated CPU-time law.
