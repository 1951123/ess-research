# Agent instructions — ESS Research

This file applies to **this repository** (`1951123/ess-research`) and is intended for Codex in VS Code and other coding/research agents. It is not an authorization to alter the other repositories.

## 1. Mandatory context before changing research artifacts

Read in order:

1. `docs/RESEARCH_CONTEXT.md` — stable definitions and cross-repo roles.
2. `docs/DECISIONS.md` — accepted decisions and reasons.
3. `docs/STATUS.md` — current work and unverified items.
4. Relevant `paper/main.tex`, `notes/`, and `experiments/` files for the requested task.

Check current git status and branch before editing. If files are missing because this workflow PR has not yet merged, inspect the workflow branch/PR rather than assuming a different research direction.

## 2. Research correctness rules

- Preserve the **generic** interface: unordered resource choice `M`, complete admissible schemes \(\Gamma_i(M)\), nonnegative task loss, and abstract nonadditive maintenance cost. Do not silently replace the generic model with a PG-specific or additive one.
- A PostgreSQL maximal-matching model is an **instance**; do not claim it describes all PostgreSQL queries, all card estimators, or fixed-PG behavior under every catalog.
- Do not confuse **maximal matching** with **maximum-cardinality matching**.
- Do not replace the task-wise sum of worst-case losses with a shared-policy global worst case without explicitly proposing and justifying that model change.
- Distinguish real possible schemes \(\mathcal R_i(M)\) from prescribed \(\Gamma_i(M)\); do not claim containment/equality or guaranteed real worst case without assumptions and evidence.
- The primary illustrative loss is positive **pre-clamp** absolute log error. Explicitly state conditions before taking logs; PG Plan Rows with rounding/clamping is not identical.
- Generic \(\operatorname{Maint}(M)\) is not assumed additive. Per-statistic cost sums are experimental proxies with scoped conditions.
- Distinguish model mathematical exactness, **Fraction** exact reference calculations, and **floating-point** MILP solver-reported optimality. Never upgrade one to another silently.

## 3. Evidence and reproducibility rules

Every substantive claim must be labeled appropriately:

- **Proven (model-internal):** mathematics with precise assumptions and proof.
- **Source-derived (conditional):** traceable to versioned source control flow, with its limited prerequisites.
- **Experimentally observed:** tests/experiments actually executed and logged; show environment, version, input, seed, command, output, and limitation.
- **Conjecture / Open:** unproved or untested.
- **Refuted / Superseded:** document the failing example or replacement.

Do **not** invent numerical results, runtime traces, successful compilation, performance improvements, or literature novelty. Do not overwrite old experiment reports without preserving provenance; compare independent baselines and keep raw data.

For theorem edits, check every assumption and separate the math statement from its PostgreSQL interpretation. For experiments, record enough to reproduce; treat `EXPLAIN` output alone as insufficient evidence for which PG statistics objects were actually selected.

## 4. Minimal Git/Codex collaboration protocol

- The researcher retains the final choice of research direction and merge.
- **Default for nontrivial code/research work:** one small task → short-lived branch → tests/evidence → reviewable **Draft PR**; use `main` directly only for simple, low-risk edits when expressly appropriate.
- Recommended branch prefixes: `research/`, `experiment/`, `fix/`, `docs/` or `workflow/`.
- Before starting, inspect `git status` and existing branches. Never reset, clean, force-push, overwrite uncommitted work, or merge a draft PR as a shortcut.
- Make smallest scoped changes that satisfy the task. Preserve unrelated work, file structure, and LaTeX manuscript template.
- At delivery, report changed paths, commits/branch/PR, tests **actually run** and their outcomes, any unresolved warnings, and the next validation step.
- Keep agent-prompts *bounded*: specify goal, assumptions, in-scope files, out-of-scope files, acceptance tests, and required output.
- A task in another repo requires explicit scope and work there; do not alter `ess-advisor` or `ess-postgresql` merely because they are related.
- **Remote and local repository states are independent.** A GitHub commit or PR merge does not automatically update any local working tree. Changes must be fetched and, when appropriate, integrated into the relevant local branch, either through explicit user action or configured tooling. Never assume synchronization has occurred without verifying the repository state.
- A remote-tracking ref such as `origin/main` records the remote branch state last observed locally (typically updated by `git fetch origin`); it is not a live mirror and does not itself advance local `main` or update the working tree.

## 5. Where information belongs

- `docs/RESEARCH_CONTEXT.md`: durable goals, notation, major cross-repo facts.
- `docs/DECISIONS.md`: accepted decisions and revisit triggers.
- `docs/STATUS.md`: short live checkpoint, unmerged PRs, next work, evidence labels.
- `notes/`: complete mathematical arguments and exploratory results.
- `paper/main.tex`: paper-ready claims that have been independently checked.
- `experiments/`: scripts, seeds, raw measurements and reports.
- GitHub Issue: a bounded *problem and acceptance criterion* (optional for small tasks).
- Draft PR: *proposed changes and review/evidence*; **not** automatically a validated or merged research result.

Update STATUS at meaningful milestones rather than every trivial commit. Do not turn chat history into a substitute for versioned evidence.
