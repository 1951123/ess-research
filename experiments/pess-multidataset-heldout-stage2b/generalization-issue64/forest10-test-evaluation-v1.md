# Forest10 official test evaluation v1 — INCONCLUSIVE

**Disposition: `INCONCLUSIVE_UNRESOLVED_ROWS`.** The frozen official-test schedule was attempted in one complete run, but none of the 30,000 ordinary EXPLAIN outputs was accepted by the Plan Rows parser. No Q1 percentile, mean log error, or paired benefit/harm/tie statistic is reported. This is a parser/transport failure, not evidence for or against any selected set.

## Frozen design and inputs

- Outcome-evaluation plan: [`forest10-test-evaluation-plan-v1.json`](forest10-test-evaluation-plan-v1.json), SHA-256 `bafee85b8d8be674c045610362f9a1af34eda3993f169c09a64c7df3aeb23f86`.
- Valid-only selection: [`forest10-valid-frozen-selection-v1.json`](forest10-valid-frozen-selection-v1.json), SHA-256 `10bcf1f6026aa4de025cbef360c8302aafb2f082d49138c4c5da2d1331f4c798`; status `FROZEN`.
- Frozen distinct deployments: Empty; B2 `{e01_06,e02_07}`; B3 `{e01_06,e02_07,e03_04}`. Nominal and PESS sets are identical at each budget, so this evaluation cannot establish a PESS-vs-Nominal resource-policy advantage even if Q1 is later measured successfully.
- Full official Forest10 test workload/truth identity: AreCEL archive SHA-256 `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`; 10,000 ordered workload IDs and 10,000 nonnegative truths. Workload JSON SHA-256 `246fdaf9408971a306cc963c59baa5cf50095eb08658fc789f8497a1156fafef`; truth JSON SHA-256 `dc7f500769468109e87c3d257e2a069d0ceb6943555938bd8687e9fb2ae62cf0`.
- PostgreSQL source: `ess-postgresql` commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`, independently built/installed as PostgreSQL 16.14 in the run. PR #58 helpers: commit `76106024611ae91505f1f05bdc35aed44d9c38c4`, `run_formal.py` SHA-256 `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322`, `gate_audit_v2.py` SHA-256 `03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4`.
- Evaluation code commit: `83ea05e7f68fe14afafd051dad6cb795a1d84230`. The subsequent offline-only parser transport correction is in the PR diff and has not been exercised against PostgreSQL.

## Attempts and observed status

| Run | Result | Test EXPLAIN calls | Elapsed | Peak allocated run disk | PG shutdown |
|---|---|---:|---:|---:|---|
| `f10-test-eval-oxy5v0ol` | FAILED before EXPLAIN: wrong PR #58 module passed to `configure_statistics` | 0 | 109.778 s | 636,637,184 bytes | PASS |
| `f10-test-eval-1_4n5nkl` | `INCONCLUSIVE_UNRESOLVED_ROWS`; all scheduled outputs failed JSON decoding | 30,000 attempted across 3 distinct sets × 10,000 queries; 0 accepted Plan Rows | 220.085 s | 650,444,800 bytes | PASS |

Both runs independently acquired the pinned helper and PostgreSQL source, built and installed PG 16.14, prepared `public.forest10`, and exported a new same-cluster sample. The second-run sample SHA-256 was `8a368a7df829384dcb887502d3c321186edd7868951a693aa3328ad4f571abcb` (10,620,460 bytes). No failed run, sample, build, or database was reused. The second run produced exactly 30,000 retained rows, all `UNRESOLVED / JSONDecodeError`; compact gzip evidence is [`forest10-test-observations.jsonl.gz`](runs/20261022-forest10-official-test-eval-v1/forest10-test-observations.jsonl.gz), SHA-256 `26a5a9d35ea63581be5cc4bbe72498692bb9bb19c8d5a16aa91a29b72bbe0154` (188,963 bytes). Each row keeps query ID, frozen selection aliases, test truth, unresolved status and error class; no Plan Rows or Q1 was fabricated.

The watcher used the frozen 7.5 h / 3 GiB early-stop and 8 h / 4 GiB hard limits. Neither run approached either limit; disk monitoring remained available. PostgreSQL was confirmed normally stopped in both runs. There was no retry of a partial schedule and no extra test query beyond the fixed 30,000-call schedule.

## Failure analysis and correction

In the first run, test inputs had been extracted after the plan and valid selection hashes were checked, but no test EXPLAIN ran. The failure was a runner wiring error: `gate_audit_v2` (cluster helper) was passed where PR #58 `run_formal` (statistics/psql helper) was required. This was corrected before the second independent run.

In the second run, all 30,000 observations contain `JSONDecodeError`. The prior implementation sent several `SET` statements and `EXPLAIN` together through ordinary psql output mode, then required the entire stdout to be one JSON document. Source inspection identifies command-status contamination as the likely cause. The raw stdout was not retained, so this causal detail is **source-derived, not directly verified from captured output**. The minimal code correction moves the same planner GUCs to startup `PGOPTIONS` and uses tuples-only output for one `EXPLAIN (FORMAT JSON, SUMMARY OFF)` statement. Its focused synthetic test and full offline suite pass, but this correction has **not** been live-tested.

The committed evaluation plan allowed at most 50,000 calls and fixed exactly 30,000 for this complete test evaluation. Repeating the full schedule would exceed that declared total; changing to a selected subset after seeing parser failures would alter the frozen schedule. Therefore execution stopped with an inconclusive result. Any further PostgreSQL test evaluation needs a newly reviewed/frozen plan and authorization; this report does not claim successful held-out evaluation.

## Scientific boundary

No Q1 metric is available, and the failure cannot be interpreted as a zero error, tie, or treatment comparison. Even a future successful run on these choices would evaluate common Nominal/PESS-selected sets against Empty, not distinguish Nominal from PESS because their deployed sets coincide. The claim would be limited to generalization under the official AreCEL split, not unseen templates; earlier Stage 1A/Stage 2B test exposure remains a limitation. No selection, coefficient, candidate, or protocol was changed in response to test values.

## Checks

After the transport correction: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s experiments/pess-multidataset-heldout-stage2b/generalization-issue64 -p 'test_*.py'` — **137 passed**; Python AST parse passed; `git diff --check` passed. These are offline checks, not a PostgreSQL validation of the correction.
