# Issue #23 Forest10 real-stage evidence

Snapshot: 2026-10-19, Asia/Shanghai. Evidence labels below distinguish source-derived facts, PostgreSQL measurements, and model-internal exact results. Raw data and PostgreSQL outputs are outside Git under `ESS_DATA_ROOT=/home/wqts/ess-data`.

## Source and data gate

The source is `sfu-db/AreCELearnedYet` at commit `aa52da7768023270bad884232972e0b77ec6534a`. Its code is MIT-licensed; the pinned upstream materials do not state a separate data-redistribution license, so the archive is retained for local validation only and is not committed or redistributed. The README Dropbox source was reachable and downloaded successfully.

| Artifact | Actual path | SHA-256 / observed value |
|---|---|---|
| Source archive | `/home/wqts/ess-data/arecel/incoming/arecel-data.tar.gz` | `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79` |
| Forest10 CSV | `/home/wqts/ess-data/arecel/raw/data/forest10/original.csv` | `3484f3037f890f6bae46ae51fb387ee883351119667139c5894654276789a73c` |
| Workload pickle | `/home/wqts/ess-data/arecel/raw/data/forest10/workload/base.pkl` | `501a3dcfe82ec5742fce4c3dc3b298eabcf78b82dab3a8ff8ad2914a61f4eaea` |
| Truth pickle | `/home/wqts/ess-data/arecel/raw/data/forest10/workload/base-original-label.pkl` | `34d830e6a30b48228ae41e6ae5643fb199e9794b3f36c915fb742af58fdfb974` |
| Derived canonical | `/home/wqts/ess-data/arecel/audit-v1/forest10.canonical.jsonl.gz` | `a38646ea371189a3fc637fa4851a2a8272ea5f0551d09e801a3b4cc433e15ea3` |
| Audit JSON | `/home/wqts/ess-data/arecel/audit-v1/audit.json` | `8f17118b7e64089974b3a438b87667990f98393231c13c3366d110eac61610a9` |

The historical canonical reference remains `a922d87660b2dec431a77c2e4a054c4f5528b0f25040859d76d0148a9ed73e74`; the derived canonical is not claimed byte-identical to it. The two pickle files were converted only by the Issue #17 allowlisted converter inside the restricted network-disabled/resource-limited service. No ordinary ETL or credentialed development environment deserialized them.

Strict `inspect` passed with `--data-root /home/wqts/ess-data` and with `ESS_DATA_ROOT` alone. The CSV has 581,012 rows, 10 columns, and zero nulls in the observed file. Derived canonical counts are valid/test `10,000/10,000`; the source-shape screen is 20,000/20,000 supported single-table conjunctive records and 18,011 eligible for the restricted pairwise syntax check. Valid/test ETL outputs are separate workload/truth artifacts; their manifest hashes are:

- valid: `62c14c7de8db1d1c7fa8a0b9a138951c7b28c1fac72a2bf30d1b0fde9d8adb20`, workload `803469c0de351211abd330fbfdb650f3805880605c8f38956a81f7e106085515`, truth `768fe20a91b8e140a08cbe421cbccc7c8ffe16144b4c02418982c81143383c4b`;
- test: `66a3744ad816b74d5c6282f0c8b5fdec22d2311d39541c44ba804dc927ce789f`, workload `4c059f5321491e34eb9b64a6e6636163071adda8bbef5036ca93f02e7d3b0180`, truth `a962f13c7163e698048428df42aea5c1ea80824409cf979accea726fe83e14ef`.

## Frozen real protocol

The frozen input manifest is [real-input-manifest.json](real-input-manifest.json), SHA-256 `bae9202b1807c05932f17e62acaec4e09121fa5a58c994862323562f44e0c71b`. It was created before objective evaluation. It fixes six adjacent two-column MCV candidates (`e01,e12,e23,e34,e45,e56`), target 300, one-unit additive proxy costs, valid-only selection, held-out test, four budgets `[0,2,3,5]`, the nominal order, all `6! = 720` shared orders, and six source query IDs/truths:

| Candidate/task | Query ID | Split | Source truth |
|---|---|---|---:|
| e01 | `arecel:forest10:valid:000005` | valid | 3 |
| e12 | `arecel:forest10:valid:000003` | valid | 0 |
| e23 | `arecel:forest10:valid:000009` | valid | 119625 |
| e34 | `arecel:forest10:valid:000001` | valid | 343 |
| e45 | `arecel:forest10:valid:000010` | valid | 12916 |
| e56 | `arecel:forest10:valid:000011` | valid | 8 |

