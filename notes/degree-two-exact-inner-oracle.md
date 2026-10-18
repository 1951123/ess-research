# Exact signed maximal-matching oracle on selected paths, cycles, and stars

**2026-10-18. Status:** model-internal proof + reproducible integer-weight
test implementation; not a new general graph-algorithm invention and not a
claim about actual PostgreSQL plan-selection policies. This note supplements
existing exact master/oracle and structural-factor notes.

## Fixed-selection inner evaluation

For a chosen global set M, let G = H_i[M] be task i's **selected**
edge-labeled multigraph, with no loops. Define the minimum/maximum matching
weight across its *maximal* matchings:

\[
s_i^-(M)=\min_{P\in\operatorname{MaximalMatchings}(G)}
\sum_{e\in P}b_{e,i},\quad
s_i^+(M)=\max_{P\in\operatorname{MaximalMatchings}(G)}
\sum_{e\in P}b_{e,i}.
\]

**Lemma 1 (endpoints).** For arbitrary real signed coefficients,

\[
\boxed{W_i(M)=\max\{|\alpha_i+s_i^-(M)|,\,
|\alpha_i+s_i^+(M)|\}.}
\]

**Proof.** The absolute value of an affine function is convex.
All feasible sums lie in the interval between the extrema, and neither
endpoint is merely hypothetical: finite maximal-matching families attain
both. Hence the maximum over the family equals the larger endpoint
loss. QED.

This is NOT the unconstrained maximum-weight matching problem; the
**maximality** requirement on each selected graph is essential.

## Parallel labels and components

Collapse each group of parallel selected candidate labels sharing
unordered endpoints {u,v} to one **edge bundle** g.
Any maximal matching uses at most one label in a bundle. Replacing
such a label with another from the same bundle preserves the chosen
matching's set of saturated vertices and maximality. Therefore, for
a given choice of selected bundles, weight minimization can use

\[
c_g^-=\min_{e\in g} b_e
\]

and maximization can use its counterpart c_g^+ = max b_e.
Choosing the extreme independently for each used bundle is valid,
including with mixed signs; **dropping labels without remembering both
extrema would be unsound**.

For vertex-disjoint selected components G_1,...,G_q, maximal matchings
factor as a Cartesian product. Thus each weight extreme is the sum
of its componentwise weight extremes. Isolated vertices are irrelevant.

## Paths: a four-state dynamic program

Let a nonempty selected path have m >= 1 edge bundles ordered
1,...,m. For each bundle, let y_j in {0,1} indicate whether it is
matched (with one label selected if y_j=1). Set y_0=y_{m+1}=0.

**Lemma 2 (path characterization).** The selected labels form a
maximal matching if and only if:

\[
y_j+y_{j+1}\leq1\quad(1\leq j<m),
\qquad
y_{j-1}+y_j+y_{j+1}\geq1\quad(1\leq j\leq m).
\]

**Proof.** The first inequality prevents two incident selected
bundles. A violation of the second means that bundle j itself and
both its neighbors are unchosen, so a label in this *available*
bundle could still be inserted. Conversely, the second inequality
ensures every unchosen available bundle is blocked by a chosen
neighbor. Each parallel label has the same conflicts. QED.

**Algorithm.** Process bundles from left to right, remembering only
the last two bits. For a new bit, reject adjacent ones and reject
a zero triple leaving the preceding bundle undominated. Add the
chosen bundle's c_g^- or c_g^+ to the respective min/max total.
Initialize the previous two bits at zero. Append a forced zero
sentinel at the end to check domination of the last bundle.
There are at most four DP states with two possible next bits.
Both extrema take O(m) arithmetic operations, even with negative weights.

## Cycles: constant-size boundary enumeration

For a selected simple cycle with m >= 3 bundles, constraints are the
same with cyclic indices. Enumerate the three admissible initial
pairs (y_1,y_2) in {(0,0),(0,1),(1,0)}, run the same four-state
recurrence through y_m, and enforce:

\[
y_m+y_1\leq1,\quad
y_{m-1}+y_m+y_1\geq1,\quad
y_m+y_1+y_2\geq1.
\]

The first closes the matching; the other two close the final
domination constraints. Every maximal matching determines a
unique initial pair and passes these checks; all accepted strings
represent maximal matchings. This gives O(m) arithmetic operations.
An endpoint pair with multiple parallel labels is a **one-bundle
path**, not a length-two simple cycle.

