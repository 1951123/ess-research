# 2026-10-17 PostgreSQL MCV tracing run

This directory contains the raw evidence for the controlled pairwise-MCV
runtime check. The SQL fixture was executed once against an isolated
PostgreSQL instance.

## Source and build

- `ess-postgresql` branch: `research/ess-mcv-trace-20261017`
- source commit: `e17bfdf0c871bec02bea8c979b29d7603772b14d`
- upstream parent: `0d1c00c624fa7367d4a895f44381887757289682`
- Research branch: `experiment/pg-mcv-trace-20261017`
- PostgreSQL: `16.14`
- host: `Linux 7.0.0-38-generic x86_64 GNU/Linux`
- compiler: `gcc (Ubuntu 13.3.0-6ubuntu2~24.04.1) 13.3.0`
- configure: `configure --prefix=/tmp/ess-pg-trace-install --enable-debug --enable-cassert --without-readline --without-zlib`
- build: `make -j2`
- install: `make install`

The effective build directory was the clean
`/home/wqts/projects/ess-postgresql` worktree checked out at the tracing
branch. A detached `/tmp/ess-pg-trace-src` worktree at the same commit supplied
the source path for the configure invocation. The source diff relative to the
upstream parent is the reviewed 13-line `DEBUG1` instrumentation in
`src/backend/statistics/extended_stats.c`.

## Isolated runtime

- install prefix: `/tmp/ess-pg-trace-install`
- data directory: `/tmp/ess-pg-trace-data`
- Unix socket directory: `/tmp/ess-pg-trace-socket`
- port: `55432`
- database: `postgres`
- table created by fixture: `ess_trace_t`
- log minimum: `debug1`
- database was initialized with `initdb --no-locale --encoding=UTF8 -U wqts`

Commands used:

```text
git fetch origin research/ess-mcv-trace-20261017
git switch research/ess-mcv-trace-20261017
cd /home/wqts/projects/ess-postgresql
/tmp/ess-pg-trace-src/configure --prefix=/tmp/ess-pg-trace-install --enable-debug --enable-cassert --without-readline --without-zlib
make -j2
make install
initdb -D /tmp/ess-pg-trace-data --no-locale --encoding=UTF8 -U wqts
pg_ctl -D /tmp/ess-pg-trace-data -l /tmp/ess-pg-trace-run/server.log -o "-p 55432 -k /tmp/ess-pg-trace-socket -c log_min_messages=debug1 -c log_line_prefix='%m [%p] %u@%d '" start
PGHOST=/tmp/ess-pg-trace-socket PGPORT=55432 psql -X -v ON_ERROR_STOP=1 -d postgres -f experiments/pg-tracing/trace_pairwise_mcv.sql
pg_ctl -D /tmp/ess-pg-trace-data -m fast stop
pg_ctl -D /tmp/ess-pg-trace-data status
```

The final status check reported `pg_ctl: no server running`. No protected or
pre-existing database was used.

## Raw evidence digests

```text
f680835acf09e3d7bd7b8fe496043cf8cf5377b6727198f916c0d88a8fae0839  psql.stdout.log
98794bbd82571ebbebce37f1e7b1bd01deabd782144891d9b96f276afc2344bb  psql.stderr.log
62c24ceb375110225d4724191d1661d1813d897c022c68a5b7867c5cb657233d  server.log
```
