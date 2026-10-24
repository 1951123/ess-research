# Agent instructions — ESS Research

This file applies to **this repository** (`1951123/ess-research`) and covers VS Code/Codex local Worktree work and expressly authorized ChatGPT GitHub API work. It is not an authorization to alter the other repositories.

## 1. Mandatory context before changing research artifacts

Read in order:

1. `docs/RESEARCH_CONTEXT.md` — stable definitions and cross-repo roles.
2. `docs/DECISIONS.md` — accepted decisions and reasons.
3. `docs/STATUS.md` — current work and unverified items.
4. Relevant `paper/main.tex`, `notes/`, and `experiments/` files for the requested task.

Check current git status and branch before editing. If files are missing because this workflow PR has not yet merged, inspect the workflow branch/PR rather than assuming a different research direction.

### Mandatory shell environment initialization (new Codex sessions)

Local VS Code/Codex execution shells may be **non-login and non-interactive** and may not automatically read `~/.bashrc`. **Before any task needing project paths, run the following in Bash**, including after starting a new Codex session:

```bash
source ~/.bashrc
: "${ESS_DATA_ROOT:?ESS_DATA_ROOT must be set}"
: "${ESS_RUNTIME_PARENT:?ESS_RUNTIME_PARENT must be set}"
: "${ESS_WORKTREE_PARENT:?ESS_WORKTREE_PARENT must be set}"
```

Sourcing affects **only the current shell process**. In a separate command runner/shell invocation, source the file again **in that same Bash process**, e.g. `bash -c 'source ~/.bashrc && <command>'` (replace `<command>` with the actual command), or use an explicitly verified environment passed by the executor. Do not assume variables carry over from a previous tool call or a terminal window. Check only variables needed by the specific operation; missing required variables **fail closed**, without guessed defaults or fallback roots. Do not print secrets, dump the full environment, edit the user's shell profile, or commit credentials. If `~/.bashrc` is guarded against non-interactive shells, verify exports actually took effect. See [docs/git-worktree-workflow.md](docs/git-worktree-workflow.md).

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

### Minimal sufficient implementation and artifact retention (mandatory)

**Answer the research question with the smallest valid experiment.** Before expanding scope, write one sentence identifying the scientific question, the existing data/tools to reuse, and the *minimum* implementation and observations needed to answer it. Prefer the benchmark's existing train/validation/test splits, established metric implementations, and existing scripts. Do not create a new workload, generator, framework, protocol layer, validator, ledger, or infrastructure merely because it might be more rigorous or convenient.

- **Separate necessity from nice-to-have.** A new prerequisite must prevent a specific error that would invalidate the stated claim; document the causal reason. Otherwise record the limitation (including benchmark overlap or generalization boundaries) and proceed with appropriately scoped claims. Do not turn every possible risk or missing optional diagnostic into a fail-closed gate.
- **Researcher controls scientific scope.** Changes to the scientific question, target population, benchmark splits, workload distribution, optimization/evaluation metrics, or meaning of the claims require explicit researcher approval. Agents may independently choose routine deterministic engineering details when they preserve the approved semantics; test them rather than repeatedly blocking on implementation minutiae.
- **Escalate substantial auxiliary work first.** Before adding a custom dataset/generator, broad audit, new storage system, or a multi-file/multi-stage validation framework, explain what conclusion would be invalid without it, the simpler reuse option, and its cost. Obtain researcher approval if the auxiliary work is not essential. Prefer a small direct test to a general-purpose harness.
- **Default retained artifacts are minimal:** (1) one authoritative experiment config with code/source/PG version and relevant settings/seeds; (2) resource decisions and any costly or non-deterministic calibration observations needed to recompute them; (3) compact query-level raw PG observations and failure statuses sufficient to recompute reported metrics; (4) analysis code; (5) one short findings/limitations report. Preserve genuinely irreplaceable or expensive observations and narrowly necessary PG trace evidence when a claim depends on it.
- **Derivable artifacts are disposable by default.** Recompute summary tables, plots, structural counts, fingerprints and intermediate representations from pinned inputs and code. For pre-existing trustworthy source datasets/workloads, record source identity/version/hash instead of duplicating their bytes. Do not retain multiple authoritative copies or create manifests of manifests. A hash alone does not replace irreplaceable measurements.
- **New Git files over 10 MB require researcher approval** and a reason why reconstruction or existing external data storage is insufficient. Do not rewrite history, delete frozen evidence, or force-push to retroactively enforce this rule.
- **Artifact test:** For each proposed persistent file, ask: "If we omit it, what evidence required for the claim becomes unavailable or impractical to reconstruct?" If the answer is none, do not persist it. A single small integrity manifest is enough when checksums are warranted.

These are **default scope and cost constraints, not permission to compromise correctness**: preserve already frozen evidence, disclose known leakage/exposure and uncertainty, and stop for real scientific invalidity, privacy/security concerns, or destructive operations. When an existing design has grown beyond the research question, propose simplification before implementing another layer.

## 4. Minimal Git/Codex collaboration protocol

