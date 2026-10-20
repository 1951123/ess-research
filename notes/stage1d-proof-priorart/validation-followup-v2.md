# Stage 1D validation follow-up v2

Status: **Experimentally observed**, not a proof or a performance claim.

## Reason for this follow-up

The review of PR #42 at commit `81cb4bfad356fdf5625d6bc04b53d90efe42d623`
found a defect in the first executable diagnostic. Its `path_edges(m)` helper
used an endpoint expression that produced disconnected components for `m >= 3`
(for example, the `m=3` edges were `(0,1),(1,2),(4,5),(3,4),(8,9)`). Thus the
earlier path-reduction pass did **not** establish the connected-path test
hypothesis. This note preserves that negative validation result rather than
reclassifying it as successful evidence.

## Corrective change

The helper now constructs the intended adjacent path

```text
[(0,1), (1,2), ..., (2m-2,2m-1)]
```

and the diagnostic adds a shape regression for `m=1,2,3,4`. The `m=1` case is
checked explicitly as the single edge `(0,1)`; the other cases check the exact
edge order, `2m` distinct vertices, and `2m-1` edges. The reduction test also
now includes deterministic subset-sum YES and NO cases at each of these small
sizes, including `m=4`. The mathematical proof and its assumptions were not
changed.

## Re-execution record

Environment: Issue #41 independent worktree and `.venv`; Python 3.12.3;
stdlib-only; no PostgreSQL, solver, external input, or other repository.

Command:

```text
./.venv/bin/python experiments/theory-stage1d/check_stage1d.py
```

Observed output after the correction:

```text
stage1d exact diagnostics: PASS
checks: star convex hull, global coupling gap, path shape, path reduction, path profile DP, matching-aware transfer
```

The corrected run uses exact `Fraction` arithmetic and bounded exhaustive
enumeration. It is evidence that these finite regression cases execute as
expected; it does not prove the reduction, establish connected-path hardness
for all instances, or provide runtime, scaling, solver, PostgreSQL, or
publication-novelty evidence.
