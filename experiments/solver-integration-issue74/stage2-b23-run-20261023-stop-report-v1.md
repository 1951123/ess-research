# Issue #74 Stage 2 B=2/3 execution stop report (2026-10-23)

**Evidence label:** Experimentally observed operational stop. No solver result or model-comparison result was produced.

## Question and minimum experiment

The question was whether pinned Nominal and task-wise PESS decisions on the frozen valid-only Forest10 and Census13 models at B=2/3 match their archived exact `Fraction` optima. The minimum experiment reuses the frozen model inputs, archived references and the merged `run_stage2_b23.py` runner: run the eight preregistered cases serially, retaining each response/status and stopping at the first failure.

## Execution and pins

- Run ID: `issue74-20261023-v1`
- Runtime root: `$ESS_RUNTIME_PARENT/ess-research/issue74/stage2-b23-issue74-20261023-v1/`
- Command: `PYTHONPATH=experiments/solver-integration-issue74 /home/wqts/projects/ess-research/.worktrees/ess-research-issue74/.venv/bin/python experiments/solver-integration-issue74/run_stage2_b23.py run --repo "$PWD" --run-id issue74-20261023-v1 --research-owner-authorized`
- Repository runner source: `ess-research` merge commit `a0aac71de45f2c2440b2fa959620954901ae67f8` (PR #77 head `bc1eeb6b959e104ab4f63ab21f69724c17015fd9`)
- Protocol: merge commit `9b858e47284a290c1b078333929238cf55efdbff`; content SHA-256 `57ba752c16dc188e4d24ef24a758590281a5f77c0418cd5911038a8d2a50af60`
- Advisor: `d40a57d4704345fef85298dd97192b2d998dc6eb`; `pess-ess 0.1.0`, Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1.
- The attempted Forest10 case passed its frozen-selection, coefficient, and adapter provenance checks before entering the solver call. Census13 was not loaded because the protocol stopped after case 1. The runner uses the unchanged pinned adapter and protocol case order.
- Limits: one case at a time, no retries; systemd `MemoryMax=12 GiB`, `RuntimeMaxSec=900`; Advisor limits 600 s and PESS inner limit 120 s.
- No random seed is used by this fixed-input solver invocation.

## Observed outcome

Only case 1, `forest10-nominal-b2`, was attempted. The systemd scope ended with `Result=timeout` at its 900-second outer limit; its child returned signal status `-15`. The observed scope `MemoryPeak` was 2,556,788,736 bytes (about 2.38 GiB), below the 12 GiB cap. No `advisor-response.json` or solver status was produced, so no selected set, exact selected-set objective, or solver-reported optimality can be assessed. GNU `time` did not write its report before the scope was terminated.

The runner durably recorded the case as `STOP_FOR_REVIEW` in `01-forest10-nominal-b2/result.json` and `case-outcomes.jsonl`, then wrote `run-summary.json` with `STOPPED_FOR_REVIEW` and `cases_attempted: 1`. Cases 2–8 were not started. There was no retry, option change, or limit increase.

The complete run metadata and failure records remain at the runtime root above; generated run files are intentionally outside Git. The empty `runner.log` and `time.txt` are retained there as produced. The observation establishes only that this attempt reached the outer wall limit without returning a solver response; it does not establish why the pinned solver failed to return within that time or anything about the frozen optimum.

## Disposition

**Stop for researcher review.** Do not start cases 2–8 or retry case 1 under this run. Any future experiment needs a reviewed explanation and a separately scoped authorization/protocol decision; this report does not authorize another solver invocation. Issue #74 remains open.
