# Issue #99 — official AreCEL train-only greedy sweep

**Scope:** official AreCEL train queries and train labels only; Forest10, Census13, DMV11, and Power7; budgets `B=0,2,3,4,5`; unit candidate cost is a proxy. This report makes no held-out generalization claim.

**Issue #96 preparation:** the 40 train resource configurations are frozen in [`frozen-train-resources-issue96-v1.json`](frozen-train-resources-issue96-v1.json). This freezes train selections only. No official Test labels or Test EXPLAIN observations were used, Issue #96 Test evaluation is not authorized by this artifact, and its remaining PostgreSQL measurement settings are not settled here.

## Evidence and interpretation

Selections were computed with the pinned deterministic `add_only_greedy` implementation. Nominal and task-wise PESS use exact `Fraction` objective values under the stated fitted train model; the outer selection is a heuristic and is not globally optimal by claim. PESS is the task-wise sum of per-task worst losses over the prescribed inclusion-maximal matching family. PostgreSQL observations are conditional on the pinned instrumented build and replayed sample; an EXPLAIN alone is not evidence that every real PostgreSQL plan selected an MCV statistic.

Train truth came from the pinned split-container label pickle. Standard unpickling materialized that container; the runner explicitly dereferenced only `train` and did not index, serialize, or use valid/test label values. No test EXPLAIN was run. Valid-only Issue #87 coefficients were not reused. Optional cross-objective fixed-set evaluation was not run. Training objective values describe the frozen training models and are not generalization accuracy.

Census13 PESS B=5 first stopped INCOMPLETE under the frozen 600-second Advisor / 900-second outer limit. The researcher authorized a continuation of this single case without wall-clock limits while retaining the 12-GiB memory, single-process/single-thread, 381 evaluation-call, and 464,100,000 matching-subset caps. The earlier attempt and a failed system-Python launch before solver start are preserved separately. The successful continuation completed 381/381 fixed-set evaluations in 723.79 seconds; its exact run and time-extension hashes are recorded per case in the frozen JSON.

The two-worker protocol-v1 Forest10 attempt was stopped at the researcher’s request for configurable parallelism after 98,616 successful observations; those observations were not reused. A first 12-worker v2 implementation attempt was stopped after detecting duplicate baseline scheduling; its 167,593 baseline rows were retained as INCOMPLETE. Forest10 and Census13 completed under v2’s 3/4-GiB disk limits. Protocol v3 used a 9.5-GiB early stop and 10-GiB hard cap; the scientific scope, PostgreSQL measurement, model fit, and selection limits matched v2. The v2 DMV11 12/11-worker attempts stopped during cluster setup at the old disk cap with zero observations; the 10-worker attempt was stopped by the researcher before observation collection when the cap was revised. Six DMV11 attempts under the initial v3 9-GiB early stop also ended during cluster setup with zero observations; their allocated-storage peaks stayed below the 10-GiB hard cap, and they are preserved separately. Revised 9.5-GiB early-stop attempts at 12, 11 and 10 workers stopped during setup with zero observations at about 10,497,945,600 peak bytes (9.78 GiB). The 12-worker attempt had worker0-worker4 directories present at the last live snapshot. A preliminary linear extrapolation suggests around 22-24 GiB for a complete 12-worker run; this is unverified. The researcher authorized the remaining DMV11 and Power7 collections at six workers under protocol v4’s 19-GiB early stop and 20-GiB hard cap.

## Cases

