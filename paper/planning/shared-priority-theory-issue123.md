# ESS shared-priority theory: formal audit note (Issue #123)

**Status:** candidate for manuscript integration after independent review; **not** a first-discovery claim. The exact novelty of simultaneous edge-priority feasibility is unresolved. No PostgreSQL or frozen-workload evidence is modified.

## Definitions

Let \(M\) be a finite set of **labeled**, non-loop, two-endpoint resources. Task \(i\) has eligible subset \(E_i\subseteq M\); a labeled graph \(H_i[M]\); an inclusion-wise maximal matching \(S_i\subseteq E_i\); and a fixed nonnegative modeled loss \(L_i\) on maximal matchings. A strict total order \(\pi\) on \(M\) induces greedy matching \(\gamma_i(\pi)\) by scanning eligible edges in \(\pi\)-order and accepting edges with free endpoints. Empty graphs have the empty matching. Parallel labeled resources remain distinguishable.

## Theorem 1: fixed target tuple

For a given tuple \((S_i)_i\), the following are equivalent:

1. A shared order \(\pi\) satisfies \(\gamma_i(\pi)=S_i\) for every task.
2. For every task \(i\) and \(e\in E_i\setminus S_i\), **some** conflicting \(f\in S_i\) appears earlier than \(e\) in \(\pi\).

**Proof.** (1)→(2): every rejected eligible edge meets an earlier accepted edge, which belongs to \(S_i\). (2)→(1): take the earliest position at which greedy processing differs from the alleged target accept/reject behavior. An accepted non-target edge has an earlier target blocker by (2), contrary to earliest deviation. A rejected target edge must meet an earlier accepted target edge, contrary to \(S_i\) being a matching. ∎

**Algorithm.** Starting with empty prefix, repeatedly append any remaining resource \(e\) that for every task either (i) is ineligible, (ii) belongs to \(S_i\), or (iii) has an already appended conflicting \(f\in S_i\). If no such resource exists, reject; else produce the prefix as witness once all resources are appended.

**Proof of selection-independence.** Suppose a feasible completion exists. Its first unprocessed edge is safe, otherwise some task would incorrectly accept a non-target. For any safe edge \(e\), move \(e\) to the front of the feasible suffix. If it is a target edge, no target edge of that task conflicts with it, and earlier acceptance can only block non-targets. If it is a non-target eligible edge, a prefix target already blocks it; if ineligible, it has no effect. The transformed completion is feasible. Induct on the remaining suffix size. Failure to find safe resource contradicts existence of a feasible completion. A basic implementation scans \(m\) positions × \(m\) candidates × \(t\) task checks and, with maintained target-blocked flags, costs \(O(tm^2)\) after setup; without maintained flags a conservative bound is \(O(tm^3)\). The task eligibility and labeled-edge representation must be explicit. ∎

**Warning:** blocker precedence uses \(\exists f\), **not** all conflicting target edges. The result tests a *specified tuple*; it does not optimize among unknown local maximizing schemes.

## Corollary 2: tightness

Let \(W_i=\arg\max_{S\in\Gamma_i}L_i(S)\), \(p_i=\max_{S\in\Gamma_i}L_i(S)\), \(P=\sum_i p_i\), and \(G=\max_\pi\sum_iL_i(\gamma_i(\pi))\). Finiteness and nonnegativity give

\[
P=G\quad\Longleftrightarrow\quad\exists\pi\ \forall i:\gamma_i(\pi)\in W_i.
\]

For an order attaining \(G\), each summand \(p_i-L_i(\gamma_i(\pi))\ge0\). The sum is zero exactly when each summand is zero. This **does not** classify the complexity of searching among the different \(W_i\).

## Theorem 3: tight task-count factor

For \(t\ge1\) tasks with nonnegative losses, in this freely-ordered maximal-matching model,

\[
G\le P\le tG.
\]

The first inequality is immediate. Each individual maximal matching is attainable by a suitable edge order: list all its edges first. Thus for each task there is a global order attaining \(p_i\), and other tasks contribute nonnegative loss, so \(G\ge\max_i p_i\). Therefore \(P\le t\max_i p_i\le tG\).

**Tightness:** with \(t\) labeled edges of one star eligible to all \(t\) tasks, each maximal matching selects one edge; task \(i\) gets loss 1 on singleton \(e_i\), otherwise 0. Independent taskwise maximization yields \(P=t\); any shared order picks one first edge in all tasks and gives \(G=A=1\). With natural-log positive ratios \(r_{e_i,i}=2\), all others \(1\), and baseline estimate/truth ratio \(1\), these are scaled by \(\ln 2\), leaving \(P/G=t\). If \(G=0\), then \(P=0\); a ratio is not defined. This is an **abstract** worst-case family, not physical PostgreSQL behavior. ∎

## Theorem 4: shared-order coupling hardness with two candidate edges per task

Take loopless directed graph \(D=(V,A)\) and integer \(K\). Make one installed labeled star edge \(e_v=(c,v)\) per vertex \(v\). Each directed arc \(a=(u,v)\) becomes a task eligible for exactly two edges \(\{e_u,e_v\}\), with loss 1 if the matching is \(\{e_u\}\), 0 otherwise. Greedy selects the earlier of the two edges, so the aggregate score under common edge order is the number of arcs forward in the corresponding vertex order:

