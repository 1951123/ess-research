# Stage 2C — exact task-oracle reuse opportunity audit

Issue #49 is a falsifiable, model-internal experiment. This directory owns
all Stage 2C artifacts; the Stage 1B, Stage 0C, paper, status, decision-log,
advisor, and PostgreSQL trees are read-only inputs.

## Freeze boundary

`protocol-v1.json` is the preregistration. Its source pin, API boundary,
input strata, canonical-key requirements, metrics, no-op control, and stop
rules were committed before any Stage 2C treatment result was inspected.
`manifest-v1.json` records the required original Stage 1B input hashes and the
independent input-generation plan. New input bytes and their hashes must be
added in a later input-freeze commit before any solver invocation.

The treatment hypothesis is deliberately narrow: a read-only wrapper may
reuse a result or reusable substate only for calls whose complete semantic
identity is equal. A task ID, selected-resource subset, or graph signature by
itself is not an admissible cache key.

## Evidence boundary

This experiment preserves the original task-wise maximal-matching PESS
objective and the additive maintenance proxy used only by the synthetic
instances. It does not alter `ess-advisor`, claim a PostgreSQL result, replace
maximal matching by maximum-cardinality matching, or treat a floating-point
solver status as an exact global certificate.

The first post-preregistration step is an input-only freeze. Profiling must
precede treatment implementation. If the protocol's no-op stop condition is
met, the correct result is a NO-GO/BLOCKED profiling report and no treatment
benchmark.
