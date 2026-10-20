"""Outcome-free cohort identity helpers matching the merged Issue #59 contract.

This module does not generate queries or read datasets. It freezes the exact
fingerprint, group/split identity and counter-based draw primitives that a
future authorized manifest builder must use.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


DATASETS = frozenset({"forest10", "census13", "dmv11", "power7"})
SPLITS = frozenset({"calibration", "heldout"})


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    )


def normalized_template(query: dict[str, Any]) -> str:
    """Byte-for-byte Issue #59 template normalization contract."""
    predicates = query.get("predicates")
    if not isinstance(predicates, list) or not predicates:
        raise ValueError("query must contain a nonempty predicates list")
    fields: list[tuple[str, str, str]] = []
    for predicate in predicates:
        if not isinstance(predicate, dict):
            raise ValueError("each predicate must be an object")
        column = predicate.get("column")
        operator = predicate.get("operator")
        if not isinstance(column, str) or not isinstance(operator, str):
            raise ValueError("predicate column/operator must be strings")
        fields.append((column, operator, "range" if operator == "[]" else "scalar"))
    return _canonical_json(sorted(fields))


def template_fingerprint(query: dict[str, Any]) -> str:
    return hashlib.sha256(normalized_template(query).encode("utf-8")).hexdigest()


def exact_predicate_fingerprint(query: dict[str, Any]) -> str:
    """Issue #59 ordered canonical predicate tuple fingerprint."""
    predicates = query.get("predicates")
    if not isinstance(predicates, list) or not predicates:
        raise ValueError("query must contain a nonempty predicates list")
    ordered: list[list[Any]] = []
    for predicate in predicates:
        if not isinstance(predicate, dict):
            raise ValueError("each predicate must be an object")
        if not isinstance(predicate.get("column"), str) or not isinstance(
            predicate.get("operator"), str
        ):
            raise ValueError("predicate column/operator must be strings")
        if "value" not in predicate:
            raise ValueError("predicate value is required for exact fingerprint")
        ordered.append([predicate["column"], predicate["operator"], predicate["value"]])
    return hashlib.sha256(_canonical_json(ordered).encode("utf-8")).hexdigest()


def split_for_template(dataset: str, template_sha256: str) -> str:
    if dataset not in DATASETS:
        raise ValueError(f"unknown dataset: {dataset}")
    if len(template_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in template_sha256):
        raise ValueError("template fingerprint must be lowercase SHA-256 hex")
    payload = f"ess-stage2b-split-v1\0{dataset}\0{template_sha256}".encode("utf-8")
    bucket = int.from_bytes(hashlib.sha256(payload).digest()[:8], "big") % 100
    return "calibration" if bucket < 50 else "heldout"


def query_id(dataset: str, split: str, template_sha256: str) -> str:
    if dataset not in DATASETS or split not in SPLITS:
        raise ValueError("invalid dataset/split")
    if len(template_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in template_sha256):
        raise ValueError("template fingerprint must be lowercase SHA-256 hex")
    return f"issue64:{dataset}:{split}:{template_sha256}"


def candidate_priority(dataset: str, seed: int, template_sha256: str) -> str:
    if dataset not in DATASETS or seed < 0:
        raise ValueError("invalid dataset/seed")
    if len(template_sha256) != 64 or any(ch not in "0123456789abcdef" for ch in template_sha256):
        raise ValueError("template fingerprint must be lowercase SHA-256 hex")
    payload = f"ess-stage2b-cohort-priority-v1\0{dataset}\0{seed}\0{template_sha256}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def counter_u64(dataset: str, seed: int, attempt: int, purpose: str, retry: int = 0) -> int:
    if dataset not in DATASETS or seed < 0 or attempt < 0 or retry < 0 or not purpose:
        raise ValueError("invalid counter-PRNG input")
    payload = f"ess-stage2b-cohort-v1\0{dataset}\0{seed}\0{attempt}\0{purpose}\0{retry}"
    return int.from_bytes(hashlib.sha256(payload.encode("utf-8")).digest()[:8], "big")


def randbelow(n: int, dataset: str, seed: int, attempt: int, purpose: str) -> int:
    """Unbiased hash-counter draw in [0,n), with a domain-separated retry."""
    if n <= 0 or n > 2**64:
        raise ValueError("n must be in 1..2^64")
    limit = 2**64 - (2**64 % n)
    retry = 0
    while True:
        value = counter_u64(dataset, seed, attempt, purpose, retry)
        if value < limit:
            return value % n
        retry += 1


def counter_rank(dataset: str, seed: int, attempt: int, purpose: str) -> tuple[int, int]:
    """Sort key for deterministic column/candidate ordering."""
    return (counter_u64(dataset, seed, attempt, purpose), attempt)
