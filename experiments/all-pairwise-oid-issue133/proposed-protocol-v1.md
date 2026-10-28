# Issue #133 proposed protocol v1 — all-pairwise MCV OID order

**State:** M0 design only. This file is not authorization to run PostgreSQL, create/drop statistics, execute `ANALYZE` or `EXPLAIN`, or inspect new Test outcomes.

## Question and frozen scope

Test whether, for the same complete two-column MCV set and physical data/statistics state, changing relative OID priority can change the MCV objects chosen, the predicates they consume, and PostgreSQL's Test Q-error. H1 is not assumed true. An ALL-versus-SELECTED difference is a separate installed-set contrast and cannot by itself establish an OID-order effect.

Keep Forest10, Census13, DMV11 and Power7; the exact 199 Issue #99 Train candidate IDs and columns; frozen Issue #99 Nominal B=5 selections; PostgreSQL 16.14 at source commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; the Issue #101/#105 configuration, target 300, fixed sample, official 10,000-query AreCEL Test split and Q-error code. Do not retrain, reselect, alter the Test workload, or use Test outcomes to choose orders or parameters.

Each arm is one physical configuration and uses **one global relative OID order for all 10,000 Test queries**. The random-order intervention is counterfactual; it does not assert PostgreSQL naturally assigns OIDs uniformly in production.

## Frozen candidate and order identity

The source inventory is [candidate-universe-manifest.json](candidate-universe-manifest.json), raw SHA-256 `20fd045a1391e6b0308d36ec581e128db185b892bc6e7384540e77c483572104`. The exact order schedule is [all-order-sample-v1.json](all-order-sample-v1.json), raw SHA-256 `6e53e60083426a0f6fedb7147eae418ceb69aa826e01484d8794b95a80546d9c`.

- For every dataset, canonical ALL is ascending stable candidate ID and reverse ALL is its exact reverse.
- Four additional ALL permutations per dataset are stored in the schedule. Root seed: `4017865097189414557` (unsigned 64-bit), drawn once with CPython `secrets.randbits(64)` before any Issue #133 Test execution; generator: `ess-splitmix64-fisher-yates-direct-v1`; child seeds derive from SHA-256 of the domain-separated tuple `(root, dataset, draw index, retry index)`. The Python version, generator SHA-256, rejection retries, every complete order and each order SHA-256 are recorded.
- Fisher–Yates uses rejection-sampled bounded integers. Each draw is a uniform permutation of the full candidate list under the PRNG model. Rejecting canonical/reverse or a previously drawn permutation gives successive sampling without replacement from the remaining order population. The full `k!` population is never enumerated.
- All schedules must be generated and committed before M1. No order can be added, replaced, or rejected based on Test results.

| Dataset | ALL objects | ALL orders | ALL configurations | ALL EXPLAIN calls |
|---|---:|---:|---:|---:|
| Forest10 | 45 | canonical, reverse, 4 random | 6 | 60,000 |
| Census13 | 78 | canonical, reverse, 4 random | 6 | 60,000 |
| DMV11 | 55 | canonical, reverse, 4 random | 6 | 60,000 |
| Power7 | 21 | canonical, reverse, 4 random | 6 | 60,000 |
| **Experiment A total** | **199 across four separate tables** |  | **24** | **240,000** |

## Experiment A — fixed ALL set, changed order

For each dataset, each of the six orders contains exactly all candidate IDs once. Only the requested CREATE sequence and its resulting within-set OID priority may differ. The full source table, query set, PG version/settings, fixed sample, column targets, extended-statistics targets and all candidate MCV payload states/content must match across arms.

Before any Test EXPLAIN for a dataset, perform the following preflight for all six arms:

