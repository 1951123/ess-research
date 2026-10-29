# PVLDB page-limit audit for PR #131

## Build identity

- Paper branch: `paper/ess-formulation-audit-130`.
- Baseline commit: `72409f296dec95c0b49d6d242efbc9c82467e5e9`.
- Baseline `paper/main.tex` SHA-256: `cc8c04334c77f1f7679525bf1296bdfb150daf394ca54aef44a3a9a12d180db4`.
- First page-limit revision (`e725363`) `paper/main.tex` SHA-256: `0895078a4a3a5f8682766c2b499e16b24cefb3890f766ec099709b1c6bbbfea8`.
- Compiler: pdfTeX 1.40.25 (TeX Live 2023/Debian); latexmk 4.83.
- PVLDB package: `paper/pvldb.sty`, v1.0 dated 2026-07-06, SHA-256 `52ad3948f3231b31d2ac90f470c1759e7f96add7b577ec4e267dfbdc87fc4eb2`.
- ACM class SHA-256: `2f949e6e3f2a79f2cdc218b9dcdbaa7dd451adb4ee0be1af6dc7ebe00b318ea7`.
- Reference format file SHA-256: `0590db3b8d255a3af91982ab710f3ace5fcaa52434020c9af8a4f141b00b68f3`.
- References are embedded in `main.tex` via `thebibliography`; there is no external `.bib` input.
- Build command, run from `paper/` with output outside the worktree:

  ```sh
  latexmk -pdf -interaction=nonstopmode -halt-on-error -file-line-error \
    -outdir="$ESS_RUNTIME_PARENT/ess-research/paper-page-limit-131/iteration-1" main.tex
  ```

## Page-limit result

| Build | Total PDF pages | Last body page | References begin | Result |
|---|---:|---:|---:|---|
| Baseline `72409f2` | 13 | 13 | 13 | Fail: page 13 still contains body text |
| Edited source | 12 | 12 | 12 | Pass: body ends on page 12; references follow it |

Both PDFs are US Letter. The baseline PDF SHA-256 is `35113530cd0001f83ef5eeaee7409868af7178647491a39bc04169a1a5683875`; the first page-limit revision PDF SHA-256 is `13b98f82b60286849a3dcc4fd0f4e562b7382e2c0ca5c7e7642d834541addf2a`.

As an approximate length comparison, `pdftotext -raw` output was truncated at the References heading and whitespace-separated tokens counted. This gives 11,188 baseline and 9,753 edited body tokens, a reduction of about 12.8%. This PDF-extraction count includes running/page-number text and extracted math tokens; it is not a source-word count.

## Semantic and visual checks

- Compression removed repeated motivation and repeated caveats, shortened long protocol/results prose, and consolidated the abstract and introduction. The section structure remains intact; no theory or experiment section was removed.
- All 9 proposition environments, 9 proof environments, 13 equation environments, 4 align environments, 7 table environments, and the figure environment are byte-identical to the baseline source. The 17 labeled display equations are unchanged.
- The experimental tables and values are unchanged, including the six Issue #133 P95 values: Forest10 ALL01/ALL02/matched B5 = 15.00/15.00/14.00; DMV11 = 57.61/67.53/36.00.
- The edited prose retains the limits on the PostgreSQL matching correspondence, model-risk versus physical Q-error, counterfactual OID orders, fixed-configuration ALL-vs-B5 comparisons, Forest10's 23 populated and 22 NULL MCV payloads, the Forest10 B5 diagnostic gap, and the absence of proven blocker causality. Results that favor different strategies on different workloads remain in the paper.
- Rendered pages 1, 7–12 were visually inspected. Abstract/Introduction, the protocol and theory pages, Tables 5–8, the results/threats/conclusion flow, and references are readable; no clipping, overlap, or misplaced float was observed. The last body text is on page 12, immediately before the References heading.
- The ALL-vs-B5 table has an explicit in-text reference and resolves to Table 6 on page 10.
- No undefined citation or reference was reported by the final LaTeX log. The final log has one 3.01 pt overfull horizontal box on an unchanged equation line, one 1.52 pt overfull vertical box, and underfull-box warnings. These are minor; visual inspection found no corresponding clipping or collision.

## Outcome

**PVLDB 12-page body limit: PASS.** The PDF is 12 pages total, and body text ends on page 12 before the references. The build and layout result does not establish compliance with any other submission requirement.

## Review 5693284366 follow-up

- Added a blank line before the Experimental Protocol subsection and whitespace after the Related Work citation period; checked for the same fused-command and citation-spacing patterns elsewhere.
- Narrowed the Introduction contribution wording to formulation-specific labeled-matching results. Related Work now states that the realizability test is used as a feasibility characterization, makes no novelty claim for it as an algorithm, and leaves its relation to prior recognition problems open.
- The researcher confirmed **Regular Research** as the intended category. The [official VLDB 2027 submission guidelines](https://www.vldb.org/2027/submission-guidelines.html) require a category suffix for EA&B, SDS, and Vision papers, but not Regular Research; the title therefore remains unchanged.
- A fresh build from the review-updated source used the same `latexmk` options, with output directed to `$ESS_RUNTIME_PARENT/ess-research/pr131-review-5693284366/20261029T053514Z/`. The build succeeded; the PDF has 12 pages, body ends on page 12, and References begins on page 12 after the final body lines. The final source SHA-256 is `e6cb4f217ec9626677b0fa9204c3faa84ad7358a7d6a636927025da3faaca57c`; the rebuilt PDF SHA-256 is `7fe0ec967b71793be63f0c4a72116fa71b458b1f3320ab7245606ab9953aae8d`. The extracted body has about 9,779 whitespace tokens, 12.6% below the baseline using the same counting method.
- Proposition, proof, equation, align, table, tabular, and figure blocks remain byte-identical to the pre-review compressed source. No undefined citation/reference was reported. Pages 7 and 10–12 were re-rendered and inspected; no clipping or overlap was observed. The small overfull-box warnings noted above remain, without visible layout damage.
