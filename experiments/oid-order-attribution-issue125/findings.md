# Issue #125 — Read-only physical order attribution

**Evidence class:** experimentally observed, frozen PostgreSQL 16.14 Test observations; all new analysis is descriptive and post hoc over the frozen sample. No database process, ANALYZE, EXPLAIN, resource reselection, training, or resampling is invoked by this analyzer.

## Data integrity gate

The analyzer resolves only the three run IDs specified in Issue #125 under `ESS_RUNTIME_PARENT`. It verifies archive SHA-256, the frozen #107 sample and schedule, arm identity, compressed member SHA-256 and exhaustive contiguous extents, one gzip member per arm, 10,000 valid Test rows per complete arm, canonical Test IDs, recomputed Issue #101 Q-error, MCV event/OID mappings, event sequence projections, and manifest metrics. Candidate IDs, not numeric OIDs, are the cross-order join key; each row’s candidate mapping is verified against that physical configuration’s catalog.

- Sample SHA-256: `0b6b247445ab81589c5c5ea7991215fd25e5c60cddf990bf07e3867cda9baa73`; seed `17770611677888985956`; RNG `ess-splitmix64-fisher-yates-v1`.
- Final #107 identities: **156**; cumulative EXPLAIN calls: **1,560,000**.
- Revalidated rows: #105 `80,000`, #107 parent `1,440,000`, #107 continuation `120,000`.
- Member counts: `issue105` 8, `issue107_parent` 144, `issue107_continuation` 12.
- Official #107 finite-population aggregates and PESS − Nominal contrasts were recomputed from the raw qerrors and matched exactly: **True**.
- #105 reuse audit: global archive/provenance **PASS**; all retained archive/member checks pass; row-level reuse eligible **0/8**; all eight fixed permutations were physically remeasured at those same positions.
- The #107 parent’s 12 invalid Forest10/Power7 three-object arms are pre-EXPLAIN configuration failures. The continuation replaces exactly those 12 frozen identities. This is separate from the #105 fixed-row reuse rejection.

### Frozen evidence locations and hashes

| Source | Runtime path | Raw archive SHA-256 | Manifest SHA-256 |
|---|---|---|---|
| `issue105` | `/home/wqts/ess-runtime/ess-research/issue105/runs/20261025T130222Z-issue105-official-v2` | `ca2ada0f057f7b439eaee98900f0ae57883adebc84f98d184ec437c1defea9c2` | `920e9ae8cb7d10531075b00b86d261545d30291678b822f18628694258acb38b` |
| `issue107_parent` | `/home/wqts/ess-runtime/ess-research/issue107/runs/20261026T055503Z-issue107-sampled-v1` | `d90b4600754fe2dedeb1e7dfc1ccfe75c2de325d630bca565150d1c8218cd767` | `360af848afa93d54a958348981c5764dc643a9fccf0ff4e1b30eaf925eec44e3` |
| `issue107_continuation` | `/home/wqts/ess-runtime/ess-research/issue107/runs/20261026T062137Z-issue107-pess3-cont-v1` | `27e0a437f5eda7a87be712fe9850bfa939b07df03eed84169b27868a34707ea5` | `639b6c30e2a168d13077a2d3866d598da8612f780285c34b3c6f142748e3d549` |

## Existing attribution and scope

Issue #105 already compares the four Nominal canonical/reverse pairs query by query, including Q-error direction and MCV selection/estimate candidate-ID sequence changes. Those eight certainty arms are not re-counted as a new result here. Issue #107’s verified aggregate analysis explicitly did not decompress raw rows or read query-level Q-error, so it did not perform the sampled-order attribution below. Issue #116 is a separate Census13 Train-only model analysis and does not explain these physical Test observations.

### Reuse rejection history (Event A)

The retained #107 parent manifest shows all global #105 archive/provenance checks and all eight compressed-member hash checks passed, but row-level reuse eligibility was 0/8. Each arm has only the generic reason `raw observation identity/recomputation failed`; `row_validation_failure` is empty, and the eight final arm records do not retain an exception. The current read-only audit verifies the original #105 members, 10,000 row identities, stored/recomputed Q-errors, MCV diagnostics, and exact canonical/reverse order labels, while the frozen #107 arms show those same eight permutations were physically remeasured. The historical rejecting assertion cannot be confirmed from retained evidence. This is not evidence that the #105 raw observations were corrupt; it does not establish the specific failure cause either.