1. Import and row-count-check the full source table; check CSV hash, ordered schema, relation identity and fixed Issue #99 sample hash/header. Apply ordinary-column target 300 and replay the exact sample with the #101 helper.
2. Create the full candidate sequence with MCV kind and target 300; run the fixed-sample `ANALYZE` path. Do not rely on SQL request order alone.
3. Independently enumerate `pg_statistic_ext` ordered by OID and map every OID to its stable candidate ID. Require exact set, exact count, requested sequence, two expected columns, `stxkind={m}`, and target 300. No OID is treated as a stable identity across arms.
4. Fingerprint ordinary column statistics and every candidate's MCV payload state and contents. Treat NULL payload, present-empty MCV list, and populated list as separate valid observations. If any candidate is absent/wrong-kind/wrong-target, or a candidate payload state/content or ordinary-statistics fingerprint changes across orders, stop before Test; the order contrast would otherwise be confounded. Do not remove the candidate or substitute another object.
5. After every ALL arm passes the shared-state checks, execute all 10,000 frozen Test queries per arm with the pinned `EXPLAIN (FORMAT JSON, SUMMARY OFF, ESS_DIAGNOSTICS true)` path, six query clients, and unchanged Q-error code. Keep diagnostics status separate from Plan Rows status.

## Experiment B — ALL versus frozen SELECTED set

Add one Nominal B=5 arm per dataset using the exact Issue #99 frozen selected IDs, in ascending ID order. That order is the subsequence of canonical ALL, so selected-object relative priority is matched. Use the same full table, query IDs, sample, PG configuration and Q-error procedure. Require each selected object's MCV payload state/content to match that candidate's state/content in ALL canonical.

This is a fixed canonical-order installed-set comparison. It is **not** an estimate of the selected set's expectation over random orders. PESS B=5, EMPTY, and randomized selected-set arms are out of scope; each would add separate configurations and calls and needs a protocol revision plus approval.

| Arm group | Configurations | EXPLAIN calls |
|---|---:|---:|
| Experiment A: 6 ALL orders × 4 datasets | 24 | 240,000 |
| Experiment B: 1 frozen Nominal B=5 order × 4 datasets | 4 | 40,000 |
| **Core total** | **28** | **280,000** |

The 16 random ALL arms alone are exactly `4 datasets × 4 orders × 10,000 = 160,000` calls. They do not include canonical/reverse or Experiment B.

## Metrics and order-sampling uncertainty

Preserve Issue #101's `qerror_for_plan_rows` and `summarize_errors` unchanged: convert Plan Rows with the existing `np.round(..., r=1)` path; Q-error is the existing three-case zero-aware ratio; P50/P95/P99 use the existing NumPy median/percentile semantics. Report no replacement or extra clamping.

For dataset `d` with `k_d` candidates and order `π`, first compute the arm statistic

\[
Y_{d,\pi}(M)=\operatorname{P95}_{q\in Test_d} Q(q,M,\pi).
\]

The ALL-order estimand is the expectation of those per-order P95 values over the uniform finite population of `N_d=k_d!` relative permutations. Let `Y_c` and `Y_r` be the fixed canonical/reverse values; let `Y_1,...,Y_4` be the four SRSWOR values from the remaining `N_d-2` orders, with mean `\bar Y_s` and sample variance `s_s^2` using denominator 3. Estimate:

\[
\widehat\mu_d = \frac{Y_c+Y_r+(N_d-2)\bar Y_s}{N_d}.
\]

The fixed orders are certainty inclusions, not random sample members. The finite-population design variance estimator is

\[
\widehat{\operatorname{Var}}(\widehat\mu_d)=
\left(\frac{N_d-2}{N_d}\right)^2
\left(1-\frac{4}{N_d-2}\right)\frac{s_s^2}{4}.
\]

The fixed-order values contribute no sampling variance. Report design SE as the square root. A 95% `t_3` interval around the estimate is only a small-sample approximation, not guaranteed design coverage; label it accordingly and report the four random observations and their spread. Four draws give weak precision and do not establish that rare order effects are absent. Do not adaptively increase the sample if the interval is wide.

Report per-order Mean Q-error, P50, P99, observed maximum P95, and MCV usage frequencies as secondary/descriptive results. Use the same certainty-plus-SRSWOR weighting for order-population means of secondary metrics. Never call the largest sampled value the global worst order or calculate P95 after pooling query-order records. Workload/query sampling uncertainty is outside the permutation interval. A change in MCV identity alone does not establish a Q-error change.

