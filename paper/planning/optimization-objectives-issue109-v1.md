# Section 3 — Optimization Objectives and Their Relationships (v1)

**Status:** standalone review draft for Issue #109; compatible with the merged Introduction and Section 2, and not yet integrated into `paper/main.tex`. This is a *modeling-first* section: PostgreSQL evaluation is evidence for later sections, not a justification for defining the optimization objectives.

## 3. Optimization Objectives and Their Relationships

### 3.1 Why policy information changes the objective

The decision variable is an unordered installed resource set \(M\in\mathcal F_B\). For each task \(i\), Section 2 specifies a nonempty family \(\Gamma_i(M)\) of complete admissible schemes and weighted loss \(L_i(\sigma)=w_i\ell_i(\sigma)\). These definitions do not prescribe how a particular database chooses one scheme from that family. The appropriate ESS objective therefore depends on the *information available about that choice*, rather than only on available statistics and maintenance cost.

If the application strategy is known and stable, its induced schemes provide a defensible **Nominal** evaluation. If an uncertain but trustworthy *shared policy family* couples scheme choices across tasks, the appropriate worst case maximizes total loss over that common family. If only task-specific admissibility is justified, without a reliable shared coupling constraint, a **task-wise pessimistic** objective treats each admissible family independently. These are distinct mathematical optimization problems; none is unconditionally best under another problem's evaluation rule.

Let \(\Theta\) be a nonempty finite global policy family, with induced schemes \(\sigma_i(M;\theta)\in\Gamma_i(M)\) for every \(i,M,\theta\). For a specified \(\theta_0\in\Theta\), define
\[
\begin{aligned}
F_{\rm Nom}(M;\theta_0)&=\sum_i L_i(\sigma_i(M;\theta_0)),\\
F_{\rm Joint}(M)&=\max_{\theta\in\Theta}\sum_i L_i(\sigma_i(M;\theta)),\\
F_{\rm PESS}(M)&=\sum_i\max_{\sigma\in\Gamma_i(M)}L_i(\sigma).
\end{aligned}
\]
The corresponding selection problem is \(\min_{M\in\mathcal F_B} F(M)\) for the chosen loss functional \(F\). Crucially, \(\theta\) or \(\sigma\) is **not** an additional advisor decision optimized jointly with \(M\). The advisor selects only \(M\).

The fixed-set model relationship follows directly:
\[
F_{\rm Nom}(M;\theta_0)\leq F_{\rm Joint}(M)\leq F_{\rm PESS}(M).
\]
The left inequality uses \(\theta_0\in\Theta\); the right requires policy-induced admissibility and the *same* weighted loss. Neither inequality is a bound on the physical Q-error of an estimator whose actual possible schemes have not been shown to lie in the prescribed families. They also do not order objective values across *different* resource sets.

### 3.2 Global priority orders as an explicit model of policy coupling

For the pairwise matching instantiation, let \(\Pi(M)\) denote the finite set of strict total permutations of the labeled selected edges \(M\). Every \(\pi\in\Pi(M)\) is a **single global priority** that applies to all tasks: task \(i\) scans its eligible edges in the order induced by restricting \(\pi\) to \(M\cap\mathcal E_i\), admitting an edge if neither endpoint has yet been consumed. Denote the resulting matching \(\gamma_i(M,\pi)\). This matching is inclusion-maximal in \(H_i[M]\), so
\[
\gamma_i(M,\pi)\in\Gamma_i^{\rm MM}(M).
\]
For each fixed resource set \(M\), write \(Z(M,\pi)=\sum_i L_i(\gamma_i(M,\pi))\). Define four comparison quantities:
\[
\begin{aligned}
N_{\pi_0}(M)&=Z(M,\pi_0),\\
A(M)&=\frac1{|\Pi(M)|}\sum_{\pi\in\Pi(M)}Z(M,\pi),\\
G(M)&=\max_{\pi\in\Pi(M)}Z(M,\pi),\\
P(M)&=\sum_i\max_{\gamma\in\Gamma_i^{\rm MM}(M)}L_i(\gamma).
\end{aligned}
\]
Here \(\pi_0\) is a deterministic nominal order **restricted from a common order on the candidate universe** so that it is defined consistently for any \(M\); the frozen training study uses a candidate-ID order. \(A(M)\) assumes a deliberately specified **uniform distribution on global orders**, not uniformity among distinct matchings, and is an analytical counterfactual unless the application supplies a justified probability law. \(G(M)\) is the worst aggregate loss attainable by **one shared** global order, whereas \(P(M)\) allows a different worst admissible matching for every task.

