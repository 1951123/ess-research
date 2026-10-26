# Section 2 draft — Problem Formulation (Issue #109)

**Status:** standalone English prose for review, not yet integrated into the existing `paper/main.tex` formulation. Based on the merged [paper argument outline](strategy-uncertainty-issue109.md) and deliberately compatible with [the existing formal formulation](../main.tex). Section 3 will introduce Nominal, shared-global-order and PESS objectives and the selection heuristic; this section defines the generic interface and structured matching instance.

## 2. Problem Formulation

### 2.1 Cardinality-estimation tasks and resource decisions

We consider a finite collection \(\mathcal I\) of cardinality-estimation tasks. A task \(i\in\mathcal I\) identifies a relational cardinality target together with the estimation context in which it is computed. It may refer to a selection, join, logical intermediate expression, or another explicitly specified estimation target; it need not correspond to an entire SQL query or a particular physical-plan node. We denote its true cardinality by \(N_i\geq0\), use the strictly positive reference \(T_i=\max\{1,N_i\}\), and associate with it a workload weight \(w_i>0\).

Let \(\mathcal E\) be a finite universe of candidate estimation resources. The advisor's decision is one **unordered** subset \(M\subseteq\mathcal E\), globally installed for the entire task collection. The decision does not specify the order in which resources are created or the subset eventually consumed by the estimator on any given task.

A maintenance-accounting rule \(\operatorname{Maint}:2^{\mathcal E}\to\mathbb R_{\geq0}\), normalized by \(\operatorname{Maint}(\varnothing)=0\), and a budget \(B\geq0\) define the feasible resource sets
\[
\mathcal F_B=\{M\subseteq\mathcal E:\operatorname{Maint}(M)\leq B\}.
\]
We fix all external conditions on which maintenance may depend, such as the database state, update workload, and refresh horizon. At the generic level, \(\operatorname{Maint}\) is **not** assumed additive, monotone, submodular, or expressible using per-resource coefficients. An additive experimental budget is introduced only for the specialized pairwise-MCV instance.

### 2.2 Complete estimation schemes and admissibility

A resource available to the estimator is not necessarily a resource it applies. To make this separation precise, each task \(i\) has a finite scheme universe \(\Omega_i\). A **complete estimation scheme** \(\sigma\in\Omega_i\) contains enough task-specific information to determine one estimate, potentially including which resources are used, which predicates they cover, and estimator-specific choices or composition rules. We write \(\operatorname{used}(\sigma)\subseteq\mathcal E\) for its required resources. A scheme is neither, in general, simply a resource subset nor a physical execution plan.

The advisor specifies a nonempty family of schemes admissible under each installed set:
\[
\Gamma_i:2^{\mathcal E}\longrightarrow 2^{\Omega_i}\setminus\{\varnothing\},
\qquad
\sigma\in\Gamma_i(M)\Longrightarrow\operatorname{used}(\sigma)\subseteq M.
\]
At \(M=\varnothing\), a baseline scheme is admissible. We **do not assume** that \(\Gamma_i(M_1)\subseteq\Gamma_i(M_2)\) whenever \(M_1\subseteq M_2\). The admissibility rule describes *complete* allowed application outcomes and may require the estimator to consume an eligible object once it has been installed. Consequently, adding a resource can remove previously complete schemes from the admissible family or add other, worse schemes. This non-nesting is one source of nonmonotone selection objectives.

**Admissibility is a model, not an automatically proven physical coverage guarantee.** Let \(\mathcal R_i(M)\) denote the schemes a particular deployed estimator can actually produce. Neither \(\mathcal R_i(M)=\Gamma_i(M)\) nor \(\mathcal R_i(M)\subseteq\Gamma_i(M)\) follows from the definitions. Any statement that the prescribed worst-case loss upper-bounds *physical* losses must separately justify containment and alignment of estimation and loss semantics.

### 2.3 Estimates, losses, and policies

A task-specific estimator maps a complete scheme to a positive, pre-output-transformation estimate:
\[
\operatorname{Est}_i:\Omega_i\longrightarrow \mathbb R_{>0}.
\]
The abstract interface does not require a multiplicative factorization, independence among attributes, or the exact rounding/clamping behavior of any DBMS. Let \(\ell_i:\Omega_i\to\mathbb R_{\geq0}\) be its nonnegative scheme loss; our principal illustration uses
\[
\ell_i(\sigma)=\left|\log\frac{\operatorname{Est}_i(\sigma)}{T_i}\right|.
\]
The task's weighted loss is \(L_i(\sigma)=w_i\ell_i(\sigma)\).

