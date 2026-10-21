# Three-repository development conventions

ESS uses three independent Git repositories: **ess-research** owns research definitions, experimental approvals, evaluation and evidence; **ess-postgresql** owns PostgreSQL source, builds and PG tests; **ess-advisor** owns advisor algorithms, package and tests. ess-research coordinates scientific decisions, but is **not** the Git parent or write authority of the other repositories.

## Local directories

Keep the existing exports and their meanings; do not rename them:

```bash
export ESS_DATA_ROOT="$HOME/ess-data"
export ESS_RUNTIME_PARENT="$HOME/ess-runtime"
export ESS_WORKTREE_PARENT="$HOME/projects/ess-research/.worktrees"
```

Optional conveniences for new worktrees in the other two repositories:

```bash
export ESS_PG_WORKTREE_PARENT="$HOME/projects/ess-postgresql/.worktrees"
export ESS_ADVISOR_WORKTREE_PARENT="$HOME/projects/ess-advisor/.worktrees"
```

The last two variables are **optional conventions**, not prerequisites for existing commands. If absent, explicitly choose the target worktree directory when creating it; never guess a runtime or data root. Agents must source and verify needed exports **in their current shell** before path-dependent commands; noninteractive shells may not inherit `~/.bashrc`.

`ESS_DATA_ROOT` is for shared original inputs, not cross-run mutable derived data. Under `ESS_RUNTIME_PARENT`, separate artifacts by repository / Issue / run and never overwrite another run. Preserve essential reproducibility metadata and compact reports; do not commit PostgreSQL builds, large data, fixed ANALYZE sample binaries, trace logs, virtual environments or secrets. Apply each repository's own `AGENTS.md` and `.gitignore`.

## Independent work and cross-repo consumption

- One Issue → one branch → one Git worktree → one Codex session → one Draft PR, within **each** repository. `main` remains the stable integration checkout. Researcher approves merges and destructive cleanup.
- By default an agent may inspect another repository read-only, but cannot edit it or run its experiments without explicit authorization.
- Consumers record an **immutable full commit SHA**, repository URL, and applicable build/version in their own experiment configuration or PR evidence. A development branch name is only a locator, never a reproducibility pin. Do not copy another repository's source into this one.
- The PostgreSQL EXPLAIN diagnostic interface from ess-postgresql PR #7 can be evaluated in a separate pinned build without overwriting the prior PG binary or abandoning the validated log-trace baseline. Any new integration requires its own bounded validation before full calibration.
- A code-review approval, a local build, a bounded pilot and authorization for full calibration/test are separate decisions. Do not run full valid calibration or official held-out test without explicit researcher approval. Do not use test outcomes to tune resource choice.
- Follow [AGENTS.md](../AGENTS.md), [docs/git-worktree-workflow.md](git-worktree-workflow.md) and the active Issue's protocol for additional research-specific rules.

These conventions are coordination guidance, not a monorepo, central tooling layer or new dependency manager.
