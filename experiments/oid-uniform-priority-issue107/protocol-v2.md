# Issue #107 — sampled uniform relative-OID Test protocol v2

**Status: protocol revision only; no execution authorization.** This version supersedes the unexecuted full-permutation proposal in [protocol v1](protocol-v1.md). It changes only how relative OID orders are sampled and how permutation-sampling uncertainty is estimated.

## Fixed scientific scope

The study retains Forest10, Census13, DMV11, and Power7; B=5 Nominal and PESS selections exactly as frozen by Issue #99; the Issue #101/#105 PostgreSQL 16.14 research build, full source tables, fixed Issue #99 samples, targets 300, planner settings, official Test queries, and Q-error definition. No selection is recomputed, and no other dataset or budget is added.

For each fixed unordered extstats set $M$, the target population is its $k!$ relative OID permutations, each with equal probability. A draw selects one global order for one physical configuration, and that same order is used for all 10,000 Test queries in the configuration. This is a counterfactual random-deployment assumption; it does not say PostgreSQL randomly assigns OIDs in production. Outcomes induced by different orders remain weighted by the number of orders that induce them.

This follow-up was specified after reading the prior Issue #101/#105 summaries. It is not prospectively untouched by those results. The sample below is generated from the frozen resource IDs and seed without using Q-error outcomes. No sample replacement, extension, or metric change may depend on results.

## Frozen sample and reproducibility

The authoritative selected IDs and candidate maps remain in `experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json`, SHA-256 `2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca`. `permutation-sample-v1.json` stores every selected permutation, its fixed/random/census status and inclusion probability, per-set SHA-256, and the complete design metadata. Its SHA-256 is `0b6b247445ab81589c5c5ea7991215fd25e5c60cddf990bf07e3867cda9baa73`.

The 64-bit root seed is **17770611677888985956**. It was drawn from the system CSPRNG and frozen before any new Test measurements. The versioned generator is `ess-splitmix64-fisher-yates-v1`: SplitMix64 with rejection-sampled `randbelow`, Fisher–Yates over a lexicographically enumerated residual population, taking the first $n$ entries. For each dataset/policy/set, the child seed is the first 8 bytes, big-endian, of SHA-256 over the UTF-8 NUL-delimited string `ess-issue107-seed-v1`, root seed, dataset, policy, and comma-joined sorted IDs. Independent child streams are used for the eight sets. The sample was generated with CPython 3.12.3; the custom RNG and canonical JSON serializer are versioned in the implementation [oid_sampling.py](../../src/ess_research/arecel/oid_sampling.py). Regenerate it from the frozen manifest with `PYTHONPATH=src python3 -m ess_research.arecel.oid_sampling`.

| Dataset / policy | $k!$ population | Fixed #105 orders | Random SRSWOR | Full census | Total selected | Child seed (hex) | Sample SHA-256 |
|---|---:|---:|---:|---:|---:|---|---|
| Forest10 / Nominal | 120 | 2 | 22 of 118 | 0 | 24 | `778e5245a11cf82e` | `6894f7317f3bdd976e00aec96d09db1f23f70bf092f4269f25f617e86e9159c3` |
| Census13 / Nominal | 120 | 2 | 22 of 118 | 0 | 24 | `70405be4a44cca31` | `0396a6ce4e14e102ac8ed49de37c8d96cdc4a00bf83347eb24b13378b32b9397` |
| DMV11 / Nominal | 120 | 2 | 22 of 118 | 0 | 24 | `e097a4592f1257b7` | `5c39dcea7e690d29d91d43246c2f35fcefb470eb9a051dcd63e4c6be2f963623` |
| Power7 / Nominal | 120 | 2 | 22 of 118 | 0 | 24 | `8bc8ec42f8356f12` | `1ebbce3843a4f71cb773ff47ee0ed2517e92930b4ba017a90c47dd7643a70371` |
| Census13 / PESS | 120 | 0 | 24 of 120 | 0 | 24 | `8f3154dce8fcb778` | `7dd2fbf3a4e7ba110e5f2786004c3be6be000e7f32f86aca9a7444de629a0749` |
| DMV11 / PESS | 120 | 0 | 24 of 120 | 0 | 24 | `826e8e81fbd78b58` | `2e7d25671473ef7dbc448d4ca81b4198ed7103dc20edf4e876fba6c9f9e8a904` |
| Forest10 / PESS | 6 | 0 | 0 | 6 | 6 | none | `2dc387a785fda6f5568f9b4dbfbe03aff7c505973006cf572f45f7df7d18cf70` |
| Power7 / PESS | 6 | 0 | 0 | 6 | 6 | none | `f261c0e9c8ee3f2e3464d3a55abbcc6f2a93db95433aa2236532e1e898fae0b4` |
| **Total** |  | **8** | **136** | **12** | **156** |  |  |

