# Formalized witness-completion lemma

This is the exact statement tested by the Stage 0A reference. It is a
model-internal lemma under the Issue #30 definitions, not a claim about an
unmodified database system.

For task i, let M and U be disjoint forced-selected and undecided resource
sets. Let P be any valid maximal matching of the old selected graph H_i[M].
Let V(P) be its endpoint set, and let U_i^P be the labeled task edges in U
that are disjoint from V(P). Define exact ordinary-matching coefficient
extrema q_i^- and q_i^+ over U_i^P, including the empty matching, and let

    a_i(P) = alpha_i + sum_{e in P} b_{e,i}
    d_i(P; U) = max(0, a_i(P) + q_i^-, -a_i(P) - q_i^+).

Then, for every completion T subset U,

    W_i(M union T) >= d_i(P; U).

Consequently, for every nonempty set of valid old-graph witnesses P_i(M),

    sum_i w_i max_{P in P_i(M)} d_i(P; U)
        <= F_PESS(M union T)

for every feasible completion. The same inequality holds against the exact
minimum over feasible completions.

## Proof under the stated assumptions

Starting from P, repeatedly add an edge of the completion graph that is
disjoint from the current matching until no such edge exists. The resulting
matching Q is maximal in H_i[M union T]. Every added edge belongs to T, is in
the task graph, and was disjoint from V(P) when it was added; therefore the
added edges form an ordinary matching in U_i^P. Its signed coefficient sum lies
in [q_i^-, q_i^+]. Hence the signed loss of Q lies in the interval
[a_i(P)+q_i^-, a_i(P)+q_i^+]. The minimum possible absolute value on this
interval is exactly d_i(P; U), so the maximum over maximal matchings is at
least that value. Taking the maximum over legal witnesses and then the
positive task-weighted sum gives the stated result.

At the root, M and P are empty. U_i^P is the full task graph, so d_i is the
distance of the ordinary-matching signed-sum interval from zero, namely the
existing ordinary-matching floor lambda_i. Thus the root witness bound equals
sum_i w_i lambda_i.

The proof does not assert that a greedy witness is worst-case, that a witness
bound is a global linear cut, that it evaluates the exact objective, or that
it is an efficient outer optimizer. It also does not cover non-additive
maintenance costs or a restricted-master comparator.

