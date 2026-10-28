# ESS / PVLDB Local Evidence Audit — 2026-10-28

**Scope:** read-only audit of T01, T02, T03, T04 and T09 in the PR #131 review triage, plus the requested frozen-sample and order-level recalculations. This report distinguishes source-derived conditional claims, retained-record observations and unverified claims. It is not a paper revision or a new PostgreSQL experiment.

## Executive Summary

| Item | Status | Finding |
|---|---|---|
| T01 — PostgreSQL source / maximal-matching correspondence | **VERIFIED WITH SCOPE LIMITATIONS** | The PostgreSQL 16.14 control flow supports the maximal-matching proposition under A1–A4. It does not establish that real workload tasks satisfy those assumptions. Candidate eligibility is not determined only by remaining attributes. |
| T02 — A1–A4 prevalence in four workloads | **NOT VERIFIABLE FROM RETAINED EVIDENCE** | Available diagnostics are not a complete task census and do not retain the predicate structure and candidate-ranking state needed to test every condition. No prevalence estimate is justified. |
| T03 — Requested vs physical OID order | **VERIFIED WITH SCOPE LIMITATIONS** | Frozen schedule replay matches byte-for-byte. Retained physical manifests and rows validate requested resource sets, OID order, MCV fingerprints and completed arms. This covers the recorded arms, not every possible five-object order or every PostgreSQL catalog. |
| T04 — Model vs PostgreSQL physical-estimate calibration | **PARTIALLY VERIFIED** | Useful Valid-split cardinalities, model artifacts and PG pre-clamp diagnostics exist, but no retained, independent join pairs frozen Train predictions with same-task, same-scheme/order PG measurements. A narrow Issue #23 calibration archive named by the report is missing locally. No calibration statistic was computed. |
| T09 — Sampling, estimand and intervals | **VERIFIED WITH SCOPE LIMITATIONS** | The 156-arm schedule regenerates byte-for-byte, and the complete frozen Test order-level estimand and reported aggregates reproduce from the retained archives. A post hoc four-contrast Bonferroni sensitivity was computed; it does not establish the marginal coverage of the original approximate t intervals. |

**Counts:** 0 unqualified VERIFIED; 3 VERIFIED WITH SCOPE LIMITATIONS (T01, T03, T09); 1 PARTIALLY VERIFIED (T04); 1 NOT VERIFIABLE FROM RETAINED EVIDENCE (T02); 0 CONTRADICTED. No broad claim was marked contradicted. Event B below is a confirmed historical validator defect that was corrected for the continuation run.

**Three main findings:** (1) the matching theorem is supported only as a conditional source/model correspondence, while workload prevalence remains unknown; (2) the OID sample, physical arm identities and final raw aggregates pass independent replay/checks, with a separate known pre-EXPLAIN validator failure repaired; (3) current files do not support an independent frozen-Train-to-PostgreSQL calibration claim.

## Repository and Evidence Boundary

- Local checkout at audit start and end: `the local ess-research checkout`, branch `main`, HEAD `e1a24929bebcca14e972c75be0c7252e733fb477`; the initial checkout was clean. Only the new audit directory and this report are untracked at delivery. No existing file was edited.
- The local task branch exists at `537ecdd7a4a8e2f30b5646478e5a229d33377ae5`. Live PR #131 was checked as a draft with base `main` at `e1a24929bebcca14e972c75be0c7252e733fb477` and PR head exactly `537ecdd7a4a8e2f30b5646478e5a229d33377ae5`. The checkout was not switched. The branch triage file SHA-256 is `ca2d2126abd888c5c6934bd1947ee1e5e277676e8bd6582edbfc989c18238a2c`; branch `paper/main.tex` SHA-256 is `4afd40de85a0a4e736f1f745973deeee4437a58cef17a108dc15a3dcdf8937e1`.
- Read repository `AGENTS.md`, `docs/RESEARCH_CONTEXT.md`, `docs/DECISIONS.md`, `docs/STATUS.md`, the PR-branch triage and formulation notes, and the relevant experiment code/reports. The four optional `r1.txt`–`r4.txt` files were not present in the local repository search; the triage checklist was used as instructed.
- Runtime archive root was resolved from the initialized shell as `$ESS_RUNTIME_PARENT`. The Issue #23 input manifest identifies `$ESS_DATA_ROOT`; specifically named calibration files there were absent. No fallback path was assumed.
- No PostgreSQL server, query, `EXPLAIN`, `ANALYZE`, training, resource reselection or resampling was run. No Test labels were used to fit or adjust anything. `paper/main.tex` was not edited. No commit, push or merge was made.

## Evidence Matrix

### T01 — Source-to-model correspondence

