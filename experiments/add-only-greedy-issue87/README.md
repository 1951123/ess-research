# Issue #87 — bounded Nominal/PESS add-only greedy protocol

**Scientific question:** Under the already-frozen Forest10 and Census13 valid-only models, does the same strict-improvement `add_only_greedy` rule produce different Nominal and task-wise PESS selections at budgets above 3? Reuse the two existing 10,000-task models and adapters; the minimum future comparison is the frozen `B=0,2,3,4,5` sequence, with exact Fraction re-evaluation of both selected sets under both objectives.

This directory records **Stage 0 only**. The authoritative design, pins, fixed case order, limits, stop rules, and JSONL record fields are in [`protocol-v1.json`](protocol-v1.json). It is frozen as planned with `execution_authorized: false`.

## Fixed design

- Forest10 and Census13 are separate valid-only model instances with 10,000 tasks and the complete 45/78 candidate universes. Their different pre-clamp transforms remain distinct model versions.
- Each candidate has unit additive proxy cost, checked before treating `Maint(M) <= B` as `|M| <= B`. This proxy is not physical maintenance cost.
- The case sequence is Forest10 then Census13; within each dataset budgets are `0, 2, 3, 4, 5`, and Nominal precedes PESS within each budget. Budgets 0/2/3 provide historical-model sanity context; 4/5 are the target. B=6 is excluded.
- The same pinned Advisor `add_only_greedy` backend applies exact Fraction fixed-set values to both objectives. Nominal uses its one archived global priority order. PESS independently maximizes over every task's inclusion-maximal matchings. The outer add-only search has no global-optimum guarantee.
- Cases are serial, single-process, with 600-second Advisor and 900-second outer wall limits and a 12-GiB memory limit. The fixed-evaluation caps are shared across objectives; PESS also has a derived cumulative matching-subset cap. The full cap table and derivation are in the protocol JSON.
- Any mismatch, timeout, cap, incomplete round, missing exact value, or failed cross-evaluation makes the affected result incomplete, stops dependent cases, and requires review. No retry, limit increase, or partial-prefix comparison is allowed.

## Stage 0 implementation

`adapter.py` wraps the existing frozen-model request builder with schema-v1 `add_only_greedy` controls. `build_frozen_dataset_payload()` checks the full task count, candidate universe/order, unit costs, frozen selection/model hashes, and archived source adapter before constructing a request. It does not launch the solver. The tests use only tiny synthetic instances and do not call that full-input builder.

This is a request builder and exact fixed-set cross-evaluator, not a prospective full-case runner. Before any full-valid execution authorization, a separate reviewed and pinned execution-gate revision must implement and test serial case orchestration, OS-enforced memory/wall limits, process exit/RSS capture, a CI check of the pinned full-input builder, and the frozen JSONL evidence records. Stage 0 does not enforce those operating-system limits or test that full-input builder in CI.

The seven preflight tests exercise the exact backend on synthetic inputs: B=0, deterministic candidate-ID ties, task eligibility, zero-cost feasibility, plateau stopping, incomplete-round handling, exact Fraction cross-objective re-evaluation, request immutability, candidate-universe validation, and post-deadline incomplete handling. No AreCEL data is needed for these tests.

## Execution gate and limits

This Stage 0 work does not execute any Forest10/Census13 selection request. The full-valid runs need a separate explicit researcher authorization after protocol review and merge. PostgreSQL, test split access/evaluation, refitting, and manuscript edits are outside this task.

The planned decision is heuristic and model-internal. A difference between greedy outputs does not establish that global Nominal and PESS optima differ; a PESS gap is measured only relative to the PESS greedy incumbent. The modeled maximal-matching family is not claimed to contain every real PostgreSQL scheme.

## Stage 0 check

On Python 3.12.3 with NumPy 2.3.4, SciPy 1.18.1, NetworkX 3.7, and the local `ess-advisor` checkout verified at main commit `5d61f75fede37d34027b437c646000a3d78d00c6`, the synthetic Issue #87 preflight passed **7 tests** after review follow-ups. The pinned Advisor `test_greedy.py` passed **14 tests**. Ruff check and format checks passed for both new Python files. The research adapter was tested only with tiny synthetic requests; `build_frozen_dataset_payload()` was not called. No complete valid workload was solved, and no PostgreSQL, held-out test, or calibration data were accessed.

GitHub Actions check status is tracked in the Draft PR and must correspond to the pushed head under review.
