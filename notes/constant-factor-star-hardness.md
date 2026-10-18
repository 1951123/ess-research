# Constant-factor outer-selection hardness on two-edge star tasks

**Status (2026-10-18):** a model-internal polynomial reduction and its immediate
approximation implications, accompanied by an independent small-instance
combinatorial check. **Not a claim of literature novelty, a PostgreSQL physical
realization, or a new algorithm.** This note supplements
[structured-outer-selection](structured-outer-selection.md) and
[structural-foundations](structural-foundations.md); it does not replace their
different Knapsack and Subset Sum reductions.

## 1. Scope and input representation

We consider only the structured pairwise/maximal-matching **instantiation**
of PESS-ESS, with one global resource choice \(M\subseteq\mathcal E\):

\[
F(M)=\sum_{i\in\mathcal I}w_i
\max_{P\in\operatorname{MaximalMatchings}(H_i[M])}
\left|\alpha_i+\sum_{e\in P}b_{e,i}\right|,
\qquad
\sum_{e\in M}\bar m_e\le B.
\]

Every candidate \(e\) is an edge labeled by a pair of distinct attributes.
Only the edges in \(\mathcal E_i\) are eligible for task \(i\). The empty
matching is the unique maximal matching of an edgeless selected graph.

The hardness result below permits *constant-size positive rational
multipliers*: for each task,
\[
n_i^0/T_i=2,\qquad r_{e,i}=1/2,\qquad
\alpha_i=\ln2,\qquad b_{e,i}=-\ln2.
\]
Thus the reduction need not encode an arbitrary integer as a logarithm of an
exponentially large rational, or assume arbitrary real coefficients are input
as exact machine numbers. The loss takes only the exact symbolic values
\(0\) and \(\ln2\). Its **zero-optimum decision** can be checked entirely
using the rational multipliers and graph incidence. Resource maintenance
coefficients and workload weights are all \(1\).

This is a *coefficient-level mathematical input family*. No claim is made
that a real PG16.14 cardinality estimator realizes every constructed factor
of \(1/2\).

## 2. Two-edge-star normal form

Let all candidates be edges of a single global star with common attribute
\(h\). For each candidate index \(v\), create an edge
\(e_v=\{h,a_v\}\), where all leaves \(a_v\) are distinct. A task can be
eligible for any specified subset of these labeled edges.

For any task \(i\) and any selected set \(M\):

* If \(M\cap\mathcal E_i=\varnothing\), the sole maximal matching is empty.
* Otherwise every maximal matching is a singleton \(\{e\}\) with
  \(e\in M\cap\mathcal E_i\).

Under the above constant multipliers, it follows **for all** \(M\) that
\[
\boxed{
W_i(M)=
\begin{cases}
\ln2,&M\cap\mathcal E_i=\varnothing,\\
0,&M\cap\mathcal E_i\ne\varnothing.
\end{cases}}
\tag{1}
\]
The adversary may have a choice between several singletons, but they have
identical loss. Hence all inner task values are computable by a simple
nonempty-intersection check. Hardness, if present, is entirely an **outer
shared-selection phenomenon**.

## 3. NP-completeness with task scopes of size two

### Theorem 1 (zero-loss decision is NP-complete on two-edge stars)

Consider the decision version of structured PESS-ESS that asks whether a
budget-feasible resource selection has \(F(M)=0\). It remains NP-complete
on the restricted family where all of the following hold simultaneously:

1. The **union of all candidate graphs** is a star (one common center).
2. Each task has **exactly two eligible edges**, which form a two-edge star.
3. Every \(w_i=1\), every \(\bar m_e=1\), and \(B=k\) is an integer.
4. Every baseline ratio \(n_i^0/T_i=2\) and every applicable pair correction
   \(r_{e,i}=1/2\) (constant-size rational inputs).
5. All tasks use maximal matchings, and their inner worst-case values are
   explicitly computable in constant time.

**Proof.** Reduce **VERTEX COVER**. Let the source be a finite simple graph
\(G=(V,E_G)\) and cardinality bound \(k\). Create one resource \(e_v\)
for every vertex \(v\in V\), with a common attribute \(h\) and unique leaf
\(a_v\): \(e_v=\{h,a_v\}\). Give all resources unit maintenance cost and
choose \(B=k\).

For each source edge \(q=\{u,v\}\in E_G\), create **one task**
\(i_q\), whose two eligible resources are precisely \(e_u,e_v\).
Its graph is a two-edge star. Give it \(w_{i_q}=1\) and the constant
ratios from Section 1.

