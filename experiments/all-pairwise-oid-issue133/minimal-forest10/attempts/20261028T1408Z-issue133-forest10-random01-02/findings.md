# Issue #133 minimal Forest10 all-MCV OID-order experiment

**Status:** `COMPLETE`.
**Outcome:** `ORDER_SENSITIVE_ESTIMATES_AND_QERROR_OBSERVED`.

This is one fixed-set comparison of the 45 frozen Forest10 ordinary two-column MCV objects. The only planned intervention was the already-frozen global CREATE/OID order. It does not estimate the result over all 45! orders and does not establish a blocker mechanism by itself.

## Frozen order identities

| Arm | Order | SHA-256 | Catalog OID order verified |
|---|---|---|---|
| forest10-all-random-01 | random-01 | `3bdaea2042c5415d2a6f45fa7521c54e1c7dd089e566c1ebf7c5a15fd7a56db5` | PASS |
| forest10-all-random-02 | random-02 | `1ad1fd03dd77b5268783de0e86799c14f5fad8082688c1070dec57b7ad373364` | PASS |

## Physical-state checks

- status: `PASS`
- table_logical_identity_equal: `True`
- ordinary_stats_fingerprint_equal: `True`
- fixed_sample_and_header_equal: `True`
- all_45_candidate_payload_states_and_fingerprints_equal: `True`
- comparison_key: `stable candidate_id; numeric OIDs are arm-local only`

## Query completeness and metrics

| Arm | Valid queries | Diagnostics complete/empty | P50 | P95 | P99 | Mean |
|---|---:|---:|---:|---:|---:|---:|
| forest10-all-random-01 | 10000 | 10000 | 1.1804512559972935 | 15.0 | 65.01000000000022 | 6.687501968656185 |
| forest10-all-random-02 | 10000 | 10000 | 1.1794969657076213 | 15.0 | 63.01000000000022 | 6.708283813517734 |

Paired differences over the same Test query IDs:

- paired_valid_query_count: `10000`
- plan_rows_changed_count: `3329`
- qerror_changed_count: `3329`
- mcv_selection_sequence_changed_count: `6475`
- mcv_estimate_sequence_changed_count: `6475`

## Paired query examples

The two arms contain 45 created MCV definitions each and 45 target-300 settings each, with one fixed-sample ANALYZE per arm. In both arms, 23 candidate IDs had populated MCV payloads and 22 had a NULL payload; none were present-empty. Each candidate ID had the same payload state, item count, and fingerprint across arms. A NULL payload is a successfully cataloged MCV definition without a stored MCV list, not a failed CREATE.

The same Test query IDs were paired. Plan Rows and Q-error each changed on 3,329/10,000 queries. MCV selection and estimate sequences changed on 6,475/10,000; among those, 3,146 had unchanged Q-error. Two examples from the beginning of the fixed Test order:

| Query ID | random-01: selected candidate IDs; Plan Rows; Q-error | random-02: selected candidate IDs; Plan Rows; Q-error |
|---|---|---|
| `arecel:forest10:test:000001` | `e02_06 → e04_07 → e01_03`; 1; 4.0 | `e03_08 → e02_04 → e01_07`; 1; 4.0 |
| `arecel:forest10:test:000003` | `e02_03 → e04_07 → e01_08`; 738; 1.82384824 | `e03_08 → e02_04 → e01_07`; 815; 1.65153374 |

The first example shows a changed MCV sequence with unchanged estimate and Q-error; the second shows both sequence and estimate/Q-error differences. These diagnostics are descriptive and do not identify a specific blocker or establish that one object is less useful. Full per-query event traces are in the external raw archive.

P95 is 15.0 in both arms despite these paired changes. Thus this comparison shows order-sensitive cardinality estimates and per-query Q-errors, while the primary P95 summary is unchanged for these two frozen orders.

## Reproducibility and resource record

