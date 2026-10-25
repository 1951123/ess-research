# Issue #99 resource envelope revision v3

## Authorized change

On 2026-10-25 the researcher raised the per-dataset disk-use ceiling from 3 GiB to 10 GiB. Protocol v3 uses a 9.5-GiB early stop and a 10-GiB hard cap; the existing 7.5-hour early stop and 8-hour hard wall limit remain unchanged. The runtime filesystem had 54,045,458,432 bytes available when the revision was requested. The initial 9-GiB early stop repeatedly interrupted DMV11 cluster setup before any observations were collected, while observed allocated-storage peaks stayed below the authorized 10-GiB hard cap. Therefore the early stop was raised to 9.5 GiB, retaining 0.5 GiB of headroom before the hard cap.

Protocol v2 remains frozen for its earlier attempts and completed collections. V3 changes only resource limits and run provenance. Its source pins, scientific scope, PostgreSQL measurement, model transforms, train-only data boundary, greedy semantics, budgets, and per-case selection limits are checked against v2 by the runner. The report records each dataset's collection protocol hash and effective resource limits so compatible v2/v3 results remain distinguishable.

## DMV11 v2 disk attempts

These attempts ran under the v2 3-GiB early stop. Each was interrupted during cluster setup and produced zero structured observations; no partial data is reused.

| Run ID | Workers | Peak allocated bytes | Outcome |
|---|---:|---:|---|
| `20261025T074723Z-issue99-dmv11-942393` | 12 | 3,421,331,456 | 3-GiB early stop during cluster setup |
| `20261025T074931Z-issue99-dmv11-d3b8bc` | 11 | 3,341,623,296 | 3-GiB early stop during cluster setup |
| `20261025T075143Z-issue99-dmv11-857ada` | 10 | 863,039,488 | Researcher stopped the old-cap attempt before collection to authorize v3 |

The v2 Forest10 and Census13 collections completed below their previous limits, with peaks of 2,840,223,744 and 2,880,544,768 bytes respectively. They remain usable under their pinned v2 hashes; rerunning them would not add evidence about the cap-triggered failure.

## Initial v3 9-GiB early-stop attempts

These fresh DMV11 attempts ran under the initial v3 9-GiB early stop. Each stopped during cluster setup with zero completed observations and remains preserved as incomplete evidence; none is reused. All measured peaks were below the 10-GiB hard cap.

| Run ID | Workers | Peak allocated bytes | Outcome |
|---|---:|---:|---|
| `20261025T075718Z-issue99-dmv11-f5b5b9` | 12 | 10,048,593,920 | 9-GiB early stop during setup |
| `20261025T080011Z-issue99-dmv11-75e01f` | 11 | 9,861,369,856 | 9-GiB early stop during setup |
| `20261025T080251Z-issue99-dmv11-623a79` | 10 | 9,705,107,456 | 9-GiB early stop during setup |
| `20261025T080532Z-issue99-dmv11-c17f20` | 9 | 9,929,543,680 | 9-GiB early stop during setup |
| `20261025T080814Z-issue99-dmv11-32102a` | 8 | 9,892,302,848 | 9-GiB early stop during setup |
| `20261025T081054Z-issue99-dmv11-f683d4` | 7 | 9,978,306,560 | 9-GiB early stop during setup |

## Revised v3 9.5-GiB attempt

The first attempt under the 9.5-GiB early stop used the maximum 12 workers. It stopped during cluster setup before any observations completed. The observed peak was 10,497,945,600 bytes (about 9.78 GiB), 239,472,640 bytes below the 10-GiB hard cap. Attempts at 11 and 10 workers stopped in the same phase at essentially the same peak. The researcher then asked to pause collection and estimate the 12-worker disk requirement before another attempt.

| Run ID | Workers | Peak allocated bytes | Completed observations | Outcome |
|---|---:|---:|---:|---|
| `20261025T081616Z-issue99-dmv11-15b3e4` | 12 | 10,497,945,600 | 0 / 2,094,044 | 9.5-GiB early stop during cluster setup |
| `20261025T081929Z-issue99-dmv11-ce8f09` | 11 | 10,497,945,600 | 0 / 2,094,044 | 9.5-GiB early stop during cluster setup |
| `20261025T082244Z-issue99-dmv11-f46e72` | 10 | 10,497,953,792 | 0 / 2,094,044 | 9.5-GiB early stop during cluster setup |

## Preliminary 12-worker storage estimate

**Conjecture / Open:** the 12-worker attempt reached a 10,497,945,600-byte (9.777-GiB) peak before any EXPLAIN observations completed. At the last live directory snapshot, `worker0` through `worker4` directories were present. Subtracting the approximately 1.08-GB shared pre-cluster footprint leaves roughly 1.87 GB per visible worker directory. A straight extrapolation to 12 worker clusters gives about 23.7 GB decimal (22.1 GiB) for setup; the historical compressed-observation sizing adds about 77 MB for DMV11, before uncertain logs and other growth. A practical planning range is **22–24 GiB**. This is a low-confidence extrapolation, not a measured full-run requirement: worker4 may have been incomplete, and no attempt completed cluster setup. The authorized 10-GiB cap is therefore likely insufficient for 12 workers. No further collection was started for this estimate.

## Implementation and next step

The collector now passes the v3 disk and wall thresholds into the shared aggregate guard and writes the effective values into each collection manifest. The shared guard keeps its existing 3/4-GiB defaults for other callers. The v3 report accepts the pinned v2 and v3 hashes, verifies their scientific and selection contracts match, and reports limits per dataset.

The next collection step is intentionally unset while the researcher reviews the preliminary 12-worker disk estimate. All incomplete attempts remain separate; no further DMV11 or Power7 collection is active.
