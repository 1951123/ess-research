# Issue #67: AreCEL valid-split pairwise-MCV candidate discovery

**Scientific question and minimum implementation.** Which distinct Forest10 source-column pairs co-occur with supported restriction predicates in the official AreCEL valid queries, and how often? Reuse the archive-first AreCEL prepared workload, its source schema order, and the existing simple-restriction operator contract; enumerate all unordered pairs of distinct supported columns once per query and retain only the compact findings report and recomputation code.

## Static eligibility rule

**Source-derived (conditional):** predicate operators follow `ess_research.arecel.real.SUPPORTED_OPERATORS` (`=`, `<`, `<=`, `>`, `>=`, and `[]`); the prepared inclusive range must contain exactly two bounds and corresponds to lower/upper comparisons in the existing query adaptation. This reuses the simple comparison forms in the Issue #47 eligibility crosswalk. A column is eligible in a query when it has at least one supported restriction and no unsupported/malformed predicate. If the same column has both supported and unsupported predicates, exclude it for that query. Repeated supported predicates on a column do not duplicate a pair. For every query, all unordered pairs among eligible distinct columns are counted once, even when the query has three or more such columns. Unsupported/malformed predicates and excluded co-occurring pairs are reported by query, predicate index, and reason.

This is a syntactic/static screen. It does not show that PostgreSQL considered, built, selected, or benefited from a statistic, and it does not establish universal MCV compatibility for arbitrary SQL or catalogs.

Issue #47's controlled PostgreSQL evidence gate was equality-only. The broader source-structured restriction screen here does not upgrade that evidence or assert that every non-equality form is usable in PostgreSQL.

## Forest10 valid split

**Experimentally observed:** 10,000 official valid queries; 45 of 45 schema-ordered pairs have positive support. Support counts range from 3,571 to 3,723. No unsupported predicates or co-occurring pairs were excluded in this valid split.

| Column A | Column B | Eligible valid queries |
|---|---|---:|
| Elevation | Aspect | 3,639 |
| Elevation | Slope | 3,637 |
| Elevation | Horizontal_Distance_To_Hydrology | 3,648 |
| Elevation | Vertical_Distance_To_Hydrology | 3,689 |
| Elevation | Horizontal_Distance_To_Roadways | 3,709 |
| Elevation | Hillshade_9am | 3,672 |
| Elevation | Hillshade_Noon | 3,665 |
| Elevation | Hillshade_3pm | 3,681 |
| Elevation | Horizontal_Distance_To_Fire_Points | 3,643 |
| Aspect | Slope | 3,615 |
| Aspect | Horizontal_Distance_To_Hydrology | 3,600 |
| Aspect | Vertical_Distance_To_Hydrology | 3,606 |
| Aspect | Horizontal_Distance_To_Roadways | 3,695 |
| Aspect | Hillshade_9am | 3,623 |
| Aspect | Hillshade_Noon | 3,627 |
| Aspect | Hillshade_3pm | 3,638 |
| Aspect | Horizontal_Distance_To_Fire_Points | 3,577 |
| Slope | Horizontal_Distance_To_Hydrology | 3,636 |
| Slope | Vertical_Distance_To_Hydrology | 3,668 |
| Slope | Horizontal_Distance_To_Roadways | 3,695 |
| Slope | Hillshade_9am | 3,636 |
| Slope | Hillshade_Noon | 3,662 |
| Slope | Hillshade_3pm | 3,639 |
| Slope | Horizontal_Distance_To_Fire_Points | 3,593 |
| Horizontal_Distance_To_Hydrology | Vertical_Distance_To_Hydrology | 3,618 |
| Horizontal_Distance_To_Hydrology | Horizontal_Distance_To_Roadways | 3,667 |
| Horizontal_Distance_To_Hydrology | Hillshade_9am | 3,633 |
| Horizontal_Distance_To_Hydrology | Hillshade_Noon | 3,623 |
| Horizontal_Distance_To_Hydrology | Hillshade_3pm | 3,633 |
| Horizontal_Distance_To_Hydrology | Horizontal_Distance_To_Fire_Points | 3,571 |
| Vertical_Distance_To_Hydrology | Horizontal_Distance_To_Roadways | 3,723 |
| Vertical_Distance_To_Hydrology | Hillshade_9am | 3,682 |
| Vertical_Distance_To_Hydrology | Hillshade_Noon | 3,610 |
| Vertical_Distance_To_Hydrology | Hillshade_3pm | 3,695 |
| Vertical_Distance_To_Hydrology | Horizontal_Distance_To_Fire_Points | 3,576 |
| Horizontal_Distance_To_Roadways | Hillshade_9am | 3,674 |
| Horizontal_Distance_To_Roadways | Hillshade_Noon | 3,672 |
| Horizontal_Distance_To_Roadways | Hillshade_3pm | 3,696 |
| Horizontal_Distance_To_Roadways | Horizontal_Distance_To_Fire_Points | 3,634 |
| Hillshade_9am | Hillshade_Noon | 3,662 |
| Hillshade_9am | Hillshade_3pm | 3,645 |
| Hillshade_9am | Horizontal_Distance_To_Fire_Points | 3,607 |
| Hillshade_Noon | Hillshade_3pm | 3,660 |
| Hillshade_Noon | Horizontal_Distance_To_Fire_Points | 3,649 |
| Hillshade_3pm | Horizontal_Distance_To_Fire_Points | 3,665 |

The other pinned AreCEL valid splits also ran through the same generic code: Census13 78 candidates (3,506–3,632 supporting queries); DMV11 55 candidates (3,501–3,687 supporting queries); Power7 21 candidates (3,734–3,917 supporting queries). Each contains 10,000 valid queries and had no unsupported predicates or excluded co-occurring pairs.

## Reproduction and provenance

From the repository root, with `ESS_DATA_ROOT` and `ESS_RUNTIME_PARENT` configured as documented:

```sh
source ~/.bashrc
PYTHONPATH=src .venv/bin/python -m ess_research.arecel.candidates --dataset forest10
```

The run used Python `3.12.3` on `Linux-7.0.0-38-generic-x86_64-with-glibc2.39`, NumPy `2.3.4`, AreCEL upstream commit `aa52da7768023270bad884232972e0b77ec6534a`, verified archive SHA-256 `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`, and clean workload-only ETL source commit `1edfba0b093a462192ef33a3d5a7bda5e18d822f`. No seed is used; the discovery is deterministic. The command emits the complete candidate list and provenance as JSON, including `labels_loaded: false`. Its workload-only path deserializes the pinned workload pickle but never the label pickle, adapts and materializes only `valid/workload.json`, and does not create or open truth files. Candidate discovery uses only that valid split output and performs no PostgreSQL measurements.

## Limitation

These counts are workload co-occurrences under the stated static rule, not calibration or selection recommendations. They do not authorize changes to Issue #64's candidate sets or calibration budget.