For a selected resource set \(M\), define the corresponding source-vertex
set \(C(M)=\{v:e_v\in M\}\). By (1), task \(i_{\{u,v\}}\) incurs
loss \(\ln2\) exactly when neither endpoint lies in \(C(M)\), and loss
zero otherwise. Consequently,
\[
F(M)=\ln2\,|\{\{u,v\}\in E_G:\ u\notin C(M),\ v\notin C(M)\}|.
\tag{2}
\]
The budget condition is precisely \(|C(M)|\le k\).
Hence there exists a selection with \(F(M)=0\) if and only if
\(G\) has a vertex cover of size at most \(k\).

The construction creates \(|V|\) candidate edges and \(|E_G|\) tasks,
each with only two eligible edges and constant-size rational coefficients.
It is polynomial in the source input.

The **restricted** decision problem is in NP: a candidate certificate
\(M\) has at most \(|V|\) bits; verify \(|M|\le k\), and check for
each two-edge task whether at least one of its edges is selected.
By (1), these checks determine whether \(F(M)=0\) in polynomial time.
Since VERTEX COVER is NP-complete, the restricted problem is
NP-complete. \(\square\)

The theorem is about **this restricted decision language**, not a
membership-in-NP assertion for the completely general PESS-ESS decision
problem, which has potentially hard adversarial inner maximization.

**Boundary sharpened relative to existing notes.** The earlier
Knapsack reduction in [structured-outer-selection](structured-outer-selection.md)
gives weak NP-hardness even for one candidate per task and a forest of
independent task--candidate components. The present construction keeps
*all numeric values constant and each task scope at most two* and already
encodes VERTEX COVER through the shared global selection. Therefore
bounded local task scope and trivial inner oracles, alone, are not
sufficient for polynomial outer optimization. The task--candidate
incidence/primal graph may nevertheless have high width; this is
consistent with the conditional bounded-primal-treewidth DP discussed
in the previous notes.

The original VERTEX COVER hardness is classic; see Garey, Johnson and
Stockmeyer (1976) and their cited predecessors [R1]. The specific
construction above is a direct reduction for our **defined** model.
It is not claimed to be new in the wider literature.

## 4. General star tasks encode MAXIMUM COVERAGE exactly

Remove only the restriction that each task has at most two eligible
edges, keeping the common-center star and *all numeric constants*.

Take an instance of MAXIMUM \(k\)-COVERAGE: universe
\(U=\{u_1,\ldots,u_n\}\), sets \(S_1,\ldots,S_m\subseteq U\), choose
up to \(k\) sets. Create one candidate \(e_j=\{h,a_j\}\) for each
source set \(S_j\). Create one task \(i_u\) for each universe
element \(u\), with eligible edges
\(\mathcal E_{i_u}=\{e_j:u\in S_j\}\). A source element contained
in no source set gives an edgeless task with unavoidable loss, correctly
representing an uncovered element.

By (1),
\[
\boxed{
F(M)=\ln2\left(n-\left|\bigcup_{e_j\in M}S_j\right|\right).
}
\tag{3}
\]
In particular, minimizing \(F\) is **exactly equivalent** to
maximizing coverage, not merely an approximation-preserving similarity.

### Corollary 2 (the correct restricted benefit approximation)

Let
\[
G(M)=F(\varnothing)-F(M)
=\ln2\,\left|\bigcup_{e_j\in M}S_j\right|.
\]
For this restricted family, \(G\) is normalized, monotone,
nonnegative and submodular. With a unit-cost budget \(|M|\le k\),
classical maximum-coverage greedy selection obtains
\[
G(M_{\rm greedy})\ge(1-1/e)\max_{|M|\le k}G(M),
\]
and the stronger standard finite-\(k\) bound
\(1-(1-1/k)^k\) applies for \(k\ge1\).
The familiar \(1-1/e\) approximation threshold for **coverage benefit**
also transfers to this larger star family under standard complexity
assumptions, because its objective is exactly the source MAXIMUM
\(k\)-COVERAGE benefit [R2, R3].

**Do not overtransfer either conclusion.**
The submodularity and greedy bound concern \(G=F(\varnothing)-F\) on
the *constant-multiplier star coverage family*, not arbitrary
mixed-sign maximal-matching PESS-ESS. Also, the \(1-1/e\) hardness
bound from general max coverage is **not** automatically a tight bound
for the more restricted two-edge-per-task family, which is MAX
\(k\)-VERTEX COVER and has stronger specialized approximation
results [R4].

### Corollary 3 (why raw-loss ratios can mislead)

For the restricted decision family in Theorem 1, no polynomial-time
algorithm can guarantee a **finite multiplicative approximation
ratio on the nonnegative minimization loss \(F\) for all instances
including \(F^*=0\)** unless P=NP. Under the conventional definition
\(F(\widehat M)\le cF^*\) with finite \(c\), a zero-optimum input
forces \(F(\widehat M)=0\), deciding VERTEX COVER via Theorem 1.
This observation relies on allowing zero optima. It does **not**
exclude additive-error guarantees or guarantees on the
baseline-relative improvement \(G\); the latter admits the
coverage guarantee above in its restricted domain.

