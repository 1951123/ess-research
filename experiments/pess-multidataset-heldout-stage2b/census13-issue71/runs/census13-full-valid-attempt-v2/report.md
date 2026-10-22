# Census13 full-valid acquisition attempt v2 — BLOCKED

**Result: BLOCKED; no valid-only model fitting or resource selection was run.**
The second attempt stopped on the first structured observation rejected by the
existing JSON adapter. The partial observations below are failure diagnostics,
not a complete calibration and must not be used for fitting or selection.

## Frozen inputs and execution

- Frozen plan SHA-256:
  `51842c6981936d9a5be39342eb5caee23b35f3137e5876064b0b1a649906d5e1`.
- Run ID: `20261022-080045-census13-full-valid`.
- Execution HEAD at start: `2e496743ecdaeeef65927d3680ae2f4797e3b9f1`.
- PostgreSQL source commit:
  `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`; run-local build/install
  succeeded as PostgreSQL 16.14 (configure 8.149 s, make 77.453 s, install
  1.635 s).
- PR #58 helpers at `76106024611ae91505f1f05bdc35aed44d9c38c4` and PR #65
  structured adapter at `27677a17b7455d89e92d5028d9585418550a8ff8`; pinned
  helper-file hashes passed.
- Outcome-free schedule reconstruction reproduced 10,000 valid queries, 78
  candidates, and exactly 288,849 planned calls (10,000 Empty + 278,849
  singleton). One fresh 8,144,782-byte sample was exported and replayed under
  the same SHA-256 `0ff61bcce532a8af07f9319365c28d6fb07e373fc4b8049bae7c72c349baba26`.

## Failure

At `arecel:census13:valid:000042` × `e01_05` on worker 1, the JSON adapter
raised `ValueError: base estimate nrows_preclamp must be finite and positive`.
It reported 1,689 characters of psql JSON output but did not expose the parsed
numeric value, so this record does not distinguish zero from a non-finite
value. The run stopped immediately; no `Plan Rows` fallback or query/config
replacement was used.

- Successful JSON observations retained locally: 25,683 on worker 0 and
  24,981 on worker 1; one explicit ERROR row; total successful calls 50,664 of
  288,849. No missing/duplicate/full-coverage claim is made.
- Run elapsed: 190.090 s. Peak allocated run-directory bytes:
  412,999,680. The 7.5-hour/3-GiB early stop and 8-hour/4-GiB hard limits did
  not trigger.
- Both run-owned clusters were checked using their run-local `pg_ctl` and
  reported `no server running`.
- No truth was loaded; official test truth, estimates, queries, and outcomes
  were not accessed. Partial measurements were not used for model fitting.

The runtime files are preserved locally at
`$ESS_RUNTIME_PARENT/ess-research/issue71/runs/20261022-080045-census13-full-valid/`.
The partial JSONL shards are intentionally not published as calibration
evidence. The original setup-order failure remains separately recorded in
`census13-full-valid-attempt-v1/report.md`.

## Disposition

The authorized retry has failed on a real non-positive/non-finite adapter
input. Per instruction, the attempt is recorded and stopped: no additional
PostgreSQL run, no partial-data fitting, and no exact resource selection.
Further work requires resolving the scientific treatment of this valid-query
observation and a new researcher decision; this report does not alter the
frozen protocol or silently relax positivity.
