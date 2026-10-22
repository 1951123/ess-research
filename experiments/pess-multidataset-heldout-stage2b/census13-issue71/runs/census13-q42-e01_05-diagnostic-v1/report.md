# Census13 q42 × e01_05 diagnostic — 2026-10-22

**Outcome: zero pre-clamp estimate reproduced; adapter correctly rejected it.**
This was one isolated diagnostic run, not a calibration observation. No truth,
test data, model fitting, or resource selection was used.

## Identity and execution

- Query: `arecel:census13:valid:000042` (`source_index=42`), official
  labels-free valid workload. SQL SHA-256:
  `14d8fbb8f75d03ff9f56cd53de9bbf87f4f7b2708c3fadfbfec12cef87dc7369`.
  The SQL includes `workclass = 'Never-worked'` and
  `occupation = 'Handlers-cleaners'`, matching frozen candidate `e01_05`.
- Census13 source archive SHA-256:
  `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`;
  imported table CSV SHA-256:
  `f751fc7ecd5bd5e62acd9868a0bbe36413528b6eb2de9c2fc8fcf71d9ef2c13a`.
- Fixed PG source commit: `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`;
  independent build/install succeeded as PostgreSQL 16.14. Phase times:
  configure 8.003 s, make 79.246 s, install 1.701 s. Installed `postgres`
  SHA-256 `e8e8f19c70183ac68fe23ea31f8481f03a287d0d5ae2f5e70cf12f928178cd7d`;
  `psql` SHA-256
  `9a1ec63d0f574d28cbee265ae239bf69c951c54655a71e0eb2ed44ffa3be6ae9`.
  Pinned `src/backend/commands/explain.c` SHA-256:
  `59dda114a28a122e1b950bd596604fe4db628edc4775388600961260bf705d55`.
- PR #58 helpers: commit `76106024611ae91505f1f05bdc35aed44d9c38c4`;
  JSON adapter: pinned PR #65 commit `27677a17b7455d89e92d5028d9585418550a8ff8`.
- Replayed the v2 frozen ANALYZE sample byte-for-byte: 8,144,782 bytes,
  SHA-256 `0ff61bcce532a8af07f9319365c28d6fb07e373fc4b8049bae7c72c349baba26`.
  Header identifies PG 16.14, `6:public8:census13`, relation OID 16384,
  13 attributes and 48,842 sampled tuples. The imported table relation OID
  matched 16384.
- Catalog check: `ess_issue71_census13_e01_05`, statistic OID 16389,
  `stxkeys=2 6` (workclass, occupation), target 300, MCV payload present with
  85 items.
- Execution code was the uncommitted diagnostic script at base commit
  `93404ce33fe74d692f28810601ee92065f22fdca`; the script itself is included
  alongside this report (script SHA-256
  `5fd299c71a586f154a0b156aa76071ad0978c0d852eb2605c7ac1c58b7477200`). One
  PostgreSQL cluster; exactly one EXPLAIN.

## Captured result

The raw JSON numeric token was `0` at
`$[0]["ESS Diagnostics"]["Events"][4]["nrows_preclamp"]`. Diagnostics status
was `complete` with five events. MCV selection was actually observed for
statistic OID 16389; it claimed clause indexes `[5, 8]`. The MCV numeric fields
were `simple_sel=8.6856614463364803e-06`, `mcv_sel=0`, `mcv_basesel=0`,
`mcv_totalsel=1.0000000000000002`, and `stat_sel=0`. Base selectivity was 0
with `rel_tuples=48842`; post-clamp rows were 1. Neither replaces the zero
pre-clamp value. The 1,689-character psql JSON response SHA-256 is
`be330351b4f9d761ebf5afc023c2b7f7302a9df80781993ac869407e43be1a05`.

The compact machine-readable event evidence is in
`diagnostic-evidence.json` (SHA-256
`92d88afd42ee9eb2fce556806dc3fc157405967f82727f46393c6580ea2a4c0f`). It
retains the raw numeric token, JSON path, complete event sequence, OIDs, and
MCV fields; the full EXPLAIN document and SQL text are not committed.

The original adapter then rejected the result under its unchanged finite,
positive requirement. This confirms a genuine zero-support case for this
query/config/sample, not a JSON parsing or missing-MCV-diagnostics failure.
Because the frozen corrected-log model takes a logarithm of positive
pre-clamp ratios, this observation is outside its domain. Do not apply an
epsilon, floor, or `Plan Rows` fallback; any zero-support policy requires a
separate researcher decision before full valid acquisition or fitting.

Total run time was 96.260 s; watchdog-measured peak run allocation was
312,659,968 bytes. No resource stop threshold fired. The cluster shut down
normally. Full-run partial observations were not used.
