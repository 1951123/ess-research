# ESS mathematical formulation audit — working draft for #130

Status: **draft, not yet a theorem-verified manuscript patch**. Based on current `paper/main.tex`, `docs/RESEARCH_CONTEXT.md`, and the restricted PostgreSQL matching correspondence note. This document records the concrete outcome of the author's 108-round concept interview and starts the mathematical correctness audit.

## 1. Specific manuscript changes

1. Rename central concept and proposed title to **Estimation Scheme Uncertainty**. Its causes include unknown deterministic application policies *and* intrinsic randomization; multiple admissible schemes alone do not imply uncertainty to an advisor who can perfectly predict selection. No requirement that scheme changes change loss or the resource decision.
2. Separate **general ESS** from the **restricted two-column PostgreSQL MCV matching model**. Move existing Section 2.4 to an instance section, and put source-level conditions A1–A4 before structural matching theory. Preserve the separation between source-grounded matching structure and assumed multiplicative numerical loss.
3. Replace the general objective's implicit additive/taskwise focus with an explicit **joint uncertainty model**, workload aggregation, and scheme-risk evaluation. Probability is optional *additional data* and cannot be reconstructed from a set of possible outcomes.
4. Add a population layer that is genuinely linked to the empirical objective; do not claim that training PESS and evaluating physical PG P95 is same-objective generalization.
5. Change the Nominal description from “known fixed priority” to “fixed reference application behavior, potentially observed as a stable black box.”
6. Keep existing modeling-vs-physical limitations and do not assert universal PESS dominance in physical evaluation.

## 2. Finite-sample mathematical core (candidate definition)

Fix a finite optional resource universe `E`, known nonnegative set cost `C:2^E→R_+`, budget `B`, and a **nonempty** feasible family `F_B={M⊆E:C(M)≤B}`. Neither cost additivity nor cost monotonicity is required. Empty selection can be feasible but need not be forced by the general definition.

For each training task `i∈{1,…,n}`, let `Ω_i` be a finite universe of **complete** schemes and `Γ_i(M)⊆Ω_i` a nonempty prescribed admissible family for every feasible `M`. Each scheme is sufficient to determine the modeled estimate and task loss `L_i:Ω_i→R_+`. Across configurations, the same scheme has the same modeled loss. Let `used(σ)⊆E` denote optional extra resources used by a scheme; require `σ∈Γ_i(M) ⇒ used(σ)⊆M`. Always-available baseline statistics need not belong to `E`. No nesting or enumerability requirement is imposed.

The joint-scheme uncertainty model is a **nonempty** family

`U_n(M) ⊆ ∏_{i=1}^n Γ_i(M)`.

This is a prescribed model, not necessarily the set of physically reachable scheme tuples. Define the associated loss-image set

`Lset_n(M) = {(L_1(σ_1),…,L_n(σ_n)) : (σ_1,…,σ_n)∈U_n(M)}`.

Let `A_n:R_+^n→R_+` be a **coordinatewise nondecreasing** workload aggregation function. The aggregated loss image is

`V_n(M)={A_n(ℓ):ℓ∈Lset_n(M)}`.

Specify a risk evaluation rule `ρ` with a **precise domain** and **any required auxiliary information** (such as probability weights over *joint scenarios*, not only their distinct loss values). The objective is

`F_n(M)=ρ(V_n(M); auxiliary uncertainty data)`

and ESS chooses `argmin_{M∈F_B}F_n(M)`. Require finite, well-defined objective for all feasible `M`.

**Mathematical warning:** `V_n(M)` alone discards the multiplicity of joint schemes and any scenario probabilities. It therefore cannot define expectation over orders or stochastic policies unless the uncertainty data retains a push-forward probability measure. Moreover, the previously agreed “loss monotonicity” of an arbitrary set-valued risk functional has to be formulated with a suitable coupling/dominance relation; **do not** impose set-inclusion monotonicity as a universal axiom. In the first manuscript draft, it is safer to state monotonicity for `A_n` and for clearly specified risk functionals, instead of an undefined universal order on sets.

**Basic instances with `A_n(ℓ)=Σ_i ℓ_i` (or `n^{-1}Σ_iℓ_i` consistently):**

- **Reference/Nominal**: `U_n(M)={ (σ_i^{ref}(M))_{i=1}^n }`; risk is the unique aggregate loss. Reference need not be internally known.
- **Shared-global worst**: for a fixed policy space `Θ` and well-defined compatible mapping `σ_i(M;θ)∈Γ_i(M)`, let `U_n(M)={ (σ_i(M;θ))_i : θ∈Θ}` and `ρ(V)=max V`. The same `θ` applies to every task and has stable semantics across candidate `M`; the chosen scheme can change with `M`.
- **Task-wise PESS**: `U_n(M)=∏_i Γ_i(M)` and `ρ(V)=max V`. For the sum aggregation this equals `Σ_i max_{σ∈Γ_i(M)}L_i(σ)`.
- **Assumed-policy mean**: equip the policy/tuple space with a specified probability law `Q_M`, or derive it as the restriction/push-forward of a declared reference law. Take expectation of `A_n` under that law. Uniform **orders** are not uniform distinct scheme outcomes and are not claimed to be production randomization.

