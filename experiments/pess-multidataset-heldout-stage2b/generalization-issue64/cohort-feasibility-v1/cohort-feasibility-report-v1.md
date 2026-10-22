# Issue #64 prospective cohort feasibility — v1

**Disposition: `BLOCKED_SPECIFICATION_AMBIGUITY` (before attempt 0).** This is an outcome-free Phase 0 feasibility record. No prospective query templates or SQL literals were generated. The fixed seeds, one-million-attempt-per-dataset ceiling, cohort size, split rule, quotas, and historical quarantine requirements remain unchanged. No outcomes, truth/estimates, plans, traces, or PostgreSQL execution were accessed.

## Reproducible boundary and frozen inputs

The protocol declares generator `ess-arecel-query-cohort-v1`, seeds Forest10/Census13/DMV11/Power7 = 6401/6402/6403/6404, at most 1,000,000 attempts per dataset, exactly 1,000 template groups per split, one query per group, and SHA-counter 50/50 group assignment. Its current executable module implements identity/hash-counter primitives only; there is no query builder or SQL literal renderer. Existing synthetic reference vectors remain testable, but do not certify a complete generator.

The reviewed identity-helper source SHA-256 is `663c869fb95b683f00ce62e4b6ab70decfdbcdba986dd55ae9b1b4d1e8b68ad5`. No complete generator source SHA exists because no generator was implemented; the new decision validator and portable-manifest verifier are separately pinned by `portable-manifest-v1.json`.

The v7 historical identity ledger remains immutable and its historical source-coverage gate remains PASS as documented: 480,000 AreCEL workload identities across 12 splits and 184/184 declared Stage 1A / Issue #48 identities matched. The compressed ledger is 75,415,704 bytes (about 71.92 MiB); its report is 58,940 bytes. The prior `SHA256SUMS-v7` with absolute local paths is retained byte-for-byte. The accompanying v1 portable manifest uses repository-relative paths, a stable Git object reference for the frozen Issue #48 protocol, and `ESS_DATA_ROOT/arecel-data.tar.gz` plus a fixed SHA-256 for the external archive.

## Blocking ambiguities in the frozen generator definition

1. **Counter-purpose schedule and column ranking:** the protocol specifies a domain-separated counter and says choices use distinct fixed purpose strings, but does not enumerate a complete purpose-to-draw mapping. The column ordering description gives a purpose and stable column ID, while `counter_u64` has no column-ID parameter; the keyed salt/composition is unspecified. Different deterministic completions can produce different templates and rejection sequences.
2. **Range-width law:** `uniform[0, span]` versus `exponential(lambda=10/span)` is named, but the inverse-CDF transform, rate/scale interpretation, truncation/clipping, zero-span behavior, and treatment when a width extends past the domain are not frozen. Endpoint handling and typed conversion can change SQL and exact fingerprints.
3. **Typed literal and renderer contract:** “pinned AreCEL source renderer” does not identify a renderer function/version for arbitrary newly generated numeric/date/category literals. Decimal/date conversion, serialization, SQL escaping, NULL/missing-value policy, and JSON representation before exact hashing are not fully specified. A historical workload converter is not by itself a frozen generator contract for newly drawn values.
4. **Input row identity:** the protocol requires a pinned parser, CSV bytes, row-order hash, and observed domains in the execution manifest, but these concrete values and parser semantics are not part of the frozen protocol. The source-row-ordinal draw therefore cannot yet be mapped reproducibly to a typed row center.

These are implementation-determining choices, not mere environment metadata. Filling them in locally would change the prospective cohort and is not authorized by the current frozen definition. Therefore no attempt was made, and no rejection count or actual post-quarantine stratum count is claimed.

## Feasibility ledger

| Dataset | Seed | Attempt cap | Attempts executed | Accepted / rejected | Calibration groups | Held-out groups | Quota gap |
|---|---:|---:|---:|---|---|---|---|
| Forest10 | 6401 | 1,000,000 | 0 | Not evaluated | Not evaluated | Not evaluated | Not assessable before specification freeze |
| Census13 | 6402 | 1,000,000 | 0 | Not evaluated | Not evaluated | Not evaluated | Not assessable before specification freeze |
| DMV11 | 6403 | 1,000,000 | 0 | Not evaluated | Not evaluated | Not evaluated | Not assessable before specification freeze |
| Power7 | 6404 | 1,000,000 | 0 | Not evaluated | Not evaluated | Not evaluated | Not assessable before specification freeze |

The cohort target is 1,000 calibration plus 1,000 held-out groups per dataset, with one query per group. The unchanged split-specific d=2 and d>=3 quotas and operator/graph minima are in `protocol-v1.json` and `schema-capacity-report-v2.json`; no reallocation or quota relaxation occurred. The future quarantine check must compare the Issue #59 source-order exact hash and Issue #48 sorted-tuple exact hash as separate namespaces, plus template fingerprints, as specified by the completed history audit. Because generation did not start, candidate-vs-history exact/template collision counts are **not run**, and calibration-vs-held-out collision counts are **not run**. The separate historical ledger's source coverage PASS must not be confused with the prospective zero-collision gate, which remains BLOCKED/NOT RUN.

## Evidence management

Keep the full compressed ledger and the original v7 integrity record as authoritative immutable evidence. A compact quarantine index is suitable for routine membership checks: the v7 report counts 441,962 Issue #59 exact fingerprints, 441,962 Issue #48 exact fingerprints, and 68,897 template fingerprints. At 32 bytes per digest, the namespace-preserving raw total is 30,490,272 bytes (about 29.1 MiB), before headers, source crosswalk, and metadata. This counts the two exact-hash namespaces separately even where they may overlap; it is a conservative index-size estimate, not a measured compressed index. The index can accelerate routine membership checks but cannot replace record-level provenance or explain the two exact-hash contracts.

No external migration is necessary to complete this audit, and none was performed. If clone cost later warrants external storage, propose an immutable content-addressed artifact with SHA verification, retain the portable in-repo manifest and deterministic rebuild script, first verify both copies, then obtain researcher approval before changing tracking/history. No history rewrite or deletion is proposed here.

## Reproduction and limits

Run `python3 -m unittest -v test_verify_portable_manifest.py` from this directory and `python3 verify_portable_manifest.py portable-manifest-v1.json` from the repository Worktree after sourcing `~/.bashrc`. The manifest verifier checks source bytes only; it does not prove generator completeness. The cohort-specific decision is intentionally fail-closed until the researcher freezes the missing algorithmic details and source-row/parser pins. No test truth or held-out estimates were consulted; no new cohort was sent to PostgreSQL.

Actual validation in this worktree used Python 3.12.3: `python3 -m unittest discover -v -s experiments/pess-multidataset-heldout-stage2b/generalization-issue64 -p 'test_*.py'` — 35 tests passed; `validate_feasibility_decision.py` — PASS; `verify_portable_manifest.py portable-manifest-v1.json` — PASS, including the Issue #48 Git object and configured external archive. These static checks do not evaluate post-quarantine candidate yield or certify a generated cohort.
