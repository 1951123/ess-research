# Issue #107 — uniform relative-OID Test protocol v1

**Status: protocol proposal only.** This issue authorizes configuration accounting, source/protocol inspection, synthetic checks, and resource estimation. It does not authorize new official AreCEL Test EXPLAIN/ANALYZE calls or a physical permutation sweep. A separate researcher decision is required before execution.

## Minimum experiment and claim boundary

The scientific question is how actual PostgreSQL Test Q-error changes under a hypothetical uniform draw over relative OID orders for the frozen B=5 Nominal/PESS sets; reuse the Issue #99 selections, Issue #101 evaluator and fixed samples, and Issue #105 physical-order path; the minimum new work is a frozen full-permutation schedule with exact counts, reuse audit and capped cost estimate.

The distribution is explicitly counterfactual: PostgreSQL does not randomly shuffle OIDs in production. For each fixed unordered set (M), one relative OID order (pi) governs every query in that configuration. The expectation is uniform over all (k!) permutations, (k=|M|); matching outcomes induced by multiple permutations keep their multiplicity. This does not average uniformly over distinct matchings.

This follow-up was specified after reading the prior Issue #101 and #105 test summaries. It is therefore not prospectively untouched by those observations. The schedule and estimands below are frozen before any new query-level outcomes are inspected; no later permutation, metric, or subset selection may depend on outcomes.

## Frozen selections and exact schedule

Source of truth is Issue #99's completed train-only manifest at `experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json` (SHA-256 `2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca`). All rows below are the B=5 selections; PESS sets with fewer than five items remain as selected. The candidate-map SHA pins each ID-to-column mapping.

| Dataset | Candidate-map SHA-256 | Nominal set (k) | PESS set (k) | Shared IDs |
|---|---|---|---|---|
| Forest10 | `8fd28b72e4b071dc2ca491502bb61b4652fe9b68269f1db2eef1f6f1f7ffc76b` | `{e01_06,e02_07,e02_08,e03_04,e06_08}` (5) | `{e01_06,e02_07,e03_04}` (3) | `e01_06,e02_07,e03_04` |
| Census13 | `c661e07db8be24050417014bb5e280dd6cc1d856b26700075638a175e0dc8c64` | `{e01_05,e02_03,e04_06,e04_08,e06_08}` (5) | `{e00_11,e01_05,e02_03,e04_06,e07_12}` (5) | `e01_05,e02_03,e04_06` |
| DMV11 | `8feab245abc557251d7446ff25d25ead1f43bdf0f39fbc591b19228a8e9d0f5d` | `{e00_05,e01_04,e01_07,e02_03,e04_07}` (5) | `{e00_05,e01_04,e02_03,e06_07,e08_10}` (5) | `e00_05,e01_04,e02_03` |
| Power7 | `0c17d1bced2f1ed9b48cb6867982b0938d180c996b3617cb36383d1851c8dfb4` | `{e00_01,e00_03,e01_02,e02_04,e03_06}` (5) | `{e00_01,e02_04,e03_06}` (3) | `e00_01,e02_04,e03_06` |

Within each dataset, the Nominal and PESS sets are distinct, so none of their schedules deduplicates. The deterministic schedule is dataset order Forest10, Census13, DMV11, Power7; within a dataset Nominal then PESS; within each set, lexicographic permutations of the sorted candidate IDs. This produces 120 permutations for (k=5) and 6 for (k=3). Each arm creates statistics in exactly its listed permutation order and runs the complete Test split before changing the order.

| Dataset | Nominal perms | PESS perms | Full configs | #105 configs reused | New configs | New EXPLAIN calls |
|---|---:|---:|---:|---:|---:|---:|
| Forest10 | 120 | 6 | 126 | 2 | 124 | 1,240,000 |
| Census13 | 120 | 120 | 240 | 2 | 238 | 2,380,000 |
| DMV11 | 120 | 120 | 240 | 2 | 238 | 2,380,000 |
| Power7 | 120 | 6 | 126 | 2 | 124 | 1,240,000 |
| **Total** | **480** | **252** | **732** | **8** | **724** | **7,240,000** |

