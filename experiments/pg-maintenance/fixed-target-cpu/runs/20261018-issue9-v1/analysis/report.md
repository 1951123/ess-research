# Issue #9 fixed-target PostgreSQL maintenance CPU analysis

This report uses the opt-in backend getrusage(RUSAGE_SELF) trace around the complete BuildRelationExtStatistics() phase. The psql round-trip measurements are retained in the raw artifact but are not the primary CPU evidence.

## Campaign validation

- Conditions: 32 (two regimes × two targets × eight subsets).
- Randomized repetition blocks: 20; timed observations: 640.
- Raw SHA256: 1aaf7d750c09d99958fc60f33528f014a9451a83007d66dc1c3ffaa2ed8e24b5.
- Environment and binary provenance: ../environment.json; checksums: ../SHA256SUMS.
- Cleanup evidence: ../cleanup-status.json; the database was absent while the private server was running and the server then stopped.
- Every cell has one warm-up and one timed CPU trace; metadata validates ordinary targets, MCV targets, payload presence, OIDs, and trace relation identity.
- Requested sample rows are source-derived as max(100, 300 * max(target)): 30,000 at target 100 and 90,000 at target 300. Realized sample rows were not claimed or measured. The fixed-target control therefore fixes the requested sampling target, not the actual realized tuple sample (S_t); standard ANALYZE sampling was not replaced by a captured-and-replayed sample.

## Independent singleton prediction

Signed error is predicted incremental CPU minus observed incremental CPU; positive values are additive overprediction. Bootstrap intervals resample complete randomized repetition blocks.

| Regime | Target | Subset | Baseline median us | Observed increment us | Predicted increment us | Signed error us | 95% block-bootstrap CI us | Relative error |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| weakassoc | 100 | ab+bc | 5.0 | 9901.5 | 10061.0 | 159.5 | [40.0, 319.5] | 0.01611 |
| weakassoc | 100 | ab+cd | 5.0 | 9980.0 | 10029.0 | 49.0 | [-186.0, 282.0] | 0.00491 |
| weakassoc | 100 | bc+cd | 5.0 | 9821.0 | 10021.0 | 200.0 | [44.5, 379.5] | 0.02036 |
| weakassoc | 100 | ab+bc+cd | 5.0 | 14999.0 | 15055.5 | 56.5 | [-101.0, 424.5] | 0.003767 |
| weakassoc | 300 | ab+bc | 7.0 | 30195.5 | 31559.5 | 1364.0 | [-562.4, 2581.0] | 0.04517 |
| weakassoc | 300 | ab+cd | 7.0 | 31251.0 | 31085.5 | -165.5 | [-1476.5, 2105.6] | -0.005296 |
| weakassoc | 300 | bc+cd | 7.0 | 30572.0 | 31907.0 | 1335.0 | [-9.6, 2688.0] | 0.04367 |
| weakassoc | 300 | ab+bc+cd | 7.0 | 43359.0 | 47276.0 | 3917.0 | [2884.4, 5365.1] | 0.09034 |
| correlated | 100 | ab+bc | 5.0 | 4483.5 | 4501.0 | 17.5 | [-99.5, 141.0] | 0.003903 |
| correlated | 100 | ab+cd | 5.0 | 4237.5 | 4400.5 | 163.0 | [38.5, 320.5] | 0.03847 |
| correlated | 100 | bc+cd | 5.0 | 4750.5 | 4951.5 | 201.0 | [-56.5, 305.5] | 0.04231 |
| correlated | 100 | ab+bc+cd | 5.0 | 6775.0 | 6926.5 | 151.5 | [-16.5, 320.0] | 0.02236 |
| correlated | 300 | ab+bc | 6.5 | 14364.5 | 15878.0 | 1513.5 | [563.5, 2791.5] | 0.1054 |
| correlated | 300 | ab+cd | 6.5 | 14404.5 | 15732.5 | 1328.0 | [460.4, 2272.5] | 0.09219 |
| correlated | 300 | bc+cd | 6.5 | 16511.5 | 17287.5 | 776.0 | [-603.1, 2318.5] | 0.047 |
| correlated | 300 | ab+bc+cd | 6.5 | 23198.0 | 24449.0 | 1251.0 | [-471.6, 3165.5] | 0.05393 |

Using a transparent descriptive tolerance of 10% relative error against the
observed incremental CPU (only where that denominator is nonzero), 15 of 16
comparisons are within the tolerance; correlated/target-300/ab+bc is the one
slightly above it at 10.54%. Six of 16 bootstrap intervals exclude zero. The
10% count is only a descriptive point estimate, not an equivalence confidence
statement: for example, the correlated/target-300/ab+bc bootstrap interval is
[563.5, 2791.5] us while its observed increment is 14364.5 us, so its upper
endpoint is about 19.4% of the observed increment. These counts are
fixture-scoped summaries, not an equivalence test or a claim that the other
ten intervals establish exact additivity.

## Interpretation boundary

The singleton construction is an independent prediction of whole-phase CPU medians; it does not add per-object timings from the same multi-object run. A confidence interval containing zero does not prove exact additivity, and an interval excluding zero is evidence only for the stated fixture, target, build, and horizon. The campaign does not measure future refreshes or establish a universal PostgreSQL maintenance law.

The fixed target controls ordinary-column and explicit MCV statistics targets.
The source-derived requested sample formula is a control invariant, not an
observation of the realized sample tuple count; consequently, this campaign
does not establish equivalence for a fixed realized reference sample.
