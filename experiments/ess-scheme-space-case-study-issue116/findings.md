# Issue #116 — Census13 Train scheme-space case study

**State:** complete offline analysis; proposed documentation and code remain on the Issue #116 Draft PR branch.
**Evidence class:** experimentally collected Train inputs plus exact/model-internal reconstruction.
**No PostgreSQL was started and no ANALYZE or EXPLAIN was executed. No Valid/Test split data was accessed.**

## Question and minimum sufficient analysis

The question is whether one actual frozen Census13 Train task makes the prescribed maximal-matching scheme family and its task-wise Nominal/PESS losses concrete, and how that local mechanism sits within the frozen Train objective. The minimum analysis reuses Issue #99's frozen resource sets and Train observations, the Issue #99 model transform, and the pinned Issue #103 exact reference; it enumerates only task-local admissible matchings and checks whole-Train aggregates.

## Scope and frozen inputs

This is a Census13 **Train-only** model case study over 100,000 frozen tasks. It does not select resources, refit estimates, inspect the Valid/Test split, or make a PostgreSQL behavior claim. The exact selection sets are unchanged:

| Label | Frozen set |
|---|---|
| M3_shared | {e01_05, e02_03, e04_06} |
| M4_nominal | {e01_05, e02_03, e04_06, e06_08} |
| M4_pess | {e00_11, e01_05, e02_03, e04_06} |
| M5_nominal | {e01_05, e02_03, e04_06, e04_08, e06_08} |
| M5_pess | {e00_11, e01_05, e02_03, e04_06, e07_12} |

The model is the frozen **census13-clamped-log-v2** transform: apply max(1,x) to the raw estimates and truth before log-error coefficient construction, then preserve the frozen decimal quantization and exact Fraction evaluation. Each official Train task has weight 1. For task i and fixed set M, let Γᵢ(M) be every labeled, inclusion-wise maximal matching of task-applicable selected edges; it is not a maximum-cardinality matching family. Let γᵢᴺ(M) be the frozen Nominal priority matching. The report uses

- Nᵢ(M) = Lᵢ(γᵢᴺ(M)),
- Pᵢ(M) = max over γ in Γᵢ(M) of Lᵢ(γ),
- rᵢ(M) = Pᵢ(M) − Nᵢ(M).

All whole-Train aggregates below are sums across the 100,000 equally weighted tasks. The exact fractions in summary.json are authoritative; displayed decimals are rounded for readability.

## Provenance and cross-checks

- Collection run: **20261025T055959Z-issue99-census13-591c9d**; 100,000 Train tasks and 2,901,893 recorded observations.
- Frozen Issue #99 selection JSON SHA-256: **2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca**.
- Issue #99 protocol-v4 SHA-256: **2f40b265bacc96d965b59bcdccc25c9bb73e3a4d99481a82107db0542343a9e6**.
- Collection manifest SHA-256: **844fcb7e3e171c97d0aab6593e2e10d15a154ea9e0a2d8f2d242d33ba14ea497**; fixed sample SHA-256: **0ff61bcce532a8af07f9319365c28d6fb07e373fc4b8049bae7c72c349baba26**.
- Train truth archive SHA-256: **b4f725def8ab5390f359dff9c2f0528a75fc7c59933ac108ebef5f82eb0439c4**; canonical truth-values SHA-256: **ae314b80cee9ad03157c2b43f1e4d867024ab5bbf32fe12861d5ef5b2d6ede9d**.
- Reconstructed 2,801,893 frozen model coefficients; exact coefficient digest **d9c285b0189883327e00655670e467632a9e2f8ac7f511e28be664c5d589561e** matched Issue #99.
- The pinned Advisor reference is commit **5d61f75fede37d34027b437c646000a3d78d00c6**; its model and reference source hashes are recorded in summary.json. All five displayed task/set evaluations matched that exact reference.
- Read-only Issue #103 cross-check used open Draft PR #104, summary run **20261025T115957Z-issue103-offline-exact** (summary SHA-256 **83b7a4d0b870d3bfd611314d71e34c06f3b41cd009c57ec96008ac173f2f3f4d**). All five fixed-set Nominal and PESS aggregate fractions match Issue #103 exactly. Issue #103's per-task reference checks were recorded there; this analysis independently rechecked the five displayed witness evaluations. This agreement is a reproducibility cross-check against existing pinned artifacts, not an independent replication of the local raw Train data.
- Whole AreCEL source archive SHA-256: **5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79**.
- The source records hashes for the Train workload and label pickle containers, but this analysis did not open or deserialize those containers. It used the frozen Train truth, candidate/support maps, and model artifacts only.

