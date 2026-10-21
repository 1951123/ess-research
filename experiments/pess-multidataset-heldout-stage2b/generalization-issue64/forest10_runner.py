"""Small Forest10 orchestration adapters; importing this module does no I/O.

The backend contract is intentionally injected. A caller may wrap the pinned
PR #58 helpers, but this module never loads AreCEL files or starts PostgreSQL.
"""

from __future__ import annotations

import math
from decimal import Decimal, ROUND_HALF_EVEN, localcontext
from fractions import Fraction
from pathlib import Path
from typing import Any, Mapping, Protocol, Sequence

from forest10_exact_selection import TaskModel, exact_select_many
from forest10_q1 import parse_top_level_plan_rows, q1

LOG_QUANTUM = Decimal("0.000000000000000001")
FOREST10_RELATION = "public.forest10"
FOREST10_SOURCE_COLUMNS = (
    "Elevation",
    "Aspect",
    "Slope",
    "Horizontal_Distance_To_Hydrology",
    "Vertical_Distance_To_Hydrology",
    "Horizontal_Distance_To_Roadways",
    "Hillshade_9am",
    "Hillshade_Noon",
    "Hillshade_3pm",
    "Horizontal_Distance_To_Fire_Points",
)
FOREST10_SAMPLE_RELATION_IDENTITY = "6:public8:forest10"


class Forest10Backend(Protocol):
    """Minimal operations supplied by a separately approved PG runner."""

    def configure(self, selected: tuple[str, ...]) -> Any: ...

    def preclamp_estimate(self, query: Mapping[str, Any], ledger: Any, marker: str) -> Decimal: ...

    def plan_rows(self, query: Mapping[str, Any]) -> int: ...


def rational_log_ratio(numerator: int | Decimal, denominator: int | Decimal) -> Fraction:
    """PR #58-compatible Decimal ln, 80-digit context, 1e-18 half-even grid."""
    left, right = Decimal(numerator), Decimal(denominator)
    if left <= 0 or right <= 0:
        raise ValueError("natural-log ratio inputs must be positive")
    with localcontext() as context:
        context.prec = 80
        value = (left / right).ln().quantize(LOG_QUANTUM, rounding=ROUND_HALF_EVEN)
    return Fraction(str(value))


def _unique_query_map(queries: Sequence[Mapping[str, Any]]) -> dict[str, Mapping[str, Any]]:
    result = {str(query["query_id"]): query for query in queries}
    if len(result) != len(queries):
        raise ValueError("query IDs must be unique")
    return result


def pr58_candidate_specs(
    candidates: Sequence[tuple[str, Sequence[str]]],
    source_columns: Sequence[str] = FOREST10_SOURCE_COLUMNS,
) -> tuple[dict[str, Any], ...]:
    """Translate PR #68 source-name pairs to PR #58 catalog candidates.

    Forest10's pinned schema folds source identifiers to lowercase catalog
    names. PR #58 creates all statistics on public.forest10.
    """
    columns = tuple(source_columns)
    if columns != FOREST10_SOURCE_COLUMNS:
        raise ValueError("Forest10 source-column order differs from the pinned schema")
    column_names = set(columns)
    result = []
    seen: set[str] = set()
    for edge, endpoints in candidates:
        pair = tuple(endpoints)
        if edge in seen or len(pair) != 2 or pair[0] == pair[1] or set(pair) - column_names:
            raise ValueError(f"invalid Forest10 candidate definition: {edge}")
        seen.add(edge)
        result.append({
            "id": edge,
            "statistic_name": f"ess_issue64_forest10_{edge}",
            "catalog_columns": [column.lower() for column in pair],
        })
    return tuple(result)


