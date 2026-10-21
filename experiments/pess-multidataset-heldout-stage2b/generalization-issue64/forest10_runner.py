"""Small Forest10 orchestration adapters; importing this module does no I/O.

The backend contract is intentionally injected. A caller may wrap the pinned
PR #58 helpers, but this module never loads AreCEL files or starts PostgreSQL.
"""

from __future__ import annotations

import json
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


def parse_pr7_structured_explain(
    output: str,
    *,
    query_id: str,
    relation_oid: int,
    expected_stat_oids: Mapping[int, str],
) -> dict[str, Any]:
    """Strictly parse the pinned PR #7 ``EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON)``.

    An empty MCV event stream is reported as *no observed MCV coverage*, not
    as evidence that a configured statistic was selected. When events exist,
    every selected OID must map to the current configured-stat ledger and its
    clauses and numeric estimate must form one ordered, complete record.
    """
    if not query_id or isinstance(relation_oid, bool) or relation_oid <= 0:
        raise ValueError("query ID and positive relation OID are required")
    if len(expected_stat_oids) != len(set(expected_stat_oids)):
        raise ValueError("configured statistic OIDs must be unique")
    if any(isinstance(oid, bool) or oid <= 0 or not stat_id for oid, stat_id in expected_stat_oids.items()):
        raise ValueError("configured statistic ledger contains an invalid OID or ID")
    try:
        document = json.loads(output)
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError("structured EXPLAIN output is not valid JSON") from exc
    if not isinstance(document, list) or len(document) != 1 or not isinstance(document[0], dict):
        raise ValueError("structured EXPLAIN must contain exactly one top-level query record")
    result = document[0]
    if not isinstance(result.get("Plan"), dict):
        raise ValueError("structured EXPLAIN is missing the Plan object")
    diagnostics = result.get("ESS Diagnostics")
    if not isinstance(diagnostics, dict):
        raise ValueError("structured EXPLAIN is missing ESS Diagnostics")
    if diagnostics.get("Status") != "complete":
        raise ValueError("ESS Diagnostics status is not complete")
    events = diagnostics.get("Events")
    event_count = diagnostics.get("Event Count")
    if not isinstance(events, list) or isinstance(event_count, bool) or not isinstance(event_count, int):
        raise ValueError("ESS Diagnostics event list/count is missing or malformed")
    if event_count != len(events) or event_count <= 0:
        raise ValueError("ESS Diagnostics Event Count does not match a nonempty Events list")

    bases: list[dict[str, Any]] = []
    mcv_records: list[dict[str, Any]] = []
    active: dict[str, Any] | None = None

    def integer(event: Mapping[str, Any], key: str, *, minimum: int = 0) -> int:
        value = event.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < minimum:
            raise ValueError(f"ESS Diagnostics event has invalid {key}")
        return value

    for expected_sequence, event in enumerate(events, start=1):
        if not isinstance(event, dict) or integer(event, "sequence", minimum=1) != expected_sequence:
            raise ValueError("ESS Diagnostics event sequence is missing, duplicated, or out of order")
        event_type = event.get("type")
        if event_type == "base_estimate":
            if active is not None:
                raise ValueError("base-estimate event interrupts an MCV diagnostic record")
            bases.append(event)
            continue
        if event_type == "mcv_selection":
            if active is not None:
                raise ValueError("MCV selection arrived before the prior MCV record completed")
            relid = integer(event, "relation_oid", minimum=1)
            statoid = integer(event, "stat_oid", minimum=1)
            if relid != relation_oid or statoid not in expected_stat_oids:
                raise ValueError("MCV selection does not correspond to the query relation/configured OID ledger")
            if integer(event, "key_count", minimum=1) != 2:
                raise ValueError("selected Forest10 MCV statistic is not a two-key object")
            active = {"relation_oid": relid, "stat_oid": statoid, "clause_indexes": []}
            continue
        if event_type == "mcv_clause":
            if active is None:
                raise ValueError("MCV clause has no preceding selected-stat record")
            identity = (integer(event, "relation_oid", minimum=1), integer(event, "stat_oid", minimum=1))
            if identity != (active["relation_oid"], active["stat_oid"]):
                raise ValueError("MCV clause relation/stat OID differs from its selected statistic")
            clause_index = integer(event, "clause_index")
            if clause_index in active["clause_indexes"]:
                raise ValueError("MCV statistic claimed a duplicate clause index")
            active["clause_indexes"].append(clause_index)
            continue
        if event_type == "mcv_estimate":
            if active is None:
                raise ValueError("MCV estimate has no preceding selected-stat record")
            identity = (integer(event, "relation_oid", minimum=1), integer(event, "stat_oid", minimum=1))
            if identity != (active["relation_oid"], active["stat_oid"]):
                raise ValueError("MCV estimate relation/stat OID differs from its selected statistic")
            clause_count = integer(event, "clause_count", minimum=1)
            if clause_count != len(active["clause_indexes"]):
                raise ValueError("MCV estimate clause_count differs from its claimed clause records")
            numeric_fields = (
                "simple_sel", "mcv_sel", "mcv_basesel", "mcv_totalsel", "stat_sel"
            )
            numeric: dict[str, str] = {}
            for field in numeric_fields:
                try:
                    value = Decimal(str(event[field]))
                except (KeyError, ValueError, ArithmeticError) as exc:
                    raise ValueError(f"MCV estimate is missing or has invalid {field}") from exc
                if not value.is_finite():
                    raise ValueError(f"MCV estimate has non-finite {field}")
                numeric[field] = str(value)
            mcv_records.append({
                "relation_oid": active["relation_oid"],
                "stat_oid": active["stat_oid"],
                "statistic_id": expected_stat_oids[active["stat_oid"]],
                "clause_indexes": list(active["clause_indexes"]),
                "clause_count": clause_count,
                **numeric,
            })
            active = None
            continue
        raise ValueError("ESS Diagnostics contains an unknown event type")

    if active is not None:
        raise ValueError("ESS Diagnostics ends with an unmatched MCV selection")
    if len(bases) != 1:
        raise ValueError("Forest10 query must have exactly one base-estimate event")
    base = bases[0]
    if integer(base, "relation_oid", minimum=1) != relation_oid:
        raise ValueError("base-estimate relation OID does not match fresh public.forest10")
    try:
        preclamp = Decimal(str(base["nrows_preclamp"]))
    except (KeyError, ValueError, ArithmeticError) as exc:
        raise ValueError("base estimate is missing a valid nrows_preclamp") from exc
    if not preclamp.is_finite() or preclamp <= 0:
        raise ValueError("base estimate nrows_preclamp must be finite and positive")
    return {
        "query_id": query_id,
        "relation_oid": relation_oid,
        "estimate_preclamp": str(preclamp),
        "diagnostics_status": "complete",
        "event_count": event_count,
        "mcv_diagnostics_status": "VERIFIED" if mcv_records else "NO_MCV_EVENTS",
        "selected_statistic_ids": [record["statistic_id"] for record in mcv_records],
        "mcv_records": mcv_records,
    }