**Conclusion — VERIFIED WITH SCOPE LIMITATIONS (source-derived, conditional).** The checked PostgreSQL 16.14 source supports Proposition 1 in `notes/pg-mcv-maximal-matching-correspondence.md` under its stated A1–A4. Under those assumptions, selected objects form a matching and termination implies no available edge can be added, hence maximality. This does not prove the four benchmark workloads satisfy A1–A4 or that arbitrary abstract tie orders are physically realizable by PostgreSQL.

Pinned source archive: PostgreSQL 16.14 source commit `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`, located under `$ESS_RUNTIME_PARENT/ess-research/issue105/runs/20261025T130222Z-issue105-official-v2/postgresql/source`. SHA-256 of each archived source file matched the same path at the pinned source commit in the local `ess-postgresql` object database.

| Source location (archived line numbers) | Actual control flow | A1–A4 relation and sufficiency | Additional failure conditions |
|---|---|---|---|
| `src/backend/optimizer/path/clausesel.c`, `clauselist_selectivity_ext`, 137–157, 161–186; SHA-256 `b7eda507dcda25c603b4291867eff54e68855cf5fa3a0bd32e671bdf7003fb9e` | The extended-statistics path is gated by clause count, relation/base-relation and `use_extended_stats` conditions; the later pass estimates clauses not already marked estimated. | Provides the call boundary relevant to A1/A3; it does not enforce the one-simple-clause-per-attribute restriction. **Necessary context, not a proof of A1.** | Single-clause path, non-base/join contexts, disabled extended stats, or clauses already consumed can bypass or alter the isolated path. |
| `src/backend/statistics/extended_stats.c`, `choose_best_statistics`, 1277–1363; SHA-256 `8a56497bb040daf36741b5f12ff38e5c38bafbc91d56835791a0cb2dc22355b2` | Filters required statistic kind and inheritance, examines only still-present clauses compatible with the statistic keys/expressions, scores covered attributes/expressions, then uses fewer total keys as a tie-break. Replacement occurs only for a better score or equal score with narrower width; an exact tie keeps the first list item. | Under A1/A2/A4, each usable two-key edge scores 2 and has width 2 while both endpoints remain, so all currently addable edges tie and list order decides. **Sufficient for the claimed ranking only under the assumptions.** | Eligibility is **not solely** a function of remaining attributes: kind, built-object status upstream, inheritance, relation/level, permission, supported clause/operator/type, key/expression coverage, pseudoconstant and prior-consumption conditions also matter. Different widths or compound/repeated-attribute clauses can break the tie. |
| `extended_stats.c`, MCV clause compatibility/consumption and loop, 1363–1608, 1735–1767, 1779–1928; `statext_clauselist_selectivity`, 2093–2129; same SHA as above | Compatible clauses are preprocessed; the selector repeatedly chooses a candidate, returns `candidate=none` when none remains, and nulls/marks clauses covered by a chosen statistic. Standard clause-list estimation invokes MCV before functional-dependency estimation on remaining clauses. | Under A1–A3, selecting an edge consumes its two distinct endpoints and prevents an overlapping edge from a later round. With A4, no candidate means no edge whose two endpoints are both uncovered. This proves maximality of the selected matching, not maximum cardinality. | Other estimator paths, OR/expression/multi-attribute predicates, multiple clauses per attribute, incompatibility, permissions, inheritance differences or candidate filtering can invalidate the correspondence. |
| `src/backend/utils/cache/relcache.c`, `RelationGetStatExtList`, 4857–4869, 4913–4925; SHA-256 `92305bb4a131619025e1830053689d8ff1b61f6d807ab41f20d63b6b59644ef8` | The relation’s extended-statistics OID list is constructed and sorted by OID. | Under A3’s homogeneous applicable candidate list, exact ties are resolved in that fixed list order; for that list the tie order is OID order. **Does not establish arbitrary priority-order reachability.** | `get_relation_statistics` filters/assembles applicable entries; mixed kinds/inheritance or other catalog/system changes are outside the A3 list. Recreating objects also changes catalog state and may change more than priority. |
| `src/backend/optimizer/util/plancat.c`, `get_relation_statistics`, 1363–1445, 1454–1530; SHA-256 `57c42a37254a6c83695b9b1547b964b952977cc77b48e76b51cca40f43e74ba3` | Planner metadata includes successfully built statistics objects and applicable kinds/inheritance metadata; it reads the OID list, keys and expressions. | Supports A2’s “successfully built” candidate precondition and explains why the active candidates are a filtered subset, not every declared object. **Conditional support.** | Unbuilt stats, missing kinds, relation/inheritance/permission restrictions, expression keys and clause-coverage conditions can remove candidates. |

