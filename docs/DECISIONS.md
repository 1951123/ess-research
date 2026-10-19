# Research decision log

**Purpose:** Why the current research and collaboration strategy exists. Each decision is revisable if the listed triggers arise. Date refers to when the project discussion reached the decision, **not** to experimental proof.

## D-001 — Paper architecture (2026-10-17; accepted, revisable)

**Decision:** Aim for **general estimator-agnostic formulation + a structured pairwise maximal-matching instantiation + theoretical/algorithmic results + PostgreSQL-facing validation** in the first paper.

**Rationale:** A wholly unrestricted \(\Gamma_i\) / loss / maintenance black-box problem is too general to carry strong algorithmic claims on its own. A PG-only engineering paper would understate the importance of unknown scheme-selection policies. A structured instance allows formal proofs, algorithms, and falsifiable empirical claims.

**Alternatives considered:** a general-theory-only paper; a PG-specific advisor/implementation-only paper.

**Revisit if:** no meaningful structural/algorithmic contributions emerge or no defensible DBMS semantics can support the proposed instance. Avoid claims of novelty without literature comparison.

## D-002 — Unknown choice policy and prescribed admissibility (2026-10-17; accepted)

**Decision:** Treat the estimator's *scheme-selection policy as unknown*. Define \(\Gamma_i(M)\) as a model of **complete admissible schemes**, which should be justifiable but **need not equal** the real possible-choice set \(\mathcal R_i(M)\). The outer decision remains an unordered resource set \(M\), **not** a chosen PG OID/creation order.

**Rationale:** Estimator internals are not always accessible (especially in closed-source DBMSs); estimating a single nominal scheme can hide policy uncertainty. A model is only as reliable as its semantics and evidence.

**Critical limits:** Over-approximation yields real worst-loss bounds only when \(\mathcal R_i(M)\subseteq\Gamma_i(M)\) and losses align. Without a demonstrated relation, report the worst case **within the model**, not a universal real-system guarantee. Joint global policies may couple choices across tasks while the objective maximizes tasks individually.

**Revisit if:** a specified application can access and control the real policy, or a refined uncertainty rule gives meaningfully better decision quality.

## D-003 — Maximal matching is a structured research abstraction (2026-10-17; accepted, fixture-level PG validation completed)

**Decision:** Study pairwise labeled-edge maximal-matchings as the first structured admissibility model, justified by the *restricted* greedy MCV selection control flow in PostgreSQL 16.14.

**Why:** Under simple single-table AND conditions and eligible built two-key MCV objects, PG repeatedly chooses an object covering two still-unestimated attributes and stops when none remain. A fixed catalog order selects **one** maximal matching. All maximal matchings are realizable if the **abstract tie order** is allowed to vary freely; this does **not** assert actual PG nondeterminism or arbitrary order realization in one fixed catalog.

