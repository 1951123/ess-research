"""Bounded exact checks for the Issue #41 theory audit.

This is a stdlib-only diagnostic, not a solver benchmark and not a proof.
All arithmetic in the checks is Fraction arithmetic.  The mathematical
arguments and the literature classifications live in the accompanying notes.
"""

from __future__ import annotations

from fractions import Fraction
from itertools import combinations, product
from typing import Iterable, Sequence


Edge = tuple[int, int]


def matching_masks(edges: Sequence[Edge]) -> list[int]:
    """Enumerate labeled ordinary matchings, including the empty matching."""
    out: list[int] = []
    for mask in range(1 << len(edges)):
        used: set[int] = set()
        valid = True
        for j, (u, v) in enumerate(edges):
            if mask & (1 << j):
                if u in used or v in used:
                    valid = False
                    break
                used.update((u, v))
        if valid:
            out.append(mask)
    return out


def maximal_matching_masks(edges: Sequence[Edge]) -> list[int]:
    """Enumerate labeled maximal matchings of the supplied selected graph."""
    out: list[int] = []
    for mask in matching_masks(edges):
        saturated: set[int] = set()
        for j, (u, v) in enumerate(edges):
            if mask & (1 << j):
                saturated.update((u, v))
        if all(
            (mask & (1 << j)) or u in saturated or v in saturated
            for j, (u, v) in enumerate(edges)
        ):
            out.append(mask)
    return out


def matching_sum(mask: int, values: Sequence[Fraction]) -> Fraction:
    return sum((value for j, value in enumerate(values) if mask & (1 << j)), Fraction(0))


def task_worst(
    all_edges: Sequence[Edge], selected: int, alpha: Fraction, b: Sequence[Fraction]
) -> Fraction:
    selected_edges = [edge for j, edge in enumerate(all_edges) if selected & (1 << j)]
    selected_b = [value for j, value in enumerate(b) if selected & (1 << j)]
    worst = Fraction(0)
    for mask in maximal_matching_masks(selected_edges):
        worst = max(worst, abs(alpha + matching_sum(mask, selected_b)))
    return worst


def exact_square_solve(matrix: list[list[Fraction]], rhs: list[Fraction]) -> list[Fraction] | None:
    """Solve a square system exactly, returning None for singular systems."""
    n = len(rhs)
    aug = [row[:] + [value] for row, value in zip(matrix, rhs)]
    pivot_row = 0
    for col in range(n):
        pivot = next((r for r in range(pivot_row, n) if aug[r][col]), None)
        if pivot is None:
            continue
        aug[pivot_row], aug[pivot] = aug[pivot], aug[pivot_row]
        divisor = aug[pivot_row][col]
        aug[pivot_row] = [value / divisor for value in aug[pivot_row]]
        for r in range(n):
            if r == pivot_row or not aug[r][col]:
                continue
            factor = aug[r][col]
            aug[r] = [a - factor * b for a, b in zip(aug[r], aug[pivot_row])]
        pivot_row += 1
    if pivot_row != n:
        return None
    return [aug[r][-1] for r in range(n)]


def feasible(point: Sequence[Fraction], inequalities: Sequence[tuple[list[Fraction], Fraction]]) -> bool:
    return all(sum(a * x for a, x in zip(row, point)) <= rhs for row, rhs in inequalities)


def lp_vertex_min(
    objective: Sequence[Fraction],
    equalities: Sequence[tuple[list[Fraction], Fraction]],
    inequalities: Sequence[tuple[list[Fraction], Fraction]],
) -> Fraction:
    """Tiny exact LP solver by vertex enumeration; intended for m <= 4 only."""
    dimension = len(objective)
    needed = dimension - len(equalities)
    best: Fraction | None = None
    for active in combinations(inequalities, needed):
        rows = [row for row, _ in equalities] + [row for row, _ in active]
        rhs = [rhs for _, rhs in equalities] + [rhs for _, rhs in active]
        if len(rows) != dimension:
            continue
        point = exact_square_solve(rows, rhs)
        if point is None or not feasible(point, inequalities):
            continue
        value = sum(c * x for c, x in zip(objective, point))
        if best is None or value < best:
            best = value
    if best is None:
        raise AssertionError("tiny LP had no feasible vertex")
    return best


