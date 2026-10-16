# Conditional Adversarial Constraints for PESS-ESS

This note develops an exact finite formulation for the two-column
maximal-matching instantiation of PESS-ESS. Its central point is that
admissibility depends on the global resource decision: a matching is a legal
complete scheme only when it is both available and maximal in the selected
graph. This dependence can be expressed by valid conditional constraints.

The resource decision remains one unordered set \(M\), or equivalently one
binary vector \(x\). The additive maintenance budget below uses the
coefficients \(\bar m_e\) from the structured outer-selection note; they are
maintenance coefficients, not creation costs. No PostgreSQL creation order,
OID order, or internal priority is an optimization variable.

## 1. Conditional admissibility of a matching

For task \(i\), let

\[
H_i=(V_i,\mathcal E_i)
\]

be its full eligible edge-labeled multigraph. Each \(e\in\mathcal E_i\) has
an endpoint set \(A_e\) of two attributes. Parallel labeled edges are
distinct candidates even when they have the same endpoints. For a matching
\(P\) of the full graph, define its saturated attribute set

\[
V(P)=\bigcup_{e\in P}A_e
\]

and the candidates disjoint from all attributes saturated by \(P\):

\[
D_i(P)=
\{f\in\mathcal E_i:A_f\cap V(P)=\varnothing\}.
\]

Let \(H_i[M]\) denote the subgraph containing precisely the eligible edges in
\(M\cap\mathcal E_i\), with the same attribute vertices and candidate labels.

### Proposition 1 (conditional maximality)

For every matching \(P\) of \(H_i\) and every \(M\subseteq\mathcal E\),

\[
P\in\operatorname{MaximalMatchings}(H_i[M])
\iff
P\subseteq M
\ \land\
M\cap D_i(P)=\varnothing .
\]

**Proof.** Suppose first that \(P\) is maximal in \(H_i[M]\). It is a
matching of the selected graph, so every \(e\in P\) belongs to \(M\), giving
\(P\subseteq M\). If some \(f\in M\cap D_i(P)\) existed, then \(f\) would be
an available edge whose two endpoints are not saturated by \(P\). It could be
added to \(P\), contradicting maximality.

Conversely, suppose \(P\subseteq M\) and \(M\cap D_i(P)=\varnothing\).
Then \(P\) is a matching of \(H_i[M]\). Every edge \(f\) available in
\(H_i[M]\) has \(f\notin D_i(P)\), so \(A_f\cap V(P)\neq\varnothing\).
Thus \(f\) conflicts with an edge of \(P\) and cannot be added. Hence \(P\)
is maximal in \(H_i[M]\). \(\square\)

This is a condition defining the legal-scheme family
\(\operatorname{MaximalMatchings}(H_i[M])\); it is not a claim about which
matching a deterministic DBMS policy actually selects.

The proposition includes the relevant edge cases. For the empty matching,
\(V(P)=\varnothing\) and \(D_i(P)=\mathcal E_i\), so it is maximal exactly
when \(M\cap\mathcal E_i=\varnothing\). An edgeless task graph has this
unique empty maximal matching. Isolated attribute vertices do not belong to
any \(A_e\) and therefore do not affect the condition. Parallel labeled
edges with the same endpoints intersect \(V(P)\) whenever one of them is in
\(P\), so the labels are preserved without allowing conflicting parallel
edges in one matching.

## 2. Binary encoding of admissibility

Let

\[
x_e=\mathbf 1[e\in M]\in\{0,1\}.
\]

For a matching \(P\), define

\[
\delta_i(P,x)=
\sum_{e\in P}(1-x_e)
+\sum_{f\in D_i(P)}x_f.
\]

### Proposition 2 (zero violation is exact)

For binary \(x\),

\[
\delta_i(P,x)=0
\iff
P\in\operatorname{MaximalMatchings}(H_i[M]),
\]

where \(M=\{e\in\mathcal E:x_e=1\}\).