An **application strategy** (or **policy**) is a rule that, when supplied with a fixed installed set and an estimation task, chooses one complete scheme. To represent a family of policies possibly coupled across tasks, write \(\Theta\) for a set of global policy parameters and \(\sigma_i(M;\theta)\) for the scheme induced for task \(i\) by \(\theta\in\Theta\). An admissibility-compatible policy satisfies
\[
\sigma_i(M;\theta)\in\Gamma_i(M)
\quad\text{for all relevant }i,M,\theta.
\]
The parameter may encode a deterministic priority, without implying that any physical DBMS draws it randomly. The same \(\theta\) can influence multiple tasks, coupling their scheme choices. This coupling distinguishes a shared-policy worst case from task-wise independent worst cases.

For a **fixed feasible resource set** \(M\) and a compatible policy family, define
\[
F_\theta(M)=\sum_{i\in\mathcal I}L_i(\sigma_i(M;\theta)),
\quad
F_{\mathrm{joint}}(M)=\max_{\theta\in\Theta}F_\theta(M),
\quad
F_{\mathrm{pess}}(M)=\sum_{i\in\mathcal I}\max_{\sigma\in\Gamma_i(M)}L_i(\sigma).
\]
Then
\[
F_{\mathrm{joint}}(M)\leq F_{\mathrm{pess}}(M).
\]
Indeed, for every common \(\theta\), each task's induced loss is no larger than that task's maximum admissible loss; sum these inequalities and maximize over \(\theta\). The bound is **model-internal** and applies to the *same* \(M\). It does not rank sets selected by different objectives, prove a global optimum for either selection procedure, or guarantee physical PostgreSQL Q-error. For an explicitly specified probability distribution over compatible shared policies, expected aggregate loss is also bounded above by \(F_{\mathrm{joint}}(M)\). In Section 3 we specialize \(\Theta\) to global resource-priority permutations and distinguish fixed-priority Nominal, expected-priority, shared-global worst-case and task-wise PESS objectives.

### 2.4 Pairwise MCV statistics as a structured admissibility model

The general interface admits arbitrary complete schemes. Our structured example instead studies restricted single-relation conjunctions with **two-column multivariate most-common-value (MCV)** statistics. Let each labeled candidate object \(e\in\mathcal E\) cover exactly two attributes \(A_e\), \(|A_e|=2\). For task \(i\), let \(\mathcal E_i\subseteq\mathcal E\) be the candidates *statically eligible* for its compatible predicates. The eligible candidates form a labeled multigraph \(H_i=(V_i,\mathcal E_i)\). Distinct statistics are distinct edges even if their covered attribute pair is the same.

Under an installed set \(M\), define the available eligible subgraph \(H_i[M]=(V_i,M\cap\mathcal E_i)\). Each matching is a collection of edges sharing no endpoints; a matching is **inclusion-maximal** when no additional available eligible edge can be added without a conflict. Our prescribed complete schemes are
\[
\Gamma_i^{\mathrm{MM}}(M)=\operatorname{MaximalMatchings}(H_i[M]).
\]
The empty matching is the unique scheme when the graph has no available edges. Every finite graph has at least one maximal matching, so admissibility is nonempty. A maximal matching need not have maximum cardinality. Importantly, this family is not generally nested as \(M\) grows: a matching previously maximal may cease to be maximal after adding a nonconflicting eligible edge.

Consider the path whose available labeled edges are \(s_{AB},s_{BC},s_{CD}\). Its admissible maximal matchings are exactly \(\{s_{AB},s_{CD}\}\) and \(\{s_{BC}\}\). A greedy selector that scans one total priority order and takes an edge whenever both endpoints remain unused produces a maximal matching. Conversely, for an *isolated task graph*, each maximal matching can be induced by putting its edges before the others in a freely chosen abstract total order. This converse does **not** imply that any one shared global order realizes independently chosen worst matchings across multiple tasks, or that any order is realizable in a fixed PostgreSQL catalog. A global priority induces one correlated scheme per task.