def star_epigraph_lp(v0: Fraction, values: Sequence[Fraction], x: Sequence[Fraction]) -> Fraction:
    """Minimum z in the STAR-HI lambda chain, checked exactly."""
    m = len(values)
    q = m + 1
    inequalities: list[tuple[list[Fraction], Fraction]] = []
    row = [Fraction(0)] * q
    row[0] = -1
    inequalities.append((row, Fraction(0)))  # lambda_0 >= 0
    for j in range(1, q):
        row = [Fraction(0)] * q
        row[j] = -1
        inequalities.append((row, Fraction(0)))  # lambda_j >= 0
        row = [Fraction(0)] * q
        row[j] = 1
        inequalities.append((row, x[j - 1]))  # lambda_j <= x_j
        row = [Fraction(0)] * q
        for k in range(j, q):
            row[k] = -1
        inequalities.append((row, -x[j - 1]))  # x_j <= sum_{k>=j} lambda_k
    objective = [v0, *values]
    equality = [([Fraction(1)] * q, Fraction(1))]
    return lp_vertex_min(objective, equality, inequalities)


def binary_epigraph_lp(values: Sequence[Fraction], v0: Fraction, x: Sequence[Fraction]) -> Fraction:
    """Exact convex-hull lower envelope from distributions over binary subsets."""
    m = len(values)
    subsets = list(range(1 << m))
    rows: list[list[Fraction]] = []
    rhs: list[Fraction] = []
    rows.append([Fraction(1)] * len(subsets))
    rhs.append(Fraction(1))
    for j in range(m):
        rows.append([Fraction(1 if mask & (1 << j) else 0) for mask in subsets])
        rhs.append(x[j])
    inequalities = [([-Fraction(1) if j == k else Fraction(0) for j in range(len(subsets))], Fraction(0)) for k in range(len(subsets))]
    objective = []
    for mask in subsets:
        if mask == 0:
            objective.append(v0)
        else:
            objective.append(max(values[j] for j in range(m) if mask & (1 << j)))
    # The equality system has m+1 rows; enumerate bases with that many columns.
    best: Fraction | None = None
    rank = len(rows)
    for basis in combinations(range(len(subsets)), rank):
        matrix = [[rows[r][c] for c in basis] for r in range(rank)]
        point = exact_square_solve(matrix, rhs)
        if point is None or any(value < 0 for value in point):
            continue
        full = [Fraction(0)] * len(subsets)
        for c, value in zip(basis, point):
            full[c] = value
        value = sum(c * p for c, p in zip(objective, full))
        if best is None or value < best:
            best = value
    if best is None:
        raise AssertionError("binary distribution LP had no feasible vertex")
    return best


def check_single_star_convex_hull() -> None:
    cases = [
        (Fraction(0), [Fraction(-2), Fraction(1), Fraction(1)]),
        (Fraction(2), [Fraction(-5), Fraction(0), Fraction(1)]),
        (Fraction(-3), [Fraction(3), Fraction(-3), Fraction(0)]),
    ]
    for alpha, b in cases:
        raw_values = [abs(alpha + value) for value in b]
        order = sorted(range(len(b)), key=lambda j: (raw_values[j], j))
        values = [raw_values[j] for j in order]
        for numerators in product(range(5), repeat=len(values)):
            x = [Fraction(n, 4) for n in numerators]
            chain = star_epigraph_lp(abs(alpha), values, x)
            hull = binary_epigraph_lp(values, abs(alpha), x)
            assert chain == hull, (alpha, b, x, chain, hull)


def check_global_locality_gap() -> None:
    # Six pair tasks on four shared resources; every task is a two-edge star.
    pairs = list(combinations(range(4), 2))
    fractional_local = sum(max(Fraction(0), Fraction(1) - Fraction(1, 2) - Fraction(1, 2)) for _ in pairs)
    assert fractional_local == 0
    integer_values = []
    for selected in range(1 << 4):
        if selected.bit_count() <= 2:
            integer_values.append(sum(1 for a, b in pairs if not (selected & (1 << a) or selected & (1 << b))))
    assert min(integer_values) == 1


def path_edges(m: int) -> list[Edge]:
    if m < 1:
        raise ValueError("the reduction uses at least one item")
    return [(j, j + 1) for j in range(2 * m - 1)]


def check_path_shape() -> None:
    """Regression for the connected 2m-vertex, (2m-1)-edge path."""
    for m in (1, 2, 3, 4):
        edges = path_edges(m)
        if m == 1:
            assert edges == [(0, 1)]
            continue
        assert len(edges) == 2 * m - 1
        assert edges == [(j, j + 1) for j in range(2 * m - 1)]
        assert {vertex for edge in edges for vertex in edge} == set(range(2 * m))


