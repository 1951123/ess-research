# Structural and Complexity Foundations of PESS-ESS

This note studies structural properties of the budgeted pessimistic
extended-statistics selection problem (PESS-ESS).  It separates facts about
the abstract admissibility interface from facts about the pairwise
maximal-matching instantiation.  The note does not claim that the abstract
admissibility sets describe every scheme realizable by a DBMS, and it does
not introduce creation order as an advisor decision.

Throughout, let \(\mathcal I\) be a finite nonempty set of cardinality-
estimation tasks, \(\mathcal E\) a finite candidate-resource universe, and
\(w_i>0\) a task weight.  The advisor chooses one unordered resource set
\(M\subseteq\mathcal E\), subject to the abstract maintenance constraint
\[
  \operatorname{Maint}(M)\leq B,
  \qquad \operatorname{Maint}(\varnothing)=0,
  \qquad B\geq 0.
\]
For each task, \(\Omega_i\) is a finite scheme universe,
\(\Gamma_i(M)\subseteq\Omega_i\) is nonempty, and
\(\operatorname{used}(\sigma)\subseteq M\) for every
\(\sigma\in\Gamma_i(M)\).  The loss \(\ell_i(\sigma)\) is nonnegative.
The objective is
\[
  F_\Gamma(M)=
  \sum_{i\in\mathcal I}w_i
  \max_{\sigma\in\Gamma_i(M)}\ell_i(\sigma).
\]
Because the generic interfaces may be supplied as black boxes, no generic
complexity classification follows without specifying how admissible schemes,
maintenance feasibility, and losses are represented and evaluated.  The
complexity statements below therefore concern explicit, finite
representations of the stated special cases.

## 1. Admissibility as a prescribed model

The mapping \(\Gamma_i\) is a prescribed mathematical model of which
complete estimation schemes are admissible after creating \(M\).  It is not,
without further evidence, the exact set of schemes that a particular DBMS
can realize.  To express this distinction, let
\[
  \mathcal R_i(M)
\]
denote the unknown set of schemes realizable by the actual DBMS under the
relevant implementation states.  None of the following containments is
automatic:
\[
  \Gamma_i(M)=\mathcal R_i(M),\qquad
  \mathcal R_i(M)\subseteq\Gamma_i(M),\qquad
  \Gamma_i(M)\subseteq\mathcal R_i(M).
\]
Each requires a separate semantic or empirical justification.

Consequently, three claims must be distinguished:

1. A **model-internal claim** is a statement about the optimization problem
   defined by \(\Gamma_i\), the estimator, the loss, and the maintenance
   function.
2. A **conditional DBMS claim** additionally assumes that the realized DBMS
   scheme belongs to \(\Gamma_i(M)\) and that the modeled loss evaluates that
   scheme correctly.
3. An **adequacy claim** is empirical evidence that the chosen model agrees
   with observed DBMS behavior on a specified workload and environment.

The advisor decision remains only the resource set \(M\).  Creation order,
OID order, and a DBMS's internal priority policy are not additional advisor
decision variables in this formulation.

## 2. Why nonmonotone admissibility is necessary for nontriviality

### Proposition 1: nested admissibility makes the empty set optimal

