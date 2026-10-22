# Stage 2B Issue #48 — final scientific disposition (2026-10-22)

**Status: INCONCLUSIVE for protocol-conformant Nominal–PESS held-out decision quality.** This note is a **later interpretive addendum**, not a replacement for or modification of any frozen measurement, historical report, selection, protocol, checksum or raw evidence.

## What remains valid

- PostgreSQL 16.14 matched measurements from the historical `formal-20261020-v4` run are retained as **as-executed Empty-control observations**: 60 Forest10 query IDs / 120 records and 52 Census13 query IDs / 104 records, with the recorded provenance and positive pre-clamp traces.
- The historical selector did choose Empty for every method and tested budget **under its erroneous as-executed coefficients**. The absence of a nontrivial physical treatment contrast in that run is a factual observation, not a model-comparison result.
- The v1 failure, superseded v2, invalidated v3, and v4 original outputs/reports remain immutable historical artifacts. Their preexisting labels must be read in light of this addendum.

## Critical protocol nonconformance

Frozen `protocol-v4.json` specified natural-log coefficients `alpha=ln(n0/T)` and `b_e=ln(ne/n0)`. The historical v4 `run_formal.py::rational_log` quantized the **raw ratio**, without taking `ln`. Thus its model selections and the old NO-GO conclusion **do not establish protocol-conformant Nominal/PESS optima or held-out generalization**. The historical report's “authoritative” wording means authoritative *as-executed evidence only*, not scientific validity of the prescribed optimization. The appropriate primary scientific outcome for Issue #48 is **INCONCLUSIVE**, not a tested failure or superiority of either model.

The corrected implementation on PR #58 HEAD computes `Decimal.ln()` at high precision, then 18-place quantization and `Fraction`; regression tests cover near-unity, above/below-unity and invalid inputs. The frozen validation-only diagnostics show changed, sometimes nonempty selections (Forest10 B=3: Nominal `{e12,e23,e34}`, PESS multiple minimizers including `{e34}`). These are **exploratory validation-model observations only**, not independently measured PostgreSQL held-out outcomes. Nonunique minimizers require all ties and deterministic representative selection to be recorded for any future freeze.

## Scope of claims and future handoff

No protocol-conformant matched physical Nominal-vs-PESS contrast was established. Do not replay corrected selections on the previously exposed test cohort and describe it as prospective independent testing. Future evaluation requires a newly preregistered, outcome-free protocol and an independent held-out boundary, respecting SQL-template/group overlap, query eligibility and actual MCV use. Coordinate but do not retroactively change approved [Issue #64](https://github.com/1951123/ess-research/issues/64) or [Issue #71](https://github.com/1951123/ess-research/issues/71).

This addendum documents the correct status for merge review. It does **not** authorize a new PG run, expand Issue #48, close the Issue, or merge the Draft PR.

## Pointers

- Historical original: [formal v4 report](formal-20261020-v4/report.md).
- Validation-only root-cause analysis: [empty-selection diagnostic](empty-selection-diagnostic-20261020-v1/empty-selection-diagnostic.md).
- Corrected exploratory diagnostic: [post-log-fix diagnostic JSON](empty-selection-log-fix-20261020-v1/diagnostic.json).
- PR #58 scientific review chronology: https://github.com/1951123/ess-research/pull/58.
