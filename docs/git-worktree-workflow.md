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

Keep each Worktree's Python `.venv`, cache, scratch output and experiment output independent. **Worktrees isolate working files and branch checkout, not shared services:** also isolate PostgreSQL instances, ports, credentials, mutable databases and data/output roots if tasks touch them. Never run conflicting jobs against a shared database/data directory or silently change another repository.

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
