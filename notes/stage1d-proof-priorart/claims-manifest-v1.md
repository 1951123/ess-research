# Stage 1D claims manifest and source-search protocol (frozen)

**Issue:** [#41](https://github.com/1951123/ess-research/issues/41)  
**Worktree/branch:** `ess-research-issue41` / `research/issue41-proof-priorart`  
**Manifest version:** v1  
**Frozen before final classification:** 2026-10-20 (Asia/Shanghai)  
**Scope:** four mandatory candidate claims only; no PostgreSQL execution, solver benchmark, forest dataset, or production implementation.

This manifest records the audit questions and search protocol before writing
the final theorem/novelty classifications. It is not evidence that any claim
is true or original. The final report must preserve the distinction between
model-internal proof, source-derived conditional statements, experimentally
observed checks, and open or refuted claims.

## 1. Frozen model boundary

Use the structured PESS instance already recorded in the repository:

- The outer decision is one unordered global resource set (M), with labeled
  candidate edges and the existing additive maintenance proxy only where the
  theorem explicitly assumes it.
- For task (i), the prescribed admissible family is
  (Gamma_i^{\rm MM}(M)=\operatorname{MaximalMatchings}(H_i[M])).
  “Maximal” is not “maximum-cardinality”.
- A task loss is nonnegative. For the primary illustrative loss, use
  (L_i(P)=|\alpha_i+sum_{e\in P}b_{e,i}|) only under the positive
  pre-clamp multiplicative-estimator assumptions stated in the report.
- Task-wise maxima remain independent in the objective; no shared-policy
  global worst case is substituted. Generic maintenance is not silently made
  additive, and real possible schemes (mathcal R_i(M)) are not identified
  with prescribed (Gamma_i(M)) without assumptions.

## 2. Candidate claims and proof obligations

### C1 — single-star local ideal epigraph

**Origin:** Issue #29 comment
[6264019796](https://github.com/1951123/ess-research/issues/29#issuecomment-6264019796),
with the earlier star-forest chain in comment
[6263743093](https://github.com/1951123/ess-research/issues/29#issuecomment-6263743093).

**Frozen statement to audit:** For one connected star task with labeled
selected edges, the binary task loss is the empty-selection value or the
largest selected singleton loss. The highest-selected-index (lambda)-chain
is claimed to describe the local convex hull of the binary epigraph, including
ties, empty selection, zero/negative signed corrections, and fractional (x).

**Required checks:** prove or refute the projected epigraph symbolically;
cover (m=0), (m=1), tied values, all signs, fractional (x), and the
upward epigraph direction. Separately construct/check a task-sharing or
budget-coupling example showing why local ideality does not imply a globally
ideal multi-task formulation.

**Failure conditions to test:** sorting by signed (b) rather than loss
values; an incorrect empty state; parallel labels; incorrect lambda bounds;
or a claim that local ideality yields global integrality or easy optimization.

### C2 — incidence structure versus task-graph structure

**Origin:** Issue #29 comment
[6264188244](https://github.com/1951123/ess-research/issues/29#issuecomment-6264188244),
building on comments [6263743093](https://github.com/1951123/ess-research/issues/29#issuecomment-6263743093)
and [6264019796](https://github.com/1951123/ess-research/issues/29#issuecomment-6264019796).

**Frozen statement to audit:** A single-star-per-task pseudo-polynomial DP may
apply when the task-resource incidence graph is a forest and costs/budget are
integer; conditioning on a resource feedback set gives a corresponding
parameterized algorithm. This must be separated from arbitrary disconnected
task incidence forests and from a connected one-task path.

**Required checks:** state the exact factor assumptions, charge resource
costs once, handle zero-cost resources, empty selections, ties, and budget
representation; distinguish pseudo-polynomial dependence on numeric (B) from
bit-polynomial/FPT claims. Verify the disjoint-edge SUBSET-SUM counterexample
and the resource-feedback parameterization. Audit the over-strong statement
that any acyclic incidence makes PESS easy.

**Failure conditions to test:** replacing a single connected star by a star
forest without changing the factor; confusing the task attribute graph with
the task-resource incidence graph; or claiming bounded feedback resources/FPT
in (k) while hiding binary-budget dependence.

### C3 — connected path hardness and finite-boundary profile DP

**Origin:** Issue #29 comments
[6264341665](https://github.com/1951123/ess-research/issues/29#issuecomment-6264341665),
[6264364864](https://github.com/1951123/ess-research/issues/29#issuecomment-6264364864),
and [6265119316](https://github.com/1951123/ess-research/issues/29#issuecomment-6265119316).

**Frozen statement to audit:** The alternating item/connector path reduction
with positive integer corrections is a weak SUBSET-SUM hardness boundary for
outer resource selection, despite a polynomial-time fixed-selected-path inner
oracle. The proposed profile DP must retain a coupled max/min boundary profile
for the common outer prefix, and its rounded guarantee is additive in a
coefficient scale, not a universal (1+\varepsilon) ratio.

**Required checks:** verify endpoints, connector effects, modulo argument,
NP-membership restriction, all budget assumptions, empty/full path cases,
maximality transition invariants, sentinel handling, n-dependent bit
complexity, multi-task sharing, and zero/near-zero OPT. Distinguish exact
pseudo-polynomial profile enumeration from rounded additive approximation.

**Failure conditions to test:** connector matching can produce an invalid
reduction witness; independently optimizing extrema loses the shared outer
prefix; a profile state omits a boundary bit; or an additive εS statement is
reported as a multiplicative FPTAS.

### C4 — matching-aware perturbation transfer

**Origin:** Issue #29 comment [6265119316](https://github.com/1951123/ess-research/issues/29#issuecomment-6265119316)
and direction review [6265230463](https://github.com/1951123/ess-research/issues/29#issuecomment-6265230463).

**Frozen statement to audit:** With graph labels, admissibility families,
costs, budget, task weights, and α fixed, coefficient perturbations transfer
task-wise worst-case objectives using an ordinary maximum-weight matching of
absolute coefficient errors, even though admissible inner schemes are
maximal matchings. Retain zero-rounded edges. Derive exact lower/upper
transfers and enumerate assumptions; do not call this a new theorem without
source comparison.

**Required checks:** compare the same Γ(M) at each M; include parallel labels,
empty matching, nonnegative weights, and the α perturbation term; prove the
max-of-functions Lipschitz step; distinguish original-model exact evaluation
from floating-point solver output. Check whether changed membership,
admissibility, costs or PG rounding invalidates the result.

**Failure conditions to test:** using maximum-cardinality instead of
maximum-weight matching; dropping zero-error/zero-rounded edges; changing
the admissible family; or claiming a real-PG calibration guarantee.

## 3. Frozen source-search buckets and query protocol

Search execution begins only after this manifest. Search primary sources first
(paper/proceedings/author preprint/DOI metadata and proofs); snippets and
generated summaries are leads only. For every source used, record title,
authors, venue/year, DOI or stable permalink, access date, exact comparison,
and whether equivalence is proved or only analogous. Mark inaccessible full
text and uncertain priority explicitly.

Buckets and seed queries (expand only by documented synonyms):

1. **Maximal matching / edge domination:** `minimum weight maximal matching`,
   `minimum maximal matching`, `edge domination`, `maximal matching polytope`,
   `weighted edge domination`, plus `series-parallel tree maximal matching`.
2. **Tree/incidence DP and feedback sets:** `weighted CSP tree decomposition`
   `factor graph budget dynamic programming`, `budgeted coverage forest`,
   `feedback vertex set resource`, `bounded treewidth extended formulation`.
3. **Order-statistics epigraphs and disjunction:** `convex hull maximum
   selected value`, `epigraph max selected item`, `disjunctive programming
   ordered formulation`, `embedding formulation order statistics`.
4. **Subset Sum / profiles / approximation:** `subset sum scaling FPTAS`,
   `approximate Pareto curve`, `multiobjective dynamic programming label
   dominance`, `weighted automata resource constrained shortest path`.
5. **Decision-dependent robust optimization:** `decision dependent
   uncertainty robust optimization`, `robust optimization oracle
   decomposition`, `maximal matching uncertainty selection`, `shared
   decision-dependent adversary`.

For each bucket, search DOI/publisher/author repositories and inspect the
actual source or a reachable author manuscript. At least two independently
located primary sources per central bucket are targeted where available; if
not accessible, report the gap. Do not infer priority from the existence of a
similar title.

## 4. Classification vocabulary frozen in advance

Each candidate receives two separate labels:

- Mathematical status: **PROVED UNDER STATED ASSUMPTIONS**,
  **COUNTEREXAMPLE/REFUTED**, or **PROOF GAP / OPEN**.
- Novelty confidence: **CLEARLY CLASSICAL/SPECIAL CASE**, **PLAUSIBLY
  DISTINCT BUT NOT VERIFIED**, **SOURCE-BACKED DISTINCTNESS NEEDS FORMAL
  PRIOR-ART REVIEW**, or **UNKNOWN/SEARCH BLOCKED**.

No label is a publication claim. A GO recommendation requires at least one
fully stated defensible claim plus a documented unresolved prior-art boundary;
otherwise recommend NO-GO or INCONCLUSIVE exactly as the evidence supports.

## 5. Explicit exclusions

No PostgreSQL instance, forest dataset, solver benchmark, paper edit,
production algorithm integration, changes to `docs/STATUS.md` or
`docs/DECISIONS.md`, changes to other Stage 1 directories, or changes in
`ess-advisor`/`ess-postgresql` are authorized by this manifest.
