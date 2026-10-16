# Structured Outer Selection under Additive Maintenance Budgets

This note studies the global resource-selection layer of PESS-ESS under an
additive maintenance budget. It is separate from the generic
maintenance-set-function formulation in paper/main.tex and from the inner
maximal-matching results in notes/structural-foundations.md. Additivity is a
restriction of the concrete instance, not a property of the generic problem.

Throughout, \(\bar m_e\) denotes an additive maintenance coefficient; it is
not a statistics-creation cost. In the knapsack reduction below, \(c_i\) is
only shorthand for the maintenance coefficient of item \(i\).

## 1. Structured instance and three graph views

For each estimation task \(i\in\mathcal I\), let \(H_i=(V_i,\mathcal E_i)\) be its
eligible, edge-labeled candidate multigraph. Candidate identities are
resources in \(\mathcal E\), while the endpoints of an edge in \(H_i\) are
attributes. Parallel candidate edges are therefore allowed and remain
distinct. For \(S\subseteq\mathcal E_i\), define

\[
W_i(S)=
\max_{P\in\operatorname{MaximalMatchings}(H_i[S])}
\left|\alpha_i+\sum_{e\in P}b_{e,i}\right|.
\]

The advisor chooses one unordered global resource set \(M\subseteq\mathcal E\).
The structured additive instance is

\[
F(M)=\sum_{i\in\mathcal I}w_iW_i(M\cap\mathcal E_i),
\qquad
C(M)=\sum_{e\in M}\bar m_e,
\]

with \(w_i>0\), \(\bar m_e\geq0\), and \(C(M)\leq B\). The corresponding
general PESS-ESS model allows an arbitrary nonnegative set function
\(\operatorname{Maint}(M)\); hence \(C\) is an explicit specialization.

Three related graphs must be kept distinct:

* \(H_i\) is the task-local attribute graph. Its edges are eligible
  statistics, and conflicts arise when two edges share an attribute.
* The task--candidate incidence graph is
  \[
  G_{\mathrm{inc}}=(\mathcal I\cup\mathcal E,A),
  \qquad
  (i,e)\in A\iff e\in\mathcal E_i.
  \]
  Its vertices are tasks and candidate identities, not attributes.
* The candidate primal interaction graph is
  \[
  G_{\mathrm{primal}}=(\mathcal E,E_{\mathrm{primal}}),
  \]
  where distinct candidates \(e,f\) are adjacent when some task contains
  both: \(e,f\in\mathcal E_i\).

The first graph controls the inner matching abstraction. The second exposes
global task--resource connectivity. The third is the interaction graph of
the outer binary variables. In particular, a task with few attributes can
still have large \(|\mathcal E_i|\): distinct parallel candidate edges can
cover the same attribute pair.

## 2. Exact decomposition by incidence components

Let the connected components of \(G_{\mathrm{inc}}\) be indexed by
\(j=1,\ldots,q\). Write \(\mathcal I_j\) and \(\mathcal E_j\) for the task
and candidate vertices in component \(j\), and \(M_j=M\cap\mathcal E_j\).
Every task's eligible candidates lie in the same incidence component as that
task. Consequently, for \(i\in\mathcal I_j\),

\[
M\cap\mathcal E_i=M_j\cap\mathcal E_i.
\]

Define

\[
F_j(S)=\sum_{i\in\mathcal I_j}w_iW_i(S\cap\mathcal E_i),
\qquad
C_j(S)=\sum_{e\in S}\bar m_e.
\]

### Proposition 1 (component decomposition)

For every \(M\subseteq\mathcal E\),

\[
F(M)=\sum_{j=1}^qF_j(M_j),
\qquad
C(M)=\sum_{j=1}^qC_j(M_j).
\]

**Proof.** Partition the task sum by incidence components. The displayed
identity shows that the argument supplied to each \(W_i\) depends only on the
candidate set in the component containing \(i\), which gives the first
equality. Partitioning the additive candidate sum gives the second. \(\square\)

