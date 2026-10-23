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

`run_stage2_b23.py` was the narrow runner. It verified the protocol
merge SHA and content hash, immutable Stage-1 adapter and Advisor pins, frozen
environment, clean merged source tree, input/candidate hashes and all 10,000
tasks per case. It launches one case at a time in its own systemd scope, keeps
full API responses and compact records under `ESS_RUNTIME_PARENT`, computes
the selected-set objective independently with exact Fraction arithmetic, and
stops at the first failure. It requires both a merged runner commit and the
explicit `--research-owner-authorized` acknowledgment. The separately
authorized run was attempted after review/merge, then stopped on case 1
(`forest10-nominal-b2`) at the 900-second outer timeout; cases 2–8 did not
start. See [the immutable stop report](stage2-b23-run-20261023-stop-report-v1.md).

The protocol and runner regression tests do not import or invoke Advisor and
never start solver code. Run them with:

```bash
python3 -m unittest discover \
  -s experiments/solver-integration-issue74 -p 'test_stage2_b23_*.py' -v
```

The original eight-case authorization was consumed by the stopped first
attempt. Do not retry or run cases 2–8 under that authorization; a separate
prospective protocol and new explicit authorization are required.

## Prospective single-case B=2 recovery proposal

After the first B=2 case stopped at the outer timeout and the Advisor CSR fix
merged at `369d90217e931c7d1b0cd6e82c88527a25cc7129`, a separate recovery
proposal is recorded in
[`stage2-b2-recovery-protocol-v1.json`](stage2-b2-recovery-protocol-v1.json).
It proposes only one Forest10 Nominal B=2 attempt on the same frozen valid-only
input, with the prior 12 GiB / 900 s outer and 600 s Advisor caps, no retry and
stop-for-review on every incomplete or nonpassing result. This is a new
prospective question about whether the fixed implementation returns the
archived exact selection; it does not reinterpret the historical timeout.

`run_stage2_b2_recovery.py` computes and verifies the frozen selection and
coefficient file SHA-256 values from repository bytes before preparing a
solver request, then records the hashes in durable evidence. It writes fsynced
phase events and an atomically replaced checkpoint, including Python
constraint construction, COO assembly, COO-to-CSR conversion, remaining
solver-input preparation, and entry/exit from each HiGHS invocation. An
interruption therefore retains the last completed stage and whether HiGHS had
started. The outer runner uses a unique systemd unit name and immediately
captures its raw `Result`, `MemoryPeak`, and `ExecMainStatus` properties with
the command exit code. If the transient unit has disappeared or the query
fails, the record says systemd status is unknown; it does not infer timeout or
OOM from the process exit code. The historical base protocol keeps
`execution_authorized` set to `false`. A separate reviewed execution-gate
revision records later authorization; its regression tests are solver-free.
Review or merge of the recovery proposal alone is not execution authorization.

## Separate one-run authorization request

After PR #79 merged, the authorization request in
[`stage2-b2-recovery-authorization-request-v1.json`](stage2-b2-recovery-authorization-request-v1.json)
proposes exactly one new Forest10 Nominal B=2 attempt against the merged runner
and Advisor pins. It binds to the SHA-256 of the unchanged recovery protocol,
repeats the existing resource caps and stop rules, and leaves
`execution_authorized` false. The researcher has since explicitly granted
this exact one-case attempt, conditional on a separate execution-gate PR being
reviewed and merged; see Issue #74. The new versioned
[`stage2-b2-recovery-execution-gate-v1.json`](stage2-b2-recovery-execution-gate-v1.json)
records that grant without editing either earlier protocol. Its `true` gate is
effective only from a clean checkout containing the reviewed runner in
`origin/main`; the runner verifies its source blob before any systemd launch.
An fsynced exclusive outer claim and child-start marker consume the grant
once and block retries, including direct child re-entry. The parent rejects a
reported PASS without a matching child marker. No solver is run by this PR or
its CI.
