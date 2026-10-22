# v2 failure analysis: `valid:000042 × e01_05`

**Disposition: BLOCKED; the partial v2 observations remain unusable for fitting.**
This is a read-only analysis of the preserved run. No PostgreSQL was run, no
truth was loaded, and no test data or outcomes were accessed.

## What the retained evidence establishes

- The sole failed JSONL row is worker 1, query
  `arecel:census13:valid:000042`, config `e01_05`. It records
  `ValueError: base estimate nrows_preclamp must be finite and positive`,
  `psql_stdout_chars=1689`, and `first_token='['`; it does **not** retain the
  response body, parsed scalar, or MCV event list. The v2 run summary repeats
  only this error. The preserved worker server log has no query ID or raw
  `nrows_preclamp` with which to recover the response. Thus the original JSON
  and its exact scalar are unavailable in the retained evidence.
- This is not a JSON syntax, missing-diagnostics, incomplete-status, or event
  association exception. In the pinned adapter, JSON decoding, complete-status
  checks, event validation, and the unique base-estimate/relation check precede
  the reported positivity guard. The value converted to `Decimal`, but the
  guard combines `not is_finite()` and `<= 0`; it cannot distinguish zero,
  negative, NaN, or infinity. **Which case occurred cannot be determined.**
- The failing query is the official valid workload row at `source_index=42`.
  The labels-free loader identifies its SQL SHA-256 as
  `14d8fbb8f75d03ff9f56cd53de9bbf87f4f7b2708c3fadfbfec12cef87dc7369`.
  Its 12 predicates include `workclass = 'Never-worked'` and
  `occupation = 'Handlers-cleaners'`, so `e01_05` (the frozen
  `workclass`/`occupation` candidate) is statically eligible. This establishes
  the query/config identity, not an actual planner MCV hit.
- Worker 1 successful observation rows from this run identify the persistent
  `public.census13` relation as OID `16384` and `e01_05` as statistic OID
  `16407`. The failed row itself contains neither OID. Its adapter reached the
  base relation-identity check, so the run's relation mapping is consistent
  with `16384`; the error record does not independently preserve that value.
  OID `16407` is the worker/config mapping from successful `e01_05` observations,
  **not a persisted MCV-selection event for query 42**.
- No MCV event or `NO_MCV_EVENTS` status was written for the failed query.
  The exact MCV outcome and clause indexes are therefore unknown. The saved
  trace lacks query identity, and static eligibility is not evidence of
  runtime selection.

The schema path used by the adapter is the top-level query record's
`[0]["ESS Diagnostics"]["Events"][i]`, for the event where
`type == "base_estimate"`, field `nrows_preclamp`. The event index `i` and its
raw value are not recoverable without the discarded JSON body.

## Minimal disposition

Do not impute a value, substitute `Plan Rows`, or add a floor/epsilon. If the
value was zero or negative, the frozen corrected-log input is outside its
positive domain; if non-finite, the observation is likewise invalid until its
source is understood. Keep the acquisition blocked and require a researcher
decision on any protocol change before collecting or fitting again. The
smallest diagnostic improvement for a separately authorized run is to persist
the rejected base scalar (or an explicit non-finite token), its JSON event
path, event count/status, and normalized MCV events in the ERROR record—without
changing acceptance rules or the model.
