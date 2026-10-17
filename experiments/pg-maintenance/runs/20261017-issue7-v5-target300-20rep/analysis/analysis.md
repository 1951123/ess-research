# PostgreSQL 16.14 ANALYZE maintenance-cost analysis

This report uses 20 separately timed post-warm-up refreshes per condition. The central estimate is the condition median; randomized repetition blocks are resampled for a descriptive interval for D(M). This is not a formal significance test.

## Additive proxy comparisons

| Regime | Targets | Set | T(M) median ms | Additive predicted ms | Signed D ms | Relative D | D interval ms | Includes zero | Error/uncertainty | Increment screen |
|---|---|---|---:|---:|---:|---:|---|---|---:|---|
| correlated | mixed_10_100_10 | ab,bc | 22.922 | 24.088 | 1.165 | 0.0528 | [-0.014, 4.570] | yes | 0.51 | detectable |
| correlated | mixed_10_100_10 | ab,cd | 4.107 | 7.086 | 2.979 | 0.9202 | [2.584, 3.936] | no | 4.41 | detectable |
| correlated | mixed_10_100_10 | bc,cd | 22.897 | 24.553 | 1.657 | 0.0752 | [0.801, 5.433] | no | 0.72 | detectable |
| correlated | mixed_10_100_10 | ab,bc,cd | 26.838 | 27.429 | 0.590 | 0.0227 | [-2.276, 5.272] | yes | 0.16 | detectable |
| correlated | mixed_10_300_10 | ab,bc | 71.584 | 67.963 | -3.620 | -0.0512 | [-13.756, 20.823] | yes | 0.21 | detectable |
| correlated | mixed_10_300_10 | ab,cd | 4.440 | 6.702 | 2.262 | 0.6477 | [1.326, 2.711] | no | 3.27 | detectable |
| correlated | mixed_10_300_10 | bc,cd | 74.666 | 67.953 | -6.713 | -0.0911 | [-15.277, 19.528] | yes | 0.39 | detectable |
| correlated | mixed_10_300_10 | ab,bc,cd | 76.376 | 70.836 | -5.540 | -0.0734 | [-16.093, 18.551] | yes | 0.32 | detectable |
| correlated | uniform10 | ab,bc | 4.069 | 7.061 | 2.992 | 0.9432 | [2.462, 3.573] | no | 5.38 | detectable |
| correlated | uniform10 | ab,cd | 3.997 | 6.923 | 2.927 | 0.9443 | [2.386, 3.297] | no | 6.43 | detectable |
| correlated | uniform10 | bc,cd | 4.386 | 6.979 | 2.594 | 0.7435 | [1.987, 3.377] | no | 3.73 | detectable |
| correlated | uniform10 | ab,bc,cd | 4.308 | 10.033 | 5.726 | 1.6793 | [5.220, 6.332] | no | 10.30 | detectable |
| correlated | uniform100 | ab,bc | 23.246 | 40.517 | 17.271 | 0.7712 | [15.335, 21.505] | no | 5.60 | detectable |
| correlated | uniform100 | ab,cd | 24.337 | 40.805 | 16.468 | 0.7012 | [10.324, 20.362] | no | 3.28 | detectable |
| correlated | uniform100 | bc,cd | 23.428 | 41.020 | 17.592 | 0.7792 | [16.454, 19.906] | no | 10.20 | detectable |
| correlated | uniform100 | ab,bc,cd | 26.634 | 60.745 | 34.111 | 1.3230 | [29.691, 38.405] | no | 7.83 | detectable |
| correlated | uniform300 | ab,bc | 77.670 | 126.790 | 49.120 | 0.6395 | [43.391, 60.922] | no | 5.60 | detectable |
| correlated | uniform300 | ab,cd | 81.644 | 130.096 | 48.452 | 0.5997 | [33.002, 59.618] | no | 3.64 | detectable |
| correlated | uniform300 | bc,cd | 71.094 | 131.278 | 60.184 | 0.8569 | [51.248, 69.183] | no | 6.71 | detectable |
| correlated | uniform300 | ab,bc,cd | 76.744 | 193.654 | 116.910 | 1.5405 | [109.187, 127.454] | no | 12.80 | detectable |
| weakassoc | mixed_10_100_10 | ab,bc | 33.855 | 31.703 | -2.152 | -0.0653 | [-7.929, 4.747] | yes | 0.34 | detectable |
| weakassoc | mixed_10_100_10 | ab,cd | 4.973 | 8.034 | 3.061 | 0.7521 | [2.683, 3.592] | no | 6.74 | detectable |
| weakassoc | mixed_10_100_10 | bc,cd | 32.094 | 31.897 | -0.197 | -0.0063 | [-3.643, 6.296] | yes | 0.04 | detectable |
| weakassoc | mixed_10_100_10 | ab,bc,cd | 38.835 | 35.365 | -3.470 | -0.0915 | [-6.684, 3.211] | yes | 0.70 | detectable |
| weakassoc | mixed_10_300_10 | ab,bc | 112.266 | 98.769 | -13.497 | -0.1211 | [-31.976, -1.188] | no | 0.88 | detectable |
| weakassoc | mixed_10_300_10 | ab,cd | 5.351 | 8.149 | 2.797 | 0.6224 | [2.294, 3.627] | no | 4.20 | detectable |
| weakassoc | mixed_10_300_10 | bc,cd | 103.989 | 98.897 | -5.092 | -0.0494 | [-15.508, 6.893] | yes | 0.45 | detectable |
| weakassoc | mixed_10_300_10 | ab,bc,cd | 120.871 | 102.479 | -18.392 | -0.1532 | [-29.083, -6.130] | no | 1.60 | detectable |
| weakassoc | uniform10 | ab,bc | 5.200 | 8.299 | 3.098 | 0.7257 | [2.553, 3.866] | no | 4.72 | detectable |
| weakassoc | uniform10 | ab,cd | 5.171 | 7.822 | 2.651 | 0.6252 | [2.336, 3.360] | no | 5.18 | detectable |
| weakassoc | uniform10 | bc,cd | 5.051 | 8.183 | 3.131 | 0.7600 | [2.546, 3.798] | no | 5.01 | detectable |
| weakassoc | uniform10 | ab,bc,cd | 6.005 | 11.686 | 5.681 | 1.1195 | [5.133, 6.375] | no | 9.15 | detectable |
| weakassoc | uniform100 | ab,bc | 34.925 | 54.169 | 19.245 | 0.5659 | [15.436, 24.811] | no | 4.11 | detectable |
| weakassoc | uniform100 | ab,cd | 32.646 | 55.505 | 22.858 | 0.7205 | [14.014, 30.007] | no | 2.86 | detectable |
| weakassoc | uniform100 | bc,cd | 32.912 | 54.471 | 21.559 | 0.6739 | [16.759, 27.336] | no | 4.08 | detectable |
| weakassoc | uniform100 | ab,bc,cd | 39.566 | 81.613 | 42.047 | 1.0880 | [37.108, 49.251] | no | 6.93 | detectable |
| weakassoc | uniform300 | ab,bc | 107.032 | 193.302 | 86.269 | 0.8131 | [52.843, 101.452] | no | 3.55 | detectable |
| weakassoc | uniform300 | ab,cd | 108.491 | 187.196 | 78.705 | 0.7318 | [61.417, 90.701] | no | 5.38 | detectable |
| weakassoc | uniform300 | bc,cd | 106.660 | 190.824 | 84.164 | 0.7961 | [55.213, 95.969] | no | 4.13 | detectable |
| weakassoc | uniform300 | ab,bc,cd | 129.484 | 285.192 | 155.708 | 1.2113 | [126.737, 169.133] | no | 7.35 | detectable |