**Proof.** Every summand is a nonnegative integer. Therefore the sum is zero
if and only if \(x_e=1\) for every \(e\in P\), and \(x_f=0\) for every
\(f\in D_i(P)\). These two conditions are exactly
\(P\subseteq M\) and \(M\cap D_i(P)=\varnothing\), respectively. Proposition
1 completes the equivalence. \(\square\)

The second term is essential. The availability condition \(P\subseteq M\)
alone would admit matchings that are extendible by a selected disjoint edge;
such a matching is not a complete admissible scheme under the
maximal-matching abstraction.

## 3. A finite exact epigraph formulation

For every full-graph matching \(P\), define its surrogate loss

\[
L_i(P)=
\left|\alpha_i+\sum_{e\in P}b_{e,i}\right|.
\]

The finite quantity

\[
U_i=|\alpha_i|+\sum_{e\in\mathcal E_i}|b_{e,i}|
\]

is a valid upper bound because \(P\subseteq\mathcal E_i\) implies

\[
0\leq L_i(P)
\leq|\alpha_i|+\sum_{e\in P}|b_{e,i}|
\leq U_i.
\]

Let \(\mathcal M_i=\operatorname{Matchings}(H_i)\) be the finite set of all
matchings of the full eligible graph, including the empty matching. Consider
the binary epigraph formulation

\[
\boxed{
\begin{aligned}
\min_{x,z}\quad&
\sum_{i\in\mathcal I}w_i z_i\\
\mathrm{s.t.}\quad&
\sum_{e\in\mathcal E}\bar m_e x_e\leq B,\\
&x_e\in\{0,1\} \qquad(e\in\mathcal E),\\
&z_i\geq0 \qquad(i\in\mathcal I),\\
&z_i\geq L_i(P)-U_i\delta_i(P,x)
 \qquad(i\in\mathcal I,\ P\in\mathcal M_i).
\end{aligned}
}
\]

### Theorem 1 (epigraph equivalence)

For every fixed binary vector \(x\), minimizing \(z_i\) subject to the
constraints for task \(i\) gives

\[
\min z_i
=
\max_{P\in\operatorname{MaximalMatchings}(H_i[M])}L_i(P).
\]

Consequently, the boxed formulation has exactly the same optimal value and
optimal resource sets as

\[
\min_{\substack{M\subseteq\mathcal E\\
\sum_{e\in M}\bar m_e\leq B}}
\sum_{i\in\mathcal I}w_i
\max_{P\in\operatorname{MaximalMatchings}(H_i[M])}
L_i(P).
\]

**Proof.** Fix binary \(x\) and its selected set \(M\). By Proposition 2,
\(\delta_i(P,x)=0\) exactly for the maximal matchings of \(H_i[M]\). For
each such matching, the epigraph constraint is \(z_i\geq L_i(P)\).

If \(P\) is not admissible, then \(\delta_i(P,x)\) is a positive integer and
therefore at least one. The upper-bound inequality gives

\[
L_i(P)-U_i\delta_i(P,x)
\leq L_i(P)-U_i\leq0.
\]

Thus every nonadmissible constraint is redundant with \(z_i\geq0\). The
smallest feasible \(z_i\) is exactly the maximum loss over the admissible
maximal matchings. Summing with \(w_i>0\) and retaining the same maintenance
constraint proves equality of the two optimization problems. \(\square\)

The formulation remains valid for negative, zero, or positive
\(b_{e,i}\), because the absolute-value loss is bounded by \(U_i\) without a
sign assumption. Zero coefficients are harmless, and \(U_i=0\) simply means
that all matching losses are zero. Zero-maintenance resources are also
valid: they may be selected without consuming budget, while their selection
still changes admissibility through \(x\). For an empty task graph, the only
matching is empty, \(D_i(P)=\varnothing\), and the formulation contains the
single correct baseline epigraph constraint.

