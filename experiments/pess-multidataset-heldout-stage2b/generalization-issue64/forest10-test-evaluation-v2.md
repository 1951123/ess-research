# Forest10 official test evaluation v2

**Disposition: `COMPLETE` for the frozen Forest10 evaluation; scientific scope is limited to the common Nominal/PESS-selected deployments versus Empty.** This report supersedes the failed execution status in v1, but preserves v1 and its 30,000 unresolved observations unchanged.

## Frozen design and execution

- Plan: [`forest10-test-evaluation-plan-v2.json`](forest10-test-evaluation-plan-v2.json), SHA-256 `a7d89c6317e1fca13ed83a578c54d72e4dc3ad7793b961a99714b5cb4c5c098d`; execution commit `694e88610511b20b3ef4b99dfd271d1cda35ebf3`.
- Frozen selection input: [`forest10-valid-frozen-selection-v1.json`](forest10-valid-frozen-selection-v1.json), SHA-256 `10bcf1f6026aa4de025cbef360c8302aafb2f082d49138c4c5da2d1331f4c798`. Distinct deployments were Empty, B2 `{e01_06,e02_07}`, B3 `{e01_06,e02_07,e03_04}`. Nominal and PESS sets are identical at every budget.
- New run: `f10-test-eval-jb18tnei`. One private PostgreSQL 16.14 build and cluster from `ess-postgresql` commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; PR #58 helpers from `76106024611ae91505f1f05bdc35aed44d9c38c4`. The newly exported same-run `public.forest10` sample was 10,620,460 bytes, SHA-256 `469b2c298cfcb48e7a7d3afa253c70ffeba5ed27226857c54a877e6df7a2c1fd`.
- The fixed Empty transport check on `arecel:forest10:test:000000` passed. Its Plan Rows was discarded; only parser acceptance was used. The unchanged evaluation then attempted exactly 30,000 calls (10,000 queries × 3 deployments), with 30,000 valid rows and zero unresolved rows. Total in this run: 30,001 calls. Across v1's one complete attempted schedule and this run, 60,001 calls were within the newly frozen aggregate cap; v1 remains immutable.
- The pinned AreCEL archive SHA-256 was `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`; ordered workload SHA-256 `246fdaf9408971a306cc963c59baa5cf50095eb08658fc789f8497a1156fafef`; truth file SHA-256 `dc7f500769468109e87c3d257e2a069d0ceb6943555938bd8687e9fb2ae62cf0`.

## Results

Q1 is `max(estimate, truth, 1) / max(min(estimate, truth), 1)`. Quantiles are nearest-rank over all 10,000 queries. Mean absolute natural-log error uses the 9,376 query pairs with strictly positive estimate and truth.

| Deployment (same for Nominal/PESS) | P50 Q1 | P95 Q1 | P99 Q1 | Max Q1 | Mean absolute log error |
|---|---:|---:|---:|---:|---:|
| Empty | 97723/80540 (1.213347) | 17 | 71 | 9438 | 0.697851 |
| B2 | 5591/4698 (1.190081) | 805/54 (14.907407) | 63 | 9438 | 0.635823 |
| B3 | 44095/36967 (1.192821) | 14 | 123/2 (61.5) | 9438 | 0.622997 |

The exact per-query Nominal/PESS comparison is a tie on all 10,000 queries at B=0, B=2 and B=3 (zero benefits, zero harms, 10,000 ties per budget), because each method deploys the same set. In this run, the two nonempty common sets had lower test P95 and mean absolute log error than Empty; maximum Q1 was unchanged. This is an observed result for these fixed Forest10 deployments and this official test split, not evidence that PESS outperforms Nominal.

## Integrity, resource use, and limits

- Compact query-level evidence: [`forest10-test-evaluation-v2.jsonl.gz`](forest10-test-evaluation-v2.jsonl.gz), 30,000 rows, 429,982 bytes, SHA-256 `71359d64523173a316a6daade852b75c8b847b947c48c47372df44697bfc1506`. Independent verification confirmed all rows `VALID`, exact 10,000-query ordered coverage for each of three distinct deployments, nonnegative integer Plan Rows/truth, and exact Q1 recomputation. Selection aliases retain the identical Nominal/PESS mapping.
- Build/install: 93.702 s; compile 81.842 s; input identity 10.489 s; cluster start 0.432 s; sample export/ANALYZE 0.776 s; transport check 0.004 s; full EXPLAIN/evaluation 110.631 s. Total 220.405 s.
- Supervisor-measured peak run-directory allocation: 650,694,656 bytes. Neither the 7.5 h / 3 GiB early stop nor the 8 h / 4 GiB hard cap triggered. PostgreSQL shutdown: PASS.
- No retries, alternate queries, changed candidates, altered selections, test-based tuning, calibration objective or resource optimization occurred. No MCV selection mechanism is claimed from this ordinary Plan Rows evaluation.
- The official AreCEL split has known template overlap and earlier Stage 2B test exposure; this is not an unseen-template or untouched confirmatory evaluation. Because Nominal/PESS selections coincide, this run cannot identify a PESS-versus-Nominal policy advantage. Results do not establish transfer beyond Forest10 or beyond the fixed sample/environment and frozen choices.
- Historical v1 and its failure observations remain unchanged. No test query/result was selected or used to modify the frozen design.