| Assumption | Audit result |
|---|---|
| A1: supported simple predicate ↔ one distinct attribute, one clause per attribute | A mathematical premise, not a property guaranteed by PostgreSQL’s general clause parser. Actual source supports broader forms and filters them through compatibility logic. |
| A2: every candidate is a built two-attribute MCV object over the same initially available clauses | Source supports the built-object and MCV-kind filters; the assumption deliberately removes other statistics shapes and eligibility differences. |
| A3: no earlier estimator consumes relevant clauses and the applicable list is exactly the modeled candidate set | The standard MCV-before-FD call order is visible, but relation, permission, inheritance and compatibility filters still require the stated isolated scope. |
| A4: all eligible edges tie at score 2 / width 2 while both endpoints remain | The source ranking preserves exact ties by first-in-list traversal. OID sorting supplies the fixed order for the homogeneous applicable list. Different candidate shapes need not tie. |

The source loop’s `candidate=none` termination is equivalent to “no addable edge” only after A1–A4 reduce remaining clauses and candidates to graph vertices and edges. Without those conditions it merely means “no candidate passed the source filters.” Instrumented fixture evidence in the correspondence note confirms two controlled creation-order outcomes, not a four-workload prevalence rate.

**Evidence / hashes:** correspondence note SHA-256 `fab3525d4a590c84a9cb77b3b44966c00bdfc790af4535ca16635a104b581b17`; pinned source commit above; four source SHA-256 values in table. **Commands:** source locations were inspected with `nl -ba`/`sed`; archived source files were hashed with `sha256sum` and compared to `git show f1bf37b5dd3d3a7087fc0af5de550ca31035854c:<path>`. **Further experiment:** none needed for the conditional theorem; task-level diagnostics are needed for a prevalence claim (T02).

### T02 — Workload prevalence of A1–A4

**Conclusion — NOT VERIFIABLE FROM RETAINED EVIDENCE.** Do not interpret absence of a recorded violation as universal satisfaction.

- `experiments/pess-multidataset-heldout-stage2b/runs/gate-a-20261020-v11-r3/gate-audit.json` (SHA-256 `62ad36316d3fb1c5f8bc792a6216301b95b5dbb5e129a9a6219098d4936fe6df`) includes only three distinct task IDs in its diagnostics: Forest10 Valid 000000 and 000003, Census13 Valid 000000. Its scope is an OID-level claim/diagnostic check, not full clause-set completeness or a census of all four workload tasks.
- Issue #107 raw rows include query/config/resource IDs, truth, `Plan Rows`, Q-error and MCV event/selection/estimate IDs. They do not retain the complete predicate AST/clause-to-attribute bijection, all candidates with per-iteration rank scores, or the full estimator-consumption and eligibility context needed to decide A1–A4 for every task.
- Catalog manifests pin available built statistics and OID mappings, but do not reconstruct the query-specific eligible candidate set and score at every selector round.

**Evidence / hashes:** gate-audit file SHA above; Issue #107 archives/manifests listed under T03. **Command:** recursive JSON diagnostic inventory and field inspection of the saved audit/raw records; no database work. **Result:** no valid numerator/denominator for the four-workload prevalence. **Further experiment:** yes, if the claim is retained—record per-task predicate shape, eligible candidate set/score and clause consumption on a complete declared task census. Otherwise limit the paper claim to the conditional proposition and existing fixture.

### T03 — Frozen OID schedule and physical execution identity

**Conclusion — VERIFIED WITH SCOPE LIMITATIONS.** The scheduled sample and completed physical arms match the saved identities checked here. This does not prove all 120 permutations of any five-object set are physically realizable, and it does not generalize beyond the pinned build/catalog/sample.

#### B1 — Deterministic schedule replay

The new audit script independently calls the project’s deterministic generator with root seed `17770611677888985956`, loads the frozen resource manifest and compares canonical serialized bytes to the frozen sample. Result: `generated_bytes == sample_bytes` **True**, not merely equal arm counts. This byte equality verifies all eight resource-ID sets, every permutation/order, all 156 arm labels and inclusion probabilities, draw indices, child seeds, per-set sample SHA values, schedule metadata and terminal-LF serialization together.