## Programmatic aggregate summaries

The following summaries are computed from the complete comparison rows. All medians use the conventional median, including the arithmetic mean of the two middle values when there are four comparisons.

| Regime | Targets | Comparisons | Median absolute D ms | Max absolute D ms | Median error/uncertainty | D intervals including zero |
|---|---|---:|---:|---:|---:|---:|
| correlated | mixed_10_100_10 | 4 | 1.41100 | 2.97900 | 0.61190 | 2/4 |
| correlated | mixed_10_300_10 | 4 | 4.57975 | 6.71350 | 0.35279 | 3/4 |
| correlated | uniform10 | 4 | 2.95900 | 5.72550 | 5.90658 | 0/4 |
| correlated | uniform100 | 4 | 17.43150 | 34.11150 | 6.71404 | 0/4 |
| correlated | uniform300 | 4 | 54.65200 | 116.91000 | 6.15765 | 0/4 |
| weakassoc | mixed_10_100_10 | 4 | 2.60625 | 3.47000 | 0.52043 | 3/4 |
| weakassoc | mixed_10_300_10 | 4 | 9.29450 | 18.39200 | 1.23966 | 1/4 |
| weakassoc | uniform10 | 4 | 3.11500 | 5.68100 | 5.09327 | 0/4 |
| weakassoc | uniform100 | 4 | 22.20900 | 42.04750 | 4.09118 | 0/4 |
| weakassoc | uniform300 | 4 | 85.21675 | 155.70850 | 4.75267 | 0/4 |

## Interpretation

The additive proxy is Ĉ(M)=sum_e[T({e})-T(empty)] using medians within the same regime and target mode. The model discrepancy is D(M)=Ĉ(M)-C(M), not C(M) itself. The block bootstrap preserves complete randomized repetition blocks when recomputing all contributing medians; it does not establish a formal significance level. The benchmark measures scoped ANALYZE wall-clock time, does not observe realized sample rows, and does not establish a universal PostgreSQL CPU-cost law.