def validate_fresh_sample_identity(
    sample: Path, identity: Mapping[str, Any], helpers: Any
) -> None:
    """Reject the old forest10_original sample and stale/mismatched metadata.

    This is an input/provenance check, not proof that PostgreSQL accepted a
    replay. The approved bootstrap path must export the sample from the same
    freshly loaded public.forest10 relation and cluster.
    """
    header = identity.get("header")
    if identity.get("table") != FOREST10_RELATION:
        raise ValueError("sample must have been exported from the Stage 2B public.forest10 relation")
    if not isinstance(header, Mapping):
        raise ValueError("fresh-bootstrap sample identity/header is required")
    actual_header = helpers.sample_header(sample) if sample.is_file() else None
    if actual_header != dict(header):
        raise ValueError("sample header does not match the fresh-bootstrap identity")
    if header.get("relation_identity") != FOREST10_SAMPLE_RELATION_IDENTITY:
        raise ValueError("sample relation identity is not the encoded public.forest10 identity")
    if header.get("server_version") != "16.14" or header.get("natts") != len(FOREST10_SOURCE_COLUMNS):
        raise ValueError("sample version or Forest10 column count differs from the pinned contract")
    if helpers.sha256_file(sample) != identity.get("sha256"):
        raise ValueError("sample bytes do not match the fresh-bootstrap identity digest")


def build_task_models(
    query_ids: Sequence[str],
    valid_truth: Mapping[str, int],
    empty_preclamp: Mapping[str, Decimal | int | str],
    singleton_preclamp: Mapping[str, Mapping[str, Decimal | int | str]],
    available_edges: Mapping[str, Sequence[str]],
) -> tuple[TaskModel, ...]:
    """Build frozen PR #58 alpha/b coefficients from valid-only observations."""
    ids = tuple(query_ids)
    expected = set(ids)
    if len(expected) != len(ids):
        raise ValueError("calibration query IDs must be unique")
    if set(valid_truth) != expected or set(empty_preclamp) != expected or set(available_edges) != expected:
        raise ValueError("valid truth, Empty estimates, and eligibility must cover exactly the calibration IDs")
    edge_ids = set(singleton_preclamp)
    models: list[TaskModel] = []
    for query_id in ids:
        truth = valid_truth[query_id]
        if isinstance(truth, bool) or not isinstance(truth, int) or truth < 0:
            raise ValueError(f"valid truth must be a nonnegative integer: {query_id}")
        n0 = Decimal(empty_preclamp[query_id])
        if not n0.is_finite() or n0 <= 0:
            raise ValueError(f"Empty pre-clamp estimate must be positive: {query_id}")
        eligible = tuple(available_edges[query_id])
        if len(eligible) != len(set(eligible)) or set(eligible) - edge_ids:
            raise ValueError(f"invalid candidate eligibility for {query_id}")
        b_values: dict[str, Fraction] = {}
        for edge in eligible:
            values = singleton_preclamp[edge]
            if query_id not in values:
                raise ValueError(f"missing eligible singleton pre-clamp estimate: {query_id}/{edge}")
            estimate = Decimal(values[query_id])
            if not estimate.is_finite() or estimate <= 0:
                raise ValueError(f"singleton pre-clamp estimate must be positive: {query_id}/{edge}")
            b_values[edge] = rational_log_ratio(estimate, n0)
        models.append(
            TaskModel(
                alpha=rational_log_ratio(n0, max(1, truth)),
                b=b_values,
                available_edges=eligible,
            )
        )

    for edge, rows in singleton_preclamp.items():
        allowed_ids = {query_id for query_id in ids if edge in available_edges[query_id]}
        if set(rows) != allowed_ids:
            raise ValueError(f"singleton rows for {edge} must exactly match statically eligible valid queries")
    return tuple(models)