Crucially, **single-task realizability** of each scheme does not entail **simultaneous realizability** of arbitrary tuples. No realizability completeness assumption is part of general ESS. Nor does `Γ_i(M)` necessarily contain physical `R_i(M)`; no unconditional physical upper bound follows.

## 3. General baseline result and exact scope

For a fixed `M`, any two nonempty joint uncertainty sets `U_n^1(M)⊆U_n^2(M)`, and the **same** loss map and aggregator, give

`sup_{σ∈U_n^1(M)} A_n((L_i(σ_i))_i) ≤ sup_{σ∈U_n^2(M)} A_n((L_i(σ_i))_i)`.

This follows from suprema over nested sets and does **not** need nonnegative losses or coordinatewise monotonicity of `A_n` (only defined values). It is a basic property, not a novel theorem. The difference `Δ_n(M)≥0` is a model-relaxation *risk gap at fixed M*, not a guarantee about chosen resources, greedy outputs, or physical Q-error.

For different objectives `F^1,F^2`, define optimal resource *sets* `argmin_{M∈F_B}F^j(M)`; their inequality is distinct from a fixed-set risk gap. In experiments, different **greedy** outputs are not evidence of different globally optimal solution sets.

## 4. Population/empirical correspondence: exact theorem prerequisites

Let tasks `X_1,…,X_n` be IID from fixed, unknown `D`. A population objective must be specified separately, together with a sample objective estimating **that same** objective and scheme uncertainty model. In particular:

- Shared policy `R_shared(M)=sup_{θ∈Θ} E_{X∼D}L_X(σ_X(M;θ))`.
- Empirical `Rhat_shared,n(M)=sup_{θ∈Θ} n^{-1}Σ_i L_{X_i}(σ_{X_i}(M;θ))`.
- Taskwise PESS `R_PESS(M)=E_{X∼D}[sup_{σ∈Γ_X(M)}L_X(σ)]`, with corresponding empirical average.

The shared-policy sup is **outside** the expectation, whereas PESS's sup is **inside**. They are different models, not interchangeable transformations.

**Conditional elementary bound:** for any real-valued population objective `R`, matching empirical objective `Rhat_n`, and algorithm output `Mtilde_n∈F_B`,

`R(Mtilde_n)-min_M R(M) ≤ 2 sup_{M∈F_B}|Rhat_n(M)-R(M)| + [Rhat_n(Mtilde_n)-min_M Rhat_n(M)]`.

This is a deterministic decomposition into uniform statistical discrepancy and empirical optimization error. A finite `E` makes `F_B` finite, so *if* pointwise convergence holds for each `M`, the supremum discrepancy converges, but IID tasks **alone do not ensure pointwise convergence for an arbitrary shared-policy supremum**.

Candidate next proof: under a finite `Θ` and suitable integrability of each `L_X(σ_X(M;θ))`, SLLN and finite maxima imply pointwise convergence of shared risk, then uniform convergence over finite `F_B`. For **infinite** `Θ`, additional uniform law-of-large-numbers assumptions are needed. **Do not generalize this proof to arbitrary P95/risk models** without checking appropriate quantile regularity, probability assumptions, and objectives.

**Boundary:** the current physical PG evaluation uses held-out Plan Rows Q-error and, in one arm, expectation of per-order Test P95 under an explicit *counterfactual* uniform relative-OID order population. These are not by default equal to the model-loss population objectives above. “Workload generalization” and “sensitivity across application policies” are distinct dimensions.

## 5. Existing source-backed instance and proof boundaries

The pinned PostgreSQL REL_16_14 note `notes/pg-mcv-maximal-matching-correspondence.md` establishes under A1–A4:

1. A fixed candidate tie order yields an **inclusion-maximal matching** of eligible labeled two-column MCV resources.
2. Under *freely variable abstract strict edge order*, every maximal matching is individually realizable.
3. The result **does not** establish simultaneous realization of arbitrary tasks' target matchings by one shared priority, nor that a fixed physical catalog can realize all abstract orders.
4. It proves no numerical fidelity for the illustrative `n_i^0 ∏_{e∈S}r_{e,i}` model. Its log loss is a *mathematically chosen approximation*, separate from physical PG Plan Rows Q-error.

Existing paper instance-specific results (shared-priority compatibility, strict `G<P` witness, task-factor bound and tightness, nonmonotonicity, fixed-set shared-order hardness) must remain clearly labeled **restricted-instance**. In particular the order-hardness result does **not** prove NP-hardness of the outer resource selection problem.

