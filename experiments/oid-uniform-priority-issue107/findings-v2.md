# Issue #107 — sampled uniform relative-OID Test findings

**Evidence label:** Experimentally observed PostgreSQL 16.14 measurements on the frozen AreCEL Test workloads. **This is a sampled estimate of a counterfactual uniform relative-OID deployment model, not an exact result for all 120 orders in every set and not a claim that PostgreSQL randomizes OIDs.**

## Frozen experiment and disposition

- Four datasets: Forest10, Census13, DMV11, Power7; B=5; frozen Issue #99 train-only Nominal/PESS sets; original AreCEL official Test split, 10,000 queries per physical configuration.
- The frozen schedule remains 156 arms: 96 Nominal, 48 five-object PESS samples, and 12 three-object PESS census arms. Issue #105 canonical/reverse Nominal orders remain fixed certainty units. The original run completed 144 arms; its only 12 incomplete arms were the predeclared Forest10/Power7 three-object PESS censuses.
- After the researcher authorized only those same 12 arms, continuation run `20261026T062137Z-issue107-pess3-cont-v1` completed each exact frozen order. It performed 120,000 EXPLAINs, 10,000 per arm, with no redraw or additional configuration. The original run's 12 pre-EXPLAIN failures and their errors remain in its manifest and in the combined analysis history.
- **Event A — Issue #105 fixed-arm reuse:** the eight fixed Nominal orders were not reused and were measured at their same frozen positions in the original run. The archived audit passes all global and per-arm configuration/member checks; its only retained rejection label is `raw observation identity/recomputation failed`. The exact row-level exception was not preserved, so its underlying cause remains unknown. This is separate from Event B below.
- **Event B — three-object PESS precheck:** the original runner rejected the 12 Forest10/Power7 PESS census arms before EXPLAIN because its catalog validator hard-coded five objects. That unrelated check was corrected to compare against the selected-set size; under separate authorization, only those same 12 arms were completed. Thus the final result contains 156 newly measured configurations and **1,560,000 cumulative EXPLAINs**, exactly the absolute authorized ceiling.
- Continuation status: **COMPLETE**; 12/12 arms and all 120,000 query outcomes valid, with complete Plan Rows and diagnostics. Original run: 1,440,000 calls, 474.496 s, peak allocated run storage 3,969,179,648 bytes. Continuation: 120,000 calls, 120.132 s, peak allocated run storage 814,166,016 bytes. Both remained below the 2 h / 4 GiB early-stop thresholds and the 3 h / 5 GiB per-run hard caps. The sum of the two recorded peak values is 4,783,345,664 bytes (about 4.46 GiB); that sum is not a measured simultaneous peak.
- Continuation source commit: `2bea487dfb5cbdbc637fd27bd4ecd42e1c845827`. Environment: CPython 3.12.3, NumPy 2.3.4, PostgreSQL 16.14 source commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`. The original and continuation used the same pinned Issue #101 protocol, settings, Test inputs and Issue #99 ANALYZE sample; continuation preflight compared its Test identity and sample hash with the parent run before collecting the target arms.
- The original run's raw archive SHA-256 is `d90b4600754fe2dedeb1e7dfc1ccfe75c2de325d630bca565150d1c8218cd767`; its manifest SHA-256 is `360af848afa93d54a958348981c5764dc643a9fccf0ff4e1b30eaf925eec44e3`. Continuation raw archive SHA-256 is `27e0a437f5eda7a87be712fe9850bfa939b07df03eed84169b27868a34707ea5`; continuation manifest SHA-256 is `639b6c30e2a168d13077a2d3866d598da8612f780285c34b3c6f142748e3d549`. The externally retained combined analysis SHA-256 is `7861f15ff62978a23f3a76307afa67fa8bceaf62a75ceacc43ff3c534a67ea3e`.
- External run roots are under `$ESS_RUNTIME_PARENT/ess-research/issue107/runs/`: `20261026T055503Z-issue107-sampled-v1/` and `20261026T062137Z-issue107-pess3-cont-v1/`. The combined analysis is `20261026T062137Z-issue107-pess3-cont-v1/combined-analysis.json`. Both raw archives and manifests are retained outside Git; no query-level measurements were added to the repository.

## Estimand and design-based uncertainty

For each fixed unordered statistics set \(M\) and sampled global relative OID order \(\pi\), the runner computes

\[
Y_\pi=\operatorname{P95}_{q\in Test} Q(q,M,\pi),\qquad
\mu(M)=\mathbb E_\pi[Y_\pi].
\]

One order is used for all 10,000 queries of a configuration. The target is the mean of the per-order Test P95 values, **not** the P95 across queries of permutation-averaged Q-error. Q-error uses Issue #101's Plan Rows rounding, zero handling and metric implementation.

For Nominal, let \(A\) be the two fixed #105 orders and let \(R\) be the residual population of 118 orders. With \(n=22\) SRSWOR draws from \(R\), \(F\) the fixed-order mean, \(S\) the sampled residual mean, and \(s_R^2\) the sample variance using denominator \(n-1\):

\[
\widehat\mu_N=\frac{2}{120}F+\frac{118}{120}S,\qquad
\widehat{\operatorname{Var}}(\widehat\mu_N)=
\left(\frac{118}{120}\right)^2\left(1-\frac{22}{118}\right)\frac{s_R^2}{22}.
\]

The fixed orders are certainty units and contribute no sampling variance. For each five-object PESS set, the 24 orders are SRSWOR from 120, so

\[
\widehat\mu_P=\bar Y_s,\qquad
\widehat{\operatorname{Var}}(\widehat\mu_P)=
\left(1-\frac{24}{120}\right)\frac{s_s^2}{24}.
\]

For each three-object PESS set, all six orders were measured; its permutation-sampling variance is zero by census. For the independent PESS-minus-Nominal contrast, the point estimate is \(\widehat\mu_P-\widehat\mu_N\), and its design variance estimate is the sum of the two design variance estimates. Reported intervals are the frozen approximate \(\widehat\mu\pm t_{0.975,21}\,SE\) intervals. They quantify permutation-sampling error only; they do not include uncertainty from treating these fixed 10,000-query Test workloads as samples from another query population.

The same certainty/SRSWOR weights and finite-population variance correction are used for each configuration's Mean Q-error, P50 and P99. The P95 permutation SD estimate uses the finite-population second-moment estimator, correcting for estimation of the population mean; a negative noisy variance estimate is truncated at zero and flagged by the analysis code. A sample maximum is an observed maximum, not a global worst order.

## Primary result: expected P95 Q-error

Values are rounded to four decimals. Confidence intervals use the frozen approximate t multiplier.

| Dataset | Nominal estimate (SE) | Nominal 95% interval | PESS estimate (SE) | PESS 95% interval |
|---|---:|---:|---:|---:|
| Census13 | 7.4813 (0.1835) | [7.0997, 7.8630] | 6.2837 (0.0000) | [6.2837, 6.2837] |
| DMV11 | 33.1024 (1.1500) | [30.7108, 35.4941] | 26.8561 (<1e-12) | [26.8561, 26.8561] |
| Forest10 | 13.8901 (0.0355) | [13.8162, 13.9640] | 14.0000 (0.0000) | [14.0000, 14.0000] |
| Power7 | 9.9283 (0.0975) | [9.7254, 10.1311] | 9.9576 (0.0000) | [9.9576, 9.9576] |

| Dataset | PESS − Nominal estimate (SE) | Approximate 95% interval |
|---|---:|---:|
| Census13 | −1.1976 (0.1835) | [−1.5793, −0.8160] |
| DMV11 | −6.2463 (1.1500) | [−8.6379, −3.8546] |
| Forest10 | +0.1099 (0.0355) | [+0.0360, +0.1838] |
| Power7 | +0.0293 (0.0975) | [−0.1735, +0.2322] |

The sampled estimates differ by dataset. For Power7, the contrast interval includes zero. Census13's five-object PESS sample has zero observed variation among its 24 sampled orders, hence a degenerate zero-width interval; that does **not** establish that the unsampled 96 orders have the same P95. The Forest10 and Power7 three-object PESS values are exact means over their six-order populations, conditional on the fixed Test workload.

## Auxiliary expected metrics and permutation spread

Each cell below is the design-weighted expected per-order metric followed by its design SE in parentheses. These are expectations of each order's Mean/P50/P99, not quantiles of a permutation-averaged query distribution.

| Dataset | Policy | Mean Q-error (SE) | P50 (SE) | P99 (SE) |
|---|---|---:|---:|---:|
| Census13 | Nominal | 2.5154 (0.0353) | 1.2011 (0.0005) | 19.7882 (0.6382) |
| Census13 | PESS | 2.2805 (0.0000) | 1.2310 (0.0000) | 16.0000 (0.0000) |
| DMV11 | Nominal | 28.3647 (1.4836) | 1.1137 (0.0010) | 822.9139 (57.9071) |
| DMV11 | PESS | 17.7429 (0.0000) | 1.1114 (0.0000) | 531.0250 (0.0000) |
| Forest10 | Nominal | 6.4683 (0.0050) | 1.1897 (0.0005) | 62.0578 (0.1013) |
| Forest10 | PESS | 6.4973 (0.0000) | 1.1916 (0.0000) | 62.1288 (0.0000) |
| Power7 | Nominal | 65.2768 (1.2719) | 1.0484 (0.0007) | 135.7652 (3.0547) |
| Power7 | PESS | 60.6523 (0.0000) | 1.0488 (0.0000) | 136.0523 (0.0000) |

Estimated finite-population SD of per-order P95 (same certainty/residual weighting for Nominal; finite-population correction for five-object PESS; exact six-order SD for three-object PESS):

| Dataset | Nominal | PESS |
|---|---:|---:|
| Census13 | 0.9657 | 0.0000* |
| DMV11 | 6.0911 | approximately 0.0000 |
| Forest10 | 0.1879 | 0.0000 (six-order census) |
| Power7 | 0.5093 | 0.0000 (six-order census) |

`*` The Census13 PESS SD estimate is zero because all 24 observed five-object sample values coincide; it is not evidence that all 120 population values coincide. DMV11's computed PESS standard error is approximately `6.63e-16`, a floating-point near-zero, not a substantive distinction.

## Event A — Issue #105 fixed-arm reuse failures

**Directly supported by retained evidence.** In the external parent manifest `$ESS_RUNTIME_PARENT/ess-research/issue107/runs/20261026T055503Z-issue107-sampled-v1/run-manifest.json`, the `issue105_reuse_audit` records `global_integrity_status: PASS`; expected, recorded-observed, and now-recomputed archive SHA-256 values agree. All 28 persisted global checks and all eight compressed-member hash/extent checks pass. For each of the eight fixed arms, every persisted provenance/configuration/sample/catalog/member check is true, but `eligible` is false and `reasons` contains only `raw observation identity/recomputation failed`. The source run was `20261025T130222Z-issue105-official-v2`; its retained manifest is `$ESS_RUNTIME_PARENT/ess-research/issue105/runs/20261025T130222Z-issue105-official-v2/run-manifest.json`, and its archive is `$ESS_RUNTIME_PARENT/ess-research/issue105/runs/20261025T130222Z-issue105-official-v2/raw-observations.jsonl.gz`. That manifest records all eight original configurations as complete with 10,000 valid observations and 10,000 valid Plan Rows each. A read-only SHA recheck of the compressed Issue #105 archive and its eight referenced members matched the recorded hashes; this check did not decompress rows.

The Issue #107 run's `logs/` directory contains no files. Its eight final fixed-arm records are `COMPLETE` with 10,000 valid observations and Plan Rows each, but neither those records nor the retained `attempts` entries contain the exception text or a `reuse_fallback_reason`. The original Issue #105 run manifest also has no row-level reuse exception because it predates this reuse attempt.

**Source-derived location, not a recovered exception.** At the exact Issue #107 runner commit used for the original run, [`run_issue107.py` lines 347–383](https://github.com/1951123/ess-research/blob/af6d01ea541c80cf9f9e4c4b8f0dca3fa7f53951/experiments/oid-uniform-priority-issue107/run_issue107.py#L347-L383), `_reused_rows` is programmed to check, in sequence, the member hash, gzip decoding, 10,000-row length, row identity/status/truth/Plan Rows, recomputed rounded Plan Rows and Q-error, and aggregate completeness. The broad `except Exception` at [lines 804–810](https://github.com/1951123/ess-research/blob/af6d01ea541c80cf9f9e4c4b8f0dca3fa7f53951/experiments/oid-uniform-priority-issue107/run_issue107.py#L804-L810) assigns the generic manifest reason `raw observation identity/recomputation failed` and falls back to measurement at the same scheduled order. This exact string occurs only at that catch site in the run's source. The catch temporarily assigns the exception string to an in-memory field, but that source revision does not serialize it into the retained arm or attempt records. The source establishes the catch path; it does not show which check the eight runs reached or failed.

Therefore the retained evidence locates all eight rejections at the `_reused_rows` reuse-validation stage, after the archive/provenance preflight and before the physical fallback. All eight received the same **generic catch label**; the evidence cannot establish that their underlying exceptions were identical. **具体拒绝原因未被持久化，无法从现存证据确认。** In particular, it cannot identify which row-level check failed, or establish that any Issue #105 measurement data were corrupt. No archive-level corruption or other persisted preflight failure was found; because the row-level exception is missing, a row-level compatibility issue cannot be ruled out. The eight exact fixed permutations were physically remeasured and all eight final Issue #107 records are complete; the reuse failure was an eligibility failure, not an invalid final physical measurement.

## Event B — separate three-object PESS precheck failures

The same parent manifest records 12 Forest10/Power7 PESS arms as `CONFIGURATION_INVALID`, each with `attempted_explain_calls: 0` and the error “relation does not have exactly the five selected statistics.” The original runner source at `af6d01e` shows [`validate_catalog_rows`](https://github.com/1951123/ess-research/blob/af6d01ea541c80cf9f9e4c4b8f0dca3fa7f53951/experiments/oid-order-stress-test-issue105/run_issue105.py#L111-L123) hard-coded `len(rows) != 5`; these frozen sets select three objects. The correction in the Issue #107 branch checks `len(rows) != len(selected)` ([current validator](https://github.com/1951123/ess-research/blob/research/issue107-uniform-oid-protocol/experiments/oid-order-stress-test-issue105/run_issue105.py#L111-L124)). The separately authorized continuation `20261026T062137Z-issue107-pess3-cont-v1` measured only those same 12 identities, completed all 120,000 EXPLAINs, and changed neither the sample nor the eight Nominal certainty orders. This catalog-size error did **not** cause Event A: Event A's eight configurations are five-object Nominal fixed orders and were rejected in the distinct `_reused_rows` path.

## Remaining integrity and statistical limitations

- Continuation preflight verified the parent run and exact 156-arm schedule; it selected only the 12 prior `CONFIGURATION_INVALID` arms with no raw member, no plan batch, and zero attempted calls. It matched parent Test input identities and fixed ANALYZE sample hashes before measurement. Post-run verification checked the 12 frozen arm identities, 10,000/10,000 query and diagnostic counts, compressed raw-member hashes/contiguity, and the cumulative call ceiling. Raw rows were not decompressed for this continuation integrity audit, and no query-level outcome was used to alter the frozen sample.
- The uniform order is a counterfactual assumption over relative OID order. These measurements do not establish random OID assignment in deployed PostgreSQL, a general PESS advantage, or behavior beyond the four fixed datasets, B=5 selections, pinned PostgreSQL build/configuration and official Test workloads.
- Approximate t intervals can have imperfect coverage under skewed/discrete finite-population outcomes. A zero estimated variance can produce a degenerate interval despite unobserved population variation; query-workload uncertainty is outside these intervals. No adaptive sample extension or result-driven order selection occurred.
- The initial and continuation attempts are separate immutable run roots. The first run's three-object validation failures remain preserved; the final analysis combines its 144 complete arms with the 12 completed continuation arms while retaining the failure history. No additional Test EXPLAIN is authorized by this report.

## Implementation checks

At the clean experiment source tree content committed as `2bea487dfb5cbdbc637fd27bd4ecd42e1c845827`, `py_compile` passed for the continuation runner and test module. `PYTHONPATH=src .venv/bin/python -m unittest tests/test_oid_sampling_issue107.py -v` passed all 13 synthetic tests, including the exact-12 continuation boundary and rejection of any additional or previously attempted failed arm. `git diff --check` passed. A pre-execution audit verified all 156 frozen identities, all 144 prior compressed raw members and the 1,440,000-call parent total without decompressing query rows; the continuation preflight then constrained the remaining work to the 12 zero-call targets.