An isolated candidate has \(e\notin\mathcal E_i\) for every task and hence
does not affect \(F\). With \(\bar m_e\geq0\), removing it from any feasible
solution preserves the objective and does not increase cost. Thus an
optimal solution exists that contains no isolated candidate; if its cost is
positive, removing it strictly lowers the cost.

The proposition does **not** permit independent optimization of the
components. They share the single budget \(B\), so a component's selected
set competes for capacity with every other component.

## 3. Component cost--loss frontiers

For component \(j\), its finite attainable cost--loss pairs are

\[
\mathcal P_j=
\{(C_j(S),F_j(S)):S\subseteq\mathcal E_j\}.
\]

A pair \((c_1,f_1)\) dominates \((c_2,f_2)\) when

\[
c_1\leq c_2,\qquad f_1\leq f_2,
\]

and at least one inequality is strict.

### Proposition 2 (safe dominance pruning)

Removing dominated component configurations does not change the global
optimum under additive objective and additive maintenance cost.

**Proof.** Suppose a global solution uses \(S\subseteq\mathcal E_j\), and
there is \(S'\subseteq\mathcal E_j\) with
\(C_j(S')\leq C_j(S)\) and \(F_j(S')\leq F_j(S)\). Replace \(S\) by \(S'\),
leaving all other components unchanged. Proposition 1 shows that total cost
does not increase and total loss does not increase. Thus every solution
represented by a dominated pair has a no-worse representative represented by
the dominating pair. The optimum value is unchanged. The argument does not
assume that \(F_j\) is monotone in the selected set. \(\square\)

If several subsets realize the same retained pair, a deterministic witness
may be kept for reconstruction; pairwise dominance alone does not identify a
unique subset.

Define the component value function for a capacity \(b\geq0\) by

\[
g_j(b)=
\min_{\substack{S\subseteq\mathcal E_j\\C_j(S)\leq b}}F_j(S).
\]

The empty subset makes the feasible family nonempty. If \(b_1\leq b_2\), the
feasible family at \(b_1\) is contained in that at \(b_2\), so

\[
g_j(b_2)\leq g_j(b_1).
\]

This capacity monotonicity is different from set monotonicity: adding a
candidate to a particular \(S\) can increase, decrease, or leave unchanged
the pessimistic loss because maximal matchings can change.

The exact global composition is

\[
\min_{C(M)\leq B}F(M)
=
\min_{\substack{b_1,\ldots,b_q\geq0\\
                 \sum_jb_j\leq B}}
\sum_{j=1}^qg_j(b_j).
\]

The equality follows in both directions. A global \(M\) induces capacities
\(b_j=C_j(M_j)\), and Proposition 1 lower-bounds its component losses by
\(g_j(b_j)\). Conversely, for each selected allocation \(b_j\), a finite
component attains \(g_j(b_j)\), and the union of those component subsets is
feasible and attains the right-hand side.

For nonnegative integer maintenance coefficients and an integer budget, an
exact capacity-indexed dynamic program is

\[
D_0[0]=0,
\qquad D_0[b]=+\infty\quad(1\leq b\leq B),
\]

and, for \(j=1,\ldots,q\),

\[
D_j[b]=
\min_{0\leq t\leq b}
\left(D_{j-1}[b-t]+g_j(t)\right).
\]

The answer for an at-most budget is \(D_q[B]\); predecessor choices recover
the component capacities and corresponding subsets. Equivalently, the
transition may range over retained nondominated frontier states rather than
all capacities. If component \(j\) has \(K_j\) retained integer-cost states,
a straightforward implementation costs

\[
O\!\left(B\sum_{j=1}^qK_j\right)
\]

arithmetic transitions, plus frontier-generation time and reconstruction
storage. A coarse \(O(qB^2)\) bound results when every capacity is treated as
a possible component state.

Frontier generation is not free. Explicitly enumerating all local subsets
already costs \(2^{|\mathcal E_j|}\) evaluations in component \(j\). Moreover,
each \(F_j(S)\) contains the inner maximal-matching problem. The DP therefore
separates budget composition from local computation; it does not by itself
make either part polynomial.

For a fixed local graph, this inner computation is itself hard in general.
The decision problem Minimum Maximal Matching asks whether a graph has a
maximal matching with at most \(k\) edges. Yannakakis and Gavril proved this
problem NP-complete as a consequence of their edge-dominating-set result
[4]. To see its direct relation to \(W_i\), let \(m\) be the number of graph
edges, set \(b_e=1\) for every edge, and set \(\alpha=-m\). Then

\[
\max_{P\ {\rm maximal}}|-m+|P||
=m-\min_{P\ {\rm maximal}}|P|.
\]

Thus even one local factor can encode Minimum Maximal Matching. This is a
prior graph-complexity result, not a new PESS-ESS hardness theorem.

## 4. Outer knapsack hardness in a degenerate matching structure

The following reduction isolates global selection hardness without any
matching ambiguity.

### Proposition 3 (weak NP-hardness)

Consider PESS-ESS instances with integer maintenance costs and directly
encoded integer log-coefficients. The outer optimization is weakly NP-hard
even when every task has one candidate, every task has a unique maximal
matching for every selected set, and the incidence graph is a disjoint union
of isolated task--candidate edges.

**Proof.** Start with a 0--1 Knapsack instance with positive integer costs
\(c_1,\ldots,c_n\), positive integer profits \(v_1,\ldots,v_n\), capacity
\(B\), and, for the decision form, target profit \(P\). Construct one task
\(i\) and one candidate \(e_i\) per item. The task graph \(H_i\) has one edge
\(e_i\), and no candidate occurs in another task. Set

\[
w_i=1,\qquad
\alpha_i=-v_i,\qquad
b_{e_i,i}=v_i,\qquad
\bar m_{e_i}=c_i.
\]

If \(e_i\notin M\), the induced graph is edgeless and its unique maximal
matching is empty, so \(W_i(M)=|-v_i|=v_i\). If \(e_i\in M\), its unique
maximal matching is \(\{e_i\}\), so \(W_i(M)=|-v_i+v_i|=0\). With
\(x_i=\mathbf1[e_i\in M]\), the objective is therefore

\[
\sum_i v_i(1-x_i)
=\sum_i v_i-\sum_i v_ix_i.
\]

Minimizing it under \(\sum_i c_ix_i\leq B\) is exactly maximizing knapsack
profit. The knapsack yes-instance condition
\(\sum_i c_ix_i\leq B\) and \(\sum_i v_ix_i\geq P\) is equivalent to asking
whether the constructed PESS objective is at most \(\sum_i v_i-P\). The
construction is polynomial in the binary encoding of the integer inputs.
Since 0--1 Knapsack is weakly NP-complete, this gives a weak NP-hardness
reduction in the stated restricted class. \(\square\)

The reduction uses log-coefficients as native integer inputs. It does not
claim that arbitrary integer logs have polynomial-size exact rational
representations when encoded through \(r_e=\exp(b_e)\), nor does it claim a
hardness result for a physical PostgreSQL encoding. Its structural point is
that incidence treewidth one and unique local schemes do not remove the
global budget trade-off.

## 5. The candidate primal and factor structure

Let \(x_e=\mathbf1[e\in M]\). Define the task factor

\[
f_i(x_{\mathcal E_i})
=w_iW_i(\{e\in\mathcal E_i:x_e=1\}).
\]

Then

\[
F(M)=\sum_{i\in\mathcal I}f_i(x_{\mathcal E_i}).
\]

This is a binary finite-domain valued constraint-optimization, or factor-graph,
representation: candidates are binary variables and each task is a local
cost factor. The observation is a translation into a standard structural
language, not a new algorithmic result.

Every scope \(\mathcal E_i\) is a clique in \(G_{\mathrm{primal}}\), by
definition. The standard clique property of tree decompositions implies that
if \(G_{\mathrm{primal}}\) has treewidth \(\tau\), every scope is contained
in some bag and

\[
|\mathcal E_i|\leq\tau+1.
\]

This is a bound on candidate scope size, not on the number of task attributes
\(|V_i|\). If \(V_i\) is defined to contain only endpoints of eligible
candidate edges, then the pairwise model gives \(d_i=|V_i|\leq2|\mathcal
E_i|\). If \(V_i\) also includes isolated task attributes, even that bound
requires replacing \(d_i\) by the number of non-isolated vertices. In either
definition, the converse fails in the presence of parallel candidate edges.

## 6. Tree-decomposition dynamic programming

Assume for this section that maintenance coefficients and \(B\) are
nonnegative integers, local factors can be evaluated exactly, and a tree
decomposition of \(G_{\mathrm{primal}}\) of width \(\tau\) is supplied. A
standard nice-tree-decomposition DP stores, for each bag \(X\), a binary
assignment to candidates in \(X\), together with an accumulated capacity and
the minimum accumulated loss for the processed subtree.

Each candidate cost is charged once, at a designated introduce node. Each
factor \(f_i\) is assigned once to a bag containing its complete scope; such a
bag exists because the scope is a clique. It is evaluated only at that bag,
so no task factor is double-counted. Constant factors for empty scopes can be
assigned to the root.

Introduce and forget transitions extend or project bag assignments. At a join
node, the two child subtrees have disjoint assigned costs and factors; for a
fixed shared bag assignment their tables combine by budget convolution, for
example

\[
DP_X[a,b]=
\min_{b_1+b_2\leq b}
\bigl(DP_{X_1}[a,b_1]+DP_{X_2}[a,b_2]\bigr),
\]

with any convention-specific shared-bag charge handled by the unique
introduce assignment. This makes the quadratic-in-\(B\) join cost explicit.

With all factor tables available, the resulting bound has the form

\[
2^{O(\tau)}\operatorname{poly}(|\mathcal E|,B,|\mathcal I|),
\]

arithmetic operations, where the polynomial may include \(B^2\) join
convolutions. Add the cost of constructing the decomposition if it is not
given, and add the time for producing factor tables. This is
pseudo-polynomial in a binary-encoded \(B\), not polynomial in the complete
input length. It is fixed-parameter in a parameterization that includes
\(\tau\) and the numeric capacity (or otherwise treats the capacity in unary),
but bounded \(\tau\) alone does not yield a polynomial-time guarantee for
arbitrary binary capacities.

This is the usual bounded-width dynamic-programming pattern for finite-domain
constraint optimization. Samer and Szeider study the parameterized
relationships among primal, dual, and incidence treewidth in CSPs [5], while
Carbonnel, Romero, and Živný analyze bounded-width phenomena for
general-valued CSPs [6]. Those results provide methodological context; the
bound here is the conditional PESS-ESS specialization above, including its
capacity and factor-evaluation qualifications.

For the maximal-matching factors, let

\[
r_i=|\mathcal E_i|,
\qquad d_i=|V_i|.
\]

The saturated-vertex-set method from the structural note evaluates one
\(W_i(S)\), for a fixed \(S\), by enumerating \(2^{d_i}\) saturated sets and
solving polynomial-time weighted perfect-matching subproblems for qualifying
induced graphs. With exactly encoded weights of bit length \(L\), this gives
a bound of the form

\[
2^{d_i}\operatorname{poly}(d_i,r_i,L)
\]

per \(S\), assuming a standard polynomial-time general-graph weighted
matching routine. Tabulating the complete task factor for all
\(S\subseteq\mathcal E_i\) therefore costs at most

\[
2^{r_i+d_i}\operatorname{poly}(r_i,d_i,L).
\]

This is an explicit preprocessing upper bound, not a claim that it is
practical for large scopes. It is fixed-parameter in \(r_i+d_i\) for the
factor-generation part, but exact arithmetic and the global budget remain
separate issues. The polynomial solvability of weighted matching and
minimum-weight perfect matching in general graphs is classical; see Edmonds
and the matching survey by Cook, Cunningham, Pulleyblank, and Schrijver
[2,3].

## 7. Structural parameters and what they do not imply

The main parameters have different algorithmic roles.

| Parameter | Supports | Insufficient by itself |
|---|---|---|
| \(d=\max_i|V_i|\) | Vertex-subset methods for a single inner matching factor. | It does not bound \(r_i=|\mathcal E_i|\) when parallel candidates are allowed. |
| \(r=\max_i|\mathcal E_i|\) | Factor scopes and explicit local tables; it bounds the number of candidate-edge endpoints, but not necessarily all task attributes. | It does not remove global knapsack hardness: Proposition 3 has \(r=1\). |
| Maximum incidence degree of a candidate | Limits the number of task factors touching one variable. | Degree one already occurs in Proposition 3 and remains weakly NP-hard. |
| Incidence-component size | Enables local enumeration and component frontiers. | A large component may contain both hard inner problems and the full outer trade-off. |
| Primal treewidth \(\tau\) | Enables factor-scope tree DP with binary states per bag. | It leaves the binary-capacity dependence and factor-generation cost. |
| Incidence treewidth | Can support CSP-style decompositions of the bipartite relation. | It is not interchangeable with primal treewidth; a single task adjacent to many candidates is an incidence star of treewidth one but induces a large primal clique. |
| Integer capacity \(B\) | Enables exact capacity-indexed DP and pseudo-polynomial budget composition. | A binary-encoded numeric capacity can be exponentially larger than its input length. |

For every task, its candidate scope is a clique in the primal graph, so
primal width gives the exact bound \(r_i\leq\tau+1\). There is no converse
without additional restrictions: the incidence star example has width one
on the incidence side and unbounded primal clique size. Bounded task arity
can limit this star's degree, but it still does not identify the two width
measures or eliminate the global budget constraint. The number of attribute
vertices is a separate parameter whenever \(V_i\) contains isolated
attributes.

The factorization also clarifies why task--candidate incidence and primal
treewidth answer different questions. Incidence components determine exact
separability of local objective and additive cost. The primal graph controls
the scopes available to a variable-elimination or tree-decomposition method.
Neither graph alone captures all of the inner maximal-matching computation.

## 8. Numerical encoding and complexity status

The integer-budget recurrence is exact when costs and capacity are integer
inputs. Its dependence on the numeric value \(B\) makes it
pseudo-polynomial under binary encoding. It is therefore appropriate to
describe such a method as a capacity DP, not simply as a polynomial-time
algorithm.

For rational costs, multiplying by a common denominator gives an integer
instance, but the resulting capacity can be much larger than \(B\), and the
denominator's bit length affects the transformed instance. For floating-point
costs, exact integer indexing is not defined without choosing a numerical
representation and a scaling rule. Discretizing costs or the budget creates
an approximation problem; an error bound would require additional assumptions
and is not supplied here.

The generic PESS-ESS interfaces are black boxes, so no general complexity
classification follows from their definitions alone. The results above are
conditional on finite explicit factors, finite exact numerical encodings, and
the stated pairwise maximal-matching structure. In particular, additive
maintenance does not imply monotonicity, submodularity, or an easy frontier;
the one-edge reduction already produces ordinary knapsack behavior.

## 9. Proven statements, baselines, and open questions

### Proven or verified statements

* Incidence components decompose both the objective and additive maintenance
  cost, but the common budget couples their choices.
* Component configurations dominated in both cost and loss can be removed
  without changing the optimum, and each component value function is
  nonincreasing in its capacity.
* Integer-capacity component composition has the stated exact DP recurrence;
  its dependence on \(B\) is pseudo-polynomial under binary encoding.
* The restricted one-candidate-per-task construction is a polynomial
  reduction from 0--1 Knapsack and establishes weak NP-hardness of outer
  selection in that class.
* Every task scope is a clique in the candidate primal graph, so primal
  treewidth \(\tau\) bounds its size by \(\tau+1\). Incidence treewidth does
  not provide the same bound.
* For a supplied primal tree decomposition, binary-scope dynamic programming
  gives the stated \(2^{O(\tau)}\) dependence, subject to numeric-capacity and
  local-factor qualifications.

These are statements about the mathematical model. They do not establish
that a particular DBMS realizes every modeled maximal matching or that the
model predicts its numerical estimates.

### Algorithmic baselines

The following are defensible exact baselines under explicit restrictions:

1. Enumerate each component's subsets, compute \(F_j\), prune dominated
   pairs, and compose retained frontiers with the integer-capacity DP.
2. Precompute each task factor by the saturated-vertex-set method, using
   weighted perfect matching as the polynomial subroutine for each qualifying
   induced vertex set, then solve the outer binary factor problem by a primal
   tree-decomposition DP when primal width and capacity are manageable.
3. Use direct exhaustive enumeration for small components or candidate
   universes as a correctness reference for either baseline.

These are combinations of standard knapsack, matching, factor-graph, and
tree-decomposition techniques; no new algorithmic guarantee is claimed here.

### Open research opportunities

The specific gap is between generic weighted-constraint optimization, which
treats each task factor as an oracle or table, and the special maximal-matching
factors, whose values have additional graph structure but can still require
exponential local preprocessing. Priority questions are:

1. Can maximum- and minimum-weight maximal-matching evaluations be reused
   across related subsets \(S\), avoiding a complete factor table?
2. Which combinations of \(r_i\), \(d_i\), primal separators, component size,
   and budget representation yield practical exact algorithms beyond plain
   subset enumeration?
3. Can global budget composition be handled directly in a compact frontier or
   separator representation when \(B\) is large or real-valued?
4. Are there useful restrictions on the log-coefficients under which the
   outer objective becomes monotone, submodular, or otherwise tractable?
5. Which decomposition results survive when admissible schemes are ordered,
   partially covering, or otherwise more general than pairwise matchings?

Any answer to the last question must preserve the separation between a
prescribed admissibility model and the unknown scheme family of an actual
DBMS. It should not silently turn creation order or internal priority into
an advisor decision variable.

## References

1. M. R. Garey and D. S. Johnson. *Computers and Intractability: A Guide to
   the Theory of NP-Completeness*. W. H. Freeman, 1979.
   [Bibliographic record](https://dblp.org/rec/books/fm/GareyJ79).
2. J. Edmonds. “Paths, Trees, and Flowers.” *Canadian Journal of
   Mathematics*, 17:449--467, 1965.
   [DOI](https://doi.org/10.4153/CJM-1965-045-4).
3. W. J. Cook, W. H. Cunningham, W. R. Pulleyblank, and A. Schrijver.
   “Optimal Matchings.” In *Combinatorial Optimization*, 1997, pp. 127--198.
   [DOI](https://doi.org/10.1002/9781118033142.ch5).
4. M. Yannakakis and F. Gavril. “Edge Dominating Sets in Graphs.” *SIAM
   Journal on Applied Mathematics*, 38(3):364--372, 1980.
   [DOI](https://doi.org/10.1137/0138030).
5. M. Samer and S. Szeider. “Constraint Satisfaction with Bounded Treewidth
   Revisited.” *Journal of Computer and System Sciences*, 76(2):103--114,
   2010. [DOI](https://doi.org/10.1016/j.jcss.2009.04.003).
6. C. Carbonnel, M. Romero, and S. Živný. “The Complexity of General-Valued
   Constraint Satisfaction Problems Seen from the Other Side.” *SIAM Journal
   on Computing*, 51(1):19--69, 2022.
   [DOI](https://doi.org/10.1137/19M1250121).

The CSP and valued-CSP references provide context for primal/incidence width
and local-factor optimization. They do not by themselves establish a
PESS-ESS-specific algorithm or complexity classification.