Assume that for every task \(i\) and every pair of resource sets
\(M\subseteq M'\),
\[
  \Gamma_i(M)\subseteq\Gamma_i(M').
\]
Then
\[
  F_\Gamma(M)\leq F_\Gamma(M')
  \qquad\text{for all }M\subseteq M'.
\]
In particular, \(\varnothing\) is an optimal feasible solution of PESS-ESS.

**Proof.**  For each \(i\), maximizing a nonnegative function over a
subset cannot exceed maximizing it over the containing set.  Therefore,
\[
  \max_{\sigma\in\Gamma_i(M)}\ell_i(\sigma)
  \leq
  \max_{\sigma\in\Gamma_i(M')}\ell_i(\sigma).
\]
Multiplication by \(w_i>0\) and summation give the claimed inequality.
Moreover, \(\operatorname{Maint}(\varnothing)=0\leq B\), so the empty set
is feasible and has objective no larger than every other feasible set.  No
additivity, monotonicity, or submodularity assumption on
\(\operatorname{Maint}\) is used. \(\square\)

The result explains why the admissibility map must not be treated as
automatically nested.  In the pairwise instantiation, a matching that is
maximal after creating \(M\) can cease to be maximal after more compatible
edges are created.  Thus maximal-matching admissibility is naturally
nonmonotone.

### Proposition 2: a loss-independent characterization of possible improvement

Let
\[
  \mathcal C_B=
  \{M\subseteq\mathcal E:\operatorname{Maint}(M)\leq B\}
\]
be the feasible family.  Assume losses can be assigned freely and
independently as arbitrary maps
\(\ell_i:\Omega_i\to\mathbb R_{\geq0}\).  There exists a loss assignment
and a feasible set \(M\in\mathcal C_B\) with
\(F_\Gamma(M)<F_\Gamma(\varnothing)\) if and only if
\[
  \exists M\in\mathcal C_B,\;\exists i\in\mathcal I:qquad
  \Gamma_i(\varnothing)\nsubseteq\Gamma_i(M).
\]

**Proof.**  For sufficiency, choose a feasible \(M\) and task \(i\) with
\(\Gamma_i(\varnothing)\nsubseteq\Gamma_i(M)\).  Select
\(\sigma^\star\in\Gamma_i(\varnothing)\setminus\Gamma_i(M)\), assign
\(\ell_i(\sigma^\star)=1\), assign zero loss to every other scheme of
task \(i\), and assign zero loss to every scheme of every other task.  Then
the task-\(i\) maximum is 1 at \(\varnothing\) and 0 at \(M\), while all
other task contributions are zero.  Hence
\(F_\Gamma(M)=0<F_\Gamma(\varnothing)=w_i\).

For necessity, suppose instead that
\(\Gamma_i(\varnothing)\subseteq\Gamma_i(M)\) for every feasible \(M\)
and every task \(i\).  The subset-max inequality used in Proposition 1
then gives \(F_\Gamma(\varnothing)\leq F_\Gamma(M)\) for every feasible
\(M\), for every nonnegative loss assignment.  Strict improvement is
therefore impossible. \(\square\)

This is an existential theorem over freely chosen losses.  It does not say
that a fixed loss function improves whenever a baseline scheme disappears.
Under a fixed loss assignment, noncontainment is necessary for strict
improvement but need not be sufficient: the remaining admissible schemes
may have equal or larger loss.  The same qualification applies to the
fixed-factor multiplicative log-loss model.  Its coefficients restrict the
loss values, so Proposition 2 cannot be transferred as a sufficient
condition without an additional argument about those coefficients.

## 3. Maximal feasible schemes

A possible general construction starts with a family
\(\mathcal F_i(M)\) of feasible, potentially incomplete resource-use
configurations and defines
\[
  \Gamma_i(M)=\operatorname{Max}_{\subseteq}\mathcal F_i(M).
\]
This expression is well-defined when every configuration is represented as a
subset of a common ground set, or when an explicit partial order replacing
set inclusion is supplied.  If \(\mathcal F_i(M)\) is finite and nonempty,
maximal elements exist: repeatedly extend any nonmaximal element, which must
terminate in a finite partially ordered set.  Without nonemptiness or a
finite/appropriately well-founded order, maximal elements need not exist.

For the two-column instantiation, let \(H_i[M]\) be the edge-labeled graph
of created, structurally eligible candidates and set
\[
  \mathcal F_i(M)=\operatorname{Matchings}(H_i[M]).
\]
The configurations are edge sets ordered by inclusion, and therefore
\[
  \operatorname{Max}_{\subseteq}\mathcal F_i(M)
  =\operatorname{MaximalMatchings}(H_i[M]).
\]
This is the concrete relationship between feasible configurations and the
maximal-matching admissibility rule.  It also proves nonemptiness for every
finite \(H_i[M]\), including an edgeless graph, whose unique maximal
matching is empty.

The construction is not a general theorem about estimation schemes.  A
scheme may be an ordered sequence rather than a set; a statistic may cover
only a subset of its defined attributes; and partial predicate coverage may
carry information not represented by set inclusion.  Maximal feasible
schemes are therefore a research abstraction, not the unique or weakest
generalization of admissibility.

## 4. The inner two-column problem

For a fixed created set \(M\), write
\[
  \mathcal M_i(M)=\operatorname{MaximalMatchings}(H_i[M])
\]
and define
\[
  W_i(M)=
  \max_{P\in\mathcal M_i(M)}
  \left|\alpha_i+\sum_{e\in P}b_{e,i}\right|.
\]
Let
\[
  L_i^{\max}(M)=
  \max_{P\in\mathcal M_i(M)}\sum_{e\in P}b_{e,i},
  \qquad
  L_i^{\min}(M)=
  \min_{P\in\mathcal M_i(M)}\sum_{e\in P}b_{e,i}.
\]
The sums may contain negative log-coefficients.

### Proposition 3: endpoint identity

For every finite nonempty \(\mathcal M_i(M)\),
\[
  W_i(M)=
  \max\left\{
    \alpha_i+L_i^{\max}(M),
    -\alpha_i-L_i^{\min}(M)
  \right\}.
\]

**Proof.**  For any real number \(x\),
\( |x|=\max\{x,-x\}\).  Therefore,
\[
\begin{aligned}
W_i(M)
&=\max_{P\in\mathcal M_i(M)}
  \max\left\{
    \alpha_i+\sum_{e\in P}b_{e,i},
    -\alpha_i-\sum_{e\in P}b_{e,i}
  \right\}\\
&=\max\left\{
  \alpha_i+\max_{P\in\mathcal M_i(M)}\sum_{e\in P}b_{e,i},
  -\alpha_i-\min_{P\in\mathcal M_i(M)}\sum_{e\in P}b_{e,i}
  \right\},
\end{aligned}
\]
which is the stated identity.  No sign restriction on any \(b_{e,i}\) is
used. \(\square\)

Thus, for a fixed \(M\), evaluating the pessimistic loss reduces to two
weighted maximal-matching extremum problems: a maximum-weight maximal
matching and a minimum-weight maximal matching.  These are not maximum- or
minimum-cardinality matching problems.  They are also not ordinary
maximum-weight matching, because maximality is required and cardinality is
not optimized unless the weights happen to encode it.

### Known result: the inner problem is hard in general

Consider the decision problem **Minimum Maximal Matching**: given a graph
\(G=(V,E)\) and integer \(k\), does \(G\) have a maximal matching with at
most \(k\) edges?  Yannakakis and Gavril proved this problem NP-complete as
a corollary of their NP-completeness result for edge dominating sets, even
for restricted graph classes; this is prior work, not a new PESS-ESS result
[1].

The reduction to the inner objective is direct.  Let \(m=|E|\), assume
\(m\geq1\), set all edges available, choose \(b_e=1\) for every edge, and
set \(\alpha=-m\).  Every maximal matching \(P\) satisfies \(|P|\leq m\),
so
\[
  \max_{P\text{ maximal}}|-m+|P||
  =m-\min_{P\text{ maximal}}|P|.
\]
For the threshold \(K=m-k\),
\[
  W\geq K
  \quad\Longleftrightarrow\quad
  \min_{P\text{ maximal}}|P|\leq k.
\]
The certificate is a maximal matching, whose matching and maximality can be
checked in polynomial time.  Hence the threshold version of this restricted
inner problem is NP-complete, and exact inner evaluation is NP-hard.  The
reduction uses simple graphs, so allowing labeled parallel edges does not
weaken the conclusion.

## 5. Outer selection remains difficult without matching uncertainty

The outer problem has a separate source of difficulty.  Consider a single
task and a candidate graph consisting of pairwise vertex-disjoint edges.
For every selected set \(M\), the selected graph has one maximal matching,
namely all edges in \(M\).  Consequently,
\[
  F(M)=\left|\alpha+\sum_{e\in M}b_e\right|.
\]

### Proposition 4: a coefficient-encoded weak NP-hardness result

Consider the abstract raw-loss input representation in which the integer
log-coefficients \(\alpha\) and \(b_e\) are part of the instance.  The
decision problem of whether the optimum is zero is NP-hard, even when every
configuration has a unique admissible scheme and
\(\operatorname{Maint}(M)=0\) for all \(M\).

**Proof.**  Given a binary-encoded SUBSET SUM instance with positive integers
\(a_1,\ldots,a_n\) and target \(T\), create one pairwise disjoint candidate
edge \(e_j\) for each item.  Set
\[
  \alpha=-T,\qquad b_{e_j}=a_j,
  \qquad \operatorname{Maint}(M)=0,
  \qquad B=0.
\]
All candidate sets are feasible and have the unique maximal matching equal
to the selected set.  Therefore,
\[
  F(M)=0
  \quad\Longleftrightarrow\quad
  \sum_{e_j\in M}a_j=T.
\]
Thus an optimum of zero exists exactly when the SUBSET SUM instance is a yes
instance.  The zero-optimum decision is in NP under this direct integer
encoding, so this gives NP-completeness for that encoding and, in particular,
NP-hardness of outer selection.  Since the reduction is from SUBSET SUM, the
claim is the corresponding weak NP-hardness statement. \(\square\)

The representation qualification is essential.  If the input is instead
encoded by positive multipliers \(r_e\) with
\(b_e=\log r_e\), setting \(b_e=a_e\) requires
\(r_e=\exp(a_e)\).  A generic real exponential is not an exact finite
rational encoding, and choosing a base such as \(r_e=2^{a_e}\) can require
bit length proportional to the numeric value \(a_e\), not to its binary
encoding length.  Thus the reduction above does not silently establish the
same polynomial-time hardness claim for every multiplier representation.
It also says nothing by itself about physical PostgreSQL inputs, whose
coefficients are measured finite-precision quantities.  Stronger hardness
claims would require a different, representation-aware construction.

The result is nevertheless useful conceptually: even when estimator
uncertainty disappears because each selected configuration has one legal
scheme, resource selection can remain computationally difficult.

## 6. A vertex-subset characterization of maximal matchings

Let \(G=(V,E)\) be an undirected graph, with parallel edges distinguished
by their labels, and let \(P\) be a matching.  Let
\[
  S=\{v\in V:v\text{ is saturated by }P\}
\]
be the vertices covered by \(P\).

### Lemma 5

The matching \(P\) is maximal in \(G\) if and only if:

1. \(P\) is a perfect matching of the induced graph \(G[S]\); and
2. \(V\setminus S\) is an independent set in \(G\).

**Proof.**  Because \(P\) saturates exactly \(S\), every vertex of \(S\)
is incident to exactly one edge of \(P\), and every edge of \(P\) has both
endpoints in \(S\).  Thus \(P\) is a perfect matching of \(G[S]\).

If \(P\) is maximal and two vertices of \(V\setminus S\) were adjacent,
their edge could be added to \(P\), contradicting maximality.  Hence the
unmatched vertices are independent.

Conversely, suppose the two conditions hold.  Any edge that could be added
to \(P\) would have to have both endpoints unmatched, because every vertex
of \(S\) is already incident to an edge of the matching.  The second
condition rules out such an edge, so no edge can be added and \(P\) is
maximal. \(\square\)

The statement includes isolated vertices: an isolated unmatched vertex is
allowed in the independent set, while an isolated vertex cannot belong to a
perfectly matched \(S\).  For an empty graph, take \(S=\varnothing\); the
empty matching is the perfect matching of the empty induced graph and all
vertices are independent.  With parallel labeled edges, the vertex
condition is unchanged, while different labeled edges can give different
perfect matchings of the same induced vertex set.

### Exact inner evaluation by saturated vertex sets

Lemma 5 yields the following exact baseline procedure for a graph with
\(d=|V|\) vertices and \(m=|E|\) labeled edges:

1. Enumerate every \(S\subseteq V\).
2. Reject \(S\) unless \(V\setminus S\) is independent.
3. Reject \(S\) unless \(G[S]\) has a perfect matching.
4. Compute the minimum- and maximum-weight perfect matching values of
   \(G[S]\).
5. Take the minimum and maximum over all qualifying \(S\), then apply
   Proposition 3.

For exactly encoded integer or rational weights of total bit length \(L\),
independence tests, perfect-matching tests, and weighted perfect matching are
polynomial-time subroutines.  General-graph weighted perfect matching is a
classical polynomial-time result of Edmonds; standard treatments include
[2,3].  Consequently, a conservative bit-complexity bound for the procedure
has the form
\[
  O\!\left(2^d\operatorname{poly}(d,m,L)\right).
\]
The exponential factor is the enumeration of saturated vertex sets.  The
matching computations and exact arithmetic are polynomial in the graph size
and the numerical encoding length.  This is fixed-parameter tractability
with respect to \(d\), in the standard exact-input model.  It is not a
polynomial-time algorithm when \(d\) is part of the unrestricted input, and
it does not remove the outer enumeration or maintenance-constrained resource
selection problem.

## 7. Objective-function structure

The concrete objective has no unconditional monotonicity, submodularity, or
supermodularity guarantee.  The following examples use the disjoint-edge
specialization, so each selected set has a unique admissible scheme.  They
therefore isolate objective structure from matching ambiguity.

For two candidate edges \(a,b\), define the submodular cross-difference
\[
  \Delta_F=F(\{a\})+F(\{b\})-F(\varnothing)-F(\{a,b\}).
\]
Submodularity requires \(\Delta_F\geq0\); supermodularity requires
\(\Delta_F\leq0\) for this pair.

### Example 1: nonnegative coefficients do not imply submodularity

Take \(\alpha=-1\) and \(b_a=b_b=1\).  The complete table is
\[
\begin{array}{c|cccc}
M&\varnothing&\{a\}&\{b\}&\{a,b\}\\ \hline
F(M)&1&0&0&1
\end{array}
\]
Thus \(\Delta_F=0+0-1-1=-2<0\), violating submodularity.  Both log
coefficients are nonnegative.

### Example 2: signed coefficients can violate supermodularity

Take \(\alpha=0\), \(b_a=-5\), and \(b_b=1\).  Then
\[
\begin{array}{c|cccc}
M&\varnothing&\{a\}&\{b\}&\{a,b\}\\ \hline
F(M)&0&5&1&4
\end{array}
\]
Here \(\Delta_F=5+1-0-4=2>0\), violating supermodularity.  Together
with Example 1, this shows that arbitrary signed coefficients permit neither
property.

### Monotonicity and a restricted positive-coefficient observation

Even with nonnegative coefficients, the absolute value can first decrease
and then increase as the accumulated correction crosses zero.  For one edge,
\(\alpha=-1,b_a=1\) gives \(F(\varnothing)=1>0=F(\{a\})\), whereas
\(\alpha=0,b_a=1\) gives \(F(\varnothing)=0<1=F(\{a\})\).  Thus no fixed
monotone direction follows even in this restricted case.

There is, however, a limited structural fact.  If every \(b_e\geq0\), then
\(F(M)=g(\alpha+\sum_{e\in M}b_e)\) with \(g(x)=|x|\), and the convexity
of \(g\) implies increasing marginal differences.  Hence this disjoint-edge
specialization is supermodular, although it need not be monotone or
submodular.  If the argument of the absolute value has one fixed sign over
the domain under consideration, the function becomes affine in the selected
edge indicators and is both submodular and supermodular.  These restricted
observations do not extend automatically through maximal-matching
admissibility or to the full outer problem.

## 8. References and status of results

1. **Prior hardness result.** M. Yannakakis and F. Gavril, “Edge Dominating
   Sets in Graphs,” *SIAM Journal on Applied Mathematics*, 38(3), 1980,
   pp. 364--372.  The paper proves NP-completeness of edge dominating set
   and gives minimum maximal matching as a corollary.  [SIAM DOI]
   (https://doi.org/10.1137/0138030).
2. **General matching algorithm.** J. Edmonds, “Paths, Trees, and Flowers,”
   *Canadian Journal of Mathematics*, 17, 1965, pp. 449--467.
   [Cambridge DOI](https://doi.org/10.4153/CJM-1965-045-4).
3. W. J. Cook, W. H. Cunningham, W. R. Pulleyblank, and A. Schrijver,
   “Optimal Matchings,” in *Combinatorial Optimization*, 1997.
   [Publisher chapter](https://doi.org/10.1002/9781118033142.ch5).
4. M. R. Garey and D. S. Johnson, *Computers and Intractability: A Guide
   to the Theory of NP-Completeness*, W. H. Freeman, 1979.  [Bibliographic
   record](https://books.google.com/books/about/Computers_and_Intractability.html?id=fjxGAQAAIAAJ).

The following status distinctions are important:

- Propositions 1--4 and Lemma 5 are directly proved here, subject to their
  stated input representations.
- NP-completeness of Minimum Maximal Matching is established prior work, not
  a new result of this note.
- The \(O(2^d\operatorname{poly}(d,m,L))\) procedure is a derivable exact
  baseline using established matching subroutines; no novelty claim is made.
- The relationship between a concrete DBMS's realizable schemes
  \(\mathcal R_i(M)\) and a chosen \(\Gamma_i(M)\) remains an empirical and
  semantic modeling question.

## 9. Prioritized research agenda

### Established or directly provable facts

1. Nested admissibility makes the empty set optimal under the pessimistic
   max-loss objective.
2. Under freely assignable losses, loss-independent strict improvement is
   possible exactly when some feasible resource set removes a baseline
   admissible scheme for some task.
3. The two-column inner objective reduces to maximum- and minimum-weight
   maximal-matching extrema, and is NP-hard in general by the prior Minimum
   Maximal Matching result.
4. The saturated-vertex-set enumeration gives an exact algorithm that is
   fixed-parameter tractable in the number of graph vertices, with exact
   finite-precision weights.
5. Outer selection remains weakly NP-hard in a unique-scheme disjoint-edge
   subclass under direct coefficient encoding.

### Structural observations

1. Nonmonotone admissibility is not a minor implementation detail: without
   it, the empty-set optimum follows for every nonnegative loss assignment.
2. Inner estimator uncertainty and outer resource selection are distinct
   sources of difficulty.  The disjoint-edge reduction removes the former
   while retaining the latter.
3. Small task graphs can make the inner problem tractable even when the
   global candidate universe is large; this suggests parameterized analyses,
   but does not imply a practical algorithm for the outer problem.
4. The maximal-feasibility construction is useful for pairwise matchings but
   may be inadequate for sequence-valued schemes, partial coverage, or
   higher-arity resources.

### Open questions, in priority order

1. Can the inner problem be solved more effectively using graph parameters
   such as vertex count, treewidth, degree, or the number of maximal
   matchings, while preserving exact negative and positive log weights?
2. Can outer selection exploit small task graphs without enumerating all
   global resource configurations under an arbitrary maintenance function?
3. Which restrictions on coefficients, task graphs, or maintenance costs
   yield useful approximation or exact-selection structure without assuming
   monotonicity or submodularity?
4. What admissibility abstractions preserve meaningful scheme structure when
   resources have arity greater than two or schemes include order and partial
   predicate coverage?
5. Under what semantic and empirical conditions can a DBMS policy be shown to
   lie inside a modeled \(\Gamma_i(M)\), and how should policy coupling across
   tasks be represented without turning creation order into an advisor
   decision?

These questions concern the mathematical model and its justified scope;
they do not assert a new algorithm, a complexity classification beyond the
results stated above, or universal correspondence with PostgreSQL.
