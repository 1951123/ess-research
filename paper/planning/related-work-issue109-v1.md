# Section 8 — Related Work (Issue #109, v1)

**Status:** independently reviewable English draft, modeling-first and source-verified at the level of titles, authors, publication records and relevant abstracts/documentation. **Not yet a complete systematic literature review** and not yet integrated into `paper/main.tex` or BibTeX. Avoid claims of priority or novelty against unsearched papers. This branch does not modify experimental evidence.

## 8. Related Work

### 8.1 Cardinality-estimation accuracy and multiattribute statistics

Cardinality estimation influences cost-based query optimization, and errors can substantially affect plan decisions. Leis et al. systematically separated cardinality estimation, cost modeling and plan enumeration in *How Good Are Query Optimizers, Really?* (PVLDB 9(3), 2015). Their findings motivate accurate estimation but do not directly study the distinction between choosing an installed statistics set and choosing which overlapping installed statistics are applied to a single estimation task. Subsequent work evaluating cardinality estimators in actual DBMS settings also cautions against equating estimation Q-error with end-to-end plan quality. In particular, the *Cardinality Estimation in DBMS: A Comprehensive Benchmark Evaluation* study discusses limitations of Q-error as a proxy for plan performance. Our evaluation accordingly treats held-out `Plan Rows` Q-error as estimation evidence, not a measured query-latency gain.

Database systems use multiattribute summaries to address correlations that single-column information can miss. PostgreSQL 16 documentation describes extended-statistics objects and distinguishes functional dependencies, multivariate ndistinct and multivariate most-common-value (MCV) lists. Creating an extended-statistics object requests subsequent collection during `ANALYZE`; collection and refresh have associated cost. Our pairwise-MCV instantiation concerns one restricted use of these resources, not the complete set of PostgreSQL multivariate estimation paths or a replacement cardinality estimator.

### 8.2 Statistics selection and database physical-design advisors

There is substantial earlier work on choosing useful statistics and physical structures under resource limits. Chaudhuri and Narasayya's *Automating Statistics Management for Query Optimizers* focuses explicitly on identifying essential optimizer statistics and reducing the set that must be maintained. Bruno and Chaudhuri's *Exploiting Statistics on Query Expressions for Optimization* (SIGMOD 2002) studies expression-level statistics and workload-driven selection. Their later *Automatic Physical Database Tuning: A Relaxation-based Approach* (SIGMOD 2005) analyzes the architecture of broader automated physical-design selection. These works establish that selecting a workload-relevant subset of statistics or physical structures, with maintenance or storage constraints, is not itself new.

Our distinction lies in the **information model attached to a selected resource set**. We explicitly separate an unordered installed set \(M\), complete admissible task-estimation schemes \(\Gamma_i(M)\), and the shared application policy that induces a particular scheme for each task. This separation matters when resources overlap and the advisor cannot safely assume a specified scheme-selection rule. We do not claim that prior advisors always apply all installed statistics independently, nor that none anticipates system-dependent statistics use. A direct algorithmic novelty comparison will require reading the primary full texts and checking whether specific advisors account for scheme conflicts or uncertainty rather than merely resource maintenance. Our frozen strictly improving add-only greedy routine is a common heuristic design choice, **not** a newly proved global optimization algorithm.

### 8.3 Robust decision making and uncertain strategies

Our Nominal and task-wise PESS objectives reflect different assumptions about the estimator's strategy. A fixed known priority yields a nominal scheme for each task. A shared uncertain global priority couples scheme choices across tasks; worst-case aggregate risk over this policy family is \(G(M)\). In contrast, the prescribed task-wise pessimistic objective \(P(M)\) maximizes separately over each task's admissible scheme family and may exceed any single shared-policy worst case. These are formal variants of decision making under different uncertainty sets, but **we do not assert a new general theory of robust optimization**, nor imply that other robust database approaches omit such distinctions without literature verification.

For the restricted labeled-edge instance, a total priority greedily induces an inclusion-maximal matching, and each task-local maximal matching is achievable under some freely chosen abstract order. A single *shared* global order need not realize the independently worst matching for every task. Uniform priority permutations weight matchings by order multiplicity and are not the same as uniform matching choices. This mechanism-specific coupling is the point of the present analysis; it is not a claim that PostgreSQL randomly draws OIDs or implements a taskwise adversary.

