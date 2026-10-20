# Protocol v1 analysis clarification

This note preserves the pre-registered `protocol-v1.json`; it does not change
the frozen inputs, methods, endpoint budgets, repetitions, or stopping rules.

During raw-result analysis it was made explicit that the unchanged Static
implementation reports `scenario_count` as the number of **all** matchings it
enumerates for its conditional MILP, not only maximal matchings. The manifest
and raw records separately retain independent task-local maximal-matching
counts. H1 is therefore evaluated with both metrics:

1. `scenario_count` is the operational Static model-expansion counter.
2. `maximal_matching_count` is a structural graph signature, not a row count.
3. Master–Oracle `distinct_cuts`, `inner_oracle_calls`, and task-evaluation
   counters are its operational work counters.

This clarification prevents the report from calling Static's all-matching
row count a maximal-matching count. No rows were removed or reclassified.
