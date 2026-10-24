# Issue #87: full-valid add-only greedy comparison (v4)

**Experimentally observed, valid-only, greedy heuristic results. No global-optimum claim.**

All 20 solver cases and all 10 exact cross-evaluations completed in the frozen order: Forest10 then Census13; budgets 0, 2, 3, 4, 5; Nominal before PESS at each budget. Each dataset used its complete 10,000-task valid workload and all 45/78 candidates. Both datasets have different Nominal/PESS selections at B=4 and B=5. B=0,2,3 selections coincide.

## Source, authorization and execution

- Run ID: `issue87-valid-only-20261024-v4`; terminal status: `ALL_CASES_AND_CONTRASTS_COMPLETE`; process exit code: 0.
- Executed clean development-branch commit: `386658d7b3895a57bd138b24611672d329edaeda` (`fix/issue87-cross-scope-evidence-path-20261024`).
- Advisor: `5d61f75fede37d34027b437c646000a3d78d00c6`; protocol SHA-256: `ef095a12dd1a1ac676acd822e24d93e369b61cbd56297ced87b6771111f07623`.
- Environment: Python 3.12.3, NumPy 2.3.4, SciPy 1.18.1, NetworkX 3.7; Intel(R) Core(TM) i7-14650HX.
- Scientific question: do the frozen Nominal/PESS objectives produce different resource selections above B=3? The existing adapter, frozen models and merged Advisor backend were reused; implementation changes were limited to cross-worker argument/path handling.
- On 2026-10-24 the researcher authorized development-branch execution before main integration and continuing engineering repair/new attempts until completion. Each failed sequence remained stopped and was preserved under its own run ID. This supersedes the previous merge-before-execution workflow and per-attempt approval requirement for this task; scientific inputs, caps and stopping behavior within each sequence were unchanged. The execution gate remained enabled and checked.
- Forest10 uses `forest10-positive-preclamp-v1`; Census13 uses `census13-clamped-log-v2`. These are separate frozen model instances.
- Limits: 600 s Advisor, 900 s outer per case, 12 GiB memory, one solver process and one numerical CPU thread. Frozen candidate-evaluation and PESS matching-subset limits were unchanged.

Execution: 2026-10-24T14:28:50.046178+08:00 to 2026-10-24T14:36:48.758535+08:00; elapsed 478.712 s.

```bash
source ~/.bashrc
: "${ESS_DATA_ROOT:?}"
: "${ESS_RUNTIME_PARENT:?}"
: "${ESS_WORKTREE_PARENT:?}"
PYTHONPATH=experiments/add-only-greedy-issue87 .venv/bin/python experiments/add-only-greedy-issue87/run_issue87.py run \
  --repo /home/wqts/projects/ess-research/.worktrees/ess-research-issue87-cross-fix \
  --run-id issue87-valid-only-20261024-v4
```

## Selections and actual proxy-budget use

All sets below are unordered. Costs are the frozen unit additive proxy, not measured physical maintenance. Used/left means actual budget used and unused. Shared counts refer to the intersection of Nominal and PESS sets.

| Dataset | B | Nominal set | PESS set | N used/left | P used/left | Same set | Shared |
|---|---:|---|---|---|---|---|---:|
| forest10 | 0 | {} | {} | 0/0 | 0/0 | True | 0 |
| forest10 | 2 | {e01_06, e02_07} | {e01_06, e02_07} | 2/0 | 2/0 | True | 2 |
| forest10 | 3 | {e01_06, e02_07, e03_04} | {e01_06, e02_07, e03_04} | 3/0 | 3/0 | True | 3 |
| forest10 | 4 | {e01_06, e02_07, e02_08, e03_04} | {e01_06, e02_07, e03_04} | 4/0 | 3/1 | False | 3 |
| forest10 | 5 | {e01_06, e02_07, e02_08, e03_04, e06_08} | {e01_06, e02_07, e03_04} | 5/0 | 3/2 | False | 3 |
| census13 | 0 | {} | {} | 0/0 | 0/0 | True | 0 |
| census13 | 2 | {e02_03, e04_06} | {e02_03, e04_06} | 2/0 | 2/0 | True | 2 |
| census13 | 3 | {e01_05, e02_03, e04_06} | {e01_05, e02_03, e04_06} | 3/0 | 3/0 | True | 3 |
| census13 | 4 | {e01_05, e02_03, e04_06, e06_08} | {e00_11, e01_05, e02_03, e04_06} | 4/0 | 4/0 | False | 3 |
| census13 | 5 | {e01_05, e02_03, e04_06, e04_08, e06_08} | {e00_11, e01_05, e02_03, e04_06, e07_12} | 5/0 | 5/0 | False | 3 |

