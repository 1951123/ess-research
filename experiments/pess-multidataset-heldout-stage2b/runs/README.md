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

`v8` and `v9` are archive-first Issue-48 runs under `protocol-v2.json`. `v8`
is retained as an immutable execution record but is superseded as the
authoritative summary because its first report did not propagate selected OIDs
from numeric trace records into the compact name mapping. `v9` reran both
datasets after that representation correction; its `gate-audit.json` and
`report.md` are the authoritative Gate A readiness evidence. Neither run
collects held-out outcomes.