## Primary task: complete task-local scheme family

The predeclared search selected the lowest stable Train task ID meeting all criteria: **arecel:census13:train:000000**. Among all 100,000 tasks, 26,998 have more than one Γ scheme under M5_nominal; 10,764 have positive M5_nominal risk; 10,764 meet both conditions, and 62,266 have a B5 Nominal/PESS scheme-family or loss interpretation change. All 10,764 meeting the first two also meet the set-change condition and the compact-display cap |Γ| ≤ 8. The lowest conflict-bearing zero-risk task is **arecel:census13:train:000010**; it is not substituted for the predeclared primary witness.

For this primary task, the relevant edge endpoints are:

| Edge | Attribute endpoints |
|---|---|
| e04_06 | marital_status — relationship |
| e04_08 | marital_status — sex |
| e06_08 | relationship — sex |

Under M3_shared, only e04_06 is task-applicable, so Γ = {{e04_06}}. Both Nominal and PESS loss are exactly 0.077897984350382657 and r = 0.

Under M4_nominal, the task-applicable conflict graph has the single pair (e04_06, e06_08). Its complete labeled maximal family is Γ = {{e04_06}, {e06_08}}. The Nominal priority matching is {e04_06}, with loss 0.077897984350382657. The unique PESS maximizer is {e06_08}, with loss 0.686090992456160296. Thus r = 0.608193008105777639.

Under M5_nominal, the applicable edges form a triangle: each pair conflicts. The entire maximal family is Γ = {{e04_06}, {e04_08}, {e06_08}}; all three are singleton maximal matchings. Their exact losses, also stored as rational strings in the summary, are:

| Matching | Task loss | Role |
|---|---:|---|
| {e04_06} | 0.077897984350382657 | Nominal priority choice |
| {e04_08} | 0.651726007346304762 | Neither Nominal nor PESS maximum |
| {e06_08} | 0.686090992456160296 | Unique PESS maximizer |

The M5_nominal risk remains 0.608193008105777639. Under M4_pess and M5_pess, only e04_06 is applicable to this task; each has Γ = {{e04_06}}, so Nominal and PESS losses coincide and risk is zero. This makes clear that the B5 policy comparison is a substitution between two frozen selected sets: their shared IDs are e01_05, e02_03, e04_06; Nominal-only IDs are e04_08, e06_08; PESS-only IDs are e00_11, e07_12. The differing resources are not all task-applicable.

### Scheme-family transition and non-nestedness

For this selected task, Census13 Nominal B3 → B4 adds e06_08. The B3 family is {{e04_06}}; the B4 family is {{e04_06}, {e06_08}}. No old scheme disappears in this particular transition; it only gains a newly admissible maximal matching.

This task therefore does not itself demonstrate that Γ must shrink under resource addition. The general non-nestedness fact has a separate model-internal example: start with two disjoint applicable edges AB and CD. Then {AB, CD} is maximal. Add a third disjoint edge EF; afterward {AB, CD} is no longer maximal because EF can be added, and the new family contains {AB, CD, EF}. Thus an old maximal matching can leave Γ after adding a resource. This is a graph-level illustration, not another Train observation.

## Whole-Train objective context

The next table reports exact objective sums rounded to three decimals, plus task counts. “Ambiguous Γ” counts tasks with more than one admissible scheme. Risk-positive counts are task-wise rᵢ > 0; all positive-risk tasks were conflict-bearing, and every set satisfies the exact identity ΣᵢNᵢ + Σᵢrᵢ = ΣᵢPᵢ.

