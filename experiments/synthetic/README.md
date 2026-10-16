# Synthetic PESS-ESS experiments

This directory contains the first reproducible synthetic study for the
two-column maximal-matching PESS-ESS prototype.

The Advisor implementation is installed into the independent Research
environment as an editable local package:

    cd /home/wqts/projects/ess-research
    .venv/bin/python -m pip install -e /home/wqts/projects/ess-advisor
    .venv/bin/python experiments/synthetic/scripts/run_suite.py

The command writes fixed-seed instances to instances/, machine-readable
measurements to results/, and a short measured report to report.md.
Generated caches and temporary solver files are not part of the study.

Every solver result is labeled with its status. A time-limited or failed
solver result is retained as unresolved and is not treated as an optimum.
The exhaustive reference is intentionally restricted to the small cases.