The formulation is finite because every \(H_i\) is finite. It can nevertheless
be exponentially large: a graph can have exponentially many matchings, and
the formulation contains a conditional inequality for every one. The bound
\(U_i\) is a correctness device, not an assertion that a resulting
mixed-integer model will be numerically well conditioned.

### Formulation strengthening: matching-specific and floor cuts

The generic bound \(U_i\) can be tightened without changing the integer
formulation. For a matching \(P\), write \(L=L_i(P)\) and
\(\delta=\delta_i(P,x)\). Since \(0\leq L\leq U_i\) and \(\delta\geq0\),
\[
L(1-\delta)-\bigl(L-U_i\delta\bigr)
=(U_i-L)\delta\geq0.
\]
Thus, with the common constraint \(z_i\geq0\), the
matching-specific inequality
\[
\boxed{z_i\geq L_i(P)\bigl(1-\delta_i(P,x)\bigr)}
\]
dominates the \(U_i\)-based inequality throughout the continuous relaxation
\(0\leq x\leq1\). For binary \(x\), an admissible matching has
\(\delta=0\), while every inadmissible matching has integer
\(\delta\geq1\). The displayed right-hand side is therefore \(L_i(P)\) for
an admissible matching and is at most zero otherwise, proving exactness.

A further unconditional lower bound follows from ordinary, not necessarily
maximal, matching extrema:
\[
a_i^-=\min_{P\in\operatorname{Matchings}(H_i)}
       \sum_{e\in P}b_{e,i},\qquad
a_i^+=\max_{P\in\operatorname{Matchings}(H_i)}
       \sum_{e\in P}b_{e,i},
\]
\[
\lambda_i=\max\{0,\alpha_i+a_i^-,-\alpha_i-a_i^+\}.
\]
Every matching sum lies in \([a_i^-,a_i^+]\), so \(\lambda_i\) is the
distance from zero to the interval
\([\alpha_i+a_i^-,\alpha_i+a_i^+]\). Hence
\(\lambda_i\leq L_i(P)\) for every full-graph matching \(P\), and
\(0\leq\lambda_i\leq W_i(M)\) for every \(M\). The two extrema are ordinary
weighted matching problems and are polynomial-time computable for exactly
encoded rational or integer weights, including signed weights.

The floor-strengthened family is
\[
\boxed{
\quad z_i\geq\lambda_i,\qquad
z_i\geq L_i(P)
-(L_i(P)-\lambda_i)\delta_i(P,x).\quad}
\]
Because \(L_i(P)\geq\lambda_i\), its conditional right-hand side dominates
the matching-specific one, and the floor also dominates \(z_i\geq0\);
therefore it dominates both earlier formulations on their common
continuous relaxation. For binary \(x\), it is exact: \(\delta=0\) activates
the loss constraint, whereas \(\delta\geq1\) makes its right-hand side at
most \(\lambda_i\). The coefficient \(L_i(P)-\lambda_i\) is the smallest
uniform deactivation coefficient if the only information about an
inadmissible binary pattern is \(\delta\geq1\). A smaller coefficient can be
valid only after exploiting additional restrictions that rule out patterns
with \(\delta=1\). This strengthening does not make the LP relaxation
ideal.

## 4. Exact conditional constraint generation

The matching-indexed formulation need not be materialized in advance. Let
\(\mathcal C_i\subseteq\mathcal M_i\) be the matching constraints currently
present in a restricted master. The master contains the budget, binary
\(x\), nonnegative \(z\), and

\[
z_i\geq L_i(P)-U_i\delta_i(P,x)
\qquad(P\in\mathcal C_i).
\]

At an integer master incumbent \((\hat x,\hat z)\), an exact separation
oracle performs, for each task,

1. construct \(M(\hat x)\);
2. compute an admissible matching
   \(\hat P_i\in\operatorname{MaximalMatchings}(H_i[M(\hat x)])\) with maximum
   \(L_i(P)\);