| Dataset | B | Nominal case | PESS case | Same selected set? |
|---|---:|---|---|---|
| forest10 | 0 | ∅ | ∅ | yes |
| forest10 | 2 | `e01_06, e02_07` | `e01_06, e02_07` | yes |
| forest10 | 3 | `e01_06, e02_07, e03_04` | `e01_06, e02_07, e03_04` | yes |
| forest10 | 4 | `e01_06, e02_07, e02_08, e03_04` | `e01_06, e02_07, e03_04` | no |
| forest10 | 5 | `e01_06, e02_07, e02_08, e03_04, e06_08` | `e01_06, e02_07, e03_04` | no |
| census13 | 0 | ∅ | ∅ | yes |
| census13 | 2 | `e02_03, e04_06` | `e02_03, e04_06` | yes |
| census13 | 3 | `e01_05, e02_03, e04_06` | `e01_05, e02_03, e04_06` | yes |
| census13 | 4 | `e01_05, e02_03, e04_06, e06_08` | `e00_11, e01_05, e02_03, e04_06` | no |
| census13 | 5 | `e01_05, e02_03, e04_06, e04_08, e06_08` | `e00_11, e01_05, e02_03, e04_06, e07_12` | no |
| dmv11 | 0 | ∅ | ∅ | yes |
| dmv11 | 2 | `e00_05, e01_04` | `e00_05, e01_04` | yes |
| dmv11 | 3 | `e00_05, e01_04, e04_07` | `e00_05, e01_04, e02_03` | no |
| dmv11 | 4 | `e00_05, e01_04, e01_07, e04_07` | `e00_05, e01_04, e02_03, e06_07` | no |
| dmv11 | 5 | `e00_05, e01_04, e01_07, e02_03, e04_07` | `e00_05, e01_04, e02_03, e06_07, e08_10` | no |
| power7 | 0 | ∅ | ∅ | yes |
| power7 | 2 | `e00_01, e03_06` | `e00_01, e03_06` | yes |
| power7 | 3 | `e00_01, e02_04, e03_06` | `e00_01, e02_04, e03_06` | yes |
| power7 | 4 | `e00_01, e00_03, e02_04, e03_06` | `e00_01, e02_04, e03_06` | no |
| power7 | 5 | `e00_01, e00_03, e01_02, e02_04, e03_06` | `e00_01, e02_04, e03_06` | no |

**Case accounting:** 40/40 COMPLETE; 0/40 INCOMPLETE. The sweep is labeled COMPLETE only when all 40 cases complete.

## Collection evidence

| Dataset | Workers | Early disk stop (bytes) | Hard disk cap (bytes) | Collection status | Train queries | Candidate pairs | Structured calls completed / required | Collection wall seconds | Peak allocated disk bytes |
|---|---:|---:|---:|---|---:|---:|---:|---:|---:|
| forest10 | 12 | 3221225472 | 4294967296 | COMPLETE | 100000 | 45 | 1741931 / 1741931 | 1941.784 | 2840223744 |
| census13 | 12 | 3221225472 | 4294967296 | COMPLETE | 100000 | 78 | 2901893 / 2901893 | 3282.381 | 2880544768 |
| dmv11 | 6 | 20401094656 | 21474836480 | COMPLETE | 100000 | 55 | 2094044 / 2094044 | 2851.137 | 14428110848 |
| power7 | 6 | 20401094656 | 21474836480 | COMPLETE | 100000 | 21 | 902535 / 902535 | 1056.812 | 3093200896 |

The sizing projection was based on a previous valid-only collection and was not treated as a runtime guarantee. Protocol v2 runs retain the 7.5-hour/3-GiB early stop and 8-hour/4-GiB hard limit; protocol v3 runs use 7.5 hours/9.5 GiB and 8 hours/10 GiB; protocol v4 runs use six workers, 7.5 hours/19 GiB and 8 hours/20 GiB. The preliminary DMV11 12-worker disk estimate of 22-24 GiB and six-worker estimate of 12-14 GiB are low-confidence extrapolations from stopped setup attempts, not completed measurements. Historical DMV11 measurement sizing was 8,624 seconds before setup and is not a six-worker throughput guarantee. Each collection manifest pins its protocol hash and effective limits. Incomplete PG attempts remain separate in the runtime store.

Exact per-case fractions, greedy traces, addition orders, selected IDs, budgets, resource limits, work counters, per-case source-run provenance, and input hashes are in [`frozen-train-resources-issue96-v1.json`](frozen-train-resources-issue96-v1.json). Query-level structured observations and run-local sample files remain outside Git under the Issue #99 runtime path.
