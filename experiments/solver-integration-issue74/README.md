# Issue #74: frozen-model solver integration

This Stage 1 adapter consumes the existing valid-only Forest10 and Census13
model artifacts and emits Advisor schema-v1 requests. It does not vendor or
modify solver code. The two model versions, transformations, resource order,
and unit-cardinality cost proxy remain explicit and separate.

`adapter.py` validates the frozen inputs and builds sparse task corrections.
Forest10 uses the exact rational `alpha`/`b` values already retained in its
coefficient artifact. Census13 reconstructs the already frozen `clamped-log-v2`
coefficients from valid-only observations using the recorded transform, then
requires the coefficient digest to match the frozen selection record. It never
loads test inputs.

## Reproduce the bounded smoke

From this Issue Worktree, install the immutable Advisor source pin into its
independent `.venv` (Python 3.11+):

```bash
.venv/bin/python -m pip install \
  'git+https://github.com/1951123/ess-advisor.git@e7bb42f5b9ac3f09dd45e341e0e215153ad5f8ec#egg=pess-ess'
```

Then set the repository path and a fresh run directory under the configured
`ESS_RUNTIME_PARENT`:

```bash
source ~/.bashrc
: "${ESS_RUNTIME_PARENT:?ESS_RUNTIME_PARENT must be set}"
RUN_ROOT="$ESS_RUNTIME_PARENT/ess-research/issue74/runs/<new-run-id>"
mkdir -p "$RUN_ROOT"
.venv/bin/python -m unittest discover \
  -s experiments/solver-integration-issue74 -p 'test_*.py' -v
.venv/bin/python experiments/solver-integration-issue74/run_bounded_smoke.py \
  --repo "$PWD" --output "$RUN_ROOT/bounded-smoke.json" \
  --task-limit 12 --candidate-limit 8
```

The runner is capped at 12 tasks and 8 candidates, and each solve has bounded
time limits. It compares both objectives at budgets 0, 2, and 3 against the
Advisor's independent Fraction exhaustive reference on that same truncated
subproblem. These results validate schema and API integration only; they do
not reproduce the full frozen-workload optima. The complete first-run summary,
all exact ties for the smoke subproblems, solver responses and per-request /
response hashes are in `bounded-smoke-results-v1.json`.

See `stage1-report-v1.md` for provenance, observed statuses, and the full-model
memory bottleneck. No PostgreSQL process or held-out test input is involved.

## Full-input B=0 follow-up

After `ess-advisor` merged sparse matrix assembly at
`d40a57d4704345fef85298dd97192b2d998dc6eb`, four bounded full-input B=0 cases
were run (both objectives on both frozen models). The adapter's historical
Stage-1 pin above is preserved; the new run pin, limits, exact-reference method,
statuses, hashes and resource measurements are documented in
[`full-input-b0-report-v1.md`](full-input-b0-report-v1.md) and
[`full-input-b0-results-v1.json`](full-input-b0-results-v1.json).

The narrow runner `run_full_input_b0.py` accepts exactly one dataset/objective
case at a time. Enforce the documented `MemoryMax=12G` and
`RuntimeMaxSec=900` around each process and keep its outputs under the
configured `ESS_RUNTIME_PARENT`. It verifies the installed immutable Advisor
commit and checks the full 10,000-task B=0 result against direct Fraction
evaluation of the sole feasible empty set. These results do not cover B=2/3;
those budgets remain behind the separately reviewed Stage 2 runner gate.

## Stage 2 B=2/3 protocol and runner gate

[`stage2-b23-protocol-v1.json`](stage2-b23-protocol-v1.json) records a
reviewed and merged eight-case, serial B=2/3 protocol against frozen Fraction
references. Its `PROPOSED_NOT_FROZEN_NOT_EXECUTED` label is historical and is
preserved. The merged protocol alone did not authorize execution; Issue #74
later granted bounded execution authorization conditional on review and merge
of a separate runner PR.

`run_stage2_b23.py` is the proposed narrow runner. It verifies the protocol
merge SHA and content hash, immutable Stage-1 adapter and Advisor pins, frozen
environment, clean merged source tree, input/candidate hashes and all 10,000
tasks per case. It launches one case at a time in its own systemd scope, keeps
full API responses and compact records under `ESS_RUNTIME_PARENT`, computes
the selected-set objective independently with exact Fraction arithmetic, and
stops at the first failure. It requires both a merged runner commit and the
explicit `--research-owner-authorized` acknowledgment. **Do not invoke it
until the runner PR is reviewed and merged.**

The protocol and runner regression tests do not import or invoke Advisor and
never start solver code. Run them with:

```bash
python3 -m unittest discover \
  -s experiments/solver-integration-issue74 -p 'test_stage2_b23_*.py' -v
```

The eight-case run remains unexecuted while this runner is under review. No
retry, concurrent case, option change, or resource escalation is permitted.
