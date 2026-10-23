# Issue #84 paper draft: v4 self-review

This review records the v3 response to Issue #86 and the targeted editorial
revision following PR #85 review `5630310609`. It is an author-side scope and
evidence check, not an independent novelty decision.

**Recommendation: keep PR #85 Draft. Thesis: REFINE. Technical novelty is
still NOT YET sufficiently supported for a SIGMOD/PVLDB/ICDE regular research
paper.** The paper now states a falsifiable, evidence-scoped claim: policy
information changes the model-selected resource set in the frozen six-task
case at B=3, even after restricting to effective-MCV candidates, while the
two larger valid-only fitted models have coincident Nominal/PESS optima for
the tested B<=3. This is an instance-level result, not evidence of a physical
policy effect or sufficient publication novelty.

## Changes following PR review `5630310609`

- Foregrounded that the B=3 displayed PESS deployment `{e01,e34}` had only
  `e34` with an effective MCV payload, while Nominal `{e12,e23,e34}` had
  three. The held-out summary for `{e01,e34}` equals that for `{e34}`; the
  `+0.024223` comparison is descriptive and does not identify a policy
  effect.
- Clarified the raw ambiguity denominators: 47.49%/46.27% count raw complete
  candidate graphs; strict syntax cohorts contain 135/58 queries out of
  10,000; the per-query intersection and realized PostgreSQL ambiguity are
  unknown.
- Corrected the overlap-composition interpretation. The archived check
  multiplied both created objects even where PostgreSQL selected only one
  overlapping statistic. Residuals 0.1590 and -0.4904 reject that all-created
  product; they do not test the matching-conditioned product over the selected
  matching. The matching-conditioned counterfactual loss prediction remains
  unvalidated, rather than refuted by those residuals.
- Compressed the nonessential six-row anchor and four-topology tables into
  prose, retaining their query/truth values and bounded fixture outcomes.
  Replaced the larger objective table with compact prose retaining all six
  exact objective displays and separate model scales. The manuscript now
  meets the 12-page main-text target.
- The B=5 text distinguishes the displayed representatives (three Nominal,
  two PESS/Joint resources) and notes tied supersets. The Issue #38 table
  caption identifies 60 query IDs, two repetitions, 120 rows, and that
  repetitions are not independent query IDs.
- `pgsource1614` already has year 2026 in the reviewed PR head and cites the
  exact upstream `REL_16_14` tag. The official [PostgreSQL 16.14 release
  notes](https://www.postgresql.org/docs/release/16.14/) date it 2026-05-14;
  no bibliography correction was needed.

## Review responses

| Review point | v4 response | Status |
|---|---|---|
| PR review `5630310609`: distinguish modeled optimum from as-built effective resources | Abstract, Introduction, table interpretation, and Discussion identify the one-payload PESS representative versus three-payload Nominal set, identical `{e01,e34}`/`{e34}` summaries, and noncausal `+0.024223` comparison. | Addressed |
| Raw graph ambiguity versus eligible/realized PostgreSQL ambiguity | First percentage discussion and table labels distinguish all three layers; the archived intersection remains explicitly unknown. | Addressed |
| Tighten a falsifiable central claim and assess novelty | The claim is scoped to one separating six-task exact model, its active-MCV restriction, and two larger coincident-optimum models. It does not establish regular-paper novelty. | Claim sharpened; novelty remains open |
| Matching-conditioned loss fidelity | The prose now distinguishes the all-created product check from the estimator's selected-matching prediction. No archived recalculation or new measurement was performed. | Interpretation corrected; prediction fidelity remains unknown |
| 13 main pages versus 12-page target | Removed redundant tables and consolidated Discussion/Conclusion while retaining result values and qualifications. | Addressed; compile confirms 12 main pages |
| `pgsource1614` year and source tag | Year was already 2026 on reviewed HEAD; exact `REL_16_14` tag is in the source entry. | Already correct; verified against official release notes |
| B=5 set cardinalities and Issue #38 repetition counts | Text gives two versus three displayed resources; caption gives 60 IDs, 120 repeated rows, and the non-independence limitation. | Addressed |

The original Issue #86 comments are also addressed in the v3 responses:
information-boundary thesis, known versus uncontrollable policy,
per-scheme loss inputs, closest-work comparisons, elementary conflict-free
certificate, no conflict-only sensitivity inference, and the active-MCV-only
restriction corollary.

## Novelty and scientific gap

Related Work compares statistics selection and composition, MAXENT, robust
query optimization/physical design, decision-dependent uncertainty, AutoCE,
and practical PostgreSQL advising by decision owner, uncertain quantity,
resource-dependent outcomes, and the limited ESS distinction. It does not
claim a first advisor or a new generic robust-optimization framework. The
active-MCV restriction inherits the archived exact optima and is not a new
theorem or experiment. The six-task separation is a small model result; the
larger full-valid fitted models show no policy contrast at tested budgets.

**Assessment:** The formulation and evidence are clearer, but this manuscript
does not yet establish sufficient technical novelty or external decision
value for a regular research-paper submission.

**Most consequential open question:** Can an advisor obtain sufficiently
faithful counterfactual complete-scheme loss estimates to make externally
meaningful resource decisions under unknown estimator policy?

The optimizer needs defensible `Gamma_i(M)` families and per-scheme losses (or
an exact loss-maximum oracle) across counterfactual resource sets. The frozen
model multiplies measured singleton corrections over an admissible matching.
The one recorded disjoint-pair check is supportive for that observation only;
the reported overlapping-pair residuals compare PostgreSQL with a product of
both created objects after PG selected only one, so they do not validate or
falsify the matching-conditioned prediction. No archive-only recalculation,
new PostgreSQL run, data collection, fitting, official test access, large
enumeration, B>=4 solve, or solver experiment was performed for this revision.

## Evidence boundaries retained

- Generic maintenance remains nonadditive; unit-cost sums are experiment-
  specific proxies.
- Positive pre-clamp absolute log loss requires positive estimates and is
  distinct from finalized Plan Rows, physical maintenance, and runtime.
- Prescribed `Gamma_i(M)` is not asserted equal to or a superset of real
  reachable `R_i(M)`; no real worst-case guarantee follows.
- Exact Fraction results apply to stored rationalized inputs, separately
  from floating-point PostgreSQL values or solver optimality.
- Forest10 and Census13 use different frozen loss conventions; objective
  values are not pooled. Their larger B<=3 Nominal/PESS optima coincide.
- The held-out test has template overlap and prior exposure; it does not
  establish unseen-template generalization.

## Build and manuscript length

- Command: `latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error main.tex`, from `paper/`.
- Environment: Latexmk 4.83, TeX Live 2023.
- Final PDF: **13 letter-size pages total: 12 main text and 1 references page.**
- No undefined citations/references, BibTeX warnings, or overfull boxes.
  Underfull boxes and the ACM template's column-balance warning remain.
- The v3 Lightweight CI run passed. CI for the current v4 head has not yet
  reported a result.

## Review priority

Keep PR #85 Draft. An independent novelty assessment and a separately scoped
validation of matching-conditioned counterfactual loss predictions are still
needed before claiming external decision value or submission readiness.
