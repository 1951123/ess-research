# Protocol amendment v3

The v2 control probe established that a target-0 `(e,f)` object has
`stxdmcv IS NULL` and is omitted from PostgreSQL's `StatisticExtInfo` list
before `choose_best_statistics`; this is a valid no-MCV exclusion control but
cannot independently test a missing endpoint predicate.

The v3 input adds a positive-MCV `(a,f)` candidate `e05` and assigns it to the
missing-endpoint control query, which predicates on `a` but intentionally omits
`f`. The no-MCV control remains `e45` with target 0. The two controls are now
independent: one tests source-level omission of an unbuilt MCV kind, and the
other tests source-level nonselection when a positive-MCV candidate lacks one
endpoint clause. Earlier v1 and v2 runs remain preserved as separate evidence.