**Proposition 1 (fixed-set order bounds).** For any fixed \(M\) with \(\Gamma_i^{\rm MM}(M)\) as above, and common finite weighted loss functions \(L_i\),
\[
\boxed{A(M)\leq G(M)\leq P(M),\qquad N_{\pi_0}(M)\leq G(M).}
\]
*Proof.* The arithmetic mean of \(\{Z(M,\pi):\pi\in\Pi(M)\}\) cannot exceed its maximum, and the designated \(\pi_0\) is among those orders. For every \(\pi\) and \(i\), priority-greedy produces an admissible maximal matching, hence \(L_i(\gamma_i(M,\pi))\leq\max_{\gamma\in\Gamma_i^{\rm MM}(M)}L_i(\gamma)\). Summing and maximizing proves the second inequality. \(\square\)

Neither \(A(M)\leq N_{\pi_0}(M)\) nor the reverse generally holds. For distinct selected sets \(M_N\) and \(M_P\), the fixed-set bounds do not imply \(A(M_P)\leq A(M_N)\), any Test-Q-error ordering, or guaranteed superiority of pessimistic training selection.

**Proposition 2 (one task, unconstrained abstract priorities).** For a fixed task graph \(H_i[M]\), every inclusion-maximal matching \(Q\in\Gamma_i^{\rm MM}(M)\) can be induced by some priority order \(\pi\in\Pi(M)\), by placing the edges of \(Q\) ahead of other edges. *Proof.* Greedy admits all pairwise nonconflicting edges of \(Q\). Any remaining eligible edge conflicts with an admitted edge by maximality, so greedy rejects it. \(\square\) This taskwise existence theorem does **not** say that independently chosen \(Q_i\) for multiple tasks are jointly realizable under one global order; nor does it assert unrestricted physical PostgreSQL OID realizability.

### 3.3 Why task-wise pessimism can be strictly conservative

The AB–BC–CD path illustrates two effects. Its maximal matchings are \(Q_1=\{s_{AB},s_{CD}\}\) and \(Q_2=\{s_{BC}\}\). If we uniformly sample all \(3!=6\) distinct global permutations, four produce \(Q_1\) and two produce \(Q_2\); therefore uniform orders induce probabilities \(2/3\) and \(1/3\) on the two matchings—not \(1/2\) each. More generally, matching probabilities depend on the number of priorities inducing each matching.

A second illustration shows a genuine gap between \(G\) and \(P\). Consider **two tasks having the same path graph**, with abstract losses \(L_1(Q_1)=1,L_1(Q_2)=0\) and \(L_2(Q_1)=0,L_2(Q_2)=1\). Each task's maximum is 1, so \(P(M)=2\). However, a shared global order produces either \(Q_1\) on both tasks or \(Q_2\) on both, and the total loss is always 1. Thus \(G(M)=A(M)=1<P(M)=2\). This is a mathematical witness, not a fitted dataset result. PESS can be strictly more conservative because it removes cross-task policy coupling.

