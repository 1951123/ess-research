# PostgreSQL 16.14 ANALYZE maintenance-cost analysis

This report uses the median of seven timed refreshes per condition.  IQR and MAD are retained; a relative incremental error is omitted when the observed increment is within the documented descriptive noise screen.

## Additive proxy comparisons

| Regime | Targets | Set | T(M) median ms | Additive predicted ms | Delta error ms | Relative delta error | Noise screen |
|---|---|---|---:|---:|---:|---:|---|
| correlated | mixed_10_100_10 | ab,bc | 23.714 | 25.396 | 1.682 | 0.0736 | no |
| correlated | mixed_10_100_10 | ab,cd | 3.915 | 6.949 | 3.034 | 0.9889 | no |
| correlated | mixed_10_100_10 | bc,cd | 23.886 | 25.206 | 1.320 | 0.0573 | no |
| correlated | mixed_10_100_10 | ab,bc,cd | 26.288 | 28.352 | 2.064 | 0.0811 | no |
| correlated | uniform10 | ab,bc | 4.164 | 6.491 | 2.327 | 0.7189 | no |
| correlated | uniform10 | ab,cd | 4.077 | 6.767 | 2.690 | 0.8540 | no |
| correlated | uniform10 | bc,cd | 4.030 | 6.845 | 2.815 | 0.9072 | no |
| correlated | uniform10 | ab,bc,cd | 4.237 | 9.588 | 5.351 | 1.6166 | no |
| correlated | uniform100 | ab,bc | 23.704 | 42.963 | 19.259 | 0.8432 | no |
| correlated | uniform100 | ab,cd | 24.033 | 43.051 | 19.018 | 0.8208 | no |
| correlated | uniform100 | bc,cd | 26.019 | 42.298 | 16.279 | 0.6471 | no |
| correlated | uniform100 | ab,bc,cd | 29.045 | 63.724 | 34.679 | 1.2306 | no |
| lowcorr | mixed_10_100_10 | ab,bc | 32.105 | 31.687 | -0.418 | -0.0134 | no |
| lowcorr | mixed_10_100_10 | ab,cd | 4.693 | 7.827 | 3.134 | 0.8326 | no |
| lowcorr | mixed_10_100_10 | bc,cd | 32.185 | 31.541 | -0.644 | -0.0206 | no |
| lowcorr | mixed_10_100_10 | ab,bc,cd | 35.747 | 35.063 | -0.684 | -0.0196 | no |
| lowcorr | uniform10 | ab,bc | 4.794 | 7.397 | 2.603 | 0.6602 | no |
| lowcorr | uniform10 | ab,cd | 4.418 | 7.550 | 3.132 | 0.8780 | no |
| lowcorr | uniform10 | bc,cd | 4.860 | 7.470 | 2.610 | 0.6510 | no |
| lowcorr | uniform10 | ab,bc,cd | 5.092 | 10.783 | 5.691 | 1.3419 | no |
| lowcorr | uniform100 | ab,bc | 31.719 | 54.918 | 23.199 | 0.7543 | no |
| lowcorr | uniform100 | ab,cd | 32.255 | 55.885 | 23.630 | 0.7551 | no |
| lowcorr | uniform100 | bc,cd | 32.123 | 56.431 | 24.308 | 0.7801 | no |
| lowcorr | uniform100 | ab,bc,cd | 36.527 | 83.136 | 46.609 | 1.3105 | no |

## Interpretation

The additive proxy is \hat{C}(M)=sum_e [T({e})-T(empty)] using condition medians within the same regime and target mode.  Raw T(M) values must be considered alongside delta errors because small or negative increments can be dominated by timing noise.  The benchmark does not observe the realized sample count and does not establish a universal PostgreSQL cost law.
