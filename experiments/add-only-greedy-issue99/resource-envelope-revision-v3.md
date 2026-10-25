# Issue #99 resource envelope revision v3

## Authorized change

On 2026-10-25 the researcher raised the per-dataset disk-use ceiling from 3 GiB to 10 GiB. Protocol v3 uses a 9-GiB early stop and a 10-GiB hard cap; the existing 7.5-hour early stop and 8-hour hard wall limit remain unchanged. The runtime filesystem had 54,045,458,432 bytes available when the revision was requested.

Protocol v2 remains frozen for its earlier attempts and completed collections. V3 changes only resource limits and run provenance. Its source pins, scientific scope, PostgreSQL measurement, model transforms, train-only data boundary, greedy semantics, budgets, and per-case selection limits are checked against v2 by the runner. The report records each dataset's collection protocol hash and effective resource limits so compatible v2/v3 results remain distinguishable.

## DMV11 v2 disk attempts

These attempts ran under the v2 3-GiB early stop. Each was interrupted during cluster setup and produced zero structured observations; no partial data is reused.

| Run ID | Workers | Peak allocated bytes | Outcome |
|---|---:|---:|---|
| `20261025T074723Z-issue99-dmv11-942393` | 12 | 3,421,331,456 | 3-GiB early stop during cluster setup |
| `20261025T074931Z-issue99-dmv11-d3b8bc` | 11 | 3,341,623,296 | 3-GiB early stop during cluster setup |
| `20261025T075143Z-issue99-dmv11-857ada` | 10 | 863,039,488 | Researcher stopped the old-cap attempt before collection to authorize v3 |

The v2 Forest10 and Census13 collections completed below their previous limits, with peaks of 2,840,223,744 and 2,880,544,768 bytes respectively. They remain usable under their pinned v2 hashes; rerunning them would not add evidence about the cap-triggered failure.

## Implementation and next step

The collector now passes the v3 disk and wall thresholds into the shared aggregate guard and writes the effective values into each collection manifest. The shared guard keeps its existing 3/4-GiB defaults for other callers. The v3 report accepts the pinned v2 and v3 hashes, verifies their scientific and selection contracts match, and reports limits per dataset.

The next attempt is a fresh DMV11 collection at the CPU-affinity maximum of 12 workers under the v3 cap. If 12 completes, Power7 also starts at 12. Every interrupted attempt stays separate and incomplete.
