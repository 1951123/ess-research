# Stage 2C prior-art and bottleneck audit

**Issue:** #49  
**Audit cutoff:** 2026-10-20 (Asia/Shanghai)  
**Scope:** exact task-local result/substate reuse for the pinned
Master–Oracle implementation. No claim of exhaustive literature coverage is
made.

## Classification

The evaluated treatment is already present in the pinned `ess-advisor` source
as `TaskLocalOracleCache`, selected by the public
`MasterOracleOptions(task_local_cache=True)` switch. Its key is the task ID and
the selected eligible labeled-resource subset, and it stores only completed
results that are either certified by equal exact Fraction bounds or backed by
optimal inner-MIP statuses. Within one top-level solve, the immutable instance,
task coefficients, tolerances, deadline, and objective/witness meaning are
fixed. The Stage 2C wrapper used a stricter research key for profiling and did
not change this advisor implementation.

This makes the observed treatment **source-derived as existing code**, not a
new algorithm. The Stage 2C full key additionally records the complete task
graph, signed coefficients, alpha, explicit tolerances/limits, and fresh-state
contract; a naive `(task_id, selected_subset)` key across instances is rejected
by an independent collision test.

## Required comparison buckets

1. **Memoized oracle evaluations.** The treatment is ordinary invocation-scoped
   memoization of a pure task-local result under a semantic key. The advisor's
   cache already performs this operation, including cacheability checks. No new
   oracle invariant, admissible-family reduction, or certificate is introduced.

2. **Reusable separation subproblems.** Existing Master–Oracle calls evaluate
   the selected task graph and then add a conditional matching cut. Reusing a
   completed task-local evaluation does not reuse a fractional separation
   subproblem or establish a new separation theorem. The exact source path
   keeps the master cuts in a set and rejects an already violated cut; this is
   standard cut bookkeeping, not a Stage 2C contribution.

3. **Cut aggregation and cut-pool management.** Aggregating or retaining valid
   cuts is a separate formulation/solver-design choice. It was not performed
   here, because aggregation could change numerical behavior and would no
   longer be the narrowly scoped exact oracle-reuse hypothesis. The existing
   advisor cache should not be relabeled as cut aggregation.

4. **Incremental branch-and-cut / branch-and-check.** The pinned advisor
   rebuilds its conditional master around the accumulated cut set on each
   iteration. The Stage 2C treatment does not reuse solver bases, branch trees,
   or internal separation state. Such reuse is a distinct future engineering
   or algorithm issue requiring its own correctness and numerical protocol.

5. **Graph dynamic-programming caching.** Memoized boundary/profile states in
   bounded-treewidth or path dynamic programs are established methodology.
   They are not equivalent to caching the general mixed-sign maximal-matching
   MIP oracle used here. The repository's prior-art ledger already records
   bounded-treewidth CSP formulations, resource-constrained label dominance,
   and fixed-graph maximal-matching algorithms; none supplies a PESS-specific
   novelty distinction for this treatment.

## Primary sources consulted

The audit used the existing versioned repository ledger and its primary-source
links, especially: Richey–Parker on fixed-graph minimum-maximal matching
([DOI](https://doi.org/10.1016/0377-2217(88)90258-5)); Bodur–Ekim–Taşkın on
decomposition for minimum-weight maximal matching
([DOI](https://doi.org/10.1002/net.21516)); Kolman–Koutecký on bounded-treewidth
CSP formulations ([DOI](https://doi.org/10.37236/5474)); Righini–Salani on
resource-constrained dynamic-programming labels
([DOI](https://doi.org/10.1016/j.endm.2004.03.047)); and Ghahtarani et al. on
double-oracle/logic-based Benders decomposition
([DOI](https://doi.org/10.1016/j.cor.2023.106243)). These are adjacent
classical ingredients, not evidence that the combined PESS model is
unoriginal.

## Decision

**NO-GO for a separate novel algorithm-development issue.** The only
material hard-case opportunity is an already implemented, exact task-local
memoization switch. The matched experiment gives a small improvement over
uncached Master–Oracle on one sharing-cycle case, but the treatment is not a
new algorithmic distinction and does not deliver a consistent advantage over
unchanged Static across the hard strata. This is a negative result about the
specific Stage 2C treatment, not a claim that all future incremental or
structure-aware methods are uninteresting.
