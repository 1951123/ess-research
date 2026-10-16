# Strengthened Conditional Master and Certified Matching Oracle

This note develops an exact algorithmic framework for the two-column
maximal-matching instantiation of PESS-ESS. It strengthens the finite
conditional master, gives certified bounds for its inner adversarial
problem, and specifies an exact master--oracle procedure. The results are
about the stated mathematical model. They do not identify the admissible
schemes of an arbitrary database system and do not introduce creation order
or OID order as decision variables.

Throughout, task \(i\) has eligible edge-labeled multigraph
\(H_i=(V_i,\mathcal E_i)\), coefficients \(\alpha_i\) and \(b_{e,i}\), and
additive maintenance coefficients \(\bar m_e\). For a full-graph matching
\(P\), let
\[
L_i(P)=\left|\alpha_i+\sum_{e\in P}b_{e,i}\right|.
\]
For \(P\), define
\[
V(P)=\bigcup_{e\in P}A_e,\qquad
D_i(P)=\{f\in\mathcal E_i:A_f\cap V(P)=\varnothing\},
\]
and, for a binary resource vector \(x\),
\[
\delta_i(P,x)=
\sum_{e\in P}(1-x_e)+\sum_{f\in D_i(P)}x_f.
\]
The conditional-maximality characterization proved in the companion note is
\[
\delta_i(P,x)=0
\quad\Longleftrightarrow\quad
P\in\operatorname{MaximalMatchings}(H_i[M]),
\]
where \(M=\{e:x_e=1\}\).

## 1. Strengthened conditional master

Let
\[
U_i=|\alpha_i|+\sum_{e\in\mathcal E_i}|b_{e,i}|.
\]
Then \(0\leq L_i(P)\leq U_i\) for every matching \(P\). The usual conditional
epigraph inequality is
\[
z_i\geq L_i(P)-U_i\delta_i(P,x).
\]

### Proposition 1 (matching-specific coefficient)

For \(0\leq x\leq1\), \(\delta_i(P,x)\geq0\), and \(z_i\geq0\),
\[
z_i\geq L_i(P)(1-\delta_i(P,x))
\]
dominates the \(U_i\)-based inequality. For binary \(x\), it has exactly
the intended conditional meaning.

**Proof.** The difference between the two right-hand sides is
\[
L_i(P)(1-\delta_i(P,x))
-\bigl(L_i(P)-U_i\delta_i(P,x)\bigr)
=(U_i-L_i(P))\delta_i(P,x)\geq0.
\]
For binary \(x\), an admissible matching has \(\delta_i(P,x)=0\).
If it is inadmissible, the two nonnegative integer sums defining
\(\delta_i(P,x)\) imply \(\delta_i(P,x)\geq1\); hence
\(L_i(P)(1-\delta_i(P,x))\leq0\), which is redundant with
\(z_i\geq0\). Thus exactly the admissible matching losses remain active.
\(\square\)

### Proposition 2 (ordinary-matching floor)

Define ordinary matching extrema on the full graph:
\[
a_i^-=\min_{P\in\operatorname{Matchings}(H_i)}
\sum_{e\in P}b_{e,i},\qquad
a_i^+=\max_{P\in\operatorname{Matchings}(H_i)}
\sum_{e\in P}b_{e,i},
\]
and
\[
\lambda_i=
\max\{0,\alpha_i+a_i^-,-\alpha_i-a_i^+\}.
\]
Then, for every full-graph matching \(P\),
\[
\lambda_i\leq L_i(P),
\]
and, for every selected resource set \(M\),
\[
0\leq\lambda_i\leq W_i(M),
\qquad
W_i(M)=
\max_{P\in\operatorname{MaximalMatchings}(H_i[M])}L_i(P).
\]

**Proof.** Every matching sum \(s(P)=\sum_{e\in P}b_{e,i}\) lies in
\([a_i^-,a_i^+]\). Therefore every value
\(\alpha_i+s(P)\) lies in the interval
\[
I_i=[\alpha_i+a_i^-,\alpha_i+a_i^+].
\]
The minimum of \(|y|\) over this interval is its distance from zero:
\[
\operatorname{dist}(0,I_i)
=\max\{0,\alpha_i+a_i^-,-\alpha_i-a_i^+\}
=\lambda_i.
\]
Consequently \(|\alpha_i+s(P)|\geq\lambda_i\) for every matching \(P\).
Maximal matchings of \(H_i[M]\) are full-graph matchings, and the finite
selected graph always has at least one maximal matching. Taking their
maximum loss gives \(\lambda_i\leq W_i(M)\). \(\square\)