| Dataset / policy | Resource IDs | Arms | Frozen design | Child seed | Per-set sample SHA-256 |
|---|---|---:|---|---|---|
| forest10 Nominal | `e01_06,e02_07,e02_08,e03_04,e06_08` | 24 | 2 fixed + 22 residual SRSWOR; probabilities `1`, `11/59` | `778e5245a11cf82e` | `6894f7317f3bdd976e00aec96d09db1f23f70bf092f4269f25f617e86e9159c3` |
| forest10 PESS | `e01_06,e02_07,e03_04` | 6 | all 3! orders enumerated; probability `1` | none | `2dc387a785fda6f5568f9b4dbfbe03aff7c505973006cf572f45f7df7d18cf70` |
| census13 Nominal | `e01_05,e02_03,e04_06,e04_08,e06_08` | 24 | 2 fixed + 22 residual SRSWOR; probabilities `1`, `11/59` | `70405be4a44cca31` | `0396a6ce4e14e102ac8ed49de37c8d96cdc4a00bf83347eb24b13378b32b9397` |
| census13 PESS | `e00_11,e01_05,e02_03,e04_06,e07_12` | 24 | SRSWOR from 120; probability `1/5` | `8f3154dce8fcb778` | `7dd2fbf3a4e7ba110e5f2786004c3be6be000e7f32f86aca9a7444de629a0749` |
| dmv11 Nominal | `e00_05,e01_04,e01_07,e02_03,e04_07` | 24 | 2 fixed + 22 residual SRSWOR; probabilities `1`, `11/59` | `e097a4592f1257b7` | `5c39dcea7e690d29d91d43246c2f35fcefb470eb9a051dcd63e4c6be2f963623` |
| dmv11 PESS | `e00_05,e01_04,e02_03,e06_07,e08_10` | 24 | SRSWOR from 120; probability `1/5` | `826e8e81fbd78b58` | `2e7d25671473ef7dbc448d4ca81b4198ed7103dc20edf4e876fba6c9f9e8a904` |
| power7 Nominal | `e00_01,e00_03,e01_02,e02_04,e03_06` | 24 | 2 fixed + 22 residual SRSWOR; probabilities `1`, `11/59` | `8bc8ec42f8356f12` | `1ebbce3843a4f71cb773ff47ee0ed2517e92930b4ba017a90c47dd7643a70371` |
| power7 PESS | `e00_01,e02_04,e03_06` | 6 | all 3! orders enumerated; probability `1` | none | `f261c0e9c8ee3f2e3464d3a55abbcc6f2a93db95433aa2236532e1e898fae0b4` |

Input SHA-256: frozen resource manifest `2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca`; frozen schedule `0b6b247445ab81589c5c5ea7991215fd25e5c60cddf990bf07e3867cda9baa73`; generator `src/ess_research/arecel/oid_sampling.py` `91295ce1abc971165b48324da3bed0dfc377289b4e23f5a5a1b178c98ab49e62`.

#### B2 — Runtime archives and physical OID/catalog identity

`experiments/oid-order-attribution-issue125/analyze_issue125.py` revalidated all three external archives and the corresponding manifest pins, schedule, rows, arm identity and metrics. The analyzer’s temporary output byte-matched the retained `findings.md` exactly (output SHA-256 `dd66859f2b2f0b967839944099ea7a2347e6cece69b6de247814f62140442037`).

| Run | Runtime path | Archive SHA-256 | Manifest SHA-256 | Validated Test rows |
|---|---|---|---|---:|
| Issue #105 official v2 | `$ESS_RUNTIME_PARENT/ess-research/issue105/runs/20261025T130222Z-issue105-official-v2` | `ca2ada0f057f7b439eaee98900f0ae57883adebc84f98d184ec437c1defea9c2` | `920e9ae8cb7d10531075b00b86d261545d30291678b822f18628694258acb38b` | 80,000 (8 prior arms) |
| Issue #107 sampled parent | `$ESS_RUNTIME_PARENT/ess-research/issue107/runs/20261026T055503Z-issue107-sampled-v1` | `d90b4600754fe2dedeb1e7dfc1ccfe75c2de325d630bca565150d1c8218cd767` | `360af848afa93d54a958348981c5764dc643a9fccf0ff4e1b30eaf925eec44e3` | 1,440,000 (144 completed arms) |
| Issue #107 three-object continuation | `$ESS_RUNTIME_PARENT/ess-research/issue107/runs/20261026T062137Z-issue107-pess3-cont-v1` | `27e0a437f5eda7a87be712fe9850bfa939b07df03eed84169b27868a34707ea5` | `639b6c30e2a168d13077a2d3866d598da8612f780285c34b3c6f142748e3d549` | 120,000 (12 completed arms) |

Checks passed for each recorded completed arm: frozen order and configuration/resource IDs match; requested candidate ID order equals observed ascending-OID candidate order; the expected candidate set is present; the catalog maps the expected IDs/OIDs to built target-300 MCV statistics with payload; MCV item count/content hashes match the catalog fingerprints; fixed ANALYZE sample hash/replay status match the protocol; raw archives have pinned member hashes and contiguous extents; each completed arm has 10,000 valid Test rows; stored Q-error recomputes from truth and rounded/clamped `Plan Rows` under the pinned Issue #101 metric; recomputed aggregates match the manifests. Within each #107 sampled-order group, candidate MCV-content fingerprints remain identical across the orders. These are identity and integrity checks, not evidence that the order caused a Q-error change.

The final #107 design contains **156 completed configurations and 1,560,000 recorded EXPLAIN calls**: 144 completed in the parent plus the same 12 frozen three-object configurations in the continuation. The separate #105 archive has 8 historical certainty arms / 80,000 rows and is not added to that final #107 configuration total.

