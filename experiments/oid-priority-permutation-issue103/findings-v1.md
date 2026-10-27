# Issue #103 — OID-priority permutation uncertainty

**Evidence label: experimentally observed, offline exact train-model calculation.** This is a counterfactual uniform distribution over global priority permutations, not an empirical PostgreSQL OID distribution.

## Method and scope

The analysis used the four frozen Issue #99 training models (100,000 tasks per dataset), the exact frozen Nominal/PESS resource sets at B=0,2,3,4,5, and all distinct resource sets (25 total). It enumerated every global priority permutation for each set, applying the same deterministic greedy inclusion-maximal matching on each task’s statically eligible selected edges. Permutation multiplicity was retained even when orders induced the same task matching.

Coefficients were reconstructed from frozen train truth and Issue #99 raw singleton/baseline observations using the Issue #99 log transform and 1e-18 quantization. Task-specific applicability was recovered from the complete train-only singleton observation IDs in frozen candidate-map order and checked against all support counts. The workload and labels pickles were not opened. Each full coefficient digest matched the frozen train-model digest. For every task and selected set, the optimized integer-scaled calculation was compared with the pinned Advisor exact Fraction reference routines for both fixed-priority Nominal loss and task-wise PESS loss. Every frozen selection objective also matched exactly.

The comparison remains within the Issue #99 pre-clamp/clamped-log train model. Neither the workload pickle nor the labels pickle was opened. No PostgreSQL query, ANALYZE, OID DDL, refitting, reselection, Issue #101 artifact, held-out label, or test outcome was read or run.

## Results

The following values are shown as decimals for readability; exact fractions for means, variances, extrema, Nominal values, PESS bounds, and paired contrasts are in `summary-v1.json`.

### forest10

| B | Nominal-selected M | E[L] ± SD; [min, max] | N(M) | P(M) | PESS-selected M | E[L] ± SD; [min, max] | N(M) | P(M) | ΔE (PESS set − Nominal set) |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|
| 0 | {∅} | 237064.72959389 ± 0.00000000; [237064.72959389, 237064.72959389] | 237064.72959389 | 237064.72959389 | {∅} | 237064.72959389 ± 0.00000000; [237064.72959389, 237064.72959389] | 237064.72959389 | 237064.72959389 | 0.00000000 |
| 2 | {e01_06, e02_07} | 222467.05636773 ± 0.00000000; [222467.05636773, 222467.05636773] | 222467.05636773 | 222467.05636773 | {e01_06, e02_07} | 222467.05636773 ± 0.00000000; [222467.05636773, 222467.05636773] | 222467.05636773 | 222467.05636773 | 0.00000000 |
| 3 | {e01_06, e02_07, e03_04} | 219193.10758476 ± 0.00000000; [219193.10758476, 219193.10758476] | 219193.10758476 | 219193.10758476 | {e01_06, e02_07, e03_04} | 219193.10758476 ± 0.00000000; [219193.10758476, 219193.10758476] | 219193.10758476 | 219193.10758476 | 0.00000000 |
| 4 | {e01_06, e02_07, e02_08, e03_04} | 218310.63524947 ± 471.51100011; [217839.12424936, 218782.14624958] | 217839.12424936 | 220853.37758395 | {e01_06, e02_07, e03_04} | 219193.10758476 ± 0.00000000; [219193.10758476, 219193.10758476] | 219193.10758476 | 219193.10758476 | 882.47233529 |
| 5 | {e01_06, e02_07, e02_08, e03_04, e06_08} | 217857.95321121 ± 530.86507974; [217031.86392223, 218423.69172400] | 217031.86392223 | 223547.39248618 | {e01_06, e02_07, e03_04} | 219193.10758476 ± 0.00000000; [219193.10758476, 219193.10758476] | 219193.10758476 | 219193.10758476 | 1335.15437355 |

### census13