The two ordinary extrema are general-graph weighted matching problems. Signed
weights cause no difficulty: minimum weight can be obtained by negating the
weights in a maximum-weight formulation, and parallel labeled edges can be
handled by the corresponding multigraph matching algorithm or an equivalent
label-preserving encoding. For exactly encoded rational or integer weights,
the extrema are polynomial-time computable.

### Proposition 3 (floor-strengthened conditional master)

Consider, for every task and full-graph matching,
\[
\boxed{
\begin{aligned}
z_i&\geq\lambda_i,\\
z_i&\geq L_i(P)
-(L_i(P)-\lambda_i)\delta_i(P,x).
\end{aligned}}
\]
For binary \(x\), this system is equivalent to the exact pessimistic
epigraph. Over \(0\leq x\leq1\), with the common budget, binary-domain
constraints, and any other common master constraints, it dominates both the
original \(U_i\)-based system and the matching-specific system.

**Proof.** Proposition 2 gives \(L_i(P)-\lambda_i\geq0\). Hence
\[
L_i(P)-(L_i(P)-\lambda_i)\delta_i(P,x)
-L_i(P)(1-\delta_i(P,x))
=(L_i(P)-\lambda_i)\delta_i(P,x)\geq0.
\]
The floor \(z_i\geq\lambda_i\) also dominates \(z_i\geq0\), and Proposition
1 gives dominance over the \(U_i\)-based inequality. For binary \(x\), an
admissible \(P\) has \(\delta=0\), so its loss constraint is active. An
inadmissible \(P\) has \(\delta\geq1\), so its conditional right-hand side is
at most \(\lambda_i\) and is redundant with the floor. Thus the active
constraints are exactly the admissible maximal-matching constraints.
\(\square\)

If \(\lambda_i>0\), the floor is a strict strengthening of the system with
only \(z_i\geq0\) at the formulation level. If \(\lambda_i=0\), it adds no
floor strength. The coefficient \(L_i(P)-\lambda_i\) is the smallest
uniform deactivation coefficient if the only information about an
inadmissible binary pattern is \(\delta_i(P,x)\geq1\). A smaller coefficient
can be valid only after exploiting additional restrictions that rule out
patterns with \(\delta=1\). This strengthening does not make the LP
relaxation ideal.

At the individual-inequality level, the matching-specific cut is strictly
stronger than the \(U_i\)-cut exactly when
\((U_i-L_i(P))\delta_i(P,x)>0\). The floor-strengthened conditional cut is
strictly stronger than the matching-specific cut exactly when
\((L_i(P)-\lambda_i)\delta_i(P,x)>0\), and its unconditional floor is a
strict strengthening of \(z_i\geq0\) exactly when \(\lambda_i>0\). Whether
these strict inequalities produce a strict reduction of the whole feasible
region also depends on the other master constraints; those constraints may
already imply the stronger bound.

With additive maintenance, the complete strengthened binary master is
\[
\boxed{
\begin{aligned}
\min_{x,z}\quad&
\sum_{i\in\mathcal I}w_i z_i\\
\mathrm{s.t.}\quad&
\sum_{e\in\mathcal E}\bar m_e x_e\leq B,\\
&x_e\in\{0,1\}\quad(e\in\mathcal E),\\
&z_i\geq\lambda_i\quad(i\in\mathcal I),\\
&z_i\geq L_i(P)
-(L_i(P)-\lambda_i)\delta_i(P,x)\\
&\hspace{35mm}(i\in\mathcal I,\ P\in\operatorname{Matchings}(H_i)).
\end{aligned}}
\]
The matching-indexed system is finite, but the number of matchings can be
exponential.

## 2. Explicit continuous-relaxation gaps

The stronger coefficient and the floor address different weaknesses. They do
not by themselves make the continuous relaxation exact.