For Experiment B report the order-matched canonical contrast `Y_ALL,canonical − Y_NominalB5,canonical` and identify it as a set effect at this fixed priority order. Do not combine it with the ALL random-order expectation as if both treatments had the same order population.

## Blocker evidence required for H1

Existing #105/#107 selected/claimed/estimate events are not enough to establish suppression. Before M1, implement a minimal diagnostic-only extension or validated source-derived trace that records, for a structurally eligible query and each selection round:

1. The normalized query's clause-index-to-attribute/operator mapping.
2. Candidate IDs and their remaining matched-attribute count/key width for the candidates tied at the current best score before selection.
3. The selected ID, its consumed clause indices, and the MCV estimate.
4. Which previously tied overlapping candidate ID loses eligibility after those clauses are consumed.
5. Under an alternate prespecified order, the alternate candidate chosen, its consumed clauses, estimate and query Q-error.

The trace must be observational only and must leave `choose_best_statistics` comparisons and planner decisions unchanged. A relevant example must show both a changed MCV choice and changed estimate/Q-error; it must not equate choice change with loss change. A1–A4 from the PostgreSQL/maximal-matching note must be checked before invoking that model explanation. Queries outside A1–A4 may still be reported as PostgreSQL physical observations, but not as theorem instances.

## Resource estimate and proposed run envelope

The exact schedule cost and historical calibration are recorded in [cost-estimate.json](cost-estimate.json). Current evidence: #105 used six clients and peaked at 2,931,474,432 bytes for 80,000 calls; #107 used six clients and peaked at 3,969,179,648 bytes for 1,440,000 calls (474.496 s), and its 120,000-call continuation used 120.132 s and peaked at 814,166,016 bytes. These runs had only three/five-object catalogues. Their wall times are not all-candidate forecasts.

Proposed M1 safety envelope: one dataset and one configuration at a time; six Test clients; stop before beginning a new arm at 6 hours; hard wall stop at 8 hours; disk early stop at 8 GiB and hard cap at 10 GiB. These are conservative guardrails, not a claim that all-candidate ANALYZE fits them. The all-candidate per-arm ANALYZE time and peak planner memory/disk remain unknown; if a pre-Test all-object pilot is desired to refine these limits, it requires separate explicit authorization.

## Stop, retry, and preservation rules

- Freeze all 28 arm identities, every order, sample/hash, PG source/configuration and metric before Test execution.
- DDL/catalog cardinality, columns, kinds, targets or actual OID order mismatch: no Test for that arm; preserve commands, manifest, catalog snapshot and logs. Do not reorder or drop an object to make it pass.
- Full-table/sample/ordinary statistics mismatch or cross-order MCV state/content mismatch: stop the dataset before Test; retain the attempt. Correct the implementation and restart only the same frozen schedule from a fresh run-owned cluster. No Q-error is inspected to choose a restart.
- Any Test arm with fewer than 10,000 valid Plan Rows or incomplete required diagnostics is marked incomplete. Preserve partial rows/statuses; do not include it as a valid arm or replace it with a different order.
- A retry is allowed only for an identified engineering/infrastructure fault, under the same input, arm ID, order, configuration and resource envelope; preserve both run IDs and all evidence. No outcome-based retry.
- Stop the whole experiment on an object-build failure, inability to realize a frozen OID order, nondeterministic sample/content state that cannot be corrected within this protocol, source/workload hash drift, or either hard resource limit. Ask for new approval before changing the object set, seed, order count, data, target, PG source, workload, diagnostics semantics or hard caps.
- Delete only this run's stopped PostgreSQL data directory after its status and required provenance are durably recorded; never remove frozen Issue #99/#105/#107/#125 evidence or another Worktree's files.

## Explicit limitations

Four random orders are an initial, low-cost probability sample, not a precise characterization of all `k!` orders. Canonical/reverse are fixed certainty arms and receive their exact finite-population weights. A wide interval is evidence of insufficient precision. Even a clear P95 order effect will be conditional on these frozen tables, selections, PostgreSQL build, Test workload, and counterfactual order design. A blocker trace is necessary for the proposed mechanism claim; `ESS_DIAGNOSTICS` sequence changes alone support only descriptive association.