**Primary artifacts:** [merged correspondence note](../notes/pg-mcv-maximal-matching-correspondence.md) ([ess-research PR #1](https://github.com/1951123/ess-research/pull/1)); [merged DEBUG1 instrumentation](https://github.com/1951123/ess-postgresql/pull/1); [fixture-level runtime report and raw evidence](../experiments/pg-tracing/runs/20261017/report.md) ([ess-research PR #4](https://github.com/1951123/ess-research/pull/4)).

**Evidence status (updated 2026-10-17):** conditional propositions are source-derived for PostgreSQL 16.14; **runtime observations support the four-attribute path fixture** under two statistics-object OID orderings (`{ab,cd}` and `{bc}`). The experimental run used the tracing branch before instrumentation was merged to PG `main`. This does not establish the assumptions for arbitrary queries or realize all abstract orderings simultaneously for a multi-task workload.

**Revisit if:** further runtime tracing contradicts scoped assumptions or the matching abstraction has unacceptable misspecification/decision regret. Broaden or replace the *instance* rather than silently weakening the generic framework.

## D-004 — Separate mathematical idealization from DBMS claims (2026-10-17; accepted)

**Decision:** Preserve three separate kinds of statement: (i) results proven for the mathematical optimization model; (ii) conditional assertions derived from inspecting a specific DBMS's code; (iii) empirical DBMS behaviors established by executed experiments.

**Rationale:** A conditional proof does not demonstrate that all queries meet its assumptions; synthetic optimizer tests do not establish real estimator fidelity, maintenance cost, or plan benefit.

**Consequences:** The pre-clamp log-loss is the primary theoretical measure; physical PostgreSQL plan-row output is secondary. The additive maintenance budget is a controlled proxy. Record nonzero/positivity assumptions and compiler/version details. Label unresolved solver-numerical status honestly.

## D-005 — GitHub-centered, local-executed research collaboration (2026-10-17; accepted)

**Decision:** Keep **VS Code + local Codex** for execution, builds and experiments; use **ChatGPT** primarily for research planning, theorem review, task specifications and PR review; use **GitHub** as the durable collaboration and evidence center across multiple chat sessions.

**Repository roles:** `ess-research` owns cross-repo context/decisions/status/paper; `ess-advisor` owns optimization implementation/tests; `ess-postgresql` owns PG source/instrumentation.

**Minimum protocol:** One small, reviewable scope per task/branch; branch + Draft PR for risky or agent-created cross-repo work; direct-to-`main` is permissible for small, well-understood edits if the researcher prefers. No compulsory Git Flow or GitHub Projects. Only the researcher decides whether a draft PR is ready to merge.

**Why:** Chat sessions have finite context and are not a durable research record. Commit decisions/verified outcomes and links to evidence, rather than full chat dumps.

**Revisit if:** multiple concurrent agents create conflicts; a larger team requires stronger reviews/CI or branch protection.

## D-006 — Research status vocabulary (2026-10-17; accepted)

Use these terms consistently:

- **Proven (model-internal):** a theorem with precisely stated assumptions and a checkable mathematical argument.
- **Source-derived (conditional):** follows from inspected source code given version and preconditions, without runtime confirmation.
- **Experimentally observed:** result from executed, reproducible tests, with environment, inputs, raw output and limitations recorded.
- **Conjecture:** stated but not proved.
- **Open / pending:** unverified question or task.
- **Refuted / superseded:** disproven or replaced, with a link to the counterexample/newer decision.

Do not describe a source-derived claim as experimentally observed, an unmerged PR as accepted `main` content, or a floating-point MIP solver status as an exact-arithmetic proof.

## D-007 — Match the optimization objective to policy knowledge (2026-10-19; accepted, revisable)

**Decision:** Nominal, Joint-Robust, and task-wise PESS are **different, conditionally justified optimization problems**, not methods with a universal ranking of decision quality. The objective should reflect what is defensibly known about the estimator's *complete scheme-selection behavior*:

- **Nominal:** The actual policy (or the task-wise schemes it induces for each candidate resource set) is known and predictable. Optimize loss under that specified policy.
- **Joint-Robust:** The policy is unknown, but all tasks are known to be coupled by **one shared global policy parameter** \(\theta\in\Theta\), such as a common candidate-priority order. Optimize worst aggregate loss over this justified shared family. Merely saying the implementation is deterministic or "fixed" is insufficient: the assumed global coupling and policy family must also be justified.
- **PESS:** Only the admissible complete-scheme family \(\Gamma_i(M)\) can be justified for each task, without a trustworthy cross-task shared-policy constraint. Minimize the sum of **independent task-wise worst losses**. This is appropriate for inaccessible or potentially varying policies, including possible task-/run-dependent choices, provided the prescribed family safely contains the choices being evaluated. It does not assert that PostgreSQL selects MCVs randomly.

For a fixed feasible unordered resource set \(M\), denote the schemes selected by shared policy \(\theta\) as \(\sigma_i(M;\theta)\), and define

\[
\begin{aligned}
F_{\rm Nom}(M)&=\sum_i w_i\ell_i(\sigma_i(M;\theta_0)),\\
F_{\rm Joint}(M)&=\max_{\theta\in\Theta}\sum_i w_i\ell_i(\sigma_i(M;\theta)),\\
F_{\rm PESS}(M)&=\sum_i w_i\max_{\sigma\in\Gamma_i(M)}\ell_i(\sigma).
\end{aligned}
\]

**Conditional relation:** If \(\theta_0\in\Theta\), and \(\sigma_i(M;\theta)\in\Gamma_i(M)\) for **every** task \(i\), feasible \(M\), and \(\theta\in\Theta\), then
\(F_{\rm Nom}(M)\le F_{\rm Joint}(M)\le F_{\rm PESS}(M)\) pointwise.
These inequalities express the inclusion of modeled uncertainties; they do **not** imply a universal ranking of the **selected resource sets** under an external or actual policy. If the shared family is misspecified, its robust guarantee need not cover the real behavior. Likewise, PESS bounds real worst-case losses only under justified inclusion \(\mathcal R_i(M)\subseteq\Gamma_i(M)\) and aligned estimator/loss assumptions (D-002).

**Rationale:** Greater policy knowledge can legitimately permit a less conservative objective; weaker knowledge motivates a broader admissibility-based worst case. Comparing the three objectives tests the consequences and sensitivity of **different information assumptions**, not whether PESS must outperform Nominal or Joint-Robust everywhere. If a trustworthy stochastic distribution is known, expectation- or risk-sensitive objectives may also be appropriate; PESS is not a universal optimizer for stochastic settings.

**Consequences for the first paper:** Retain **PESS under unknown/inaccessible policy** as the main algorithmic research focus, with Nominal and Joint-Robust serving as explicitly assumption-scoped comparisons. Study (a) correctness/adequacy of each modeled scheme family, (b) decision and conservatism gaps under *common evaluation conditions*, (c) robustness to misspecified shared-policy assumptions, and (d) new algorithms for the structured PESS problem. Never present coincident PESS/Joint selections as a failure, treat all abstract shared orders as physically realizable PG OID orders, or promote PG-calibrated model losses to actual latency benefits. The unordered resource set remains the decision, not an OID/creation order (D-002/D-003).

**Context:** [Issue #14](https://github.com/1951123/ess-research/issues/14) (decision value / price of pessimism) and [completed Issue #23](https://github.com/1951123/ess-research/issues/23) (real Forest10 measured-input model comparison). Neither supplies a policy-agnostic empirical dominance claim.

**Revisit if:** New source/runtime evidence establishes stronger shared-policy constraints, disproves the chosen admissibility coverage, or motivates a different justified uncertainty or stochastic model.
