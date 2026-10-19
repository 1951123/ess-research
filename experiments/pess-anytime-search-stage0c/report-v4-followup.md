# Stage 0c v4 review follow-up

Evidence label: experimentally observed. This is a targeted follow-up to
`report-v3.md`; it does not overwrite v1/v2/v3 evidence and does not change
the scoped scientific **NO-GO** decision.

## Review disposition

The second independent review verified the first review's manifest, exclusive
output, causal checkpoint, compact-evidence, and CI fixes. It identified two
anytime edge cases and one accounting-label issue. This follow-up addresses all
three.

## Targeted fixes

### Greedy interruption

`search_timed.py` now maintains a separate best-evaluated feasible incumbent
and records it immediately at its actual objective-completion timestamp. The
original greedy best-improvement scan and acceptance path are unchanged when
the scan completes. If a later candidate crosses the cap, the already
completed better candidate is returned as a valid pending incumbent rather
than discarded. History entries carry `accepted_by_search` so a pending
best-evaluated result is not mislabeled as a completed greedy-pass acceptance.

The regression uses two independent singleton candidates, a deterministic
0.06-second objective delay, a 0.15-second cap, and checkpoints at 0.05/0.1/
0.15 seconds. The first improving candidate completes before the second
candidate crosses the cap; the short run returns that candidate with objective
`0`, while the trace uses its actual completion time. A longer-cap comparison
showed no objective change in the v3 corpus.

### No-incumbent serialization

`run_search.py` now centralizes reference annotation. If no valid incumbent is
available, it records the exact tiny-instance reference optimum but leaves
`regret=null` and `optimal=null`; it never calls `Fraction(None)`. The
zero-cap runner regression serialized all 126 records with no incumbent and
null regret successfully.

### End-to-end baseline timing

`run_baselines.py` now records `solver_adapter_wall_seconds` for the adapter
call and `full_invocation_wall_seconds` after the independent original-PESS
verification. Therefore the full invocation metric includes post-solver
validation and is not compared as if it were solver-only time.

## v4 observations

- `search-results-v4.json`: 126 records; all independent checks passed; all
  checkpoint completions were causal; objectives were unchanged from v3.
- `baseline-results-v4.json`: 36 records; all statuses were `optimal`; all
  independent checks passed; every full invocation duration was at least the
  adapter-only duration.
- Code SHA used for both v4 runs:
  `b004fb1689d8e216e797b01ea53061eb292ae410`.
- Existing Gate A and checkpoint endpoint evidence remain valid v3 artifacts;
  neither was rewritten.

## Validation and limitations

The new targeted test suite has 7 passing tests, the pinned advisor suite has
24 passing tests, Ruff passes, and the zero-cap runner test produces a valid
new scratch JSON. The CI run for the preceding v3 head succeeded; the v4
commit should be rechecked by CI before researcher merge.

The result remains bounded model-internal evidence. It is not a PostgreSQL
universal claim, a maximum-cardinality matching claim, a global shared-policy
worst-case claim, or a proof of generic efficiency. Solver duals remain
solver-reported floating-point quantities, distinct from exact Fraction
reference calculations.