- Run ID: `20261028T1408Z-issue133-forest10-random01-02`
- Frozen source commit before Test: `55a5188fa4d08904d26114330c215596a0266b0e`
- Protocol SHA-256: `5168554019cf40438ccdde4826c6fb9147aade96518ad2f8d5bbd41a9ba78a70`
- Input identity: `{"catalog_columns": ["elevation", "aspect", "slope", "horizontal_distance_to_hydrology", "vertical_distance_to_hydrology", "horizontal_distance_to_roadways", "hillshade_9am", "hillshade_noon", "hillshade_3pm", "horizontal_distance_to_fire_points"], "container_deserialization_materializes_all_split_objects": true, "csv_rows": 581012, "csv_sha256": "3484f3037f890f6bae46ae51fb387ee883351119667139c5894654276789a73c", "dataset": "forest10", "explicitly_dereferenced_label_split": "test", "labels_pickle_sha256": "34d830e6a30b48228ae41e6ae5643fb199e9794b3f36c915fb742af58fdfb974", "non_test_label_values_indexed_serialized_or_used": false, "query_count": 10000, "query_ids_are_ordered_and_unique": true, "query_ids_sha256": "2d78f84909b5722f8b02ba6bc871ac337fc9d5c7a45ca667ea27ab48cbf6f3a5", "rendered_test_sql_sha256": "307f741da68ea570026ebf1b9f4494141b7030e29a8d2618357747e1a8adb24c", "sample_identity": {"bytes": 10620460, "header": {"alignof": 8, "blcksz": 8192, "file_bytes": 10620460, "format_version": 1, "item_pointer_size": 6, "natts": 10, "relation_filenode": 16384, "relation_identity": "6:public8:forest10", "relation_oid": 16384, "relation_pages": 7792, "sample_target": 90000, "server_version": "16.14", "server_version_num": 160014, "tuple_count": 90000, "tuple_header_size": 24, "tuple_size": 24}, "sha256": "95670277a138f577a7e21eb1567e0f6e1bce1ac489c10907c4a5662577d1aff8", "source_issue99_run_id": "20261025T050116Z-issue99-forest10-fee458", "source_manifest_sha256": "876a692bd3e067f48d70c870e612a900c5e876257ece6ac4e114af51cb45271f"}, "schema_columns": ["Elevation", "Aspect", "Slope", "Horizontal_Distance_To_Hydrology", "Vertical_Distance_To_Hydrology", "Horizontal_Distance_To_Roadways", "Hillshade_9am", "Hillshade_Noon", "Hillshade_3pm", "Horizontal_Distance_To_Fire_Points"], "source_csv_sha256": "3484f3037f890f6bae46ae51fb387ee883351119667139c5894654276789a73c", "split": "test", "test_truth_canonical_sha256": "7c3cdb46422bb6238c35704dc4a7c52fd0528a5900a7cb607d414046a56d2bf7", "truth_count": 10000, "workload_pickle_sha256": "501a3dcfe82ec5742fce4c3dc3b298eabcf78b82dab3a8ff8ad2914a61f4eaea"}`
- Resource usage: `{"cpu_note": "runner process CPU/RSS only; PostgreSQL server/backend CPU is not separately attributed", "early_or_hard_stop_reason": null, "elapsed_wall_seconds": 11.662, "final_run_directory_allocated_bytes": 434458624, "minimum_global_filesystem_free_bytes": 53958127616, "peak_run_directory_allocated_bytes": 432975872, "runner_peak_rss_kib": 490340, "runner_process_cpu_seconds": 6.01}`
- External raw query archive: `{"bytes": 2768796, "path_under_runtime_root": "/home/wqts/ess-runtime/ess-research/issue133/runs/20261028T1408Z-issue133-forest10-random01-02/raw-observations.jsonl.gz", "sha256": "d088a9b8cb33d62a507dc9cef0fb8e7cc73c12f8116e91ce528a9123d98b7318"}`

## Interpretation and limits

The two fixed OID orders produced different Plan Rows and Test Q-errors with the recorded physical-state checks passing. This supports order sensitivity for this PostgreSQL build, dataset, workload, and these two interventions only.

MCV sequence changes are association evidence. No claim that a less useful object blocked a more useful object is made without candidate eligibility/ranking/blocker traces.
The complete query-level observations are retained outside Git under the configured ESS_RUNTIME_PARENT; the report stores only compact summaries and a small number of diagnostic cases.
