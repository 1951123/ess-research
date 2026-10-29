# Issue #133 Forest10 ALL versus matched Nominal B5

**Status:** `INCOMPLETE`.

This is a one-configuration, fixed-workload installed-set comparison. B5's five shared candidate IDs were created in their predeclared ALL random-01 relative order. ALL has 40 additional candidate definitions, which may precede and interact with the shared objects; the contrast is therefore not a claim that every mechanism is isolated.

## Frozen selection and order

- Frozen Issue #99 Nominal B5 IDs: `e01_06, e02_07, e02_08, e03_04, e06_08`.
- ALL random-01 projection / B5 CREATE order: `e02_08, e03_04, e02_07, e01_06, e06_08`.
- ALL random-02 projection (not matched): `e02_07, e03_04, e06_08, e02_08, e01_06`.
- B5 order SHA-256: `6aba403c6bd839e0f20059f0793f11322886dc0fcf3af811d1a8b4fc04d9b088`.
- The random-01 and random-02 projections differ; random-01 was frozen as primary before this B5 Test run. random-02 is descriptive only.

## Physical-state verification

- PostgreSQL: 16.14 source `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; pinned binary hashes verified.
- B5 CREATE/target/ANALYZE counts: 5/5/1.
- Exact five-object catalog and ascending OID order: `PASS`.
- Fixed Issue #99 sample SHA-256: `95670277a138f577a7e21eb1567e0f6e1bce1ac489c10907c4a5662577d1aff8`; ordinary column statistics match ALL: `True`.
- Five candidate-ID keyed MCV states/content match both ALL arms: `True`.
- B5 MCV payload states: {"POPULATED": 5}.

## Test Q-error

All three configurations use the same 10,000 official query IDs/truths and Issue #101 zero-aware Q-error/NumPy quantile implementation.

| Configuration | P50 | P95 | P99 | Mean |
|---|---:|---:|---:|---:|
| ALL random-01 (primary) | 1.1804512559972935 | 15.0 | 65.01000000000022 | 6.687501968656185 |
| ALL random-02 (unmatched secondary) | 1.1794969657076213 | 15.0 | 63.01000000000022 | 6.708283813517734 |
| Nominal B5 matched to random-01 | 1.1904948609896286 | 14.0 | 61.506200000000135 | 6.490653490329585 |

Primary contrast: `P95(ALL random-01) - P95(B5) = None`. Positive values mean worse P95 Q-error for ALL.

## Paired query comparison (ALL random-01 minus B5)

- Plan Rows changed: None/10,000.
- Q-error lower for ALL: None; higher for ALL: None; unchanged: None.
- Q-error delta distribution: `null`.
- MCV selection sequence changed: None; estimate sequence changed: None.
- P95-rank neighborhood: None queries in the union of the two predeclared 201-rank bands; Plan Rows changed for None, Q-error changed for None.

### Shared-object MCV use frequency

| Candidate ID | ALL random-01 queries selected / estimated | B5 queries selected / estimated |
|---|---:|---:|
| e01_06 | n/a / n/a | n/a / n/a |
| e02_07 | n/a / n/a | n/a / n/a |
| e02_08 | n/a / n/a | n/a / n/a |
| e03_04 | n/a / n/a | n/a / n/a |
| e06_08 | n/a / n/a | n/a / n/a |

ALL-only candidate IDs participated in selection for None queries and in MCV estimation for None queries (union: None).

### P95-neighborhood query examples

| Query ID | ALL Plan Rows / Q-error / selected IDs | B5 Plan Rows / Q-error / selected IDs | Δ Q-error (ALL−B5) |
|---|---|---|---:|

## Interpretation and limits

The P95 result answers the predeclared fixed-priority comparison for this Forest10 Test workload only. Query-level differences, MCV sequence changes, and ALL-only candidate use are descriptive. Shared-object priority matching does not remove interactions from the 40 additional ALL objects, and no particular blocking mechanism is established.

Issue #135 raw observations and all prior ALL run files remain unchanged outside Git. This run stores only its B5 query archive under ESS_RUNTIME_PARENT; Git contains the compact summary, manifest, catalog audit, and findings.