### Three-object pre-EXPLAIN rejection history (Event B)

The other 12 failures are distinct: six Forest10 and six Power7 PESS configurations had three selected objects, zero EXPLAIN calls, and no raw member. Their parent manifest records `relation does not have exactly the five selected statistics`. The source pinned to the initial #107 run (`af6d01e`) confirms `validate_catalog_rows` used a literal `len(rows) != 5` guard; the corrected runner compares against the selected-set length. The continuation completed those same 12 identities and 120,000 EXPLAIN calls. This validator defect did not cause the eight five-object Nominal reuse rejections in Event A.

The order-level inferential target remains `E_pi[P95_q Q(q,M,pi)]`. This report does not calculate or substitute `P95_q[E_pi Q]`. Query comparisons below are paired descriptive contrasts to one anchor order within each frozen set; they are not independent order samples, do not estimate a new population mean, and do not alter #107’s finite-population weighted estimator.

For Nominal, the anchor is the fixed canonical order and the 22 SRSWOR orders are compared separately; the fixed reverse order remains a certainty arm and is not pooled into those comparisons. For five-object PESS sets, the anchor is the first frozen SRSWOR draw and the remaining 23 sampled orders are descriptive contrasts. For three-object PESS sets, the lexicographically first order anchors the other five fully enumerated orders. No anchor is selected by its Q-error.

High-tail membership is defined within each order as `Q-error >= that order's NumPy P95`; values tied at the threshold are retained. Entrants/exits compare those per-order sets against the stated anchor. This is a descriptive query-membership diagnostic, not a second estimand.

## Observed per-order P95 ranges

Ranges are split by the frozen design class; extrema are observed sample extrema unless the stratum is fully enumerated.

| Dataset | Policy | Set size | Fixed certainty P95 range | SRSWOR P95 range | Full enumeration P95 range |
|---|---|---:|---|---|---|
| forest10 | nominal | 5 | 13.5842 (forest10-nominal-000-fixed) – 14 (forest10-nominal-001-fixed) | 13.5042 (forest10-nominal-011-srswor) – 14 (forest10-nominal-022-srswor) | — |
| forest10 | pess | 3 | — | — | 14 (forest10-pess-000-enumerated) – 14 (forest10-pess-005-enumerated) |
| census13 | nominal | 5 | 6.25 (census13-nominal-000-fixed) – 8 (census13-nominal-001-fixed) | 6.25 (census13-nominal-010-srswor) – 8.38889 (census13-nominal-019-srswor) | — |
| census13 | pess | 5 | — | 6.28369 (census13-pess-015-srswor) – 6.28369 (census13-pess-016-srswor) | — |
| dmv11 | nominal | 5 | 22.226 (dmv11-nominal-000-fixed) – 36.0044 (dmv11-nominal-001-fixed) | 22.226 (dmv11-nominal-010-srswor) – 36.6579 (dmv11-nominal-019-srswor) | — |
| dmv11 | pess | 5 | — | 26.8561 (dmv11-pess-005-srswor) – 26.8561 (dmv11-pess-021-srswor) | — |
| power7 | nominal | 5 | 9.80685 (power7-nominal-001-fixed) – 9.84495 (power7-nominal-000-fixed) | 9.22287 (power7-nominal-004-srswor) – 11.0004 (power7-nominal-013-srswor) | — |
| power7 | pess | 3 | — | — | 9.95763 (power7-pess-000-enumerated) – 9.95763 (power7-pess-005-enumerated) |

## Paired query diagnostics by frozen set

Counts are query-order pairs against the anchor described above. The repeated observations share Test queries and, in sampled strata, the anchor is also part of the finite sample; counts are descriptive and are not IID standard errors.

