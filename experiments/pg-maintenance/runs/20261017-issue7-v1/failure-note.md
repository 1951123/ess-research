# Failure note

The v1 attempt initialized the disposable cluster successfully but `initdb`
created only the current system-user role.  The wrapper then attempted to
connect as `postgres`, so database creation failed before any fixture or
`ANALYZE` command ran.  The private server was stopped manually with its own
`pg_ctl` and verified to have no running postmaster.  This attempt produced
zero timed observations and is not part of the scientific matrix.
