# Protocol chronology

The Issue branch chronology is intentionally explicit:

1. `b57bfc2c5f16ecdb42a6ee28d82e4f3855ab6da7` — committed only
   `pilot-manifest-v1.json`, before any comparison output existed.
2. `f804219`, `704afe7`, `c09e33d`, and `d636da6` — added the independent
   reference, quantization/certificate code, deterministic bounded solver,
   frozen input instances, tests, proof, and reproduction documentation.
3. `3aa6bf3` and `6e50876` — added certificate diagnostics and the detailed
   comparison report generator; tests passed before the recorded pilot.
4. The first complete comparison was executed only after step 1 and the
   implementation commits, then rerun as the preserved v1 evidence under
   `runs/20261019-issue33-v1/`.
5. `77aa490` — committed the first SHA256-checked v1 evidence; `89f04f9` —
   added the short `docs/STATUS.md` checkpoint after evidence was committed.
   `8547cfa` isolated Stage 0B module names for full pytest collection, and
   `f65eead` refreshed the v1 evidence with that current code SHA.
6. Draft PR #34 was created after the local/live/PR HEAD checks; it remains
   open and unmerged for researcher review.
7. The post-review `analysis/20261019-issue33-v1/` files are derived from the
   preserved v1 JSONL; they add no new comparisons and do not overwrite v1.

The protocol commit is recorded in `environment.json`, `manifest-copy.json`,
`summary.json`, and `report.md`. No GitHub Contents/Git-data API was used to
create source files, commits, or the task branch; the local Worktree Git
history is authoritative.