3. if \(L_i(\hat P_i)>\hat z_i\), add the globally valid conditional
   constraint for \(\hat P_i\); and
4. repeat until no task has a violated constraint.

The oracle in step 2 is precisely the worst-case maximal-matching evaluation
for a fixed selected graph. The known hardness of this oracle is not removed
by writing the outer problem with conditional cuts.

### Theorem 2 (finite exact generation under idealized assumptions)

Assume that:

* the master is solved to global optimality over binary \(x\);
* all arithmetic and comparisons are exact;
* the separation oracle returns a true maximum-loss admissible matching for
  every integer incumbent; and
* a newly violated matching constraint is not added twice.

Then the procedure terminates after finitely many iterations and returns a
global optimum of the full epigraph formulation.

**Proof.** Every conditional constraint is valid for every binary \(x\) by
Theorem 1, so adding one cannot remove a feasible solution of the full
formulation. The restricted master is therefore a relaxation and its
objective is a lower bound on the full optimum.

If the oracle finds no violation at a master-optimal incumbent, that
incumbent satisfies every full epigraph constraint: for each task, the
oracle checked the maximum loss over all admissible matchings. It is therefore
feasible for the full formulation. Its objective is at least the full
optimum because it is a full-feasible solution, and at most the full optimum
because it is the optimum of a relaxation. Hence the values are equal and
the incumbent is globally optimal.

Otherwise, at least one new matching constraint is added. There are only
\(\sum_i|\mathcal M_i|\) possible matching constraints, so the process can
add only finitely many distinct constraints. Under the assumptions, it must
eventually reach the no-violation case. \(\square\)

This is a finite-exactness statement, not a polynomial-time result. It assumes
an exact master solver and an exact, potentially NP-hard separation oracle.
Practical performance depends on how many constraints are generated and on
the master solver's behavior.

The separation just described is an **integer-incumbent** oracle. It should
not be confused with separation over a fractional LP relaxation. If
\(x\in[0,1]^{|\mathcal E|}\), then \(\delta_i(P,x)\) is no longer a
zero-or-positive-integer admissibility indicator. Separating the finite
conditional-cut family at a fractional point would require maximizing

\[
L_i(P)-U_i\delta_i(P,x)-z_i
\]

over all full-graph matchings \(P\), which is a different weighted problem
and need not return a matching maximal under any integral selected set. The
integer oracle therefore does not automatically provide a fractional
separation oracle or a strong LP relaxation.

## 5. Why unconditional scenario cuts are invalid

Consider one task with two disjoint candidate edges

\[
e=\{u,v\},\qquad f=\{w,t\}.
\]

Let \(\alpha_i=0\), \(b_{e,i}=10\), and \(b_{f,i}=-10\). The matching
\(P=\{e\}\) is maximal when \(M_1=\{e\}\), because no other selected edge
can be added. It has loss

\[
L_i(P)=|10|=10.
\]

Now select \(M_2=\{e,f\}\). The only maximal matching of the selected graph
is \(\{e,f\}\), with loss

\[
|10-10|=0.
\]

Thus the universal scenario inequality \(z_i\geq L_i(P)=10\) would
incorrectly rule out the valid selected configuration \(M_2\), whose true
pessimistic loss is zero. The matching \(P\) is a legal scheme at \(M_1\) but
not at \(M_2\).

Here \(D_i(P)=\{f\}\). With \(x(M_1)\), \(\delta_i(P,x)=0\), while with
\(x(M_2)\), \(\delta_i(P,x)=1\). The valid conditional constraint uses
\(U_i=|0|+|10|+|-10|=20\):

\[
z_i\geq10-20\delta_i(P,x).
\]

It enforces \(z_i\geq10\) at \(M_1\), but becomes \(z_i\geq-10\), hence is
inactive under \(z_i\geq0\), at \(M_2\). This example is the minimal
manifestation of the nonmonotonicity of maximal-matching admissibility:
adding a resource can remove a previously admissible complete scheme.

