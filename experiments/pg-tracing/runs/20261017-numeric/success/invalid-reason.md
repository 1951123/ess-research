# Invalid run annotation

This run completed the SQL fixture but was not a valid numeric observation.
The temporary build was created from the PostgreSQL branch `HEAD` before the
uncommitted numeric instrumentation diff had been applied to that worktree.
Consequently its stderr contains the pre-existing `ESS_MCV_TRACE` lines but no
`ESS_MCV_NUMERIC_TRACE` lines, and its analyzer failed with missing base
traces. The raw logs are retained for auditability and are excluded from all
scientific calculations. The valid run is `../success-instrumented/`.
