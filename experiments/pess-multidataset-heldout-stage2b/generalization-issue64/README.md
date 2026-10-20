# Issue #64 — Stage 2B generalization protocol (Phase 0 only)

**Status: `OUTCOME_FREE_DRAFT_REQUIRES_RESEARCHER_APPROVAL`.** This is a design artifact, not a frozen execution authorization or an experimental result. No fresh cohort has been generated, no test truth or estimate was read, and no PostgreSQL held-out query was measured.

The protocol in [`protocol-v1.json`](protocol-v1.json) is an independent, versioned follow-up. It does not modify `protocol-v4.json`, any v1–v4 evidence, the Stage 2B runner, `ess-postgresql`, `ess-advisor`, or the paper. Historical formal v4 is explicitly not treated as valid new held-out evidence because its coefficient defect was documented; corrected-log PR #58 artifacts remain validation-only until reviewed and pinned.

## AreCEL correspondence and adaptation

Wang et al. define single-table conjunctive cardinality queries and discuss equality, open-range and closed-range predicates (Section 2.1). Their workload generator varies predicate count, predicate columns, in-/out-of-domain centers and range widths (Section 4.1); their motivation includes the absence of a common workload generator and the sensitivity of workload results (Section 2.5). Section 3 defines symmetric natural Q-error as `max(estimate, truth) / min(estimate, truth)` on a positive domain. Table 4 reports P50, P95, P99 and Max Q-error for Census, Forest, Power and DMV.

This study borrows the metric family and workload-shape reporting, not AreCEL's estimator training, experimental numbers, or claims. The proposed primary `Q1=max(E,A,1)/max(min(E,A),1)` is a one-row-floor adaptation, explicitly not the paper's unmodified metric. Natural Q-error is also reported on the positive-positive subset with its denominator, while zero agreement, estimate-only zero, truth-only zero, invalid and nonfinite cases remain explicit. Q1 is measured from PostgreSQL's declared plan estimate; the model's positive pre-clamp log loss is reported separately and is not interchangeable with rounded/clamped `Plan Rows`.

P95 is primary per dataset; P50/P99/Max are secondary. Per-query paired `log(Q1_PESS)-log(Q1_Nominal)` is used for benefits/harms/ties and group-resampled uncertainty. Plans and repeated physical sample realizations are not counted as independent queries. No pooled primary metric is proposed.

## Workload, independence and physical boundary

The Issue #59/PR #60 v4 audit is descriptive, outcome-free structural evidence. It reports exact/template overlap across the legacy splits and strict exact-two-predicate eligibility of only 0.52%–4.16% across the four datasets. Thus a generalized evaluation should allow 1..D predicates and retain all valid generated queries; graph conflict, usable MCV payload and selected-OID trace are strata, not silent eligibility filters. Existing test sets are not fresh: prior exposure bars their reuse for the primary prospective evaluation.

The proposed new cohort is generated per dataset with fixed, reviewable seeds and template fingerprints assigned to splits before labels are opened. Entire normalized predicate-template SHA-256 groups belong to one split. Exact SQL and template hashes are compared against all historic split/cohort manifests; overlap is reported and quarantined without looking at outcomes. At least 1,000 unique held-out template groups per dataset is proposed for P95 stability; P99/Max remain tail-descriptive. A failure to form a clean cohort is `BLOCKED/INCONCLUSIVE`, not permission to reuse exposed outcomes.

Calibration, coefficient derivation and resource optimization happen separately on each dataset. The four bounded candidate universes are inherited from the outcome-free Issue #59 audit (six Forest pairs, six Census pairs, ten DMV adjacent pairs, six Power adjacent pairs); they are not exhaustive across table columns. Budgets 0/2/3/5 use one additive candidate-count proxy unit and do not assert physical maintenance additivity. Every optimal resource set is recorded; a deterministic lexical rule selects one deployed set, while PG creation order is separately fixed to candidate order.

Keep four layers distinct:

1. **Model objective:** corrected-log Nominal and task-wise PESS objectives, selected independently per dataset from validation only.
2. **Resource decision:** unordered extstats set at each budget; report all minimizers/ties and chosen deployed set.
3. **Physical PG behavior:** actual catalog object definitions/OIDs, usable MCV payload and per-query selected-OID/clause traces; `EXPLAIN` alone is insufficient.
4. **Held-out evaluation:** PG row estimate versus cardinality truth under paired query IDs; no result feeds back into model choice, resources or cohort membership.

PostgreSQL’s matching correspondence is scoped and conditional. Queries with >2 predicates and conflicting candidate edges are retained, but a matching in the abstract graph is not asserted to be what PostgreSQL selected. Mismatch and incomplete traces are reported. Same PG build, table bytes, settings and sampling conditions are required within each dataset. The draft proposes two physical sample replicates and a sample-identity/comparability gate; this gate is not yet demonstrated and can block the study.

## Phase 0 feasibility and stopping point

Source-derived from merged #59: four datasets and candidate definitions are documented; structural overlap exists; DMV11/Power7 physical payload/traces are `NOT MEASURED`; no fresh cohort is available from this protocol. Historical Forest/Census PR #58 evidence is not repurposed as new held-out evidence. Corrected-log validation artifacts require PR #58 source/input pin review. Sample identity, runtime and disk caps need a real preflight. All these are explicit `NOT RUN`/approval gates.

The proposed upper cap is 56,000 count-query plans (4 datasets × at most 7 distinct sets × 2 sample realizations × 1,000 query groups), 24 hours per dataset and 100 GiB disposable data, subject to researcher feasibility approval. At least two datasets must pass all gates for cross-dataset replication language. Stop per dataset on integrity, trace, comparability or resource-cap failures; preserve the failed state and do not substitute queries or rerun based on outcomes.

**Stop here.** Phase 0 did not read test truth/estimates or execute PostgreSQL measurements. Researcher review is required for Q1, the prospective cohort and independence gate, bounded candidate sets/budgets/ties, corrected-log implementation, sample/trace gates, and resource caps. A separate explicit authorization is required before any future held-out outcomes are opened or measured.