## 6. Relation to existing outer-selection baselines

The conditional formulation exploits a structure that a generic factor
representation does not expose directly: for a fixed full-graph matching
\(P\), the selected sets for which it is admissible are described by
\(P\subseteq M\) and \(M\cap D_i(P)=\varnothing\). It does not eliminate the
inner worst-case computation.

* **Exhaustive outer enumeration.** Enumerate every budget-feasible \(M\),
  compute each \(W_i(M\cap\mathcal E_i)\), and retain the best set. This is
  the simplest reference method. Conditional constraints replace repeated
  evaluation by a growing master, but may still generate nearly all matching
  scenarios.
* **Full task factor tables.** Precompute \(W_i(S)\) for every
  \(S\subseteq\mathcal E_i\), then solve the resulting finite outer factor
  problem. This has explicit local tables; the conditional model has
  explicit matching scenarios instead. Neither representation is uniformly
  smaller.
* **Component frontiers.** Incidence components decompose objective and
  additive maintenance cost, after which local subsets can be reduced to
  nondominated cost--loss pairs and combined by a budget DP. Conditional cuts
  can be generated independently within a component, but the common budget
  still couples components.
* **Primal tree-decomposition DP.** Task scopes are cliques in the candidate
  primal graph. The conditional constraint for a matching \(P\) mentions
  \(P\cup D_i(P)\subseteq\mathcal E_i\), so its variable scope is still local
  to task \(i\); however, the number of such constraints can be exponential.
  Treewidth controls the assignment state size, not the number or generation
  cost of matching constraints.
* **Direct bilevel min--max optimization.** One may keep the adversarial
  matching as an inner optimization problem. This is conceptually direct,
  but a single-level exact reformulation requires either the finite
  matching-indexed epigraph, valid cuts, or additional structure for
  dualization. A model in which the outer optimizer also chooses the
  matching would solve the wrong, optimistic problem.

The conditional representation is therefore a candidate exact solution
framework, not an automatic replacement for exhaustive enumeration, frontiers,
or treewidth methods. Its most concrete benefit is a correct globally valid
cut indexed by a matching whose legality is conditional on the master
selection.

## 7. A compact adversarial-matching representation

For a fixed task \(i\), introduce binary variables \(y_{i,e}\) for the
matching used by the adversary. For every candidate \(e\), impose

\[
y_{i,e}\leq x_e.
\]

For every attribute vertex \(v\), impose the matching constraints

\[
\sum_{e\ni v}y_{i,e}\leq1.
\]

Finally, for every candidate edge \(e=\{u,v\}\), impose

\[
x_e\leq
\sum_{f\ni u}y_{i,f}
+\sum_{f\ni v}y_{i,f}.
\]

The \(y\) variables must be binary. The last inequality is required only for
selected edges, because it is vacuous when \(x_e=0\).

### Proposition 3 (compact characterization for fixed binary \(x\))

For a fixed binary \(x\), a binary vector \(y_i\) satisfies these constraints
if and only if its support is a maximal matching of \(H_i[M]\).

**Proof.** The inequalities \(y_{i,e}\leq x_e\) make every used edge
available. The vertex inequalities make the support a matching. If \(x_e=1\),
the last inequality says that at least one endpoint of \(e\) is incident to a
used matching edge. Hence every available edge conflicts with the current
matching, so the matching is maximal.

Conversely, let the support be a maximal matching of \(H_i[M]\). It uses only
selected edges and satisfies the vertex constraints. If a selected edge
\(e=\{u,v\}\) had no used matching edge at either endpoint, it could be added,
contradicting maximality. Therefore its last inequality also holds. \(\square\)

This is a compact description of the feasible adversarial matching set for a
fixed \(x\), with a number of variables and constraints polynomial in the
task graph. It does not by itself give a compact single-level formulation of
the outer min--max problem. The adversary must maximize

