# PostgreSQL 16.14 ANALYZE maintenance-cost analysis

This report uses 7 separately timed post-warm-up refreshes per condition. The central estimate is the condition median; randomized repetition blocks are resampled for a descriptive interval for D(M). This is not a formal significance test.

## Additive proxy comparisons

| Regime | Targets | Set | T(M) median ms | Additive predicted ms | Signed D ms | Relative D | D interval ms | Includes zero | Error/uncertainty | Increment screen |
|---|---|---|---:|---:|---:|---:|---|---|---:|---|
| correlated | mixed_10_100_10 | ab,bc | 23.341 | 24.950 | 1.609 | 0.0715 | [0.959, 2.804] | no | 1.74 | detectable |
| correlated | mixed_10_100_10 | ab,cd | 3.935 | 6.602 | 2.667 | 0.8651 | [2.240, 3.076] | no | 6.38 | detectable |
| correlated | mixed_10_100_10 | bc,cd | 23.869 | 24.848 | 0.979 | 0.0425 | [0.086, 1.893] | no | 1.08 | detectable |
| correlated | mixed_10_100_10 | ab,bc,cd | 25.641 | 27.774 | 2.133 | 0.0860 | [1.739, 2.748] | no | 4.23 | detectable |
| correlated | uniform10 | ab,bc | 4.147 | 6.526 | 2.379 | 0.7207 | [2.082, 3.085] | no | 4.74 | detectable |
| correlated | uniform10 | ab,cd | 4.022 | 6.681 | 2.659 | 0.8372 | [2.554, 3.313] | no | 7.01 | detectable |
| correlated | uniform10 | bc,cd | 4.136 | 6.835 | 2.699 | 0.8204 | [2.442, 2.997] | no | 9.73 | detectable |
| correlated | uniform10 | ab,bc,cd | 4.336 | 9.598 | 5.262 | 1.5077 | [3.901, 5.833] | no | 5.45 | detectable |
| correlated | uniform100 | ab,bc | 22.924 | 42.386 | 19.462 | 0.8843 | [17.649, 21.821] | no | 9.33 | detectable |
| correlated | uniform100 | ab,cd | 22.684 | 42.883 | 20.199 | 0.9279 | [18.891, 20.752] | no | 21.71 | detectable |
| correlated | uniform100 | bc,cd | 23.997 | 42.581 | 18.584 | 0.8052 | [17.181, 20.820] | no | 10.21 | detectable |
| correlated | uniform100 | ab,bc,cd | 25.621 | 63.467 | 37.846 | 1.5319 | [36.426, 40.370] | no | 19.19 | detectable |
| lowcorr | mixed_10_100_10 | ab,bc | 28.838 | 29.546 | 0.708 | 0.0253 | [0.141, 1.758] | no | 0.88 | detectable |
| lowcorr | mixed_10_100_10 | ab,cd | 4.443 | 7.754 | 3.311 | 0.9295 | [2.748, 3.570] | no | 8.06 | detectable |
| lowcorr | mixed_10_100_10 | bc,cd | 29.521 | 29.957 | 0.436 | 0.0152 | [-0.376, 2.028] | yes | 0.36 | detectable |
| lowcorr | mixed_10_100_10 | ab,bc,cd | 32.043 | 33.188 | 1.145 | 0.0367 | [-0.041, 1.753] | yes | 1.28 | detectable |
| lowcorr | uniform10 | ab,bc | 4.529 | 7.390 | 2.861 | 0.7774 | [2.281, 3.677] | no | 4.10 | detectable |
| lowcorr | uniform10 | ab,cd | 4.297 | 7.089 | 2.792 | 0.8097 | [2.338, 3.213] | no | 6.38 | detectable |
| lowcorr | uniform10 | bc,cd | 4.420 | 7.240 | 2.820 | 0.7897 | [2.404, 3.831] | no | 3.95 | detectable |
| lowcorr | uniform10 | ab,bc,cd | 4.801 | 10.435 | 5.634 | 1.4256 | [5.380, 6.650] | no | 8.87 | detectable |
| lowcorr | uniform100 | ab,bc | 28.435 | 51.509 | 23.074 | 0.8396 | [21.197, 23.633] | no | 18.94 | detectable |
| lowcorr | uniform100 | ab,cd | 29.047 | 51.513 | 22.466 | 0.7997 | [21.215, 23.889] | no | 16.81 | detectable |
| lowcorr | uniform100 | bc,cd | 28.970 | 51.634 | 22.664 | 0.8090 | [21.913, 24.339] | no | 18.68 | detectable |
| lowcorr | uniform100 | ab,bc,cd | 31.712 | 76.851 | 45.139 | 1.4676 | [43.290, 46.371] | no | 29.30 | detectable |

## Programmatic aggregate summaries

The following summaries are computed from the complete comparison rows. All medians use the conventional median, including the arithmetic mean of the two middle values when there are four comparisons.

| Regime | Targets | Comparisons | Median absolute D ms | Max absolute D ms | Median error/uncertainty | D intervals including zero |
|---|---|---:|---:|---:|---:|---:|
| correlated | mixed_10_100_10 | 4 | 1.87100 | 2.66700 | 2.98629 | 0/4 |
| correlated | uniform10 | 4 | 2.67900 | 5.26200 | 6.22690 | 0/4 |
| correlated | uniform100 | 4 | 19.83050 | 37.84600 | 14.70274 | 0/4 |
| lowcorr | mixed_10_100_10 | 4 | 0.92650 | 3.31100 | 1.07609 | 2/4 |
| lowcorr | uniform10 | 4 | 2.84050 | 5.63400 | 5.24028 | 0/4 |
| lowcorr | uniform100 | 4 | 22.86900 | 45.13900 | 18.81421 | 0/4 |

## Interpretation

The additive proxy is Ĉ(M)=sum_e[T({e})-T(empty)] using medians within the same regime and target mode. The model discrepancy is D(M)=Ĉ(M)-C(M), not C(M) itself. The block bootstrap preserves complete randomized repetition blocks when recomputing all contributing medians; it does not establish a formal significance level. The benchmark measures scoped ANALYZE wall-clock time, does not observe realized sample rows, and does not establish a universal PostgreSQL CPU-cost law.