def calibrate_and_select(
    valid_queries: Sequence[Mapping[str, Any]],
    valid_truth: Mapping[str, int],
    candidates: Sequence[tuple[str, Sequence[str]]],
    available_edges: Mapping[str, Sequence[str]],
    backend: Forest10Backend,
    budgets: Sequence[int] = (0, 2, 3),
    expected_query_count: int | None = 10_000,
) -> dict[str, Any]:
    """Measure only Empty/eligible singletons on valid, then exact-select."""
    query_map = _unique_query_map(valid_queries)
    query_ids = tuple(query_map)
    if expected_query_count is not None and len(query_ids) != expected_query_count:
        raise ValueError(f"valid calibration must contain exactly {expected_query_count} queries")
    if set(valid_truth) != set(query_ids):
        raise ValueError("valid truth must exactly match the supplied valid queries")
    candidate_ids = tuple(edge for edge, _ in candidates)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate IDs must be unique")
    available = {query_id: tuple(available_edges[query_id]) for query_id in query_ids}
    if set(available_edges) != set(query_ids):
        raise ValueError("static eligibility must exactly match the supplied valid queries")
    if any(set(edges) - set(candidate_ids) for edges in available.values()):
        raise ValueError("query eligibility refers to an unknown candidate")

    empty_ledger = backend.configure(())
    empty = {
        query_id: backend.preclamp_estimate(
            query_map[query_id], empty_ledger, f"issue64-forest10-valid-empty-{index:05d}"
        )
        for index, query_id in enumerate(query_ids)
    }
    singletons: dict[str, dict[str, Decimal]] = {}
    for edge in candidate_ids:
        eligible_ids = tuple(query_id for query_id in query_ids if edge in available[query_id])
        if not eligible_ids:
            continue
        ledger = backend.configure((edge,))
        singletons[edge] = {
            query_id: backend.preclamp_estimate(
                query_map[query_id], ledger, f"issue64-forest10-valid-{edge}-{index:05d}"
            )
            for index, query_id in enumerate(eligible_ids)
        }
    models = build_task_models(query_ids, valid_truth, empty, singletons, available)
    selection = exact_select_many(models, candidates, budgets)
    return {
        "dataset": "Forest10",
        "calibration_split": "valid",
        "task_count": len(models),
        "empty_and_eligible_singleton_preclamp_only": True,
        "selection": selection,
    }


class PR58Forest10Backend:
    """Thin adapter over PR #58 helpers; construction itself is side-effect free.

    `helpers` is the already hash-verified PR #58 module. `cluster` and the
    replayed `sample` are supplied by its approved preparation path. Methods
    perform PostgreSQL operations only when explicitly called by an approved
    runner; this module's tests use a synthetic backend instead.
    """

    def __init__(
        self,
        helpers: Any,
        prefix: Path,
        cluster: dict[str, Any],
        candidates: Sequence[Mapping[str, Any]],
        sample: Path,
        sample_identity: Mapping[str, Any],
    ) -> None:
        validate_fresh_sample_identity(sample, sample_identity, helpers)
        self.helpers = helpers
        self.prefix = prefix
        self.cluster = cluster
        self.candidates = {str(candidate["id"]): dict(candidate) for candidate in candidates}
        self.sample = sample
        self.sample_identity = dict(sample_identity)
        self.dataset = "forest10"
        self.name_to_id = {
            str(candidate["statistic_name"]): str(candidate["id"])
            for candidate in candidates
        }
        self._log_offset = int(cluster["server_log"].stat().st_size)

    @classmethod
    def from_fresh_bootstrap(
        cls,
        helpers: Any,
        prefix: Path,
        cluster: dict[str, Any],
        candidates: Sequence[Mapping[str, Any]],
        prepared_root: Path,
        spec: dict[str, Any],
        prepared_csv: Path,
    ) -> "PR58Forest10Backend":
        """Create the table and sample through PR #58 in the same PG cluster."""
        sample, identity = helpers.bootstrap_cluster(
            prefix,
            cluster,
            prepared_root,
            "forest10",
            spec,
            prepared_csv,
        )
        return cls(helpers, prefix, cluster, candidates, sample, identity)

    def configure(self, selected: tuple[str, ...]) -> Any:
        return self.helpers.configure_statistics(
            self.prefix,
            self.cluster,
            self.dataset,
            self.candidates,
            selected,
            self.sample,
        )

    def preclamp_estimate(self, query: Mapping[str, Any], ledger: Any, marker: str) -> Decimal:
        measured, self._log_offset = self.helpers.run_query(
            self.prefix,
            self.cluster,
            dict(query),
            ledger,
            marker,
            self._log_offset,
            self.name_to_id,
        )
        estimate = Decimal(measured["estimate_preclamp"])
        if not estimate.is_finite() or estimate <= 0:
            raise ValueError("PR #58 returned a nonpositive/nonfinite pre-clamp estimate")
        return estimate

    def plan_rows(self, query: Mapping[str, Any]) -> int:
        env = dict(self.helpers.os.environ, LD_LIBRARY_PATH=str(self.prefix / "lib"))
        sql = (
            "SET client_min_messages=warning; SET plan_cache_mode=force_custom_plan; "
            "SET max_parallel_workers_per_gather=0; EXPLAIN (FORMAT JSON, SUMMARY OFF) "
            + str(query["sql"])
        )
        output = self.helpers.psql(
            self.prefix,
            self.cluster["socket_dir"],
            self.cluster["port"],
            sql,
            env,
        )
        return parse_top_level_plan_rows(output.strip())