class PR7StructuredExplainAdapter:
    """Strict PR #7 JSON adapter; the sole active calibration observation source."""

    def __init__(
        self,
        helpers: Any,
        prefix: Path,
        cluster: Mapping[str, Any],
        relation_oid: int,
        configured_ledger: Sequence[Mapping[str, Any]],
        statistic_name_to_id: Mapping[str, str] | None = None,
    ) -> None:
        self.helpers = helpers
        self.prefix = prefix
        self.cluster = cluster
        self.relation_oid = relation_oid
        name_to_id = statistic_name_to_id or {}
        self.expected_stat_oids = {
            int(row["oid"]): str(
                row.get("id") or row.get("statistic_id")
                or name_to_id.get(str(row.get("statistic_name", "")), "")
            )
            for row in configured_ledger
        }
        if len(self.expected_stat_oids) != len(configured_ledger):
            raise ValueError("configured statistics ledger contains duplicate OIDs")
        if any(not statistic_id for statistic_id in self.expected_stat_oids.values()):
            raise ValueError("configured statistics ledger cannot be mapped to candidate IDs")

    def explain(self, query: Mapping[str, Any]) -> dict[str, Any]:
        query_id = str(query.get("query_id", ""))
        sql_text = str(query.get("sql", ""))
        if not query_id or not sql_text.lstrip().upper().startswith("SELECT "):
            raise ValueError("structured EXPLAIN requires a named SELECT query")
        env = dict(self.helpers.os.environ, LD_LIBRARY_PATH=str(self.prefix / "lib"))
        sql = (
            "SET client_min_messages=warning; SET plan_cache_mode=force_custom_plan; "
            "SET max_parallel_workers_per_gather=0; "
            "EXPLAIN (ESS_DIAGNOSTICS, FORMAT JSON, SUMMARY OFF) " + sql_text
        )
        output = self.helpers.psql(
            self.prefix, self.cluster["socket_dir"], self.cluster["port"],
            sql, env, tuples=True,
        )
        return parse_pr7_structured_explain(
            output.strip(), query_id=query_id, relation_oid=self.relation_oid,
            expected_stat_oids=self.expected_stat_oids,
        )


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

    observations: list[dict[str, Any]] = []

    def measure(query_id: str, config_id: str, ledger: Any, marker: str, eligible: bool | None) -> Decimal:
        estimate = backend.preclamp_estimate(query_map[query_id], ledger, marker)
        parsed = getattr(backend, "last_observation", None)
        if parsed is not None:
            if parsed.get("query_id") != query_id or parsed.get("diagnostics_status") != "complete":
                raise ValueError("structured calibration observation is incomplete or associated with another query")
            if Decimal(parsed["estimate_preclamp"]) != Decimal(estimate):
                raise ValueError("backend estimate differs from its structured nrows_preclamp observation")
            observations.append({
                "query_id": query_id,
                "config_id": config_id,
                "static_eligible": eligible,
                "diagnostics_status": parsed["diagnostics_status"],
                "nrows_preclamp": str(estimate),
                "mcv_diagnostics_status": parsed["mcv_diagnostics_status"],
                "mcv_events": [
                    {"relation_oid": row["relation_oid"], "stat_oid": row["stat_oid"],
                     "statistic_id": row["statistic_id"], "clause_indexes": row["clause_indexes"]}
                    for row in parsed["mcv_records"]
                ],
                "status": "SUCCESS",
            })
        elif isinstance(backend, PR58Forest10Backend):
            raise ValueError("pinned calibration backend did not produce a structured JSON observation")
        return estimate

    empty_ledger = backend.configure(())
    empty = {
        query_id: measure(query_id, "Empty", empty_ledger,
                           f"issue64-forest10-valid-empty-{index:05d}", None)
        for index, query_id in enumerate(query_ids)
    }
    singletons: dict[str, dict[str, Decimal]] = {}
    for edge in candidate_ids:
        eligible_ids = tuple(query_id for query_id in query_ids if edge in available[query_id])
        if not eligible_ids:
            continue
        ledger = backend.configure((edge,))
        singletons[edge] = {
            query_id: measure(query_id, edge, ledger,
                              f"issue64-forest10-valid-{edge}-{index:05d}", True)
            for index, query_id in enumerate(eligible_ids)
        }
    models = build_task_models(query_ids, valid_truth, empty, singletons, available)
    selection = exact_select_many(models, candidates, budgets)
    return {
        "dataset": "Forest10",
        "calibration_split": "valid",
        "task_count": len(models),
        "empty_and_eligible_singleton_preclamp_only": True,
        "calibration_observations": observations,
        "selection": selection,
    }


class PR58Forest10Backend:
    """PR #58 model/setup helpers plus PR #7 JSON-only calibration observations.

    `helpers` is the already hash-verified PR #58 module. `cluster` and the
    replayed `sample` are supplied by its approved preparation path. Methods
    perform PostgreSQL operations only when explicitly called by an approved
    runner. Estimates come from structured diagnostics, never the server log.
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
        self.relation_oid = int(self.sample_identity["header"]["relation_oid"])
        self.last_observation: dict[str, Any] | None = None

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
        del marker  # Kept in the injected backend contract; JSON has no trace marker.
        adapter = PR7StructuredExplainAdapter(
            self.helpers,
            self.prefix,
            self.cluster,
            self.relation_oid,
            ledger,
            self.name_to_id,
        )
        self.last_observation = adapter.explain(query)
        estimate = Decimal(self.last_observation["estimate_preclamp"])
        if not estimate.is_finite() or estimate <= 0:
            raise ValueError("PR #7 returned a nonpositive/nonfinite pre-clamp estimate")
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
