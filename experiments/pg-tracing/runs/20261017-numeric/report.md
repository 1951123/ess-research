# PostgreSQL 16.14 fixed-snapshot MCV numeric validation

## Scope and status

This is the scoped runtime validation for Issue #5. It tests whether the
pre-clamp selectivity produced by compatible two-column MCV statistics can be
reconstructed from independently measured singleton and pair observations in
the controlled fixture. It is not a claim about all PostgreSQL queries, all
statistics configurations, or arbitrary DBMS estimators.

The valid run used PostgreSQL 16.14 built from the diagnostic branch commit
reported in [`environment.md`](environment.md). All original stdout, stderr,
server, initialization and shutdown logs are retained under
[`success-instrumented/`](success-instrumented/). The earlier failed and
uninstrumented attempts are retained under [`failed-initial/`](failed-initial/)
and the sibling `success/` directory and are not used as scientific input.

## Source observation point

The opt-in `ESS_MCV_NUMERIC_TRACE` instrumentation records two related events.

1. In the two-key MCV AND branch, it runs after `mcv_combine_selectivities()`
   and the existing `sel *= stat_sel` operation. It records the selected
   statistic OID, number of consumed clauses, `simple_sel`, `mcv_sel`,
   `mcv_basesel`, `mcv_totalsel`, and `stat_sel` with `%.17g`.
2. In `set_baserel_size_estimates()`, it records the target base relation OID,
   range-table index, `rel->tuples`, complete selectivity before row clamping,
   raw rows before `clamp_row_est()`, and final `rel->rows`.

Both traces are compiled only under `ESS_MCV_NUMERIC_TRACE` and require the
SQL marker in `debug_query_string`. The diagnostic code executes after the
estimator's existing calculations; it does not select statistics or alter the
computed values. The standard, macro-disabled estimator path was not run as a
separate comparison in this task, so the no-behavior-change conclusion is
source-grounded rather than a separately measured A/B result.

## Fixed input and catalog evidence

The fixture creates 100,000 deterministic rows with four identical integer
columns (`g % 10`), creates exactly three two-column MCV objects, sets all
targets to 100, and performs one `ANALYZE`. The valid run reported:

| Item | Observed value |
|---|---:|
| PostgreSQL | 16.14 |
| target relation OID | 16384 |
| `reltuples` / actual rows | 100000 / 100000 |
| `relpages` | 541 |
| `default_statistics_target` | 100 |
| `ess_num_ab` OID, keys | 16387, `1 2` |
| `ess_num_bc` OID, keys | 16388, `2 3` |
| `ess_num_cd` OID, keys | 16389, `3 4` |
| statistics kind and target | `{m}`, 100 for all three |
| MCV payload built | true for all three |
| MCV payload size | 366 bytes for all three |
| ordinary-statistics fingerprint | `67b46933d3b28b200e887b9fb210fc6e` |

The after-rollback catalog snapshot contains the same three OIDs, targets,
MCV-built flags and payload sizes. The ordinary-statistics fingerprint is the
same. Each availability transaction reports exactly one visible statistic for
the corresponding singleton scenario and zero for `none`; each transaction is
rolled back before the next scenario.

## Selection traces and maximality

The existing `ESS_MCV_TRACE` lines and the numeric traces identify the
following selections. Clause indices are zero-based in the four-clause full
query.

| Marker | Selected statistic OIDs | Claimed clause indices | Termination |
|---|---|---|---|
| `pair_ab` | 16387 (`ab`) | 0, 1 | no candidate |
| `pair_bc` | 16388 (`bc`) | 0, 1 in the pair query | no candidate |
| `pair_cd` | 16389 (`cd`) | 0, 1 in the pair query | no candidate |
| `full_all` | 16387 (`ab`), 16389 (`cd`) | 0, 1, 2, 3 | no candidate |
| `full_only_bc` | 16388 (`bc`) | 1, 2 | no candidate |
| `full_only_ab` | 16387 (`ab`) | 0, 1 | no candidate |
| `full_only_cd` | 16389 (`cd`) | 2, 3 | no candidate |
| `full_none` | none | none | no candidate |

The full eligible attribute graph is the path `a--b--c--d`. Thus `{ab,cd}`
and `{bc}` are matchings. `{ab,cd}` is maximal because the remaining edge
`bc` conflicts with both selected edges; `{bc}` is maximal because both
remaining edges conflict with it. The singleton-availability cases are
maximal in their one-edge selected graphs, and the empty matching is maximal
in the edgeless `none` graph. This is a fixture-level observation of the
matching property, not a universal characterization of PostgreSQL.

## Raw selectivity observations

The relation multiplier was `R = 100000` in every parsed base-relation event.
Values below are the full-precision decimal values parsed from the `%.17g`
trace; raw rows equal `R` times selectivity.