Forest10 PESS terminates at three resources even when B=4 or B=5, because no remaining candidate has a strictly positive exact PESS improvement. Census13 PESS uses both additional budget units, choosing different fourth and fifth resources from Nominal.

## Resource identities

| Dataset | Resource ID | Endpoints |
|---|---|---|
| forest10 | e01_06 | Aspect, Hillshade_9am |
| forest10 | e02_07 | Slope, Hillshade_Noon |
| forest10 | e02_08 | Slope, Hillshade_3pm |
| forest10 | e03_04 | Horizontal_Distance_To_Hydrology, Vertical_Distance_To_Hydrology |
| forest10 | e06_08 | Hillshade_9am, Hillshade_3pm |
| census13 | e00_11 | age, hours_per_week |
| census13 | e01_05 | workclass, occupation |
| census13 | e02_03 | education, education_num |
| census13 | e04_06 | marital_status, relationship |
| census13 | e04_08 | marital_status, sex |
| census13 | e06_08 | relationship, sex |
| census13 | e07_12 | race, native_country |

## Additions and exact improvements

For each dataset/objective the completed B=0,2,3,4 traces were checked to be prefixes of the B=5 trace below. Thus this table records every distinct addition made in all budgets. Every improvement is strictly positive and equals the exact before-minus-after objective difference. Complete before/after values also remain in `case-results.jsonl`.

| Dataset | Objective | Round | Added resource | Exact improvement | Exact objective after addition |
|---|---|---:|---|---|---|
| forest10 | nominal | 1 | e02_07 | 839359151334019858487/1000000000000000000 | 11243733239965563205331/500000000000000000 |
| forest10 | nominal | 2 | e01_06 | 613321886104430774177/1000000000000000000 | 4374828918765339127297/200000000000000000 |
| forest10 | nominal | 3 | e03_04 | 180694736335679629259/500000000000000000 | 21512755121155336377967/1000000000000000000 |
| forest10 | nominal | 4 | e02_08 | 134378324741118275633/1000000000000000000 | 10689188398207109051167/500000000000000000 |
| forest10 | nominal | 5 | e06_08 | 44955678358050142359/500000000000000000 | 1330529089981132363601/62500000000000000 |
| forest10 | pess | 1 | e02_07 | 839359151334019858487/1000000000000000000 | 11243733239965563205331/500000000000000000 |
| forest10 | pess | 2 | e01_06 | 613321886104430774177/1000000000000000000 | 4374828918765339127297/200000000000000000 |
| forest10 | pess | 3 | e03_04 | 180694736335679629259/500000000000000000 | 21512755121155336377967/1000000000000000000 |
| census13 | nominal | 1 | e02_03 | 1260289068511204085589/1000000000000000000 | 6879067993917333915329/1000000000000000000 |
| census13 | nominal | 2 | e04_06 | 1013818022214515506953/1000000000000000000 | 733156246462852301047/125000000000000000 |
| census13 | nominal | 3 | e01_05 | 378589872191300971297/1000000000000000000 | 5486660099511517437079/1000000000000000000 |
| census13 | nominal | 4 | e06_08 | 164654703527366042617/1000000000000000000 | 2661002697992075697231/500000000000000000 |
| census13 | nominal | 5 | e04_08 | 10052313330810439527/100000000000000000 | 652685282834505874899/125000000000000000 |
| census13 | pess | 1 | e02_03 | 1260289068511204085589/1000000000000000000 | 6879067993917333915329/1000000000000000000 |
| census13 | pess | 2 | e04_06 | 1013818022214515506953/1000000000000000000 | 733156246462852301047/125000000000000000 |
| census13 | pess | 3 | e01_05 | 378589872191300971297/1000000000000000000 | 5486660099511517437079/1000000000000000000 |
| census13 | pess | 4 | e00_11 | 20486782603924050071/250000000000000000 | 1080942593819164247359/200000000000000000 |
| census13 | pess | 5 | e07_12 | 18300001974723270583/500000000000000000 | 5368112965146374695629/1000000000000000000 |

