# ESS Research

Research repository for budgeted pessimistic extended-statistics selection under admissible estimation schemes and maintenance-cost constraints.

The general formulation selects a resource set (M), admits estimation schemes through \(\Gamma_i(M)\), measures estimation losses \(\ell_i\), and constrains an abstract maintenance-cost function \(\operatorname{Maint}(M)\) by a single maintenance budget \(B\). The PostgreSQL two-column MCV case is a narrower instantiation, not the definition of the general problem.

Related repositories:

- [ess-postgresql](https://github.com/1951123/ess-postgresql): PostgreSQL source and future ESS integration work.
- [ess-advisor](https://github.com/1951123/ess-advisor): implementation of admissibility, estimation, maintenance-cost, and optimization components.

Synthetic prototype experiments are in
experiments/synthetic/. Install the local Advisor package into this
repository's independent virtual environment with
.venv/bin/python -m pip install -e /home/wqts/projects/ess-advisor, then
run experiments/synthetic/scripts/run_suite.py.

The bounded Forest10 ETL input boundary is documented in
[docs/arecel-forest10-etl.md](docs/arecel-forest10-etl.md), with the four-dataset
source inventory in [docs/arecel-asset-inventory.md](docs/arecel-asset-inventory.md).
It requires an explicit, independently verified data root; no historical
checkout or hidden benchmark-data default is used.


## Research collaboration and continuity

This repository is the **durable research context** shared by the researcher,
ChatGPT (theory/design/review), and local VS Code/Codex (implementation and
experimental execution). Start with:

- [Research context](docs/RESEARCH_CONTEXT.md) — problem definition, scope, cross-repo roles, and primary evidence.
- [Decision log](docs/DECISIONS.md) — accepted directions, rejected alternatives, and revisit conditions.
- [Current status](docs/STATUS.md) — active work, draft PRs, evidence status, and next actionable task.
- [Agent instructions](AGENTS.md) — safe, reproducible Codex/research-agent task rules.

A new ChatGPT conversation should read these files and check linked open PRs
before giving project-specific advice. Status claims must distinguish mathematical
results, version-scoped source inspection, executed experiments, and open questions.
Changes proposed in a Draft PR have **not** yet entered `main` or automatically
synchronized to the researcher's local clone.

## Parallel development with Git Worktree

For independent research and engineering tasks, we use **one Issue → one branch → one Git Worktree → one Codex session → one Draft PR**. Keep `main` as the stable integration checkout; review and merge are researcher-controlled. See the [Git Worktree + Codex workflow](docs/git-worktree-workflow.md) for creation, isolated environments, parallel PR conflict handling, and safe cleanup.