def nearest_rank(values: Sequence[Fraction], percentile: int) -> Fraction:
    if not values or percentile not in (50, 95, 99):
        raise ValueError("nearest-rank requires values and percentile 50, 95, or 99")
    ordered = sorted(values)
    rank = max(1, math.ceil(percentile * len(ordered) / 100))
    return ordered[rank - 1]


def evaluate_frozen_selections(
    test_queries: Sequence[Mapping[str, Any]],
    test_truth: Mapping[str, int],
    selections: Mapping[str, Sequence[str]],
    backend: Forest10Backend,
    expected_query_count: int | None = 10_000,
) -> dict[str, Any]:
    """Evaluate pre-frozen distinct sets with top-level EXPLAIN Plan Rows/Q1.

    This function is deliberately not called by this outcome-free workflow.
    Callers must obtain separate execution approval and pass the official test
    split only after selection/protocol freeze.
    """
    query_map = _unique_query_map(test_queries)
    query_ids = tuple(query_map)
    if expected_query_count is not None and len(query_ids) != expected_query_count:
        raise ValueError(f"test evaluation must contain exactly {expected_query_count} queries")
    if set(test_truth) != set(query_ids):
        raise ValueError("test truth must exactly match the supplied test queries")
    if not selections:
        raise ValueError("at least one frozen selection is required")
    aliases_by_set: dict[tuple[str, ...], list[str]] = {}
    for alias, selected in selections.items():
        chosen = tuple(selected)
        if len(chosen) != len(set(chosen)):
            raise ValueError(f"selection contains duplicate resources: {alias}")
        aliases_by_set.setdefault(chosen, []).append(alias)

    raw: dict[str, dict[str, int | None]] = {}
    compact: list[dict[str, Any]] = []
    for selected, aliases in aliases_by_set.items():
        ledger = backend.configure(selected)
        del ledger  # ordinary Q1 evaluation does not require trace attribution
        key = ",".join(selected)
        estimates: dict[str, int | None] = {}
        for query_id in query_ids:
            actual = test_truth[query_id]
            try:
                if isinstance(actual, bool) or not isinstance(actual, int) or actual < 0:
                    raise ValueError("truth must be a nonnegative integer")
                estimate = backend.plan_rows(query_map[query_id])
                ratio = q1(estimate, actual)
                estimates[query_id] = estimate
                compact.append({
                    "query_id": query_id,
                    "selection_aliases": aliases,
                    "estimate_plan_rows": estimate,
                    "true_cardinality": actual,
                    "q1": str(ratio),
                    "status": "VALID",
                })
            except Exception as exc:
                estimates[query_id] = None
                compact.append({
                    "query_id": query_id,
                    "selection_aliases": aliases,
                    "estimate_plan_rows": None,
                    "true_cardinality": actual if isinstance(actual, int) and not isinstance(actual, bool) else None,
                    "q1": None,
                    "status": "UNRESOLVED",
                    "error_type": type(exc).__name__,
                })
        raw[key] = estimates

    metrics: dict[str, Any] = {}
    q1_by_alias: dict[str, dict[str, Fraction]] = {}
    for selected, aliases in aliases_by_set.items():
        key = ",".join(selected)
        ratios = {
            qid: q1(raw[key][qid], test_truth[qid])
            for qid in query_ids
            if raw[key][qid] is not None
            and isinstance(test_truth[qid], int)
            and not isinstance(test_truth[qid], bool)
            and test_truth[qid] >= 0
        }
        for alias in aliases:
            q1_by_alias[alias] = ratios
            complete = len(ratios) == len(query_ids)
            metrics[alias] = {
                "status": "COMPLETE" if complete else "INCONCLUSIVE_UNRESOLVED_ROWS",
                "query_count": len(query_ids),
                "valid_q1_count": len(ratios),
                "unresolved_count": len(query_ids) - len(ratios),
                "p50_q1": str(nearest_rank(tuple(ratios.values()), 50)) if complete else None,
                "p95_q1": str(nearest_rank(tuple(ratios.values()), 95)) if complete else None,
                "p99_q1": str(nearest_rank(tuple(ratios.values()), 99)) if complete else None,
                "max_q1": str(max(ratios.values())) if complete else None,
                "mean_abs_log_error_positive_pairs": (
                    math.fsum(abs(math.log(raw[key][qid] / test_truth[qid])) for qid in query_ids
                              if raw[key][qid] is not None and raw[key][qid] > 0
                              and isinstance(test_truth[qid], int) and not isinstance(test_truth[qid], bool)
                              and test_truth[qid] > 0)
                    / sum(raw[key][qid] is not None and raw[key][qid] > 0
                          and isinstance(test_truth[qid], int) and not isinstance(test_truth[qid], bool)
                          and test_truth[qid] > 0 for qid in query_ids)
                    if any(raw[key][qid] is not None and raw[key][qid] > 0
                           and isinstance(test_truth[qid], int) and not isinstance(test_truth[qid], bool)
                           and test_truth[qid] > 0 for qid in query_ids)
                    else None
                ),
                "positive_pair_count": sum(
                    raw[key][qid] is not None and raw[key][qid] > 0
                    and isinstance(test_truth[qid], int) and not isinstance(test_truth[qid], bool)
                    and test_truth[qid] > 0 for qid in query_ids
                ),
            }

    paired: dict[str, Any] = {}
    aliases = set(q1_by_alias)
    for nominal_alias in sorted(alias for alias in aliases if alias.startswith("Nominal")):
        suffix = nominal_alias[len("Nominal") :]
        pess_alias = "PESS" + suffix
        if pess_alias not in q1_by_alias:
            continue
        common_ids = set(q1_by_alias[nominal_alias]) & set(q1_by_alias[pess_alias])
        changes = [q1_by_alias[pess_alias][qid] - q1_by_alias[nominal_alias][qid]
                   for qid in query_ids if qid in common_ids]
        paired[nominal_alias.removeprefix("Nominal").lstrip("_-") or "default"] = {
            "nominal_alias": nominal_alias,
            "pess_alias": pess_alias,
            "estimand": "exact per-query Q1(PESS)-Q1(Nominal)",
            "benefit_count": sum(delta < 0 for delta in changes),
            "harm_count": sum(delta > 0 for delta in changes),
            "tie_count": sum(delta == 0 for delta in changes),
            "common_valid_query_count": len(changes),
            "unresolved_query_count": len(query_ids) - len(changes),
            "status": "COMPLETE" if len(changes) == len(query_ids) else "INCONCLUSIVE_UNRESOLVED_ROWS",
        }
    return {
        "dataset": "Forest10",
        "evaluation_split": "test",
        "selection_sets_measured": len(aliases_by_set),
        "query_observations": compact,
        "metrics": metrics,
        "paired_q1": paired,
        "estimator": "top-level PostgreSQL EXPLAIN Plan Rows",
        "model_coefficients_are_not_pg_plan_rows": True,
    }


def explain_plan_rows_from_psql_output(output: str) -> int:
    """Parse ordinary psql JSON output without depending on trace payloads."""
    return parse_top_level_plan_rows(output.strip())