The full target is 7,320,000 query/configuration observations (732 × 10,000). The 80,000 observations already present in the eight reusable #105 arms are not new calls. For each Nominal set, those arms are its ascending-ID order and exact reverse; they are the first and last entries in the lexicographic 120-permutation schedule. All 724 other arms are new. Issue #103's 906 training-model orders are not part of this physical Test schedule.

## Reuse audit

Reuse only the eight query-level members already recorded in successful Issue #105 run `20261025T130222Z-issue105-official-v2`, raw archive SHA-256 `ca2ada0f057f7b439eaee98900f0ae57883adebc84f98d184ec437c1defea9c2`. The run manifest and configuration/catalog metadata were audited; the raw query-level archive was not opened for this protocol. The verified identity checks are:

- all four selected Nominal sets and candidate-map hashes match Issue #99;
- each canonical/reverse CREATE sequence equals the observed OID-sorted candidate sequence;
- all four fixed sample hashes match Issue #101's pinned Issue #99 samples, with successful replay;
- the pinned PostgreSQL 16.14 research build, Issue #101 helper/protocol, six-client planner setup, GUCs, query path, target 300, Q-error implementation and NumPy rounding are shared;
- within each dataset's pair, the full-table identity, ordinary-column-statistics fingerprints and per-candidate MCV-content fingerprints match; Issue #105 records populated target-300 MCVs and complete diagnostics for all 80,000 queries.

The reused run was produced at task source commit `5fb8053e1d9717a543a45a2bf19d4adc2c6bdb65` (included in current `main` via merge `6759657ce8c512773bb786438e852d298157788e`), with Issue #105 protocol SHA-256 `3afe7853a891f177ed836993bef2cd77a232f35e5398843d0019b12b384653d6`, amendment SHA-256 `58b2a15b6fee0f86212c27482aa646c25a9d0b1024ddd79a17520db6ab870e8b`, and runner SHA-256 `77a7f927b16568bf2656ee8d864a078a720ded53b1f134f31efe3e2e74270a2c`. Its run manifest pins PostgreSQL source `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`, Issue #101 protocol SHA-256 `7bd11b3743c5ca0467b4268cf47e8328f2bbe500fd53cea45a8efe3eab415787`, and Issue #101 runner SHA-256 `894b8276f58d36d7d513138e574a9832aa03b8e8a21f3dd84494dbc0367b9244`.

Issue #101's 250,000-call run is **not** counted as reusable. Its runner issued `EXPLAIN (FORMAT JSON, SUMMARY OFF)` and did not use the `ESS_DIAGNOSTICS true` option required by this protocol, so it fails the issue's exact diagnostic-option identity gate. Its summaries remain prior context only. No other configuration is reused.

Before the eventual execution, verify the external raw archive SHA and the eight reused arms' member offsets/hashes against the #105 manifest, and confirm from the recorded arm-completeness metadata that each has exactly 10,000 query records with complete Plan Rows and diagnostics. The raw query-level archive was not opened during this protocol phase. If any preflight integrity/completeness check fails, remove that arm from reuse and add its 10,000 calls to the new schedule; do not substitute a summary row for missing raw evidence.

## Frozen source, data, settings and physical-state checks

