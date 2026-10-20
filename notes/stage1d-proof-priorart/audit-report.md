# Stage 1D independent proof and prior-art audit

**Issue:** [#41](https://github.com/1951123/ess-research/issues/41)  
**Branch:** `research/issue41-proof-priorart`  
**Audit cutoff:** 2026-10-20 (Asia/Shanghai)  
**Scope:** the four mandatory candidate claims from Issue #41. No PostgreSQL
instance, real forest input, solver benchmark, production implementation,
paper edit, or change to another Stage 1 workstream was performed.

## Executive result

The four claims separate into useful model-internal facts and non-results:

| Candidate | Mathematical status | Novelty confidence | Audit decision |
|---|---|---|---|
| C1: single-star local ideal epigraph | **PROVED UNDER STATED ASSUMPTIONS** | **CLEARLY CLASSICAL/SPECIAL CASE** for the disjunctive/order-statistic formulation; no PESS-specific publication claim established | Local result is correct. It does not produce a globally ideal or easy multi-task model. |
| C2: incidence structure and star/path boundaries | **PROVED UNDER STATED ASSUMPTIONS** for the single-star incidence-forest DP and resource-feedback conditioning; the unrestricted “acyclic incidence makes PESS easy” reading is **COUNTEREXAMPLE/REFUTED** | **CLEARLY CLASSICAL/SPECIAL CASE** | The task-resource incidence forest, task attribute graph, and numeric budget/range are different parameters. |
| C3: connected-path hardness and profile DP | **PROVED UNDER STATED ASSUMPTIONS** for the weak SUBSET-SUM reduction, fixed-path profile DP, and scale-additive transfer; multiplicative-FPTAS interpretation is **COUNTEREXAMPLE/REFUTED** by zero-optimum instances | **CLEARLY CLASSICAL/SPECIAL CASE** for the DP/scaling ingredients; PESS-specific combination not source-backed as new | Valid research boundary, not a novelty theorem. |
| C4: matching-aware perturbation transfer | **PROVED UNDER STATED ASSUMPTIONS** | **CLEARLY CLASSICAL/SPECIAL CASE** | A useful correctness certificate; it is a direct Lipschitz/error-envelope argument, not an established new theorem. |

The audit therefore recommends **NO-GO for a separate formal-theory Issue based
on these four claims alone**. The conclusion is not that no future PESS result
can be original; it is that this bounded inventory contains no claim with a
documented unresolved prior-art distinction strong enough for a defensible GO.
The best follow-up, if separately authorized, would be a narrowly specified
PESS-specific outer coupling or topology-adaptive algorithm study with a
predeclared comparison—not a rebranding of the local ingredients as novel.

## Evidence and provenance rules used

- **Proven (model-internal):** the displayed assumptions and a checkable proof
  establish the result for the structured mathematical instance.
- **Source-derived (conditional):** a statement follows from a cited source
  only within that source's graph/model/version assumptions.
- **Experimentally observed:** the exact stdlib diagnostic in
  [`experiments/theory-stage1d/check_stage1d.py`](../../experiments/theory-stage1d/check_stage1d.py)
  was executed in the Issue #41 `.venv` with `Python 3.12.3`; it passed. This
  is an arithmetic sanity check, not a proof, benchmark, or solver certificate.
- The repository comments and PRs are originating research records, not
  published results. In particular, PR #12 and PR #13 were inspected as
  repository provenance and their own limitations were retained.

## Gate A: frozen claim inventory and originating records

The immutable pre-classification protocol is
[`claims-manifest-v1.md`](claims-manifest-v1.md), committed before the final
classifications. The candidate origins are:

1. C1: Issue #29 comments [6264019796](https://github.com/1951123/ess-research/issues/29#issuecomment-6264019796)
   and [6263743093](https://github.com/1951123/ess-research/issues/29#issuecomment-6263743093).
2. C2: Issue #29 comment [6264188244](https://github.com/1951123/ess-research/issues/29#issuecomment-6264188244),
   with the star-forest discussion in [6263743093](https://github.com/1951123/ess-research/issues/29#issuecomment-6263743093)
   and the local/global gap in [6264019796](https://github.com/1951123/ess-research/issues/29#issuecomment-6264019796).
3. C3: Issue #29 comments [6264341665](https://github.com/1951123/ess-research/issues/29#issuecomment-6264341665),
   [6264364864](https://github.com/1951123/ess-research/issues/29#issuecomment-6264364864),
   and [6265119316](https://github.com/1951123/ess-research/issues/29#issuecomment-6265119316).
4. C4: Issue #29 comments [6265119316](https://github.com/1951123/ess-research/issues/29#issuecomment-6265119316)
   and [6265230463](https://github.com/1951123/ess-research/issues/29#issuecomment-6265230463).

The prior repository theory artifacts were also checked: the constant-factor
two-edge-star reduction in [PR #12](https://github.com/1951123/ess-research/pull/12)
and the fixed-selected path/cycle/star inner oracle in
[PR #13](https://github.com/1951123/ess-research/pull/13). PR #12 separates
outer shared-selection hardness from trivial inner evaluation. PR #13 itself
already records Richey–Parker as broader prior art for fixed-graph weighted
maximal matching. Neither PR establishes publication novelty for the four
claims here.

## Claim-by-claim audit

### C1 — local single-star exact ideal epigraph

#### Exact statement and proof

Let a task be one connected star with labeled eligible edges
(e_1,ldots,e_m). All selected edges conflict at the common center; parallel
labels remain distinct resources but still conflict. Under the maximal-matching
admissibility rule, the empty selected graph has only the empty matching and a
nonempty selected star has exactly the selected singleton matchings. Define

\[
v_0=|\alpha|,\qquad v_e=|\alpha+b_e|.
\]

Therefore, for binary selection (x),

\[
W(x)=
\begin{cases}
v_0,&x=0,\\
\max\{v_e:x_e=1\},&\text{otherwise}.
\end{cases}
\]

Sort the labeled edges by nondecreasing (v_e), breaking ties by a fixed
label order, and call the resulting values (v_1\le\cdots\le v_m). The
following continuous formulation is the local epigraph candidate:

\[
\begin{aligned}
&\sum_{j=0}^m\lambda_j=1,\qquad \lambda_j\ge0,\\
&\lambda_j\le x_j\le\sum_{k=j}^m\lambda_k\quad(1\le j\le m),\\
&z\ge v_0\lambda_0+\sum_{j=1}^m v_j\lambda_j.
\end{aligned}
\tag{C1}
\]

For a binary (x), let (J) be the largest selected index, or (J=0) for
the empty set. The inequalities force (lambda_J=1) and all other
(lambda)'s to zero, so (C1) gives exactly (W(x)), including (m=0),
ties, zero values, negative (b_e), and an empty selection.

For fractional (x), interpret (lambda_j) as the probability that (J=j).
Necessity is immediate: an edge (j) can be selected only when (J\ge j),
and it must be selected when (J=j). Conversely, for every (j), the
excess (x_j-lambda_j) lies between zero and
(sum_{k>j}lambda_k). Distribute that excess among the events (J=k>j),
selecting edge (j) conditionally with probability at most one; when (J=k),
edge (k) is selected and no edge larger than (k) is selected. This constructs
a distribution on binary subsets with marginal vector (x) and expected loss
(sum_jv_jlambda_j). Since the epigraph is upward closed in (z), the
projection of (C1) is exactly the convex hull of the binary epigraph.

Thus C1 is **Proven (model-internal)**. The proof is local and does not require
all (v_e) to be positive or all (b_e) to have one sign.

#### Global coupling counterexample

Take four global resources (e_1,ldots,e_4), unit costs and budget (B=2).
Create one task for each of the six pairs ({e_j,e_k}), with a two-edge
star, (alpha=1), (b_{e_j}=b_{e_k}=-1), and unit task weights. Each task
has loss one exactly when neither of its two resources is selected. The local
convex-hull epigraph for pair ({j,k}) has fractional lower envelope

\[
z_{jk}\ge\max(0,1-x_j-x_k).
\]

The fractional point (x_1=\cdots=x_4=1/2) satisfies the global budget and
sets every (z_{jk}=0). Any integer set of at most two resources leaves at
least one pair unselected, so the integer objective is at least one (and is
one when exactly two are selected). Thus all six local epigraphs can be ideal
while the shared budget and cross-task resource variables create a positive
global integrality gap. Local ideality is not global ideality.

#### Prior-art and classification

The local construction is a small disjunctive/order-statistic epigraph. Balas'
disjunctive convex-hull framework and Vielma's survey of embedding and
formulation techniques cover the underlying method; the ledger records the
source links and access limits. No source in this audit was shown to state the
PESS notation, but that absence is not evidence of originality. **Mathematical
status: PROVED UNDER STATED ASSUMPTIONS. Novelty: CLEARLY
CLASSICAL/SPECIAL CASE.**

### C2 — incidence structure versus task-graph structure

#### Valid restricted DP

Assume every nonempty task's entire eligible attribute graph is one connected
star (singleton and labeled parallel edges allowed), resource costs are
nonnegative integers, budget (B) is an integer, and the bipartite graph with
resource vertices on one side and task-factor vertices on the other is a
forest. For a task factor (i), its exact value is

\[
f_i(x_{E_i})=
\begin{cases}
|\alpha_i|,&\sum_{e\in E_i}x_e=0,\\
\max_{e:x_e=1}|\alpha_i+b_{e,i}|,&\text{otherwise}.
\end{cases}
\]

Root each incidence component. A resource-to-task message is indexed by the
parent resource bit and exact descendant budget; a resource cost is charged
once at its resource node. A task-to-resource message combines child-resource
messages and its factor value. To compute the latter exactly, enumerate the
distinct singleton values (v_{i,e}=|\alpha_i+b_{e,i}|) plus a NONE state,
and keep one Boolean recording whether the current threshold has been attained.
Min-plus budget convolutions over the children then give the exact message.
Ties are grouped by value or handled by a deterministic label order; NONE
remains distinct even if its value is zero. Zero-cost resources stay in the
same budget layer and are charged once, so they do not invalidate the tree DP.

This is a standard tree-factor dynamic program. A conservative arithmetic
operation bound of the form

\[
O\!\left((m+A+\sum_i d_i^2)(B+1)^2\right)
\]

is valid for the stated one-star factors, where (A=\sum_i d_i), subject to
the usual exact-rational arithmetic cost. It is **pseudo-polynomial in the
numeric budget**, not polynomial in the binary encoding of (B).

If a set of (k) resource vertices intersects every cycle of the incidence
graph, enumerate their (2^k) assignments, charge their costs once, remove
them, and run the forest DP on every residual forest and budget. This is exact
under the same one-star factor assumptions and is FPT in the combined
numeric parameters ((k,B)) only in a pseudo-polynomial sense; it is not an
FPT-in-(k)-alone claim for binary-encoded budgets.

These are **Proven (model-internal)** under their stated restrictions. They do
not say that arbitrary task graphs are star factors, or that a resource
feedback set repairs a non-star task factor.

#### Counterexamples to overly broad acyclicity claims

Incidence acyclicity alone is insufficient. Given positive integer SUBSET SUM
items (a_1,ldots,a_m) and target (K), make one task whose attribute graph
is a matching of (m) disjoint candidate edges, set

\[
\alpha=-K,\qquad b_e=a_e,qquad c_e=1,qquad B=m.
\]

The task-resource incidence graph is a tree (one task node adjacent to all
resource nodes), but the selected graph is a matching and has a unique
maximal matching containing exactly the selected edges. Hence

\[
F(M)=\left|-K+\sum_{e\in M}a_e\right|,
\]

which is zero exactly for a SUBSET SUM solution. The inner adversary is
trivial; the outer signed cancellation remains weakly NP-hard. This refutes
“acyclic incidence makes all PESS easy”. The connected-path reduction in C3 is
an independent counterexample with a connected attribute graph and strictly
positive corrections.

The task attribute graph, task-resource incidence graph, candidate-primal
graph, feedback-resource set, budget magnitude, and correction-sum magnitude
are distinct parameters. No one may be substituted for another without a
new proof.

#### Prior-art and classification

Tree-decomposition/CSP extended formulations and tree-factor marginal gluing
are classical. The 2016/2025 ground-set-cost budgeted maximum-coverage work
also explicitly gives forest-incidence pseudo-polynomial/FPTAS results and a
fixed-size feedback-node extension, but its nonnegative coverage factors are
not general signed PESS factors. **Mathematical status: PROVED UNDER STATED
ASSUMPTIONS for the restricted DP; the unrestricted acyclicity reading is
COUNTEREXAMPLE/REFUTED. Novelty: CLEARLY CLASSICAL/SPECIAL CASE.**

### C3 — connected path hardness and finite-boundary profile DP

#### Connected-path reduction

For a SUBSET SUM instance (a_1,ldots,a_m,K), let (L=m+1). Build a path
with (2m-1) alternating edges: item edges have corrections (La_j), and
the (m-1) connector edges have correction (1). Set

\[
\alpha=-LK,\qquad c_e=1,\qquad B=2m-1.
\]

All corrections are strictly positive and the budget is nonbinding. If a
subset (S) sums to (K), select only its item edges. The selected graph is a
matching with a unique maximal matching, and its loss is zero.

Conversely, if a selected resource set has worst loss zero, every maximal
matching (P) has zero loss. Choose any such (P). Let (s) be the sum of
the (a_j)'s for item edges in (P), and let (r) be the number of connector
edges in (P). Then

\[
Ls+r=LK,\qquad 0\le r\le m-1<L.
\]

Reduction modulo (L) gives (r=0), followed by (s=K). Thus a zero-loss
selection yields a SUBSET SUM solution. The path is connected; the
task-resource incidence graph with one task is still a star. This proves
weak NP-hardness of the outer selection problem even when a fixed selected
path has a polynomial-time inner oracle. It is not a strong-NP-hardness claim.

For membership in NP of this restricted zero-loss language, a candidate (M)
can be checked by the finite-boundary path DP below: compute the minimum and
maximum signed sums over maximal matchings of (H[M]), then check that the
maximum absolute affine loss is zero. This is a polynomial-time verifier for
the restricted path family. Therefore the restricted language is NP-complete
under the stated representation, weakly via SUBSET SUM. This does not classify
the unrestricted general PESS decision problem.

#### Exact finite-boundary profile DP

For a one-task path with outer bits (x_j) and inner matching bits (y_j),
with (y_0=y_{n+1}=0), maximality is exactly

\[
y_j\le x_j,\qquad y_j+y_{j+1}\le1,\qquad
x_j\le y_{j-1}+y_j+y_{j+1}.
\]

The last inequality says that every selected but unmatched edge is blocked by
a matched neighbor. A left-to-right transfer retains the boundary
((y_{j-1},y_j,x_j)), at most eight states. For one fixed outer prefix, retain
both the maximum and minimum prefix correction for every boundary state,
using (-\infty) and (+\infty) sentinels for unreachable states. When the
next outer bit is chosen, enforce the just-resolved maximality condition for
edge (j), then update the boundary. At the right endpoint enforce
(x_n\le y_{n-1}+y_n).

The max and min profiles must remain coupled to the **same outer prefix**.
For each exact profile pair, storing only the least nonnegative resource cost
is safe because all future transitions depend only on the profile and future
outer bits. With integer corrections and (H=\sum_j|b_j|), each of the 16
finite profile coordinates lies in ([-H,H]), plus its unreachable sentinel.
A coarse state bound is therefore ((2H+2)^{16}), yielding a
pseudo-polynomial arithmetic bound such as

\[
O\!\left(n(2H+2)^{16}\right).
\]

The exponent is a worst-case state-space bound, not a practical scaling
claim. It is pseudo-polynomial in the numeric correction range, not in the
bit length of the input; rational common-denominator scaling can enlarge the
range. With multiple tasks sharing resources, a joint profile (one pair per
task) is required, so the state space becomes a product and the one-task
claim does not transfer automatically.

#### Additive rounding and its limit

For one path, keep graph labels, admissibility, costs and budget fixed, and
round only (b_j) to (widetilde b_j). With
(S=\sum_j|b_j|>0), (delta=\varepsilon S/n), and nearest-grid rounding,

\[
\eta=\sum_j|b_j-\widetilde b_j|\le n\delta/2=\varepsilon S/2.
\]

Because the maximal-matching family is unchanged for every fixed (M), every
matching loss changes by at most (eta), and so does the task maximum. An
exact optimum of the rounded model then yields an original-model candidate
with additive error at most (2eta\le\varepsilon S), assuming exact
evaluation and exact optimization of the rounded model. A general certified
transfer is

\[
\max(0,\widetilde L-\eta)\le\operatorname{OPT},\qquad
F(\widehat M)\le\widetilde U+\eta,
\]

when (widetilde L) and (widetilde U) are genuine rounded-model lower and
upper bounds. A floating-point MILP “optimal” status is not such a certificate.

This is an **additive scale-(S)** statement. It is not a multiplicative
(1+\varepsilon) guarantee: the path reduction has zero-optimum instances,
and the bound can be vacuous when (S) is large relative to OPT. The standard
SUBSET SUM FPTAS/scaling literature and approximate-Pareto/label-DP literature
are prior art for the ingredients. **Mathematical status: PROVED UNDER STATED
ASSUMPTIONS for the reduction and DP; the multiplicative interpretation is
COUNTEREXAMPLE/REFUTED. Novelty: CLEARLY CLASSICAL/SPECIAL CASE.**

### C4 — matching-aware perturbation transfer

#### Proof

Fix each task graph and its labeled edges. Let the original coefficients be
((\alpha_i,b_{e,i})) and perturbed coefficients be
((\widetilde\alpha_i,\widetilde b_{e,i})). Keep the candidate labels,
graphs, task weights, maintenance rule, budget, and the complete admissible
family (Gamma_i(M)) unchanged. Define the ordinary matching error bound

\[
\rho_i=|\alpha_i-\widetilde\alpha_i|
 +\max_{Q\in\operatorname{Matchings}(H_i)}
     \sum_{e\in Q}|b_{e,i}-\widetilde b_{e,i}|.
\]

The inner maximum here is over ordinary matchings with nonnegative error
weights. It is not a maximal-matching optimization, and using it is safe
because every admissible maximal matching is an ordinary matching. For every
common admissible scheme (P),

\[
\left|
|\alpha_i+\sum_{e\in P}b_{e,i}|
-|\widetilde\alpha_i+\sum_{e\in P}\widetilde b_{e,i}|
\right|
\le |\alpha_i-\widetilde\alpha_i|
  +\sum_{e\in P}|b_{e,i}-\widetilde b_{e,i}|
\le\rho_i.
\]

The maximum over a common finite family is 1-Lipschitz in the uniform norm,
so (|W_i(M)-\widetilde W_i(M)|\le\rho_i). With nonnegative task weights,

\[
|F(M)-\widetilde F(M)|
\le\eta_{\rm match}:=\sum_iw_i\rho_i.
\]

Consequently, for a rounded-model lower bound (widetilde L) and a feasible
rounded-model upper bound (widetilde U),

\[
\operatorname{OPT}
\ge\max(0,\widetilde L-\eta_{\rm match}),
\qquad
F(\widehat M)\le\widetilde U+\eta_{\rm match}.
\]

If (widehat M) is an exactly optimal rounded selection, the usual transfer
gap is at most (2\eta_{\rm match}). Zero-rounded edges must remain in the
graph: setting a coefficient to zero is a parameter perturbation, while
deleting the edge changes (Gamma_i(M)) and invalidates the common-family
argument. Parallel labels must also remain labeled; an ordinary matching may
select at most one incident parallel label, but its error weight still belongs
to the labeled graph.

The transfer does not cover changes to candidate membership, admissibility,
task weights, costs, budget, PG rounding/clamping, or real DBMS policy. It also
does not turn a float solver result into an exact bound. **Mathematical status:
PROVED UNDER STATED ASSUMPTIONS. Novelty: CLEARLY CLASSICAL/SPECIAL CASE.**

#### Prior-art comparison

Decision-dependent robust optimization is established by Nohadani–Sharma and
subsequent work. The 2026 Lefebvre–Schmidt–Stevens–Thürauf preprint gives a
current branch-and-cut/DDRO comparison and explicitly limits special cuts to
appropriate uncertainty-set structure. General robust-stability literature
also studies Lipschitz/continuity transfer. The present matching-aware bound
is a useful PESS-specific instantiation of the reverse-triangle inequality
plus ordinary maximum-weight matching; the search did not establish a
publication-level gap.

## 4x evidence matrix

| Candidate | Origin/status in repository | Exact theorem or counterexample | Scope | Closest prior art | Unresolved question |
|---|---|---|---|---|---|
| C1 | #29 comments 6264019796/6263743093; explicitly model-internal, not novelty | STAR-HI projection equals the binary star epigraph hull; 4-resource/6-pair example gives global gap 1 vs fractional 0 | One connected star, labeled edges, arbitrary signs/ties, local epigraph; shared (x)/budget globally | Balas 1985; Vielma 2015; generic disjunctive/order-statistic formulations | A PESS-specific formulation may be useful computationally, but no unresolved mathematical novelty was documented |
| C2 | #29 comment 6264188244; theorem sketches and structure audit | Single-star factors on incidence forests admit exact budget DP; feedback-resource conditioning is exact; disjoint-edge SUBSET SUM refutes generic acyclicity | One connected star per task, integer costs/B; feedback parameter; not star forests or arbitrary task graphs | Kolman–Koutecký; Wainwright–Jordan; ground-set-cost coverage forest DP/FPTAS | Which mixed star/nonstar shared-resource classes yield useful certified algorithms remains open, but is a new bounded question, not established novelty |
| C3 | #29 comments 6264341665/6264364864/6265119316 | Positive-correction connected-path SUBSET SUM reduction; coupled 8-state min/max profile; additive \(\varepsilon S\) transfer | One path task for exact DP; fixed selected path; multi-task requires joint profile product; bit complexity matters | Ibarra–Kim; Kellerer et al.; Koiliaris–Xu; Papadimitriou–Yannakakis; Righini–Salani | Practical PESS-specific compression or cross-task algorithmic gain is untested and not a theorem of novelty |
| C4 | #29 comments 6265119316/6265230463; explicitly called correctness mechanism, likely generic | Uniform objective transfer via ordinary maximum-weight matching of errors; exact lower/upper formulas | Same graphs, labels, (Gamma_i(M)), weights, costs and budget; nonnegative task weights | Robust stability; DDRO; reverse triangle inequality and matching optimization | A tighter application-specific error allocation may be useful; no formal prior-art distinction was found |

## Literature coverage matrix

| Bucket | At least two primary sources located? | What they establish for this audit | What they do not establish |
|---|---:|---|---|
| Maximal matching / edge domination | Yes | Fixed-graph weighted maximal matching, exact algorithms, decomposition, tree polyhedral results | PESS outer shared-resource optimization or task-wise independent adversaries |
| Incidence/tree DP | Yes | Treewidth/CSP formulations, tree factor gluing, forest budgeted coverage and feedback-node methods | General signed maximal-matching factors with shared global budget |
| Disjunctive/order statistics | Two strong sources plus author PDF | Convex-hull and embedding methods are established | PESS publication novelty of the particular notation |
| SUBSET SUM/profile approximation | Yes | Weak numeric hardness, scaling/FPTAS, Pareto and label dominance are established ingredients | A multiplicative guarantee for zero-optimum PESS; an original PESS profile algorithm |
| DDRO/decomposition/perturbation | Yes | Decision-dependent uncertainty and branch-and-cut/decomposition are established; robust stability is known | The exact maximal-matching perturbation certificate as a published theorem |

Full bibliographic records, links, access limitations, and query provenance are
in [`bibliography-ledger.md`](bibliography-ledger.md). The search was targeted,
not exhaustive; inaccessible full text and uncertain priority are explicitly
marked there.

## Reproducible exact diagnostic

Command executed from the Issue #41 Worktree:

```text
./.venv/bin/python experiments/theory-stage1d/check_stage1d.py
```

Environment observed: Python 3.12.3; stdlib-only; no PostgreSQL, SciPy,
HiGHS, NetworkX, external input, or other repository was used. Output:

```text
stage1d exact diagnostics: PASS
checks: star convex hull, global coupling gap, path reduction, path profile DP, matching-aware transfer
```

The diagnostic uses exact `Fraction` arithmetic and bounded exhaustive
enumeration for the stated tiny cases. It checks, but does not prove:

- local STAR-HI values against an exact distribution LP on small fractional
  grids, including ties and signed coefficients;
- the explicit global local-ideality/budget gap;
- the connected-path reduction on deterministic small instances;
- the fixed-selected path profile transition against independent maximal-
  matching enumeration;
- the matching-aware perturbation inequality on a labeled multigraph with a
  parallel edge and zero-rounded coefficients.

No runtime, scaling, speedup, PostgreSQL behavior, or literature novelty is
inferred from this diagnostic.

## Stage 1B implications and limits

The audit supports only the following conditional implication for Stage 1B:
local star or path inner structure may reduce the cost of evaluating a fixed
selection, while shared global resource/budget coupling can remain the main
outer bottleneck. It does **not** authorize changing Stage 1B's frozen
benchmark protocol, importing a profile DP as a solver baseline, or claiming a
speed improvement. The Stage 0B negative finding that coefficient quantization
alone did not establish a useful exhaustive-state/time advantage remains
separate evidence and is not overwritten.

## Decision

**Separate formal theory Issue: NO-GO on the four audited candidates.**

The claims that survive are worth preserving as carefully scoped lemmas,
counterexamples and correctness interfaces. None is currently a fully stated
structural claim with a source-backed unresolved prior-art distinction meeting
Issue #41's GO gate. The strongest negative conclusion is itself useful:

1. local ideality does not remove global shared-budget gaps;
2. incidence forests do not neutralize signed outer selection;
3. paths can be weakly hard despite a finite-state inner oracle;
4. matching-aware rounding transfer is valid but generic in mechanism.

Any future authorization should name a new bounded question—such as a tested
PESS-specific cross-task cut or a topology-adaptive method—and require a fresh
manifest and prior-art gate. This audit does not authorize that work.
