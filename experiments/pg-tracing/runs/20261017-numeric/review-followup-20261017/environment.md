# Issue #5 review follow-up: environment and provenance

Date: 2026-10-17 (Asia/Shanghai)

## Repository identities

- `ess-postgresql` PR #2 branch: `experiment/mcv-numeric-trace-20261017`
- PostgreSQL instrumentation commit: `2891af8ade29a9b584d6c0fb969e311a10230282`
- PostgreSQL parent used for the build: `bb532b919afbf6fe0fc0435b3f9628ff747f7ed2`
- Official PostgreSQL ancestor: `0d1c00c624fa7367d4a895f44381887757289682`
- `ess-research` PR #6 branch: `experiment/mcv-numeric-validation-20261017`
- Research HEAD before follow-up edits: `d454f028e3c1e7572eb471015f69b87a853864f9`

The disposable source worktree was at `/tmp/ess-pg-mcv-numeric-src`. Its
`HEAD` was the PostgreSQL parent above plus the uncommitted two-file diagnostic
diff. The diff is byte-for-byte identical to the patch in PostgreSQL PR #2;
its SHA256 is:

```text
caa5828349f8207d26728a71ef61c115f81453689a7c361b88d5239b5026b608
```

## Build and runtime

The already-built diagnostic installation was reused because the follow-up
requires no PostgreSQL source change:

```text
/tmp/ess-pg-mcv-numeric-install/bin/postgres --version
postgres (PostgreSQL) 16.14
```

Binary SHA256 values:

```text
22136a9e88a5f40270cca618b1e4ba7f2fd4f48f0aa18e2eb6b824bbc88ed702  postgres
fa2272f438c91b51128d7d0a6d08b23df204ae88969a8227969fd8f40428aaf5  psql
b470f914283083bd681e5b1e9b8e568ba17a5b4fd3b0adc4a8142e6be6947639  pg_ctl
```

The build command for this installation was:

```text
env CFLAGS='-DESS_MCV_NUMERIC_TRACE' ./configure \
  --prefix=/tmp/ess-pg-mcv-numeric-install \
  --enable-debug --enable-cassert --without-readline --without-zlib
make -j2
make install
```

The compiler was GCC 13.3.0 on x86_64 Ubuntu 24.04. The instrumentation is
compile-time opt-in and the SQL marker further limits output to these
controlled queries.

## Exact follow-up command sequence

The isolated cluster and database were created, used, and stopped as follows:

```text
/tmp/ess-pg-mcv-numeric-install/bin/initdb \
  -D /tmp/ess-pg-mcv-followup-data --no-locale --encoding=UTF8
/tmp/ess-pg-mcv-numeric-install/bin/pg_ctl \
  -D /tmp/ess-pg-mcv-followup-data \
  -o '-k /tmp/ess-pg-mcv-followup-socket -p 55436' \
  -l /tmp/ess-pg-mcv-followup-server.log -w start
/tmp/ess-pg-mcv-numeric-install/bin/createdb \
  -h /tmp/ess-pg-mcv-followup-socket -p 55436 ess_followup
/tmp/ess-pg-mcv-numeric-install/bin/psql -X \
  -h /tmp/ess-pg-mcv-followup-socket -p 55436 -d ess_followup \
  -f experiments/pg-tracing/mcv_numeric_followup.sql \
  > review-followup-20261017/psql.stdout.log \
  2> review-followup-20261017/psql.stderr.log
/tmp/ess-pg-mcv-numeric-install/bin/pg_ctl \
  -D /tmp/ess-pg-mcv-followup-data -m fast -w stop
/tmp/ess-pg-mcv-numeric-install/bin/pg_ctl \
  -D /tmp/ess-pg-mcv-followup-data status
```

The SQL script contains two distinct table snapshots. It runs exactly one
`ANALYZE` for `ess_mcv_partial_t` and one for
`ess_mcv_heterogeneous_t`; no statistics are regenerated between availability
scenarios. Each scenario uses transactional `DROP STATISTICS` followed by
`ROLLBACK` and `DISCARD PLANS`.

The final status command reported `pg_ctl: no server running` with exit code
3, and the data directory had no `postmaster.pid`. No protected or production
database was contacted.

## Source files

```text
c7c22a4e0fd4503e021b667a855558e8587eb76b0934cffe369566fec8f673a  experiments/pg-tracing/mcv_numeric_followup.sql
3622d7470a3bbdded13ee0ba2f2c1c79e0ef6934463d7231040f88c2820d8244  experiments/pg-tracing/analyze_mcv_numeric_followup.py
```

The raw logs and analysis output are checksummed in
[`SHA256SUMS`](SHA256SUMS). The strict checker uses relative tolerance
`1e-12` and absolute tolerance `1e-15`, and its acceptance status is recorded
in [`numeric-followup-analysis.json`](numeric-followup-analysis.json).
