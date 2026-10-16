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
