# Forest10 Stage 2B — scoped scientific closeout

**Status: completed for the first Forest10 milestone; PR #65 remains Draft and Issue #64 remains Open for review.** This is not a claim that the broader multi-dataset study or a PESS advantage has been established.

## Frozen protocol and valid-only decision

The experiment used the official Forest10 split, 45 workload-supported pair candidates, budgets `B=0,2,3`, and the frozen corrected-log model. Valid calibration used all 10,000 official valid queries: 10,000 Empty plus 164,088 statically eligible singleton observations, for **174,088 observations across 46 configurations**. All recorded positive finite pre-clamp estimates were retained, including values below one and `NO_MCV_EVENTS` rows. Acquisition integrity passed; 87,404 rows contained verified MCV events and 86,684 were `NO_MCV_EVENTS`.

The corrected-log model was fitted using valid truth only. Complete exact feasible-subset enumeration produced one unique optimum for each method and budget; Nominal and PESS selected exactly the same sets:

| Budget | Exact objective (both methods) | Unique frozen set |
|---:|---:|---|
| 0 | `23326825631265146269149/1000000000000000000` | `{}` |
| 2 | `4374828918765339127297/200000000000000000` | `{e01_06,e02_07}` |
| 3 | `21512755121155336377967/1000000000000000000` | `{e01_06,e02_07,e03_04}` |

Thus this experiment has **no Nominal-versus-PESS treatment contrast**. Equality of the selected sets is an observed result for this Forest10 validation fit, not proof that their objectives are identical on all feasible sets.

## Official test evaluation

Using the frozen sets, the ordinary PostgreSQL `Plan Rows` estimate was evaluated against all 10,000 official Forest10 test truths for each of the three distinct deployments (30,000 accepted rows; no unresolved rows). Q1 is `max(estimate, truth, 1) / max(min(estimate, truth), 1)`; quantiles use nearest rank.

| Deployment | P50 Q1 | P95 Q1 | P99 Q1 | Max Q1 | Mean absolute log error |
|---|---:|---:|---:|---:|---:|
| Empty | 1.213347 | 17 | 71 | 9438 | 0.697851 |
| B2 | 1.190081 | 14.907407 | 63 | 9438 | 0.635823 |
| B3 | 1.192821 | 14 | 61.5 | 9438 | 0.622997 |

Relative to Empty's P95 Q1 of 17, B2 decreased by **2.092593 (12.309%)** and B3 by **3 (17.647%)**. These are observed comparisons for the frozen deployments and tested environment; they do not establish a PESS advantage. Since the Nominal and PESS set coincide at each budget, all 10,000 paired comparisons at each budget are ties.

## Evidence and scientific boundary

- [Frozen valid fit and exact selections](forest10-valid-fit-selection-v1.md) and [machine-readable frozen selection](forest10-valid-frozen-selection-v1.json).
- [Test evaluation report](forest10-test-evaluation-v2.md), [frozen v2 plan](forest10-test-evaluation-plan-v2.json), and [30,000 compact query-level observations](forest10-test-evaluation-v2.jsonl.gz).
- The complete test run used an independently built PostgreSQL 16.14 at commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`, the pinned PR #58 helper `76106024611ae91505f1f05bdc35aed44d9c38c4`, and one fresh same-run sample. Runtime was 220.405 s; measured peak run-directory allocation was 650,694,656 bytes; watchdog did not stop the run and the cluster shut down normally.
- Historical test exposure and known template overlap constrain interpretation: this is official-split performance, **not unseen-template generalization or untouched confirmatory evidence**. It covers Forest10 only, one fixed sample/environment and these frozen selections. Q1 is based on rounded/clamped top-level `Plan Rows`, not the model's pre-clamp loss. The test evaluation did not collect MCV-selection traces, so it makes no claim about which statistic PostgreSQL selected.
- Historical v1 parser failures and all prior reports remain unchanged. No selection was retuned from test outcomes. The exact raw valid/test observations and report hashes are recorded in `SHA256SUMS`.

No further PostgreSQL run, model change, resource selection or test analysis is authorized or proposed by this closeout. Stop for researcher and ChatGPT review; do not merge PR #65 or close Issue #64 automatically.