| B | Nominal-selected M | E[L] ± SD; [min, max] | N(M) | P(M) | PESS-selected M | E[L] ± SD; [min, max] | N(M) | P(M) | ΔE (PESS set − Nominal set) |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|
| 0 | {∅} | 79483.70303306 ± 0.00000000; [79483.70303306, 79483.70303306] | 79483.70303306 | 79483.70303306 | {∅} | 79483.70303306 ± 0.00000000; [79483.70303306, 79483.70303306] | 79483.70303306 | 79483.70303306 | 0.00000000 |
| 2 | {e02_03, e04_06} | 56408.58626241 ± 0.00000000; [56408.58626241, 56408.58626241] | 56408.58626241 | 56408.58626241 | {e02_03, e04_06} | 56408.58626241 ± 0.00000000; [56408.58626241, 56408.58626241] | 56408.58626241 | 56408.58626241 | 0.00000000 |
| 3 | {e01_05, e02_03, e04_06} | 52865.90511571 ± 0.00000000; [52865.90511571, 52865.90511571] | 52865.90511571 | 52865.90511571 | {e01_05, e02_03, e04_06} | 52865.90511571 ± 0.00000000; [52865.90511571, 52865.90511571] | 52865.90511571 | 52865.90511571 | 0.00000000 |
| 4 | {e01_05, e02_03, e04_06, e06_08} | 53581.97937417 ± 2172.84581050; [51409.13356366, 55754.82518467] | 51409.13356366 | 56485.62440908 | {e00_11, e01_05, e02_03, e04_06} | 52163.36434188 ± 0.00000000; [52163.36434188, 52163.36434188] | 52163.36434188 | 52163.36434188 | -1418.61503229 |
| 5 | {e01_05, e02_03, e04_06, e04_08, e06_08} | 53675.07377931 ± 2411.42329049; [50347.35647341, 55984.81677010] | 50347.35647341 | 56821.28266685 | {e00_11, e01_05, e02_03, e04_06, e07_12} | 51718.70534127 ± 0.00000000; [51718.70534127, 51718.70534127] | 51718.70534127 | 51718.70534127 | -1956.36843804 |

### dmv11

| B | Nominal-selected M | E[L] ± SD; [min, max] | N(M) | P(M) | PESS-selected M | E[L] ± SD; [min, max] | N(M) | P(M) | ΔE (PESS set − Nominal set) |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|
| 0 | {∅} | 268850.36611971 ± 0.00000000; [268850.36611971, 268850.36611971] | 268850.36611971 | 268850.36611971 | {∅} | 268850.36611971 ± 0.00000000; [268850.36611971, 268850.36611971] | 268850.36611971 | 268850.36611971 | 0.00000000 |
| 2 | {e00_05, e01_04} | 235810.29243051 ± 0.00000000; [235810.29243051, 235810.29243051] | 235810.29243051 | 235810.29243051 | {e00_05, e01_04} | 235810.29243051 ± 0.00000000; [235810.29243051, 235810.29243051] | 235810.29243051 | 235810.29243051 | 0.00000000 |
| 3 | {e00_05, e01_04, e04_07} | 240454.85598670 ± 6871.08890359; [233583.76708310, 247325.94489029] | 233583.76708310 | 248195.44489488 | {e00_05, e01_04, e02_03} | 233837.56774842 ± 0.00000000; [233837.56774842, 233837.56774842] | 233837.56774842 | 233837.56774842 | -6617.28823828 |
| 4 | {e00_05, e01_04, e01_07, e04_07} | 240746.05229042 ± 6600.14011500; [231416.58237585, 245662.81431237] | 231416.58237585 | 247418.82980831 | {e00_05, e01_04, e02_03, e06_07} | 233601.78552262 ± 0.00000000; [233601.78552262, 233601.78552262] | 233601.78552262 | 233601.78552262 | -7144.26676780 |
| 5 | {e00_05, e01_04, e01_07, e02_03, e04_07} | 238737.41961688 ± 6570.26109888; [229450.22050859, 243632.90387346] | 229450.22050859 | 245405.04846339 | {e00_05, e01_04, e02_03, e06_07, e08_10} | 233601.77050022 ± 0.00000000; [233601.77050022, 233601.77050022] | 233601.77050022 | 233601.77050022 | -5135.64911666 |

### power7

