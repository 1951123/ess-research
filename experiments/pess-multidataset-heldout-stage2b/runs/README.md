# Versioned Gate A audit runs

Each audit output is retained.  The v1–v4 outputs were produced by the
superseded pre-review writer; v5–v7 use the exclusive-create writer. `v1`–`v3` are
superseded implementation checkpoints, not scientific outcomes: v1 required
the trace marker in the wrong source file, v2 corrected that but preceded the
canonical source-table contract check, and v3 exposed the Forest10
`forest10_original` table-name distinction.  `v4` is the last pre-review
report.  `v5`/`v6` are the post-review reruns; `v7` uses the final corrected
script with an existing but empty runtime directory and is the report used by
`test_gate_audit.py` and the Stage 2B handoff.

`v8` and `v9` are archive-first Issue-48 runs under the original
`protocol-v2.json`. `v8`
is retained as an immutable execution record but is superseded as the
authoritative summary because its first report did not propagate selected OIDs
from numeric trace records into the compact name mapping. `v9` reran both
datasets after that representation correction; its `gate-audit.json` and
`report.md` are the authoritative Gate A readiness evidence. Neither run
collects held-out outcomes.

`v10` is the review-response rerun under the exact
`protocol-v2-amendment.json` bytes recorded in its report. It adds the predeclared positive-MCV
coverage probe and separates numeric tracing, selected-OID mapping, and
claimed-clause coverage. The first two checks pass for both datasets;
`claimed_clause_indices` remains `UNVERIFIED` because this approved PG build
emits no independent clause-index records, so v10 is explicitly `BLOCKED`.
The v8/v9 files remain unchanged.

`protocol-v3.json` is the current default for future audits. No new runtime or
held-out comparison is implied by this protocol-version correction.

`v11` is retained as a fail-closed implementation checkpoint: its first
replay exposed an overly broad parser for marker-free `ESS_MCV_TRACE`
termination records and did not verify either dataset. `v11-r2` is the first
corrected exclusive rerun; `v11-r3` repeats it from committed code and is the
authoritative final v11 evidence under `protocol-v3.json`. Its raw numeric/MCV
records are PID-associated and both Forest10 and Census13 passed the frozen
Gate A readiness checks. The result is `GATE_A_READY` infrastructure evidence
only, not held-out decision-quality evidence; see `v11-r3/report.md`.
