# Git Worktree + Codex collaboration workflow

This is the default development workflow for **nontrivial, independently scoped** ESS Research work. It complements [AGENTS.md](../AGENTS.md): GitHub Issues define scope, local VS Code/Codex performs implementation and experiments, Draft PRs preserve evidence for review, and **the researcher alone decides to merge**.

## Default lifecycle

**One scoped Issue → one branch → one Git Worktree → one Codex session → one Draft PR → review → researcher merge → clean up the Worktree.**

A small one-off documentation correction may use a simpler workflow when appropriate; do not create a Worktree for every trivial command or detached experiment. Multiple branches/Worktrees can coexist, but a single branch cannot normally be checked out in multiple Worktrees simultaneously.

## Configure the three persistent roots

The user explicitly chooses exactly three stable roots, for example in `~/.bashrc`:

```sh
# Examples only, never built-in defaults. Do not edit profiles automatically.
export ESS_DATA_ROOT="$HOME/ess-data"
export ESS_WORKTREE_PARENT="$HOME/ess-worktrees"
export ESS_RUNTIME_PARENT="$HOME/ess-runtime"
```

- `ESS_DATA_ROOT` contains **network-origin raw archives only**. For AreCEL the
  sole shared data input is `arecel-data.tar.gz`, checked against its pinned
  whole-archive SHA-256. No extracted CSV, pickle, canonical, audit, logs, or
  experiment outputs belong here.
- `ESS_WORKTREE_PARENT` holds task Worktrees at `<repo>-issueNN`.
- `ESS_RUNTIME_PARENT` holds disposable derived data and isolated execution
  resources at `<repo>/issueNN/runs/<unique-run-id>/`.

Missing/empty/invalid needed variables fail with an actionable configuration
message. A valid nonexistent root may be created by its owning workflow. Check
only the roots the operation needs: Worktree creation needs its parent; ETL
needs data/runtime roots. Imports, tests, and read-only Git checks need none.
Never substitute a CLI path for a missing required variable or search historical
roots. `ESS_ISSUE_ROOT` may identify one run **within the current task process**;
never globally pin it, PGDATA, PGHOST, or PGPORT in a shell profile.

## Codex shell startup: load the configured roots explicitly

New Codex sessions and tool invocations may use non-interactive Bash, which does **not** reliably load `~/.bashrc` by itself. **Explicitly source `~/.bashrc` in the Bash process that needs the configured roots**, including when starting a new session:

```bash
source ~/.bashrc
: "${ESS_DATA_ROOT:?ESS_DATA_ROOT must be set}"
: "${ESS_WORKTREE_PARENT:?ESS_WORKTREE_PARENT must be set}"
: "${ESS_RUNTIME_PARENT:?ESS_RUNTIME_PARENT must be set}"
```

Only check variables needed for the current operation. If a command runner starts a fresh shell for each call, sourcing in an earlier invocation is **not persistent**; start dependent commands with `source ~/.bashrc && ...` in the **same Bash invocation**, or pass a previously verified environment explicitly. Do not assume a login shell, alter the researcher's shell profiles, invent default paths, or expose environment contents/secrets in logs. An interactive-only guard inside `~/.bashrc` can prevent exports; if verification fails, stop and report which required variable is missing. Merely creating a `~/.bash_profile` or setting `BASH_ENV` does not guarantee the Codex executor will inherit a changed environment.

## Create a task workspace

Verify the existing checkout and live state first:

```sh
pwd
git rev-parse --show-toplevel
git branch --show-current
git status --short
git worktree list
git fetch origin
```

Resolve an explicitly assigned Issue (replace `53` and the branch below). The
small helper validates the configured parent without creating or finding another
task's directory. `--no-track` prevents accidental upstream `origin/main`:

```sh
TASK_WORKTREE=$(PYTHONPATH=src python3 -c \
  'from ess_research.task_paths import worktree_path; print(worktree_path("ess-research", 53))') || exit 1
mkdir -p "$ESS_WORKTREE_PARENT"
git worktree add --no-track -b fix/issue53-archive-first-etl "$TASK_WORKTREE" origin/main
```

