# Issue #9: fixed-target extstats maintenance CPU

This directory contains the independent fixed-target CPU campaign for
research Issue #9. It reuses the checked-in
experiments/pg-maintenance/fixture.sql weak-association and correlated
200,000-row tables. The historical Issue #7/v1-v5 directories are not
modified.

The experiment has 32 condition cells:

* two data regimes (weakassoc, correlated);
* two common targets (100 and 300);
* all eight subsets of the three two-column MCV objects ab, bc, and cd.

Each randomized repetition block contains every condition once. The
authorized campaign uses 20 blocks, hence 640 timed refreshes. Every
condition sets all ordinary column targets and all enabled MCV targets to the
same target. The requested sample size is recorded only from the pinned
PostgreSQL 16.14 source formula
max(100, 300 * max(ordinary target, extended-stat target)); the realized
sample tuple count is not claimed to be observed.

The primary measurement is the opt-in ESS_EXT_CPU_TRACE DEBUG1 record from
the Issue #9 PostgreSQL branch. The current instrumentation is named for MCV
tracing but wraps the complete extended-statistics phase; this fixture enables
only MCV objects. It uses backend getrusage(RUSAGE_SELF) and starts before the
extended-statistics catalog scan and ends after statistics objects are
serialized and persisted. The psql round-trip time is retained as a secondary
diagnostic only. Singleton medians independently predict each multi-object
incremental median:

sum_e median(CPU({e})) - (|M|-1) * median(CPU(empty)).

The analyzer resamples complete randomized blocks for 5,000 percentile
bootstrap replicates. It does not sum per-object timings from a multi-object
run.

## Offline preflight

From the repository root (pytest-style tests must be invoked through pytest):

    .venv/bin/python -m pytest -q experiments/pg-maintenance/fixed-target-cpu/test_fixed_target_cpu.py

The tests validate the 640-cell schedule, replay the committed v1 matrix
through the strict validator, and exercise negative metadata and trace-order
cases. The parser requires all CPU telemetry to be present in one ordered
stream; the v1 logs contain all 1,280 traces in stderr.

The recorded validation environment used pytest 8.4.2. The actual final test
outputs were:

    $ .venv/bin/python -m pytest --version
    pytest 8.4.2
    $ .venv/bin/python -m pytest -q experiments/pg-maintenance/fixed-target-cpu/test_fixed_target_cpu.py
    ........                                                                 [100%]
    8 passed in 0.62s
    # exit status: 0
    $ .venv/bin/python -m pytest -q experiments/pg-maintenance/test_analyze_benchmark.py experiments/pg-maintenance/fixed-target-cpu/test_fixed_target_cpu.py
    ..............                                                           [100%]
    14 passed in 0.68s
    # exit status: 0

The complete v1 run directory is covered by `SHA256SUMS`, except for the
manifest itself and the `checksums-verify.txt` transcript. Regenerate and
verify the derived manifest without touching raw measurements with:

    .venv/bin/python experiments/pg-maintenance/fixed-target-cpu/make_manifest.py \
      experiments/pg-maintenance/fixed-target-cpu/runs/20261018-issue9-v1
    .venv/bin/python experiments/pg-maintenance/fixed-target-cpu/make_manifest.py \
      experiments/pg-maintenance/fixed-target-cpu/runs/20261018-issue9-v1 --verify

## Isolated campaign

The live command is deliberately explicit and requires an already installed
Issue #9 PostgreSQL prefix:

    python3 experiments/pg-maintenance/fixed-target-cpu/run_isolated_fixed_target_cpu.py \
      --prefix /tmp/ess-pg-issue9-install \
      --source-commit 4ba5fcafe6ed62ecd40f34bbc2fdef3c917081a4 \
      --root /tmp/ess-pg-issue9-cpu-20261018 \
      --output-dir experiments/pg-maintenance/fixed-target-cpu/runs/20261018-issue9-v1 \
      --fixture experiments/pg-maintenance/fixture.sql \
      --database ess_issue9_cpu \
      --port 55439 \
      --seed 20261018 \
      --repetitions 20

The lifecycle wrapper uses a private data directory, socket, port, and
database, retains raw psql/lifecycle logs, verifies database absence while
the server remains running, then stops the server. It refuses to overwrite
an output directory. If any stage fails, the output is incomplete and must
not be used as a completed scientific result.

Offline replay, without PostgreSQL, is:

    python3 experiments/pg-maintenance/fixed-target-cpu/analyze_fixed_target_cpu.py \
      experiments/pg-maintenance/fixed-target-cpu/runs/20261018-issue9-v1/measurement/raw-observations.json \
      --output-dir experiments/pg-maintenance/fixed-target-cpu/runs/20261018-issue9-v1/analysis
