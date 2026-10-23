# Issue #74 full-input B=0 follow-up

**Evidence label: experimentally observed** for the four runs below, with
model-internal exact reference calculations under the stated assumptions.
This follow-up uses the sparse Advisor merge
`1951123/ess-advisor@d40a57d4704345fef85298dd97192b2d998dc6eb`. The original
Stage-1 adapter pin `e7bb42f...` remains the provenance for the Stage-1 smoke
and has not been rewritten.

## Question and fixed limits

Can the pinned sparse Advisor complete full-input B=0 solves for the frozen
Forest10 and Census13 models within explicit resource limits and return the
same objective and selected set as an independent exact Fraction reference?
The run reuses the archived valid-only inputs and existing adapter. It includes
all 10,000 valid tasks and all frozen candidates, with both objectives for each
model. It does not access official test inputs, run PostgreSQL, refit models,
or evaluate another budget.

The run configuration is
[`full-input-b0-config-v1.json`](full-input-b0-config-v1.json); compact per-case
results, input provenance, status details and request/response hashes are in
[`full-input-b0-results-v1.json`](full-input-b0-results-v1.json). Raw per-case
JSON and `/usr/bin/time -v` logs are retained under
`$ESS_RUNTIME_PARENT/ess-research/issue74/full-b0-d40a57d-20261023/`.

Each candidate has unit proxy cost. Therefore B=0 admits exactly one resource
set, the empty set. The independent Advisor reference evaluated that set
directly with `reference_nominal_objective` or `reference_objective`, which
uses Fraction arithmetic. This avoids the reference's generic subset wrapper,
which enumerates all `2^|E|` subsets before filtering by budget. An initial
attempt using that wrapper was interrupted before any solver call; it is not a
solver result. The direct evaluation preserves the exact unique feasible set
and evaluates all full-input task losses.

## Results

All four results are experimentally observed as `MATCH`: Advisor returned a
validated feasible empty selection, its exact serialized objective equaled
the independent Fraction objective, and all solver calls reported optimal.
Nominal selected-policy losses were replayed and summed with Fraction
arithmetic. PESS selected-value evidence is reported as Fraction-certified;
the returned solver statuses remain floating-point MILP statuses and are not
the exactness argument for the B=0 selection.

| Model | Objective | Tasks / candidates | Exact objective | Outer wall | Peak RSS |
|---|---|---:|---:|---:|---:|
| Forest10 `positive-preclamp-v1` | Nominal | 10,000 / 45 | `23326825631265146269149/1000000000000000000` | 47.57 s | 1.58 GiB |
| Forest10 `positive-preclamp-v1` | PESS | 10,000 / 45 | `23326825631265146269149/1000000000000000000` | 11.92 s | 0.22 GiB |
| Census13 `clamped-log-v2` | Nominal | 10,000 / 78 | `4069678531214269000459/500000000000000000` | 107.63 s | 3.17 GiB |
| Census13 `clamped-log-v2` | PESS | 10,000 / 78 | `4069678531214269000459/500000000000000000` | 22.28 s | 0.25 GiB |

Each case had `MemoryMax=12G`, an outer `RuntimeMaxSec=900`, and Advisor
`time_seconds=total_time_seconds=600`. The largest peak RSS was about 3.17 GiB;
the longest outer wall time was 107.63 s. All four exited successfully without
reaching a configured limit. The environment used Python 3.12, `pess-ess`
0.1.0 from the pinned commit, SciPy 1.18.1, and HiGHS via SciPy.

## Reproduction

From this Issue Worktree, install the immutable sparse merge in its `.venv`:

```bash
.venv/bin/python -m pip install --force-reinstall --no-deps \
  'git+https://github.com/1951123/ess-advisor.git@d40a57d4704345fef85298dd97192b2d998dc6eb#egg=pess-ess'
```

Run one case per bounded systemd scope (the example uses Forest10 Nominal):

```bash
source ~/.bashrc
: "${ESS_RUNTIME_PARENT:?ESS_RUNTIME_PARENT must be set}"
RUN_ROOT="$ESS_RUNTIME_PARENT/ess-research/issue74/full-b0-<run-id>"
mkdir -p "$RUN_ROOT"
systemd-run --user --scope --quiet \
  -p MemoryMax=12G -p RuntimeMaxSec=900 \
  /usr/bin/time -v -o "$RUN_ROOT/forest10-nominal.time" \
  .venv/bin/python experiments/solver-integration-issue74/run_full_input_b0.py \
  --repo "$PWD" --dataset forest10 --objective nominal \
  --output "$RUN_ROOT/forest10-nominal.json"
```

Repeat for datasets `forest10`, `census13` and objectives `nominal`, `pess`.
The runner verifies the installed Advisor commit, imposes the 600-second solver
limit, hashes the exact request and response, compares against the full-input
Fraction reference, and writes a failure record for ordinary exceptions.
Systemd and `/usr/bin/time` enforce and record the outer limits. A killed case
is not a pass and must not be replaced by a larger-limit retry without a new
reviewed run configuration.

## Limits and next step

These results establish a bounded full-input B=0 comparison for these two
frozen models and this pinned solver on this environment. They do not establish
runtime or memory behavior at B=2/3 or larger, solver scalability generally,
PostgreSQL effects, or any test-set result. The dense-allocation failure with
the prior Advisor pin remains historical. Larger budgets stay behind the
separate Stage 2 protocol gate.
