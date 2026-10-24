# Issue #95 — task-level attribution of the v4 greedy gaps

**Evidence label: experimentally observed, fixed-set model-internal analysis.** This explains the four already completed Issue #87 v4 contrasts. It does not rerun the greedy solver, choose resources, or describe PostgreSQL runtime behavior.

## Method and exact check

The analysis reused the exact serialized 10,000-task valid model requests, Nominal priority orders, selected sets, cross-evaluation rows and pinned `pess_ess.reference` implementation from v4. It evaluated each task once under the fixed Nominal priority matching and once over all inclusion-maximal matchings on the same Nominal-selected applicable edges. Task weights are frozen at one, so (r_i=P_i(M_N)-N_i(M_N)) sums directly to the objective difference. The reference implementation's equal-loss matching witness is lexicographically stable; positive-risk task ties are ordered by stable task ID.

For every contrast the analysis verified both task-loss totals against the stored exact cross-objectives and verified
\[
\sum_i r_i=P(M_N)-N(M_N).
\]
Every nominal and worst-loss witness was checked as an inclusion-maximal matching. Positive risk without an applicable endpoint conflict and nonzero risk on any nonconflicting task both fail the analysis.

| Dataset | B | Exact Σ r_i | Positive-risk tasks | Tasks with an applicable endpoint conflict | Conflict tasks with zero risk | Nonconflicting zero-risk tasks |
|---|---:|---|---:|---:|---:|---:|
| Forest10 | 4 | `143686425662955357609/500000000000000000` (287.372851) | 1,373 | 2,747 | 1,374 | 7,253 |
| Forest10 | 5 | `156858668642273915419/250000000000000000` (627.434675) | 2,288 | 3,841 | 1,553 | 6,159 |
| Census13 | 4 | `243688746919924698317/500000000000000000` (487.377494) | 1,038 | 2,682 | 1,644 | 7,318 |
| Census13 | 5 | `317910845522358842747/500000000000000000` (635.821691) | 1,088 | 2,682 | 1,594 | 7,318 |

An endpoint conflict is necessary for positive task risk in these four fixed selections, but it is not sufficient: the conflict counts exceed positive-risk counts in every row. The exact counts, `N(M_N)` and `P(M_N)` sums, and per-task reference work are in [`issue95-task-attribution.json`](issue95-task-attribution.json).

## Concentration and matching witnesses

Top-k tasks are ranked by exact risk descending, then task ID ascending. The table reports contribution sum and its share of Σ r_i; exact Fraction sums and proportions are in the JSON artifact.

| Dataset | B | Top 10 sum (share) | Top 100 sum (share) |
|---|---:|---:|---:|
| Forest10 | 4 | 15.956809 (5.5527%) | 90.768895 (31.5858%) |
| Forest10 | 5 | 22.899337 (3.6497%) | 140.462222 (22.3867%) |
| Census13 | 4 | 12.070206 (2.4766%) | 108.354828 (22.2322%) |
| Census13 | 5 | 18.726061 (2.9452%) | 141.999932 (22.3333%) |

Each row below names the three largest-risk witnesses. The JSON contains each witness's exact Nominal loss, exact worst PESS loss, exact risk, selected-edge endpoints, and conflicting pairs, so the matching can be checked directly.

| Dataset, B | Stable task ID | Nominal matching | Worst-loss maximal matching |
|---|---|---|---|
| Forest10, 4 | `arecel:forest10:valid:004037` | `{e02_07,e03_04}` | `{e02_08,e03_04}` |
|  | `arecel:forest10:valid:003057` | `{e01_06,e02_07,e03_04}` | `{e01_06,e02_08,e03_04}` |
|  | `arecel:forest10:valid:007766` | `{e01_06,e02_07,e03_04}` | `{e01_06,e02_08,e03_04}` |
| Forest10, 5 | `arecel:forest10:valid:007852` | `{e01_06,e03_04}` | `{e03_04,e06_08}` |
|  | `arecel:forest10:valid:008039` | `{e01_06,e02_08}` | `{e06_08}` |
|  | `arecel:forest10:valid:003650` | `{e01_06,e02_07,e03_04}` | `{e02_07,e03_04,e06_08}` |
| Census13, 4 | `arecel:census13:valid:004945` | `{e04_06}` | `{e06_08}` |
|  | `arecel:census13:valid:001814` | `{e01_05,e02_03,e04_06}` | `{e01_05,e02_03,e06_08}` |
|  | `arecel:census13:valid:008731` | `{e04_06}` | `{e06_08}` |
| Census13, 5 | `arecel:census13:valid:004945` | `{e04_06}` | `{e04_08}` |
|  | `arecel:census13:valid:000719` | `{e02_03,e04_06}` | `{e02_03,e04_08}` |
|  | `arecel:census13:valid:001446` | `{e02_03,e04_06}` | `{e02_03,e04_08}` |

The differing matchings trace to small endpoint-sharing groups in the fixed Nominal selections:

- Forest10 B=4: `e02_07` and `e02_08` share `Slope`. At B=5, conflicts also involve `e01_06`/`e06_08` on `Hillshade_9am` and `e02_08`/`e06_08` on `Hillshade_3pm`.
- Census13 B=4: `e04_06` and `e06_08` share `relationship`. At B=5, `e04_06`, `e04_08`, and `e06_08` form a triangle across `marital_status`, `relationship`, and `sex`.

The conflict gives the task alternative maximal matchings; the frozen exact coefficients determine whether that alternative has strictly higher loss. This explains the observed task-wise risk inside the prescribed matching family, not the behavior of a live database estimator.

## Provenance, work, and limits

- Source worktree commit: `0e7da4d2c7073e1a2dba531fda4e317adf414a10`; analysis script SHA-256: `080320de10b82e109bdccb27b5d65469fe9c5a020edc2483fd7be3f4c29b56d5`.
- Frozen Issue #87 solver source: `386658d7b3895a57bd138b24611672d329edaeda`; Advisor: `5d61f75fede37d34027b437c646000a3d78d00c6`; protocol SHA-256: `ef095a12dd1a1ac676acd822e24d93e369b61cbd56297ced87b6771111f07623`.
- v4 evidence manifest SHA-256: `6e1f9a07d52bf5dd2d5e250e80dad2146cacf8cadeeecf0f078a86b8017eb1e4`; analysis JSON SHA-256: `2be62f667251dfec5636efa790cbc7152cd5e451a203e81aacf994182d4bfc1f`.
- Environment: Python 3.12.3, NumPy 2.3.4, SciPy 1.18.1, NetworkX 3.7, `pess-ess==0.1.0` from the pinned Advisor commit. Reproduction command:

  ```bash
  source ~/.bashrc
  : "${ESS_RUNTIME_PARENT:?ESS_RUNTIME_PARENT must be set}"
  .venv/bin/python experiments/add-only-greedy-issue87/analyze_issue95.py \
    --run-dir "$ESS_RUNTIME_PARENT/ess-research/issue87/runs/issue87-valid-only-20261024-v4" \
    --output experiments/add-only-greedy-issue87/issue95-task-attribution.json
  ```

- Elapsed analysis time: 4.445 seconds; 40,000 fixed-set task pairs (10,000 per contrast), 248,349 matching subsets examined and 56,430 maximal matchings scored by the exact PESS reference. No greedy solve was launched.
- Forest10 and Census13 retain different frozen loss transforms. These are valid-only, model-internal task attributions for heuristic-selected sets; they are not PostgreSQL performance measurements, held-out results, population-generalization claims, or global-optimum comparisons.

No PostgreSQL, held-out/test data, calibration, model changes, candidate changes, or additional solver budgets were used.