### Example 1: the floor removes a unit fractional gap

Take one task with two vertex-disjoint candidate edges \(e\) and \(f\),
\(\alpha=1\), \(b_e=b_f=0\), unit maintenance costs, and \(B=1\).
The full matchings are
\[
\varnothing,\quad\{e\},\quad\{f\},\quad\{e,f\},
\]
and every matching has loss \(L=1\). With an integer budget-feasible
selection, the selected graph has a nonempty maximal matching when one edge
is selected and the empty matching otherwise; in either case the
pessimistic loss is exactly \(1\). Thus the integer optimum is \(1\).

At \(x_e=x_f=\tfrac12\), each of the four full matchings has
\(\delta(P,x)=1\). For the empty matching this is
\(x_e+x_f\); for a singleton it is one missing-edge term plus the selected
disjoint edge; for the two-edge matching it is
\((1-x_e)+(1-x_f)\). Therefore the old and matching-specific inequalities
both permit \(z=0\):
\[
1-U\delta=0,\qquad 1(1-\delta)=0
\]
when \(U=1\). The ordinary extrema give
\(\lambda=1\), so the floor-strengthened relaxation requires \(z\geq1\)
and removes this particular gap.

### Example 2: a positive gap remains after floor strengthening

Use the same graph and budget, but set
\[
\alpha=-5,\qquad b_e=b_f=1.
\]
The losses of the four matchings are respectively \(5,4,4,3\), and
\(\lambda=3\). Every integer feasible selection has loss \(5\) when empty
and \(4\) when exactly one edge is selected, so the integer optimum is \(4\).
At \(x_e=x_f=\tfrac12\), every matching again has \(\delta=1\). The
floor-strengthened conditional right-hand side is \(3\) for every matching,
so \(z=3\) is feasible in the LP relaxation
\[
0\leq x_e,x_f\leq1,\qquad x_e+x_f\leq1,
\qquad\text{all floor-strengthened cuts}.
\]
The floor itself proves that this relaxation has value exactly \(3\), giving
a positive integrality gap \(4-3\). The example only shows that the floor
does not eliminate all gaps; it is not a bound on gaps in general.

## 3. Certified bounds for the inner adversary

For a fixed selected set \(M\), define ordinary matching extrema on the
selected graph:
\[
a_i^-(M)=\min_{P\in\operatorname{Matchings}(H_i[M])}
\sum_{e\in P}b_{e,i},
\qquad
a_i^+(M)=\max_{P\in\operatorname{Matchings}(H_i[M])}
\sum_{e\in P}b_{e,i}.
\]
Every maximal matching is an ordinary matching, so its weight lies in the
interval \([a_i^-(M),a_i^+(M)]\). Since \(y\mapsto|\alpha_i+y|\) is convex,
its maximum on an interval is attained at an endpoint. Hence
\[
\boxed{
W_i(M)\leq
\overline W_i(M)=
\max\{|\alpha_i+a_i^-(M)|,\,
      |\alpha_i+a_i^+(M)|\}.}
\]
This proof permits arbitrary signed coefficients and does not use
cardinality of a matching.

Conversely, for any maximal matching \(Q\) of \(H_i[M]\),
\[
L_i(Q)\leq W_i(M)
\]
by the definition of \(W_i(M)\). Thus a legal maximal matching is a
certified lower-bound witness. A practical certified evaluation sequence is:

1. Compute \(a_i^-(M)\) and \(a_i^+(M)\), giving the upper bound
   \(\overline W_i(M)\).
2. Obtain one or more legal maximal matching witnesses and take the
   largest observed loss as a lower bound.
3. If a witness loss equals \(\overline W_i(M)\) under exact arithmetic,
   certify \(W_i(M)\) without further search.
4. Otherwise invoke an exact worst-case maximal-matching oracle.

Any matching \(R\) can be converted into a legal maximal witness by repeatedly
adding an available selected edge disjoint from every edge currently in
\(R\), until no such edge remains. Finiteness guarantees termination, and
the result is maximal by construction. The extension is a valid witness,
not necessarily a worst-case matching: adding edges can either increase or
decrease a signed sum before the absolute value is taken.

