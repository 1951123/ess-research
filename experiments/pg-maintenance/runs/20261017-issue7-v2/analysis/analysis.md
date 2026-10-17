# PostgreSQL 16.14 ANALYZE maintenance-cost analysis

This report uses the median of seven timed refreshes per condition.  IQR and MAD are retained; a relative incremental error is omitted when the observed increment is within the documented descriptive noise screen.

## Additive proxy comparisons

| Regime | Targets | Set | T(M) median ms | Additive predicted ms | Delta error ms | Relative delta error | Noise screen |
|---|---|---|---:|---:|---:|---:|---|
| correlated | mixed_10_100_10 | ab,bc | 22.902 | 25.081 | 2.179 | 0.0988 | no |
| correlated | mixed_10_100_10 | ab,cd | 4.384 | 7.094 | 2.710 | 0.7679 | no |
| correlated | mixed_10_100_10 | bc,cd | 24.902 | 25.472 | 0.570 | 0.0237 | no |
| correlated | mixed_10_100_10 | ab,bc,cd | 25.296 | 28.396 | 3.100 | 0.1268 | no |
| correlated | uniform10 | ab,bc | 3.855 | 6.682 | 2.827 | 0.9752 | no |
| correlated | uniform10 | ab,cd | 4.070 | 6.393 | 2.323 | 0.7460 | no |
| correlated | uniform10 | bc,cd | 4.067 | 6.615 | 2.548 | 0.8190 | no |
| correlated | uniform10 | ab,bc,cd | 4.123 | 9.367 | 5.244 | 1.6558 | no |
| correlated | uniform100 | ab,bc | 23.329 | 41.888 | 18.559 | 0.8275 | no |
| correlated | uniform100 | ab,cd | 22.756 | 41.796 | 19.040 | 0.8712 | no |
| correlated | uniform100 | bc,cd | 23.634 | 43.125 | 19.491 | 0.8574 | no |
| correlated | uniform100 | ab,bc,cd | 25.776 | 62.954 | 37.178 | 1.4946 | no |
| lowcorr | mixed_10_100_10 | ab,bc | 33.064 | 31.411 | -1.653 | -0.0513 | no |
| lowcorr | mixed_10_100_10 | ab,cd | 4.608 | 7.398 | 2.790 | 0.7468 | no |
| lowcorr | mixed_10_100_10 | bc,cd | 32.166 | 31.357 | -0.809 | -0.0259 | no |
| lowcorr | mixed_10_100_10 | ab,bc,cd | 35.889 | 34.647 | -1.242 | -0.0355 | no |
| lowcorr | uniform10 | ab,bc | 4.588 | 7.385 | 2.797 | 0.7572 | no |
| lowcorr | uniform10 | ab,cd | 4.614 | 7.504 | 2.890 | 0.7769 | no |
| lowcorr | uniform10 | bc,cd | 4.785 | 7.551 | 2.766 | 0.7109 | no |
| lowcorr | uniform10 | ab,bc,cd | 4.901 | 10.773 | 5.872 | 1.4654 | no |
| lowcorr | uniform100 | ab,bc | 31.744 | 55.935 | 24.191 | 0.7825 | no |
| lowcorr | uniform100 | ab,cd | 32.751 | 55.170 | 22.419 | 0.7023 | no |
| lowcorr | uniform100 | bc,cd | 31.991 | 56.367 | 24.376 | 0.7823 | no |
| lowcorr | uniform100 | ab,bc,cd | 35.695 | 83.321 | 47.626 | 1.3660 | no |

## Interpretation

The additive proxy is \hat{C}(M)=sum_e [T({e})-T(empty)] using condition medians within the same regime and target mode.  Raw T(M) values must be considered alongside delta errors because small or negative increments can be dominated by timing noise.  The benchmark does not observe the realized sample count and does not establish a universal PostgreSQL cost law.