\[
Z(\pi)=\sum_{(u,v)\in A}\mathbf 1[e_u\prec_\pi e_v].
\]

Consequently \(G=\operatorname{MAS}(D)=|A|-\operatorname{MinFAS}(D)\), \(P=|A|\), \(A=|A|/2\), and **on this constructed subclass only** \(P=G\) iff \(D\) is acyclic. Since Maximum Acyclic Subgraph / Feedback Arc Set is NP-hard, the explicitly normalized decision \(G\ge K\) is NP-complete for these instances: a vertex/edge order is a polynomial certificate and each task has exactly two eligible edges.

**Exact input encoding:** in the paper's multiplicative loss use positive rational baseline \(n_a^0/T_a=1\), correction factors \(r_{e_u,a}=2\), \(r_{e_v,a}=1\), with weight 1. Each loss is either \(\ln 2\) or 0; use a declared **normalized loss** \(L/\ln 2\) and integer threshold \(K\). Do not claim a general rational-threshold real-log decision language. Input sizes: \(|V|\) installed edges, \(|A|\) tasks, two incidences and constant-bit rational factors each. Opposite arcs and repeated arcs (as separately labeled tasks) are allowed; loops must be excluded. ∎

**Illustration:** the directed cycle of length 3 has \((A,G,P)=(3/2,2,3)\) under unit-normalized loss. Pairwise consistency of desired local outcomes is insufficient for global feasibility.

## Additional classical embedding (not central manuscript contribution)

One task with an arbitrary graph \(H=(V,E)\), \(m=|E|\), and normalized loss \(L(S)=m-|S|\) has \(G=P=m-\min_{S\text{ maximal}}|S|\). Minimum Maximal Matching / edge domination is classically NP-complete. For positive multiplicative ratios choose \(n^0/T=2^m\), each \(r_e=1/2\), and normalize by \(\ln 2\); \(2^m\) has \(m+1\) binary bits. The same matching model with \(L(S)=|S|\) is polynomial via maximum matching. Neither statement establishes hardness of outer budgeted selection.

## Primary literature and provenance

- **M. Yannakakis and F. Gavril (1980)**, *Edge Dominating Sets in Graphs*, SIAM Journal on Applied Mathematics 38(3), DOI: https://doi.org/10.1137/0138030. Classical minimum maximal matching / edge domination hardness. Research-review source attribution, not new hardness.
- **R. M. Karp (1972)**, *Reducibility Among Combinatorial Problems*, DOI: https://doi.org/10.1007/978-1-4684-2001-2_9. Feedback Arc Set NP-completeness.
- **V. Guruswami, R. Manokaran, P. Raghavendra**, *Beating the Random Ordering is Hard: Inapproximability of Maximum Acyclic Subgraph*: https://people.eecs.berkeley.edu/~venkatg/pubs/papers/mas.pdf. Distinguish UGC-conditional near-half approximation inapproximability from unconditional exact optimization hardness.
- **A. Eden, U. Feige, M. Feldman (2022)**, *Max-Min Greedy Matching*, Theory of Computing 18(6), DOI https://doi.org/10.4086/toc.2022.v018a006. Verified original journal abstract: two-sided **vertex ordering** in online bipartite matching, not the same common **edge order** across target maximal matchings.
- **F. F. Dragan (1997)**, *On Greedy Matching Ordering and Greedy Matchable Graphs*, DOI https://doi.org/10.1007/BFb0024498. Verified original abstract describes **vertex ordering** and greedy matchability of induced graphs, not the present fixed-target simultaneous edge-priority decision.
- **A. Darmann, U. Pferschy, J. Schauer, G. J. Woeginger (2011)**, *Paths, Trees and Matchings under Disjunctive Constraints*, Discrete Applied Mathematics, DOI https://doi.org/10.1016/j.dam.2010.12.016. Examines **pairwise edge-selection conflict constraints** rather than simultaneous greedy priority realization; superficially related but a distinct decision model.
- **Nohadani and Sharma (2018)**, *Optimization under Decision-Dependent Uncertainty*, SIAM J. Optimization, DOI https://doi.org/10.1137/17M1110560. General decision-dependent uncertainty predates ESS.

**Prior-art audit limit:** The above original abstracts and source materials clarify model differences; a comprehensive equivalence search of all simultaneous-order/greedy independent-set literature has **not** been achieved. In particular the fixed-target theorem may be an instance of a known greedoid, antimatroid, order-extension, or simultaneous-priority property. DO NOT write "first", "novel polynomial algorithm", or claim absence of equivalent prior art.

## Synthetic test artifact

Run from repository root:

```bash
python3 -m unittest tests/test_shared_priority_theory_issue123.py -v
python3 ci/check_evidence.py
git diff --check
```

The synthetic test includes seeded comparisons of safe-prefix feasibility against every order on small labeled edge sets, a parallel-label infeasibility witness, a complete tiny-digraph MAS score test and tight star / minimum maximal matching identities. It is **not** a PostgreSQL experiment and does not validate physical Q-error. Unlike earlier off-repository tests, this is a committed source artifact.

## Gate

Independent review of this committed code, proof, log-coordinate normalization, and the narrower novelty ledger is required before any `paper/main.tex` change. Issue #123 and this standalone research branch must remain separate from PR #122. No merges are authorized.