- The researcher retains the final choice of research direction and merge.
- **Default for nontrivial code/research work:** one small task → short-lived branch → tests/evidence → reviewable **Draft PR**; use `main` directly only for simple, low-risk edits when expressly appropriate.
- **Authorized experiments run on the development branch before merging.** Use a clean, committed Issue Worktree and record its exact source SHA. Validate implementation and experimental evidence there, then merge when the researcher has authorized merge and the agreed checks succeed. Do not require a prior `main` merge merely to execute or validate an authorized experiment. Follow the session's authorization for engineering fixes and further attempts without repeatedly requesting the same permission; retain each attempt separately and preserve scientific scope and resource limits.
- Recommended branch prefixes: `research/`, `experiment/`, `fix/`, `docs/` or `workflow/`.
- Before starting, inspect `git status` and existing branches. Never reset, clean, force-push, overwrite uncommitted work, or merge a draft PR as a shortcut.
- Make smallest scoped changes that satisfy the task. Preserve unrelated work, file structure, and LaTeX manuscript template.
- At delivery, report changed paths, commits/branch/PR, tests **actually run** and their outcomes, any unresolved warnings, and the next validation step.
- Keep agent-prompts *bounded*: specify goal, assumptions, in-scope files, out-of-scope files, acceptance tests, and required output.
- A task in another repo requires explicit scope and work there; do not alter `ess-advisor` or `ess-postgresql` merely because they are related.
- **Remote and local repository states are independent.** A GitHub commit or PR merge does not automatically update any local working tree. Changes must be fetched and, when appropriate, integrated into the relevant local branch, either through explicit user action or configured tooling. Never assume synchronization has occurred without verifying the repository state.
- A remote-tracking ref such as `origin/main` records the remote branch state last observed locally (typically updated by `git fetch origin`); it is not a live mirror and does not itself advance local `main` or update the working tree.

### Mandatory source-commit and PR-head integrity (Codex)

**One task, one authoritative branch history; choose a single writer per task.** **VS Code/local Codex** continues to edit, commit and push from its assigned local Git Worktree; it must not bypass that path with GitHub API source writes. **Chat-mode ChatGPT**, when the researcher explicitly authorizes it for a scoped task, **may create a separate task branch, write files/commits via GitHub API/MCP, and open a Draft PR directly**. This does not grant standing permission to overwrite Codex-owned branches, local changes, frozen evidence, or other repositories. Never mix API and Worktree writes on the same branch without a fresh explicit handoff, synchronization and head-SHA check. The researcher controls merges. A newly created API branch is not automatically present in a local clone; local Codex must fetch before inspecting or continuing it.

**API-authorized ChatGPT procedure:** read the live base commit and relevant documents; use a fresh uniquely named branch and non-force commits; keep changes small and scoped; verify the live branch HEAD equals the created commit and the Draft PR head SHA; report exactly what was changed and checked. If the base advanced, describe the divergence and request review instead of rewriting history or forcing a branch update. API work cannot attest to local Worktree cleanliness or locally executed tests and must say so explicitly.

**Local Codex-only integrity checks (below):**

- Before work: verify `pwd`, `git rev-parse --show-toplevel`, `git branch --show-current`, `git status --short`, `git worktree list`, and the target Issue/PR. Never use `origin/main` as an Issue branch's upstream.
- Before a PR update: ensure intended files are committed and the Worktree is clean; push the **exact current HEAD** with an explicit refspec, `git push -u origin HEAD:refs/heads/<issue-branch>` (replace the placeholder). Verify the **live server** branch SHA using `git ls-remote --heads origin refs/heads/<issue-branch>`; it must equal `git rev-parse HEAD`. A stale `origin/<issue-branch>` alone is insufficient.
- After creating/updating a PR: verify GitHub's PR `head.sha` equals that same local HEAD. Recheck local HEAD = live remote HEAD = PR HEAD **immediately before requesting final review/merge**. If any check fails, **stop**; report SHA and divergence without force-push, history rewrite, or direct API source writes.
- Report Worktree path, branch, local/remote/PR HEAD SHAs, clean/dirty state, and actual test evidence in the PR handoff. If the remote task branch has been deleted after merge, check the PR's recorded head and merge ancestry instead of treating a stale remote-tracking ref as live.
- No rebase/force-push/recreate-branch/reset of published task history without explicit researcher authorization. Following an ordinary merge commit, an unchanged local PR HEAD should be an ancestor of `main`; if `git branch -d` fails, diagnose first. Squash/rebase merges have different ancestry semantics.

See the verification commands and divergence recovery steps in [docs/git-worktree-workflow.md](docs/git-worktree-workflow.md).

### Parallel development with Git Worktree

For concurrent nontrivial tasks, use **one Issue → one task branch → one Git Worktree → one Codex session → one Draft PR**. The main checkout stays stable; each task's editor, virtual environment and outputs should be isolated. Git Worktrees do **not** isolate shared databases or services. Always check local branch/status before editing; never modify or remove another task's Worktree. After a parallel PR merges, fetch and merge the newest `origin/main` into remaining active task branches, preserving both sides of documentation/evidence conflicts. The researcher approves merges and controls clean-up. Full setup, conflict-resolution and safe deletion instructions: [docs/git-worktree-workflow.md](docs/git-worktree-workflow.md).

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
