# Stage 2B formal held-out decision-quality report

Evidence label: **Experimentally observed — valid matched PostgreSQL measurements, with a negative/no-contrast decision result.**

## Decision

**NO-GO for the tested nontrivial PESS-versus-Nominal physical contrast under this frozen validation-selection procedure.** Both real datasets passed the measurement validity checks, but validation-only model selection chose `Empty` for Empty, Nominal, and PESS at every budget. Consequently the held-out PostgreSQL measurements are valid repeated Empty controls, not a nontrivial PESS/Nominal treatment contrast.

This is not a claim that PESS is universally worse, that Nominal is universally better, or that Empty is an optimal PostgreSQL resource policy. It is a bounded negative result: the preregistered procedure produced no distinct nonempty policy to compare on these supported cohorts. A broader study would need a separately authorized protocol amendment or follow-up that changes the validation calibration/task construction without consulting these held-out outcomes.

## Frozen protocol and independence

Protocol SHA-256: `54867e0bf3ca116b044d77da14efe1b12d06851af522cfbeb49af14ae33733ad`. The protocol froze strict pairwise eligibility, cohorts, cross-split fingerprint audit, Stage 1A exclusion, validation-only calibration, budgets, methods, metrics, repetitions, sample procedure, and fail-closed rules before this run. The v1 runner failure is preserved in `runs/formal-20261020-v1/failure-note.md`; the earlier v2 evidence is retained but superseded because its Empty tie ledger was corrected before this authoritative `formal-20261020-v3` rerun.

The strict eligibility rule was exactly two predicates on two distinct source columns with an exact predeclared candidate endpoint match. Forest10's source has no equality-only records under this rule, so the protocol retained the declared supported range operators rather than silently discarding Forest10. Normalized SQL-template groups overlap across train/valid/test in both datasets; query IDs are therefore not group-independent population samples.

## Validity and effective-MCV coverage

| Dataset | frozen query IDs | held-out rows | positive traces | trace-selected rows | zero-truth rows | mean | median | P90 | max |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| forest10 | 60 | 120 | 120 | 0 | 0 | 0.28740906138032777223240402040903883333333333333333333333333333333333333333333333 | 0.03610635368922594998822114991 | 0.4457851881571978628972310747 | 5.189928547135720025713354961 |
| census13 | 52 | 104 | 104 | 0 | 0 | 0.235547413397544984827483086513 | 0.08122478566318774911074504701 | 0.5810081562401626952534234193 | 1.806028887813390317641442183 |

All held-out rows had positive pre-clamp numeric traces and valid trace attribution. No held-out row selected an MCV statistic because every selected decision set was Empty; applicable claimed-clause coverage was therefore `NOT_APPLICABLE`, not falsely marked verified. The cohorts contained zero zero-truth rows; this is reported rather than replaced or inferred away.

Validation singleton catalogs retained the requested/payload distinction:

- **forest10**: calibration-e01=no-payload:0; calibration-e12=payload:300; calibration-e23=payload:300; calibration-e34=payload:300; calibration-e45=no-payload:0; calibration-e56=no-payload:0.
- **census13**: calibration-c01=payload:300; calibration-c12=payload:119; calibration-c23=payload:16; calibration-c34=payload:104; calibration-c45=payload:98; calibration-c56=payload:88.

Forest10's validation payloads were present for `e12/e23/e34` (300 items each) and absent for `e01/e45/e56`. Census13's six validation singleton payloads were present with item counts recorded in the bounded evidence. These are validation calibration observations; they were not used to revise the frozen test cohort.

## Model layer versus PostgreSQL layer

The model layer used validation-only positive pre-clamp estimates and truths, with `T=max(1,N)`. Natural logs were quantized to 18 decimal places and represented as `Fraction` strings; exactness applies only to that rationalized model input. The PostgreSQL layer used the actual positive numeric trace from each held-out query, with two repeats on one Issue-owned fixed sample per dataset. The layers are separate and do not establish a PG guarantee.

For every dataset, budget, and method, the recorded selected set was `[]`; all PESS/Nominal/Empty aliases are therefore physically identical. No PESS-versus-Nominal harms, benefits, or ties are interpreted as a treatment result because there was no nonempty treatment contrast. The Empty metrics above are descriptive held-out controls only.

## Provenance and limitations

The formal runner summary is `MEASURED_PENDING_ANALYSIS` before this analysis. Forest10 and Census13 used fresh clusters, fixed samples, PostgreSQL 16.14, and the pinned source/binary audit. Raw trace files remain external under the Issue runtime; bounded ledgers and summaries are committed under `runs/formal-20261020-v3/`.

The result does not establish universal PostgreSQL maximal-matching containment, real-scheme inclusion, PESS dominance, physical maintenance additivity, latency benefit, statistical significance, or population-level generalization. The normalized SQL group overlap and absence of zero-truth rows further restrict interpretation.

Evidence labels: source/build facts are source-derived conditional evidence; the two-dataset rows and metrics are experimentally observed; rationalized model objectives are exact only for their recorded Fraction inputs; the NO-GO judgment is a bounded protocol decision, not a universal theorem.
