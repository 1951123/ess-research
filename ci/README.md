# Lightweight CI for ESS Research

The [GitHub Actions workflow](../.github/workflows/ci.yml) runs automatically
for pull requests and pushes to `main`. It may also be started manually using
**Actions → Lightweight CI → Run workflow**. It does not merge, deploy, or
re-run expensive PostgreSQL CPU benchmarks.

## Checks

1. **Python tests and evidence integrity** (Python 3.13, pytest 8.4.2):
   executes the repository's *offline* PostgreSQL-maintenance and numerical
   tracing tests and the validator's positive/negative regression tests. It
   checks all committed experimental `SHA256SUMS` files, including the full
   coverage of the Issue #9 evidence directory. The checksum step is strictly
   read-only. A mismatched hash, missing file or malformed manifest fails CI.
2. **Build paper PDF**: compiles `paper/main.tex` with the bundled
   `acmart.cls` and `pvldb.sty` using pdfLaTeX/latexmk in TeX Live 2026.
   The PDF appears as the short-lived `paper-preview` artifact on the Actions
   run. Warnings that do not abort compilation remain visible in build logs.

Both jobs are required for an all-green workflow. A green badge means these
*specified checks* passed, not that a mathematical theorem or experimental
claim has been independently proven.

## Run locally (from the repository root)

Install the standalone offline-test runner in your Python environment:

```sh
python -m pip install pytest==8.4.2
python -m pytest -q \
  ci/test_check_evidence.py \
  experiments/pg-maintenance/test_analyze_benchmark.py \
  experiments/pg-maintenance/fixed-target-cpu/test_fixed_target_cpu.py \
  experiments/pg-tracing/test_analyze_mcv_numeric_followup.py
python ci/check_evidence.py
```

For paper compilation with a TeX Live installation:

```sh
cd paper
latexmk -pdf -file-line-error -halt-on-error -interaction=nonstopmode main.tex
```

The synthetic end-to-end test at
`experiments/synthetic/tests/test_run_suite.py` is **intentionally excluded**
from this first CI: it imports the separately developed `ess-advisor` Python
package. Later cross-repository integration CI can install a version-pinned
advisor and exercise it, without making this lightweight workflow depend on
another repository's current development state.

## How to read a PR's result

Open a PR → **Checks**. Expand either CI job to see the command output; green
means the checks passed, red means a check failed. When the PDF job succeeds,
find the **paper-preview** artifact on the workflow run's summary page.

This workflow is not configured as a mandatory GitHub branch-protection rule.
The researcher retains the merge decision. GitHub repository settings can
later require the two named job checks after the workflow has run successfully.
