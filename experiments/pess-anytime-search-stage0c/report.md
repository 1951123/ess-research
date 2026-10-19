# Stage 0C v2 — anytime PESS search benchmark

Status: **NO-GO for opening a new algorithm-development issue**, scoped to the
predeclared synthetic v1/v2 corpus and protocol. This is not a universal claim
about PostgreSQL, all PESS instances, or all local-search implementations.

## Evidence classification

- **Proven (model-internal):** the independent evaluator enumerates every
  feasible outer subset where used and every labeled maximal matching of each
  selected task graph; its arithmetic is exact `Fraction`. The code preserves
  signed coefficients, labeled parallel edges, zero-cost resources, task-wise
  maxima, and the additive maintenance proxy.
- **Experimentally observed:** Gate A, the full advisor baselines, and the v1/v2
  search runs below were executed in the Issue #35 Worktree. Every reported
  search incumbent passed an independent original-PESS Fraction evaluation.
- **Solver-reported / numerically qualified:** advisor MIP `optimal` statuses,
  primal/dual bounds and MIP gaps come from SciPy/HiGHS. They are not exact
  rational certificates by themselves.
- **Open:** there is no independent global outer optimum for the 24-resource
  stress fixture, no physical maintenance-cost conclusion, and no PostgreSQL
  behavior claim.

## Protocol and provenance

The required input-only v1 commit is `c212d53`. Gate A and adapter code were
then committed in `cb4bf6e`. v1 failed one predeclared corpus acceptance
condition: its named greedy-trap row did not actually trap add-only greedy.
That failure and all v1 raw evidence are retained. Protocol v2 was frozen in
`ca25d15` before its rerun, adding one fixed input without replacing any v1
row. The v2 input SHA is recorded in `protocol-v2.json`.

The read-only advisor checkout was pinned to
`1052ff4a46270c90414d76b32d6f6b37e5908f6a`. The independent Worktree Python
environment used Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1, NetworkX 3.7 and
the package pins in `python-packages.txt`. SciPy's bundled HiGHS was used; the
SciPy Python API did not expose a standalone HiGHS version string, so this is
recorded as a limitation rather than invented metadata. All methods ran as
single-threaded processes with a 10-second full-invocation cap; memory was
**NOT ENFORCED**. Three repetitions used seeds 3501, 3502 and 3503. The search
methods are deterministic, so the seeds identify repetitions rather than
randomize tie choices.

The recorded v1/v2 runs used source HEAD `ca25d15`; a later lint-only commit
reordered imports and removed unused imports without changing experiment logic.
The final code was lint-clean and the two local regression tests were rerun
after that mechanical cleanup.

## Gate A

Gate A ran before approximate-search comparisons on the three v1 tiny inputs.
Static and default Master–Oracle were invoked through the research-side
adapter, with `total_time_limit` covering the full advisor call. All six
Gate-A solver calls (3 inputs × 2 methods) returned `optimal`, and
all returned selections agreed with independent Fraction truth:

| input | independent OPT | Static | Master–Oracle |
|---|---:|---:|---:|
| `tiny_greedy_trap_03` | 0 | 0 | 0 |
| `tiny_mixed_01` | 15/8 | 15/8 | 15/8 |
| `tiny_parallel_zero_02` | 1 | 1 | 1 |

This is a **PASS** for Gate A. No `ess-advisor`, `ess-postgresql`, PG source,
statistics, paper, or real-data root was modified.

## Baseline verification

The v2 full corpus contains six fixed inputs. At the complete 10-second budget,
all 36 advisor baseline calls (6 inputs × 2 methods × 3 repetitions) returned
`optimal`; all returned selections passed independent original-PESS feasibility
and loss checks.

| input | Static objective | Master–Oracle objective | status at 10 s | independent global reference |
|---|---:|---:|---|---|
| `tiny_greedy_trap_03` | 0 | 0 | `optimal` | exact Fraction outer enumeration |
| `tiny_greedy_trap_04` | 0 | 0 | `optimal` | exact Fraction outer enumeration |
| `tiny_mixed_01` | 15/8 | 15/8 | `optimal` | exact Fraction outer enumeration |
| `tiny_parallel_zero_02` | 1 | 1 | `optimal` | exact Fraction outer enumeration |
| `medium_strata_01` | 7/4 | 7/4 | `optimal` | exact Fraction outer enumeration |
| `stress_exploratory_01` | 5/8 | 5/8 | `optimal` | **NO GLOBAL GAP**; selected loss independently exact, outer optimum not enumerated |

The checkpoint sweep retained short-budget outcomes rather than reclassifying
them: 27 v2 endpoint calls were `not_optimal` at short caps, while every v2
10-second endpoint was `optimal` (261 `optimal`, 27 `not_optimal` across all
checkpoint calls). These are independent endpoint-at-budget invocations,
because the advisor API exposes no incumbent callback; they are not presented
as continuous within-run traces. Solver dual bounds remain solver-reported and
tolerance-dependent.