The sequence is correct provided the ordinary matching routines are exact,
the witness construction checks the selected graph, equality tests use exact
input arithmetic, and the fallback oracle terminates and returns the true
maximum over maximal matchings. No claim is made that the cheap bounds will
usually coincide.

## 4. Sign-coherent polynomial cases

The mixed-sign case remains the general case. Two sign-coherent cases have
simple inner oracles.

### Case 1: nonnegative baseline and nonnegative corrections

Suppose
\[
\alpha_i\geq0,\qquad b_{e,i}\geq0\quad(e\in\mathcal E_i).
\]
Every matching loss is then
\[
L_i(P)=\alpha_i+\sum_{e\in P}b_{e,i}.
\]
Let \(R\) be a maximum-weight ordinary matching of \(H_i[M]\). Extend it
by adding disjoint selected edges until it is maximal. The extension cannot
decrease its weight, while no matching can exceed the ordinary maximum.
Consequently the extension has the same weight as \(R\), and
\[
\boxed{W_i(M)=\alpha_i+a_i^+(M).}
\]
If extension is needed, every added edge must have zero weight; a positive
added edge would contradict the optimality of \(R\). This accounts for
zero-weight edges.

### Case 2: nonpositive baseline and nonpositive corrections

Suppose
\[
\alpha_i\leq0,\qquad b_{e,i}\leq0\quad(e\in\mathcal E_i).
\]
Now
\[
L_i(P)=-\alpha_i-\sum_{e\in P}b_{e,i}.
\]
Extend a minimum-weight ordinary matching to a maximal matching. Adding
nonpositive edges cannot increase its weight, and ordinary optimality prevents
the extended matching from having smaller weight. The extension therefore
has the same weight, yielding
\[
\boxed{W_i(M)=-\alpha_i-a_i^-(M).}
\]
Again, any required added edges have zero weight.

In Case 1, \(a_i^+(M)\) is nondecreasing under resource inclusion. In Case 2,
\(a_i^-(M)\) is nonincreasing, so \(-a_i^-(M)\) is nondecreasing. Therefore
\(W_i(M)\) is nondecreasing in both cases. If every task satisfies one of
these two conditions, the total objective is nondecreasing under inclusion.
Because the empty set is feasible under a nonnegative maintenance budget, it
is globally optimal, possibly with ties. Thus a polynomial inner oracle under
sign coherence does not produce a nontrivial selection problem for this
minimize-worst-loss objective. Mixed signs are not covered by this argument.

## 5. Exact master--oracle procedure

The full conditional master can be solved by exact integer constraint
generation. Four quantities must be kept separate:

* The restricted-master objective is a lower bound on the global optimum,
  denoted \(LB_{\mathrm{master}}\).
* A fully evaluated feasible resource set gives an objective upper bound
  \(UB_{\mathrm{selection}}\).
* For a fixed incumbent \(M\), a legal witness loss, together with
  \(\lambda_i\), is a lower bound \(LB_i\) on task \(i\)'s \(W_i(M)\).
* The ordinary-matching endpoint value \(\overline W_i(M)\) is an upper
  bound \(UB_i\) on that task's \(W_i(M)\).

The exact master is initialized with the budget, binary \(x\), nonnegative
\(z\), the unconditional floors \(z_i\geq\lambda_i\), and any previously
generated conditional cuts. The following procedure is stated at the level
of exact mathematical oracles.

    repeat
        solve the current binary master exactly, obtaining (x_hat, z_hat)
        set M_hat = {e : x_hat_e = 1}
        violated = false
        for each task i:
            compute ordinary matching bounds and set UB_i
            initialize LB_i = lambda_i
            if z_hat_i >= UB_i:
                certify that no conditional matching cut is violated
                continue
            construct legal maximal witnesses and update LB_i
            if z_hat_i < LB_i:
                choose a witness Q with L_i(Q) > z_hat_i
                add its globally valid strengthened conditional cut
                violated = true
                continue
            if LB_i == UB_i:
                certify W_i(M_hat) = LB_i = UB_i
                continue
            invoke an exact worst-case maximal-matching oracle
            if W_i(M_hat) > z_hat_i:
                choose a worst-case matching P
                add its globally valid strengthened conditional cut
                violated = true
        if violated:
            continue
        independently record the fully evaluated value of M_hat
        return M_hat and the exact task losses

