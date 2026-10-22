# Historical fingerprint reconstruction and isolation gate

**Evidence class:** outcome-free, source-identity reconstruction only  
**Historical source-coverage gate:** `PASS`  
**Prospective cohort zero-collision gate:** `BLOCKED / NOT RUN`

## Scope and method

The rebuild used the pinned AreCEL archive and decoded only the four
`data/<dataset>/workload/base.pkl` members. It verified all four dataset
workloads and their `train`, `valid`, and `test` structure. It also read only
identity fields from the frozen Issue #48 `protocol-v4.json` and the frozen
Stage 1A #38 `protocol.json`.

No label pickle, truth, estimate, PostgreSQL trace, execution plan, measurement
result, or result summary was opened. No new query cohort was generated or
measured. The ledger stores identifiers, split/index metadata, hashes, and
source provenance; it contains no SQL literals or outcomes. The Stage 1A
`canonical_record_sha256` (which is not a query identity fingerprint) was not
used for reconciliation.

The earlier Issue #64 preflight's statement that an outcome-free Issue #48
fingerprint source was missing is superseded by this verified extraction. This
supersession is limited to historical identity-source coverage; it does not
change any frozen protocol or authorize prospective cohort generation.

Pinned inputs and artifacts are enumerated in `SHA256SUMS-v7`; the full counts,
cross-split intersections, and per-claim reconciliation are in
`historical-fingerprint-rebuild-report-v7.json`. The gzip JSONL ledger is
`historical-fingerprint-ledger-v7.jsonl.gz`.

## Coverage result

The source-identity reconstruction **passes**:

- AreCEL archive SHA-256: `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`.
- 480,000 source workload queries: each of Forest10, Census13, DMV11, and
  Power7 has 100,000 train, 10,000 valid, and 10,000 test records; no split is
  missing.
- Issue #48 protocol-v4: 112 test-cohort and 12 validation-calibration
  identities checked.
- Stage 1A #38: 60 frozen selected-query identities checked.
- All **184/184** frozen identity claims match query ID, dataset, source index,
  and source SQL SHA; exact and template fingerprints were checked under their
  respective contracts. No identity mismatch remains.

The frozen protocol hashes are independently pinned in the manifest:

- Issue #48 protocol-v4 SHA-256:
  `54867e0bf3ca116b044d77da14efe1b12d06851af522cfbeb49af14ae33733ad`.
- Stage 1A protocol SHA-256:
  `79d76dbb2cd5c47e3fe434c32a9156040c66bac13f8d7a4cfbda8538fef74307`.
- Issue #59 reference implementation SHA-256:
  `711be1a472439a8c27b59d5a91e6f7a0259ea22fbe69cdfdf7bef25e46fb6ebb`.

## Exact-fingerprint contract distinction

The initial cross-contract comparison reported 49 apparent exact-hash
mismatches. Inspection of the frozen generator resolved these without changing
either contract:

- Issue #48 protocol-v4 hashes sorted `(column, operator, value)` tuples.
- Issue #59 canonical exact fingerprints hash predicates in source/canonical
  SQL order.

Among the 112 Issue #48 test-cohort records, 49 produce different digest bytes
between those two definitions and 63 happen to produce the same digest. All
112 match their own frozen v4 digest when recomputed with v4's sorted-tuple
rule; their SQL SHA and template SHA also match. This is a fingerprint
definition difference, not a failed query-identity reconciliation. Both exact
fingerprints are retained in the ledger and both digest sets are included in
the historical quarantine union. The original v4 and Issue #59 definitions
are not rewritten or treated as interchangeable.

## Structural split audit and gate decision

The JSON report contains exact and template fingerprint intersections for every
within-dataset `train`/`valid`/`test` pair. They are reported, not discarded.
Examples include 1,687 shared Forest10 valid/test template fingerprints,
1,925 Census13 valid/test template fingerprints, 1,976 DMV11 valid/test
template fingerprints, and 1,144 Power7 valid/test template fingerprints.
These are historical source-split properties, not new-cohort collisions.
The full exact-fingerprint and template intersection counts are in the JSON
report.

**Historical ledger coverage: PASS.** All requested historical identity
sources were found and verified; there is no remaining missing historical
source for this ledger.

**Prospective cohort isolation: BLOCKED / NOT RUN.** A fixed-attempt candidate
pool was deliberately not generated, so no claim is made that a future cohort
can satisfy quotas or have zero collisions with this quarantine. This is the
required stop under the task boundary, not a missing-source failure. Cohort
freeze remains unauthorized until a separately approved phase runs the
predeclared pool gate and verifies zero collisions against both exact
fingerprint contracts and the template-fingerprint quarantine.

No PostgreSQL experiment or held-out evaluation is authorized or implied by
this report.

## Reproduction

The rebuild ran with Python 3.12.3 in the isolated task runtime. It has no
random seed or outcome-dependent branch. Re-run from this directory with:

```bash
python rebuild_historical_fingerprints.py \
  --repo-root /home/wqts/projects/ess-research/.worktrees/ess-research-issue64 \
  --archive "$ESS_DATA_ROOT/arecel-data.tar.gz" \
  --issue48-protocol-v4 /home/wqts/projects/ess-research/.worktrees/ess-research-issue48/experiments/pess-multidataset-heldout-stage2b/protocol-v4.json \
  --stage1a-protocol /home/wqts/projects/ess-research/.worktrees/ess-research-issue64/experiments/forest10-heldout-decision-stage1a/protocol.json \
  --output-dir historical-fingerprint-ledger-v7
```

The writer uses exclusive creation and will refuse to replace any existing
versioned output.
