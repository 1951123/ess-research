# Issue #84 paper draft: author self-review

This review accompanies the complete manuscript draft in `main.tex`. It is
an academic scope check, not a claim that the work has passed external peer
review.

**Readiness recommendation: FOCUSED-GAP.** The manuscript is complete for
end-to-end researcher review. Before submission, the focused remaining gap is
a broader claim-level novelty comparison, especially against recent robust
query-plan methods and practical workload-aware statistics advisors. This
gap does not require reopening the frozen experiments to produce a reviewable
draft.

## Innovation and positioning

The strongest current contribution is a clear separation between a global,
unordered resource decision and task-dependent families of complete
estimation schemes, with Nominal, shared-policy Joint, and task-wise PESS
objectives stated under one interface. The PostgreSQL matching instance
makes that boundary concrete, and the frozen studies show both a
policy-sensitive decision and cases where optimization removes modeled
ambiguity. The paper does not establish a new general-purpose algorithm or
an empirical PESS advantage.

Novelty remains the largest publication risk. The repository's prior-art
audit found the previously considered structural and algorithmic claims to
be classical ingredients or special cases, and did not support novelty claims
for them (`notes/stage1d-proof-priorart/audit-report.md`). The current draft
therefore limits its theory claims to model-internal statements and does not
claim a new matching result. Its broader framing and empirical synthesis
still need comparison against a more complete literature review before a
submission claim of novelty is defensible.

## Theory and model limits

- The pointwise Nominal--Joint--PESS hierarchy follows from set inclusion.
  The conflict-free lemma is correct under its stated singleton-family
  premise, but is sufficient rather than necessary.
- The generic problem retains nonadditive maintenance, complete schemes, and
  a prescribed nonempty `Gamma_i(M)`. A real-system worst-case guarantee
  still requires `R_i(M) subseteq Gamma_i(M)` and aligned estimator and loss
  definitions; the PostgreSQL evidence does not establish this generally.
- The PostgreSQL correspondence is conditional on the restricted PostgreSQL
  16.14 selector path. Abstract priority-order completeness does not imply
  all orders are physically realizable in a fixed catalog.
- Positive pre-clamp log loss and multiplicative factor composition are
  modeling assumptions. The composition check is mixed, and PostgreSQL's
  rounded/clamped `Plan Rows` is a separate outcome.
- The fixed-set hardness observation cites a classical minimum maximal
  matching result. The outer SUBSET SUM construction is limited to direct
  signed-log coefficient representations. Neither should be presented as a
  new general complexity theorem.

## Experimental limits

- Issue #23 uses six construction-sample Forest10 tasks and one-unit object
  costs. Its reference calculation is exact only for the recorded
  18-decimal rationalized log inputs. The 720 Joint orders are abstract
  scenarios, not verified PostgreSQL catalog orders.
- Issue #38 covers 60 frozen query IDs with two repeated PostgreSQL
  measurements. PESS has a small higher mean error than Nominal, but also a
  lower median, the same P90 and maximum, and 11 query-level improvements.
  This is descriptive, not a significance or population claim. The PESS
  selected `e01`, which lacked an effective MCV payload in the frozen sample.
- Forest10 and Census13 valid-only models return coincident Nominal and PESS
  optima at the tested budgets. They provide no treatment contrast. Their
  model versions differ, and Census13's PESS solution was reused rather than
  reoptimized in its ten-order Nominal run.
- Forest10 `Plan Rows` results compare the common selected deployments with
  Empty. The official test split has template overlap and earlier exposure;
  no MCV selection trace, latency, or physical maintenance cost was measured.
- Raw graph ambiguity is not actual catalog eligibility. The strict syntax
  cohorts and frozen payload observations are much smaller and answer
  different questions.

## Checks completed for this draft

- External publication metadata in `references.bib` was checked against
  publisher or DOI records. Versioned repository reports and PostgreSQL
  16.14 source are cited separately as evidence sources.
- The current VLDB paper template was compiled with the manuscript-specific
  sources. Final build: **13 pages total, pages 1--12 main text and page 13
  references**; letter size. The compile used the standard `pdflatex`,
  `bibtex`, `pdflatex`, `pdflatex` sequence. BibTeX emitted no warnings; the
  final LaTeX pass had no undefined citations/references or overfull boxes.
  No new database experiment, model refit, or optimization solve was run for
  this manuscript.

## Exhibit-to-source map

- Figure 1 is the generic model boundary defined in `main.tex`; it makes no
  empirical claim.
- Figure 2 is the directly traced PostgreSQL 16.14 path fixture
  (`pgtrace2026`); the equality-gate topology table is from `pg_gate2026`.
- Figure 3 is a model-only illustration of the strict Joint/PESS gap and the
  conflict-free certificate; its values are the mathematical example in the
  manuscript, not experimental measurements.
- Figure 4 is the 60-query-ID paired held-out summary from Issue #38
  (`issue38_heldout`), with two repetitions averaged before the harm/better/tie
  counts.
- The related-work table cites the listed papers and EDB product documentation.
  The provenance table points to the versioned reports for experimental
  setup and scope.
- The six-task anchor, payload/composition, and exact-decision tables use
  Issues #23 and #38 (`issue23_forest10`, `issue38_heldout`).
- The raw-graph ambiguity and valid-only objective tables use Issues #59,
  #64, and #71 (`issue59_structure`, `issue64_forest10`, `issue71_census13`).
- The Plan Rows table uses the frozen Forest10 test report
  (`issue64_forest10_test`); it is a deployment-versus-Empty comparison,
  not a Nominal-versus-PESS treatment contrast.

## Review priorities

1. Decide whether the scoped formulation-and-evidence synthesis is sufficient
   for a regular research paper after a broader novelty review.
2. Challenge the real-scheme coverage assumptions and the practical
   relevance of the pairwise MCV eligibility gate.
3. Treat the six-task adverse example as hypothesis-generating until a
   separate, adequately powered, independently held-out study can compare
   deployments whose selected sets differ.
4. Require calibrated maintenance measurements and estimator traces before
   any claim about physical cost, real worst-case guarantees, or advisor
   deployment recommendations.