def path_reduction_objective(a: Sequence[int], target: int, selected: int) -> Fraction:
    m = len(a)
    edges = path_edges(m)
    scale = m + 1
    b = [Fraction(scale * a[j // 2]) if j % 2 == 0 else Fraction(1) for j in range(2 * m - 1)]
    return task_worst(edges, selected, Fraction(-scale * target), b)


def check_path_reduction() -> None:
    cases = [
        ([3], 3),
        ([3], 2),
        ([1, 2], 3),
        ([1, 3], 2),
        ([2, 3, 4], 5),
        ([2, 4, 4], 5),
        ([2, 3, 4, 7], 10),
        ([2, 4, 4, 7], 5),
    ]
    for a, target in cases:
        m = len(a)
        optimum = min(path_reduction_objective(a, target, selected) for selected in range(1 << (2 * m - 1)))
        subset_sum = any(sum(a[j] for j in range(m) if mask & (1 << j)) == target for mask in range(1 << m))
        assert (optimum == 0) == subset_sum, (a, target, optimum, subset_sum)


def path_profile_extrema(edges: Sequence[Edge], b: Sequence[Fraction], selected: int) -> tuple[Fraction, Fraction]:
    """Four-bit-boundary DP for one fixed selected path; exact arithmetic."""
    n = len(edges)
    if n == 0:
        return Fraction(0), Fraction(0)
    x = [(selected >> j) & 1 for j in range(n)]
    states: dict[tuple[int, int, int], tuple[Fraction, Fraction]] = {}
    for y in (0, 1):
        if y <= x[0]:
            states[(0, y, x[0])] = (b[0] * y, b[0] * y)
    for j in range(n - 1):
        new: dict[tuple[int, int, int], tuple[Fraction, Fraction]] = {}
        for (yp, yc, _), (lo, hi) in states.items():
            for yn in (0, 1):
                if yn > x[j + 1] or yc + yn > 1 or x[j] > yp + yc + yn:
                    continue
                state = (yc, yn, x[j + 1])
                values = (lo + b[j + 1] * yn, hi + b[j + 1] * yn)
                if state not in new:
                    new[state] = values
                else:
                    old_lo, old_hi = new[state]
                    new[state] = (min(old_lo, values[0]), max(old_hi, values[1]))
        states = new
    extrema: list[Fraction] = []
    for (yp, yc, _), (lo, hi) in states.items():
        if x[-1] <= yp + yc:
            extrema.extend((lo, hi))
    if not extrema:
        raise AssertionError("selected path has no maximal matching")
    return min(extrema), max(extrema)


def check_path_profile_dp() -> None:
    edges = [(j, j + 1) for j in range(6)]
    b = [Fraction(-3), Fraction(2), Fraction(4), Fraction(-1), Fraction(0), Fraction(5)]
    for selected in range(1 << len(edges)):
        selected_edges = [edge for j, edge in enumerate(edges) if selected & (1 << j)]
        selected_b = [value for j, value in enumerate(b) if selected & (1 << j)]
        brute = [matching_sum(mask, selected_b) for mask in maximal_matching_masks(selected_edges)]
        if not selected_edges:
            expected = (Fraction(0), Fraction(0))
        else:
            expected = (min(brute), max(brute))
        assert path_profile_extrema(edges, b, selected) == expected, (selected, expected)


def ordinary_max_error_matching(edges: Sequence[Edge], errors: Sequence[Fraction]) -> Fraction:
    return max((matching_sum(mask, errors) for mask in matching_masks(edges)), default=Fraction(0))


def check_matching_aware_transfer() -> None:
    edges = [(0, 1), (1, 2), (2, 3), (3, 4), (0, 1)]  # retain the labeled parallel edge
    alpha, tilde_alpha = Fraction(2), Fraction(1)
    b = [Fraction(-3), Fraction(2), Fraction(0), Fraction(4), Fraction(1)]
    tilde_b = [Fraction(-2), Fraction(2), Fraction(0), Fraction(0), Fraction(0)]
    errors = [abs(a - t) for a, t in zip(b, tilde_b)]
    eta = abs(alpha - tilde_alpha) + ordinary_max_error_matching(edges, errors)
    for selected in range(1 << len(edges)):
        original = task_worst(edges, selected, alpha, b)
        rounded = task_worst(edges, selected, tilde_alpha, tilde_b)
        assert abs(original - rounded) <= eta, (selected, original, rounded, eta)
    # The zero-rounded parallel/connector labels stay in the graph; deleting
    # them changes admissibility and is not a permitted perturbation.
    assert tilde_b[2] == 0 and tilde_b[3] == 0 and tilde_b[4] == 0


def main() -> None:
    check_single_star_convex_hull()
    check_global_locality_gap()
    check_path_shape()
    check_path_reduction()
    check_path_profile_dp()
    check_matching_aware_transfer()
    print("stage1d exact diagnostics: PASS")
    print("checks: star convex hull, global coupling gap, path shape, path reduction, path profile DP, matching-aware transfer")


if __name__ == "__main__":
    main()
