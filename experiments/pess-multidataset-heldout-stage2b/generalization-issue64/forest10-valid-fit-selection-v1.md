# Forest10 valid-only fit and exact resource selection v1

**Disposition: `FROZEN` — valid-only model inputs and exact B=0/2/3 Nominal/PESS selections.** No PostgreSQL operation or official test data/outcome was used in this phase.

## Inputs and reproducibility

- Durable observation run: [`runs/20261022-forest10-full-valid-v1/`](runs/20261022-forest10-full-valid-v1/), collection manifest SHA-256 `a6972008f73f24ca3c1a456c96caf64e109895ef5b9525fa2b35791ca5bca99b`. The read-only verifier passed all 174,088 rows, 86 parts and the outcome-free official valid schedule before fitting.
- Workload/truth source: pinned AreCEL archive SHA-256 `5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79`, upstream commit `aa52da7768023270bad884232972e0b77ec6534a`. Only `data/forest10/workload/base-original-label.pkl`'s `labels['valid']` values were used, aligned by source index to `arecel:forest10:valid:000000`–`009999`. The canonical valid ID/cardinality stream SHA-256 is `fc301ee43eac7dd1f3d381f0d0c8ad6bb4534dca6c1005719d703c18956c7d90`. The combined pickle is deserialized as permitted by the Issue clarification; test labels are never retrieved or used.
- Model source: PR #58 corrected-log commit `76106024611ae91505f1f05bdc35aed44d9c38c4`; pinned `run_formal.py` SHA-256 `61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322`. The Issue #64 coefficient builder uses the same natural-log definition and numeric contract: Decimal precision 80, `1e-18` `ROUND_HALF_EVEN` quantization, then exact `Fraction` arithmetic.
- Analysis script: [`fit_forest10_valid_and_freeze.py`](fit_forest10_valid_and_freeze.py), SHA-256 `0a3b3ebe5d926c18df23b68f38f17f68abc521d97c8ae3b168106263677a4b41`. It calls the outcome-free observation verifier and existing complete selector; it has no test-split loader or PostgreSQL calls.
- Reproduction (after sourcing the configured shell environment):

  ```bash
  .venv/bin/python experiments/pess-multidataset-heldout-stage2b/generalization-issue64/fit_forest10_valid_and_freeze.py \
    --run experiments/pess-multidataset-heldout-stage2b/generalization-issue64/runs/20261022-forest10-full-valid-v1 \
    --result experiments/pess-multidataset-heldout-stage2b/generalization-issue64/forest10-valid-frozen-selection-v1.json \
    --coefficients experiments/pess-multidataset-heldout-stage2b/generalization-issue64/coefficients.jsonl.gz
  ```

## Fit and numerical checks

The model is `alpha_i = ln(n0_i / max(1, valid_truth_i))` and `b_e,i = ln(n_e,i / n0_i)` for every statically eligible edge. All 10,000 Empty values and all 164,088 eligible singleton values were positive, finite and used; no `Plan Rows` substitute, epsilon, or floor was applied to estimates. **71,760** of the 174,088 pre-clamp estimates were below 1 (including 2,428 Empty values), and remained unchanged inputs. The 607 zero valid truths use only the frozen target convention `max(1, truth)`.

There are 10,000 `alpha` and 164,088 `b` coefficients. The exact rational coefficients are retained per valid query in [`coefficients.jsonl.gz`](coefficients.jsonl.gz) (1,184,496 bytes; SHA-256 `421ce57d443e425f3c3c73a6cdbbf5b2f4fa3aa00a5eea172e514f882b54b82d`). The observation statuses were retained without filtering: 87,404 `VERIFIED` MCV-event rows and 86,684 `NO_MCV_EVENTS` rows. No invalid/missing estimate was found by the verifier.

## Frozen exact selections

The frozen candidate order is the complete 45-pair source-schema order. The selector enumerated every feasible set (`1`, `1,036`, and `15,226` sets for B=0, 2, and 3), using `|S| <= B`. Nominal uses greedy matching in that order; PESS uses every inclusion-maximal matching. The objective is the unweighted sum across all 10,000 valid tasks; exact ties are retained, with the existing minimum-cardinality then candidate-order representative.

| Budget | Method | Exact objective (Fraction) | Approximate objective | Optimal-set count | All optimal sets | Frozen selection |
|---:|---|---:|---:|---:|---|---|
| 0 | Nominal | `23326825631265146269149/1000000000000000000` | 23,326.825631265146269149 | 1 | `{}` | `{}` |
| 0 | PESS | `23326825631265146269149/1000000000000000000` | 23,326.825631265146269149 | 1 | `{}` | `{}` |
| 2 | Nominal | `4374828918765339127297/200000000000000000` | 21,874.144593826695636485 | 1 | `{e01_06, e02_07}` | `{e01_06, e02_07}` |
| 2 | PESS | `4374828918765339127297/200000000000000000` | 21,874.144593826695636485 | 1 | `{e01_06, e02_07}` | `{e01_06, e02_07}` |
| 3 | Nominal | `21512755121155336377967/1000000000000000000` | 21,512.755121155336377967 | 1 | `{e01_06, e02_07, e03_04}` | `{e01_06, e02_07, e03_04}` |
| 3 | PESS | `21512755121155336377967/1000000000000000000` | 21,512.755121155336377967 | 1 | `{e01_06, e02_07, e03_04}` | `{e01_06, e02_07, e03_04}` |

The selected sets are identical under Nominal and PESS for all three budgets; each result has one exact minimizer. For each selected set, its candidate edges are mutually vertex-disjoint, so every task's available selected-edge subset has exactly one maximal matching. The recorded selected-set diagnostic therefore found zero tasks with multiple maximal matchings or a PESS-vs-Nominal loss difference. This explains equality **on these winning sets**; it does not imply the two objective functions agree on every feasible set or that PostgreSQL actually chooses these resources.

The versioned machine-readable [`FROZEN selection JSON`](forest10-valid-frozen-selection-v1.json) contains all ties, selected sets, exact objectives, source hashes and limitations. `SHA256SUMS` records the integrity hashes for the report, script, coefficient artifact and result.

## Verification and boundary

**Experimentally observed:** the full Issue #64 offline suite passed 134 tests (including valid-truth isolation, corrected-log and independent small exact-enumeration checks); the full 174,088-row data verifier passed; Python AST/compile checks, `sha256sum -c SHA256SUMS`, and `git diff --check` passed. No new PostgreSQL run occurred.

This is a valid-split **model objective/resource-selection** result, not PostgreSQL accuracy, MCV-use validation, test generalization/Q1, or evidence that PESS dominates Nominal. Official test evaluation requires a separate decision and must consume the frozen result without retuning.
