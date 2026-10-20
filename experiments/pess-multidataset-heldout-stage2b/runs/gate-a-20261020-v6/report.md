# Stage 2B Gate A audit — 2026-10-20 review rerun

Evidence label: **experimentally observed input availability only**.

This post-review rerun preserves v1–v4 and specifically exercises the
reviewer’s negative case: the runtime path exists but is an empty directory.
The audit still reports **BLOCKED** because source marker presence is not a
pinned/tested PostgreSQL binary, and directory presence is not a fixed-sample
or disposable-cluster validation.

## Command and provenance

```text
mkdir -p /tmp/ess-stage2b-empty-runtime-for-audit
python3 experiments/pess-multidataset-heldout-stage2b/gate_audit.py \
  --data-root /home/wqts/ess-data \
  --pg-source /home/wqts/projects/ess-postgresql \
  --runtime-root /tmp/ess-stage2b-empty-runtime-for-audit \
  --output experiments/pess-multidataset-heldout-stage2b/runs/gate-a-20261020-v6/gate-audit.json
```

The pinned source checkout is at
`23c7c2fdd4bfb561f3257d947fee956a2999fdb6`; source markers are reported as
`SOURCE_MARKERS_PRESENT`, not as runtime readiness.  The audit’s runtime
validator is deliberately `NOT_IMPLEMENTED_BLOCKED` until a separate complete
validator checks binary provenance, fixed-sample manifests, cluster identity,
and trace-contract usability.

## Result

| Check | Status | Meaning |
|---|---|---|
| Forest10 source inputs | INPUT_AVAILABLE | Prior pinned CSV/canonical/pickle identities and contracts pass |
| Census13 / DMV11 / Power7 | MISSING | Required files are absent at the explicitly supplied root |
| PostgreSQL source markers | SOURCE_MARKERS_PRESENT | Source HEAD and marker strings match; this is not a tested binary |
| Runtime directory presence | PRESENT | The directory exists but is empty and is not a cluster |
| PG binary pinned | BLOCKED | Complete binary provenance validator not implemented |
| Fixed-sample manifest verified | BLOCKED | No verified sample/manifest check is performed |
| Issue cluster ready | BLOCKED | No cluster identity/port/socket/database validation is performed |
| Trace contract verified | BLOCKED | No runtime trace validation is performed |
| Overall Gate A | **BLOCKED** | The audit has no PASS path without the complete runtime validator |

No PostgreSQL cluster or query outcome was collected.  This remains a blocked
preparation checkpoint, not a cross-dataset PESS/Nominal experiment.