For each Nominal set the two fixed certainty units are the sorted candidate-ID order and its exact reverse. The random sample is drawn only from the other 118 orders, so neither fixed order can appear twice. A random order has first-order inclusion probability $22/118=11/59$; each fixed order has inclusion probability 1. In a five-object PESS set each of the 120 orders has inclusion probability $24/120=1/5$. The three-object PESS schedules contain every order once. The lists in the JSON file are the complete, frozen sample; no runtime redraw is permitted.

## Issue #105 reuse audit and fallback

The eight canonical/reverse Nominal configurations are fixed inclusions, not random sample members. Their configuration identity audit passed:

- The selected IDs, candidate-map hashes, source build, Issue #101 helpers/protocol, GUCs, query path, statistics targets and Issue #99 sample hashes match the frozen setup.
- For every arm, CREATE order matches the observed OID-sorted candidate IDs. The full-table identity, ordinary-column-statistics fingerprint, and per-candidate MCV content fingerprints agree within each canonical/reverse pair; the five target-300 MCV objects are populated.
- The #105 run manifest reports 10,000 queries, 10,000 valid Plan Rows, 10,000 complete diagnostics and zero unresolved queries for each arm. A byte-level audit also verified the external compressed archive SHA-256 (`ca2ada0f057f7b439eaee98900f0ae57883adebc84f98d184ec437c1defea9c2`) and all eight manifest-declared member offsets, lengths and SHA-256 values. The archive was not decompressed; no per-query Q-error values were read or used to choose the sample.

Issue #101 configurations are not reused because that run omitted `ESS_DIAGNOSTICS true`, which is part of the required configuration identity. Before an approved execution, repeat the #105 archive/member integrity check and compare the saved configuration metadata with the frozen manifest. If any of the eight fixed arms fail that preflight, remeasure that same canonical/reverse permutation; do not replace it with a random permutation or change the seed. If all pass, 8 arms are reused; otherwise at most all 8 are new. No Q-error value participates in this gate.

## PostgreSQL protocol and validity gate

For each selected arm, create only its frozen set in the sample's listed relative order, replay the exact Issue #99 sample, and ANALYZE the existing full source table. Use one run-local cluster/table per dataset, targets 300, and the Issue #105 instrumented PostgreSQL 16.14 build at `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`. AreCEL is pinned to upstream commit `aa52da7768023270bad884232972e0b77ec6534a`, archive SHA-256 `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`; the reused Issue #101 protocol SHA-256 is `7bd11b3743c5ca0467b4268cf47e8328f2bbe500fd53cea45a8efe3eab415787`. The four fixed-sample SHA-256 values remain those in protocol v1 and the Issue #101 protocol. Verify the full-table/source identity, relation identity, sample hash/header, all-and-only requested statistics, candidate-to-column mapping, MCV kind/target/population, OID order, and ordinary/MCV content fingerprints before Test queries. Ordinary statistics must be invariant over all arms for a dataset; a shared candidate's MCV fingerprint must agree across Nominal/PESS arms.

Run all 10,000 official Test queries within each arm using six read-only planner sessions on the same deployment/order. Use the Issue #101 planner GUCs and `EXPLAIN (FORMAT JSON, SUMMARY OFF, ESS_DIAGNOSTICS true)`, read top-level `Plan Rows`, and do not reuse prepared plans across arms. No DDL, ANALYZE, data writes, or configuration changes occur during an arm. Preserve per-query Plan Rows and diagnostic statuses externally. Continue to disclose the trusted-pickle container boundary: materialize the split container but index only Test workload and Test labels; do not index, serialize, or use train/valid label values.

For Plan Rows, preserve Issue #101's static $r=1$, NumPy rounding, and AreCEL zero-aware Q-error. If estimate $e$ and truth $t$ are both zero, set $Q=1$; if only $e=0$, set $Q=t$; if only $t=0$, set $Q=e$; otherwise set $Q=\max(e,t)/\min(e,t)$. Compute each permutation statistic across all 10,000 Test queries using the same NumPy percentile convention as Issue #101.

