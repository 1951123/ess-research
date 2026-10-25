# Issue #99 parallelism revision v2

## Decision

The researcher requested configurable within-dataset parallelism and an attempt at the highest supported worker count. Protocol v1 is preserved as the record for the initial two-worker attempt. Protocol v2 changes only the acquisition schedule and corresponding provenance; dataset, train split, query set, candidate universe, statistics settings, sample semantics, observation contract, transforms, greedy rule, budgets, and resource caps remain fixed.

`collect DATASET --parallelism K` selects `K` run-local PostgreSQL clusters and one serial query loop per cluster. `K` must be between 1 and the lesser of 12 and the process CPU-affinity count; omitting it selects that maximum. The same binary ANALYZE sample is replayed and identity-checked on every cluster. The empty-statistics baseline runs on worker 0. Singleton candidates are assigned deterministically in descending train support to the least-loaded worker, with worker ID as the tie break; each worker processes its candidates in ascending ID order. Dataset runs remain serial.

The 7.5-hour/3-GiB early stop and 8-hour/4-GiB hard cap still apply to the aggregate per-dataset run directory, including every database copy, build, CSV input, and retained observation. The maximum supported worker setting is an attempt, not a promise that each dataset fits the disk cap. A resource-limited attempt remains INCOMPLETE with its raw observations and worker accounting; a lower-parallelism retry gets a separate run ID. No subsampling is permitted.

## Sizing evidence

**Experimentally observed, incomplete v1 attempt:** source commit `dadb0a5ec3ed8a8ff0a6d5f2f32697e4616b1537`, Forest10, two workers. The researcher stopped it to revise parallelism. The durable observation parts were SHA-256 and row-count checked: worker 0 retained 50,249 successful calls and worker 1 retained 48,367, for 98,616 total. Peak allocated run storage before cleanup was 643,457,024 bytes. The run manifest records the stop as researcher-directed, not a resource-cap stop. These observations are preserved under `$ESS_RUNTIME_PARENT/ess-research/issue99/runs/20261025T044454Z-issue99-forest10-7a144b/` and are not reused in v2.

The last progress samples reported 273.215 and 262.582 calls/second for workers 0 and 1. Dividing the full 7,640,403-call plan by the combined 535.797 calls/second gives a 3.961-hour sizing projection before PostgreSQL build/import/sample setup. This linear projection is not a throughput guarantee at higher concurrency.

The pinned source CSV member sizes are Forest10 22,878,434 bytes, Census13 4,662,791 bytes, DMV11 695,149,262 bytes, and Power7 92,498,589 bytes. These are archive member sizes, not database storage estimates. The runtime early-stop limit remains the controlling measurement for actual per-run disk use.

At protocol revision, the process had affinity to 12 CPUs with no cgroup CPU quota; host `MemAvailable` was 14,498,742,272 bytes and the runtime filesystem had 54,283,423,744 bytes free. The maximum of 12 is therefore the current CPU-affinity ceiling, not a statement that all datasets will support 12 duplicated table copies under the per-run disk cap. Each run records its selected worker count and available CPU/memory snapshot.

## Reproducibility boundary

The v1 Forest10 attempt is an interrupted operational record. Its observations do not enter any v2 fit or selection. V2 collection starts from the committed protocol-v2 source SHA and recomputes the complete baseline/singleton observation set under its recorded worker count. Official test labels and test EXPLAIN remain out of scope. Standard deserialization of the split-container label pickle materializes its container; only the train key is explicitly dereferenced, as approved by the researcher, and that boundary is recorded in each run manifest.