The branch \(z_i\geq UB_i\) is a certificate that no matching in the
currently selected graph can violate the task epigraph. A witness lower bound
alone is not such a certificate: if \(z_i\geq LB_i\), an unexamined matching
may still be worse. The exact fallback is required unless the lower and upper
bounds coincide or the upper bound already lies below the master value.

Each generated cut is valid for every binary resource selection by
Proposition 3. If a cut is violated at an incumbent, it was not already
present in an exact feasible master. If the loop terminates without a new
cut, the incumbent satisfies every full conditional constraint: each task
has \(z_i\geq W_i(M)\). The restricted master optimum is then a lower bound
on the full optimum, while the incumbent is a feasible full solution and
therefore an upper bound. Equality proves global optimality.

Termination is finite under exact master solves and terminating exact inner
oracles. Every nonterminal iteration adds at least one previously absent
matching cut, and the total number of possible cuts is
\[
\sum_{i\in\mathcal I}|\operatorname{Matchings}(H_i)|.
\]
This is a finite bound, not a polynomial-time bound. Duplicate cuts must be
identified so that a violated cut cannot be re-added indefinitely.

## 6. Fractional separation and algorithmic levels

The integer separation oracle above asks for the worst maximal matching of a
selected graph. It is not the same as separating the strengthened cuts at a
fractional master point. For \(0\leq x\leq1\), exact separation for task \(i\)
would maximize
\[
\max_{P\in\operatorname{Matchings}(H_i)}
\left[
L_i(P)
-(L_i(P)-\lambda_i)\delta_i(P,x)
-z_i
\right].
\]
Here \(\delta_i(P,x)\) is fractional, and a matching \(P\) need not be
maximal in any integral graph associated with \(x\). Therefore an integer
worst-maximal-matching oracle does not solve fractional separation.

The following levels should be distinguished:

* **Integer-incumbent generation:** exact and sufficient for the finite
  binary formulation when the fallback oracle is exact.
* **Root-node fractional separation:** a separate combinatorial optimization
  problem; exactness requires its own oracle.
* **Branch-and-check:** integer separation performed at branch-and-bound
  incumbents, with the usual need to preserve global cut validity.
* **Fully integrated branch-and-cut:** requires a verified fractional
  separator or another valid relaxation mechanism in addition to integer
  separation.

For small tasks, enumeration of all matchings gives an exact fractional
separator. For larger tasks, candidate matching generation, LP relaxations,
or heuristic separators can produce useful cuts, but without a proof they do
not certify the fractional closure or the global optimum by themselves.

The compact selected-matching representation
\[
y_{i,e}\in\{0,1\},\qquad
y_{i,e}\leq x_e,\qquad
\sum_{e\ni v}y_{i,e}\leq1\quad(v\in V_i),
\]
\[
x_e\leq
\sum_{f\ni u}y_{i,f}+\sum_{f\ni v}y_{i,f}
\qquad(e=\{u,v\}\in\mathcal E_i)
\]
does exactly characterize a maximal matching of \(H_i[M]\) for fixed binary
\(x\), assuming loop-free two-attribute edges. The first constraints make
\(y\) a matching contained in the selected graph. The last constraint says
that every selected edge has an endpoint incident to a selected matching edge;
therefore no selected edge can be added to \(y\). Conversely, a maximal
matching satisfies all three families. Parallel labels are retained by
having separate \(y_{i,e}\) variables.

This is a compact representation of feasible adversarial matchings, not a
compact single-level formulation of the maximum loss. The remaining
quantifier is the adversary's optimization over \(y\), and the outer problem
must still enforce its maximum for every selected \(x\). A bilinear or
disjunctive treatment of loss and selection would require additional valid
reformulation work.

## 7. Numerical representation and stability

The exact statements above assume finite, exactly represented coefficients.
Several numerical issues matter in an implementation:

* Large positive and negative coefficients can make
  \(\alpha_i+\sum b_{e,i}\) suffer cancellation.
* A small \(\lambda_i\) can be the result of a near-zero interval distance,
  so an equality test between a witness lower bound and \(\overline W_i(M)\)
  needs exact arithmetic or a justified tolerance.
