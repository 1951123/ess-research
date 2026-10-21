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


## Isolation and durability rule (supersedes any shared-build examples)

**Only original input data under `ESS_DATA_ROOT` may be shared across Issue/experiment environments**, and it should be treated read-only. Source code can of course be fetched by immutable Git commit from another repository; this is not permission to reuse a prior Issue's *runtime environment*. Never read another Issue's `pg-prefix`, PGDATA, sample binary, generated workload or virtualenv as an experiment dependency.

Each Issue/experiment must own its reproducible, disposable runtime beneath `ESS_RUNTIME_PARENT/<repository>/issue<N>/runs/<run-id>/`: its own pinned PostgreSQL source checkout, **fresh build and install**, cluster/PGDATA, Unix socket, ANALYZE sample, generated input copies, logs, intermediate files and outputs. A new run must not reuse a previous run's binary or database; a task Worktree may persist for source edits while runs remain separately owned. Its Python `.venv` belongs only to its development Worktree and must not be shared. Prefer PG out-of-tree builds, external temp paths and short sockets; some PG build tools write generated files inside their build tree, which must be outside the main checkout. If an unavoidable tool writes into a source tree, Codex must identify and relocate/clean the owned products rather than leave ignored litter. **No scripts should default to emitting generated files into main or a Git Worktree.** Do not treat a clean `git status` as proof there are no ignored artifacts.

The main checkout of **each** repository stays on `main`; branch edits run in Issue-specific Worktrees under the appropriate parent. Existing experiments, including ess-research Issue #64, must adopt these rules **before the next substantive run**: replace any hard-coded cross-Issue runtime/build reference (for example `issue38/pg-prefix`) with a per-Issue freshly compiled pinned PostgreSQL; record the source commit and actual built binary identity. Preserve historical results unchanged; do not rerun already completed pilots solely to rewrite history. The new rule does **not** authorize a new pilot, full calibration, or held-out test.

`ESS_RUNTIME_PARENT` is **scratch space, not a durable archive**. The researcher is not required to curate or keep its contents. Codex must distill essential and potentially expensive-to-recreate observations, input identities and full source/version pins into compact Git-tracked evidence that can be read and used to recompute scientific claims. Do not commit PGDATA, binaries, fixed samples, verbose traces or duplicate derivable outputs. Before undertaking expensive work, decide whether necessary evidence is small enough for Git; if not, obtain separate approval for an actual durable store **before** relying on local scratch. A sample hash proves identity, not recoverability of its bytes. Delete only owned scratch once indispensable evidence has been verified pushed; never silently destroy the sole copy of irreplaceable observations. No persistent cross-Issue artifact manager or shared binary cache is required.
