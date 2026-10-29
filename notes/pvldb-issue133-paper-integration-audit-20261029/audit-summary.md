# Issue #133 paper integration audit

**Audit date:** 2026-10-29
**Paper under review:** PR #131, commit `9f9773d09c9b4d9224345c362723c320c5e71b46`
**Scope:** read-only LaTeX/PDF review and independent offline recomputation from the three retained physical-observation archives. No PostgreSQL process or query was started.

## Result

| Audit area | Status | Finding |
|---|---|---|
| Paper source identity | PASS | The live PR #131 head observed for this audit equals the requested commit. `paper/main.tex` SHA-256 is `16b60239ba12f48205b6860176edebed9ca112e3ae59c79ae78eb762be085746`. |
| LaTeX compilation | PASS | `latexmk` completed successfully from the exact paper snapshot; no unresolved citations or references were found. |
| PDF readability | PASS with minor warnings | The new table and section render without clipping or overlap. A 1.27 pt overfull box remains in the new paragraph; other small overfull/underfull warnings are listed in `latex-build-audit.md`. |
| PVLDB page limit | FAIL | The PDF has 13 pages and substantive body text continues onto page 13, where references also begin. Current VLDB 2027 Regular Research and Experiment, Analysis & Benchmark submissions allow at most 12 pages excluding references. The paper's category is not identified in its title; all listed research categories have a body limit no greater than 12 pages. |
| Three raw archive byte identities | PASS | All files exist and their SHA-256 values match the values specified for this audit. Gzip member boundaries, CRC/end-of-member checks, member hashes and expected row counts pass. |
| Six-arm metric recomputation | PASS | All 60,000 query-level Q-errors were recomputed from `Plan Rows` and truth with the Issue #101 zero-aware rules and NumPy 2.3.4 behavior. Every recomputed row value matches its stored Q-error within the script's explicit tolerance; the six P50/P95/P99/mean/max summaries match the expected values. |
| Query pairing | PASS | Stable query IDs and truth vectors match within each dataset. All requested paired counts and P95 deltas independently reproduce. |
| Physical configuration controls | PARTIAL (source-recorded) | The reports/manifests and catalog audits agree on PG build, data/sample/query identity, requested versus actual OID order, targets and candidate-ID-keyed MCV fingerprints. These are execution-time manifest/catalog-audit claims; this read-only audit did not launch PostgreSQL to re-query catalogs. |
| MCV diagnostics | PARTIAL | DMV11 raw diagnostics and candidate-ID attribution statuses are complete per the retained records. Forest10 #136 has 6,648 original `UNKNOWN_SELECTED_STAT_OID` statuses; offline same-run OID-to-candidate remapping recovers observed events but does not restore original diagnostic completeness. The paper preserves this limitation. |
| Blocker mechanism | PARTIAL / not established | Selection sequences differ, but the experiment records do not establish a complete candidate-ranking, predicate-consumption and loss-of-eligibility chain. The paper explicitly avoids claiming that an inferior statistic blocked a superior one. |
| Claim scope | PASS with one stale sentence | New quantitative and causal-scope claims match the evidence. Section 6.3 still says an independent reread is “pending” (lines 1515–1516); this audit now supplies that reread, so update that sentence before final paper integration. |

## Independent recomputation

The raw archives and analysis were independently read from `ESS_RUNTIME_PARENT`; the recomputation does not use any existing `comparison-summary.json` as its source of metric values. The implementation, exact archive identities and machine-readable results are in this directory.

| Dataset / arm | n | P50 | P95 | P99 | Mean | Max | zero-related rows |
|---|---:|---:|---:|---:|---:|---:|---:|
| Forest10 ALL random-01 | 10,000 | 1.1804512560 | 15.0000000 | 65.0100000 | 6.6875019687 | 9,492 | 624 |
| Forest10 ALL random-02 | 10,000 | 1.1794969657 | 15.0000000 | 63.0100000 | 6.7082838135 | 9,369 | 624 |
| Forest10 matched Nominal B5 | 10,000 | 1.1904948610 | 14.0000000 | 61.5062000 | 6.4906534903 | 9,364 | 624 |
| DMV11 ALL random-01 | 10,000 | 1.1510955468 | 57.6052273 | 1,367.5383333 | 107.1089460777 | 79,770 | 799 |
| DMV11 ALL random-02 | 10,000 | 1.1632009595 | 67.5250000 | 2,085.4700000 | 187.1573442231 | 79,775 | 799 |
| DMV11 matched Nominal B5 | 10,000 | 1.1165838603 | 36.0044444 | 984.0750000 | 32.7643870763 | 14,673 | 799 |

