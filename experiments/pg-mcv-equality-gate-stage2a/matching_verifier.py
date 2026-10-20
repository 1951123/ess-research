"""Independent labeled maximal-matching checks for Issue #47."""

from __future__ import annotations

from collections.abc import Iterable, Mapping


class MatchingVerificationError(ValueError):
    """The observed selected set is not a matching or is not maximal."""


def verify_maximal_matching(
    candidates: Iterable[Mapping[str, object]],
    available_ids: Iterable[str],
    selected_ids: Iterable[str],
) -> dict[str, object]:
    edges: dict[str, frozenset[str]] = {}
    for candidate in candidates:
        label = str(candidate["id"])
        endpoints = frozenset(str(item) for item in candidate["columns"])
        if len(endpoints) != 2:
            raise MatchingVerificationError(f"candidate {label} is not a two-endpoint edge")
        if label in edges:
            raise MatchingVerificationError(f"duplicate candidate label: {label}")
        edges[label] = endpoints

    available = list(available_ids)
    selected = list(selected_ids)
    if len(set(available)) != len(available):
        raise MatchingVerificationError("available candidate labels are not unique")
    if len(set(selected)) != len(selected):
        raise MatchingVerificationError("selected candidate labels are not unique")
    unknown = (set(available) | set(selected)) - set(edges)
    if unknown:
        raise MatchingVerificationError(f"unknown candidate labels: {sorted(unknown)}")
    if not set(selected) <= set(available):
        raise MatchingVerificationError("selected candidate is not in the available graph")

    used: set[str] = set()
    for label in selected:
        overlap = used & set(edges[label])
        if overlap:
            raise MatchingVerificationError(
                f"selected edges are not a matching: {label} overlaps {sorted(overlap)}"
            )
        used.update(edges[label])
    addable = [
        label for label in available
        if label not in selected and not (set(edges[label]) & used)
    ]
    if addable:
        raise MatchingVerificationError(
            f"selected set is not inclusion-wise maximal; addable={addable}"
        )
    return {
        "selected_ids": selected,
        "available_ids": available,
        "used_endpoints": sorted(used),
        "is_matching": True,
        "is_inclusion_wise_maximal": True,
        "addable_ids": [],
    }