**Event A — eight Issue #105 certainty-arm reuse rejections.** The #107 parent manifest records 0/8 as reusable with only the generic reason `raw observation identity/recomputation failed`; no row-specific exception or exact rejecting assertion was retained. This audit independently validates the preserved #105 rows and confirms the same frozen certainty configurations were physically remeasured in #107. The historical reason for rejecting reuse is **not determinable from retained evidence**. It is not evidence that the original rows were corrupt.

**Event B — twelve three-object PESS pre-EXPLAIN failures.** The #107 parent manifest records six Forest10 and six Power7 arms failing before EXPLAIN with `relation does not have exactly the five selected statistics`; the initial validator used a literal five-object count guard. The continuation corrected the check to compare against the selected-set size and completed those exact 12 frozen identities with 120,000 EXPLAIN calls. This is separate from Event A; Event B did not cause the certainty-arm reuse rejections.

**Evidence / hashes:** analyzer `c60934c335587412375c820991cd7c2ae76e5aa03e1a04ed4496b2b8f603bd66`; retained findings `dd66859f2b2f0b967839944099ea7a2347e6cece69b6de247814f62140442037`; runtime archive and manifest hashes in table. **Command:**

```bash
PYTHONPATH=src:experiments/arecel-test-generalization-issue101:experiments/oid-order-stress-test-issue105:experiments/oid-uniform-priority-issue107 .venv/bin/python -B experiments/oid-order-attribution-issue125/analyze_issue125.py --output "$tmp/issue125-findings.md"
cmp "$tmp/issue125-findings.md" experiments/oid-order-attribution-issue125/findings.md
```

The same analyzer was called by the saved recomputation script for the final run. **Limitations / further experiment:** no new PG experiment is needed to verify these saved arms. A physical census of all five-object permutations or a causal/mechanism-isolation claim requires additional PG measurements and is outside this audit.

### T04 — Model prediction vs PostgreSQL physical calibration

**Conclusion — PARTIALLY VERIFIED.** Existing artifacts establish that several inputs and observables exist, but do not provide a valid independent calibration comparison for the frozen Train-selected model on matching multi-object schemes/orders. No model-vs-PG error, direction agreement, loss-ranking agreement, Spearman or Kendall statistic was computed.

| Artifact | Retained fields / identity | What it can establish | What it cannot establish |
|---|---|---|---|
| `experiments/forest10-decision/real-input-manifest.json`, SHA-256 `bae9202b1807c05932f17e62acaec4e09121fa5a58c994862323562f44e0c71b` | Six selected Valid query IDs and true cardinalities; upstream data/split hashes; issue #23 server/source pin. | Correct identity and truth for six narrowly constructed Valid tasks. | It is not the missing PG observation archive and is not broad workload calibration. |
| `experiments/forest10-decision/real-model-evidence.json`, SHA-256 `6085e8f7f2f140120033477b219fdb15288cd108a8f400161764eb5582afbc1f` | Exact model-side selection/objective evidence for candidates e01…e56; it describes abstract model order scenarios. | The selection/model layer. | It is not a query-level PG measurement join. |
| `experiments/forest10-decision/results/forest10-decision-observations.jsonl.gz`, SHA-256 `5c3a0d78bd8f56e2959213031fecfd90ff2010520cd3578e95f9b01d07874279` | 11,520 `common_shared_order_observation` model records (`budget`, abstract `global_order`, `loss`, selected IDs and model task schemes). | Reproduces abstract model order outcomes. | It contains no PG cardinality, pre-clamp estimate, Plan Rows, truth field or PG MCV event. It is not physical calibration data. |
| `experiments/forest10-decision/real-stage-report.md`, SHA-256 `91f39ddf6e5e20c029cd6c69610fd2079cd3345188bf66dc5f4ef0dba29a1986` | Author-reported 84 Issue #23 task/candidate/repetition records and a six-query Valid composition study; it names `calibration.json` SHA-256 `636d363792d36f27d5b2ff6ea5f9311437ea4f8d04dd964d6a7be12a8cffd3e`. | Reports a narrow, unverified observation: disjoint e12+e34 relative discrepancy `-1.84e-16`; overlapping pseudo-products e12+e23 and e23+e34 `0.1590` and `-0.4904`. | Reported numbers are not independently verified because the named `calibration.json`, `composition-check.json` and `forest10-real-pg-instance.json` are absent under the configured data/runtime roots. The hash is author-reported, not rechecked. |
| Stage2B `generalization-issue64/runs/20261022-forest10-full-valid-v1/collection-manifest.json`, SHA-256 `a6972008f73f24ca3c1a456c96caf64e109895ef5b9525fa2b35791ca5bca99b` | Manifest identifies Valid split, 46 empty/singleton configurations, 174,088 observation rows, 10,000 Valid queries, pre-clamp `nrows_preclamp`, MCV events/status; no truth objective access in collection. | A keyed set of within-Valid physical baseline/singleton pre-clamp observations and diagnostics. | It does not cover multi-object order/scheme arms and has no per-row true cardinality or rounded Plan Rows in this observation collection. |
| Stage2B `generalization-issue64/coefficients.jsonl.gz`, SHA-256 `b1f0e6521804cc0e77f0616271d94b10a3602bde6eb677591ee040e14c7dbd04`; Valid selection `forest10-valid-frozen-selection-v1.json`, SHA-256 `10bcf1f6026aa4de025cbef360c8302aafb2f082d49138c4c5da2d1331f4c798` | Query IDs, alpha/beta, pre-clamp baseline and Valid truth; these are **Valid-fitted** coefficients, not frozen Train coefficients. | It demonstrates a model artifact with Valid identities/truth. | Reusing coefficients fit from the same Valid physical observations is not an independent frozen-Train calibration. It does not supply same-configuration multi-object PG results. |
| Stage2B `forest10-json-calibration-smoke-v1.jsonl`, SHA-256 `44b6af801f501d2f078c92ee41d9e5c1a645f492e668d5f06258d862db981210` | 212 Valid records / 20 queries, query/config ID, pre-clamp estimates and MCV diagnostics, intentionally no truth labels. | Confirms schema-level keyed pre-clamp observations. | Cannot compute Q-error or model-vs-truth calibration alone. |

