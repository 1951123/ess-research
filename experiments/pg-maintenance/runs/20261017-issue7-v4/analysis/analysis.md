# PostgreSQL 16.14 ANALYZE maintenance-cost analysis

This report uses the median of seven timed refreshes per condition.  IQR and MAD are retained; a relative incremental error is omitted when the observed increment is within the documented descriptive noise screen.

## Additive proxy comparisons

| Regime | Targets | Set | T(M) median ms | Additive predicted ms | Delta error ms | Relative delta error | Noise screen |
|---|---|---|---:|---:|---:|---:|---|
| correlated | mixed_10_100_10 | ab,bc | 23.341 | 24.950 | 1.609 | 0.0715 | no |
| correlated | mixed_10_100_10 | ab,cd | 3.935 | 6.602 | 2.667 | 0.8651 | no |
| correlated | mixed_10_100_10 | bc,cd | 23.869 | 24.848 | 0.979 | 0.0425 | no |
| correlated | mixed_10_100_10 | ab,bc,cd | 25.641 | 27.774 | 2.133 | 0.0860 | no |
| correlated | uniform10 | ab,bc | 4.147 | 6.526 | 2.379 | 0.7207 | no |
| correlated | uniform10 | ab,cd | 4.022 | 6.681 | 2.659 | 0.8372 | no |
| correlated | uniform10 | bc,cd | 4.136 | 6.835 | 2.699 | 0.8204 | no |
| correlated | uniform10 | ab,bc,cd | 4.336 | 9.598 | 5.262 | 1.5077 | no |
| correlated | uniform100 | ab,bc | 22.924 | 42.386 | 19.462 | 0.8843 | no |
| correlated | uniform100 | ab,cd | 22.684 | 42.883 | 20.199 | 0.9279 | no |
| correlated | uniform100 | bc,cd | 23.997 | 42.581 | 18.584 | 0.8052 | no |
| correlated | uniform100 | ab,bc,cd | 25.621 | 63.467 | 37.846 | 1.5319 | no |
| lowcorr | mixed_10_100_10 | ab,bc | 28.838 | 29.546 | 0.708 | 0.0253 | no |
| lowcorr | mixed_10_100_10 | ab,cd | 4.443 | 7.754 | 3.311 | 0.9295 | no |
| lowcorr | mixed_10_100_10 | bc,cd | 29.521 | 29.957 | 0.436 | 0.0152 | no |
| lowcorr | mixed_10_100_10 | ab,bc,cd | 32.043 | 33.188 | 1.145 | 0.0367 | no |
| lowcorr | uniform10 | ab,bc | 4.529 | 7.390 | 2.861 | 0.7774 | no |
| lowcorr | uniform10 | ab,cd | 4.297 | 7.089 | 2.792 | 0.8097 | no |
| lowcorr | uniform10 | bc,cd | 4.420 | 7.240 | 2.820 | 0.7897 | no |
| lowcorr | uniform10 | ab,bc,cd | 4.801 | 10.435 | 5.634 | 1.4256 | no |
| lowcorr | uniform100 | ab,bc | 28.435 | 51.509 | 23.074 | 0.8396 | no |
| lowcorr | uniform100 | ab,cd | 29.047 | 51.513 | 22.466 | 0.7997 | no |
| lowcorr | uniform100 | bc,cd | 28.970 | 51.634 | 22.664 | 0.8090 | no |
| lowcorr | uniform100 | ab,bc,cd | 31.712 | 76.851 | 45.139 | 1.4676 | no |

## Interpretation

The additive proxy is \hat{C}(M)=sum_e [T({e})-T(empty)] using condition medians within the same regime and target mode.  Raw T(M) values must be considered alongside delta errors because small or negative increments can be dominated by timing noise.  The benchmark does not observe the realized sample count and does not establish a universal PostgreSQL cost law.
