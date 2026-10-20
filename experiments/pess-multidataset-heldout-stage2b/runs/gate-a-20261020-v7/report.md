# Stage 2B Gate A audit — 2026-10-20 review-fix rerun

Evidence label: **experimentally observed input availability only**.

This is the final post-review rerun for the current blocker checkpoint. It
preserves v1–v6 unchanged and exercises an existing but empty runtime
directory. The result is **BLOCKED**: input availability and source markers
are reported separately from runtime readiness, and the audit has no PASS path
until a complete runtime validator is implemented.

## Command and hashes

```text
mkdir -p /tmp/ess-stage2b-empty-runtime-for-audit
python3 experiments/pess-multidataset-heldout-stage2b/gate_audit.py \
  --data-root /home/wqts/ess-data \
  --pg-source /home/wqts/projects/ess-postgresql \
  --runtime-root /tmp/ess-stage2b-empty-runtime-for-audit \
  --output experiments/pess-multidataset-heldout-stage2b/runs/gate-a-20261020-v7/gate-audit.json
```

Audit script SHA256:
`c57a48bc7bf8d5d8475b3c7afe4cb8570eab5d94cd187bb49c5a2ed82fa94481`.
Result JSON SHA256:
`1aafcd9191f88ea995cf7dd4e23504d50d4f29a077a679667b281777c7e5d0ef`.

## Result

| Check | Status | Meaning |
|---|---|---|
| Forest10 source inputs | INPUT_AVAILABLE | Pinned CSV/canonical/pickle identities and contracts pass |
| Census13 / DMV11 / Power7 | MISSING | Required files are absent at the explicitly supplied root |
| PostgreSQL source | SOURCE_MARKERS_PRESENT | Expected HEAD and trace markers match; this is not binary validation |
| Runtime directory | PRESENT | Directory exists but is empty and is not a cluster |
| PG binary pinned | BLOCKED | Complete binary provenance validator is not implemented |
| Fixed-sample manifest verified | BLOCKED | No verified sample/manifest check is performed |
| Issue cluster ready | BLOCKED | No cluster identity/port/socket/database validation is performed |
| Trace contract verified | BLOCKED | No runtime trace validation is performed |
| Overall Gate A | **BLOCKED** | Empty-directory presence cannot produce PASS |

No PostgreSQL cluster or query outcome was collected. This remains a blocked
preparation checkpoint, not a cross-dataset PESS/Nominal experiment.
