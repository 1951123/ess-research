# Issue #87 — bounded Nominal/PESS add-only greedy protocol

**Scientific question:** Under the already-frozen Forest10 and Census13 valid-only models, does the same strict-improvement `add_only_greedy` rule produce different Nominal and task-wise PESS selections at budgets above 3? Reuse the two existing 10,000-task models and adapters; the comparison uses the frozen `B=0,2,3,4,5` sequence, with exact Fraction re-evaluation of both selected sets under both objectives.

The full frozen comparison completed in [`issue87-valid-only-20261024-v4`](runs/issue87-valid-only-20261024-v4/report.md): 20 complete solver cases and 10 exact cross-evaluations. Nominal and PESS greedy selections differ at B=4 and B=5 on both datasets. These are valid-only greedy heuristic results, without a global-optimum claim. The report retains compact decisions and hashes of all raw runtime evidence; the failed v1/v2/v3 attempts remain preserved separately.

The authoritative scientific design, pins, fixed case order, limits and record fields remain in [`protocol-v1.json`](protocol-v1.json). Issue #87 comment 6380444478 records the original execution authorization. On 2026-10-24 the researcher additionally authorized clean development-branch execution before merge and continuing engineering fixes/new attempts until completion. This changes the execution workflow, not the scientific protocol or resource limits.

## Fixed design

- Forest10 and Census13 are separate valid-only model instances with 10,000 tasks and the complete 45/78 candidate universes. Their different pre-clamp transforms remain distinct model versions.
- Each candidate has unit additive proxy cost, checked before treating `Maint(M) <= B` as `|M| <= B`. This proxy is not physical maintenance cost.
- The case sequence is Forest10 then Census13; within each dataset budgets are `0, 2, 3, 4, 5`, and Nominal precedes PESS within each budget. Budgets 0/2/3 provide historical-model sanity context; 4/5 are the target. B=6 is excluded.
- The same pinned Advisor `add_only_greedy` backend applies exact Fraction fixed-set values to both objectives. Nominal uses its one archived global priority order. PESS independently maximizes over every task's inclusion-maximal matchings. The outer add-only search has no global-optimum guarantee.
- Cases are serial, single-process, with 600-second Advisor and 900-second outer wall limits and a 12-GiB memory limit. The fixed-evaluation caps are shared across objectives; PESS also has a derived cumulative matching-subset cap. The full cap table and derivation are in the protocol JSON.
- Any mismatch, timeout, cap, incomplete round, missing exact value, or failed cross-evaluation makes the affected result incomplete and stops that sequence. Failed sequences are never resumed or presented as complete comparisons. A further attempt follows the researcher's execution authorization, including explicit continuing authorization for engineering repairs, and uses a new run ID; limits and scientific inputs remain frozen.

## Protocol and run preparation

`adapter.py` wraps the existing frozen-model request builder with schema-v1 `add_only_greedy` controls. `build_frozen_dataset_payload()` checks the full task count, candidate universe/order, unit costs, frozen selection/model hashes, and archived source adapter before constructing a request. It does not launch the solver. The Stage 0 adapter tests use tiny synthetic inputs; runner CI separately calls this builder for both frozen datasets without solving them.

The minimal full-case runner is in [`run_issue87.py`](run_issue87.py). It checks the authorization flag and exact protocol hash before any worker path, reuses the B=0 frozen request to construct later budget-specific case requests, runs one case or cross-evaluation at a time in a systemd scope, and keeps exact request/response bytes, JSONL records, resource reports and failure details under `$ESS_RUNTIME_PARENT/ess-research/issue87/runs/<run-id>/`. Cross-evaluation receives the current budget's Nominal request. Any failed or incomplete case stops the sequence; partial prefixes never become selected sets. Authorized runs start from a clean, committed Issue development Worktree and record its exact SHA; a prior main merge is not required. Integration follows successful checks and experimental validation under researcher authorization.

The existing preflight tests exercise the exact backend on synthetic inputs. Runner tests cover the frozen 20-case order and limits, the execution gate (including hidden worker commands), incomplete-result handling, and the full Forest10/Census13 input builder. The full-input test only builds and validates requests; it does not call the solver.

## Execution gate and limits

The first authorized run attempted Forest10 Nominal B=0 and stopped because the exited systemd scope reported unbounded memory and wall properties. Its raw response remains incomplete evidence. v2 stopped on a missing cross-worker directory argument; v3 stopped because a B=0 request was supplied to B=2 cross-evaluation. v4 completed after these runner defects were repaired, with all 30 active scope/cgroup checks passing. The [v4 report](runs/issue87-valid-only-20261024-v4/report.md) records exact results and preserves the failed-attempt hashes. No PostgreSQL, test split access/evaluation, refitting, or manuscript work was performed.

The planned decision is heuristic and model-internal. A difference between greedy outputs does not establish that global Nominal and PESS optima differ; a PESS gap is measured only relative to the PESS greedy incumbent. The modeled maximal-matching family is not claimed to contain every real PostgreSQL scheme.

## Stage 0 check (historical)

On Python 3.12.3 with NumPy 2.3.4, SciPy 1.18.1, NetworkX 3.7, and the local `ess-advisor` checkout verified at main commit `5d61f75fede37d34027b437c646000a3d78d00c6`, the synthetic Issue #87 preflight passed **7 tests** after review follow-ups. The pinned Advisor `test_greedy.py` passed **14 tests**. Ruff check and format checks passed for both new Python files. The research adapter was tested only with tiny synthetic requests; `build_frozen_dataset_payload()` was not called. No complete valid workload was solved, and no PostgreSQL, held-out test, or calibration data were accessed.

GitHub Actions check status is tracked in the Draft PR and must correspond to the pushed head under review.

## Runner revision check (historical)

On Python 3.12.3 with the frozen dependency pins, the authorization PR's repository CI passed **149 tests**; Ruff and all 22 evidence manifests also passed. The runner's full-input CI tests build both 10,000-task requests without solving them. A post-merge `/bin/true` scope probe on this host returned the configured memory and wall properties, but the first actual runner scope later reported both as `infinity` and triggered the fail-closed stop. See the run report for exact evidence and the additional record-format issue discovered during review.

## Issue #95 task-level attribution

[`analyze_issue95.py`](analyze_issue95.py) is a read-only fixed-set analysis of the four B=4/5 Nominal greedy selections from v4. It reuses the exact Advisor reference evaluator and stored v4 requests/cross-objectives; it does not rerun selection. The [findings report](issue95-task-attribution.md) and [compact exact output](issue95-task-attribution.json) record per-task risk counts, Top-10/Top-100 concentration, and maximal-matching witnesses. The separate test file uses only tiny synthetic tasks.