Open that Worktree in a separate VS Code window and start its own Codex session.
Give the agent the Issue, permitted scope, evidence requirements, and Draft PR
handoff requirement. Recheck path/branch/status before edits. Each Issue owns its
`.venv/`, working files, and outputs. Worktrees do not isolate shared services.

## Shared raw archive, disposable Issue/run derivation

[The AreCEL preparation API](arecel-real-etl.md) downloads on a missing cache,
verifies the whole archive, and prepares any one dataset independently. Derived
CSV/workload/truth files are computed within a unique Issue/run, never published
as a permanent cross-Issue input. No manual `tar`, separate gated converter,
canonical/audit prerequisites, or compatibility bridge is needed.

Use its context-managed API or CLI consuming command so PG import/measurement
finishes before owned derived files are cleaned. Retain only the owning
experiment's minimal scientific evidence (source IDs, frozen protocol, actual
measurements) in `results/` or its versioned evidence bundle. `--keep-scratch`
is an explicit debug option. The ETL removes only its own `derived/` directory;
it does not shut down clusters, remove PGDATA, delete results, migrate historical
outputs, or touch the researcher's backup. Historical evidence is preserved.

### Independent PostgreSQL per Issue

Every Issue that needs PostgreSQL starts and owns its **own isolated cluster**, even if another Issue uses the same PG fork/binaries and the same verified CSV. Unique PGDATA, socket directory, port, logs, database objects and statistics are mandatory. A single shared installed PostgreSQL binary can be reused *if its build is immutable and commit/build options are pinned*; Issues requiring different instrumentation/build flags use separate builds. No Issue may connect to, `ANALYZE`, `DROP`, change GUCs in, or shut down another Issue's cluster.

Illustrative setup **after verifying paths and allocating an unused port**:

```sh
# ESS_ISSUE_ROOT is supplied by the current consuming run, not a global setting.
: "${ESS_ISSUE_ROOT:?use the current Issue/run root}"
export PGDATA="$ESS_ISSUE_ROOT/pgdata"
export PGHOST="$ESS_ISSUE_ROOT/socket"
export PGPORT=55NNN  # replace with a real unused integer port; not a literal value
mkdir -p "$ESS_ISSUE_ROOT"/{socket,logs,results}
# Use the explicitly pinned PostgreSQL build for this Issue:
# /path/to/pg/bin/initdb -D "$PGDATA"
# /path/to/pg/bin/pg_ctl -D "$PGDATA" -o "-k $PGHOST -p $PGPORT" -l "$ESS_ISSUE_ROOT/logs/server.log" start
```

Do not rely on the example port or assume the example paths exist. Avoid concurrent port allocation races; check ownership before starting and record the chosen port/build hash in the Issue's evidence manifest. Use disposable research databases, and import the frozen dataset separately into each Issue cluster. Fixed-sample `ANALYZE` files and their SHA-256 identities are **per-Issue artifacts**, not shared mutable resources. Shutdown the owned cluster with its matching `pg_ctl` before cleaning up; never recursively delete `PGDATA` merely because a Worktree was removed.

### Python environment per Worktree

Use **one independent `.venv/` per Worktree**, not a sibling repository's or another Issue's environment. The same Python package download/wheel cache can be shared; installed environments cannot. `.venv/` is ignored by Git and may be safely recreated from a pinned Python version and the repository's declared requirements/lock/constraints.

```sh
cd /path/to/current/ess-research-issueNN
python3 -m venv .venv
.venv/bin/python -m pip install --upgrade pip
# Install from the existing project-approved dependency or lock specification.
# Example ONLY if this repo defines a "dev" extra:
# .venv/bin/python -m pip install -e '.[dev]'
.venv/bin/python -m pytest -q
.venv/bin/python -m pip freeze > "$ESS_ISSUE_ROOT/results/python-packages.txt"
```

