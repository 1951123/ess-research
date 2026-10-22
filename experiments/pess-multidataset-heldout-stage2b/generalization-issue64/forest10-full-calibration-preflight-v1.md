# Forest10 full-calibration preflight v1 — code only

2026-10-22 (Asia/Shanghai). Responds to PR #65 review `5608528228` at source/evidence commit `e5194dca623bd48bb75b750920bc09817015396a`.

**Verdict: the bounded JSON smoke is accepted evidence, but the current entry points are not a ready full-calibration observation runner.** This preflight adds synthetic failure-path tests, not PostgreSQL execution or execution authorization. Existing scientific configs, candidates (45), budgets (0/2/3), objectives, exact enumeration, sample semantics and historical evidence are unchanged.

Question: what is the smallest safe extension needed to collect all valid-only observations without losing failure evidence or silently changing the positive-log domain? Reuse the existing JSON adapter, isolated setup/watchdog and compact row format; audit them and test failures before proposing any long-run implementation. No new framework, workload, label loading, model fitting or selection is needed for this preflight.

## 1. Exact work and source-derived execution gaps

The published Issue #67/PR #68 counts, already pinned by `forest10-first-implementation-v1.json`, give **10,000 Empty + 164,088 eligible singleton = 174,088 EXPLAIN calls**, across **46 configurations**. One initial sample-export ANALYZE plus 46 replay ANALYZE operations would be required. These counts are structural, not estimates of execution success. This preflight does not reopen the archive or any truth/test input.

| Existing path | Source-derived behavior | Long-run consequence |
|---|---|---|
| `run_forest10_trace_probe.py::_worker` | Exactly 20 queries, committed 212-call plan, exclusive `open("x")`, per-row `flush()`, error row followed by stop; normal finalization writes summary and closes cluster | Suitable for its bounded smoke only. Do not change query count or pass it off as a full runner. |
| Same worker cleanup | Deletes its own sample/CSV/schema/server log; no append/resume mode | Partial rows are evidence, not a resumable checkpoint. Recreating a cluster/table and combining new-sample rows would break same-sample comparability. |
| `forest10_runner.py::calibrate_and_select` | Keeps estimates/observations in memory, then directly builds models and calls exact selection; returns only on success | Not a collection-only command. Failure can prevent any returned observation artifact; do not use this function for a newly authorized observations-only phase. Its MCV observation projection also omits five-term numeric fields retained by the smoke. |
| Existing watcher | 30 min / 2 GiB hard limits, 28 min / 1.5 GiB early stops; watches all worker stages; attempts process-group termination and own-cluster cleanup | These limits have not been changed. Past single-run success is not a full-workload fit guarantee. |
| JSON adapter / pinned `psql` helper | One structured EXPLAIN per call; strict complete/positive/OID association; helper command timeout defaults to 180 s; configuration helper permits 600 s | A slow or malformed call stops the run; per-call timeout is not a guarantee that 174,088 calls fit the run budget. |

`flush()` is not `fsync()` or an atomic crash checkpoint. Python-handled failure retains complete earlier lines, but power loss, SIGKILL, partial writes, ENOSPC and host loss have **not** been certified. The final summary is not written atomically. The watcher can stop a process without a complete worker summary; a surviving JSONL prefix must not be mistaken for a completed cohort. Existing `configuration_count` increments on attempted configuration, including failed attempts, so it is not a successful-configuration count in a failed run.

### Minimal proposed collection boundary (not implemented or authorized here)

Prefer **bounded streaming in one fresh run**, not a general checkpoint/resume system:

1. Reuse the frozen full-valid schedule and existing JSON adapter; separate observation acquisition from `calibrate_and_select`. A collector must not open truth, fit coefficients or invoke selection.
2. Write compact rows immediately, with a small fixed flush/fsync batch boundary inside each configuration; record configuration errors separately from query errors and record the last fully persisted sequence. A single file/prefix with an explicit incomplete status is sufficient; no ledger database or dependency manager is needed.
3. Keep all 46 configurations in that one run's cluster against the same freshly exported sample and unchanged table identity. Retain sample/header/digest until acquisition and evidence verification finish. Configured OID mappings and numeric MCV records must remain associated with their configuration.
4. On any invalid observation, cap, monitor or I/O failure, stop and save the valid prefix plus error/unattempted suffix information, close the cluster, and mark full collection incomplete. **No automatic resume or replay**, no silent duplicate replacement, no cross-run sample concatenation. Any restart needs a new researcher decision; partial data alone must not feed selection.
5. Before execution, review this small collection-only adaptation, its synthetic I/O/failure tests, exact counts and retention/budget choice. No full-run readiness is claimed by merely proposing it.

