# Issue #64 Phase 0 preflight checkpoint v2

**Status: `BLOCKED_INCOMPLETE_HISTORICAL_FINGERPRINT_LEDGER`.** This is an outcome-free feasibility checkpoint, not a cohort manifest, frozen protocol, or experimental result.

## Review issue addressed

The third PR #65 review identified that the prior schema-only singleton allocations exactly consumed all pre-quarantine d=1 templates in each split. V2 changes d=1 to descriptive-only (zero mandatory quota), caps d=2 planning targets at at most half of the exact split capacity, and reallocates the remaining target to d>=3 bins. For DMV11 this changes the d=2 provisional targets from 60/45 to 30/22, preserving at least half of each split's schema-only d=2 capacity before quarantine.

These values are **provisional schema-only planning targets**. The fixed-attempt candidate pool and final cohort quotas have not been established.

## Outcome-free checks performed

- Confirmed PR #65 local HEAD and live remote branch SHA were both `4d693620e79f1f33be619f59d7a7467e11572072` before edits; the dedicated worktree was clean.
- Initialized the shell with `source ~/.bashrc` and verified the required ESS paths.
- Read only the Issue #64 protocol, schema enumerator, static tests, and repository documentation needed for this revision.
- Checked local data/runtime **filenames only** to locate possible fingerprint-ledger inputs. The configured data root contains a file named `arecel-data.tar.gz`; this preflight did not read or hash its bytes. Issue #59's committed run contains aggregate audit JSON/markdown, not a reusable raw fingerprint ledger. No independent Issue #48 exposed-cohort fingerprint ledger is available as a separate outcome-free file.
- Did not open any formal held-out/calibration JSONL, truth, estimate, trace, or PostgreSQL data file. No archive member was extracted or deserialized; no source row/literal was read.
- Recomputed the schema-only provisional split targets with `schema_capacity.py`; exact d=1/d=2 split capacities remain the prior v1 report's unquarantined upper bounds.

## Gate result and boundary

The full historical quarantine requires the pinned AreCEL workload/schema splits plus Stage 1A #38, Stage 2B #48, Issue #59 inputs and all published cohort manifests. Because the #48 exposed cohort has no independent fingerprint ledger in the available outcome-free artifacts, complete quarantine coverage cannot be demonstrated without opening mixed outcome records. Therefore the actual fixed-attempt pool was **not** accepted or frozen, and final immutable quotas were **not** selected. The current protocol is `BLOCKED` at this pre-outcome gate.

The schema-only test suite can establish combinatorial upper bounds and deterministic quota arithmetic only. It cannot certify post-quarantine capacity, source-literal renderability, cohort independence, or PostgreSQL readiness. This checkpoint grants no authority to read outcomes or run physical measurements. Researcher input or a separately staged outcome-free #48 fingerprint ledger is required before continuing that gate.

## Evidence files

- `schema-capacity-report.json`: unchanged v1 schema-capacity proposal, retained for provenance.
- `schema-capacity-report-v2.json`: versioned v2 provisional quota calculations.
- `protocol-v1.json`: retains the same protocol version identifier but marks quotas provisional and the historical gate blocked; no experiment is authorized.
