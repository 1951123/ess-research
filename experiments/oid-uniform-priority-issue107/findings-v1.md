# Issue #107 — sampled uniform relative-OID Test evaluation

- Evidence label: **experimentally observed PostgreSQL measurements**.
- Run ID: `20261026T055503Z-issue107-sampled-v1`; source commit: `af6d01ea541c80cf9f9e4c4b8f0dca3fa7f53951`.
- Status: **INCOMPLETE**; attempted new EXPLAIN calls: 1440000.
- Raw new-arm observations SHA-256: `d90b4600754fe2dedeb1e7dfc1ccfe75c2de325d630bca565150d1c8218cd767`.
- Estimand: uniform-permutation expectation of the per-order Test P95; intervals cover only order sampling.
- One global OID order applied to all 10,000 Test queries per arm; six planner clients; serial configurations.
- Primary statistic is `Y_pi = P95_{q in Test} Q(q,M,pi)` and target is `E_pi[Y_pi]`, not the P95 across queries of `E_pi[Q]`.
- Nominal uses `(2/120) F + (118/120) S`, with design variance `(118/120)^2 (1-22/118) s_s^2/22`; PESS five-object sets use the SRSWOR mean with `(1-24/120) s_s^2/24`; PESS three-object sets require all six arms.
- Contrast is PESS − Nominal, with independent-design variances added; intervals use the predeclared approximate `t(0.975,21)` multiplier and cover permutation sampling only.
- Frozen sample SHA-256: `0b6b247445ab81589c5c5ea7991215fd25e5c60cddf990bf07e3867cda9baa73`; root seed `17770611677888985956`; RNG `ess-splitmix64-fisher-yates-v1`.
- Environment: Python `3.12.3`, NumPy `2.3.4`, PostgreSQL `PostgreSQL 16.14` at `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`.
- Command: `PYTHONPATH=src:experiments/arecel-test-generalization-issue101:experiments/oid-order-stress-test-issue105:experiments/oid-uniform-priority-issue107 .venv/bin/python experiments/oid-uniform-priority-issue107/run_issue107.py --run-id 20261026T055503Z-issue107-sampled-v1`.

## Per-dataset estimates

### forest10

| Policy | Set size | Arms | Mean Q | P50 | Expected P95 | P99 |
|---|---:|---:|---:|---:|---:|---:|
| nominal | 5 | 24 | 6.468253 | 1.189743 | 13.89013 | 62.05779 |

nominal expected P95: `13.8901254`; design SE `0.0355466`; approximate 95% interval `[13.8162022, 13.9640485]`; permutation SD estimate `0.1879239`; observed sample P95 range `[13.50417, 14]`.
| pess | 3 | INCOMPLETE | — | — | — | — |

pess configuration failure: `forest10/forest10-pess-000-enumerated relation does not have exactly the five selected statistics`.

PESS − Nominal contrast: **INCOMPLETE**.

### census13

| Policy | Set size | Arms | Mean Q | P50 | Expected P95 | P99 |
|---|---:|---:|---:|---:|---:|---:|
| nominal | 5 | 24 | 2.515385 | 1.201069 | 7.481334 | 19.78816 |

nominal expected P95: `7.48133418`; design SE `0.183509`; approximate 95% interval `[7.09970531, 7.86296304]`; permutation SD estimate `0.9656998`; observed sample P95 range `[6.25, 8.388889]`.
| pess | 5 | 24 | 2.28054 | 1.230951 | 6.283689 | 16 |

pess expected P95: `6.2836887`; design SE `0`; approximate 95% interval `[6.2836887, 6.2836887]`; permutation SD estimate `0`; observed sample P95 range `[6.283689, 6.283689]`. **DEGENERATE SAMPLE VARIANCE:** the 95% interval is not evidence of zero permutation uncertainty.

PESS − Nominal expected P95: `-1.19764548`; design SE `0.183509`; approximate 95% interval `[-1.57927434, -0.816016614]`.

### dmv11

| Policy | Set size | Arms | Mean Q | P50 | Expected P95 | P99 |
|---|---:|---:|---:|---:|---:|---:|
| nominal | 5 | 24 | 28.36474 | 1.113731 | 33.1024 | 822.9139 |

nominal expected P95: `33.1024047`; design SE `1.15005`; approximate 95% interval `[30.7107517, 35.4940578]`; permutation SD estimate `6.091103`; observed sample P95 range `[22.22596, 36.65788]`.
| pess | 5 | 24 | 17.74294 | 1.111373 | 26.85613 | 531.025 |

