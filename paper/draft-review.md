# Issue #84 paper draft: author self-review

This review accompanies the complete manuscript draft in `main.tex`. It is
an academic scope check, not a claim that the work has passed external peer
review.

**Readiness recommendation: FOCUSED-GAP.** The manuscript is complete for
end-to-end researcher review. The remaining gap is one bounded claim-level
novelty comparison: test whether the selected-set conflict-free certificate
and its evidence add to automatic statistics selection/composition and robust
physical-design/query-optimization work. This comparison needs separate
researcher approval before it is treated as a new work item; it does not
require reopening frozen experiments to produce this reviewable revision.

## Innovation and positioning

The manuscript's specific testable claim is that conflict in the selected
resource set gives a decision-level certificate that raw ambiguity across
the full candidate universe cannot provide by itself. Under the stated
model, a conflict-free Nominal optimum is also optimal for Joint and PESS.
The larger frozen fits meet this condition and have coincident selections;
the six-task model has a conflict-bearing Nominal optimum and a distinct,
nonunique PESS optimum. This is model-level evidence, not a general empirical
law or an empirical PESS advantage.

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
  measurements. The exact B=3 PESS/Joint optimum has four tied sets,
  including `{e34}`; the held-out summary for `{e01,e34}` is exactly the same
  as for `{e34}`. The displayed PESS deployment has one effective payload,
  versus three for Nominal. Its small higher mean, lower median, same P90 and
  maximum, and 11 query-level improvements are descriptive contrasts between
  different as-built sets, not a causal policy effect or price of robustness.
- Forest10 and Census13 valid-only models return coincident Nominal and PESS
  optima at the tested budgets. They provide no treatment contrast. Their
  model versions differ, and Census13's PESS solution was reused rather than
  reoptimized in its ten-order Nominal run.
- Forest10 `Plan Rows` results compare the common selected deployments with
  Empty. The official test split has template overlap and earlier exposure;
  no MCV selection trace, latency, or physical maintenance cost was measured.
- Raw graph ambiguity is not actual catalog eligibility. Issue #59 archives
  marginal raw-conflict and strict-eligibility counts, not their query-level
  intersection; that intersection is unknown. Neither count measures actual
  catalogs with multiple simultaneously eligible, built MCV objects.

## Checks completed for this draft

- Review-driven revision rebuilt locally with `latexmk` 4.83 and TeX Live
  2023. The PDF has 13 pages total, letter size; the final pass has no
  undefined citations/references, BibTeX warnings, or overfull boxes.
  Underfull boxes and the template's column-balance warning remain. The
  repository CI pins TeX Live 2026 and has not yet run on this revised head.
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

1. With researcher approval, complete the bounded comparison of the
   selected-set certificate against the closest statistics-selection,
   statistics-composition, and robust physical-design/query-optimization
   work; until then, regular-paper novelty remains open.
2. Challenge the real-scheme coverage assumptions and the practical
   relevance of the pairwise MCV eligibility gate.
3. Treat the six-task PostgreSQL deployment contrast as descriptive and
   noncausal until a separate, adequately powered, independently held-out
   study compares deployments with controlled effective payloads.
4. Require calibrated maintenance measurements and estimator traces before
   any claim about physical cost, real worst-case guarantees, or advisor
   deployment recommendations.
