# Issue #74 Stage 1 integration report

**State:** adapter and bounded smoke complete; full frozen-workload solver
comparison is incomplete because the pinned conventional Nominal backend
requires an infeasible dense allocation on the 10,000-task input. This is an
engineering feasibility observation, not a new scientific result. No Stage 2
budget comparison, PostgreSQL execution, or test evaluation was performed.

## Scope and provenance

- Advisor: `1951123/ess-advisor@e7bb42f5b9ac3f09dd45e341e0e215153ad5f8ec`,
  schema v1, package `pess-ess 0.1.0`. The source commit was fetched and
  verified before installation.
- Research base: `ess-research@a7aa91e10dd199fd8eb6e5cbaaf1f6e05a607207`.
- PostgreSQL source provenance carried with both model requests:
  `f1bf37b5dd3d3a7087fc0af5de550ca31035854c`. No PG server was started.
- Python 3.12.3; NumPy 2.5.4; SciPy 1.18.1; NetworkX 3.7.
- Request provenance carries model version, frozen selection SHA, coefficient
  or observation hashes, valid-truth provenance/hash, AreCEL archive hash,
  model-source commit, research commit, PostgreSQL commit, and Advisor commit.
- Both datasets use task weight 1 and a unit per-candidate maintenance proxy,
  matching their frozen `|M| <= B` cardinality constraint. Nominal uses the
  frozen Forest10 candidate order or Census13's predeclared `schema_order`.
  These are model inputs, not PostgreSQL OID-order claims.

Forest10 consumed the exact rational coefficients from
`forest10-valid-frozen-selection-v1.json` and its coefficient artifact
(`b1f0e6521804cc0e77f0616271d94b10a3602bde6eb677591ee040e14c7dbd04`), with
10,000 valid tasks and 45 candidates. Census13 reconstructed the frozen
`clamped-log-v2` task coefficients using the recorded `max(1,x)` transform,
Decimal precision 80 and `1e-18` half-even quantization. Its computed full
coefficient digest exactly matched
`7671c4d8837c4f63423bb4a0cf1a132923301ef4f6d04cdf5ee380dfe6cbc0a5`; all
10,000 valid tasks, 78 candidates and candidate-specific coverage counts
matched the frozen plan. Worker hashes were checked over decompressed JSONL
bytes, as specified by the frozen record. No model was refit and no frozen
artifact was changed.

## Bounded integration smoke

Command (run in the Issue Worktree):

```bash
.venv/bin/python -m unittest discover -s experiments/solver-integration-issue74 -p 'test_*.py' -v
.venv/bin/python experiments/solver-integration-issue74/run_bounded_smoke.py \
  --repo "$PWD" --output "$RUN_ROOT/bounded-smoke.json" --task-limit 12 --candidate-limit 8
```

Four offline adapter tests passed. The smoke ran Nominal and PESS for both
datasets at budgets 0, 2, and 3, with 12 tasks, at most 8 candidates, and
5-second per-MILP / 2-second inner / 8-second total limits. All 12 runs
reported validated feasible results and solver-reported `optimal`; every
selected set belonged to the independent exhaustive Fraction reference's full
tie set, and every reported Fraction objective matched that reference.
Advisor `optimal` is floating-point solver status, not a mathematical
certificate. For PESS at budgets 2 and 3,
`selected_pess_value_fraction_certified` was false. Their observed witness
aggregates matched the small exact reference values, but are not promoted to
certified full PESS values.

The full smoke responses and all exact tie sets are retained in
`bounded-smoke-results-v1.json` (SHA-256
`ce3612a2209585e95d638ab512912e8de62ffadc73ef120c13063786da611873`). The
file records request and response hashes for every solve:

| Dataset | Objective | B | Selected in exact ties | PESS value Fraction-certified | Request SHA-256 | Response SHA-256 |
|---|---|---:|---|---|---|---|
| Forest10 | Nominal | 0 | yes | n/a | `04f0c68af1ffd67fff024379c6b9ea357a3984af1eb5014ca648b4751aacbbb6` | `778b58f3d284ef5a12cc914e13849a583cef7e491687b66c159e532cc74b6458` |
| Forest10 | PESS | 0 | yes | yes | `904f9c5125e81730e38ba23ffb814f7bc391c65172818a02653ae3b812282e0e` | `aa19d7811d7474db194eb1b7fee2847330350d74b90ededc5f8a4836b9c653d6` |
| Forest10 | Nominal | 2 | yes | n/a | `b9ed00eeac2e98c7dd8a6533237c19c18fa17f41f2e0771c219d96b257b22371` | `774568a69f6b1ced7a3a0fc09ee8c6531d30ac397cf8f92cd29cf74dbb61869d` |
| Forest10 | PESS | 2 | yes | no | `f62f039b4c7fbbb78a465ff54f97db60a5fe2c9083b63962d9e28be424a32b97` | `a8a8eb614434f3ddd5ef51a3d20dce568db675e0a91f7c7d8656bfa03be20dce` |
| Forest10 | Nominal | 3 | yes | n/a | `caba2be1582d40148212f8550d0c4106a2eb90f2f7a2d91eaa25ce49d9f30e7a` | `3e9c15eb786fc94c1ba376e64d8be21e7381431191dd99bda57a3a2a9b2869a5` |
| Forest10 | PESS | 3 | yes | no | `5f3144162e3c11d99b4c8be0243f09ca4008e072d649c99445dd761f27054c0e` | `c2bff9b7d887f1e04ff512a9b89cc787d16f7ef5d52cfe0693cee07663d50a7a` |
| Census13 | Nominal | 0 | yes | n/a | `e6895e8429409b4212b911fc173dce6c20908362184f02de311c15227f9761a5` | `f73e559ea55f7594a59ac1ecf05f1df02419e1c5e112fa325a913107ba514f73` |
| Census13 | PESS | 0 | yes | yes | `46764547f5c9d96d4b382eb6873b955bc74fcb330f324635b2c76839ebf49ae9` | `b76a4e7b1aca276ea97f9d32a8ae11341a88eec29ec376803ab1ff0bb914587e` |
| Census13 | Nominal | 2 | yes | n/a | `3d1c8b427932b289baf78a26397a7ba0effce4559d7fbc8002fd7627abdad9c5` | `18fd67c1b4a8b9dee207269aece5c952be4842327ac70280799a0d0c43af4f63` |
| Census13 | PESS | 2 | yes | no | `d1ada0650b498c47b9cdf75d9c0901b84945313664e7190a32436213109c49c9` | `b62b30a9de68def326fc16b4cd68868eec88ab00afb60f4dacb30fa7136ef842` |
| Census13 | Nominal | 3 | yes | n/a | `90c4bf4444f1d04265ec02f81c643a19e3ce7e0c7d4509d943593ad49b016b96` | `5e09201a9d54c3cffa430b2cd5630a22202e9d60174dc0c63938503bf092ed16` |
| Census13 | PESS | 3 | yes | no | `02f60ab6b383d2ee192e5066b8aecc6d7c9a61d323efb299339ea0c994d6f74c` | `d1ffee9741ec453efae6fba924622f577204cc223f3994702b8130112edc0b2f` |

This is a deliberately truncated integration check. Its choices and objectives
are not claims about full 10,000-task optima.

## Full-workload feasibility boundary

The first full-input Forest10 Nominal B=0 attempt used the frozen sparse model
(10,000 tasks, 45 candidates; canonical request SHA-256
`e804775f93f02094168acf43e0c4f81636b11d727021689dce98be0098cfaa4e`,
7,544,123 request bytes) and the Advisor pin above. It failed before allocation
in `pess_ess/mip.py` when NumPy attempted a dense `1,330,848 x 174,133` float64
matrix, approximately 1.69 TiB. No matrix was allocated and no response was
produced. The error was `numpy._core._exceptions._ArrayMemoryError`.

The other full-workload Nominal/PESS budget runs were not attempted. This Draft
does **not** claim the full frozen B=0/2/3 solver comparisons passed. A
sparse/scalable solver path or an explicitly bounded alternative is needed
before those comparisons. That algorithm work belongs in the separate
solver-capability track (and may be reported to Issue #29); Stage 2 and larger
budgets remain outside this PR.

## Tests and retained artifacts

- `python -m unittest discover -s experiments/solver-integration-issue74 -p 'test_*.py' -v` — 4 passed.
- `pess-ess-solve --help` — CLI entry point available from the pinned install.
- Bounded smoke — 12/12 exact-reference selected-set and objective matches.
- Full Nominal check — stopped on the dense memory allocation error above; not a solver result.
- No PostgreSQL process, official test truth, test EXPLAIN, or test outcome was used.

Committed artifacts are the adapter, smoke runner, four small offline tests,
the versioned manifest, this report, and the compact 84 KB smoke evidence.
The virtual environment and intermediate raw runs remain in the Worktree's
ignored `.venv/` and configured runtime directory.