pess expected P95: `26.8561275`; design SE `6.62585e-16`; approximate 95% interval `[26.8561275, 26.8561275]`; permutation SD estimate `5.840039e-07`; observed sample P95 range `[26.85613, 26.85613]`.

PESS − Nominal expected P95: `-6.24627727`; design SE `1.15005`; approximate 95% interval `[-8.63793033, -3.8546242]`.

### power7

| Policy | Set size | Arms | Mean Q | P50 | Expected P95 | P99 |
|---|---:|---:|---:|---:|---:|---:|
| nominal | 5 | 24 | 65.27682 | 1.048397 | 9.92829 | 135.7652 |

nominal expected P95: `9.92829041`; design SE `0.097538`; approximate 95% interval `[9.72544902, 10.1311318]`; permutation SD estimate `0.5093437`; observed sample P95 range `[9.222867, 11.00043]`.
| pess | 3 | INCOMPLETE | — | — | — | — |

pess configuration failure: `power7/power7-pess-000-enumerated relation does not have exactly the five selected statistics`.

PESS − Nominal contrast: **INCOMPLETE**.

## Limits and interpretation

The confidence intervals use the frozen finite-population SRSWOR variance estimates and an approximate df=21 t critical value. They do not cover query/workload uncertainty, and are not exact coverage guarantees for skewed or heavy-tailed order outcomes. The sampled schedule is not full-permutation enumeration; sample extrema are not global extrema except for a complete census.

A configuration with missing Plan Rows or any diagnostics status other than `complete`/`empty` is invalid. No order was dropped, replaced, or added in response to its outcome. A set or contrast with any incomplete arm is reported incomplete.

## Execution disposition

- Frozen arms recorded: `156/156`; completed query arms: `144`; invalid before/within execution: `12`; reused #105 arms: `0`.
- #105 archive/provenance preflight: **PASS**. Row-level reuse eligibility after current-input and raw-row validation: `0`; rejected fixed arms were remeasured at the same frozen orders.
- Elapsed wall time: `474.496 s`; peak allocated run storage: `3969179648 bytes`.
- Authorized limits: early stop before next arm at 2 h or 4 GiB; hard limit 3 h or 5 GiB; maximum six planner clients per configuration. This run remained below both early-stop thresholds.
- The row-level #105 reuse fallback exception text was not persisted in this run manifest; the generic validation failure is retained. The eight fixed arms were physically measured at their unchanged orders.
- Post-run analysis revalidated schedule identity, aggregate row counts/statuses, and compressed-member hashes; it did not decompress raw rows or read query-level Q-error.

## Reproducibility and retained evidence

- Protocol v2 SHA-256: `07fe0b0ce20126c9ad98604e9dc25bf93187b2fee26093135e5136a9d7b8d7d5`; frozen permutation sample SHA-256: `0b6b247445ab81589c5c5ea7991215fd25e5c60cddf990bf07e3867cda9baa73`.
- Run source commit: `af6d01ea541c80cf9f9e4c4b8f0dca3fa7f53951`. Post-run analysis code commit: `a02001d8a29ba237ae80e31cda05a5b4f1687acc`; Issue #105 runner source hash at run commit: `77a7f927b16568bf2656ee8d864a078a720ded53b1f134f31efe3e2e74270a2c`.
- Run manifest SHA-256: `360af848afa93d54a958348981c5764dc643a9fccf0ff4e1b30eaf925eec44e3`. Post-run analysis SHA-256: `f4f773e49aa8d61d0a54d8d058dfcd819e547d1c60af7ce234ff75357998611f`.
- External run directory: `$ESS_RUNTIME_PARENT/ess-research/issue107/runs/20261026T055503Z-issue107-sampled-v1/`. It retains the run manifest, verified analysis, logs, and raw archive.
- Raw archive: `raw-observations.jsonl.gz`, 121645647 bytes, SHA-256 `d90b4600754fe2dedeb1e7dfc1ccfe75c2de325d630bca565150d1c8218cd767`. The 144 compressed members were hash-checked in order; the post-run audit did not decompress them or read query-level Q-error.
- #105 source metadata/member hashes passed global preflight. Row-level reuse validation rejected all eight fixed arms, so the runner remeasured their same frozen orders; the run manifest preserved only a generic rejection reason, not the exception detail. No arm was chosen or replaced using Q-error.
- The 12 invalid three-object PESS arms were not retried. The inherited validator fix is covered by synthetic test only; physical follow-up of those same 12 frozen orders requires renewed authorization.