## Exact cross-objectives

Let N(M) be the frozen Nominal loss sum and P(M) the frozen task-wise PESS loss sum. M_N and M_P denote their respective greedy sets. The gap is P(M_N) - P(M_P), relative only to the PESS greedy incumbent. All entries are exact Fraction values over the 10,000 valid tasks.

| Dataset | B | N(M_N) | N(M_P) | P(M_N) | P(M_P) | P(M_N) − P(M_P) |
|---|---:|---|---|---|---|---|
| forest10 | 0 | 23326825631265146269149/1000000000000000000 | 23326825631265146269149/1000000000000000000 | 23326825631265146269149/1000000000000000000 | 23326825631265146269149/1000000000000000000 | 0 |
| forest10 | 2 | 4374828918765339127297/200000000000000000 | 4374828918765339127297/200000000000000000 | 4374828918765339127297/200000000000000000 | 4374828918765339127297/200000000000000000 | 0 |
| forest10 | 3 | 21512755121155336377967/1000000000000000000 | 21512755121155336377967/1000000000000000000 | 21512755121155336377967/1000000000000000000 | 21512755121155336377967/1000000000000000000 | 0 |
| forest10 | 4 | 10689188398207109051167/500000000000000000 | 21512755121155336377967/1000000000000000000 | 1354109352983758051097/62500000000000000 | 21512755121155336377967/1000000000000000000 | 30598905316958487917/200000000000000000 |
| forest10 | 5 | 1330529089981132363601/62500000000000000 | 21512755121155336377967/1000000000000000000 | 5478975028566803369823/250000000000000000 | 21512755121155336377967/1000000000000000000 | 16125799724475084053/40000000000000000 |
| census13 | 0 | 4069678531214269000459/500000000000000000 | 4069678531214269000459/500000000000000000 | 4069678531214269000459/500000000000000000 | 4069678531214269000459/500000000000000000 | 0 |
| census13 | 2 | 733156246462852301047/125000000000000000 | 733156246462852301047/125000000000000000 | 733156246462852301047/125000000000000000 | 733156246462852301047/125000000000000000 | 0 |
| census13 | 3 | 5486660099511517437079/1000000000000000000 | 5486660099511517437079/1000000000000000000 | 5486660099511517437079/1000000000000000000 | 5486660099511517437079/1000000000000000000 | 0 |
| census13 | 4 | 2661002697992075697231/500000000000000000 | 1080942593819164247359/200000000000000000 | 726172861228000098887/125000000000000000 | 1080942593819164247359/200000000000000000 | 404669920728179554301/1000000000000000000 |
| census13 | 5 | 652685282834505874899/125000000000000000 | 5368112965146374695629/1000000000000000000 | 2928651976860382342343/500000000000000000 | 5368112965146374695629/1000000000000000000 | 489190988574389989057/1000000000000000000 |

For readability, the B=4/5 PESS gaps rounded to six decimal places are:

| Dataset | B=4 | B=5 |
|---|---:|---:|
| forest10 | 152.994527 | 403.144993 |
| census13 | 404.669921 | 489.190989 |

## Resource overlap within selected sets

Endpoint-sharing resource pairs are distinct from the cross-set intersections above. Task counts use each task’s applicable selected resources; incidence counts sum the overlapping resource-pair counts over tasks.

