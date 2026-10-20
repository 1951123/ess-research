# Issue #38 Stage 1A held-out Forest10 evidence

Snapshot: 2026-10-20 (Asia/Shanghai). This is an author-reported local measurement bundle produced in the dedicated Issue #38 Worktree/runtime.

## Gate A and protocol

**Gate A: PASS for this descriptive run.** The approved Forest10 archive/CSV/pickles/canonical/audit hashes matched the frozen Issue #23 records; the pinned PostgreSQL 16.14 source commit was clean; the pre-frozen sample relation identity and physical page count matched; all 1,200 planned measurements had a positive pre-clamp final numeric trace; and all 20 set/repetition catalog snapshots were matched.

The held-out cohort contains 60 deterministic test queries, 1200 measurements, and 2 repetitions. Selection was frozen before outcome collection using query IDs, source-query hashes, syntax eligibility, and candidate coverage only. The cohort selection SHA is recorded in `protocol.json`; the raw measurements SHA is `913459527105059514882f60e047256669786544f6513f25356bfb0fb11ed437`.

The primary metric is absolute log error from the positive pre-clamp trace, `|ln(estimate/T)|`, with `T=max(1,N)`. Plan Rows are secondary; latency and physical maintenance cost were not measured. P90 is nearest-rank with ceiling rank. The six tail queries are the largest true `N` values, with query-ID tie ordering. There are three zero-truth query IDs, measured twice per set, and they remain a separate stratum.

## Actual PostgreSQL held-out results

The table reports pooled repetition-level metrics (`n=120` per set). `MCV payload` is based on catalog inspection, while `trace selected` is based on the instrumented PostgreSQL trace, not EXPLAIN alone.

| Set | Issue #23 aliases | MCV payloads present | Trace-selected query count | Mean | Median | P90 | Max |
|---|---|---|---:|---:|---:|---:|---:|
| `Empty` | joint_robust@B0, nominal@B0, pess@B0 | none | 0 | 5.02103904978363555044361729127362932400089199974822910210121 | 2.55550212796810175940282301196086600963170745794220883451338 | 12.7993173826699629101240649825519862968533475723577303471991 | 33.4474104406851672984201857966450805460268465985012485820311 |
| `{e01,e34}` | joint_robust@B2, nominal@B2, pess@B2, joint_robust@B3, pess@B3, joint_robust@B5, pess@B5 | e34 | 94 | 4.9520556140595575809328996770789275390314406076689685406764 | 2.47246017460337404940262893617229215569133052654550525846032 | 12.7993173826699630911092040196952649928310253247254105921495 | 33.4474104406851671641171654425378639241711022767376489642573 |
| `{e01,e34,e56}` | — | e34 | 94 | 4.9520556140595575809328996770789275390314406076689685406764 | 2.47246017460337404940262893617229215569133052654550525846032 | 12.7993173826699630911092040196952649928310253247254105921495 | 33.4474104406851671641171654425378639241711022767376489642573 |
| `{e12,e23,e34}` | nominal@B3, nominal@B5 | e12,e23,e34 | 114 | 4.92783260951075323917449491511521554243577455871953269445204 | 2.55728431812098560063674233866086103382945104264553904227744 | 12.7993173826699629101240649825519862968533475723577303471991 | 33.4474104406851672984201857966450805460268465985012485820311 |
| `{e12,e23,e34,e45}` | — | e12,e23,e34 | 114 | 4.92783260951075323917449491511521554243577455871953269445204 | 2.55728431812098560063674233866086103382945104264553904227744 | 12.7993173826699629101240649825519862968533475723577303471991 | 33.4474104406851672984201857966450805460268465985012485820311 |
| `{e12,e23,e34,e45,e56}` | — | e12,e23,e34 | 114 | 4.92783260951075323917449491511521554243577455871953269445204 | 2.55728431812098560063674233866086103382945104264553904227744 | 12.7993173826699629101240649825519862968533475723577303471991 | 33.4474104406851672984201857966450805460268465985012485820311 |
| `{e12,e23,e34,e56}` | — | e12,e23,e34 | 114 | 4.92783260951075323917449491511521554243577455871953269445204 | 2.55728431812098560063674233866086103382945104264553904227744 | 12.7993173826699629101240649825519862968533475723577303471991 | 33.4474104406851672984201857966450805460268465985012485820311 |
| `{e34}` | — | e34 | 94 | 4.9520556140595575809328996770789275390314406076689685406764 | 2.47246017460337404940262893617229215569133052654550525846032 | 12.7993173826699630911092040196952649928310253247254105921495 | 33.4474104406851671641171654425378639241711022767376489642573 |
| `{e34,e45}` | — | e34 | 94 | 4.9520556140595575809328996770789275390314406076689685406764 | 2.47246017460337404940262893617229215569133052654550525846032 | 12.7993173826699630911092040196952649928310253247254105921495 | 33.4474104406851671641171654425378639241711022767376489642573 |
| `{e34,e56}` | — | e34 | 94 | 4.9520556140595575809328996770789275390314406076689685406764 | 2.47246017460337404940262893617229215569133052654550525846032 | 12.7993173826699630911092040196952649928310253247254105921495 | 33.4474104406851671641171654425378639241711022767376489642573 |

Observed effective behavior is narrower than the requested resource sets: `e01`, `e45`, and `e56` had no MCV payload in these fixed-sample snapshots. Adding those objects therefore did not change the measured estimate summaries. The nominal set `{e12,e23,e34}` had three 300-item MCV payloads; the PESS-selected set `{e01,e34}` had only `e34` with a 300-item payload.