There is also no general monotonic-improvement guarantee as a resource is added. Consider a task whose complete scheme is \(Q_1=\{s_{AB},s_{CD}\}\) when only those two resources are installed, with \(L(Q_1)=0.1\). Adding \(s_{BC}\) permits the additional complete matching \(Q_2=\{s_{BC}\}\), with a hypothetical loss of 2.0. Then \(P(\{s_{AB},s_{CD}\})=0.1\) while \(P(\{s_{AB},s_{BC},s_{CD}\})=2.0\). This establishes possible nonmonotonicity of the prescribed worst-case objective, not a physical claim that adding an MCV object always harms PostgreSQL. In particular, resources and *complete admissible schemes* cannot be modeled as nested families by default.

### 3.4 Which objectives are actually optimized in the frozen study?

The empirical selection study trains **two policies only**: Nominal \(N_{\pi_0}\) and task-wise PESS \(P\). Its separate selections \(M_N(B)\) and \(M_P(B)\) are produced on the original AreCEL **Train** tasks by the same add-only greedy method under a common, frozen nonnegative additive budget proxy \(\sum_{e\in M}\bar m_e\leq B\), for \(B\in\{0,2,3,4,5\}\). Starting from the empty set, the algorithm chooses a *feasible single addition* with the greatest **strictly positive** decrease in that objective, resolves ties deterministically by candidate ID, and stops when no such improving addition exists. It does not force a set to use all of its nominal budget, perform deletions or swaps, or claim global optimality. Equal B values need not yield equal selected counts.

For the purpose of transparent comparisons, the subsequent offline model study evaluates \(N_{\pi_0}(M),A(M),G(M),P(M)\) on the **already-selected fixed sets** by enumerating all global priority permutations (25 distinct physical resource configurations, 906 permutations in aggregate). Importantly, neither \(A\) nor \(G\) was trained or used to reselect \(M\) in the frozen evidence. The independent *physical* PostgreSQL evaluation measures held-out, rounded/clamped Plan Rows Q-error under fixed or sampled relative-OID orders. It does **not** directly measure the pre-clamp model loss \(L_i\) or optimize the budget under physical Test outcomes.

An abstract upper bound on loss should thus be described as **model-internal** unless a physical containment and metric-alignment argument is established. Uncertainty over a globally sampled priority is a *counterfactual test distribution*, not a statement that PostgreSQL assigns new random OIDs per query. Results can compare the consequences of different modeling assumptions; they cannot establish that one assumption or chosen set dominates in all deployed systems.

### 3.5 What this theory establishes—and leaves open

The formal contribution is a hierarchy of strategy-information assumptions and an explicit distinction between shared/global and independently taskwise adversarial choices. It establishes exact inclusion-maximal-matching statements and fixed-set objective inequalities within a specified model. It does **not** prove that the real PostgreSQL selector is encompassed for every query, that its outputs equal the multiplicative model after clamping, or that an independently greedy-selected PESS set gives lower held-out Q-error than a Nominal set. These require the scoped source/experiment arguments in later sections.

---

## Review anchors and provenance (outside manuscript prose)

- **Mathematical soundness:** Verify \(\pi_0\) comes from a global candidate-ID order; prove every priority-greedy output is *maximal*, not necessarily maximum cardinality; check the permutation multiplicities 4/6 and 2/6; check two-task witness \(G=1<P=2\).
- **Objective/algorithm separation:** \(N,P\) trained with the same strict-improvement add-only heuristic, \(A,G\) read-only offline evaluation. No data leakage from official Test. No claim of optimizing \(A\), \(G\) or exact physical expected P95.
- **Compatibility:** [Merged Section 2](problem-formulation-issue109-v1.md), [Issue #109 outline](strategy-uncertainty-issue109.md), [accepted D-007](../../docs/DECISIONS.md), [frozen #99 resources](../../experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json), [#103 Draft PR #104](https://github.com/1951123/ess-research/pull/104), and the [conditional matching proof](../../notes/pg-mcv-maximal-matching-correspondence.md).
- **Scientific positioning:** Model and assumptions are the leading contribution. PG16.14 serves as restricted later evidence; uniform global priorities and real OID assignment are not equated. No solver novelty, global optimality, runtime benefit, physical worst-case coverage, or universal PESS advantage claimed.