Inspect `pyproject.toml` and the project's real dependency instructions before choosing an install command. Do **not** assume `.[dev]` exists or silently borrow `ess-advisor/.venv`. Capture the Python executable/version, resolved dependency versions and exact test commands; use pinned dependency versions or a lock/constraints file for numerical reproducibility. For cross-repository calls, execute each project with its **own** environment or a deliberately documented, pinned integration environment. Do not commit the virtual environment itself.

## Mandatory Git push / GitHub PR synchronization gate

**Canonical source-writer: local Issue Worktree Git only.** This applies to Codex even when GitHub API/MCP permissions are available. Edit and commit repository files (including research evidence) locally, then push the exact local commit. GitHub API/MCP may inspect repository state and create/update Issue or PR metadata and comments; **never use contents/Git-data APIs to create or edit source files, create task commits, or construct a parallel remote history** without explicit task-specific authorization. Approval to use GitHub API generally is **not** approval to write source commits through it. In the exceptional authorized API-write case, stop and coordinate fetch/integration into the same local branch before another local edit; record the resulting SHA chain.

### Start: bind the Issue branch to its same-named remote, not `origin/main`

```sh
# Execute INSIDE the Issue's dedicated Worktree, after replacing the placeholder.
BRANCH=research/issueNN
test "$(git branch --show-current)" = "$BRANCH" || exit 1
git rev-parse --show-toplevel
git status --short
git worktree list
git branch -vv

# If upstream is wrong (e.g., origin/main) but the remote Issue branch EXISTS:
# git branch --set-upstream-to="origin/$BRANCH" "$BRANCH"
# If the remote Issue branch does not yet exist, the first successful push -u
# below establishes the correct upstream. Never assume origin/main is valid.
```

Do not change upstream or push until you have checked for a live, possibly divergent remote branch. A branch created with `git worktree add -b ... origin/main` may initially track `origin/main`, so the branch name alone is **not** evidence of correct upstream configuration.

### Before handing off or updating a Draft PR: three-way SHA gate

```sh
# Replace with the real current task branch, and run in its own Worktree.
BRANCH=research/issueNN
test "$(git branch --show-current)" = "$BRANCH" || exit 1
test -z "$(git status --porcelain)" || {
  echo "FAIL: Worktree contains uncommitted/untracked files; inspect first"
  exit 1
}

# Inspect live remote BEFORE pushing. If it exists and is not an ancestor of
# HEAD, STOP and investigate. Do not force-push or overwrite API-created commits.
git fetch --prune origin
REMOTE_BEFORE=$(git ls-remote --heads origin "refs/heads/$BRANCH" | cut -f1)
if test -n "$REMOTE_BEFORE"; then
  git merge-base --is-ancestor "$REMOTE_BEFORE" HEAD || {
    echo "FAIL: remote HEAD is not in local history; resolve divergence"
    exit 1
  }
fi

# Only after the pre-push check passes:
git push -u origin "HEAD:refs/heads/$BRANCH" || exit 1
LOCAL_SHA=$(git rev-parse HEAD)
REMOTE_SHA=$(git ls-remote --heads origin "refs/heads/$BRANCH" | cut -f1)
test -n "$REMOTE_SHA" && test "$LOCAL_SHA" = "$REMOTE_SHA" || {
  echo "FAIL: local and live remote HEAD differ"
  exit 1
}
echo "PASS: local and live remote HEAD = $LOCAL_SHA"
```

**Then check the actual GitHub PR `head.sha` using GitHub API/CLI or the PR page.** It must equal `LOCAL_SHA`; check again before final review or researcher merge. A local `origin/$BRANCH` remote-tracking reference may be stale and does **not** substitute for `git ls-remote`. If another actor changes the remote after verification, re-run this gate. Never report "pushed/ready" without these checks.

At PR handoff, report: repository/Worktree path, Issue and branch, clean/dirty status, local SHA, live remote SHA, PR head SHA, tests actually run, and any exceptions. Source-changing PRs created by this workflow should use the same real branch as the local Worktree.