This matching formulation is a **research abstraction with restricted PostgreSQL 16.14 source-level and fixture-level support**, not a representation of arbitrary SQL conditions, joins, other extended-statistics kinds, or every numeric cardinality-estimation path. The precise source prerequisites and observed OID-tie behavior are addressed in the systems-mechanism section rather than silently assumed here.

### 2.5 Positive pre-clamp estimates and the controlled budget instance

For the structured model only, let \(n_i^0>0\) be a positive baseline pre-clamp estimate and \(r_{e,i}>0\) a task-and-resource-specific correction factor fixed in advance for each eligible edge. For a matching \(P\in\Gamma_i^{\mathrm{MM}}(M)\), assume the explicitly separable approximation
\[
\widehat n_i(P)=n_i^0\prod_{e\in P}r_{e,i}.
\]
Writing \(\alpha_i=\log(n_i^0/T_i)\) and \(b_{e,i}=\log r_{e,i}\), the raw weighted error is
\[
L_i(P)=w_i\left|\alpha_i+\sum_{e\in P}b_{e,i}\right|.
\]
These are modeling assumptions, not claims that PostgreSQL's actual MCV composition always factorizes this way. Positivity is required before taking logarithms. The subsequent rounded/clamped PostgreSQL `Plan Rows` and the benchmark's zero-aware held-out Q-error are **different measurements**, not interchangeable forms of this raw loss.

The frozen selection study uses a nonnegative per-object **proxy** \(\bar m_e\) and the specialized capacity constraint
\[
\sum_{e\in M}\bar m_e\leq B.
\]
This additive proxy is a *restricted experimental choice* and must not be substituted for the generic function \(\operatorname{Maint}(M)\), nor described as measured physical refresh CPU time. Resource-selection objectives are defined in Section 3; in the frozen study, the same strictly improving, add-only greedy heuristic is applied separately to Nominal and PESS using *Train-only* inputs. Physical Test data play no role in determining selected resources.

### 2.6 Scope of the formulation

The contributions of this model are the separation of installed resources from complete admissible schemes, an explicit interface for policy knowledge, and an analyzable pairwise overlapping-resource instance. The formulation permits conservatism but does not automatically guarantee good physical estimates. Its validity depends on the prescribed admissibility families, estimates, loss definition, and maintenance proxy. In particular, a worst-case training-model loss must not be interpreted as a bound on unseen query error, and a conditional matching correspondence must not be represented as all-purpose PostgreSQL semantics.

---

## Editorial review notes (not paper prose)

1. **Consistency against the existing formal draft:** Generic \(\operatorname{Maint}\) remains abstract and nonadditive; each \(\Omega_i\) contains complete schemes; \(\Gamma_i(M)\) is nonempty and need not be nested; \(\operatorname{Est}_i\) is positive; log loss is pre-clamp. Avoid migrating this draft over `paper/main.tex` until review of any duplication and existing maintenance/sample-control caveats.
2. **Four concepts to lock:** resource set \(M\) (advisor decision), \(\sigma\) (complete estimation scheme), \(\Gamma_i(M)\) (prescribed compatibility/admissibility family), \(\theta\) (one globally shared parameter inducing correlated scheme choices). The physical policy family's coverage by \(\Gamma\) is an additional condition, not a definition.
3. **Model-internal check:** For every globally compatible \(\theta\), \(F_\theta(M)\leq F_{\rm pess}(M)\) at the same fixed \(M\). No real-system coverage without \(\mathcal R_i(M)\subseteq\Gamma_i(M)\), and no ranking of independently selected \(M\)'s.
4. **Scope boundary:** The pairwise-MCV graph is only a restricted instantiation; maximal is not maximum; global orders need not simultaneously attain each taskwise maximum; \(\bar m_e\) is a controlled proxy, not runtime maintenance cost. All source claims should cite the pinned [correspondence note](../../notes/pg-mcv-maximal-matching-correspondence.md) and [PG16.14 source](https://github.com/postgres/postgres/blob/REL_16_14/src/backend/statistics/extended_stats.c).
5. **Open editorial choices:** Decide whether this paper should first present only abstract PESS and move all alternative objectives into Section 3, and whether the existing `paper/main.tex` should eventually be transformed into the full multi-section manuscript. The current draft deliberately does neither without review.
