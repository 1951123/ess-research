# Initial failed attempt annotation

The SQL stopped before the measurement section because the ordinary-statistics
fingerprint query used column names from a different catalog interface
(`most_common_vals`, `most_common_freqs`, and `histogram_bounds`). PostgreSQL
16.14 exposes the relevant `pg_statistic` slots as `stavalues1`,
`stanumbers1`, and `stakind1`. No numeric measurement cell was accepted from
this attempt. The original stdout, stderr, server and shutdown logs are kept
unchanged.
