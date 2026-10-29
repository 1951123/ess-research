# LaTeX build and PDF inspection

## Source and toolchain identity

- Paper commit: `9f9773d09c9b4d9224345c362723c320c5e71b46` (detached, clean snapshot).
- `paper/main.tex` SHA-256: `16b60239ba12f48205b6860176edebed9ca112e3ae59c79ae78eb762be085746`.
- PVLDB template revision recorded in `paper/TEMPLATE_REVISION`: `39c95f5c6fcbe652a83be24e4eff8f2134cd3fbc`.
- `paper/pvldb.sty` SHA-256: `52ad3948f3231b31d2ac90f470c1759e7f96add7b577ec4e267dfbdc87fc4eb2`.
- `paper/acmart.cls` SHA-256: `2f949e6e3f2a79f2cdc218b9dcdbaa7dd451adb4ee0be1af6dc7ebe00b318ea7`.
- `paper/ACM-Reference-Format.bst` SHA-256: `0590db3b8d255a3af91982ab710f3ace5fcaa52434020c9af8a4f141b00b68f3`.
- Toolchain: TeX Live 2023/Debian; pdfTeX 1.40.25; latexmk 4.83; BibTeX 0.99d; Poppler/pdfinfo and pdftoppm 24.02.0.
- Bibliography: embedded `thebibliography` in `main.tex` (starts at source line 1917); there is no external `.bib` input to identify or resolve.
- Build output and rendered previews: `$ESS_RUNTIME_PARENT/ess-research/issue133/paper-audit-20261029-9f9773d/` (outside the paper source tree).
- PDF SHA-256: `e50d395ac85375b9624ff765e2f1c37300220059bf253e6ca5d07e8a796ea43f`.

## Build and reference checks

Command, run from the exact snapshot's `paper/` directory with an external output directory:

```bash
latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error \
  -outdir="$build" main.tex
```

Exit status was 0. The document compiled to a 13-page, 612 × 792 pt Letter PDF (583,350 bytes, PDF 1.5). `main.aux` resolves `sec:all-versus-selected` to subsection 6.3 on page 10 and `tab:all-b5` to Table 6 on page 10. No undefined citation or reference was found. The bibliography is in source, so a BibTeX run is not needed; `latexmk` resolved cross-references over its LaTeX passes.

Warnings in the final LaTeX log:

- Overfull hbox 3.00798 pt at source line 493 (outside the new section).
- Overfull hbox 1.26894 pt at source lines 1503–1517 (new section).
- Underfull hboxes at source line 862 and bibliography lines 1953–1957 and 1998–2002.
- Underfull output-page vbox warnings and `\balance` warning (“called in second column”).

There are no undefined-reference/citation warnings. The small overfulls did not produce visible clipping in the inspected pages.

## Visual review

Rendered page previews for all 13 pages were generated externally. Pages 1, 2, 10, 11, 12 and 13 received detailed visual inspection, including the requested Abstract, Introduction, new section/table, adjacent text and final reference page.

- Abstract and Introduction additions are complete and readable.
- Table 6 (`tab:all-b5`) is legible and within the column. It appears above the new subsection heading at the bottom of page 10; there is no collision or clipping.
- Section 6.3 begins on page 10 and continues on page 11. The paragraph with the small overfull warning is readable.
- No missing math glyph or special-character defect was seen.
- Page 13 contains the end of the body text and the beginning/continuation of references. The reference tail fits, with no clipped final entry.
- No float overlays or visually broken column transitions were observed.

**Visual layout result: PASS with minor TeX warnings.**

## Submission page-limit result

The official VLDB 2027 submission guidance says Regular Research and Experiment, Analysis & Benchmark papers are limited to 12 pages excluding references; Scalable Data Science and Vision have lower limits. It says only references may extend the page count. This PDF has substantive body text on page 13, so it exceeds even the largest listed research-category body limit. The current title does not identify a category; if submitted as Experiment, Analysis & Benchmark, the current rule also requires that category suffix in the title. Therefore:

- Template/build correctness: PASS.
- Readable visual rendering: PASS with minor warnings.
- Current VLDB 2027 page-limit compliance: **FAIL**.

The finding follows the current [VLDB 2027 Submission Guidelines](https://www.vldb.org/2027/submission-guidelines.html) and [Formatting Guidelines](https://www.vldb.org/2027/formatting-guidelines.html). The paper should be shortened and rebuilt before being treated as submission-ready. This audit does not change the paper.

## Text consistency and actionable paper findings

- `paper/main.tex:56–62` (Abstract): Forest10 15 vs 14; DMV11 57.61 vs 36.00; DMV11 order 57.61 to 67.53; fixed-configuration and non-blocker limitation. Consistent with raw recomputation.
- `paper/main.tex:96–109` (Introduction): same results; explicitly says shared objects retain relative OID priority and this does not establish that installing more statistics is always harmful. Consistent.
- `paper/main.tex:1450–1465` (`sec:all-versus-selected`): describes candidate set sizes, two frozen ALL orders, B5 order projected from ALL01, matching shared-object priority, and the common 10,000-query controls. Consistent with protocols and catalog audits.
- `paper/main.tex:1467–1488` (`tab:all-b5`): all six P95/mean cells agree after rounding with the independent recomputation.
- `paper/main.tex:1490–1501`: DMV11 and Forest10 differences/counts agree with the recomputation. It does not turn the two orders into a permutation expectation.
- `paper/main.tex:1503–1517`: correctly distinguishes Forest10 NULL MCV payloads from object creation failure and preserves the #136 original diagnostics limitation; correctly says DMV11 records passed their checks. The sentence at lines 1515–1516 stating an independent byte reread is pending is stale and should be updated after incorporating this audit.
- `paper/main.tex:1518–1525`: correctly says the candidate ranking/predicate-consumption/blocker chain was not recorded and does not attribute the observed changes to a proven “bad object blocks good object” mechanism.
- The Abstract and new table report per-arm test-workload P95s; neither labels them as an all-order mean. The paper does not claim that PESS avoids all degradation or that adding more objects must monotonically worsen error.

No numerical inconsistency was found in the audited additions. The stale pending-reread sentence and page limit are the concrete fixes before final integration.
