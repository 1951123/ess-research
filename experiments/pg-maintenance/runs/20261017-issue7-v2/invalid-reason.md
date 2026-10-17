# Invalidity note

The v2 run contains 336 complete timed `ANALYZE` observations, but its
`META|...` queries ran before the untimed warm-up.  Consequently the recorded
`mcv_payload_built=false` values describe the newly created, not-yet-analyzed
statistics objects and cannot establish the required post-refresh payload
state.  The raw timing evidence is retained unchanged for provenance, but v2
is not used as the final Issue #7 result.  The runner was corrected to collect
the same metadata after warm-up, and the complete matrix was rerun in the v3
directory.