- AreCEL upstream: `aa52da7768023270bad884232972e0b77ec6534a`; source archive SHA-256 `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`.
- PostgreSQL research build: 16.14, source commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`, flags `--without-readline --without-zlib`, `make -j2`. This is the instrumented research build with `ESS_DIAGNOSTICS`, not pristine upstream PostgreSQL.
- Reuse Issue #101 protocol SHA-256 `7bd11b3743c5ca0467b4268cf47e8328f2bbe500fd53cea45a8efe3eab415787`, helper SHA-256 values recorded in its run manifest (`gate_audit_v2.py`: `03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4`; `run_formal.py`: `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322`). The frozen Issue #99 selection manifest and each sample's source-run ID/hash remain authoritative.
- Samples: Forest10 `95670277a138f577a7e21eb1567e0f6e1bce1ac489c10907c4a5662577d1aff8`; Census13 `0ff61bcce532a8af07f9319365c28d6fb07e373fc4b8049bae7c72c349baba26`; DMV11 `fc1013bb57547aaed5e15bab4de0f126ce21d0e781b5a66d7eabe21423fee249`; Power7 `a9cea3b48a2eddd7c8285256eabe26373f39c58ff45095d3940042a7bbb9eba7`. Require each Issue #99 sample header to identify PostgreSQL 16.14, target 90,000, the expected tuple count/natts and the matching dataset relation.
- Load each pinned full source table once per dataset into one run-local cluster; do not use a sample-only table. Keep the relation OID, file node and ordered column/type descriptor stable through that dataset's configurations. Replay the same frozen sample and ANALYZE for every arm. Use column target 300 and two-column MCV target 300.
- Use the original nonaggregate AreCEL query conversion and all 10,000 official Test qids. Planner startup GUCs are `client_min_messages=warning`, `plan_cache_mode=force_custom_plan`, and `max_parallel_workers_per_gather=0`. Use `EXPLAIN (FORMAT JSON, SUMMARY OFF, ESS_DIAGNOSTICS true)` and read the top-level `Plan Rows`.
- Before any arm's Test queries, assert that all and only the requested objects exist; verify candidate ID → columns, kind MCV, target 300, populated MCV data, and OID-sorted candidate sequence equal to the scheduled permutation. Retain OID mapping plus MCV values/frequencies/base-frequency fingerprints.
- Across permutations of a fixed set, ordinary-column-statistics and each candidate's MCV-content fingerprints must be identical. Across Nominal/PESS arms, ordinary statistics must remain identical and any shared selected candidate must have the same MCV fingerprint. A mismatch invalidates that arm before Test queries; preserve the failed state and status.
- Keep one relative OID order fixed for the entire 10,000-query arm: no DDL, writes, ANALYZE, or configuration changes during its six read-only planner clients; do not reuse prepared plans across arms. Dataset and arm schedules are serial; no parallel configurations.

The trusted pickle adapter materializes its split container but indexes only Test workload and Test labels, matching the disclosed Issue #101 boundary. It must not index, serialize, or use train/valid label values. For each query retain `dataset, configuration, permutation, query_id, source_index, Plan Rows, truth, Q-error, Plan Rows status, diagnostics status`; external compressed observations and a compact manifest/hash are required to recompute the exact summaries. Do not put large raw observations in Git.

## Estimands and reporting

For every dataset, frozen set (M), and permutation (pi), calculate query Q-error using the pinned AreCEL rule: both zero gives 1; estimate zero gives truth; truth zero gives estimate; otherwise use `max(estimate, truth) / min(estimate, truth)`. Apply static (r=1) and NumPy rounding to Plan Rows exactly as Issue #101 does. No result is defined for invalid/missing Plan Rows; keep every status.

The **primary** statistic for a set is

\[
\frac{1}{k!}\sum_{\pi\in S_k} P95_{q\in Test} Q(q,M,\pi).
\]

For each dataset report Δ = primary(PESS set) − primary(Nominal set), with negative values favoring PESS for this statistic. This is a difference between two exact finite-uniform expectations; it does not impose a pairing between permutations of different sets. Also report, per set, uniform-permutation expectations of query mean/P50/P99/max, the population SD (ddof=0) of permutation-level P95, and the minimum/maximum permutation-level P95. Use the same NumPy percentile convention as Issue #101. Query-level paired lower/higher/tie counts may compare per-query mean Q across each set's complete permutation family on the shared qids; mark these as descriptive. Keep Plan Rows and diagnostic completeness/status counts separate.

Do not substitute `P95_q(E_pi[Q])` for `E_pi[P95_q(Q)]`. Do not estimate from a subset of permutations, apply Monte Carlo, silently drop invalid queries, claim significance from this exact enumeration, or make a universal PESS-superiority claim. If any set lacks one or more of its (k!) valid, diagnostically complete arms, mark that set's exact expectation and its policy contrast **incomplete**; do not shrink its denominator. Retain all failed attempts and statuses.

## Cost forecast and proposed controls

**Observed baseline:** Issue #105 completed 80,000 EXPLAIN calls across eight arms in 135 seconds (2026-10-25 13:02:28–13:04:43 UTC), at 592.6 calls/s including its setup phases. At that aggregate rate, the planned 7,240,000 new calls project to 12,217 seconds, about **3.39 hours**; the no-reuse upper case of 7,320,000 calls projects to about **3.43 hours**. This is a linear extrapolation, not a runtime guarantee; the 724–732 repeated DDL/sample-replay arms are not represented at scale. The issue #101 ordinary-EXPLAIN run is not the estimator because its diagnostic option differs.

Issue #105 retained 6,516,233 compressed raw bytes for 80,000 calls (81.45 bytes/call). Linear scaling predicts about **589.7–596.2 MB / 562.4–568.5 MiB** of new compressed observations for 7.24–7.32M calls. Keeping the non-raw part of the #105 peak approximately fixed gives a projected peak near **3.51–3.52 GB / 3.27–3.28 GiB**; metadata and diagnostic-event mix may raise it. This is a measured-rate forecast, not a hard upper bound.

Proposed execution envelope for a separately approved run:

| Control | Proposed limit |
|---|---:|
| Schedule | 724 planned new arms / 7,240,000 attempts; hard maximum 732 arms / 7,320,000 attempts if none of the eight prior raw members passes final integrity checks; six planner clients per arm; no concurrent arms or extra test queries |
| Wall time | Early stop before starting another arm at 10 h; hard run limit 12 h |
| Allocated disk | Early stop before starting another arm at 7 GiB (7,516,192,768 bytes); hard cap 8 GiB (8,589,934,592 bytes) |
| Process concurrency | One dataset cluster at a time; at most six read-only planner clients; no concurrent DDL/configuration work |
| Failure policy | No query retries, skips, or outcome-based filtering; preserve unresolved statuses and failed attempt records |
| Checkpoint | After each complete arm, fsync its compressed member and atomically update the manifest with identity, hashes and call count; resume only at an arm boundary from the frozen schedule |

At an early limit, finish the current arm only if it can complete below the hard cap; otherwise stop and mark it incomplete. A hard time/disk stop leaves an incomplete run. Reuse only complete, hash-verified arm checkpoints. A partial arm never contributes to an exact expectation, and no incomplete set is reported with a reduced permutation denominator. Preserve raw observations and run logs externally; Git stores only this protocol, compact accounting/findings and hashes. The proposed 8-GiB cap is below the prior 20-GiB experiment cap because the observed baseline plus scaled raw estimate is about 3.27 GiB; the 7-GiB early stop leaves roughly 2.1× forecast headroom before the hard cap.

## Decision gate

The concrete proposal is **four datasets × frozen B=5 Nominal/PESS sets; exact 732-arm uniform schedules; plan to reuse the eight #105 Nominal canonical/reverse arms after raw-member integrity preflight; acquire 724 arms / 7.24M calls if all pass, with an absolute cap of 732 arms / 7.32M calls if none pass; six planner clients serially; 12-hour/8-GiB hard limits with 10-hour/7-GiB early stops; no retries or adaptive truncation**. The issue remains design-only until the researcher separately approves this execution envelope. No new official Test query was run for this protocol.