## Estimands, finite-population variance and intervals

For each permutation define $Y_\pi=\operatorname{P95}_{q\in Test}Q(q,M,\pi)$. The target for one fixed set is

\[
\mu(M)=\frac{1}{k!}\sum_{\pi\in S_k}Y_\pi
=\mathbb E_{\pi\sim Uniform(S_k)}[P95_{q\in Test}Q(q,M,\pi)].
\]

This is not $\operatorname{P95}_{q}(\mathbb E_\pi Q)$. The full Test split is fixed for this estimand; the interval below covers only relative-permutation sampling error, not workload/split uncertainty.

**Nominal with two fixed orders.** Let $A$ be the two certainty orders, $R=118$ the residual population size, and $s$ the SRSWOR sample of $n=22$. Let $F=\frac12\sum_{\pi\in A}Y_\pi$, $\bar Y_s=n^{-1}\sum_{\pi\in s}Y_\pi$, and $s_s^2=(n-1)^{-1}\sum_{\pi\in s}(Y_\pi-\bar Y_s)^2$. The unbiased estimate of the full 120-order mean and its design-variance estimate are

\[
\widehat\mu_N=\frac{2}{120}F+\frac{118}{120}\bar Y_s,
\qquad
\widehat{Var}(\widehat\mu_N)=\left(\frac{118}{120}\right)^2\left(1-\frac{22}{118}\right)\frac{s_s^2}{22}.
\]

The fixed values are certainty units and contribute no design variance. The random residual units are an equal-probability SRSWOR; this is not the unweighted mean of the 24 observed values.

To derive the variance, let $S_R^2=(R-1)^{-1}\sum_{\pi\in R}(Y_\pi-\bar Y_R)^2$ be the residual finite-population variance. Under SRSWOR, $\mathbb E[s_s^2]=S_R^2$ and $\operatorname{Var}(\bar Y_s)=(1-n/R)S_R^2/n$. Since the fixed contribution is known and the residual mean is multiplied by $R/120$, the variance of the full-population mean estimator is $(R/120)^2(1-n/R)S_R^2/n$. Replacing $S_R^2$ with its unbiased sample estimate $s_s^2$ gives the stated design-unbiased variance estimator. For PESS five-object sets, use the same SRSWOR identity with $R=N=120$ and $n=24$.

**PESS five-object set.** For $N=120,n=24$, use $\widehat\mu_P=\bar Y_s$ and $\widehat{\operatorname{Var}}(\widehat\mu_P)=(1-24/120)s_s^2/24$.

**PESS three-object set.** All $N=n=6$ orders are enumerated. The expected statistic is their exact arithmetic mean and the permutation-sampling variance/SE of that mean is zero. The six $Y_\pi$ values may still have nonzero permutation dispersion.