The zero-related count is `truth=0, estimate>0`; there were no both-zero or estimate-zero cases in these six test vectors. Q-error was recomputed from integer `Plan Rows` and the per-record truth cardinality; the stored Q-error was checked, not used as input. NumPy 2.3.4 `round` and default percentile behavior were preserved.

| Paired comparison (left minus right) | P95 delta | Plan Rows / Q-error changed | Left better / worse / equal | MCV sequence changed |
|---|---:|---:|---:|---:|
| Forest10 ALL01 − ALL02 | 0.000000 | 3,329 | 1,728 / 1,601 / 6,671 | 6,475 |
| Forest10 ALL01 − B5 | +1.000000 | 4,539 | 2,124 / 2,415 / 5,461 | 7,766 |
| DMV11 ALL02 − ALL01 | +9.919773 | 6,246 | 2,870 / 3,376 / 3,754 | 7,663 |
| DMV11 ALL01 − B5 | +21.600783 | 7,458 | 2,384 / 5,074 / 2,542 | 8,846 |

The DMV11 ALL01-vs-B5 comparison had 8,846 queries with a different MCV selection/estimate sequence; all 8,846 selected at least one ALL-only object. Across those queries there were 22,711 ALL-only selection events. These are descriptive event associations, not proof of a blocker mechanism.

## Archive and control findings

| Run | Observed archive SHA-256 | Rows | Gzip members | Preserved manifest status |
|---|---|---:|---:|---|
| `20261028T1408Z-issue133-forest10-random01-02` | `d088a9b8cb33d62a507dc9cef0fb8e7cc73c12f8116e91ce528a9123d98b7318` | 20,000 | 2 | COMPLETE |
| `20261029Tissue133-forest10-b5-nominal-matched` | `43a4ee6e53106768cef26fefa2b797ed948199451f2ac431f9040cde881ef0b4` | 10,000 | 1 | INCOMPLETE |
| `20261029T0300Z-issue133-dmv11-three-arm` | `69a2202d815c1db991ffdfbfc431d2fa447ddeffc31de898d4ae87d3f5101dbe` | 30,000 | 3 | COMPLETE |

All six arms contain exactly 10,000 unique Test query IDs in the expected sequence. Query-ID and canonical truth hashes match across configurations within each dataset; `Plan Rows` are present and valid for all 60,000 rows. Archive byte hashes match the requested identities. Each concatenated gzip member was independently decompressed, checked for a completed stream/CRC, and hashed separately. No evidence of a shortened or substituted archive was found.

Execution-time records report the same PostgreSQL 16.14 source/build across arms. Forest10 uses the same full table identity, ANALYZE sample SHA `95670277a138f577a7e21eb1567e0f6e1bce1ac489c10907c4a5662577d1aff8`, and ordinary-statistics fingerprint `7438a497092f3fe9bc35eff152e476aa3bf48e60f000f9da9de3937d48a5775e`. DMV11 uses sample SHA `fc1013bb57547aaed5e15bab4de0f126ce21d0e781b5a66d7eabe21423fee249` and ordinary-statistics fingerprint `4763ab61d14d912a9709454bbfa2936de4313590f7e4f5798f34eee9cfb6178d`. Candidate-ID-keyed MCV payload status, item count, content hash, target and attributes match across shared objects. Forest10 ALL had 23 populated and 22 NULL MCV payloads; those NULL payloads were successfully created statistic definitions. DMV11 ALL had 55 populated payloads; DMV11 B5 had five.

These control facts are reported by the retained run manifests/catalog audits and independently cross-compared here. Because the audit prohibited PostgreSQL access, they are not presented as newly observed catalog state.

## Recommendations

1. Shorten or restructure the paper so all non-reference material ends by page 12; rerun visual review after the change. Page-limit compliance is a submission requirement, not a cosmetic issue.
2. Replace the “independent reread ... pending” sentence at `paper/main.tex:1515–1516` with an accurate reference to this completed audit, or remove it when the audited evidence is incorporated.
3. Keep the scope statements that these are fixed physical configurations and that the blocking mechanism is not established.
4. Retain the Forest10 #136 diagnostics limitation exactly as a limitation; do not upgrade its original `INCOMPLETE` manifest/status based on offline remapping.

## Reproduction

See `audit-run.log` for the commands and environment; run `recompute_issue133.py` with the runtime root and frozen source inputs. `python -m unittest -v test_recompute_issue133.py` passed all seven synthetic/boundary tests. The script makes no database connection and does not modify source archives.
