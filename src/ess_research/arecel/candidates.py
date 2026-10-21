"""Discover statically eligible pairwise MCV candidates from AreCEL valid queries.

This is a workload-shape screen only. It does not establish that PostgreSQL
considers, builds, selects, or benefits from any discovered statistics object.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from collections.abc import Mapping, Sequence
from itertools import combinations
from typing import Any

from .archive import DATASETS, _schema, prepare_valid_workload
from .real import SUPPORTED_OPERATORS


def discover_candidates(
    queries: Sequence[Mapping[str, Any]], source_columns: Sequence[str]
) -> dict[str, Any]:
    """Count supported unordered column pairs once per valid query.

    Predicate columns with Issue #47-supported simple comparisons are deduped
    within each query. The prepared inclusive-range operator (``[]``) has the
    same supported restriction meaning as its two bound comparisons. Pairs
    containing a malformed, unknown-column, or unsupported predicate are
    reported by reason and are not counted as eligible candidates. If any
    predicate for a column is unsupported, that column is conservatively
    excluded for the whole query even if another predicate on it is supported.
    """

    column_order = {column: index for index, column in enumerate(source_columns)}
    if len(column_order) != len(source_columns):
        raise ValueError("source schema contains duplicate columns")

    candidate_support: Counter[tuple[str, str]] = Counter()
    rejected_pair_support: Counter[str] = Counter()
    rejected_predicates: Counter[str] = Counter()
    rejection_details: list[dict[str, Any]] = []

    for query_index, query in enumerate(queries):
        predicates = query.get("predicates")
        if not isinstance(predicates, list):
            raise ValueError(f"query {query_index}: predicates must be a list")

        observed_columns: set[str] = set()
        eligible_columns: set[str] = set()
        rejected_columns: dict[str, set[str]] = {}
        query_id = query.get("query_id", f"query:{query_index}")
        for predicate_index, predicate in enumerate(predicates):
            if not isinstance(predicate, Mapping):
                reason = "malformed_predicate"
                rejected_predicates[reason] += 1
                rejection_details.append(
                    {
                        "query_id": query_id,
                        "predicate_index": predicate_index,
                        "reason": reason,
                    }
                )
                continue
            column = predicate.get("column")
            operator = predicate.get("operator")
            if not isinstance(column, str):
                reason = "missing_or_invalid_column"
                rejected_predicates[reason] += 1
                rejection_details.append(
                    {
                        "query_id": query_id,
                        "predicate_index": predicate_index,
                        "reason": reason,
                    }
                )
                continue
            observed_columns.add(column)
            if column not in column_order:
                reason = "unknown_column"
            elif not isinstance(operator, str) or operator not in SUPPORTED_OPERATORS:
                reason = "unsupported_operator"
            elif operator == "[]" and (
                not isinstance(predicate.get("value"), (list, tuple))
                or len(predicate["value"]) != 2
            ):
                reason = "malformed_inclusive_range"
            else:
                eligible_columns.add(column)
                continue
            rejected_columns.setdefault(column, set()).add(reason)
            rejected_predicates[reason] += 1
            rejection_details.append(
                {
                    "query_id": query_id,
                    "predicate_index": predicate_index,
                    "column": column,
                    "operator": operator if isinstance(operator, str) else repr(operator),
                    "reason": reason,
                }
            )

        eligible_columns.difference_update(rejected_columns)
        ordered_observed = sorted(
            observed_columns,
            key=lambda column: (column_order.get(column, len(column_order)), column),
        )
        for left, right in combinations(ordered_observed, 2):
            if left in eligible_columns and right in eligible_columns:
                pair = tuple(sorted((left, right), key=column_order.__getitem__))
                candidate_support[pair] += 1
            else:
                reasons = sorted(
                    {
                        reason
                        for column in (left, right)
                        if column in rejected_columns
                        for reason in rejected_columns[column]
                    }
                )
                reason = "+".join(reasons) if reasons else "no_supported_restriction"
                rejected_pair_support[reason] += 1

    candidates = [
        {
            "column_a": left,
            "column_b": right,
            "eligible_valid_query_count": candidate_support[(left, right)],
        }
        for left, right in sorted(
            candidate_support,
            key=lambda pair: (column_order[pair[0]], column_order[pair[1]]),
        )
    ]
    return {
        "valid_query_count": len(queries),
        "candidate_count": len(candidates),
        "candidates": candidates,
        "rejected_predicates": rejection_details,
        "rejected_predicate_count_by_reason": dict(sorted(rejected_predicates.items())),
        "cooccurring_pair_query_count_excluded_by_reason": dict(
            sorted(rejected_pair_support.items())
        ),
    }


def _run(dataset: str) -> dict[str, Any]:
    source_columns, _columns, _relation = _schema(dataset)
    with prepare_valid_workload(issue=67, dataset=dataset) as prepared:
        workload_path = prepared.workload_path
        workload = json.loads(workload_path.read_text(encoding="utf-8"))
        if (
            workload.get("dataset") != dataset
            or workload.get("split") != "valid"
            or not isinstance(workload.get("queries"), list)
        ):
            raise ValueError(f"unexpected prepared valid workload: {workload_path}")
        result = discover_candidates(workload["queries"], source_columns)
        return {
            "format": "arecel-valid-pairwise-mcv-candidates-v1",
            "dataset": dataset,
            "split": "valid",
            "source_columns": list(source_columns),
            "archive_sha256": prepared.manifest["archive_sha256"],
            "upstream_commit": prepared.manifest["upstream_commit"],
            "etl_commit": prepared.manifest["etl"].get("git_commit"),
            "etl_worktree_dirty": prepared.manifest["etl"].get("worktree_dirty"),
            "python_version": prepared.manifest["python"],
            "labels_loaded": prepared.manifest["labels_loaded"],
            "eligibility_basis": (
                "Existing AreCEL simple-restriction operator contract; distinct source columns "
                "with at least one supported predicate per query. Inclusive ranges require two bounds."
            ),
            **result,
            "interpretation": (
                "Static workload eligibility only; PostgreSQL use or benefit was not measured."
            ),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=DATASETS, required=True)
    args = parser.parse_args(argv)
    print(json.dumps(_run(args.dataset), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