This is an engineering gap needed to preserve expensive observations and the collection/selection boundary, not a new scientific eligibility gate. General crash recovery is optional; bounded stop-with-evidence is the simpler sufficient alternative requested by review.

## 2. Workload-wide zero / invalid-estimate policy

The active config already requires finite **strictly positive** `nrows_preclamp` and `Status=complete` on the correct relation. Apply that same rule to every scheduled Empty/singleton call; no query-dependent exception or test-based tuning:

- Finite values in `(0,1)` are valid; do not round or clamp to one.
- Zero, negative, NaN, infinities, missing pre-clamp fields, malformed/incomplete JSON or wrong association reject the observation and stop. Retain the query/configuration identity and error class; the current failed-row estimate is null, not an invented replacement. The current generic error row does not distinguish all numeric-invalid subclasses; do not report unrecorded zero/NaN counts.
- `NO_MCV_EVENTS` is not an invalid estimate. A positive complete singleton observation remains usable as an observation even if the planner did not select that statistic. Do not discard, retry or substitute it.
- Unattempted rows after a stop remain unattempted, not successful or excluded. Full-cohort calibration/model fitting/selection is blocked by any missing or rejected required input. Do not silently optimize on a surviving subset.
- If real full-valid observations expose zero pre-clamp estimates, the positive-log model is outside its domain there. Report the failure and request a researcher decision; do not invent an epsilon, floor or revised cohort. The target convention `max(1, valid_truth)` and held-out Q1 floor do **not** authorize flooring PG model inputs. No truth is read in this preflight.

The accepted smoke cannot establish that all 10,000 valid queries have positive estimates. Its MCV proportions (102/192 eligible singleton calls; 102/212 overall) are descriptive of a nonrepresentative fixed slice, **not** rates to assume for the full workload.

## 3. Time: all-in sensitivity, not a completion guarantee

Observed Phase C totals: 111.796 s supervised wall; 0.750827 s for 212 EXPLAIN client/parse calls; 8.162678 s for all 46 configurations/replays; 93.264639 s private source/build/install. Thus wall time not attributed to EXPLAIN calls was 111.045173 s (including setup, configuration, serialization, watcher and other overhead). The full run still has 46 configurations, not 46 times the query-count expansion.

For a transparent **planning scenario only**, use `T = 120 s + 174088 * t`, where 120 s approximates the observed non-EXPLAIN work with a small margin and `t` is assumed mean per-call client/parse/output cost. This is neither a confidence interval nor a proven upper bound: build variance, long-tail queries, disk synchronization, log/WAL growth, watcher cost and serialization can increase both terms.

| Assumed mean call time | All-in scenario | Interpretation |
|---|---:|---|
| 3.542 ms | 736.620 s / 12.28 min | Optimistic smoke-mean arithmetic only; **not a reliable forecast** |
| 10 ms | 1,860.880 s / 31.01 min | Already exceeds current hard cap |
| 50 ms | 8,824.400 s / 2.45 h | Sensitivity case, not measured |
| 100 ms | 17,528.800 s / 4.87 h | Sensitivity case, not measured |
| 250 ms | 43,642.000 s / 12.12 h | Sensitivity case, not measured |
| 500 ms | 87,164.000 s / 24.21 h | Sensitivity case, not measured |
| 1 s | 174,208.000 s / 48.39 h | Sensitivity case, not measured |

With that 120-second overhead assumption, the existing 28-minute early stop leaves only **8.961 ms/call** on average. Neither the biased 20-query sample nor the helper timeout certifies this. There is **no evidence-backed narrow full-run duration interval** yet. Budget planning must consider hours and failure, not promise the optimistic 12-minute arithmetic. Any larger envelope needs explicit approval and code/config review; this document does not activate it. Model fitting, exact selection and test evaluation are separate stages and excluded from every timing here; the old synthetic selector projection is not added as a verified full-run cost.

