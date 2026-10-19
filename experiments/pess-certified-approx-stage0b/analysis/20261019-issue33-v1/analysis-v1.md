# Stage 0B v1 follow-up accounting analysis

This file is derived from the preserved `runs/20261019-issue33-v1/` evidence; it does not rewrite that evidence.

## Matched tiny ablation

| setup | original incumbent mean/median | certified gap mean/median | tau | rounded-core seconds (sum/median) | recorded partial seconds, tiny n=12 (sum/median) |
|---|---|---|---:|---:|---:|
| `unrounded` | 215/288 / 0 | 0 / 0 | 12/12 | 0.023484 / 0.000183 | 0.024868 / 0.000220 |
| `coarse_uniform_delta_1` | 241/288 / 5/12 | 83/288 / 0 | 8/12 | 0.022813 / 0.000177 | 0.024177 / 0.000217 |
| `matching_aware_eta_1_2` | 233/288 / 1/3 | 11/144 / 0 | 11/12 | 0.023276 / 0.000186 | 0.024549 / 0.000225 |
| `matching_aware_eta_1_4` | 215/288 / 0 | 1/192 / 0 | 12/12 | 0.022843 / 0.000165 | 0.024200 / 0.000207 |

All tiny setups used the same feasible state count per instance: `True`. This is a negative result for state-space reduction; the recorded solver-core times are single-run diagnostics and are not end-to-end method times.

## Same-rounded perturbation-bound ablation

For every frozen v1 row, the matching-aware `eta = sum_i w_i max_ordinary_matching(sum_e |error_e|)` is compared with `eta_naive = sum_i w_i sum_{eligible e} |error_e|` using the identical recorded rounded coefficients. The exact row-level values are retained in `analysis-v1.json`.

| setup | matching-aware strictly tighter | equal / zero gain | rows | total tightening | mean tightening | max tightening |
|---|---:|---:|---:|---:|---:|---:|
| `unrounded` | 0 | 15 | 15 | 0 | 0 | 0 |
| `coarse_uniform_delta_1` | 6 | 9 | 15 | 73/24 | 73/360 | 3/4 |
| `matching_aware_eta_1_2` | 2 | 13 | 15 | 11/40 | 11/600 | 1/4 |
| `matching_aware_eta_1_4` | 0 | 15 | 15 | 0 | 0 | 0 |

Positive gains are listed exactly below; all other rows are explicit zero-gain cases in the JSON report:
- `unrounded`: no strict tightening; all rows are zero-gain.
- `coarse_uniform_delta_1`: `random_33102` (small): 5/6 -> 17/12 (gain 7/12), `random_33103` (small): 1 -> 3/2 (gain 1/2), `star_zero_near_optimum` (small): 1/2 -> 3/4 (gain 1/4), `stress_12_2` (stress): 19/12 -> 7/3 (gain 3/4), `stress_14_4` (stress): 11/4 -> 25/8 (gain 3/8), `stress_16_4` (stress): 5/4 -> 11/6 (gain 7/12).
- `matching_aware_eta_1_2`: `star_zero_near_optimum` (small): 1/2 -> 3/4 (gain 1/4), `stress_14_4` (stress): 3/20 -> 7/40 (gain 1/40).
- `matching_aware_eta_1_4`: no strict tightening; all rows are zero-gain.

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