## Fixed greedy counterexample and v1 correction

The v2 input `tiny_greedy_trap_04.json` has budget 4 and exact optimum
`{g4,g5}` with objective 0. Every singleton has objective 4, so the
deterministic add-only greedy rule stops at the empty set with objective 4.
This is an experimentally reproduced nonmonotone greedy trap, not a claim of
an approximation lower bound. It was added through the explicit versioned v2
change-control path after v1's predeclared trap check failed; v1 remains
available for audit.

The second predeclared counterexample is also present: on
`medium_strata_01`, the simple singleton and greedy controls reach 7/4 while
the basic neighborhood and cache-only variants stop at 7/2. Thus a simple
method wins on this fixed stratum; the specialized ordering reaches 7/4 but
does not improve on the simple controls or Static.

## v2 approximate-search results

Each row below is the same result in all three repetitions; all final
objectives and every checkpoint incumbent were independently evaluated by the
original Fraction PESS evaluator. `OPT` is shown only where independent outer
enumeration was run.

| input | empty | singleton | greedy | basic neighborhood | cache only | PESS ordering | ordering + cache | Static/Master at 10 s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `tiny_greedy_trap_03` | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| `tiny_greedy_trap_04` | 4 | 4 | 4 | 4 | 4 | 4 | 4 | 0 |
| `tiny_mixed_01` | 31/8 | 15/8 | 15/8 | 15/8 | 15/8 | 15/8 | 15/8 | 15/8 |
| `tiny_parallel_zero_02` | 1 | 1 | 1 | 1 | 1 | 1 | 1 | 1 |
| `medium_strata_01` | 23/4 | 7/4 | 7/4 | 7/2 | 7/2 | 7/4 | 7/4 | 7/4 |
| `stress_exploratory_01` | 39/8 | 19/8 | 5/8 | 5/8 | 5/8 | 5/8 | 5/8 | 5/8 |

The treatment produced no material original-PESS objective improvement over
the strongest cheap generic control or Static. On the medium fixture it ties
the optimum while singleton/greedy already attain it. On stress every method
shown reaches the same independently evaluated incumbent as the advisor
baselines, but that does not certify a global optimum. On the fixed greedy
trap, the neighborhood variants cannot escape because v1's acceptance rule is
strict improvement from the empty set; Static finds the pair. This is retained
as a failure case, not suppressed.

The treatment's implementation signal is also negative in this corpus. On the
stress fixture, basic neighborhood used 97 exact objective evaluations in
about 0.009 s; cache-only used 74 evaluations in about 0.007 s with 23 cache
hits; ordering-plus-cache used 76 evaluations in about 0.027 s with 8 hits.
The fewer exact evaluations did not yield a better incumbent and the
signed-extrema ordering overhead was larger in this run. These are bounded
observations, not general performance laws.

## Decision

**NO-GO (scoped):** do not open a new algorithm-development issue based on
this corpus. Gate A is valid and the baselines are available, but the one
explicit PESS-specific treatment has no reproducible material advantage over
the strongest cheap heuristic or the unmodified Static baseline, and it loses
to simple methods on the medium trap stratum when the basic neighborhood is
used. The result supports preserving the adapter, exact evaluator, negative
counterexamples and matched traces for future work; it does not establish
universal ineffectiveness, a PostgreSQL result, or a literature novelty claim.

## Raw evidence hashes

| artifact | SHA-256 |
|---|---|
| `protocol-v1.json` | `f71c25d9a2f311344207e36d7db6c30b7ecaba81ecd94b07705b2a9ae7c1cfb2` |
| `protocol-v2.json` | `50f2e5746c4449c6409fb3ea3d844c6872f2fe7456a243c8bcc6cfcd36ff03ec` |
| `gate-a-result.json` | `fbabf5d52a3f780377c140fa9ba1c9e865f8316c72d59a9eeb108345f7af7f2d` |
| `baseline-results.json` (v1) | `d444b34b075d8532919244489147a17ea0878c688ccba0dc0b11d3ae8acb5f03` |
| `search-results.json` (v1) | `60d97bf2db7b07af41513c606753ff7eb5730aa0ce048ef8ec1ff6521c281ae0` |
| `baseline-results-v2.json` | `f2484936312bba3eae1710a7f7b134c33bcefed19584690ed3bba0169cc21309` |
| `search-results-v2.json` | `6ac65417e62a146e27235d83665046df74b9ab183b6c0359718f0eb0bb496016` |
| `baseline-checkpoints-v2.json` | `ff18d06694ad6218eaa4ad329eb2e5a45770683f099fd5d16c73177db798a16c` |

The complete v1 and v2 raw JSON, environment pins, scripts, frozen inputs,
and adapter diagnostics are in this directory. Researcher review and merge
remain required; this Worktree has not been merged automatically.