Against Empty, `{e01,e34}` had mean paired delta `-0.0689834357240779695` (54 benefits, 50 ties, 16 harms over 120 paired repetition/query rows); `{e12,e23,e34}` had mean delta `-0.0932064402728823113` (78 benefits, 30 ties, 12 harms). These are descriptive paired differences, not a dominance claim.

Against the nominal selected set `{e12,e23,e34}`, the PESS-selected `{e01,e34}` was worse on mean absolute log error by `0.02422300454880434175840476196368509591739766000000000000000`; it had 22 benefits, 30 ties, and 68 harms. Its largest per-row adverse delta was `0.2588783138432469120132488941`. This is a meaningful harmful-overconservatism observation under the frozen construction order, while the nominal set itself improves over Empty by mean `-0.0932064402728823112691223761594050899704423183333333333333333`.

Repetition instability was reported in the bounded JSON summary for every set. The raw trace also records which statistics were selected per query; no claim is made that the abstract maximal-matching family contains every real PG choice.

## Issue #23 model layer (separate)

The following are the original Issue #23 rationalized measured-input model certificates on its six valid selection tasks. They are not test-query PostgreSQL outcomes and were not refit from the held-out cohort.

| Budget | Method | Selected | Exact model objective | Task-wise PESS bound |
|---:|---|---|---:|---:|
| 0 | joint_robust | `Empty` | `14672700091697225791/1000000000000000000` | `14672700091697225791/1000000000000000000` |
| 0 | nominal | `Empty` | `14672700091697225791/1000000000000000000` | `14672700091697225791/1000000000000000000` |
| 0 | pess | `Empty` | `14672700091697225791/1000000000000000000` | `14672700091697225791/1000000000000000000` |
| 2 | joint_robust | `{e01,e34}` | `2699689273055419537/200000000000000000` | `2699689273055419537/200000000000000000` |
| 2 | nominal | `{e01,e34}` | `2699689273055419537/200000000000000000` | `2699689273055419537/200000000000000000` |
| 2 | pess | `{e01,e34}` | `2699689273055419537/200000000000000000` | `2699689273055419537/200000000000000000` |
| 3 | joint_robust | `{e01,e34}` | `2699689273055419537/200000000000000000` | `2699689273055419537/200000000000000000` |
| 3 | nominal | `{e12,e23,e34}` | `13303092326884799533/1000000000000000000` | `14320233961846001243/1000000000000000000` |
| 3 | pess | `{e01,e34}` | `2699689273055419537/200000000000000000` | `2699689273055419537/200000000000000000` |
| 5 | joint_robust | `{e01,e34}` | `2699689273055419537/200000000000000000` | `2699689273055419537/200000000000000000` |
| 5 | nominal | `{e12,e23,e34}` | `13303092326884799533/1000000000000000000` | `14320233961846001243/1000000000000000000` |
| 5 | pess | `{e01,e34}` | `2699689273055419537/200000000000000000` | `2699689273055419537/200000000000000000` |

The model layer is exact for its recorded rationalized instance/reference calculation; the PostgreSQL trace layer is floating-point solver/server output observed in this run. The two layers must not be merged into one calibration or guarantee.

At budget 3, both layers select different resource sets in the same direction of nominal-vs-PESS comparison: the Issue #23 model reports PESS `{e01,e34}` versus nominal `{e12,e23,e34}`, while held-out PG means are 4.9520556 versus 4.9278326. The magnitude is not directly comparable because the model sums six valid-task losses and the held-out table averages 120 test observations; the measured catalog payload gap is a concrete model-vs-real semantic discrepancy.

## Judgment

**Recommendation: GO for broader real-decision evaluation, not as evidence that PESS wins.** The frozen held-out cohort produced a reproducible, nontrivial paired difference and a meaningful adverse PESS-versus-nominal case with valid trace fidelity. The sharper follow-up hypothesis is that resource-selection decisions can be dominated by whether requested statistics actually acquire MCV payloads and by PG's realized candidate-selection behavior; this needs a broader, independently audited cohort.

This recommendation is bounded. The cohort is only 60 deterministic syntax/coverage-selected test queries, not population-level generalization. The instrumented PostgreSQL build is not pristine upstream. The additive one-unit budget is a proxy, not physical maintenance cost. Stage 1C remains the gate for any stronger multi-statistic composition, real-scheme containment, or PESS-guarantee claim. No latency, universal PostgreSQL, or universal PESS-dominance conclusion follows.

## Provenance and preserved negative result

- Protocol SHA: `79d76dbb2cd5c47e3fe434c32a9156040c66bac13f8d7a4cfbda8538fef74307`; raw run summary SHA: `913459527105059514882f60e047256669786544f6513f25356bfb0fb11ed437` for measurements, setup SHA `21d0f48f49f3eb5a09ae652363a42b78a258029f1dc6ee708c1b33b910f55e19`.
- Raw Forest10 rows, sample, PGDATA, server logs, full traces, and EXPLAIN text remain outside Git under the Issue-owned runtime root.
- Runtime isolation: PGDATA `/home/wqts/ess-runtime/issue38/pgdata-replay`, PGHOST `/home/wqts/ess-runtime/issue38/socket-replay`, port `55639`, database `postgres`; the cluster was shut down after collection.
- An earlier harness attempt is preserved externally: it collected 120 valid Empty rows, then stopped on a catalog-name parser bug before non-empty-set outcomes. It was not combined with the final run.
- Evidence labels: the source/build and trace format are source-derived conditional facts; the 1,200 rows and summaries are experimentally observed; the Issue #23 model certificates are exact/rationalized reference results; no universal or physical-cost claim is asserted.