* A large \(U_i\) is valid but can make the old big-\(M\) relaxation and
  numerical conditioning weak. The matching-specific and floor coefficients
  are smaller, but \(L_i(P)-\lambda_i\) can itself involve cancellation.
* Integer or rational log-coefficients support the stated exact matching and
  verification arguments. Floating-point coefficients require explicit
  finite-value checks and tolerance rules.
* A floating-point optimization solver should be followed by independent
  recomputation of budget feasibility, cut activity, matching admissibility,
  and task losses. These are engineering requirements, not guarantees
  supplied by the mathematical formulation.

No arbitrary epsilon smoothing or replacement of invalid coefficients is part
of this framework.

## 8. Prior work and research assessment

The ordinary general-graph matching routines used for the bounds are
classical polynomial-time machinery [5]. Minimum maximal matching is a different
problem: it is equivalent to minimum edge domination in the relevant
unweighted setting and is NP-complete in prior work by Yannakakis and Gavril
[1]. Thus the certified upper bound is easy to compute, while exact
worst-case maximal-matching evaluation remains a genuine bottleneck in the
mixed-sign case.

The master--oracle loop is a problem-specific instance of established
logic-based Benders or branch-and-check ideas [2]. The conditional
inequalities are also a disjunctive/implication formulation in the broad
sense of disjunctive programming [3]. Decision-dependent uncertainty is a
useful conceptual comparison, but its general complexity and modeling
issues are known independently of this matching formulation [4]. These
connections do not establish algorithmic novelty.

### Proven or directly derived

1. Matching-specific cuts dominate the original \(U_i\)-cuts on the common
   continuous relaxation and are exact for binary selections.
2. \(\lambda_i\) is a polynomially computable unconditional floor from
   ordinary matching extrema and is valid for every selected graph.
3. The floor-strengthened cuts are binary-exact and globally valid.
4. Ordinary endpoint bounds certify the inner value when a legal witness
   reaches the bound.
5. Sign-coherent tasks have polynomial inner evaluation and make the empty
   resource set globally optimal when every task is sign-coherent.
6. Exact integer incumbent constraint generation terminates after finitely
   many distinct matching cuts under exact master and oracle assumptions.

### Claims rejected or requiring qualification

The floor strengthening is not an ideal LP formulation: Example 2 has an
integer optimum \(4\) and floor-relaxation value \(3\). A legal maximal
witness obtained by greedily extending a matching is not necessarily a
worst-case witness. Integer separation does not imply fractional separation.
Finally, the compact \(y\)-encoding does not by itself remove the
maximization quantifier or prove a compact exact outer formulation.

### Remaining bottlenecks

The main unresolved algorithmic issue is an exact, practically effective
oracle for mixed-sign maximum-loss maximal matching, together with a useful
fractional separator if branch-and-cut is pursued. Other questions are
whether task-specific graph parameters yield stronger bounds, whether
conditional cuts materially outperform local factor tables, and which
admissibility generalizations preserve a finite certifiable oracle. Any
claim of a practical advantage requires implementation and benchmark evidence,
which is outside this note.

## References

[1] M. Yannakakis and F. Gavril, “Edge Dominating Sets in Graphs,”
SIAM Journal on Applied Mathematics, 38(3), 1980, 364--372.
[DOI](https://doi.org/10.1137/0138030).

[2] J. N. Hooker, “Logic-Based Benders Decomposition,” in *Encyclopedia of
Optimization*, 2000.
[DOI](https://doi.org/10.1002/9781118033036.ch19).

[3] E. Balas, “Disjunctive Programming,” *Annals of Discrete Mathematics*,
5, 1979, 3--51.
[DOI](https://doi.org/10.1016/S0167-5060(08)70342-X).

[4] M. Nohadani and K. Sharma, “Optimization under Decision-Dependent
Uncertainty,” *SIAM Journal on Optimization*, 2018.
[DOI](https://doi.org/10.1137/17M1110560).

[5] J. Edmonds, “Paths, Trees, and Flowers,” *Canadian Journal of
Mathematics*, 17, 1965, 449--467.
[DOI](https://doi.org/10.4153/CJM-1965-045-4).
