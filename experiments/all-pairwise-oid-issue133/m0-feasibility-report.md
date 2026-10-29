# Issue #133 M0 — all-pairwise MCV OID-order feasibility

**State:** M0 complete; no Issue #133 PostgreSQL DDL, `ANALYZE`, `EXPLAIN`, or Test result was executed or read in this worktree. This is a static feasibility finding and a proposed protocol, not an experimental result.

**Minimum sufficient work:** test whether installing the complete frozen two-column candidate universe changes PostgreSQL's per-query MCV choices and Test Q-error as relative OID order changes; reuse the Issue #99 candidate maps/selections/samples and the Issue #101/#105/#107 query, metric, physical-state, and aggregation paths; M0 needs only candidate/hash verification, source inspection, a fixed order schedule, and a bounded runner/trace design.

## Findings summary

| Item | M0 conclusion |
|---|---|
| Four candidate universes complete | **VERIFIED** as static Issue #99 Train maps: 45 + 78 + 55 + 21 = 199 unique ordinary column pairs. |
| All two-column MCV objects statically constructible | **PARTIAL**: generated DDL uses ordinary supported PostgreSQL columns, valid short names, target 300 and two keys. No physical build was attempted; a non-NULL or non-empty MCV payload is not established. |
| Existing framework supports more than five objects end-to-end | **REQUIRES CHANGE**: the pinned helper accepts a variable selected-ID list and the current low-level Issue #105 catalog-order count is dynamic, but its top-level schedule is frozen to four Nominal B=5 sets. The catalog audit also currently rejects null/empty MCV payloads, which must be represented rather than silently filtered in an ALL set. |
| OID order identity control sufficient | **REQUIRES CHANGE**: Issue #105's per-arm OID audit is reusable, but a new schedule must assert exactly 21/45/55/78 IDs and verify each requested order against actual `ORDER BY oid`; candidate IDs, never OIDs across rebuilds, are the cross-arm identity. |
| ANALYZE/sample/MCV content control sufficient | **REQUIRES CHANGE**: exact #99 samples and full-table loading are reusable. Extend per-candidate fingerprinting to the whole set and compare NULL/empty/non-empty payload states and contents across every ALL order. |
| Q-error and blocker diagnostics sufficient | **REQUIRES CHANGE**: the current diagnostics preserve selected candidate IDs, claimed clause indices, and MCV estimates; they do not preserve all tied candidate ranks, clause-to-attribute mapping, or why another candidate became blocked. |
| Cost | **ESTIMATED for counts; UNKNOWN for total wall time and peak disk** until 199-object ANALYZE and query planning are measured under separate M1 authorization. Proposed fail-safe envelope: 6 h early stop / 8 h hard wall, 8 GiB early disk stop / 10 GiB hard cap, six query clients and one active dataset/configuration. |
| Ready to apply for M1 | **CONDITIONAL**: the frozen schedule is complete, but the ALL-specific validator/trace work and M1 resource envelope need review. This report does not authorize execution. |

## M0-A — candidate universe and static constructability

The source of truth is the merged Issue #99 train-only frozen resource manifest, SHA-256 `2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca`. Its four collection run IDs point to the runtime files through `ESS_RUNTIME_PARENT/ess-research/issue99/runs/<run-id>/`; these exact run IDs and paths are recorded in the [candidate universe manifest](candidate-universe-manifest.json). Each `collection-manifest.json` is `COMPLETE`, each source `candidate-map.json` is present, and its recorded collection-manifest byte hash matches the frozen Issue #99 reference.