The required identity tuple is `dataset + split + query_id + configuration/resource_ids + scheme/order`. `query_id` alone is insufficient: Issue #23 uses six selected tasks and e01…e56, while Stage2B has a different 45-candidate map and only empty/singleton physical configurations. The Stage2B coefficients were fit using Valid observations/truth; the Issue #99 Train resource selection manifest does not provide the missing task-level frozen Train coefficients. Rounded Plan Rows and MCV event sequences are not paired with frozen Train predictions for the same multi-object scheme/order. No Test split was read for model fitting or selection.

**Evidence / command:** artifact hash inventory with `sha256sum`; read-only schema/row-count inspection used Python `gzip`/`json` on `forest10-decision-observations.jsonl.gz` and the in-Git Valid smoke file; missing paths were checked only under configured `$ESS_DATA_ROOT` and `$ESS_RUNTIME_PARENT`. **Further work:** first restore the named Issue #23 archive and verify its reported SHA if the six-query check is useful. A broader independent calibration requires frozen Train parameters and selected resources joined to same-query Valid truth, pre-clamp PG estimates, rounded Plan Rows and MCV event sequence for the same multi-object schemes/orders. If those observations do not already exist, a new Valid-only PG experiment is required; do not tune on Test.

### T09 — Estimand and finite-population recalculation

**Conclusion — VERIFIED WITH SCOPE LIMITATIONS.** The order-level values and final estimates were recomputed from the retained raw archives. The manuscript’s four-decimal summary table matches the recalculated values at four decimals. Intervals remain approximate design-based t intervals; this audit does not prove their coverage.

The recomputation used exactly

\[
Y_\pi(M)=\operatorname{P95}_{q\in Test} Q(q,M,\pi),\qquad
\widehat\mu(M)=\mathbb E_{\pi\sim U(\Pi(M))}[Y_\pi(M)].
\]

For each of 156 arms, the analyzer first recomputed Q-error from each query’s rounded/clamped PostgreSQL `Plan Rows` and true cardinality, then NumPy `percentile(values, 95)` (default linear interpolation, NumPy 2.3.4) over that order’s 10,000 Test rows. It then applied the frozen design weights to order-level P95 values. It did **not** pool all query/order Q-errors into one P95. This physical metric is not the same as a pre-clamp estimator loss.

| Design stratum | Frozen arms | Estimate \(\widehat\mu\) | Design SE | FPC | Original approximate 95% t interval (df 21) |
|---|---:|---:|---:|---:|---:|
| Forest10 Nominal | 24 (2 certainty + 22 SRSWOR) | 13.890125363944291 | 0.0355465816960854 | `96/118` | [13.816202200516368, 13.964048527372213] |
| Forest10 PESS (3 objects) | 6/6 enumerated | 14.000000000000000 | 0 | `0/6` | [14.000000000000000, 14.000000000000000] |
| Census13 Nominal | 24 (2 certainty + 22 SRSWOR) | 7.481334175084175 | 0.18350948304556242 | `96/118` | [7.099705313503807, 7.862963036664543] |
| Census13 PESS (5 objects) | 24/120 SRSWOR | 6.283688699360339 | 0 | `96/120` | [6.283688699360339, 6.283688699360339] |
| DMV11 Nominal | 24 (2 certainty + 22 SRSWOR) | 33.10240471774089 | 1.150046712553566 | `96/118` | [30.710751652230957, 35.49405778325082] |
| DMV11 PESS (5 objects) | 24/120 SRSWOR | 26.856127450980342 | 6.625845175565202e-16 | `96/120` | [26.856127450980342, 26.856127450980342] |
| Power7 Nominal | 24 (2 certainty + 22 SRSWOR) | 9.928290407132032 | 0.09753800612769023 | `96/118` | [9.725449019201756, 10.131131795062307] |
| Power7 PESS (3 objects) | 6/6 enumerated | 9.957631822386663 | 0 | `0/6` | [9.957631822386663, 9.957631822386663] |