| Dataset | B | Objective | Endpoint-sharing pairs | Tasks with applicable overlap | Pair/task incidences |
|---|---:|---|---:|---:|---:|
| forest10 | 4 | nominal | 1 | 2747 | 2747 |
| forest10 | 4 | pess | 0 | 0 | 0 |
| forest10 | 5 | nominal | 3 | 3841 | 8150 |
| forest10 | 5 | pess | 0 | 0 | 0 |
| census13 | 4 | nominal | 1 | 2682 | 2682 |
| census13 | 4 | pess | 0 | 0 | 0 |
| census13 | 5 | nominal | 3 | 2682 | 8046 |
| census13 | 5 | pess | 0 | 0 | 0 |

## Runtime and evaluation work

Case wall time and peak RSS are from `/usr/bin/time`; Advisor time is the backend-reported elapsed time. Candidate attempts include infeasible candidates, so they need not equal exact fixed-set evaluations.

| Dataset | B | Objective | Case s | Advisor s | Candidate attempts | Fixed-set evaluations | Matching subsets | Maximal matchings scored | Peak RSS MiB |
|---|---:|---|---:|---:|---:|---:|---:|---:|---:|
| forest10 | 0 | nominal | 1.84 | 0.084 | 45 | 1 | 0 | 0 | 148.27 |
| forest10 | 0 | pess | 1.18 | 0.108 | 45 | 1 | 10000 | 10000 | 148.10 |
| forest10 | 2 | nominal | 8.70 | 7.630 | 132 | 90 | 0 | 0 | 148.71 |
| forest10 | 2 | pess | 11.70 | 10.669 | 132 | 90 | 1490174 | 943658 | 149.03 |
| forest10 | 3 | nominal | 12.62 | 11.593 | 174 | 133 | 0 | 0 | 148.84 |
| forest10 | 3 | pess | 17.95 | 16.951 | 174 | 133 | 2761707 | 1451992 | 148.31 |
| forest10 | 4 | nominal | 16.38 | 15.329 | 215 | 175 | 0 | 0 | 148.27 |
| forest10 | 4 | pess | 26.17 | 25.130 | 174 | 175 | 4705672 | 1976610 | 148.62 |
| forest10 | 5 | nominal | 20.03 | 18.992 | 255 | 216 | 0 | 0 | 148.53 |
| forest10 | 5 | pess | 26.45 | 25.415 | 174 | 175 | 4705672 | 1976610 | 149.18 |
| census13 | 0 | nominal | 8.98 | 0.149 | 78 | 1 | 0 | 0 | 179.44 |
| census13 | 0 | pess | 1.55 | 0.147 | 78 | 1 | 10000 | 10000 | 178.95 |
| census13 | 2 | nominal | 18.84 | 17.364 | 231 | 156 | 0 | 0 | 179.29 |
| census13 | 2 | pess | 22.76 | 21.332 | 231 | 156 | 2565843 | 1618918 | 180.00 |
| census13 | 3 | nominal | 26.96 | 25.533 | 306 | 232 | 0 | 0 | 179.18 |
| census13 | 3 | pess | 34.45 | 33.029 | 306 | 232 | 4767827 | 2487418 | 179.44 |
| census13 | 4 | nominal | 36.30 | 34.926 | 380 | 307 | 0 | 0 | 179.33 |
| census13 | 4 | pess | 50.63 | 49.166 | 380 | 307 | 8180934 | 3388116 | 179.71 |
| census13 | 5 | nominal | 46.36 | 44.983 | 453 | 381 | 0 | 0 | 179.27 |
| census13 | 5 | pess | 70.50 | 69.129 | 453 | 381 | 13639686 | 4312196 | 180.09 |