## 6. Proof and editorial audit findings

- Existing `paper/main.tex` already defines a generic set maintenance cost and nonnested `Γ` correctly; **do not present these as new changes or invent unsupported novelty**.
- Existing “known fixed priority” Nominal description is overly specific relative to author's intended baseline; revise to “fixed reference behavior (potentially black-box evaluated).”
- Existing `Γ_i:2^E→2^{Ω_i}\setminus\{∅\}` requires nonempty schemes even for *infeasible* resource sets; could retain this stronger convenience convention or restrict only to `F_B`; document the choice.
- The initial manuscript explicitly assumes **finite** per-task scheme universes and **finite** policy space for its core results. Retain these where proofs invoke maxima; population extensions with general `Θ` need separate conditions.
- Distinguish **loss monotonicity in coordinatewise comparable outcomes** from **risk monotonicity under expanding scenario sets** and from **resource monotonicity**. None implies the others by definition.
- The basic nested-sets risk inequality holds under a common objective and fixed `M` only. Do not claim it predicts a resource set or physical Test performance.
- Check carefully before adding any population theorem: uniform LLN under shared-global supremum; quantile assumptions if P95 is analyzed; scheme-parameter measurability; algorithm error if greedy replaces exact ERM.

## 7. Proposed section sequence and implementation plan

1. Introduction + title/abstract (formulation-first claim).
2. **General ESS Formulation**: resources, tasks, schemes, losses, joint uncertainty, workload aggregation/risk, concrete objectives, finite-sample optimization, carefully scoped population counterpart.
3. **Restricted PostgreSQL MCV Instantiation**: assumptions A1–A4, source-level selector, maximal matching, *assumed* multiplicative estimator.
4. **Structural Properties**: shared-priority realizability, `A≤G≤P` and task-factor bound, examples, computational hardness.
5. Experimental protocol (same greedy for Nominal/PESS; reference OID intervention; frozen Train/Test).
6. Results (claim/evidence alignment, not extra experiments).
7–9. Threats, related work, conclusion.

Target **12 pages of main text**, adding chiefly mathematical clarity and theory; actual allocation is subject to TeX compilation. No new experiments, algorithms, physical-worst guarantees, or unsupported generalization statements.

## 8. Open correctness gates

- [ ] Specify a risk interface that handles scenario sets and optional *joint* probability laws without implying all risk rules are defined by bare sets.
- [ ] State precisely what monotonicity assumptions are needed, avoiding unsupported dominance relations on arbitrary sets.
- [ ] Verify and if appropriate prove a **finite-policy / finite-resource** population consistency lemma; do not pretend it covers all abstract risk objectives.
- [ ] Recheck the existing instance-specific proofs against their assumptions before moving sections.
- [ ] Draft the actual LaTeX revision, compile, and check paper-level references/page count separately.

*This audit note is a staged research artifact; it has not modified `paper/main.tex` and is not a claim that 12 pages or the final theory have been completed.*

## 9. First LaTeX implementation pass (2026-10-28)

- Updated `paper/main.tex` on this draft branch: new scheme-uncertainty title and terminology; refined Nominal description; added `sec:joint-framework` and `sec:population` with labeled formulas.
- **Proved conditional finite-policy consistency**: for finite feasible `F_B` and finite nonempty `Θ`, measurable integrable task losses imply pointwise SLLN for every resource-policy pair, hence uniform convergence of shared-policy empirical risk across the finite set, and consistency of exact empirical minimizers. This is a narrow, valid candidate proposition, not an infinite-policy or quantile theorem.
- **Proved deterministic optimization/statistics decomposition**: population excess risk is bounded by twice the uniform empirical-to-population discrepancy plus empirical suboptimality. It supplies no greedy guarantee absent a bound on the latter.
- **Basic joint-family relaxation result**: nested model families imply ordered fixed-set worst-case objectives; this is elementary and not advertised as headline novelty.
- Mechanical sanity check of updated TeX: new labels occur exactly once, braces balanced, old sections still present. **No successful LaTeX compilation or PDF/page-count verification yet.**
- **Outstanding primary structural edit**: move pairwise-MCV definition from the general Section 2 into the restricted instance; order source-level A1–A4 before the full instance-specific theory; eliminate duplication and repair cross-references. Current document intentionally has both general and old objective subsections during transition.
- **Additional editorial issue**: updated abstract still describes the old fixed-priority taxonomy and should be revised once Section 2–4 restructuring is complete. Do not claim 12-page compliance until a compiled PDF is checked.

## 10. Section architecture implementation (2026-10-28)

