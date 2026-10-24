# Issue #87 valid-only attempt — stopped incomplete

**Status: INCOMPLETE; no completed selection result.** The authorized runner started the frozen sequence from research commit `e8f98c6ed5cdfd4d63aa6ef21270badc98f4cbd8`, protocol SHA-256 `ef095a12dd1a1ac676acd822e24d93e369b61cbd56297ced87b6771111f07623`, and Advisor commit `5d61f75fede37d34027b437c646000a3d78d00c6`.

The only attempted case was Forest10 Nominal B=0. The 10,000-task request and Advisor response were saved. The Advisor response reports `heuristic_completed`, one completed fixed-set evaluation, and an internal wall time of about 0.081 seconds. The runner correctly marked the case `INCOMPLETE`: after the scope exited, systemd reported `MemoryMax=infinity`, `RuntimeMaxUSec=infinity`, and `MemoryPeak=[not set]`, despite the invocation requesting 12 GiB and 900 seconds. `/usr/bin/time` recorded 1.56 seconds and 155,504,640 bytes peak RSS, but these measurements do not replace enforcement. The case record has `selected_ids=null`, `objective_fraction=null`, and an empty completed prefix; its response is not an accepted greedy choice.

The run summary says `STOPPED_INCOMPLETE`, `attempted_cases=1`, with the failure `effective_memory_limit_missing_or_mismatched;effective_wall_limit_missing_or_mismatched`. The remaining 19 cases were not started: Forest10 PESS B=0 and both objectives at B=2,3,4,5; Census13 Nominal then PESS at B=0,2,3,4,5. No cross-objective evaluation ran. No PostgreSQL, held-out test, calibration, model change, retry, or limit change occurred.

**Evidence directory:** `/home/wqts/ess-runtime/ess-research/issue87/runs/issue87-valid-only-20261024-v1/`. The saved request SHA-256 is `2c01182d66fec6460cde4e51d9f134c8582887e3a78457835833bbe8f1b7a886`; the saved response SHA-256 is `d30a51cfbad62ecf152fab09139db6a675a15542a18e24679aa8d32179fee531`.

Key evidence file hashes:

- `run-metadata.json`: `8f6d9bd962c5a1897eede47e9d2bb4c8fb4a3fa8df8913c2518cabce4d0139bd`
- `run-summary.json`: `632b7b9c9e723547a929dc213e519ad92b9a95e1620ee3155ca7b1a0ce1208c0`
- `case-results.jsonl`: `17b780d71a41859425132420d81990d4742dbd1dbc3ac2c2871c57f9e5051487`
- `contrasts.jsonl`: `6d0d81746a3515e151256343e35bdb2698de3005a9954133e86a2eeab93a67d9`
- First case `failure.json`: `4196f5aa50ae6d011988db535b9c1883ea5e0c6fb77a0fb66ef252d1ceeba093`
- First case `execution.json`: `723c7a27bc116d1568642b75ef5feb1495acdae7f5b2f9482ce5ea1d1c22e7f9`
- First case `systemd-status.json`: `9222c6c20df10983fbb0c2817c1bdc60b73c74866e57930c8231574afbb2284c`
- First case `resource-usage.txt`: `3345314d1d179d3f42ce0f8cecf0ee2ebf7667c296a25bdf7fdbe39cb7c86394`

Evidence limitations discovered after the stop: `case-results.jsonl` and `contrasts.jsonl` contain pretty-printed multi-line JSON objects, not one JSON object per line; `run-metadata.json` still says `STARTED` while the final `run-summary.json` says `STOPPED_INCOMPLETE`. Raw files remain unchanged. The earlier post-merge `/bin/true` and `/bin/false` probes captured scope limits and the nonzero client return code, but the actual runner scope did not retain the requested effective limit properties.

These are **not experimental selection findings**. Further execution requires a new researcher decision after review of the runner's scope-property and evidence-record behavior; this one-shot authorized sequence was not resumed.