| Dataset | B | Cross-evaluator s | Fixed-set evaluations | Matching subsets | Maximal matchings scored |
|---|---:|---:|---:|---:|---:|
| forest10 | 0 | 0.401 | 4 | 20000 | 20000 |
| forest10 | 2 | 0.414 | 4 | 38882 | 20000 |
| forest10 | 3 | 0.529 | 4 | 57796 | 20000 |
| forest10 | 4 | 0.560 | 4 | 74966 | 22747 |
| forest10 | 5 | 0.586 | 4 | 107126 | 25637 |
| census13 | 0 | 0.481 | 4 | 20000 | 20000 |
| census13 | 2 | 0.525 | 4 | 38344 | 20000 |
| census13 | 3 | 0.574 | 4 | 57254 | 20000 |
| census13 | 4 | 0.682 | 4 | 90201 | 22682 |
| census13 | 5 | 0.814 | 4 | 149802 | 25364 |

## Evidence and validation

- Raw runtime evidence: `/home/wqts/ess-runtime/ess-research/issue87/runs/issue87-valid-only-20261024-v4`. All request/response bytes, result records, scope samples, terminal state and resource logs are retained there; `evidence-sha256.json` records SHA-256 for all 234 raw files.
- `case-results.jsonl` and `contrasts.jsonl` here are byte-identical retained copies of the compact runtime records. Requests are retained only in the runtime directory, not duplicated in Git.
- Terminal summary SHA-256: `ce4eb42c9ee14c093c9492d41dd18a025f372c174d89b0bdfd612f0858879c33`.
- Case JSONL SHA-256: `599ea8833e11b0f1171294e5f2aa1e0584b3815479475fa8230f4fdb46188c03`.
- Contrast JSONL SHA-256: `27c437e58c050900cb7cd8a3c8607a69c7df4055cb7e4d78ca31925b07160290`.
- Post-run read-only audit: exactly 20 complete cases and 10 complete contrasts in frozen order; complete workload/candidate counts; all request/response hashes; exact budget usage, strictly positive trace improvements and objective telescoping; diagonal cross-objectives equal solver objectives; exact PESS gap identities; evaluation caps; all 30 process exits and active-scope checks passed. This audit read recorded values and did not re-solve tasks.
- All 30 active scope samples verify MemoryMax=12884901888, RuntimeMaxUSec=15min and matching process/cgroup memory.max. Exited transient scopes report inactive/unbounded properties; these terminal properties are not used as evidence of live enforcement. Peak RSS is measured by `/usr/bin/time`.
- Maximum case wall time: 70.50 s; maximum case peak RSS: 180.09 MiB. No timeout, cap violation, incomplete result or missing evidence was observed in v4.
- Two targeted offline regressions cover the cross-worker directory argument and the full 20-case orchestration’s budget-specific cross request, without solver or full-data execution. Both passed locally; Ruff checks passed. CI status is attached to PR #93.

## Preserved failed attempts

No v1/v2/v3 evidence was overwritten or promoted to a complete comparison. Each sequence stopped on its first failure.

| Run | Failure | Terminal summary SHA-256 |
|---|---|---|
| v1 | Forest10 Nominal B=0: post-exit scope properties could not establish enforced limits. | 632b7b9c9e723547a929dc213e519ad92b9a95e1620ee3155ca7b1a0ce1208c0 |
| v2 | Forest10 B=0 cross worker: missing case_dir argument. | ad99b4fb616e493c604421c3b3db2b9e0784bab144be28fa7f51a4714cc01405 |
| v3 | Forest10 B=2 cross worker: B=0 request incorrectly reused as the cross-evaluation request. | 465516087835207d19ed113a7296a9ea7ca82a1a359d53452e5e0939b3192da9 |

## Interpretation and limitations

These observations answer the frozen valid-only greedy comparison: Nominal and PESS can choose different resources at B=4 and B=5, and the Nominal greedy set has a larger exact PESS loss than the PESS greedy incumbent in all four target contrasts. This establishes neither global optimality nor a difference between true model optima. It also does not establish population generalization, PostgreSQL benefit, or containment of all real PostgreSQL schemes in the modeled matching family. Forest10 and Census13 use different frozen loss transforms; their raw objective sums should not be interpreted as a common cross-dataset performance scale.

No PostgreSQL experiment, held-out test access/evaluation, recalibration, candidate/model change, extra budget, or generalization experiment was performed.