### Divergence and merge cleanup

If local and remote HEAD disagree, **stop all writes** and inspect `git log --left-right --graph --oneline HEAD...origin/<issue-branch>` after fetch, `git branch -vv`, the live remote SHA, and the PR head SHA. Do not automatically reset/rebase, cherry-pick blindly, force-push, or create an API-only alternative history. Ask the researcher to approve the reconciliation plan.

After PR merge, remote task branches may be deleted; `origin/<issue-branch>` can remain as a stale ref until `git fetch --prune origin`. Verify the PR's recorded final `head.sha`, its merge commit, and whether the local branch's HEAD is in the merged ancestry. With **Create a merge commit**, matching local PR HEAD normally lets `git branch -d` work; if the local branch has later unmerged commits or a parallel history, `-d` correctly refuses even if file trees match. For **Squash** or **Rebase and merge**, identical final content does not imply commit ancestry; a careful, researcher-approved `-D` may be warranted only after confirming no unmatched work/evidence remains. Do not create archive branches by default or delete Worktrees with unsaved outputs.

## Concurrent work and PR review

- Scope tasks to avoid editing the same files when possible. Changes to common status or documentation may still conflict; this is normal and must be resolved semantically.
- Commit and push only the current task branch. Open one reviewable **Draft PR** per bounded task with commands actually run, tests/CI status, hashes/provenance, limitations and relevant Issue link.
- The reviewer can comment or request changes; Codex continues on the **same task branch**. No agent auto-merges, force-pushes, resets unrelated work or deletes someone else's Worktree.
- GitHub changes are **not automatically present locally**. Fetch before checking out, comparing or merging the newest remote branch.
- When another PR merges into `main`, synchronize an active task branch (after ensuring local edits are safely committed or otherwise preserved):

```sh
git fetch origin
git merge origin/main
# Resolve conflicts carefully, preserving BOTH merged work and current task's evidence.
# Run affected tests/evidence checks, commit the resolution, push normally.
```

For example, when two tasks edit `docs/STATUS.md`, preserve both sets of research findings; do not blindly accept one whole side of the conflict. Prefer a merge on a shared PR branch rather than rebasing published commits and force-pushing unless expressly coordinated. Confirm the new PR head's CI has completed successfully before recommending merge.

## After the researcher merges

First verify the PR is merged and local task work is saved. Close running editors, Python jobs and other processes using those directories. In the **main checkout**:

```sh
git status --short
git switch main
git fetch origin
git pull --ff-only origin main
git worktree list

git -C "$ESS_WORKTREE_PARENT/ess-research-issueNN" status --short
git -C "$ESS_WORKTREE_PARENT/ess-research-issueMM" status --short

# Only when both are clean and contain nothing else to retain:
git worktree remove "$ESS_WORKTREE_PARENT/ess-research-issueNN"
git worktree remove "$ESS_WORKTREE_PARENT/ess-research-issueMM"
git worktree list

# Optional local branch cleanup AFTER verifying merge/retention:
git branch -d experiment/issueNN
git branch -d research/issueMM
```

If worktree removal complains about modified/untracked files, inspect and preserve them; **do not use `--force` or `rm -rf` as a shortcut**. If `git branch -d` refuses after a squash merge, Git may not recognize the old branch as merged: verify all needed changes are retained in `main` before choosing any stronger deletion. No need to delete remote branches automatically.

## Safety and evidence boundary

- The main checkout is the stable integration view; keep research tasks on bounded branches.
- Check the *actual* local path/branch/status before destructive operations, not a guessed path from a previous chat.
- Do not inspect hidden historical clones, implicit benchmark-data directories or another project's worktrees to work around missing input.
- Protect old experiment evidence and preserve accuracy labels: mathematical proof, source-derived observation, experimentally executed result, and open conjecture are different.
- A completed GitHub PR/Issue does not prove local worktree cleanup has happened; cleanup is a distinct, human-controlled step.