## 5. Connection to the existing master/oracle research

Nothing in this note changes the already proven conditional scenario-cut
characterization in
[conditional-adversarial-constraints](conditional-adversarial-constraints.md)
or the sign-coherent cases in
[master-oracle-algorithm-design](master-oracle-algorithm-design.md).

* The present reduction has **opposite-signed** \(\alpha_i>0\) and
  \(b_{e,i}<0\). It does not contradict the previous result that if
  all tasks have a nonnegative baseline and nonnegative corrections,
  or the symmetric all-nonpositive regime, \(M=\varnothing\) is
  optimal.
* The inner graphs here are stars and the adversarial objective value
  is trivial, yet shared outer selection is NP-hard. Conversely,
  the known NP-hard minimum maximal matching result [R5] shows
  difficult inner evaluation even when \(M\) is fixed in more
  general graphs. These are **independent complexity sources**.
* A task scope bound of two alone does not bound the primal graph's
  treewidth. The source VERTEX COVER graph is exactly the candidate
  interaction graph in Theorem 1; it can have large treewidth.
* Applying unconditional matching-scenario cuts across distinct
  resource choices remains invalid; the exact conditional-cut
  method in existing notes addresses that issue.
* Decision-dependent robust optimization is the proper broader
  methodological comparison [R6]. This reduction neither
  establishes a new \(\Sigma_2^P\)-hardness classification nor
  demonstrates algorithmic superiority to established DDRO methods.

## 6. Independent exhaustive sanity check

A local stdlib-Python combinatorial cross-check was performed on
2026-10-18 without PostgreSQL or an MILP solver.

* Random source VERTEX COVER graphs: seed 18; 600 graphs,
  2--9 vertices; checked **74,692** vertex selections.
  For every selection, the number of uncovered source edges equaled
  the sum of the normalized star-task losses (losses divided by
  \(\ln2\)); each instance's zero-loss feasibility under its
  randomly selected budget equaled its vertex-cover feasibility.
* Random MAX COVERAGE set systems: seed 20261018; 600 systems with
  1--7 sets and 1--7 elements; checked **21,438** selected
  configurations. Every normalized task loss equaled the number
  of uncovered elements; each optimum agreed with maximum coverage
  under the same cardinality budget.

These are arithmetic/graph-combinatorics checks of the reductions,
**not** experimental measurements of PostgreSQL and not formal proofs
or a claim of certified solver output. The proofs above stand
independently.

## 7. Research implications and open questions

1. The paper can present the weak Knapsack obstruction and the
   stronger **constant-ratio two-edge-star/Vertex-Cover obstruction**
   as distinct outer-hardness boundaries. Check whether an
   even narrower practically realizable PG class can support one.
2. Benchmarking against maximum coverage or maximum \(k\)-vertex
   cover makes sense as a **special-case correctness baseline**.
   Do not borrow their greedy guarantees for arbitrary PESS-ESS.
3. The next substantive algorithm work should compare the existing
   exact conditional master/oracle and factor-table/bounded-width
   methods on instances with *nontrivial* adversarial matching
   ambiguity. The coverage reductions intentionally lack such
   ambiguity and cannot prove a novel performance advantage.
4. A complete combined complexity classification and a useful
   approximation result for genuinely mixed-sign general graphs
   remain open.

## References

- [R1] Garey, Johnson, Stockmeyer (1976), *Some Simplified NP-Complete
  Graph Problems*, Theoretical Computer Science 1(3), 237--267.
  https://doi.org/10.1016/0304-3975(76)90059-1
- [R2] Nemhauser, Wolsey, Fisher (1978), *An Analysis of Approximations
  for Maximizing Submodular Set Functions—I*, Mathematical
  Programming 14, 265--294. https://doi.org/10.1007/BF01588971
- [R3] Feige (1998), *A Threshold of ln n for Approximating Set Cover*,
  Journal of the ACM 45(4), 634--652.
  https://doi.org/10.1145/285055.285059
- [R4] Bonnet, Escoffier, Paschos, Stamoulis (2018),
  *Purely combinatorial approximation algorithms for maximum
  k-vertex cover in bipartite graphs*, Discrete Optimization 27,
  26--56. https://doi.org/10.1016/j.disopt.2017.09.001
- [R5] Yannakakis, Gavril (1980), *Edge Dominating Sets in Graphs*,
  SIAM Journal on Applied Mathematics 38(3), 364--372.
  https://doi.org/10.1137/0138030
- [R6] Nohadani, Sharma (2018), *Optimization under Decision-Dependent
  Uncertainty*, SIAM Journal on Optimization 28(2), 1773--1795.
  https://doi.org/10.1137/17M1110560
