# Issue #7 — PostgreSQL 16.14 ANALYZE maintenance cost

## Scope and evidence status

This is the final valid historical run for Issue #7.  It measures refresh-only
wall time for two deterministic 200,000-row tables.  The raw `lowcorr` label is
now explicitly interpreted as a **functionally dependent/modular** regime,
not a weak-association regime; its four columns are affine functions of
`g mod 100`.  The second table is the correlated/skewed regime.  Both have
three two-column MCV objects (`ab`, `bc`, `cd`).  Every one of the eight
subsets, two uniform target regimes (10 and 100), and the mixed target regime
`ab=10, bc=100, cd=10` was tested.  There are 48 conditions and seven timed
refreshes per condition: **336 timed `ANALYZE` observations**.

The raw observations are in `measurement/raw-observations.json`; the original
`psql` stdout/stderr and exact generated schedule are in `measurement/raw/`.
The offline analysis is reproducible from that JSON and is in `analysis/`.
The v1 startup failure, v2 pre-warm-up metadata defect, and v3 no-MCV fixture
are retained with explicit notes and are not included in this result.  The v4
raw evidence is unchanged; corrected D(M) uncertainty is in `analysis/`.

## Matrix and payload validation

The final raw JSON reports 48 conditions and 336 unique
`(condition, repetition)` cells.  It contains 546 post-warm-up metadata rows:
504 object rows and 42 explicit empty-subset rows.  All 504 nonempty rows have
the expected object name, target, distinct OID, and non-null MCV payload.  The
42 empty rows contain no candidate statistic object.  OIDs are evidence of
object identity within the disposable run, not an experimental decision
variable.

## Raw timing result

`T(M)` below means the median of the seven timed command intervals in the same
regime and target condition.  IQR and MAD for every condition are retained in
`analysis/analysis.json`; the complete per-run values remain in the raw JSON.

| Regime | Target mode | Empty | ab | bc | cd | ab,bc | ab,cd | bc,cd | ab,bc,cd |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| modular-dependent (raw: lowcorr) | uniform10 | 0.849 | 4.044 | 4.195 | 3.894 | 4.529 | 4.297 | 4.420 | 4.801 |
| modular-dependent (raw: lowcorr) | uniform100 | 0.954 | 26.171 | 26.292 | 26.296 | 28.435 | 29.047 | 28.970 | 31.712 |
| modular-dependent (raw: lowcorr) | mixed10/100/10 | 0.881 | 4.112 | 26.315 | 4.523 | 28.838 | 4.443 | 29.521 | 32.043 |
| correlated | uniform10 | 0.846 | 3.609 | 3.763 | 3.918 | 4.147 | 4.022 | 4.136 | 4.336 |
| correlated | uniform100 | 0.916 | 21.802 | 21.500 | 21.997 | 22.924 | 22.684 | 23.997 | 25.621 |
| correlated | mixed10/100/10 | 0.852 | 3.778 | 22.024 | 3.676 | 23.341 | 3.935 | 23.869 | 25.641 |

The table is wall-time in milliseconds.  The modular and correlated tables had
identical measured sizes, but their MCV construction times differ, so data
distribution matters in this controlled instance.  This historical run does
not establish a weak-versus-high-association comparison.

## Additive proxy calculation

For each fixed regime and target mode, the calculation is exactly:

\[
C(M)=T(M)-T(\varnothing),\qquad
\widehat C(M)=\sum_{e\in M}C(\{e\}),\qquad
\widehat T(M)=T(\varnothing)+\widehat C(M).
\]

The full 24 multi-object comparisons, including absolute and relative errors,
are in `analysis/analysis.md` and `analysis/analysis.json`. Selected aggregate
results (absolute incremental error is `|Ĉ-C|`) are:

| Regime | Target mode | Median absolute error (ms) | Maximum absolute error (ms) | Median absolute relative error |
|---|---|---:|---:|---:|
| modular-dependent (raw: lowcorr) | uniform10 | 2.841 | 5.634 | 0.800 |
| modular-dependent (raw: lowcorr) | uniform100 | 22.869 | 45.139 | 0.824 |
| modular-dependent (raw: lowcorr) | mixed10/100/10 | 0.927 | 3.311 | 0.031 |
| correlated | uniform10 | 2.679 | 5.262 | 0.829 |
| correlated | uniform100 | 19.831 | 37.846 | 0.906 |
| correlated | mixed10/100/10 | 1.871 | 2.667 | 0.079 |

The earlier `noise_dominated` screen has been withdrawn: it tested whether
`|C(M)|` exceeded a scale based only on the current and empty spreads, rather
than uncertainty in the additive-model discrepancy.  The corrected analyzer
reports `D(M)=sum_e T({e})-T(M)-(k-1)T(empty)` and block-resamples the seven
randomized repetition blocks, recomputing all singleton and baseline medians.
Its interval and `includes_zero` flag are descriptive and are not a formal
significance test.  For example, the raw-label `lowcorr` mixed target
`{bc,cd}` has `D=0.436 ms` and a corrected 95% descriptive interval that
includes zero.  The raw IQR/MAD and all seven values remain retained.

The uniform-target cases show substantial overprediction by the singleton
additive proxy: pair predictions are around 6--7 ms at target 10 versus
observed 4--5 ms, and around 42--52 ms at target 100 versus observed about
22--29 ms.  Triple predictions are also much larger than observed.  In the
mixed-target cases, combinations containing the target-100 `bc` object are
closer, while the low-target `ab+cd` combination remains overpredicted by
about 2.7--3.3 ms.  These observations are compatible with shared per-refresh
work and a max-target-driven sample request, but timing alone does not isolate
causality.  They do not establish universal physical nonadditivity or a bound
for another PostgreSQL version.

## Source versus observation

The max-target sampling rule is **source-derived** from pinned PostgreSQL
16.14.  The six-row timing table, the payload/OID checks, and the additive
errors are **experimentally observed** for this fixture and environment.  The
requested minima (300, 3,000, and 30,000) are not reported as realized sample
counts.  No `ANALYZE VERBOSE` row count was misinterpreted as a sample size.

The benchmark measured client-observed command wall time, not CPU seconds.
The PostgreSQL maintenance proxy in the paper is therefore not calibrated by
this run as a CPU-cost model.  It is only an initial wall-time additivity
diagnostic under an isolated, warm-cache-prone environment.

## Cleanup and limitations

`cleanup-status.json` confirms that the owned database was absent while the
server was still running, the server stopped, and the temporary root was
removed.  No PostgreSQL source file or `ess-postgresql` branch was changed;
the clean upstream binary was sufficient, so no companion PostgreSQL Draft PR
is needed.

Remaining limitations are: no controlled cold-cache comparison; no realized
sample-row instrumentation; no separation of CPU time, I/O, and catalog write
cost; one host and PostgreSQL 16.14; two synthetic distributions; and a
descriptive block bootstrap rather than a formal inferential model.  The
corrected weak-association and target-scaling evidence is in the separate v5
run on this PR.
The next physical-cost step should calibrate CPU components separately before
using them as the scalar maintenance budget.
