# Stage 0B v1 follow-up accounting analysis

This file is derived from the preserved `runs/20261019-issue33-v1/` evidence; it does not rewrite that evidence.

## Matched tiny ablation

| setup | original incumbent mean/median | certified gap mean/median | tau | rounded-core seconds (sum/median) | recorded partial seconds (sum/median) |
|---|---|---|---:|---:|---:|
| `unrounded` | 215/288 / 0 | 0 / 0 | 12/12 | 0.023484 / 0.000183 | 0.038737 / 0.000250 |
| `coarse_uniform_delta_1` | 241/288 / 5/12 | 83/288 / 0 | 8/12 | 0.022813 / 0.000177 | 0.037323 / 0.000230 |
| `matching_aware_eta_1_2` | 233/288 / 1/3 | 11/144 / 0 | 11/12 | 0.023276 / 0.000186 | 0.038508 / 0.000279 |
| `matching_aware_eta_1_4` | 215/288 / 0 | 1/192 / 0 | 12/12 | 0.022843 / 0.000165 | 0.037878 / 0.000272 |

All tiny setups used the same feasible state count per instance: `True`. This is a negative result for state-space reduction; the recorded solver-core times are single-run diagnostics and are not end-to-end method times.

## Stress tier

| setup | original feasible score mean/median | global gap |
|---|---|---|
| `unrounded` | 7/9 / 1/2 | `NO_GLOBAL_GAP` |
| `coarse_uniform_delta_1` | 11/9 / 1 | `NO_GLOBAL_GAP` |
| `matching_aware_eta_1_2` | 7/9 / 1/2 | `NO_GLOBAL_GAP` |
| `matching_aware_eta_1_4` | 7/9 / 1/2 | `NO_GLOBAL_GAP` |

## Accounting limits

- End-to-end comparison: **NOT MEASURED** in v1. Delta/nu setup, quantization, original incumbent evaluation, complete matching-oracle counts, and peak memory were not all inside the recorded timer.
- The JSON records source-derived matching-oracle call counts for the deterministic certificate path; stress greedy neighbor objective calls remain **NOT RECORDED** because v1 only stored accepted-extension states.
- v1 wall caps are therefore interpreted as **selection-engine-only** caps; the declared memory cap was **NOT ENFORCED**. No full-pipeline resource claim is made.
- Stress greedy rows retain original feasible scores but report **NO GLOBAL GAP**. Reference B remains **NOT EXECUTED**.
- Decision remains **INCONCLUSIVE** and there is no speedup claim.