| B | Nominal-selected M | E[L] ± SD; [min, max] | N(M) | P(M) | PESS-selected M | E[L] ± SD; [min, max] | N(M) | P(M) | ΔE (PESS set − Nominal set) |
|---:|---|---:|---:|---:|---|---:|---:|---:|---:|
| 0 | {∅} | 105798.26062675 ± 0.00000000; [105798.26062675, 105798.26062675] | 105798.26062675 | 105798.26062675 | {∅} | 105798.26062675 ± 0.00000000; [105798.26062675, 105798.26062675] | 105798.26062675 | 105798.26062675 | 0.00000000 |
| 2 | {e00_01, e03_06} | 94039.87166113 ± 0.00000000; [94039.87166113, 94039.87166113] | 94039.87166113 | 94039.87166113 | {e00_01, e03_06} | 94039.87166113 ± 0.00000000; [94039.87166113, 94039.87166113] | 94039.87166113 | 94039.87166113 | 0.00000000 |
| 3 | {e00_01, e02_04, e03_06} | 93372.37485914 ± 0.00000000; [93372.37485914, 93372.37485914] | 93372.37485914 | 93372.37485914 | {e00_01, e02_04, e03_06} | 93372.37485914 ± 0.00000000; [93372.37485914, 93372.37485914] | 93372.37485914 | 93372.37485914 | 0.00000000 |
| 4 | {e00_01, e00_03, e02_04, e03_06} | 92896.15936097 ± 231.88059482; [92402.79513018, 93089.18000347] | 92908.12813700 | 97554.60404946 | {e00_01, e02_04, e03_06} | 93372.37485914 ± 0.00000000; [93372.37485914, 93372.37485914] | 93372.37485914 | 93372.37485914 | 476.21549817 |
| 5 | {e00_01, e00_03, e01_02, e02_04, e03_06} | 92466.91794040 ± 265.66953692; [91859.52700593, 92759.62140049] | 92489.13355435 | 98144.93177354 | {e00_01, e02_04, e03_06} | 93372.37485914 ± 0.00000000; [93372.37485914, 93372.37485914] | 93372.37485914 | 93372.37485914 | 905.45691874 |

## Interpretation and limits

For every evaluated set, the exact calculation satisfies `Eπ L(M,π) ≤ maxπ L(M,π) ≤ P(M)`. The second inequality is conditional on each priority-induced scheme belonging to the frozen inclusion-maximal matching family, which is how the analysis constructs it. `P(M)` is task-wise adversarial and can exceed the maximum under one shared global permutation. Uniform priority permutations also do not imply uniform probabilities over task matchings.

The Nominal priority is the frozen candidate-ID order used by Issue #99; it is one counterfactual order in this analysis, not a claim about an observed PostgreSQL OID order. Results describe training-model loss only and do not establish actual PostgreSQL choice probabilities, held-out generalization, or a universal Nominal/PESS winner.

## Reproduction and provenance

- Analysis source commit: `7665174249ba9ef6b0b832eac8667938c7dc61a4`; analysis script SHA-256: `dbe1a9b455ef7853dd98687ed58834bd8e74709a18436851728bdc9306514aaf`.
- Frozen selection SHA-256: `2dfa3268e3cbdf145be2521498115dc10e67bd8b03b523fe151363ba77645eca`; Issue #99 protocol-v4 SHA-256: `2f40b265bacc96d965b59bcdccc25c9bb73e3a4d99481a82107db0542343a9e6`.
- Advisor reference source commit: `5d61f75fede37d34027b437c646000a3d78d00c6`; `model.py` SHA-256: `4bf07c229cbeaf003a3ebbe55c4018091288240069298fbd95c4ef6691865781`; `reference.py` SHA-256: `c301d3b7d8314728326ddc7f12ab44805226546e95038f862730487f0ab35ac0`.
- Python: `3.12.3`. Summary JSON contains per-dataset runtime IDs, source hashes, model digest checks, exact fractions, all 40 frozen case mappings, and paired contrasts.
- Actual command, after the repository-mandated shell initialization: `python3 experiments/oid-priority-permutation-issue103/run_issue103.py --advisor-source /home/wqts/projects/ess-advisor`.
- Task applicability is reconstructed from the complete frozen train singleton records, not from test queries. Neither workload nor labels pickle was opened. The analysis reads no Issue #101 runtime path or test-split outcome artifact.
