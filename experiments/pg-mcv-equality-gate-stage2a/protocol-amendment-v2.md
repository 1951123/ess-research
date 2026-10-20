# Protocol amendment v2

The first full execution used the committed v1 manifest and target 1000 for
all columns. PostgreSQL 16.14 produced 1000 MCV items for the intended
high-cardinality `(e,f)` control, so that run did not execute a no-MCV control.
The v1 observations and hash are retained and are not overwritten.

Before rerunning the matrix, an Issue-owned control probe dropped and
recreated `e45`, set its extended-statistics target to 0, ran `ANALYZE`, and
observed `stxstattarget=0` with `stxdmcv IS NULL`. This amendment records that
explicit mechanism as the v2 input. No positive-gate query, candidate order,
or matching outcome was selected based on an observed result; the full v1
matrix remains the first-run baseline.

The amended manifest adds `statistics_target: 0` only to `e45` and changes its
runner command to apply that setting immediately after creating the object and
before `ANALYZE`. The corrected full run uses a fresh runtime root and a new
result hash.
