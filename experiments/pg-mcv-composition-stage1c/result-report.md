# Issue #40 Stage 1C result report

Evidence status: **INCONCLUSIVE/OUTSIDE RESTRICTED GATE** for the 28 old
matching failures in the bounded fixture.
The run is not a universal PostgreSQL claim and does not establish a shared
policy or a PESS theorem.

## Scope and gate

The run used the frozen manifest in this directory, Forest10 inputs from the
hash-pinned data root, and the `ess-postgresql` source at commit
`23c7c2fdd4bfb561f3257d947fee956a2999fdb6` (PostgreSQL 16.14).  The issue-owned
runtime was `/tmp/ess-issue40-stage1c-v8`, port `55440`, database
`ess_issue40`; it was stopped after completion.  The table was constructed in
the issue-owned database with the fixed sample identity
`relation_oid=16384`, `relation_filenode=16384`, `relation_pages=7792`,
double-precision columns, and `fillfactor=100`.

The positive pre-clamp gate passed for all 340 observations: every observation
had one numeric final trace with a finite, strictly positive `nrows_preclamp`.
No observation relied on `Plan Rows` as a pre-clamp value.  The run used two
repetitions and the frozen creation orders; no Stage 1A tuning or held-out
error was used.

## Matching audit

The preserved v8 ledger and trace mapping produced 312 inclusion-wise
maximal-matching passes and 28 old failures.  Every old failure has the same
pattern: task `q_tail`, available candidate `e12`, selected candidate set
empty, and verifier message `selected set is not inclusion-wise maximal;
addable=['e12']`.  The post-run eligibility audit parses the exact executed
SQL and applies the pinned PostgreSQL 16.14 source's simple compatible-clause
conditions.  For `q_tail`, `Slope` expands to clause indices 2 and 3, but
`Aspect` has no predicate; consequently `e12=(Aspect,Slope)` is outside the
restricted candidate gate.  All 28 old failures are therefore
**INCONCLUSIVE_OUTSIDE_RESTRICTED_GATE**, not model-limitation
counterexamples.  No selected statistic OID was unmapped.

The audit records 340 eligibility ledgers: 916 candidate/task entries with
both endpoints syntactically covered and 1,804 with a missing supported
predicate.  There are 232 observations containing at least one outside-gate
resource, which is recorded separately from the 28 old failures.  The
candidate consideration trace reports selected statistics and claimed clause
indices, but does not emit a positive candidate-considered line for every
unselected statistic.  Thus the crosswalk is necessary eligibility evidence,
not a complete certificate of planner consideration.

In both the live runner and the offline reclassifier, a selected candidate
outside the screened set is retained rather than filtered away and is marked
`INCONCLUSIVE_SELECTED_OUTSIDE_ELIGIBILITY`; an unmapped selected OID is
marked `INCONCLUSIVE_UNMAPPED_SELECTED_OID`.  Accordingly,
`SUPPORTED_FOR_ELIGIBLE_GRAPH` means only consistency with the syntactically
screened reduced graph.  It is not a verified full-PostgreSQL candidate
consideration result and does not pass the preregistered equality-only gate.

Evidence-audit provenance is hash-bound: the preserved v8
`observations.jsonl`, fresh v2 derived crosswalk, and committed 340-row
redacted ledger have their exact SHA-256 values in
`eligibility-reclassification-summary.json` and `result-summary.json`.  The
redacted ledger contains row identity, selected OIDs and labels, claimed
clause indices, screened eligible/outside candidate IDs, legacy status, and
new status/reason, but no raw SQL or PostgreSQL log payload.  The reclassifier
uses exclusive-create output paths and refuses to overwrite an existing
derived artifact.

## Composition audit

All 28 frozen joint records were positive pre-clamp.  The residual is the
signed single-ratio product heuristic from the manifest versus the actual
final pre-clamp trace; logs are taken only after positivity checks.  This is a
tested reconstruction heuristic, not a general identity.

| Case | Observed absolute relative residual | Interpretation in this fixture |
| --- | ---: | --- |
| `q_star_disjoint` | `1.8432196214468729e-16` | near-zero in this run |
| `q_star_overlap` | `0.15903912485392598` | non-multiplicative for one creation order |
| `q_star_star` | `0.049577015684355985` | non-multiplicative for one creation order |
| `q_star_parallel` | `0` | near-zero in this run |
| `q_path_disjoint` | `0.21378131889174559` | largest observed discrepancy |
| `q_tail_overlap` | `0` | near-zero in this run |
| `q_tail_three` | `0` | near-zero in this run |

The order-dependent differences in the overlap, star, and path cases are
observations of this build and fixture only.  They do not prove a general
composition theorem or refute every possible implementation/model variant.

## Reproducibility and limitations

The exact command is in `run-commands.txt`; the raw server log and result JSONL
remain under the private runtime root.  The committed summary records their
hashes and the immutable input hashes.  The run used the instrumented
`ESS_MCV_TRACE`, `ESS_MCV_NUMERIC_TRACE`, and fixed-sample import path.  The
sample was replayed before each controlled `ANALYZE`.

The selected query/resource universe is a bounded construction from Forest10,
not a representative workload.  The result distinguishes prescribed
`Gamma_i(M)` membership from all real schemes and does not claim containment
or equality without additional assumptions.

The manifest's preregistered `simple_clause_rule` said "one equality clause",
but the immutable canonical SQL records used here contain `BETWEEN` and
inequality comparisons.  The runner executed those source clauses verbatim;
it did not rewrite them or claim equality-only coverage.  This declaration
discrepancy is retained as a fixture limitation and should be resolved in a
future preregistration rather than silently repaired after observation.

The eligibility audit is implemented by `predicate_eligibility.py` and
`reclassify_v8.py`.  It is an offline, fail-closed crosswalk over the
preserved v8 observations; it does not rewrite `observations.jsonl`,
`composition.json`, the frozen manifest, or the raw server log.  A future
equality-only fixture would require a separately versioned preregistration.

The pinned source locations used for trace interpretation are:

- `src/backend/statistics/extended_stats.c:1263-1600` for statistic selection
  and simple compatible-clause conditions;
- `src/backend/statistics/extended_stats.c:1842-1911` for candidate-none,
  selected-statistic, and claimed-clause trace lines;
- `src/backend/statistics/extended_stats.c:2059-2069` for per-statistic
  numeric trace fields;
- `src/backend/optimizer/path/costsize.c:5032-5039` for final
  pre-clamp/post-clamp numeric values;
- `src/backend/commands/analyze_sample_cache.c:332-430` for fixed-sample
  import and relation/descriptor validation.
