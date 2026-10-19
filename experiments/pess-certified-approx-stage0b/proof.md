# Phase A certificate proof and assumptions

This pilot uses the original task-wise PESS objective

\[
F(M)=\sum_i w_i\max_{P\in\operatorname{MaximalMatchings}(H_i[M])}
\left|\alpha_i+\sum_{e\in P}b_{e,i}\right|.
\]

For each task, coefficient quantization changes only `b` to `b~`. The labeled
graph, eligible edges, resource selection, task alpha, weights, budget, and
selected-graph maximal-matching family are unchanged. In particular, an edge
whose rounded coefficient is zero remains an edge in the graph.

For a fixed selected matching `P`, the reverse triangle inequality gives

\[
\left|\left|\alpha_i+\sum_{e\in P}b_{e,i}\right|
-\left|\alpha_i+\sum_{e\in P}\widetilde b_{e,i}\right|\right|
\leq \sum_{e\in P}|b_{e,i}-\widetilde b_{e,i}|.
\]

The right-hand side is at most

\[
\rho_i=\max_{Q\in\operatorname{Matchings}(H_i)}
\sum_{e\in Q}|b_{e,i}-\widetilde b_{e,i}|,
\]

because every maximal matching is an ordinary matching. Taking the maximum
over the unchanged finite maximal-matching family on both models preserves the
same uniform error bound:

\[
|F_i(M)-\widetilde F_i(M)|\leq\rho_i,
\qquad |F(M)-\widetilde F(M)|\leq\eta=\sum_iw_i\rho_i.
\]

The code checks `rho_i` two ways: exhaustive labeled ordinary matchings and a
separate include/skip recursion with nonnegative error weights. It also checks
the nearest-grid corollary `rho_i <= nu_i delta_i / 2`, where `nu_i` is the
ordinary maximum matching cardinality of the full eligible graph. The corollary
is only recorded when every edge error is at most `delta_i/2`; the exact pilot
always uses the directly computed `rho_i` in the certificate.

If a rounded-model search has a genuinely global lower bound `L~` and a
certified rounded upper bound `U~`, then `OPT~` lies in `[L~, U~]`. Applying the
uniform bound gives

\[
L=\max(0,L~-\eta)\leq OPT\leq F(\widehat M)
\leq U~+\eta.
\]

The pilot prefers the directly evaluated original incumbent `F(M^)` as its
upper bound. Exact tiny rounded enumeration supplies a global lower bound and
therefore produces a scoped original-model certificate. The stress greedy
engine does not supply a global rounded lower bound; those rows are recorded as
`UNCERTIFIED_INCONCLUSIVE` and never advertise a heuristic gap as global
optimality.

The proof is model-internal. It is not a PostgreSQL maintenance or physical
ANALYZE claim, and it does not establish a multiplicative approximation ratio
or a polynomial-time stopping guarantee.
