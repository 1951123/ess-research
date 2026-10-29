# Claim-to-evidence matrix

Evidence classes used below:

- **Independent raw recomputation:** recomputed from the retained JSONL gzip observations by `recompute_issue133.py`.
- **Execution-recorded:** taken from the run manifest, protocol, catalog audit or execution commit; cross-checked for consistency but not queried anew because PostgreSQL access was prohibited.
- **Paper interpretation:** checked against the scope and completeness of the preceding evidence.

| Paper claim | Source evidence | Independent audit result | Status |
|---|---|---|---|
| Forest10 ALL01 P95 15.00, matched B5 P95 14.00 | #135 and #136 archive rows; paper `main.tex:60`, `:99–103`, Table 6 | 15.0 and 14.0; both 10,000 queries | PASS |
| Forest10 ALL02 P95 15.00 | #135 archive rows; Table 6 | 15.0; 10,000 queries | PASS |
| DMV11 ALL01 P95 57.61, matched B5 P95 36.00 | #137 archive rows; Abstract/Introduction/Table 6 | 57.6052273 and 36.0044444; both 10,000 queries | PASS |
| DMV11 ALL02 P95 67.53 | #137 archive rows; Abstract/Introduction/Table 6 | 67.52499999999964; rounds to 67.53 | PASS |
| DMV11 ALL02−ALL01 P95 about +9.92 | #137 archive rows; `main.tex:1490–1494` | +9.9197727273 | PASS |
| Forest10 ALL01−B5 P95 +1.0 | #135/#136 archives; `main.tex:1497–1501` | +1.0 | PASS |
| Forest10 ALL orders change 3,329 queries while P95 remains 15 | #135 raw paired rows; `main.tex:1497–1501` | 3,329 Plan Rows and Q-errors differ; 6,475 selection sequences differ; P95 delta 0 | PASS |
| DMV11 ALL orders change 6,246 queries | #137 raw paired rows; `main.tex:1490–1497` | 6,246 Plan Rows and Q-errors differ; 7,663 selection sequences differ | PASS |
| DMV11 ALL01 vs B5: 5,074 worse, 2,384 better, 2,542 equal | #137 raw paired rows; `main.tex:1494–1497` | Recomputed exactly | PASS |
| ALL and B5 have matched relative OID priority among the five shared objects | Frozen order file, Issue #99 resource manifest, protocols and catalog audits | In each dataset B5 candidate IDs/order equal the projection of ALL01; ALL02 projection differs. Numeric OIDs were not compared across arms. Manifest/catalog-audit reported. | PASS (execution-recorded) |
| Shared MCV contents and ordinary stats were controlled | Per-arm catalog audits and manifests | Candidate-ID-keyed MCV state/item count/content hash/target/attributes and ordinary-stat fingerprints agree across compared arms. Manifest/catalog-audit reported, not a live catalog reread. | PASS (execution-recorded) |
| Forest10 ALL has 23 populated and 22 NULL MCV payloads | #135 catalog audits and `main.tex:1503–1510` | 23/22 in each ALL arm; catalog records say definitions exist. NULL payload is not treated as CREATE failure. | PASS (execution-recorded) |
| DMV11 ALL payloads are all populated; B5 has five populated | #137 catalog audits and `main.tex:1511–1517` | 55/55 and 5/5 per catalog audit | PASS (execution-recorded) |
| Forest10 B5 has complete Plan Rows/Q-error but incomplete original diagnostics | #136 raw rows/manifest | 10,000 valid rows; 6,648 original statuses `UNKNOWN_SELECTED_STAT_OID`, 3,352 `complete`; offline remap has no unknown event OIDs but does not upgrade original status or manifest (`INCOMPLETE`). | PASS (limitation retained) |
| DMV11 diagnostic checks passed | #137 archive and catalog/run records | 10,000 Plan Rows and diagnostics-integrity PASS per arm; zero unknown OIDs; attribution PASS/PASS_EMPTY status counts preserved. | PASS (execution-recorded) |
| Observed selection changes prove that a less useful candidate blocks a more useful one | No complete candidate-ranking / clause-consumption / eligibility transition trace | Evidence does not prove this mechanism. The paper explicitly disclaims that inference. | PASS (paper limitation is accurate) |
| ALL is worse under every OID order, PESS prevents all degradation, or more objects always worsen error | Not supported by these fixed arms | Paper does not make these claims in the audited additions. | PASS (no overclaim found) |
| Independent byte reread is still pending | This completed audit and 3 verified raw archives | The sentence at `main.tex:1515–1516` is now stale and should be revised. | FIX REQUIRED |
| Manuscript fits VLDB body page limit | Built 13-page PDF and current VLDB 2027 rules | Body text continues onto page 13; Regular Research and EA&B max is 12 pages excluding references. | FAIL |
