# Issue #40 Stage 1C result report

Evidence status: **MODEL LIMITATION COUNTEREXAMPLE** for the bounded fixture.
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

The issue-owned ledger and trace mapping produced 312 inclusion-wise maximal
matching passes and 28 failures.  Every failure has the same bounded pattern:
task `q_tail`, available candidate `e12`, selected candidate set empty, and
verifier message `selected set is not inclusion-wise maximal; addable=['e12']`.
The failures occur across the frozen resource configurations that include
`e12`, including the composition singleton and three-resource case.  This is
reported as a **MODEL LIMITATION COUNTEREXAMPLE** to treating the prescribed
graph admissibility/maximality rule as guaranteed for this PostgreSQL trace.
It is not evidence that every real PostgreSQL scheme is captured by this
prescribed `Gamma`.

## Composition audit

All 28 frozen joint records were positive pre-clamp.  The residual is the
signed single-ratio prediction from the manifest versus the actual final
pre-clamp trace; logs are taken only after positivity checks.

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