\[
\left|\alpha_i+\sum_{e\in\mathcal E_i}b_{e,i}y_{i,e}\right|
\]

over this \(x\)-dependent binary set, while the outer problem must enforce
that \(z_i\) dominates the value of that maximization. If \(y\) is placed in
the same minimization model, the outer optimizer can choose a favorable
matching rather than the worst one. If \(y\) is left in a separate
maximization, the model remains bilevel. A direct compact formulation would
need a valid reformulation or separation method for this discrete
decision-dependent inner problem; the compact feasibility description alone
does not supply one.

## 8. Literature and epistemic status

Minimum Maximal Matching and its relation to edge domination are established
graph-complexity results. Yannakakis and Gavril proved NP-completeness of
the minimum maximal matching problem as a corollary of their edge-dominating
set result [1]. The conditional formulation above is a derivation from the
definition of maximality; it is not a new hardness theorem.

The dependence of an admissible scenario family on a decision is related to
decision-dependent uncertainty in robust optimization. Nohadani and Sharma
study robust optimization with uncertainty sets affected by decisions and
show that general forms can be computationally difficult [2]. PESS-ESS is a
finite combinatorial specialization with a particular matching-based
admissibility rule; it should not be identified with that broader literature
without specifying the mapping of scenarios, losses, and decisions.

The iterative master--separation process is also closely related in spirit
to logic-based Benders decomposition and branch-and-check. Hooker presents
logic-based Benders as a framework in which subproblems can be discrete or
otherwise non-LP and problem-specific inference yields master cuts [3].
Here, the matching-indexed inequality is directly proved valid for binary
resource selections, and Theorem 2 gives finite exactness under an exact
integer master and exact separation. This establishes a PESS-ESS
specialization, not a new general decomposition paradigm.

The following qualifications are important:

* A finite exponential formulation is not automatically smaller or faster
  than a local factor table.
* Integer-incumbent separation does not imply fractional LP separation.
* A compact adversarial-feasibility model does not remove the adversarial
  quantifier.
* The mathematical admissible family need not equal the set of schemes
  realizable by a concrete DBMS. Any empirical policy claim requires separate
  validation.

## 9. Prioritized unresolved questions

1. Can the exact matching separation oracle exploit repeated task graphs or
   repeated coefficient patterns across nearby resource selections, rather
   than solving each maximal-matching problem independently?
2. Can conditional cuts be strengthened while remaining valid for all binary
   selections, for example by using partial matching structure without
   enumerating every full matching?
3. Which graph parameters make the integer separation problem tractable, and
   can those parameters be combined with primal separators or component
   frontiers?
4. Can the compact \(y\)-representation support useful relaxations whose
   integrality gap is controlled, without confusing a fractional adversary
   with an admissible integer matching?
5. How should conditional generation be integrated with additive-budget
   decomposition when maintenance costs are rational or continuous?

These questions concern exact or approximate optimization of the prescribed
two-column model. They do not introduce creation order or DBMS policy as an
advisor decision variable.

## References

1. M. Yannakakis and F. Gavril. “Edge Dominating Sets in Graphs.” *SIAM
   Journal on Applied Mathematics*, 38(3):364--372, 1980.
   [DOI](https://doi.org/10.1137/0138030).
2. O. Nohadani and K. Sharma. “Optimization under Decision-Dependent
   Uncertainty.” *SIAM Journal on Optimization*, DOI
   [10.1137/17M1110560](https://doi.org/10.1137/17M1110560).
3. J. N. Hooker. “Logic-Based Benders Decomposition.” In *Logic-Based
   Methods for Optimization*, 2000, Chapter 19.
   [DOI](https://doi.org/10.1002/9781118033036.ch19).

The prior PESS-ESS structural notes provide the vertex-subset inner
evaluation method, component-frontier decomposition, and treewidth
background used here. The references above identify related established
optimization frameworks; no publication-novelty claim is made.
