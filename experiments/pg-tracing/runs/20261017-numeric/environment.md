# Fixed-snapshot MCV numeric validation environment

Date: 2026-10-17 (Asia/Taipei)

## Repository identities

- `ess-postgresql` experiment branch: `experiment/mcv-numeric-trace-20261017`
- PostgreSQL source commit: `2891af8ade29a9b584d6c0fb969e311a10230282`
- PostgreSQL parent/main before the diagnostic commit: `bb532b919afbf6fe0fc0435b3f9628ff747f7ed2`
- PostgreSQL upstream ancestor: `0d1c00c624fa7367d4a895f44381887757289682`
- `ess-research` experiment branch: `experiment/mcv-numeric-validation-20261017`
- Research base before this experiment: `5469ed8bbed4cad1c43cf067954b96c5a2f51ea3`

The PostgreSQL branch contains only opt-in diagnostic instrumentation. The
research branch contains the fixture, parser, raw evidence and report.

## Build

The source was built in the disposable detached worktree
`/tmp/ess-pg-mcv-numeric-src` and installed in
`/tmp/ess-pg-mcv-numeric-install`:

```text
env CFLAGS='-DESS_MCV_NUMERIC_TRACE' ./configure \
  --prefix=/tmp/ess-pg-mcv-numeric-install \
  --enable-debug --enable-cassert --without-readline --without-zlib
make -j2
make install
```

Observed version: PostgreSQL 16.14. Compiler: GCC 13.3.0
(`Ubuntu 13.3.0-6ubuntu2~24.04.1`). Platform: x86_64 Ubuntu 24.04.

## Isolated runtime

The valid run used:

- data directory: `/tmp/ess-pg-mcv-numeric-data-3`
- Unix socket directory: `/tmp/ess-pg-mcv-numeric-socket-3`
- port: `55435`
- server log: `success-instrumented/server.log`

The cluster was initialized solely for this fixture. `pg_ctl status` after
the run reported `no server running`, and `postmaster.pid` was absent. No
production database or pre-existing test instance was contacted.

The first SQL attempt failed before measurements because the fixture used
nonexistent `pg_statistic` column names; its logs are retained under
`failed-initial/`. A second SQL run completed without the new numeric
instrumentation because its temporary build predated the uncommitted source
diff; those logs are retained but are explicitly invalid. The valid result is
the `success-instrumented/` run after rebuilding the instrumented source.

## Valid command

```text
PGHOST=/tmp/ess-pg-mcv-numeric-socket-3 PGPORT=55435 \
  /tmp/ess-pg-mcv-numeric-install/bin/psql -X -v ON_ERROR_STOP=1 \
  -d postgres \
  -f experiments/pg-tracing/mcv_numeric_snapshot.sql \
  > success-instrumented/psql.stdout.log \
  2> success-instrumented/psql.stderr.log

python3 experiments/pg-tracing/analyze_mcv_numeric.py \
  --stdout success-instrumented/psql.stdout.log \
  --stderr success-instrumented/psql.stderr.log \
  --output success-instrumented/numeric-analysis.json
```

The fixture performs exactly one `ANALYZE`. Availability scenarios use
transactional `DROP STATISTICS` followed by `ROLLBACK`; no later ANALYZE is
performed.

## Evidence checksums

Final source and valid-run checksums:

```text
724cc4dbb8165cff8927a9daace1ddd27a5af18bb26dcdadf0a7ede04f37cb83  experiments/pg-tracing/mcv_numeric_snapshot.sql
558c3c81f97905cca21a0f3036c3853d01e244ae002d1db170f419c625f5c098  experiments/pg-tracing/analyze_mcv_numeric.py
1a90c60ca90b1fc9f23b51b1ca9de05032a9ef454544c1f02d439a765b2df44e  success-instrumented/psql.stderr.log
15ca79dc55d5b8723b8452b35162d2658b3d8213789b8a0fb95da1277fe2dac0  success-instrumented/psql.stdout.log
d96bbce975f9192bc336d157e2c3cafbd6706e57d8c71d72d9a12ff309dcbcb1  success-instrumented/numeric-analysis.json
626fbf67cb347731c841fe12161fd6ad2200646689a320fbd53a287acdc5c357  success-instrumented/server.log
eb5af2fdcd95d427dcb455ea767968778f9a34cf6266e8567ca83bfa424cc789  success-instrumented/initdb.log
ca19178a35ab4153b75b494963b66ce8243e1b94c173107c87b44d09db23652d  success-instrumented/stop.log
```

The failed and invalid attempt files have their own hashes in the local
`sha256sum` audit output and remain separate from the valid evidence. Re-run
the following after any deliberate evidence change:

```text
sha256sum success-instrumented/*
sha256sum failed-initial/*
```