The test split was not used for selection or calibration.

## PostgreSQL measurement layer

This is **experimentally observed PostgreSQL behavior**, not an optimization result. The isolated server was built from ess-postgresql commit `23c7c2fdd4bfb561f3257d947fee956a2999fdb6` (PostgreSQL 16.14) with the opt-in numeric trace enabled in a temporary source copy; the original repository was not modified. The real table was `public.forest10_original`, a single heap table loaded from the verified CSV.

The exported fixed sample is `/home/wqts/ess-data/pg-calibration/issue23/forest10.sample`, 10,620,470 bytes, SHA-256 `1fd69245a27283a431ff73704aa25096fc39dcea7f6be33be4d5d4eb1e5a4993`. It was replayed before each `ANALYZE` for two repetitions of baseline plus each of the six candidate statistics. The raw calibration artifact is `/home/wqts/ess-data/pg-calibration/issue23/calibration.json`, 84 task/candidate/repetition records, SHA-256 `636d363792d36f27d5b2ff6ea5f9311437ea4f8d04dd9646d7a6be12a8cffd3e`. It contains statistic OIDs, catalog rows, every observed MCV item, `ESS_MCV_TRACE` selection/claimed-clause logs, and the numeric pre-clamp trace. Plan Rows were not used as pre-clamp values.

Observed examples: `e01`, `e45`, and `e56` produced no two-column MCV items under this fixed sample (`stxdmcv` null); `e12`, `e23`, and `e34` produced 300, 300, and 300 MCV items respectively. The trace, rather than `EXPLAIN` alone, showed actual selection. Replaying the same sample reproduced MCV contents and numeric values after ignoring recreated statistic OIDs and query markers. These are fixed-table/fixed-sample observations and do not establish universal PostgreSQL behavior or physical maintenance additivity.

## Exact model layer

The measured-input model instance is `/home/wqts/ess-data/experiment-data/forest10-real-pg-instance.json`, SHA-256 `5e56416429586f7dd56deaf70e05576bbfa461f8cd300d8ba0f1ec733ff3bf11`. It uses the existing `run_experiment.py` and `verify_reference.py` exhaustive framework. Measured positive pre-clamp ratios were converted to natural logs with 80-digit `Decimal` arithmetic, quantized to 18 decimal places, and then represented as exact `Fraction` strings. Therefore the optimization is exact for that recorded rationalized instance; the original binary floating-point PostgreSQL values and transcendental logs remain measurement provenance, not exact rational inputs.

The frozen zero-truth task `arecel:forest10:valid:000003` is retained in the PG artifact but excluded from this primary log-loss model because `T_i > 0` is required before taking `log(n_i^0/T_i)`. No replacement truth or synthetic value was introduced. The retained model has five positive-truth tasks. The model result artifacts are under `/home/wqts/ess-data/experiment-data/forest10-real-decision-results/`: summary SHA-256 `d8b2533dc735d4032f44b304bd95373c4ea2fecd99351b6a2749d0c2ef576294`, raw common-order observations SHA-256 `4303e0b581a9b29c853c3476c3de2b145e11789f5e2a6068d1b755cceaba248d`. The independent verifier returned `verified_objective_certificates=12`.

At budget 3, the real-input rationalized model selected `['e01','e34']` for PESS and Joint-Robust, while Nominal selected `['e12','e23','e34']`; at budgets 0, 2, and 5 the three methods' selected sets were respectively `[]`, `['e01','e34']`, and `['e01','e34']` for PESS/Joint-Robust, with the Nominal budget-5 set `['e12','e23','e34']`. These are model-level choices, not claims about which statistics a fixed PostgreSQL run will select under an arbitrary shared order.

## Reproduction and remaining limits

The code changes add consistent `ESS_DATA_ROOT` fallback with explicit `--data-root` precedence to the Forest10 and reusable real ETL CLIs, and add external-instance support to the existing exact runner. Focused tests passed `43 passed`; the full suite passed `89 passed in 50.69s`. No large data or PostgreSQL output was added to Git. The next research decision is whether the positive-truth restriction and measured-input rationalization are acceptable for paper-level use; they must not be silently generalized.