## Stars

Every edge in a nonempty selected star shares a common center, so
every maximal matching is a singleton. Consequently,

\[
s^-(G_\star)=\min_{e\in E(G_\star)}b_e,\qquad
s^+(G_\star)=\max_{e\in E(G_\star)}b_e.
\]

This also covers single edges and two-edge paths.

### Theorem 3 (adaptive inner oracle)

Fix the advisor's selection M and task i. If every nontrivial
connected component of the **selected simple graph** obtained by
collapsing parallel labels in H_i[M] is a path, cycle or star,
then its exact worst-case absolute affine loss W_i(M) is computable
in O(|V_i'|+|M intersect E_i|) arithmetic/graph-traversal operations,
where V_i' are the non-isolated attributes.

**Proof.** Group parallel labels and partition connected components
in linear time. For each component calculate its min/max weight
from Lemma 2 and the path DP, the cycle boundary enumeration, or the
star scan. Component extrema add. Apply Lemma 1. Each component
vertex and selected labeled candidate is visited a constant
number of times. QED.

This count assumes unit-cost arithmetic/comparisons. The same
mathematics works for exact rationals with appropriate bit-cost
accounting, but production log coefficients need a documented
numerical-certification policy. The accompanying Python code
deliberately uses exact **integer weights**.

Importantly, the condition is on H_i[M], **not** necessarily the
full graph H_i. A general selected topology must be rejected or
delegated to a general exact oracle; it must NOT silently use the
special-case recurrence.

## How this advances PESS-ESS (and what it does not prove)

The existing model in
[master-oracle-algorithm-design.md](master-oracle-algorithm-design.md)
requires a worst-case inner matching witness or value at each
integer master incumbent. A future hybrid oracle can inspect
the **current** selected subgraph and choose this certified
fast path, leaving a general exact solver for remaining cases.

This does NOT imply that optimizing the outer set M is easy.
Indeed, the independent pending
[constant-factor Vertex-Cover reduction PR #12](https://github.com/1951123/ess-research/pull/12)
has each task's graph a two-edge star and nonetheless has a
NP-complete restricted outer zero-loss decision problem.
The low-degree **attribute graph per task** is not the
candidate-primal graph used by the bounded-width outer DP.

The source paper by Richey and Parker [R1] gives a **strictly
wider** linear-time special case: weighted minimum maximal
matching on series-parallel graphs, even with arbitrary integer
edge weights. Hence the graph algorithm in this note must be
described as an explicit application/specialization, not a
new matching-complexity discovery.

## Reproducibility

Source: experiments/theory/degree_two_oracle.py

Independent exact-combinatorial tests:
experiments/theory/test_degree_two_oracle.py

Run from repository root:

    python -m pytest -q experiments/theory/test_degree_two_oracle.py

Tests enumerate all selected labeled-edge subsets on small random
paths, cycles and stars including parallel edges and negative
weights. For each selected instance, a completely separate
brute-force routine enumerates ALL maximal matchings and compares
the min/max sums and absolute losses. Additional tests cover mixed
disconnected components and reject unsupported branching/loops.

The Draft PR adds the test path to lightweight CI. No PostgreSQL
benchmark, manuscript change or claim of solver speedup is made.
This is a verified exact oracle *design*, not yet an integrated
ess-advisor algorithm.

## Prior literature

- [R1] M. B. Richey and R. G. Parker, "Minimum-maximal matching in
  series-parallel graphs," European Journal of Operational Research,
  33(1):98–105, 1988.
  https://doi.org/10.1016/0377-2217(88)90258-5
  (Linear-time weighted algorithm; arbitrary integer edge weights.)
- [R2] J. M. M. van Rooij and H. L. Bodlaender, "Exact Algorithms for
  Edge Domination," Algorithmica, 2012.
  https://doi.org/10.1007/s00453-011-9546-x
  (General-graph exact exponential and parameterized approaches,
  including minimum-weight maximal matching.)
- [R3] O. Nohadani and K. Sharma, "Optimization under Decision-Dependent
  Uncertainty," SIAM Journal on Optimization 28(2), 2018.
  https://doi.org/10.1137/17M1110560
  (Broader DDRO framework; does not turn our discrete maximization
  inner oracle automatically into an easy single-level reformulation.)
