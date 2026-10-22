# Census13 Stage 2B plan status (2026-10-22)

The outcome-free plan is frozen in `census13-stage2b-plan-v1.json`. It uses the pinned AreCEL archive and Census13 valid workload structure only; the workload preparation attests `labels_loaded=false`, and the plan records `test_truth_loaded=false`.

Frozen scope: 10,000 valid queries; 78 schema-ordered supported pairs (`e00_01`–`e11_12`); 278,849 statically eligible singleton calls plus 10,000 Empty calls; budgets 0/2/3; schema order, reverse order, and Python `random.Random(seed).shuffle` orders for seeds 0–7. All ten materialized permutations are distinct. Exact feasible subset counts are 1, 3,082, and 79,158.

The first-20 smoke cohort is fixed by valid `source_index` 0–19, with 481 eligible singleton calls and 20 Empty calls per mode (501 per mode; 1,002 total across serial and two-worker modes). The configuration assignment and semantic comparison helpers have synthetic tests; they require exact Decimal pre-clamp equality and equal normalized diagnostic/MCV evidence while retaining and independently validating each cluster's OIDs.

## Current evidence boundary

No PostgreSQL build, cluster, ANALYZE, or EXPLAIN has yet been run for Census13. Therefore the smoke equivalence, throughput benefit, sample replay, full valid collection, valid model fit, and order-sensitive selections remain unverified. No truth, test estimate, or test outcome was loaded or used. This report does not authorize or imply official test evaluation.

The next necessary step is to connect the frozen assignment to the pinned JSON-only PostgreSQL runner and execute the predeclared smoke on one serial and two-worker configuration using the same run-local sample. If parity fails, use serial acquisition only and report the discrepancy; do not change the cohort or candidates.
