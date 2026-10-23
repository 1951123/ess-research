# Issue #84 paper draft: v3 self-review

This self-review records the v3 response to the scientific-positioning review
in Issue #86. It is an author-side scope and evidence check, not an
independent referee decision.

**Thesis: REFINE. Technical novelty: NOT YET sufficiently supported for a
SIGMOD/PVLDB/ICDE regular research paper.** The paper now centers the
information boundary between prescribed complete-scheme admissibility,
estimator-policy knowledge, and scheme-loss prediction. This makes the
question coherent and falsifiable; it does not establish that the resulting
database contribution clears the regular-paper novelty threshold.

## What changed in v3

- Rewrote the Abstract and Introduction around the question: when can an
  advisor use knowledge of admissible complete schemes without knowing the
  actual selection policy to make budgeted resource decisions?
- Separated requested statistics, catalog objects, effective MCV payloads,
  eligibility in a complete scheme, policy-selected schemes, and resulting
  estimates/losses.
- Stated that knowing Gamma_i(M) does not reveal counterfactual scheme
  losses. An executable instance also needs an estimator oracle, measurements,
  or an explicitly stated loss approximation.
- Distinguished a known but uncontrollable deterministic policy (Nominal),
  one unknown shared policy (Joint-Robust), and taskwise admissibility-only
  uncertainty (PESS). PESS is described as a conservative risk criterion,
  not a PostgreSQL adversary.
- Expanded Related Work with claim-level comparisons to Chaudhuri–Narasayya
  (ICDE 2000), Bruno–Chaudhuri (SIGMOD 2002 and 2004), MAXENT (SIGMOD 2006),
  Babcock–Chaudhuri (SIGMOD 2005), El Gebaly–Aboulnaga (EDBT 2008),
  Nohadani–Sharma (SIAM J. Optimization 2018), AutoCE (ICDE 2023), and EDB
  Statistics Advisor/PostgreSQL documentation. Added source-verified AutoCE
  and PostgreSQL 16 documentation entries.
- Added an active-MCV-only restriction corollary from the frozen Issue #23
  exact B=3 results. It lists all four original PESS ties and establishes
  that only {e34} remains optimal in the restricted universe, while the
  unique Nominal optimum remains {e12,e23,e34} and has a strictly larger
  PESS value. This is a logical inheritance argument, not a new enumeration
  or physical result.
- Kept the conflict-free result as an elementary sufficient certificate.
  The text now says conflict alone is neither necessary nor sufficient for a
  policy-sensitive optimal decision.
- Retained the v2 corrections on physical outcomes, raw graph ambiguity,
  cohort counts, frozen objective versions, and noncausal interpretation.

## Issue #86 objections

| Review point | v3 response | Status |
|---|---|---|
| #6367455608: REFINE the information-boundary thesis | Abstract, Introduction, Model, and Discussion distinguish admissibility, policy, and losses. | Addressed |
| Unknown policy is not the same as uncontrollable policy | Nominal allows a known deterministic policy even if the advisor cannot control it. | Addressed |
| Admissibility does not supply counterfactual estimates/losses | Model input requirements and the calibrated-loss limitation are explicit. | Addressed as a limitation; predictive validity remains open |
| Prior-work novelty and AutoCE comparator | Named primary works are compared by decision owner, uncertain quantity, effect of resource availability, and remaining ESS distinction. Metadata was checked against publisher or primary records. | Comparison added; novelty remains unproven |
| Conflict-free certificate is elementary; conflict does not imply sensitivity | Labeled as a sufficient certificate and explicitly disclaimed necessary/sufficient implications from conflict alone. | Addressed |
| Larger valid-only cohorts have coincident optima and no treatment contrast | Discussion explains that agreement means no decision value from changing policy objective in those tested models/budgets; raw ambiguity is not realized PG ambiguity. | Addressed |
| #6367624297: active-MCV-only candidate restriction | Exact archived optima imply model-level separation survives restriction to A={e12,e23,e34}; all four full-universe PESS ties are stated. | Addressed by derivation; not rerun |
| Physical effect, real-scheme coverage, or causal PESS benefit | Not claimed. The selected held-out sets have different effective payloads and the {e01,e34} and {e34} summaries are identical. | Remains unsupported, correctly scoped |

## Novelty assessment

The cited prior work controls neighboring decisions directly: statistics advisors
select resources; Bruno–Chaudhuri and MAXENT specify ways to use or combine
statistics; robust query optimization and physical design model other
uncertainties; decision-dependent robust optimization already studies
decision-shaped uncertainty sets; AutoCE selects a learned estimator model.
The current review did not verify an exact antecedent to ESS's full
advisor/admissibility/policy triple. That absence is not evidence of priority.