| Dataset | Policy | Anchor | Compared orders | Q-error lower / higher / tie | Selection IDs changed | Estimate IDs changed | ID-sequence changed, Q-error tied | ID-sequence changed, Q-error changed | ID-sequence same, Q-error changed | MCV estimate values changed | Tail entered / exited events | Distinct entering / exiting queries |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| forest10 | nominal | fixed canonical certainty order | 22 | 14862 / 14161 / 190977 | 75939 | 75939 | 46916 | 29023 | 0 | 56719 | 371 / 303 | 41 / 27 |
| forest10 | pess | lexicographically first fully enumerated order | 5 | 0 / 0 / 50000 | 13499 | 13499 | 13499 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| census13 | nominal | fixed canonical certainty order | 22 | 2534 / 15197 / 202269 | 77552 | 77552 | 59821 | 17731 | 0 | 37016 | 1799 / 1792 | 165 / 159 |
| census13 | pess | first frozen SRSWOR draw (descriptive anchor only) | 23 | 0 / 0 / 230000 | 87921 | 87921 | 87921 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| dmv11 | nominal | fixed canonical certainty order | 22 | 6052 / 31791 / 182157 | 83087 | 83087 | 45244 | 37843 | 0 | 45271 | 2144 / 2144 | 135 / 130 |
| dmv11 | pess | first frozen SRSWOR draw (descriptive anchor only) | 23 | 0 / 0 / 230000 | 89890 | 89890 | 89890 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |
| power7 | nominal | fixed canonical certainty order | 22 | 22952 / 23667 / 173381 | 81610 | 81610 | 34991 | 46619 | 0 | 54560 | 474 / 474 | 64 / 59 |
| power7 | pess | lexicographically first fully enumerated order | 5 | 0 / 0 / 50000 | 14041 | 14041 | 14041 | 0 | 0 | 0 | 0 / 0 | 0 / 0 |

## Counterexample audit over every eligible order pair

This second diagnostic checks every unordered pair of frozen orders except the canonical/reverse pair already analyzed in #105. It keeps certainty-versus-SRSWOR, SRSWOR-versus-SRSWOR, and complete-enumeration pairs separate. These repeated pair counts are not independent observations and are not used for a mean, confidence interval, or population extrapolation.

| Dataset | Policy | Pair design | Order pairs | Query pairs | ID sequence changed, Q-error tied | ID sequence changed, Q-error changed | ID sequence same, Q-error changed | Numeric MCV values changed after candidate-ID alignment |
|---|---|---|---:|---:|---:|---:|---:|---:|
| forest10 | nominal | certainty_vs_sampled | 44 | 440000 | 101313 | 55144 | 0 | 105855 |
| forest10 | nominal | sampled_vs_sampled | 231 | 2310000 | 544841 | 263777 | 0 | 498427 |
| forest10 | pess | fully_enumerated_pairs | 15 | 150000 | 40497 | 0 | 0 | 0 |
| census13 | nominal | certainty_vs_sampled | 44 | 440000 | 117104 | 34045 | 0 | 76676 |
| census13 | nominal | sampled_vs_sampled | 231 | 2310000 | 602354 | 184870 | 0 | 425684 |
| census13 | pess | sampled_vs_sampled | 276 | 2760000 | 1054847 | 0 | 0 | 0 |
| dmv11 | nominal | certainty_vs_sampled | 44 | 440000 | 82431 | 69648 | 0 | 85216 |
| dmv11 | nominal | sampled_vs_sampled | 231 | 2310000 | 453040 | 334535 | 0 | 412765 |
| dmv11 | pess | sampled_vs_sampled | 276 | 2760000 | 1071735 | 0 | 0 | 0 |
| power7 | nominal | certainty_vs_sampled | 44 | 440000 | 67985 | 89304 | 0 | 104323 |
| power7 | nominal | sampled_vs_sampled | 231 | 2310000 | 293555 | 548452 | 0 | 637306 |
| power7 | pess | fully_enumerated_pairs | 15 | 150000 | 42123 | 0 | 0 | 0 |

No `ID sequence same, Q-error changed` pair was observed in the checked pair classes.
This is a finite sample/enumeration statement about the listed pair classes, not a causal result or a claim about every one of the 120 possible five-object orders.


## Recurrent Test IDs entering or leaving the high-error tail

For each set, the IDs below recur most often among paired entrant/exit events; ties are ordered by Test index. They identify sample-level cases for inspection, not population-wide tail probabilities.