| Configuration | Selected MCV OIDs | Pre-clamp selectivity | Pre-clamp rows | Final Plan Rows |
|---|---|---:|---:|---:|
| `single_a` | none | 0.1009666696190834 | 10096.66696190834 | 10097 |
| `single_b` | none | 0.1009666696190834 | 10096.66696190834 | 10097 |
| `single_c` | none | 0.1009666696190834 | 10096.66696190834 | 10097 |
| `single_d` | none | 0.1009666696190834 | 10096.66696190834 | 10097 |
| `pair_ab` | 16387 | 0.10096666666666666 | 10096.666666666666 | 10097 |
| `pair_bc` | 16388 | 0.10096666666666666 | 10096.666666666666 | 10097 |
| `pair_cd` | 16389 | 0.10096666666666666 | 10096.666666666666 | 10097 |
| `full_all` | 16387, 16389 | 0.010194267777777778 | 1019.4267777777778 | 1019 |
| `full_only_bc` | 16388 | 0.0010292812968250842 | 102.92812968250843 | 103 |
| `full_only_ab` | 16387 | 0.0010292812968250842 | 102.92812968250843 | 103 |
| `full_only_cd` | 16389 | 0.0010292812968250842 | 102.92812968250843 | 103 |
| `full_none` | none | 0.00010392310768050742 | 10.392310768050741 | 10 |

The MCV numeric fields for each positive pair were identical:

```text
simple_sel     = 0.01019426837396914
mcv_sel        = 0.10096666666666666
mcv_basesel    = 0.010194267777777778
mcv_totalsel   = 1
stat_sel       = 0.10096666666666666
```

The pair `stat_sel` equals the independently reconstructed pair selectivity
for all three pairs at the recorded double precision. The singleton-to-pair
correction factor is

```text
r_ab = r_bc = r_cd = 9.904258252066724
```

The fixed snapshot makes these factors comparable within this fixture; it
does not by itself prove multiplicative separability for arbitrary compatible
statistics.

## Multiplicative reconstruction

The parser uses only pre-clamp values. It does not use final Plan Rows as
factors. For each positive full-query scenario, the predictions were:

| Scenario | Prediction | Actual | Absolute deviation | Relative deviation | Log residual |
|---|---:|---:|---:|---:|---:|
| `full_all`: `pair_ab * pair_cd` | 0.010194267777777778 | 0.010194267777777778 | 0 | 0 | 0 |
| `full_only_bc`: `pair_bc * single_a * single_d` | 0.0010292812968250842 | 0.0010292812968250842 | 0 | 0 | 0 |
| `full_only_ab`: `pair_ab * single_c * single_d` | 0.0010292812968250842 | 0.0010292812968250842 | 0 | 0 | 0 |
| `full_only_cd`: `pair_cd * single_a * single_b` | 0.0010292812968250842 | 0.0010292812968250842 | 0 | 0 | 0 |
| `full_none`: `single_a * single_b * single_c * single_d` | 0.00010392310768050742 | 0.00010392310768050742 | 0 | 0 | 0 |

Reconstructing `full_all` from the all-singleton baseline and the two fixed
correction factors gives `0.01019426777777778`; its difference from the
actual value is `-1.734723475976807e-18` and its log residual is zero in the
recorded double-precision calculation. Thus the positive fixture supports the
pre-clamp factorization to floating-point precision.

The corresponding raw-row predictions are exactly the observed raw rows in
the parsed double values. Applying PostgreSQL's final row transformation only
after composition gives 1019, 103, 103, 103 and 10, respectively. The
displayed `Plan Rows` in stdout agrees with each post-clamp trace.

## Boundary cases

The rare-value controls intentionally produce zero raw selectivity:

| Configuration | Raw selectivity | Raw rows | Final Plan Rows |
|---|---:|---:|---:|
| `single_a_rare` | 0 | 0 | 1 |
| `pair_ab_rare` | 0 | 0 | 1 |

The pair numeric trace reports `mcv_sel=0`, `mcv_basesel=0`,
`mcv_totalsel=1`, and `stat_sel=0`. No negative or nonfinite selectivity was
observed. Because the raw value is zero, no logarithmic factor or log residual
is formed for this boundary case; replacing it with an epsilon would be an
unsupported alteration of the model.

## Assessment

For the positive fixed-snapshot path fixture, the observed PostgreSQL
pre-clamp base-relation selectivities exactly reproduce the singleton/pair
composition identities at the available double precision. The final integer
row values are consistent with applying clamping and rounding after the raw
composition, not with multiplying the displayed Plan Rows.

The evidence does **not** establish that this factorization holds for all
queries, all MCV payloads, non-disjoint statistics, zero-selectivity tasks,
other estimator branches, or future data snapshots. It also does not identify
all internal policy choices beyond the trace records in this fixture. A
broader calibration matrix remains a separate follow-up.

## Evidence files

- Fixture SQL: [`mcv_numeric_snapshot.sql`](../../mcv_numeric_snapshot.sql)
- Offline parser: [`analyze_mcv_numeric.py`](../../analyze_mcv_numeric.py)
- Valid raw stdout: [`success-instrumented/psql.stdout.log`](success-instrumented/psql.stdout.log)
- Valid raw stderr: [`success-instrumented/psql.stderr.log`](success-instrumented/psql.stderr.log)
- Valid numeric analysis: [`success-instrumented/numeric-analysis.json`](success-instrumented/numeric-analysis.json)
- Initial failed attempt logs: [`failed-initial/`](failed-initial/)

The valid stderr SHA256 is
`1a90c60ca90b1fc9f23b51b1ca9de05032a9ef454544c1f02d439a765b2df44e`; valid
stdout is
`15ca79dc55d5b8723b8452b35162d2658b3d8213789b8a0fb95da1277fe2dac0`; and
the parsed analysis is
`d96bbce975f9192bc336d157e2c3cafbd6706e57d8c71d72d9a12ff309dcbcb1`.