The Nominal expectation uses certainty-order weight `2/120` and residual SRSWOR weight `118/120`. The archived variance estimator is

\[
\widehat{\operatorname{Var}}(\widehat\mu)=\left(\frac{N_r}{120}\right)^2\left(1-\frac n{N_r}\right)\frac{s^2}{n},
\]

where `N_r=118,n=22` for the Nominal residual frame, and `N_r=120,n=24` for five-object PESS. Thus its finite-population variance multiplier `1−n/N_r` is `96/118` and `96/120`, respectively. These are not square-root corrections. Three-object PESS enumerates all six orders and has zero finite-population sampling variance.

| Dataset | PESS − Nominal | Original approximate 95% interval | Post hoc four-comparison Bonferroni sensitivity interval |
|---|---:|---:|---:|
| Forest10 | +0.10987463605570902 | [+0.03595147262778692, +0.18379779948363112] | [+0.012774438856836351, +0.20697483325458169] |
| Census13 | −1.197645475723836 | [−1.5792743373042037, −0.8160166141434682] | [−1.6989259404372574, −0.6963650110104144] |
| DMV11 | −6.246277266760547 | [−8.637930332270477, −3.854624201250617] | [−9.387782223034986, −3.104772310486109] |
| Power7 | +0.029341415254631187 | [−0.17349997267564496, +0.23218280318490733] | [−0.23709657055109173, +0.2957794010603541] |

Bonferroni critical value is `t_(0.99375,21) = 2.7316324823876363`; the original two-sided 95% critical value is `t_(0.975,21) = 2.079613844727662`. This is explicitly **post hoc sensitivity analysis** on the same frozen estimands and samples. Bonferroni does not prove the marginal t approximation or its coverage; no new significance, causal effect, or physical-performance guarantee is claimed. The original four-dataset table values agree after rounding to four decimals. The five-object PESS strata sample 24/120 orders, so their observed extrema are not the global 120-order extrema; the three-object PESS strata enumerate all six orders.

**Full-precision output:** [`order-level-recomputation.json`](pvldb-local-codex-evidence-audit-20261028/order-level-recomputation.json), SHA-256 `ef93b140483e58f4bffa89ad9cda735e9d9a0ec17c439cba793d2bf4b45b29eb`. It retains each arm’s order, selection label, draw index, inclusion probability, 10,000-query Test P95 and float64 hex, plus design and contrast values. **Further experiment:** none to recalculate these frozen results; improved repeated-workload/generalization inference would require a separately scoped workload sample, not alteration of this frozen estimand.

## Discrepancies

1. **Confirmed historical implementation defect — medium severity:** the initial Issue #107 validator rejected a three-object statistic set using a literal “exactly five” count and failed before EXPLAIN. Reproduce from the parent manifest’s 12 failure records and the initial runner’s guard; the continuation’s selected-set-length validation completed the same 12 frozen configurations. Impact: 12 scheduled configurations were absent from the parent archive; the continuation supplies them. This does not alter Event A or the final sample identities.
2. **Retained evidence gap — Event A reason unknown:** eight Issue #105 certainty arms were rejected for reuse with a generic message and no persisted exact exception. The preserved original rows pass this audit’s current validation, but this does not reveal which historical reuse assertion failed. Do not attribute a cause.
3. **No verified discrepancy in frozen outcome aggregates:** the 156-arm raw recomputation matches the official finite-population aggregates and the manuscript’s reported table to its displayed precision.

The missing Issue #23 external archive and missing T02 task census are evidence gaps, not proven errors in the reported scientific values.

## Minimal Follow-up Plan

### A. Existing data can answer more

- If desired, run a dedicated read-only verifier over the 86 Stage2B Valid observation chunks and pin its summary; this cannot by itself resolve frozen-Train vs multi-object scheme calibration.
- Preserve/use the new full-precision frozen order output for any wording around the four original intervals or a family-wise sensitivity statement.

### B. Restore or obtain missing archive

- Restore Issue #23 `calibration.json`, `composition-check.json` and `forest10-real-pg-instance.json` from the configured data store; verify the reported calibration SHA before interpreting its six-query results. If the bytes cannot be recovered, retain them as author-reported and unverified.
- For T02, seek a complete saved task-level diagnostic census only if one was collected. Existing gate-A snippets cannot be expanded into a prevalence denominator.