| Dataset | Policy | Most recurrent entrants (ID × order pairs) | Most recurrent exits (ID × order pairs) |
|---|---|---|---|
| forest10 | nominal | `arecel:forest10:test:004544` × 19, `arecel:forest10:test:000115` × 15, `arecel:forest10:test:000171` × 15, `arecel:forest10:test:005199` × 15 | `arecel:forest10:test:001848` × 19, `arecel:forest10:test:006832` × 19, `arecel:forest10:test:008650` × 19, `arecel:forest10:test:000743` × 18 |
| forest10 | pess | — | — |
| census13 | nominal | `arecel:census13:test:000102` × 14, `arecel:census13:test:000278` × 14, `arecel:census13:test:000324` × 14, `arecel:census13:test:000382` × 14 | `arecel:census13:test:000230` × 14, `arecel:census13:test:000257` × 14, `arecel:census13:test:000270` × 14, `arecel:census13:test:000273` × 14 |
| census13 | pess | — | — |
| dmv11 | nominal | `arecel:dmv11:test:000066` × 17, `arecel:dmv11:test:000112` × 17, `arecel:dmv11:test:000194` × 17, `arecel:dmv11:test:000343` × 17 | `arecel:dmv11:test:000013` × 17, `arecel:dmv11:test:000152` × 17, `arecel:dmv11:test:000169` × 17, `arecel:dmv11:test:000309` × 17 |
| dmv11 | pess | — | — |
| power7 | nominal | `arecel:power7:test:000182` × 12, `arecel:power7:test:001177` × 12, `arecel:power7:test:001603` × 12, `arecel:power7:test:002173` × 12 | `arecel:power7:test:006898` × 21, `arecel:power7:test:000487` × 17, `arecel:power7:test:000551` × 17, `arecel:power7:test:004372` × 17 |
| power7 | pess | — | — |

## Query-level examples for Census13 and DMV11

### census13

**nominal** — all eligible order pairs are grouped by design in the table above; anchor-based tail diagnostics use `census13-nominal-000-fixed`.

- **MCV ID sequence changed while Q-error tied (certainty_vs_sampled):** `arecel:census13:test:000001`; `census13-nominal-000-fixed` Q-error 1 → `census13-nominal-002-srswor` 1 (tie). Selection sequence `['e01_05', 'e02_03', 'e04_06']` → `['e06_08', 'e02_03', 'e01_05']`; estimate sequence `['e01_05', 'e02_03', 'e04_06']` → `['e06_08', 'e02_03', 'e01_05']`; per-candidate numeric MCV estimate values changed: `True`.
- **MCV ID sequence and Q-error both changed (certainty_vs_sampled):** `arecel:census13:test:000000`; `census13-nominal-000-fixed` Q-error 1.67666871 → `census13-nominal-002-srswor` 2.44464286 (higher). Selection sequence `['e02_03', 'e04_06']` → `['e06_08', 'e02_03']`; estimate sequence `['e02_03', 'e04_06']` → `['e06_08', 'e02_03']`; per-candidate numeric MCV estimate values changed: `True`.
- **MCV ID sequence changed while Q-error tied (sampled_vs_sampled):** `arecel:census13:test:000001`; `census13-nominal-002-srswor` Q-error 1 → `census13-nominal-003-srswor` 1 (tie). Selection sequence `['e06_08', 'e02_03', 'e01_05']` → `['e02_03', 'e01_05', 'e04_06']`; estimate sequence `['e06_08', 'e02_03', 'e01_05']` → `['e02_03', 'e01_05', 'e04_06']`; per-candidate numeric MCV estimate values changed: `True`.
- **MCV ID sequence and Q-error both changed (sampled_vs_sampled):** `arecel:census13:test:000000`; `census13-nominal-002-srswor` Q-error 2.44464286 → `census13-nominal-003-srswor` 1.67666871 (lower). Selection sequence `['e06_08', 'e02_03']` → `['e02_03', 'e04_06']`; estimate sequence `['e06_08', 'e02_03']` → `['e02_03', 'e04_06']`; per-candidate numeric MCV estimate values changed: `True`.

**pess** — all eligible order pairs are grouped by design in the table above; anchor-based tail diagnostics use `census13-pess-000-srswor`.

- **MCV ID sequence changed while Q-error tied (sampled_vs_sampled):** `arecel:census13:test:000000`; `census13-pess-000-srswor` Q-error 1.63219076 → `census13-pess-001-srswor` 1.63219076 (tie). Selection sequence `['e07_12', 'e02_03', 'e04_06']` → `['e02_03', 'e07_12', 'e04_06']`; estimate sequence `['e07_12', 'e02_03', 'e04_06']` → `['e02_03', 'e07_12', 'e04_06']`; per-candidate numeric MCV estimate values changed: `False`.

### dmv11

**nominal** — all eligible order pairs are grouped by design in the table above; anchor-based tail diagnostics use `dmv11-nominal-000-fixed`.

