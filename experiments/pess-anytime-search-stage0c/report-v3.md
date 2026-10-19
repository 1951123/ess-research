# Stage 0c v3 corrected evidence

Evidence label: experimentally observed. This report is the corrected rerun
requested by the Issue #36 review. The scientific decision remains the scoped
NO-GO from v2: the Gate A/baseline observations are reproducible on this
corpus, but they do not establish the stronger approximate-search claim.

## Provenance and protocol

- Protocol: `protocol-v3.json`, code SHA recorded by the runners:
  `75bed771192585b6b1403225b0810862a501079b`.
- Advisor dependency: pinned `ess-advisor` SHA
  `1052ff4a46270c90414d76b32d6f6b37e5908f6a`.
- Python environment: the existing worktree `.venv`; NumPy 2.5.4, SciPy
  1.18.1, NetworkX 3.7, and the SciPy-bundled HiGHS used by the adapter.
- Inputs are selected only from the explicit manifest and each listed file is
  SHA-256 checked before execution. v1 has 5 inputs/3 Gate A inputs; v2 and
  v3 have 6 inputs/4 Gate A inputs.
- Methods, seeds `(3501, 3502, 3503)`, 10-second cap, checkpoints
  `(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10)`, exact `Fraction` reference
  calculations, and the NO-GO rule are unchanged.

The earlier `protocol-v1.json`/`protocol-v2.json` outputs remain preserved as
archival observations. Their anytime traces are timing-unfit for future
time-to-target claims because they used final-only or non-causal checkpoint
accounting; they were not overwritten or silently relabeled.

## Review fixes implemented

1. `search_timed.py` starts its clock before initialization/evaluation,
   records actual completion time for every valid initial or accepted
   incumbent, and defines each checkpoint as the last completion at or before
   that checkpoint. An evaluation completing after the cap is rejected as an
   incumbent, with overshoot retained in the result.
2. `_ordered_neighbors` polls the cap while scoring neighbors; singleton and
   greedy controls also enforce the cap during evaluation. A deterministic
   test-only objective delay crosses the 0.05/0.1-second checkpoints and
   verifies causal availability and positive wall time.
3. All runners use the explicit manifest and fail closed on missing or changed
   inputs. Evidence writers use exclusive creation, so an existing historical
   output cannot be overwritten.
4. Advisor v3 output keeps the decision, feasibility, objective, bounds,
   solver status, tolerances, warnings, and timing fields while omitting
   repeated solver variable vectors. The preserved v1/v2 raw evidence remains
   available for audit; v3 is the corrected compact rerun.

## Executed v3 evidence

| Artifact | Observation |
|---|---|
| `gate-a-result-v3.json` | Gate A PASS; 4 tiny instances; Static and Master–Oracle independently agree with Fraction exhaustive optima |
| `baseline-results-v3.json` | 36 records; all returned status `optimal`; all independent original-PESS checks passed |
| `baseline-checkpoints-v3.json` | 36 rows × 8 independent endpoint budgets; explicitly labeled endpoint-at-budget, not a continuous incumbent trace |
| `search-results-v3.json` | 126 records; all independent checks passed; every emitted checkpoint is causal under the corrected history rule |

The v3 approximate runs completed under the 10-second cap on this machine;
the largest observed wall time was about 0.031 seconds. This is only an
experimentally observed runtime on this environment, not a performance claim.

## Footprint and limits

The v3 artifacts are compact relative to the preserved raw checkpoint evidence
because they omit repeated solver value arrays. The old raw files are retained
for provenance, so the repository still carries their storage cost; deleting
them would remove irreplaceable historical evidence and was not authorized.
The v3 compact representation is not a claim that the omitted solver vectors
can be reconstructed from the summary.

The result remains a model-internal, bounded corpus experiment. It does not
establish a PostgreSQL-wide claim, a maximum-cardinality matching claim, a
shared-policy global worst case, or real-scheme containment/equality. Generic
maintenance remains nonadditive; any per-statistic cost interpretation is an
experimental proxy only.

