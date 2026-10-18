# AreCEL source asset inventory

This inventory is a source-contract audit for Issue #15. It does not claim
that any raw archive or workload is present in the current three-project
environment. The entries below are pinned expectations copied from the
historical adapter audit at commit
[`3452f7e74561255b93b7d9687cb71c76f557df88`](https://github.com/1951123/extstats-advisor-research/tree/3452f7e74561255b93b7d9687cb71c76f557df88).

## Common upstream and acquisition status

- Producer: [AreCELearnedYet](https://github.com/sfu-db/AreCELearnedYet) at
  commit `aa52da7768023270bad884232972e0b77ec6534a`.
- Source archive: the upstream README's Dropbox URL
  `https://www.dropbox.com/s/5bmvc1si5hysapf/data.tar.gz?dl=0`.
- Historical archive SHA256:
  `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`.
- The pinned upstream repository declares the MIT license for its code. The
  archive's separate data-redistribution terms have not been independently
  verified here; downloading or redistributing the data is therefore opt-in
  and remains a review gate.
- No archive, CSV, workload pickle, label pickle, or canonical workload was
  supplied through this task. No historical local repository or global data
  directory was inspected.

## Dataset contracts

| Dataset | Historical source identity | Historical workload/label/canonical hashes | Expected source shape | Current status |
|---|---|---|---|---|
| Forest10 | `original.csv`; `public.forest10`; 581,012 rows; 10 ordered `DOUBLE PRECISION` columns; nullable | CSV `3484f3037f890f6bae46ae51fb387ee883351119667139c5894654276789a73c`; workload pickle `501a3dcfe82ec5742fce4c3dc3b298eabcf78b82dab3a8ff8ad2914a61f4eaea`; label pickle `34d830e6a30b48228ae41e6ae5643fb199e9794b3f36c915fb742af58fdfb974`; canonical JSONL.gz `a922d87660b2dec431a77c2e4a054c4f5528b0f25040859d76d0148a9ed73e74` | 10,000 valid + 10,000 test records | Vertical slice implemented; full input **BLOCKED / NOT RUN** |
| Census13 | `original.csv`; `public.census13`; 48,842 rows | CSV `f751fc7ecd5bd5e62acd9868a0bbe36413528b6eb2de9c2fc8fcf71d9ef2c13a`; workload `492faa529ecc6b212733602fd140a42182439a89d22bcf9c8e8b82db1a5154ba`; labels `5fd6d187830681b16b3c561f7d0a2a014a7fdbabfa1579db655de8131b0ba451`; canonical `9bcfc868effee9a796fff08454eeb85f135049e862ee0eb2dd801831d7df9388` | 13 columns: mixed `DOUBLE PRECISION` and `VARCHAR(64)`; historical adapter marks them not-null | Inventory only; no adapter |
| DMV11 | `original.csv`; `public.dmv11`; 11,591,877 rows | CSV `ae310972b7ac08629d135a1da7c580e3fe603bfc2e665e1969005bd481d4605a`; workload `e37136725ace8f60a6dfcf55529da328ab202d74988538726cff8589ccec65dc`; labels `14b29cc7f28aab5dd85f3bec2e49fe841d4194b7417dcc881459a1d9d9f98d65`; canonical `71bb6e3c61da5ab1096cc52d41e7f696d486e4a3ba1c4586c01119df26fe9f40` | 11 columns: ten `VARCHAR(64)` and one `DOUBLE PRECISION`; historical adapter marks nullable | Inventory only; no adapter |
| Power7 | `original.csv`; `public.power7`; 2,075,259 rows | CSV `a58a43b0e9f26e92744c2130053dd343fb6b3bb9f73b05fd39f6a44d355ddba9`; workload `1f270912f529e362545b6da519492a5aff63bdc65ecc10f71674e5779a7247a5`; labels `d7369b34d2ddc866dbb16c3b2f5147cb10a86832dba54c905ef400bc3514cdf5`; canonical `9f1b11d72bcefe9d76cd83b1f995a6d6f4e0922434975550e2d5783425152327` | 7 ordered `DOUBLE PRECISION` columns; historical adapter marks nullable | Inventory only; no adapter |

The three non-Forest datasets are intentionally not migrated in this bounded
PR. Their historical hashes are requirements for later independently scoped
adapters, not evidence that the corresponding files are locally available.

## Evidence boundary

The current PR does not read `extstats-advisor-research`, `extstats-advisor`,
`postgresql-pgextadv`, `/home/wqts/benchmark-data`, old run directories, a
database, or credentials. A missing or mismatched input is a hard blocker for
ETL rather than a reason to substitute stale artifacts.