### C. New PostgreSQL experiment

- Required only for a broad independent model/physical calibration conclusion if no matching archive exists: freeze Train-derived coefficients and resource IDs first; on existing Valid tasks, collect same-identity pre-clamp values, rounded Plan Rows, MCV events and order for the same multi-object schemes. Keep the estimator and PostgreSQL outputs distinct and do not fit or select on Test.
- Required for a complete four-workload A1–A4 prevalence claim if there is no complete task diagnostic archive: add task-level predicate shape, candidate eligibility/rank, and consumed-clause evidence on a declared census. This is a new instrumentation/data-collection task, not a conclusion available from current files.
- No new PG run is required to reproduce T03/T09. A physical census of all five-object orders or single-statistic causal attribution would be a separate scientific question.

### D. Paper positioning / wording

- Keep the maximal-matching statement explicitly conditional on A1–A4 and describe it as a restricted PostgreSQL instance. Do not add a workload-prevalence claim from the current diagnostics.
- Do not claim frozen model predictions are calibrated to physical PostgreSQL Q-error; current evidence supports only a reported narrow composition check and separate keyed Valid-split observations.
- If discussing a four-dataset family, consider a post hoc sensitivity note with the intervals above and explicitly retain the t-coverage caveat. No immediate `paper/main.tex` change is recommended until researchers decide whether that family-wise framing belongs in the paper.
- Event B can be described as a pre-EXPLAIN validator defect corrected on unchanged frozen configurations; Event A’s exact cause must remain unknown.

## Reproducibility

### Commands and environment

Every project-path shell command initialized the required environment in the same Bash process:

```bash
source ~/.bashrc
: "${ESS_DATA_ROOT:?ESS_DATA_ROOT must be set}"
: "${ESS_RUNTIME_PARENT:?ESS_RUNTIME_PARENT must be set}"
: "${ESS_WORKTREE_PARENT:?ESS_WORKTREE_PARENT must be set}"
```

Repository state was checked with `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git status --short`, `git worktree list`, local branch refs and the PR #131 base/head. The audit’s archive validation command is recorded under T03. The deterministic sample replay and full-precision result were generated with:

```bash
PYTHONPATH=src:experiments/arecel-test-generalization-issue101:experiments/oid-order-stress-test-issue105:experiments/oid-uniform-priority-issue107:experiments/oid-order-attribution-issue125 \
  .venv/bin/python -B notes/pvldb-local-codex-evidence-audit-20261028/recompute_order_level.py
```

Environment recorded by the script: Python `3.12.3`, NumPy `2.3.4`, SciPy `1.18.1`. The script imports the existing Issue #125 archive checker and Issue #101 metric implementation, regenerates the schedule from the pinned Train resource manifest, requires byte equality to the frozen schedule, and writes only the adjacent JSON output. Current script SHA-256 is `48e36743db0a887e3a52b4d03421bcc6088e844462946405089fa7f49795db61`; run stdout is retained in `audit-run.log`, SHA-256 `0ba49362428dd2a07e2c3055e802bbce3c16bcd9f0d793715ef06cd8da638b30`.

**Hash inventory for the frozen T03/T09 run:**

- Resource manifest: `2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca`.
- Schedule: `0b6b247445ab81589c5c5ea7991215fd25e5c60cddf990bf07e3867cda9baa73`.
- Sampler: `91295ce1abc971165b48324da3bed0dfc377289b4e23f5a5a1b178c98ab49e62`.
- Issue #125 analyzer: `c60934c335587412375c820991cd7c2ae76e5aa03e1a04ed4496b2b8f603bd66`.
- Issue #107 runner: `84b29fea0cd6e0837f01d1e22d2febed56070cd0b5c021af433018de93466278`.
- Issue #101/Issue #105/Issue #107 runtime archives and manifests: listed under T03.
- Audit script: `48e36743db0a887e3a52b4d03421bcc6088e844462946405089fa7f49795db61`.
- Full-precision JSON: `ef93b140483e58f4bffa89ad9cda735e9d9a0ec17c439cba793d2bf4b45b29eb`.

**Audit artifacts written locally:**

- [`notes/pvldb-local-codex-evidence-audit-20261028.md`](pvldb-local-codex-evidence-audit-20261028.md)
- [`recompute_order_level.py`](pvldb-local-codex-evidence-audit-20261028/recompute_order_level.py)
- [`order-level-recomputation.json`](pvldb-local-codex-evidence-audit-20261028/order-level-recomputation.json)
- [`verification-summary.json`](pvldb-local-codex-evidence-audit-20261028/verification-summary.json)
- [`audit-run.log`](pvldb-local-codex-evidence-audit-20261028/audit-run.log)

All are below 10 MB. The retained result is derived and reproducible from pinned source inputs; no existing evidence was overwritten.
