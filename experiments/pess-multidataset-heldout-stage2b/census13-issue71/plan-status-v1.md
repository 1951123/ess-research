# Census13 Stage 2B plan status (2026-10-22)

The outcome-free plan is frozen in `census13-stage2b-plan-v1.json`. It uses the pinned AreCEL archive and Census13 valid workload structure only; the workload preparation attests `labels_loaded=false`, and the plan records `test_truth_loaded=false`.

Frozen scope: 10,000 valid queries; 78 schema-ordered supported pairs (`e00_01`–`e11_12`); 278,849 statically eligible singleton calls plus 10,000 Empty calls; budgets 0/2/3; schema order, reverse order, and Python `random.Random(seed).shuffle` orders for seeds 0–7. All ten materialized permutations are distinct. Exact feasible subset counts are 1, 3,082, and 79,158.

The first-20 smoke cohort is fixed by valid `source_index` 0–19, with 481 eligible singleton calls and 20 Empty calls per mode (501 per mode; 1,002 total across serial and two-worker modes). The configuration assignment and semantic comparison helpers have synthetic tests; they require exact Decimal pre-clamp equality and equal normalized diagnostic/MCV evidence while retaining and independently validating each cluster's OIDs.

## Current evidence boundary — updated 2026-10-22

The predeclared 20-query smoke completed in `runs/census13-smoke-v1/report.md`: serial and true two-worker runs each completed 501 calls using one identical fixed sample. All 501 pairs matched exact Decimal pre-clamp values and normalized MCV event identity, clauses, and five numeric fields. Observed interval throughput was 36.44 versus 70.07 calls/s (1.923x); this is a small-cohort engineering result, not a full-calibration throughput guarantee. Two earlier failures and one sequential-coordinator run are documented but excluded from the successful result.

No truth, test estimate, or test outcome was loaded or used. The 288,849-call full valid acquisition, valid model fit, order-sensitive selections, and all official test evaluation remain unperformed. This smoke does not authorize or imply official test evaluation.