| Set | Ambiguous Γ tasks | Risk-positive tasks | Conflict-bearing, zero-risk tasks | ΣN | ΣP | Σr |
|---|---:|---:|---:|---:|---:|---:|
| M3_shared | 0 | 0 | 0 | 52,865.905 | 52,865.905 | 0 |
| M4_nominal | 26,998 | 10,262 | 16,736 | 51,409.134 | 56,485.624 | 5,076.491 |
| M4_pess | 0 | 0 | 0 | 52,163.364 | 52,163.364 | 0 |
| M5_nominal | 26,998 | 10,764 | 16,234 | 50,347.356 | 56,821.283 | 6,473.926 |
| M5_pess | 0 | 0 | 0 | 51,718.705 | 51,718.705 | 0 |

These are model objective totals over the frozen Train task collection, not PostgreSQL measurements, held-out performance, or claims that PESS always improves an external metric. Nonzero risk is concentrated in the Nominal resource sets here; the PESS fixed sets happen to have no conflicting applicable edges across this Train collection.

## Frozen greedy selection context

The six Issue #99 Census13 objective traces were replayed against the same frozen selected sets; every final objective fraction matches exactly. Both objectives share the accepted additions e02_03, e04_06, e01_05 through B3, with recorded objective reductions 12,637.905162, 10,437.211609, and 3,542.681147 respectively. For Nominal, the frozen order then adds e06_08 at B4 (reduction 1,456.771552) and e04_08 at B5 (1,061.777090). For PESS, it instead adds e00_11 at B4 (702.540774) and e07_12 at B5 (444.659001). Each trace uses its full budget (3/3, 4/4, or 5/5), records no_feasible_candidate at termination, and makes no outer global-optimum claim. The witness explains one task-level mechanism; it does not by itself explain the dataset-wide greedy choice.

## Suggested paper insert (not applied to paper/main.tex)

> In the frozen Census13 Train clamped-log model, task arecel:census13:train:000000 has Γ={{e04_06}} at B3; adding e06_08 for Nominal B4 expands Γ to {{e04_06},{e06_08}}, and adding e04_08 for B5 expands it to {{e04_06},{e04_08},{e06_08}}. No earlier matching disappears in this witness. Nominal selects e04_06 (absolute-log model loss ≈0.077898), while the unique task-wise PESS maximum is e06_08 (≈0.686091; gap ≈0.608193).
>
> These task-specific losses and aggregate sums are absolute-log losses under the frozen Train model, not physical PostgreSQL Q-error or observed OID-induced estimates. The illustrated task is a deterministic mechanism witness; the resource sets came from whole-Train add-only greedy, and this task does not by itself explain those global selections or establish global optimality. Across M5 Nominal, 26,998 Train tasks have multiple admissible schemes, but only 10,764 have positive Nominal-to-PESS risk while 16,234 have zero risk: a conflict is necessary but not sufficient for positive risk in this frozen model. The B5 Nominal/PESS comparison is a substitution between distinct frozen resource sets, not a single-resource addition.

Use only alongside the exact-definition and evidence-scope caveats above. The quoted text is a suggested draft; no manuscript file was changed.

## Reproduction and checks

Analysis source commit: **41429b39e375e2095d1b3ad4553e13ed94a02bd2**; analyzer SHA-256: **1262e13c3516a2c23fe7b0bbffe0cc6cf3be677d7452204d909bd49f143e3a0e**. Output JSON SHA-256: **e6b9076abd063145020a6a42997f636dbced3a111ed055f6a9f586c51e022e47**. The full offline analysis ran with Python 3.12.3 in 87.00 seconds. It read Issue #99 frozen runtime evidence and the pinned Issue #103/Advisor references only.

From this Worktree, with the repository environment initialized, the invocation was:

    python -B experiments/ess-scheme-space-case-study-issue116/analyze_issue116.py \
      --issue103-source "$ESS_WORKTREE_PARENT/ess-research-issue103" \
      --advisor-source /home/wqts/projects/ess-advisor \
      --output-json experiments/ess-scheme-space-case-study-issue116/summary.json

Four pure synthetic unit tests passed. Python byte-compilation and git diff --check passed. No repository-wide suite was run.