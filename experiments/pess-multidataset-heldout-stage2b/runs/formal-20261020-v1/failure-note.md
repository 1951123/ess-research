# Preserved formal run attempt v1

Evidence label: **Experimentally observed runner failure; no held-out outcome.**

The first post-freeze formal runner attempt used commit `fbf9240` and a fresh
archive-first runtime run at
`/home/wqts/ess-runtime/ess-research/issue48/runs/arecel-z0mhgqx9`. It failed
closed after validation calibration, when the implementation incorrectly
compared the full 10,000-record test truth ID set with the frozen 60-record
Forest10 cohort. The exact error was:

```text
RuntimeError: test truth/workload IDs mismatch
```

No held-out measurement row was written. The ETL failure diagnostic remains at
the runtime path above. The bug was fixed in commit `451d74d` to check that the
frozen cohort is a subset of the full test truth split. The rerun used the
exclusive `formal-20261020-v2` evidence directory; v1 was not overwritten.