The design standard error is the square root of the applicable design-unbiased variance estimate. The base SRSWOR correction is the usual finite-population correction (see [Penn State STAT 506, estimating a mean under SRS](https://online.stat.psu.edu/stat506/Lesson01)); the Nominal certainty-stratum factor follows by scaling the residual mean by $118/120$. Report the expectation as estimate $\pm t_{0.975,21}\,SE$, where $t_{0.975,21}=2.0796138447$. Using df=21 is the minimum residual-sample df and is a conservative Student-t critical value relative to df=23 for the PESS five-object stratum. This is an **approximate 95% design-based t interval**, not an exact finite-population coverage guarantee; the per-order P95 distribution may be skewed or heavy-tailed. If the sample variance is zero while the residual population is not exhausted, flag a degenerate interval and do not interpret it as certainty.

For each dataset report $\widehat\Delta=\widehat\mu_{PESS}-\widehat\mu_{Nominal}$. Independently derived child seeds make the set-specific sample designs independent, so

\[
\widehat{Var}(\widehat\Delta)=\widehat{Var}(\widehat\mu_{PESS})+\widehat{Var}(\widehat\mu_{Nominal}),
\]

Report this difference with a $t_{0.975,21}$ interval using the combined SE. Negative $\Delta$ favors PESS on expected P95. Do not pair orders from different sets or omit a covariance term while using correlated random streams.

For each permutation, define the secondary query statistics as mean Q-error, P50, and P99 across the fixed 10,000-query Test split. Estimate the permutation expectation of each with the same fixed-plus-residual or SRSWOR mean estimator and finite-population variance formula as the primary P95 statistic. Report the estimated permutation-population SD of P95 descriptively. Its finite-population variance target uses denominator $N$; estimate it with

\[
\widehat V_\pi=\widehat{N^{-1}\sum_\pi Y_\pi^2}-\widehat\mu^2+\widehat{Var}(\widehat\mu),
\]

where the second-moment total is the exact sum over fixed orders plus the residual population size times the sampled residual mean-square. The final correction makes the raw variance estimator design-unbiased; report $\sqrt{\max(0,\widehat V_\pi)}$ and flag if truncation was needed. For the three-object census, compute the SD across all six orders exactly. Report sampled minimum/maximum P95 only as **observed sample extrema**, never as global best/worst orders.

Any failed/missing Plan Rows or incomplete diagnostics makes that arm invalid for estimands requiring complete 10,000-query outcomes. Do not drop it, substitute a new permutation, or shrink the denominator. Finish the predeclared schedule where the environment remains valid, retain every status, and mark the affected set and its Nominal/PESS contrast **incomplete** if any selected arm is incomplete. A three-object census with a failed arm is not a complete enumeration. Do not add favorable orders if intervals are wide; report “evidence insufficient.”

## Configuration and resource budget

| Dataset | Nominal | PESS | Total arms | Reused #105 | New if reuse passes | New EXPLAIN |
|---|---:|---:|---:|---:|---:|---:|
| Forest10 | 24 | 6 | 30 | 2 | 28 | 280,000 |
| Census13 | 24 | 24 | 48 | 2 | 46 | 460,000 |
| DMV11 | 24 | 24 | 48 | 2 | 46 | 460,000 |
| Power7 | 24 | 6 | 30 | 2 | 28 | 280,000 |
| **Total** | **96** | **60** | **156** | **8** | **148** | **1,480,000** |

If no #105 arm passes integrity validation, the unchanged sample still has 156 configurations; remeasuring the fixed arms makes the maximum new-call count 1,560,000.

Issue #105 completed 80,000 calls in 135 seconds with six planner clients, including its setup phases. Linear scaling estimates 148 new arms at about **2,498 seconds / 41.6 minutes**; 156 new arms if reuse fails estimate about **2,633 seconds / 43.9 minutes**. This extrapolation has substantial uncertainty because the number of CREATE/DROP/sample-replay cycles grows from 8 to 148–156.

Issue #105's 6,516,233 compressed raw bytes for 80,000 calls imply approximately 120.6 MB for 1.48M new calls and 127.1 MB for 1.56M. Holding its non-raw peak approximately fixed gives a projected peak near **3.05 GB / 2.84 GiB** (plus manifest growth and workload-dependent diagnostic variation). This is an estimate, not a hard bound.

Proposed execution controls, pending separate approval:

| Control | Proposed limit |
|---|---:|
| Calls | 1.48M planned; 1.56M absolute maximum if all eight fixed arms must be remeasured |
| Wall | Stop before a new arm at 2 h; hard run limit 3 h |
| Allocated disk | Stop before a new arm at 4 GiB (4,294,967,296 bytes); hard cap 5 GiB (5,368,709,120 bytes) |
| Concurrency | One dataset cluster and one arm at a time; at most six read-only planner clients; no concurrent configurations |
| Checkpoint | After each complete arm, fsync its compressed member and atomically update manifest with sample ID, order, physical fingerprint, counts and member hash; resume only predeclared unattempted arms after revalidating cluster/input identity |
| Failure | No replacement draw or query retry; preserve failed/incomplete arm and statuses; its set has no complete expectation/CI |

The 2-hour early/3-hour hard limits are approximately 2.9×/4.3× the reuse-passing runtime extrapolation. The 4-GiB early/5-GiB hard limits provide about 1.4×/1.8× the estimated peak; they are lower than v1's 7/8-GiB proposal because this sample cuts new query volume from 7.24M to at most 1.56M while preserving six-worker parallelism. If a hard limit interrupts an arm, stop and retain an incomplete run; do not report a reduced-sample estimate as complete.

## Execution gate and current status

This amendment authorizes no AreCEL Test EXPLAIN/ANALYZE. The exact frozen schedule, estimators, synthetic tests, and proposed 3-hour/5-GiB envelope are reviewable in Draft PR #108. Start the physical sample only after a separate researcher execution approval. No result from this design is an exact full-permutation expectation; all sampled estimates and intervals must be labeled as such.