| Dataset | Frozen source columns | Full table rows | Candidates | Candidate-map digest (Issue #99 canonical JSON) | Candidate-order SHA-256 | Runtime candidate-map file-byte SHA-256 |
|---|---:|---:|---:|---|---|---|
| Forest10 | 10 | 581,012 | 45 | `8fd28b72e4b071dc2ca491502bb61b4652fe9b68269f1db2eef1f6f1f7ffc76b` | `d8efee32db760af2f70ecb494f5dae26c7e99faa9914fd7c60781774bc7482cb` | `042f1d58daec461a127782f2c9658f5fee502ffb478000a08b9261f03d7eb627` |
| Census13 | 13 | 48,842 | 78 | `c661e07db8be24050417014bb5e280dd6cc1d856b26700075638a175e0dc8c64` | `131d526d4fa7540dede14923c2e6a08b2b4238c11ba9399f7c061e587ca65e97` | `39c3b9a6ebc3e9d6f8ed5a1946634ec9e8e4e099a12a9c0ebc40e2fb8b09886f` |
| DMV11 | 11 | 11,591,877 | 55 | `8feab245abc557251d7446ff25d25ead1f43bdf0f39fbc591b19228a8e9d0f5d` | `88d96d9a64de771133d0a3383db2aaec28803f5341596b63f3893ad68e3e0f25` | `ada69993ab2e91acbe0fceaa79c8b95f61d73c3088794df609d485f6a300c0ed` |
| Power7 | 7 | 2,075,259 | 21 | `0c17d1bced2f1ed9b48cb6867982b0938d180c996b3617cb36383d1851c8dfb4` | `11ef38578064f385e28821788344b8e729a35d7f4c01f507df10f1c1618a4bcb` | `aa3a80c9a8850bd2d609b5456b67bab1100ea3c2be0f71d8ac624d75a31bf88f` |

**Hash clarification:** the first digest is not a hash of the pretty-printed runtime file bytes. Issue #99 hashes `json.dumps(candidate_rows, ensure_ascii=True, separators=(",", ":"))`; independently recomputing that exact canonical form reproduced all four collection and frozen-selection digests. The separately listed raw file-byte hashes differ only because those files are formatted with whitespace. The verified output inventory itself has raw SHA-256 `20fd045a1391e6b0308d36ec581e128db185b892bc6e7384540e77c483572104`.

Independent static checks reconstructed every pair from the ordered schema and verified the source map ID, zero-based `(i,j)` ID suffix, endpoint columns, uniqueness, and `n choose 2` count. Candidate names are generated as `ess_issue99_<dataset>_e<i>_<j>`; all are short ASCII identifiers. The catalog columns are ordinary `DOUBLE PRECISION` or `VARCHAR(64)` columns, and every definition is `(mcv)` over exactly two columns with no expression or duplicate unordered pair. The complete ID-to-source-column/catalog-column crosswalk and generated `CREATE STATISTICS` plus target SQL are in the JSON inventory.

Each source map covers every unordered schema pair. The Issue #99 collector also refuses to freeze its map if any Train pair has zero supported queries. That is evidence of a candidate-map construction condition, not evidence that PostgreSQL built every object or that every Test task can use it.

The frozen physical recipe remains: import and row-count-check the **full** source table; set ordinary column statistics targets to 300; create each requested extended-statistics object with MCV kind and set its target to 300; replay the exact Issue #99 sample and run `ANALYZE`. Sample files were read-only SHA-256 checked against the frozen manifest. They carry PostgreSQL 16.14 / target 90,000 headers; Forest10, DMV11 and Power7 contain 90,000 tuples, while Census13 contains its entire 48,842-row table. Thus Test cardinalities still use the full source tables; the fixed sample only controls ANALYZE.

The pinned PostgreSQL source/build is the Issue #105/#107 run-manifest commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; the same commit object and the relevant source file are present in the local `ess-postgresql` repository, whose Worktree was inspected read-only and was clean. In this source, `ComputeExtStatisticsRows` uses `300 * max(target)` over buildable extended statistics, not the sum over objects. With target 300 this is a 90,000-row target regardless of 5 versus 199 statistics objects; the frozen sample itself caps Census13 at all 48,842 rows. This avoids an object-count sample multiplier, but it does not remove the per-object MCV build work.

Static source inspection shows the only-key width is two, below PostgreSQL 16.14's supported statistics-key limit. The native numeric and varchar columns have ordinary ANALYZE support. This makes the DDL **expected to be valid**, not physically verified. In particular, the source MCV builder can return no MCV payload when no sortable sample items exist. A null or zero-item payload must be recorded as part of the ALL treatment rather than filtered out because it may itself be relevant to suppression. Whether such an object is considered and can consume clauses is query- and source-path-dependent and must be traced.

## M0-B — what existing code can and cannot reuse

**Reusable directly:**

- Issue #101 imports and verifies the full source table, applies column target 300, extracts the official Test split, and computes the frozen rounded/zero-aware Q-error.
- The pinned Issue #99 setup helper's `configure_statistics` iterates the supplied selected-ID tuple, drops only this candidate-name universe, emits one MCV `CREATE STATISTICS` and `ALTER ... SET STATISTICS 300` per ID, replays the supplied sample, and runs `ANALYZE`. Its loop is not capped at five.
- Issue #105 checks requested CREATE sequence against actual catalog names/OID-sorted order, maps OIDs back to candidate IDs per arm, fingerprints ordinary statistics, and hashes MCV values/frequencies/base-frequencies. Its lower-level catalog count compares against `len(selected)`.
- Issue #105/#107 preserve per-query selected candidate IDs, MCV clause indices, estimate sequences and Q-error; Issue #107 contains weighted finite-population aggregation machinery for fixed and sampled order strata.

**Needs a small, isolated extension in this experiment directory:**

- A full-universe order schedule and runner must replace the frozen four-set B=5 schedule and overlap-count assertions. Do not change the existing Issue #105/#107 runner or frozen outputs.
- The per-arm validator must require the exact scheduled ID set and dynamic count (21/45/55/78), check the actual OID sequence, expected columns/kind/target, and fingerprint every candidate. It must distinguish `stxdmcv IS NULL`, present-empty, and populated payload; a null/empty list is not a reason to drop a candidate from ALL.
- The new run must compare table identity, ordinary-statistics fingerprints, sample identity, and every candidate payload state/content across all orders before querying Test.
- A lightweight direct shuffle is needed. Issue #107's general finite-population sampler explicitly materializes all `k!` permutations before sampling, which is infeasible at 21–78 candidates. The M0-only [direct Fisher–Yates generator](sample_all_orders.py) shuffles the ID list in O(k) memory and its frozen [schedule](all-order-sample-v1.json) contains the exact candidate orders and hashes.

**Must be added before an M1 that claims blocker evidence:** the current `ESS_DIAGNOSTICS` events name the chosen object, claimed clause indices and MCV estimates. The pinned source's `ESS_MCV_TRACE` logs selected OID and claimed clause index, but neither records every eligible candidate's coverage/key-width score nor maps clause indices to predicate attributes. Issue #125 likewise notes the absence of candidate ranks/blockers. Therefore the current artifacts can show an association between changed MCV sequences and Q-error, but cannot alone prove that a more useful overlapping object was eligible and suppressed.

The minimal trace addition is to retain, under each query ID and selection round, the clause-index-to-attribute/operator map and the candidate IDs that tie the current best `(matched-attribute-count, key-count)` score, followed by which such candidate loses eligibility after the chosen object's clauses are consumed. Join by candidate ID; use OIDs only within each arm. A diagnostic-only PostgreSQL source patch or a proven source-derived replay is required. It must not change the estimator decision path; the source hash/build identity must be recorded. If the exact #105 binary/source pin cannot be kept while adding this evidence, that source change is a separate M1 review risk.

## Evidence boundaries and decision

- **Source-derived (conditional):** PostgreSQL obtains extended-statistics objects in OID order and `choose_best_statistics` selects by most matched remaining attributes, then fewer keys; exact ties retain the first list item. OID order is a causal intervention only when the candidate match scores tie and relevant clauses remain eligible.
- **Experimentally observed in earlier, narrower work:** #105 and #107 successfully audited five- or three-object arms; their successful physical validation does not establish that 21–78 objects build successfully or that all have MCV payloads.
- **Open:** full-universe per-arm ANALYZE time, MCV payload states, query planner time, rank/blocker frequency, and resulting Q-error are unknown. No result supports H1 yet.

M0 produces a frozen, outcome-blind candidate inventory and a 24-arm ALL order schedule. The proposed M1 also includes four matched Nominal B=5 controls, for 28 configurations / 280,000 EXPLAIN calls. No M1 operation is authorized by this report or Draft PR.
