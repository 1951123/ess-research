# Git Worktree + Codex collaboration workflow

This is the default development workflow for **nontrivial, independently scoped** ESS Research work. It complements [AGENTS.md](../AGENTS.md): GitHub Issues define scope, local VS Code/Codex performs implementation and experiments, Draft PRs preserve evidence for review, and **the researcher alone decides to merge**.

## Default lifecycle

**One scoped Issue → one branch → one Git Worktree → one Codex session → one Draft PR → review → researcher merge → clean up the Worktree.**

A small one-off documentation correction may use a simpler workflow when appropriate; do not create a Worktree for every trivial command or detached experiment. Multiple branches/Worktrees can coexist, but a single branch cannot normally be checked out in multiple Worktrees simultaneously.

## Create two independent task workspaces

Illustrative layout (adjust paths to the actual clone; do not assume this path exists):

```text
<parent>/ess-research/              # stable main checkout
<parent>/ess-research-issueNN/      # issue NN branch, Codex session A
<parent>/ess-research-issueMM/      # issue MM branch, Codex session B
```

Run from the existing `ess-research` checkout, after verifying the repository, current branch and uncommitted work:

```sh
git status --short
git worktree list
git fetch origin

# Replace numbers and branch names for actual tasks; do not reuse existing paths/branches.
git worktree add -b experiment/issueNN ../ess-research-issueNN origin/main
git worktree add -b research/issueMM ../ess-research-issueMM origin/main
```

Open **each Worktree as a separate VS Code window** and start a **separate Codex conversation** in that window. Give each agent its Issue link, permitted scope, evidence requirements, and the instruction to work **only in its current Worktree/branch** and to submit a Draft PR without merging. Check `pwd`, `git branch --show-current`, `git status --short`, and `git worktree list` in each window before edits. Read `AGENTS.md`, research context, decisions, status, and relevant source artifacts before changing anything.

Keep each Worktree's Python `.venv`, cache, scratch output and experiment output independent. **Worktrees isolate working files and branch checkout, not shared services.** See the mandatory runtime isolation policy below.

## Shared immutable inputs, isolated Issue runtime

**Rule: share verified immutable datasets; isolate all mutable execution state per Issue.**

- `ESS_DATA_ROOT` names a researcher-approved, persistent directory **outside Git repositories and Worktrees** (example: `/home/wqts/ess-data`). It holds verified, hash-pinned raw sources and canonical read-only inputs. Multiple Issues may read these same bytes. Do not modify them in place; generate a newly versioned derived artifact for changes, preserve source checksums, and do not infer an unapproved path.
- `ESS_ISSUE_ROOT` names a **unique directory for the current Issue** (example: `/home/wqts/ess-runtime/issueNN`); each Issue owns its `pgdata/`, `socket/`, `logs/`, `results/` and temporary outputs. Never put mutable PG files, sample exports, generated stats or calibration data into the shared immutable-input tree. For reproducibility, pin hashes of inputs copied into each Issue.
- `--data-root` overrides `ESS_DATA_ROOT`; if neither is supplied, real-data commands fail closed. An environment variable only selects an input root: it does not establish that the data exists or passes validation. Do not silently substitute a synthetic instance.
- Treat derived ETL outputs as **versioned immutable snapshots** when shared across Issues, or keep them under each `ESS_ISSUE_ROOT` if mutable. Never overwrite another Issue's outputs.
- `ESS_DATA_ROOT` may be a shell/profile-level setting; `ESS_ISSUE_ROOT`, `PGDATA`, `PGHOST` and `PGPORT` must be configured separately in each VS Code/Codex task terminal. Never store credentials in committed files.

### Independent PostgreSQL per Issue

Every Issue that needs PostgreSQL starts and owns its **own isolated cluster**, even if another Issue uses the same PG fork/binaries and the same verified CSV. Unique PGDATA, socket directory, port, logs, database objects and statistics are mandatory. A single shared installed PostgreSQL binary can be reused *if its build is immutable and commit/build options are pinned*; Issues requiring different instrumentation/build flags use separate builds. No Issue may connect to, `ANALYZE`, `DROP`, change GUCs in, or shut down another Issue's cluster.

Illustrative setup **after verifying paths and allocating an unused port**:

```sh
export ESS_DATA_ROOT=/home/wqts/ess-data
export ESS_ISSUE_ROOT=/home/wqts/ess-runtime/issueNN
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

git -C ../ess-research-issueNN status --short
git -C ../ess-research-issueMM status --short

# Only when both are clean and contain nothing else to retain:
git worktree remove ../ess-research-issueNN
git worktree remove ../ess-research-issueMM
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
