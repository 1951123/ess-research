# Issue #99 Phase A — train input feasibility

**Scientific question.** On each official AreCEL train split, what resources does the same deterministic add-only greedy rule choose under Nominal and task-wise PESS at proxy budgets 0, 2, 3, 4, and 5? Reuse the pinned archive/schema adapter, PR #7 structured EXPLAIN collector, and Issue #87 Advisor greedy/Fraction semantics; the minimum required observations are one empty-statistics estimate per train query and one singleton estimate per statically applicable schema pair.

## Preflight result

**Experimentally observed:** the archive-only static preflight was run on Python 3.12.3 with NumPy 2.5.4. It opened the pinned workload pickle member and iterated only `train`; it did not open the label pickle, start PostgreSQL, or select a valid/test workload. All four official train splits contain 100,000 queries, and every full schema pair has positive train support. The exact candidate order, full pair map, and per-pair train support hashes are frozen in [`protocol-v1.json`](protocol-v1.json).

| Dataset | Schema pairs | Train tasks with an applicable pair | Empty calls | Singleton calls | Total structured calls |
|---|---:|---:|---:|---:|---:|
| Forest10 | 45 | 90,026 | 100,000 | 1,641,931 | 1,741,931 |
| Census13 | 78 | 92,360 | 100,000 | 2,801,893 | 2,901,893 |
| DMV11 | 55 | 90,941 | 100,000 | 1,994,044 | 2,094,044 |
| Power7 | 21 | 85,830 | 100,000 | 802,535 | 902,535 |
| **Total** | **199** | — | **400,000** | **7,240,403** | **7,640,403** |

The archived source CSV members total 815,189,076 bytes. They are identified by upstream member hashes rather than copied into Git. The official workload and label pickle hashes are pinned in the protocol. Prior valid-only coefficient files are not suitable train inputs and will not be reused. The collector will select only the train workload and train label arrays; it does not create or pass valid/test labels or test observations to the fitter or selector.

## Resource estimate and bound

**Sizing estimate, not a train result:** the Issue #64 full-valid collection recorded 174,088 structured calls in 716.951 seconds across two workers (242.82 calls/second) and 6,408,799 allocated compressed observation bytes ([historical report](../pess-multidataset-heldout-stage2b/generalization-issue64/forest10-json-full-valid-collection-v1.md)). Applying that measured rate yields about 8.74 hours of structured EXPLAIN wall time across the four datasets, before dataset loading and PostgreSQL setup; the largest single dataset projection is Census13 at 3.32 hours. The observation-only compression projection is about 281 MB. These extrapolations may differ on train queries and the larger DMV table.

**Bounded execution:** run one dataset at a time with its own run-local PostgreSQL build/clusters and the existing Issue #64 envelope: stop at 7.5 hours or 3 GiB allocated disk, with hard limits of 8 hours or 4 GiB per dataset run. A stopped run is retained as incomplete; no train subsampling or partial model fit is allowed. The next dataset starts only after the active clusters stop. Collection evidence stays under `$ESS_RUNTIME_PARENT/ess-research/issue99/runs/`; the protocol records the exact call counts, historical sizing basis, early-stop thresholds, and hard caps.

## Model-input decision carried into execution

**Source-derived, conditional:** the existing Forest10 and Census13 fitted payloads are valid-only artifacts, so new coefficients must be fit from train truth and train-only PG observations. Preserve Forest10's positive pre-clamp transform and Census13's existing `max(1,x)` clamped-log transform. DMV11 and Power7 have no frozen fitted payload; use the paper's primary positive pre-clamp log loss with `T=max(1,N)` and require positive finite pre-clamp estimates before logs. If a positive-model input is zero/nonfinite or the PG observation contract fails, mark that dataset's model and dependent cases incomplete rather than adding an unapproved clamp. Natural logs use the existing 80-digit Decimal calculation quantized to `1e-18` with half-even rounding, then exact `Fraction` coefficients.

**Not claimed:** the unit candidate cost is a proxy and does not measure physical PG maintenance. The PR #7 instrumented PostgreSQL result is an estimator observation for this pinned build/sample, not a claim that all PostgreSQL queries select an MCV object. PESS ranges over the prescribed task-wise inclusion-maximal matching family, not all possible real PostgreSQL behavior. Greedy selections are heuristic and carry no global-optimum guarantee. This issue does not assess held-out generalization.
