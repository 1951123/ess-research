# Gate A v11 initial attempt

Evidence label: **Experimentally observed — fail-closed implementation
checkpoint, not an authoritative Gate A result.**

The first v11 replay was run from the Issue #56 task worktree before commit
`8a75fc5`. The archive-first inputs, pinned PostgreSQL source and binary
provenance checks passed, but both runtime probes stopped with:

```text
ESS_MCV_TRACE contains a claim without selected_stat_oid or claimed_clause_index
```

The cause was an overly broad offline parser that classified PostgreSQL's
marker-free `ESS_MCV_TRACE` termination/selection records (including
`candidate=none`) as claimed-clause records. No result was marked verified and
no historical v8/v9/v10 evidence was overwritten. The corrected parser and
fixtures are committed in `8a75fc5`; the exclusive corrected rerun is
`gate-a-20261020-v11-r2/`.