## 4. Storage and retained evidence

The existing 212-row artifact has 86,713 bytes, mean **409.024 bytes/row**, range **269–578 bytes/row**. This preflight reads line lengths, not truth or new PG outcomes.

| Row-size assumption | Raw JSONL bytes for 174,088 calls |
|---|---:|
| Observed mean (descriptive extrapolation) | 71,206,098 |
| Observed maximum for every row (not a proven upper bound) | 100,622,864 |
| 2 KiB / row planning allowance | 356,532,224 |
| 4 KiB / row stress allowance | 713,064,448 |

The smoke's total measured run peak was 448,634,880 bytes. Conservatively adding the raw-record scenarios gives roughly **0.52–1.16 GB** before additional full-run log/WAL/temp-file growth, filesystem allocation overhead, synchronization and export copies. This addition is approximate and slightly double-counts existing smoke output; it is not an occupancy bound. At 4 KiB/row, keeping a second full uncompressed copy would reach about **1.875 GB** even before extra growth, exceeding the existing 1.5 GiB early stop. Avoid duplicate raw artifacts in the run and measure allocation with the existing watcher; do not assume EXPLAIN is disk-free.

A future streaming collector avoids storing 174,088 nested observation dictionaries in RAM. The current integrated function retains them and additional Decimal/model structures; their peak RAM has not been measured and the disk watcher does not limit it. This is another reason not to use that in-memory function as the long-run observation command.

Any single new Git file over 10 MB requires researcher approval. Do **not** automatically commit a 71–101 MB raw JSONL. Before collection choose either approved external storage with durable identity/location, or simple bounded compressed JSONL parts below the repository limit, retaining every observation/error and one small integrity manifest. Compression ratio is unknown; a digest alone cannot replace expensive data. This is a retention choice for review, not a new storage system implemented here. Local runtime remains disposable only after necessary observations are durably retained. Samples/binaries/PGDATA/full logs are not default Git artifacts.

Recompute the row-size and runtime arithmetic without PG or dataset access:

```python
from pathlib import Path
from decimal import Decimal
p = Path("experiments/pess-multidataset-heldout-stage2b/generalization-issue64")
lines = (p / "forest10-json-calibration-smoke-v1.jsonl").read_bytes().splitlines(keepends=True)
n = 174088
sizes = list(map(len, lines))
print(len(lines), sum(sizes), min(sizes), max(sizes))
print(Decimal(sum(sizes)) * n / len(sizes), max(sizes) * n, 2048 * n, 4096 * n)
for t in ("0.003542", "0.01", "0.05", "0.1", "0.25", "0.5", "1"):
    print(t, Decimal(120) + n * Decimal(t))
```

## 5. Actually executed tests and decision boundary

Added four focused synthetic tests to the existing `test_forest10_trace_probe.py`, with the real worker and adapter but fake external I/O:

- Malformed JSON on the first singleton after 20 successful Empty calls: 20 successes + one error row survive, no subsequent call, cluster cleanup invoked.
- Zero, negative, NaN and both infinities after two valid calls: earlier rows survive; the third is an explicit error with null estimate; no clamping or continuation (five subcases).
- Injected Python `KeyboardInterrupt` after three successes: prefix plus error survives and normal cleanup is invoked. This tests handled interruption, **not real SIGKILL/power-loss durability**.
- Singleton configuration failure after Empty: 20 successes retained, no fabricated failed EXPLAIN, whole run FAILED. Attempted configuration count is distinguished from successful calls.

Actual command: `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -B -m unittest discover -s experiments/pess-multidataset-heldout-stage2b/generalization-issue64 -p 'test_*.py'` — **122 tests passed**. AST parsing, existing manifest checks and `git diff --check` also passed. No production runner, parser, mathematical model or frozen config was modified; no new PostgreSQL process, cluster or experiment was run.

**Next decision:** review the small collection-only streaming adaptation and choose retention plus an explicit time/disk envelope before authorizing full valid acquisition. General resume infrastructure and another exploratory workload are not required. The current evidence does not justify promising full-valid completion under the smoke limits. Keep PR #65 Draft and Issue #64 Open; no full calibration, fitting, selection or official test execution is authorized by this preflight.