- **MCV ID sequence changed while Q-error tied (certainty_vs_sampled):** `arecel:dmv11:test:000004`; `dmv11-nominal-000-fixed` Q-error 1 → `dmv11-nominal-002-srswor` 1 (tie). Selection sequence `['e00_05', 'e02_03', 'e04_07']` → `['e02_03', 'e00_05', 'e04_07']`; estimate sequence `['e00_05', 'e02_03', 'e04_07']` → `['e02_03', 'e00_05', 'e04_07']`; per-candidate numeric MCV estimate values changed: `False`.
- **MCV ID sequence and Q-error both changed (certainty_vs_sampled):** `arecel:dmv11:test:000006`; `dmv11-nominal-000-fixed` Q-error 1.13741168 → `dmv11-nominal-002-srswor` 1.48506919 (higher). Selection sequence `['e00_05', 'e01_04', 'e02_03']` → `['e02_03', 'e00_05', 'e04_07']`; estimate sequence `['e00_05', 'e01_04', 'e02_03']` → `['e02_03', 'e00_05', 'e04_07']`; per-candidate numeric MCV estimate values changed: `True`.
- **MCV ID sequence changed while Q-error tied (sampled_vs_sampled):** `arecel:dmv11:test:000000`; `dmv11-nominal-002-srswor` Q-error 1.42736267 → `dmv11-nominal-003-srswor` 1.42736267 (tie). Selection sequence `['e00_05', 'e01_04']` → `['e01_04', 'e00_05']`; estimate sequence `['e00_05', 'e01_04']` → `['e01_04', 'e00_05']`; per-candidate numeric MCV estimate values changed: `False`.
- **MCV ID sequence and Q-error both changed (sampled_vs_sampled):** `arecel:dmv11:test:000006`; `dmv11-nominal-002-srswor` Q-error 1.48506919 → `dmv11-nominal-003-srswor` 1.13741168 (lower). Selection sequence `['e02_03', 'e00_05', 'e04_07']` → `['e02_03', 'e01_04', 'e00_05']`; estimate sequence `['e02_03', 'e00_05', 'e04_07']` → `['e02_03', 'e01_04', 'e00_05']`; per-candidate numeric MCV estimate values changed: `True`.

**pess** — all eligible order pairs are grouped by design in the table above; anchor-based tail diagnostics use `dmv11-pess-000-srswor`.

- **MCV ID sequence changed while Q-error tied (sampled_vs_sampled):** `arecel:dmv11:test:000004`; `dmv11-pess-000-srswor` Q-error 1 → `dmv11-pess-001-srswor` 1 (tie). Selection sequence `['e00_05', 'e02_03', 'e08_10', 'e06_07']` → `['e06_07', 'e00_05', 'e02_03', 'e08_10']`; estimate sequence `['e00_05', 'e02_03', 'e08_10', 'e06_07']` → `['e06_07', 'e00_05', 'e02_03', 'e08_10']`; per-candidate numeric MCV estimate values changed: `False`.

## Interpretation and paper-use boundary

**Safe as a scoped descriptive statement:** on the frozen PostgreSQL 16.14 build, Issue #99 train-only selected sets, fixed ANALYZE samples/statistics target, and official 10,000-query Test workloads, sampled global OID-order configurations show query-level Q-error and MCV diagnostic variation. The tables give paired associations and concrete diagnostic traces for these exact physical configurations.

**Not established:** that OID order or a particular MCV event caused a Q-error change; that MCV diagnostics fully mediate planner estimates; that PostgreSQL randomly assigns OIDs; that the observed sample extrema are global worst cases; that the paired query-order counts are independent or population estimates; or that results generalize beyond these frozen builds, sets, data, and sampled orders. No causal intervention isolated one statistic or planner mechanism.

No query-level average was converted to a P95. No resource set, Test query, or order was selected or replaced based on these observations. No new physical experiment was run.

## Reproduction

From the repository Worktree with the frozen environment initialized:

```bash
PYTHONPATH=src:experiments/arecel-test-generalization-issue101:experiments/oid-order-stress-test-issue105:experiments/oid-uniform-priority-issue107 \
  ../../.venv/bin/python -B experiments/oid-order-attribution-issue125/analyze_issue125.py \
  --output experiments/oid-order-attribution-issue125/findings.md
```

The command reads the pinned runtime archives and writes only the derived findings report at the requested output path. It does not start PostgreSQL or modify run artifacts.
