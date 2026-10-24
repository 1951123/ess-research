# Issue #87 — bounded Nominal/PESS add-only greedy protocol

**Scientific question:** Under the already-frozen Forest10 and Census13 valid-only models, does the same strict-improvement `add_only_greedy` rule produce different Nominal and task-wise PESS selections at budgets above 3? Reuse the two existing 10,000-task models and adapters; the minimum future comparison is the frozen `B=0,2,3,4,5` sequence, with exact Fraction re-evaluation of both selected sets under both objectives.

This directory records the frozen protocol and execution preparation; it contains no formal experiment results. The authoritative design, pins, fixed case order, limits, stop rules, and JSONL record fields are in [`protocol-v1.json`](protocol-v1.json). Issue #87 comment 6380444478 records the researcher's execution authorization; PR #90 updates only that gate and the runner's protocol hash pin.

## Fixed design

- Forest10 and Census13 are separate valid-only model instances with 10,000 tasks and the complete 45/78 candidate universes. Their different pre-clamp transforms remain distinct model versions.
- Each candidate has unit additive proxy cost, checked before treating `Maint(M) <= B` as `|M| <= B`. This proxy is not physical maintenance cost.
- The case sequence is Forest10 then Census13; within each dataset budgets are `0, 2, 3, 4, 5`, and Nominal precedes PESS within each budget. Budgets 0/2/3 provide historical-model sanity context; 4/5 are the target. B=6 is excluded.
- The same pinned Advisor `add_only_greedy` backend applies exact Fraction fixed-set values to both objectives. Nominal uses its one archived global priority order. PESS independently maximizes over every task's inclusion-maximal matchings. The outer add-only search has no global-optimum guarantee.
- Cases are serial, single-process, with 600-second Advisor and 900-second outer wall limits and a 12-GiB memory limit. The fixed-evaluation caps are shared across objectives; PESS also has a derived cumulative matching-subset cap. The full cap table and derivation are in the protocol JSON.
- Any mismatch, timeout, cap, incomplete round, missing exact value, or failed cross-evaluation makes the affected result incomplete, stops dependent cases, and requires review. No retry, limit increase, or partial-prefix comparison is allowed.

## Protocol and run preparation

`adapter.py` wraps the existing frozen-model request builder with schema-v1 `add_only_greedy` controls. `build_frozen_dataset_payload()` checks the full task count, candidate universe/order, unit costs, frozen selection/model hashes, and archived source adapter before constructing a request. It does not launch the solver. The Stage 0 adapter tests use tiny synthetic inputs; runner CI separately calls this builder for both frozen datasets without solving them.

The minimal full-case runner is in [`run_issue87.py`](run_issue87.py). It checks the authorization flag and exact protocol hash before any worker path, reuses the B=0 frozen request for later cases, runs one case or cross-evaluation at a time in a systemd scope, and keeps exact request/response bytes, JSONL records, resource reports and failure details under `$ESS_RUNTIME_PARENT/ess-research/issue87/runs/<run-id>/`. Any failed or incomplete case stops the sequence; partial prefixes never become selected sets. The authorized flag only takes effect when this reviewed hash-pinned revision is merged; formal runs start from that merged clean checkout.

The existing preflight tests exercise the exact backend on synthetic inputs. Runner tests cover the frozen 20-case order and limits, the execution gate (including hidden worker commands), incomplete-result handling, and the full Forest10/Census13 input builder. The full-input test only builds and validates requests; it does not call the solver.

## Execution gate and limits

No Forest10/Census13 selection request has been executed by this runner revision. The Issue #87 execution authorization is recorded separately from the software gate; formal execution starts only after this authorization/hash change passes review and CI. PostgreSQL, test split access/evaluation, refitting, and manuscript edits remain outside scope.

The planned decision is heuristic and model-internal. A difference between greedy outputs does not establish that global Nominal and PESS optima differ; a PESS gap is measured only relative to the PESS greedy incumbent. The modeled maximal-matching family is not claimed to contain every real PostgreSQL scheme.

## Stage 0 check

On Python 3.12.3 with NumPy 2.3.4, SciPy 1.18.1, NetworkX 3.7, and the local `ess-advisor` checkout verified at main commit `5d61f75fede37d34027b437c646000a3d78d00c6`, the synthetic Issue #87 preflight passed **7 tests** after review follow-ups. The pinned Advisor `test_greedy.py` passed **14 tests**. Ruff check and format checks passed for both new Python files. The research adapter was tested only with tiny synthetic requests; `build_frozen_dataset_payload()` was not called. No complete valid workload was solved, and no PostgreSQL, held-out test, or calibration data were accessed.

GitHub Actions check status is tracked in the Draft PR and must correspond to the pushed head under review.

## Runner revision check

On Python 3.12.3 with the frozen dependency pins, the repository CI test command passed **149 tests**; Ruff and all 22 evidence manifests also passed. The runner checks built both 10,000-task frozen requests without solving them. A prior `/bin/true` systemd-scope probe returned `Result=success`, `MemoryMax=12884901888`, and `RuntimeMaxUSec=15min`; the runner accepted those effective limits and captured the `/usr/bin/time` report. This authorization revision does not run a solver case. The same synthetic control-flow and full-input builder checks are in CI.
