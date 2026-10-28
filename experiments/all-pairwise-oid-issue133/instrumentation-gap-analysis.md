# Issue #133 M0 — instrumentation and framework gap analysis

This is a read-only comparison of existing code and evidence; no runner or PostgreSQL source in the frozen experiments was changed.

## Reuse map

| Need | Existing evidence/code | M0 disposition |
|---|---|---|
| Frozen Train candidate IDs and columns | Issue #99 `candidate-map.json`; Issue #99 frozen selection manifest; canonical map hashes independently recomputed | Reuse as immutable source; full map copied with provenance to the new candidate inventory. |
| CREATE MCV objects and target 300 | Pinned Issue #99 `run_formal.configure_statistics` iterates a supplied ID tuple, drops only candidate names, creates each `(mcv)` object, applies target 300, then runs fixed-sample ANALYZE | The helper has no explicit five-item loop guard. It can issue a 21–78 item sequence in code, but physical success is untested. |
| Fixed full table, ANALYZE sample, PG/Test setup | Issue #101 runner and protocol; Issue #105 verifies full table identity and replays exact sample | Direct reuse, with all source/sample hashes and table identity checked per dataset and arm. |
| Requested-to-actual OID mapping | Issue #105 catalog audit orders by OID and maps object names back to candidate IDs | Extend expected set/count and run over all candidates; verify the requested sequence on every order before Test. |
| MCV payload inventory/content fingerprints | Issue #105 audit records MCV state/count and hashes value/frequency/base-frequency content | Extend to all candidates; preserve explicit NULL, present-empty and populated states and compare each ID across all ALL arms. Do not reject an empty MCV object solely for being empty. |
| Per-query selected candidates and estimates | `ESS_DIAGNOSTICS` JSON: `mcv_selection`, `mcv_clause`, and `mcv_estimate` events; Issue #105/#125 analysis maps per-arm OIDs to candidate IDs | Reuse for selected/consumed/estimate sequences, but add query clause metadata to interpret clause indices. |
| Expected P95 under a uniform finite order population | Issue #107 weighted finite-population aggregation handles fixed certainty and SRSWOR strata | Adapt the same design logic to two certainty orders plus four random draws from `k!−2`; do not average six order metrics equally. |
| All-candidate random order sampling | Issue #107 `sample_permutations` constructs `itertools.permutations(ids)` before sampling | Cannot reuse at `k=21…78`; factorial population construction is infeasible. Use direct Fisher–Yates on the candidate ID list. |

## Five-object assumption and the earlier three-object failure

The current Issue #105 `validate_catalog_rows` checks `len(rows) == len(selected)` and verifies the expected ordered names; its low-level count is dynamic. Its surrounding `frozen_schedule` remains specifically for four Nominal B=5 selections and recomputes their frozen overlap counts. Issue #107's `len(catalog_rows) == 5` check appears in its **Issue #105 reuse audit**, which audits only the eight original five-object configurations; it is not the general physical-arm catalog validator.

There was a separate historical Issue #107 Event B: the original execution commit `af6d01ea541c80cf9f9e4c4b8f0dca3fa7f53951` hard-coded five in the physical catalog validator. The six Forest10 and six Power7 three-object PESS arms were rejected before any EXPLAIN. The validator was corrected to compare against the selected-set length; the separately authorized continuation completed those same 12 arms. That old defect does not describe the Issue #105 eight-arm reuse rejection. For Issue #133, use only a new dynamic full-universe validator and assert exact map count (21/45/55/78), not a copied `==5` check.

## Specific instrumentation gap

The PostgreSQL 16.14 source used by #105/#107 is pinned at `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`. In `src/backend/statistics/extended_stats.c`, `choose_best_statistics` computes the number of still-unestimated attributes covered and the number of keys, then keeps the first entry on an exact tie. `RelationGetStatExtList` sorts extended-statistics OIDs ascending. The existing trace records selected statistic OID/key count and claimed clause index. `ESS_DIAGNOSTICS` adds selected MCV ID, clause index and estimate/selectivity values.

Neither `ESS_MCV_TRACE` nor the current event schema records, per selection round, the other eligible candidates' coverage scores, their tie status, or a candidate's loss of eligibility after an earlier object consumed a clause. The saved query observation also does not carry a clause-index-to-column/operator map. Thus a changed candidate sequence plus changed Q-error is not enough to prove the blocker chain in H1.

Issue #125 already recomputed the frozen #107 query/order summaries and compared Q-error changes with selected/estimated MCV sequence changes. That is the existing descriptive attribution to reuse; its findings do not identify the alternative candidate ranks or a blocker transition. This M0 does not repeat that result analysis.

### Smallest additional evidence

For the all-two-column experiment, the essential trace can stay narrow:

1. At each query's MCV estimation entry, preserve an outcome-blind clause-index map to base attribute and supported operator.
2. At each `choose_best_statistics` round, record candidate IDs with at least two currently eligible distinct attributes, their match score/key width, and the chosen ID.
3. Record the exact clause indices consumed by the chosen object and flag which previously tied candidates drop below eligibility because of those indices.
4. Store the corresponding estimate event and query Q-error; map numeric OID to candidate ID using that arm's catalog audit.

This trace must be observational and leave ranking/comparison state untouched. The smallest implementation is an opt-in, test-only diagnostic extension in the new Issue #133 branch/build plus a parser/schema assertion there. No source patch is authorized in this M0. If the requirement to keep the exact #105 binary hash prohibits adding instrumentation, the remaining alternative is a validated source-derived replay of the chooser from captured clause maps and catalog objects; it must be independently checked against the existing selected-ID events before being used as mechanism evidence.

## Scope-preserving implementation plan for later review

- Add an Issue #133-specific schedule/runner, never edit the frozen #105/#107 runners or reports.
- Reuse #101 input, Q-error and fixed-sample helpers and #105 physical catalog checks; remove only their B=5 schedule assumptions from the new runner.
- Generate the committed full orders with `sample_all_orders.py`; tests use synthetic IDs only.
- Require full catalog and state equality before Test. Keep empty/null MCV payload states rather than removing candidates.
- Keep ordinary Test metrics and weighted order estimator separate from the blocker trace. Query-level examples are descriptive/causal only if all stated prerequisites are verified.
- Keep the PostgreSQL `choose_best_statistics` decisions and source pin unchanged if possible. If diagnostic instrumentation changes the source commit, record the patch/build identity and require review before M1; no result from the base build can be mixed with the instrumented build unless equivalence is validated under a separately frozen rule.

## Open engineering/statistical risks

- A four-random-order sample has low precision for a very large permutation population; the `t_3` 95% interval is approximate. The order-sampling SE is not Test workload uncertainty.
- Full-set MCV payloads may be null, empty or differ across orders if any physical state is not truly fixed. The current #105 validation was written for populated B=5 objects and cannot silently define ALL's empty-payload treatment.
- The number of candidate objects raises each chooser scan from 5 to at most 78 candidates (or from 3 to 78 relative to the prior PESS arm); CPU time is not linear or measured. ANALYZE traverses each object over the same sample, so number of object builds is the other major unknown.
- Candidate-rank traces can grow with query width. Store only eligible/tied candidate scores and blocker transitions, not a dump of all 199 objects for every clause/round; enforce the proposed run-wide disk cap and retain per-arm compressed evidence.
- Existing tests/metrics know only frozen Issue #105/#107 schedules. The new tests must reject duplicate or incomplete orders and missing/incomplete physical arm records, without invoking PG or Test.