### 8.4 Positioning relative to benchmarking and the source-derived systems mechanism

The original AreCEL evaluation, *Are We Ready for Learned Cardinality Estimation?* (Wang et al., 2021), provides the four-workload family from which we retain official frozen Train/Test splits. Our evaluation does **not** reproduce that paper's learned estimator; it applies a PostgreSQL 16.14 two-column MCV resource-selection study under a different statistics target and pinned planner settings. Earlier benchmark results therefore cannot be directly equated to the physical `Plan Rows` results reported here.

In the present paper, the PostgreSQL 16.14 MCV selector provides **scoped evidence for practical relevance**, not the origin of the mathematical problem. We use a version-pinned conditional correspondence between its restricted clause-consumption loop and labeled inclusion-maximal matching, then separately evaluate fixed-resource counterfactual priority changes. This is evidence about how an estimator applies existing resources, distinct from inventing a new estimator, a new sampling algorithm, or a new execution-plan optimizer. The observed dataset-dependent outcomes do not show universal superiority of PESS or any real-world probability distribution over object OIDs.

### 8.5 Synthesis

The paper connects three established concerns—accurate cardinality estimates, budgeted statistics maintenance, and uncertain decisions—to a precise missing interface between **resource availability** and **resource application**. Its contribution is to define and analyze that interface, distinguish the loss functionals induced by policy knowledge, and establish one source-grounded restricted DBMS mechanism plus carefully scoped empirical evidence. Stronger claims about earliest precedence in this literature, algorithmic dominance or physical risk bounds are outside the verified evidence.

---

## Citation verification ledger — editorial notes, not manuscript prose

**Verified primary sources/records (do not fabricate final BibTeX keys):**

1. Viktor Leis et al., *How Good Are Query Optimizers, Really?*, PVLDB 9(3):204–215 (2015), DOI 10.14778/2850583.2850594. Institutional record: https://ir.cwi.nl/pub/24379 ; original paper: https://vldb.org/pvldb/vol9/p204-leis.pdf.
2. *Cardinality Estimation in DBMS: A Comprehensive Benchmark Evaluation*, PVLDB 15(4):752–765, DOI 10.14778/3503585.3503586. Primary proceedings: https://doi.org/10.14778/3503585.3503586. **Check the publication author metadata before generating BibTeX.**
3. PostgreSQL 16 documentation, *Statistics Used by the Planner*, especially §14.2.2: https://www.postgresql.org/docs/16/planner-stats.html. Documentation, **not** peer-reviewed article.
4. Surajit Chaudhuri and Vivek Narasayya, *Automating Statistics Management for Query Optimizers*, author-hosted paper: https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/stats.pdf . **Verify venue/year against publication record before final BibTeX.**
5. Nicolas Bruno and Surajit Chaudhuri, *Exploiting Statistics on Query Expressions for Optimization*, SIGMOD 2002, DOI 10.1145/564691.564722: https://doi.org/10.1145/564691.564722.
6. Nicolas Bruno and Surajit Chaudhuri, *Automatic Physical Database Tuning: A Relaxation-based Approach*, SIGMOD 2005, pp. 227–238, DOI 10.1145/1066157.1066184: https://www.microsoft.com/en-us/research/publication/automatic-physical-database-tuning-a-relaxation-based-approach/ .
7. Xiaoying Wang et al., *Are We Ready for Learned Cardinality Estimation?* (2021), original associated benchmark repository: https://github.com/sfu-db/AreCELearnedYet ; preprint: https://liuyehcf.github.io/resources/paper/Are-We-Ready-For-Learned-Cardinality-Estimation.pdf. **Verify complete authors, venue, pages, DOI before bibliography insertion.**

**Needed before submission:** independently inspect more relevant statistics-selection, physical design under uncertainty and robust query-optimization literature, including direct full-text comparison and qualified originality analysis. The sources above are an initial **verified seed list**, not a systematic negative novelty search; avoid claiming no earlier work explicitly considers estimator-policy uncertainty.

**Internal provenance:** [general problem](problem-formulation-issue109-v1.md), [objective bounds](optimization-objectives-issue109-v1.md), [PG mechanism](postgresql-mcv-mechanism-issue109-v1.md), [experimental protocol](experimental-protocol-issue109-v1.md), [results](experimental-results-issue109-v1.md), and [validity Draft PR #119](https://github.com/1951123/ess-research/pull/119).
