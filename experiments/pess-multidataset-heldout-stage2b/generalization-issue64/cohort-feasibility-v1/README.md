# Issue #64 cohort feasibility v1

This evidence bundle is intentionally outcome-free and records `BLOCKED_SPECIFICATION_AMBIGUITY` before candidate attempt 0. It does not contain a generated query cohort or claim prospective isolation.

From this directory, run:

```bash
python3 -m unittest -v test_verify_portable_manifest.py test_validate_feasibility_decision.py
```

From the repository root, verify pinned bytes and the fail-closed decision:

```bash
python3 experiments/pess-multidataset-heldout-stage2b/generalization-issue64/cohort-feasibility-v1/verify_portable_manifest.py experiments/pess-multidataset-heldout-stage2b/generalization-issue64/cohort-feasibility-v1/portable-manifest-v1.json
python3 experiments/pess-multidataset-heldout-stage2b/generalization-issue64/cohort-feasibility-v1/validate_feasibility_decision.py
```

The manifest uses repository-relative paths, an immutable Git commit/path for the Issue #48 protocol blob, and `ESS_DATA_ROOT` plus a fixed SHA-256 for the external AreCEL archive. The old absolute-path `SHA256SUMS-v7` is preserved unchanged. These checks verify provenance and quota-record consistency only; they do not run or certify a cohort generator.
