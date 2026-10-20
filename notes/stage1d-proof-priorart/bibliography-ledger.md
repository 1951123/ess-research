# Stage 1D bibliography and query ledger

**Search cutoff:** 2026-10-20 (Asia/Shanghai).  
**Protocol:** the frozen queries in
[`claims-manifest-v1.md`](claims-manifest-v1.md) were executed after the
manifest commit. DOI/publisher pages, author manuscripts, proceedings pages,
and repository copies were preferred. Search snippets were used only to find
sources, not as evidence. “Abstract/full text” below records what was actually
reachable during this audit; it is not a claim that the source was exhaustively
reviewed.

## Query log

| Bucket | Executed query family | Primary-source result links used |
|---|---|---|
| Maximal matching / edge domination | `minimum weight maximal matching series-parallel graphs`; `minimum weighted maximal matching exact algorithms edge domination`; `maximal matching polytope trees`; `decomposition algorithms minimum weight maximal matching` | [Richey–Parker DOI](https://doi.org/10.1016/0377-2217(88)90258-5), [van Rooij–Bodlaender DOI](https://doi.org/10.1007/s00453-011-9546-x), [Bodur–Ekim–Taşkın DOI](https://doi.org/10.1002/net.21516), [Tural tree-polytope DOI](https://doi.org/10.1080/10556788.2015.1104679), [Tural valid-inequalities DOI](https://doi.org/10.37094/adyujsci.540858) |
| Tree/incidence DP and feedback sets | `dynamic programming bounded treewidth weighted CSP factor graph budget`; `ground-set-cost budgeted maximum coverage forest`; `bounded treewidth extended formulation`; `tree factor graph marginal polytope` | [Kolman–Koutecký EJC](https://www.combinatorics.org/ojs/index.php/eljc/article/view/v22i4p30), [van Heuven van Staereling et al. final DOI](https://doi.org/10.1007/s00224-025-10248-5), [MFCS open proceedings](https://doi.org/10.4230/LIPIcs.MFCS.2016.50), [Wainwright–Jordan DOI](https://doi.org/10.1561/2200000001) |
| Order-statistics / disjunctive epigraphs | `convex hull maximum selected value`; `epigraph max selected item`; `disjunctive programming ordered formulation`; `embedding formulation order statistics` | [Balas](https://doi.org/10.1137/0606047), [Vielma](https://doi.org/10.1137/130915303), [Vielma author PDF](https://juan-pablo-vielma.github.io/publications/Mixed-Integer-Linear-Programming-Formulation-Techniques.pdf) |
| SUBSET SUM / profiles / approximation | `subset sum scaling FPTAS`; `approximate Pareto curve`; `multiobjective dynamic programming label dominance`; `resource constrained shortest path dominance` | [Ibarra–Kim DOI](https://doi.org/10.1145/321906.321909), [Kellerer–Mansini–Pferschy–Speranza DOI](https://doi.org/10.1016/S0022-0000(03)00006-0), [Koiliaris–Xu arXiv](https://arxiv.org/abs/1807.08248), [Papadimitriou–Yannakakis DOI](https://doi.org/10.1109/SFCS.2000.892068), [Righini–Salani DOI](https://doi.org/10.1016/j.endm.2004.03.047) |
| Decision-dependent robust optimization | `decision dependent uncertainty robust optimization`; `branch and cut mixed integer decision dependent robust optimization`; `double oracle logic based Benders K-adaptability`; `robust optimization stability perturbation` | [Nohadani–Sharma DOI](https://doi.org/10.1137/17M1110560), [Lefebvre et al. preprint page](https://optimization-online.org/2026/03/branch-and-cut-for-mixed-integer-linear-decision-dependent-robust-optimization/), [Lefebvre et al. PDF](https://optimization-online.org/wp-content/uploads/2026/03/bnc-for-dec-dep-robust-opt.pdf), [Ghahtarani et al. DOI](https://doi.org/10.1016/j.cor.2023.106243), [robust stability DOI](https://doi.org/10.1137/16M1067512) |

## Source records and exact comparison

### Maximal matching / edge domination

1. **M. B. Richey and R. G. Parker, “Minimum-maximal matching in
   series-parallel graphs,” European Journal of Operational Research (1988),
   DOI 10.1016/0377-2217(88)90258-5.** The publisher record states the fixed
   graph problem of finding a minimum-weight matching that is maximal, on a
   series-parallel graph. Abstract/publisher record was reachable; full paper
   was not relied on for page-level claims. It directly covers fixed-selected
   graph weighted maximal matching, not PESS outer resource selection or task
   sharing.

2. **J. M. M. van Rooij and H. L. Bodlaender, “Exact Algorithms for Edge
   Domination,” Algorithmica 64 (2012), DOI 10.1007/s00453-011-9546-x.** The
   publisher record states exact exponential algorithms for edge domination and
   related minimum-weight maximal matching. This is a general-graph fixed
   inner-problem baseline, not a proof about the selected-graph outer problem.

3. **M. Bodur, T. Ekim and Z. C. Taşkın, “Decomposition algorithms for
   solving the minimum weight maximal matching problem,” Networks (2013),
   DOI 10.1002/net.21516.** The publisher abstract describes integer
   programming formulations and a decomposition method combining IP and
   combinatorial matching algorithms. A proposed PESS inner-oracle
   decomposition therefore requires a non-equivalence argument; “oracle” or
   “decomposition” alone is not a novelty claim.

4. **M. K. Tural, “Maximal matching polytope in trees,” Optimization Methods
   and Software 31 (2016), DOI 10.1080/10556788.2015.1104679.** The author/repository
   record states that the LP relaxation of a known formulation describes the
   maximal-matching polytope for trees. This is relevant to any tree/path
   formulation but does not include the PESS outer shared-resource coupling.

5. **M. K. Tural, “Valid Inequalities for the Maximal Matching Polytope,”
   Adıyaman University Journal of Science (2019), DOI 10.37094/adyujsci.540858.**
   The journal page and accessible PDF describe valid inequalities for the
   maximal-matching polytope. Candidate PESS cuts must be compared against
   these polyhedral results; no equivalence to the task-sharing model was
   established here.

### Tree/incidence DP and factor structure

6. **P. Kolman and M. Koutecký, “Extended Formulation for CSP that is Compact
   for Instances of Bounded Treewidth,” Electronic Journal of Combinatorics
   22 (2015), DOI 10.37236/5474.** The open journal record states compact
   extended formulations for bounded-treewidth CSP instances. It supports the
   general classical status of tree-decomposition formulations; it does not
   instantiate the PESS signed max-of-maximal-matchings factor.

7. **I. van Heuven van Staereling, J. de Keijzer and M. Schäfer, “The
   Ground-Set-Cost Budgeted Maximum Coverage Problem,” Theory of Computing
   Systems (2025), DOI 10.1007/s00224-025-10248-5.** The publisher record
   states a pseudo-polynomial algorithm and an FPTAS for the forest-incidence
   case, plus a fixed-size feedback hyperedge-node extension. The earlier open
   MFCS version is [here](https://doi.org/10.4230/LIPIcs.MFCS.2016.50). The
   source is adjacent rather than equivalent: it has coverage-style
   nonnegative factors, while general PESS has signed affine losses, maximal
   matching admissibility and a shared global budget.

8. **M. J. Wainwright and M. I. Jordan, “Graphical Models, Exponential
   Families, and Variational Inference,” Foundations and Trends in Machine
   Learning (2008), DOI 10.1561/2200000001.** The author PDF/book record covers
   exact local-to-global marginal descriptions on trees. It supports the
   tree-factor-gluing comparison in Issue #29, but does not imply integrality
   after adding a cyclic factor graph or an active global budget.

### Order statistics and disjunctive formulations

9. **E. Balas, “Disjunctive Programming and a Hierarchy of Relaxations for
   Discrete Optimization Problems,” SIAM Journal on Matrix Analysis and
   Applications (1985), DOI 10.1137/0606047.** The publisher record describes
   convex-hull formulations for unions/disjunctions. The local highest-index
   star epigraph is a small special case of this established paradigm.

10. **J. P. Vielma, “Mixed Integer Linear Programming Formulation
    Techniques,” SIAM Review 57(1) (2015), DOI 10.1137/130915303.** The open
    author manuscript and publisher record survey standard logical, convex-hull
    and embedding formulation techniques. It is directly relevant to the
    lambda-chain mechanism, but not specific to PESS.

### SUBSET SUM, Pareto labels and rounding

11. **O. H. Ibarra and C. E. Kim, “Fast Approximation Algorithms for the
    Knapsack and Sum of Subset Problems,” JACM 22(4) (1975), pp. 463–468,
    DOI 10.1145/321906.321909.** The bibliographic record and accessible copy
    identify the classic scaling-based approximation results. It establishes
    prior art for scale-based approximation of subset-sum-like numeric
    objectives, not the PESS path transfer bound.

12. **H. Kellerer, R. Mansini, U. Pferschy and M. G. Speranza, “An efficient
    fully polynomial approximation scheme for the Subset-Sum Problem,” Journal
    of Computer and System Sciences (2003), DOI 10.1016/S0022-0000(03)00006-0.**
    The publisher record states an FPTAS for Subset Sum. Its guarantee is for a
    different objective and must not be relabeled as a multiplicative PESS
    guarantee.

13. **K. Koiliaris and C. Xu, “Subset Sum Made Simple,” arXiv:1807.08248
    (2018), later published in ACM Transactions on Algorithms.** The author
    preprint and ACM record cover faster pseudo-polynomial subset-sum methods.
    This is a baseline for the reduction's numeric boundary, not evidence that
    the PESS profile state space is small.

14. **C. H. Papadimitriou and M. Yannakakis, “On the Approximability of
    Trade-offs and Optimal Access of Web Sources,” FOCS (2000), DOI
    10.1109/SFCS.2000.892068.** The IEEE record states conditions for
    polynomially constructible approximate Pareto curves. This supports the
    classification of profile/label compression and approximate Pareto ideas
    as established methodology; it does not prove a PESS-specific scheme.

15. **G. Righini and M. Salani, “Dynamic programming algorithms for the
    elementary shortest path problem with resource constraints,” 2004, DOI
    10.1016/j.endm.2004.03.047.** The publisher/author record describes label
    setting and dominance criteria in resource-constrained DP. It is an
    analogous prior-art bucket for profile dominance, not an exact PESS
    equivalence.

### Decision-dependent robust optimization and perturbation

16. **O. Nohadani and K. Sharma, “Optimization under Decision-Dependent
    Uncertainty,” SIAM Journal on Optimization 28(2), 1773–1795 (2018), DOI
    10.1137/17M1110560.** The publisher page and author preprint establish the
    broader DDRO setting. It makes decision-dependent uncertainty a classical
    framework; it does not identify the maximal-matching PESS family or the
    specific matching-weight perturbation bound.

17. **H. Lefebvre, M. Schmidt, S. Stevens and J. Thürauf, “Branch-and-Cut for
    Mixed-Integer Linear Decision-Dependent Robust Optimization,” 2026
    preprint, [landing page](https://optimization-online.org/2026/03/branch-and-cut-for-mixed-integer-linear-decision-dependent-robust-optimization/),
    [PDF](https://optimization-online.org/wp-content/uploads/2026/03/bnc-for-dec-dep-robust-opt.pdf).** The accessible abstract/PDF describes a
    tailored branch-and-cut method for mixed-integer DDRO and distinguishes
    general intersection cuts from special interdiction cuts for downward-
    monotone uncertainty. PESS maximal-matchings are not generally downward
    closed, so the special cuts cannot be transferred without a proof.

18. **A. Ghahtarani, A. Saif, A. Ghasemi and E. Delage, “A double-oracle,
    logic-based Benders decomposition approach to solve the K-adaptability
    problem,” Computers & Operations Research (2023), DOI
    10.1016/j.cor.2023.106243.** The publisher record describes adversarial
    scenario generation for K-adaptability. It is adjacent decomposition
    prior art with a different min–max–min recourse model, not an exact PESS
    formulation.

19. **“Stability and Continuity in Robust Optimization,” SIAM Journal on
    Optimization, DOI 10.1137/16M1067512.** The publisher search record
    identifies Lipschitz continuity results for robust optimal values under
    uncertainty-set perturbation. The PESS matching-aware transfer is derived
    directly from the reverse triangle inequality and an ordinary matching
    upper bound; it should therefore be described as a model-specific
    correctness lemma, not as a new general robust-optimization theorem.

## Coverage gaps and priority limits

- Several publisher pages expose abstracts/metadata but not the complete
  article text in this environment. No page numbers, theorem numbers, or
  priority claims are asserted from inaccessible full text.
- The search is targeted, not an exhaustive systematic literature review.
  The audit can support “classical/special case” and “not established”
  classifications, but cannot certify absence of an unpublished or obscure
  PESS-specific result.
- No source located in this pass was shown to prove the exact combined model
  (unordered outer resource set, task-wise independent maximal-matching
  adversaries, signed absolute-affine loss, shared budget and nonadditive
  maintenance). This non-finding is not a novelty claim.