The remaining ESS distinction is a formulation of an external statistics
advisor that receives a resource-dependent family of complete admissible
estimator schemes plus scheme-loss inputs, while the selection policy may be
known, shared-but-unknown, or unavailable beyond taskwise admissibility.
The PostgreSQL maximal-matching construction is conditional, and its
conflict-free certificate is elementary. The exact six-task separation is a
small measured-input model result, not a new general theorem or solver
contribution. The restricted-universe corollary removes one artifact concern
but is an inheritance argument, not an independent novelty claim.

**Assessment:** The thesis is coherent and database-relevant, but this
manuscript does not yet demonstrate sufficient technical novelty or
externally meaningful decision value for a regular research-paper
submission. No first claim is made.

## Most consequential remaining scientific gap

> Can an advisor obtain sufficiently faithful counterfactual complete-scheme
> loss estimates to make externally meaningful resource decisions under
> unknown estimator policy?

The optimizer needs defensible Gamma_i(M) families and a loss value (or
exact loss-maximum oracle) for every admissible counterfactual scheme across
candidate resource sets. In the frozen calibration, singleton corrections
are measured and multiplied by an explicit approximation. The overlapping
composition residuals show that this is not universally faithful to
PostgreSQL. Knowing admissibility does not fix this gap. Resolving it would
require a separately scoped validation and decision-value study; v3 performs
no such study.

## Evidence and nonclaims retained

- The generic maintenance function remains nonadditive; unit-cost sums are
  experiment-specific proxies.
- The positive pre-clamp absolute log loss requires positive estimates and is
  distinct from rounded/clamped Plan Rows, physical maintenance cost, and
  query runtime.
- Gamma_i(M) is prescribed; R_i(M) is physically reachable. No general
  inclusion or equality is established.
- The restricted PostgreSQL 16.14 maximal-matching correspondence is
  conditional on the stated built-payload, eligibility, and execution-path
  assumptions. Abstract priority-order coverage does not imply all orders
  occur in a fixed catalog.
- The Issue #23 exact rational reference is exact for its stored
  18-decimal rationalized inputs. It is separate from floating-point
  PostgreSQL observations and solver-reported optimality.
- The B=3 PESS/Joint model has four ties:
  {e01,e34}, {e01,e34,e56}, {e34}, and {e34,e56}. The displayed
  {e01,e34} set had only e34 with an effective MCV payload.
- Issue #38's approximately +0.024223 held-out mean error difference is
  descriptive, not a causal policy effect or intrinsic price of robustness.
- Forest10/Census13 raw graph ambiguity rates 47.49%/46.27% are distinct
  from syntax-eligible cohorts of 135/58 queries out of 10,000 and do not
  measure realized PostgreSQL ambiguity. The query-level intersection was
  not archived.
- Forest10/Census13 full-valid B<=3 models have coincident Nominal/PESS
  optima and no between-policy treatment contrast. Their loss conventions
  differ, so their objective values are not pooled.
- The held-out Plan Rows comparison uses a frozen test split with template
  overlap and earlier exposure; it does not establish unseen-template
  generalization. It compares deployments with Empty, not a Nominal-versus-
  PESS treatment.
- No new PostgreSQL run, data collection, model fit, official test access,
  large enumeration, B>=4 solve, or HiGHS experiment was performed for v3.

## Build and manuscript length

- Build command: latexmk -pdf -interaction=nonstopmode -halt-on-error
  -file-line-error main.tex, run from paper/. Local environment: Latexmk
  4.83 and TeX Live 2023.
- Final PDF: 14 letter-size pages total; pages 1--13 are main text and page
  14 contains references. The 12-page main-text target was not met after
  adding the claim-level literature comparison and active-MCV restriction
  result; the additional page was retained rather than removing those
  scientific qualifications.
- Final build has no undefined references or citations, BibTeX warnings, or
  overfull boxes. Underfull boxes and the template's column-balance warning
  remain. The new PR-head CI has not yet run.

## Exhibit-to-source map

- Figure 1 is the generic advisor/estimator information boundary.
- Figure 2 and the eligibility table use the versioned PostgreSQL 16.14
  source/fixture reports (pgsource1614, pgtrace2026, pg_gate2026).
- Figure 3 is a model-only illustration of shared versus taskwise risk and
  the sufficient singleton-family certificate.
- Figure 4 and the six-task calibration/results tables cite frozen Issues
  #23 and #38.
- The restricted-universe corollary inherits the exact Issue #23 Fraction
  optima; it adds no observation.
- Larger-workload ambiguity, validity, and Plan Rows displays cite Issues
  #59, #64, and #71 and retain their separate denominators and model versions.
- Related Work citations refer to the primary publication or publisher/
  author-hosted source listed in paper/references.bib.

## Review priority

Keep the draft in review until an independent novelty assessment and a
counterfactual scheme-loss fidelity/decision-value study establish what
external decision benefit the model can support. The latter is the single
most consequential scientific gap; this manuscript revision does not
authorize or conduct that study.