- Reorganized `paper/main.tex` on the draft branch into: Introduction; Problem Formulation (now incorporating general objectives and population risk); A Scoped PostgreSQL MCV Mechanism (including pairwise MCV family and modeled loss); Structural Properties of the Restricted Instance; Experimental Protocol (including frozen greedy procedure); Experimental Results; Threats; Related Work; Conclusion.
- Updated the abstract and main contribution wording to lead with **Estimation Scheme Uncertainty**, preserve the scope of the source-grounded matching result and its deliberately approximate numerical loss, and correctly state held-out physical comparisons.
- Mechanical checks at section-move commit: 9 sections preserved; no duplicated TeX label strings; no experiments modified.
- The original figure of the three-edge path is still introduced in the Introduction, with its technical justification deferred to the instance section. The source-level correspondence proposition still refers forward to the individual matching-completeness proposition, which is acceptable for LaTeX cross-references but should be considered for reader flow.
- **Not yet verified by compilation:** valid TeX/pvldb class output, hyperlink/label resolution, theorem page breaks, and main-text page count. Treat this as a draft patch; further proof and editorial checks remain before review-ready status.

## 11. Structural and build feasibility check (2026-10-28)

- Reordered restricted mechanism section: source-level selector and A1–A4 now precede the graph/matching abstraction and numerical proxy, making physical assumptions visible before interpreting abstract maximal matchings.
- Connector-based static audit of `paper/main.tex`: **45 labels, no duplicate labels, zero unresolved \\ref/\\eqref/\\autoref targets within this file, balanced literal curly braces**. These checks do not replace an actual TeX engine run.
- Local build environment has `pdflatex` and `latexmk`; however the current GitHub branch's source and its dependencies could not be downloaded into that runtime due disabled outbound DNS. The mounted `/mnt/data/main.pdf` is an **older 9-page PDF titled 'Estimator Strategy Uncertainty'**, not the updated manuscript, so its page count is not evidence for this draft.
- **Blocked verification gates:** compile current branch, resolve build warnings and citation dependencies, inspect resulting typography/figures, and confirm 12 pages of main text. Do not mark these complete until using the actual updated source.

## 12. User-supplied compiled PDF inspection (2026-10-28)

The author compiled the current draft and supplied `main(1).pdf`. Direct inspection using `pdfinfo` and PDF text extraction confirms:

- **10 letter-size PDF pages**, not yet the target of **12 main-text pages**. Section 9 Conclusion and References both occupy the final page (p. 10), so main text is **less than 10 full pages**.
- Updated **Estimation Scheme Uncertainty** title and abstract are present.
- The new joint-family / aggregation / risk section, empirical/population distinction and **Proposition 2.2 finite-policy consistency** appear on pp. 2–3.
- Section sequence is as intended: 1 Introduction, 2 Problem Formulation, 3 Scoped PG Mechanism, 4 Restricted Instance Theory, 5 Experimental Protocol, 6 Results, 7 Threats, 8 Related Work, 9 Conclusion.
- Visual inspection of pp. 3 and 6 showed formulas/table and two-column text readable, with no obvious gross overlap in those inspected pages. **Not a full visual page-by-page preflight**.
- PDF textual inspection confirms cross-references to Proposition 4.2 from Proposition 3.1 resolve after restructuring.
- Next: deepen substantively justified mathematical material to reach 12 *main-text* pages; do not merely add filler, new experiments, or falsely claim 12-page compliance.

The PDF is a user-provided compilation artifact, not generated by the assistant or committed to the repository. This note records inspection findings only.

## 13. Risk interface and matched-population theorem pass (2026-10-28)

- Replaced vaguely typed optional `Q_M` in `F_n(M)` with an explicit distinction: a probability distribution `Q_M` on **joint scheme outcomes** and its push-forward `ν_M` to aggregated losses. This correctly retains probability weights even when distinct schemes yield identical losses. Worst-case risk needs no probability; expectation requires it. A support set alone does not determine expected loss.
- Removed duplicate explanation of Nominal/shared/PESS joint families in the general framework; the immediately following subsection continues to supply the concrete formulas.
- Added **Proposition 2.3 (Task-wise pessimistic consistency)** under measurable integrable taskwise maximum loss and IID tasks, finite feasible resource family. Proof applies scalar SLLN per resource set and finite uniformization. This is separate from finite-policy shared-global consistency and does not need finite `Θ` because no global policy sup is present.
- Narrowed the claims of the two consistency propositions: neither establishes rates, arbitrary quantile-risk consistency, physical PG Plan Rows P95 generalization, or greedy optimization guarantees.
- Static source checks after edits: 46 distinct labels, no missing internal `ref/eqref/autoref` targets, literal TeX curly braces balanced.
- **Pending:** author recompilation for exact new pagination and all-page rendering, and holistic proof and copy-edit audit. The earlier user-compiled PDF has 10 pages; it predates these latest changes.
