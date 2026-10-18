"""Bounded, offline-safe Forest10 ETL boundary.

This module deliberately does not import the historical AreCEL code and never
deserializes the historical pickle inputs.  The accepted workload input is an
audited, hash-checked JSONL artifact derived outside this module.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import os
import re
import sys
import tarfile
import tempfile
from collections.abc import Iterable
from pathlib import Path, PurePosixPath
from typing import Any

BENCHMARK_ID = "arecel-forest10"
UPSTREAM_URL = "https://github.com/sfu-db/AreCELearnedYet"
UPSTREAM_COMMIT = "aa52da7768023270bad884232972e0b77ec6534a"
ARCHIVE_URL = "https://www.dropbox.com/s/5bmvc1si5hysapf/data.tar.gz?dl=0"
ARCHIVE_SHA256 = "5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79"
CSV_SHA256 = "3484f3037f890f6bae46ae51fb387ee883351119667139c5894654276789a73c"
WORKLOAD_PICKLE_SHA256 = (
    "501a3dcfe82ec5742fce4c3dc3b298eabcf78b82dab3a8ff8ad2914a61f4eaea"
)
LABEL_PICKLE_SHA256 = "34d830e6a30b48228ae41e6ae5643fb199e9794b3f36c915fb742af58fdfb974"
CANONICAL_WORKLOAD_SHA256 = (
    "a922d87660b2dec431a77c2e4a054c4f5528b0f25040859d76d0148a9ed73e74"
)
DERIVED_CANONICAL_FORMAT = "arecel-forest10-derived-canonical-v1"
DERIVED_AUDIT_FORMAT = "arecel-source-audit-derived-canonical-v1"
EXPECTED_ROWS = 581_012
EXPECTED_SPLIT_COUNTS = {"valid": 10_000, "test": 10_000}
SCHEMA_CONTRACT_ID = "arecel-forest10-postgres-schema-v1"
TRANSFORMATION_VERSION = "forest10-etl-v1"
RELATION = "public.forest10"
SOURCE_RELATIONS = frozenset(
    {
        'public."forest10"',
        'public."forest10_original"',
        "public.forest10_original",
        '"forest10_original"',
        '"public"."forest10_original"',
    }
)
SOURCE_COLUMNS = (
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
COLUMNS = tuple((name.lower(), "DOUBLE PRECISION") for name in SOURCE_COLUMNS)
SOURCE_TO_CATALOG = dict(
    zip(SOURCE_COLUMNS, (name for name, _ in COLUMNS), strict=True)
)
EXPECTED_ARCHIVE_MEMBERS = frozenset(
    {
        "data/forest10/original.csv",
        "data/forest10/workload/base.pkl",
        "data/forest10/workload/base-original-label.pkl",
    }
)
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
PROTECTED_PROJECT_NAMES = (
    "ess-advisor",
    "ess-postgresql",
    "extstats-advisor",
    "extstats-advisor-research",
    "postgresql-pgextadv",
)
COUNT_FROM = re.compile(
    r"\A(?P<prefix>\s*SELECT\s+COUNT\s*\(\s*\*\s*\)\s+FROM\s+)"
    r"(?P<relation>[^\s]+)(?P<tail>.*)\Z",
    re.IGNORECASE | re.DOTALL,
)


class InputContractError(ValueError):
    """A supplied source root or artifact violates the versioned contract."""


def _root(value: Path | str | None) -> Path:
    if value is None:
        raise InputContractError(
            "an explicit --data-root is required; no historical or environment default is used"
        )
    root = Path(value).expanduser().resolve()
    if root == Path("/"):
        raise InputContractError("the data root may not be the filesystem root")
    projects_root = Path(__file__).resolve().parents[3].parent
    protected = {(projects_root / name).resolve() for name in PROTECTED_PROJECT_NAMES}
    if any(root == path or path in root.parents for path in protected):
        raise InputContractError(
            "the data root may not be inside another ESS or legacy project"
        )
    return root


def _contained_path(root: Path, path: Path, label: str) -> Path:
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise InputContractError(
            f"{label} resolves outside the explicit data root: {path}"
        ) from exc
    return resolved


def _paths(value: Path | str | None) -> dict[str, Path]:
    root = _root(value)
    forest = root / "arecel" / "raw" / "data" / "forest10"
    audit = root / "arecel" / "audit-v1"
    paths = {
        "root": root,
        "archive": root / "arecel" / "incoming" / "arecel-data.tar.gz",
        "audit": audit / "audit.json",
        "canonical": audit / "forest10.canonical.jsonl.gz",
        "csv": forest / "original.csv",
        "workload_pickle": forest / "workload" / "base.pkl",
        "label_pickle": forest / "workload" / "base-original-label.pkl",
    }
    return {
        name: path if name == "root" else _contained_path(root, path, name)
        for name, path in paths.items()
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except FileNotFoundError as exc:
        raise InputContractError(f"missing required input: {path}") from exc
    return digest.hexdigest()


def schema_contract() -> dict[str, Any]:
    return {
        "id": SCHEMA_CONTRACT_ID,
        "relation": RELATION,
        "source_relation": 'public."forest10_original"',
        "columns": [
            {"source_name": source, "catalog_name": catalog, "postgres_type": type_}
            for source, (catalog, type_) in zip(SOURCE_COLUMNS, COLUMNS, strict=True)
        ],
        "column_count": len(COLUMNS),
        "nullable": True,
        "identifier_contract": "source DDL identifiers fold to lowercase catalog names",
    }


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputContractError(f"missing audit metadata: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputContractError(f"invalid JSON metadata: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise InputContractError(f"audit metadata must be a JSON object: {path}")
    return value


def _require_hex(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise InputContractError(f"{label} must be a 64-character hexadecimal SHA256")
    return value.lower()


def _hash_field(container: Any, keys: tuple[str, ...], label: str) -> str:
    if isinstance(container, str):
        return _require_hex(container, label)
    if not isinstance(container, dict):
        raise InputContractError(f"{label} metadata is missing")
    for key in keys:
        if key in container:
            return _require_hex(container[key], label)
    raise InputContractError(f"{label} metadata is missing")


def _normalise_audit_metadata(audit: dict[str, Any]) -> dict[str, Any]:
    """Normalize the current and pinned historical audit layouts.

    The historical adapter used ``archive_expected_sha256``,
    ``upstream.AreCELearnedYet``, and ``datasets.forest10.{csv,pickles}``.
    These names are accepted only through this explicit, source-pinned
    normalizer; no arbitrary legacy metadata is treated as equivalent.
    """

    if audit.get("format") in {
        "arecel-source-audit-v1",
        DERIVED_AUDIT_FORMAT,
    }:
        upstream = audit.get("upstream")
        archive = audit.get("archive")
        dataset = audit.get("datasets", {}).get(BENCHMARK_ID)
        if not isinstance(upstream, dict) or not isinstance(archive, dict):
            raise InputContractError("current audit metadata is incomplete")
        normalized = {
            "format": audit.get("format"),
            "upstream_commit": upstream.get("commit"),
            "upstream_repository": upstream.get("repository"),
            "archive_sha256": archive.get("sha256"),
            "archive_url": archive.get("url"),
            "dataset": dataset,
        }
    elif "archive_expected_sha256" in audit:
        upstream = audit.get("upstream", {}).get("AreCELearnedYet")
        dataset = audit.get("datasets", {}).get("forest10")
        if not isinstance(upstream, dict) or not isinstance(dataset, dict):
            raise InputContractError("historical audit metadata is incomplete")
        normalized = {
            "format": "historical-arecel-adapter-audit-v1",
            "upstream_commit": upstream.get("commit"),
            "upstream_repository": upstream.get("repository", UPSTREAM_URL),
            "archive_sha256": audit.get("archive_expected_sha256"),
            "archive_url": audit.get("archive_url", ARCHIVE_URL),
            "dataset": dataset,
        }
    elif audit.get("format_version") == "arecel-authoritative-observations-audit-v1":
        if audit.get("benchmark_id") != BENCHMARK_ID:
            raise InputContractError(
                "historical authoritative audit benchmark ID is invalid"
            )
        normalized = {
            "format": "historical-authoritative-observations-audit-v1",
            "upstream_commit": audit.get("upstream_commit"),
            "upstream_repository": audit.get("authority_url", UPSTREAM_URL),
            "archive_sha256": ARCHIVE_SHA256,
            "archive_url": ARCHIVE_URL,
            "dataset": {
                "csv": {"sha256": CSV_SHA256, "rows": EXPECTED_ROWS},
                "workload": {
                    "pickle_sha256": audit.get("source_workload_pickle_sha256"),
                    "label_pickle_sha256": audit.get("source_label_pickle_sha256"),
                    "canonical_sha256": audit.get("canonical_workload_sha256"),
                },
                "schema_contract_id": SCHEMA_CONTRACT_ID,
            },
        }
    else:
        raise InputContractError(
            "audit metadata is neither the current nor the pinned historical format"
        )

    if normalized["upstream_commit"] != UPSTREAM_COMMIT:
        raise InputContractError(
            "audit upstream commit does not match the frozen contract"
        )
    if normalized["upstream_repository"] != UPSTREAM_URL:
        raise InputContractError(
            "audit upstream repository does not match the frozen contract"
        )
    if normalized["archive_url"] != ARCHIVE_URL:
        raise InputContractError("audit archive URL is not the pinned source URL")
    if (
        _require_hex(normalized["archive_sha256"], "audit archive SHA256")
        != ARCHIVE_SHA256
    ):
        raise InputContractError(
            "audit archive SHA256 does not match the frozen contract"
        )

    dataset = normalized["dataset"]
    if not isinstance(dataset, dict):
        raise InputContractError("audit Forest10 dataset metadata is missing")
    csv_metadata = dataset.get("csv")
    if (
        _hash_field(csv_metadata, ("sha256", "expected_sha256"), "audit CSV SHA256")
        != CSV_SHA256
    ):
        raise InputContractError(
            "audit Forest10 CSV SHA256 does not match the frozen contract"
        )
    csv_rows = csv_metadata.get("rows") if isinstance(csv_metadata, dict) else None
    if csv_rows is None:
        csv_rows = dataset.get("rows", dataset.get("row_count"))
    if csv_rows != EXPECTED_ROWS:
        raise InputContractError(
            "audit Forest10 row count does not match the frozen contract"
        )

    if normalized["format"] in {
        "arecel-source-audit-v1",
        "historical-authoritative-observations-audit-v1",
        DERIVED_AUDIT_FORMAT,
    }:
        workload = dataset.get("workload")
        workload_hashes = (
            _hash_field(workload, ("pickle_sha256",), "audit workload pickle SHA256"),
            _hash_field(
                workload, ("label_pickle_sha256",), "audit label pickle SHA256"
            ),
            _hash_field(
                workload, ("canonical_sha256",), "audit canonical workload SHA256"
            ),
        )
        schema_id = dataset.get("schema_contract_id")
    else:
        pickles = dataset.get("pickles")
        workload_hashes = (
            _hash_field(
                pickles,
                ("workload", "base", "base.pkl", "workload_pickle_sha256"),
                "audit workload pickle SHA256",
            ),
            _hash_field(
                pickles,
                (
                    "label",
                    "base-original-label",
                    "base-original-label.pkl",
                    "label_pickle_sha256",
                ),
                "audit label pickle SHA256",
            ),
            _hash_field(
                pickles,
                (
                    "canonical",
                    "canonical_workload",
                    "canonical_sha256",
                    "canonical_workload_sha256",
                ),
                "audit canonical workload SHA256",
            ),
        )
        schema_id = dataset.get("schema_contract_id", SCHEMA_CONTRACT_ID)
    canonical_sha256 = workload_hashes[2]
    if normalized["format"] == DERIVED_AUDIT_FORMAT:
        workload = dataset.get("workload")
        if not isinstance(workload, dict):
            raise InputContractError("derived canonical workload metadata is missing")
        if workload.get("canonical_format") != DERIVED_CANONICAL_FORMAT:
            raise InputContractError(
                "derived canonical workload format is not the pinned version"
            )
        if (
            _hash_field(
                workload,
                ("historical_canonical_sha256",),
                "historical canonical workload SHA256",
            )
            != CANONICAL_WORKLOAD_SHA256
        ):
            raise InputContractError(
                "historical canonical workload SHA256 reference is invalid"
            )
        conversion = workload.get("conversion")
        if (
            not isinstance(conversion, dict)
            or conversion.get("format") != DERIVED_CANONICAL_FORMAT
        ):
            raise InputContractError(
                "derived canonical conversion provenance is missing"
            )
    elif canonical_sha256 != CANONICAL_WORKLOAD_SHA256:
        raise InputContractError(
            "audit workload artifact hashes do not match the frozen contract"
        )
    if workload_hashes[:2] != (WORKLOAD_PICKLE_SHA256, LABEL_PICKLE_SHA256):
        raise InputContractError(
            "audit workload artifact hashes do not match the frozen contract"
        )
    if schema_id != SCHEMA_CONTRACT_ID:
        raise InputContractError(
            "audit schema contract does not match the frozen contract"
        )
    normalized["canonical_sha256"] = canonical_sha256
    normalized["canonical_format"] = (
        dataset.get("workload", {}).get("canonical_format", "historical-canonical-v1")
        if isinstance(dataset.get("workload"), dict)
        else "historical-canonical-v1"
    )
    normalized["historical_canonical_sha256"] = (
        dataset.get("workload", {}).get("historical_canonical_sha256")
        if normalized["format"] == DERIVED_AUDIT_FORMAT
        and isinstance(dataset.get("workload"), dict)
        else CANONICAL_WORKLOAD_SHA256
    )
    return normalized


def _audit_metadata(path: Path) -> dict[str, Any]:
    return _normalise_audit_metadata(_read_json(path))


def _archive_members(path: Path) -> list[str]:
    try:
        with tarfile.open(path, mode="r:*") as archive:
            names: list[str] = []
            for member in archive.getmembers():
                pure = PurePosixPath(member.name)
                if pure.is_absolute() or ".." in pure.parts:
                    raise InputContractError(
                        f"unsafe archive member path: {member.name}"
                    )
                names.append(pure.as_posix())
    except (FileNotFoundError, tarfile.TarError) as exc:
        raise InputContractError(f"invalid or missing source archive: {path}") from exc
    if not EXPECTED_ARCHIVE_MEMBERS.issubset(names):
        missing = sorted(EXPECTED_ARCHIVE_MEMBERS.difference(names))
        raise InputContractError(f"source archive is incomplete; missing {missing}")
    return sorted(names)


def _csv_metadata(
    path: Path, expected_rows: int, expected_sha256: str | None
) -> dict[str, Any]:
    actual_sha256 = sha256_file(path)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise InputContractError(
            f"CSV SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    null_counts = [0] * len(SOURCE_COLUMNS)
    rows = 0
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            if header != list(SOURCE_COLUMNS):
                raise InputContractError(
                    "Forest10 CSV header/order does not match the contract"
                )
            for row in reader:
                rows += 1
                if len(row) != len(SOURCE_COLUMNS):
                    raise InputContractError(
                        f"Forest10 CSV row {rows} has {len(row)} columns"
                    )
                for index, value in enumerate(row):
                    if value == "":
                        null_counts[index] += 1
                    else:
                        try:
                            parsed = float(value)
                        except ValueError as exc:
                            raise InputContractError(
                                f"Forest10 CSV row {rows} column {SOURCE_COLUMNS[index]} "
                                "is not a PostgreSQL DOUBLE PRECISION literal"
                            ) from exc
                        if math.isnan(parsed) or math.isinf(parsed):
                            raise InputContractError(
                                f"Forest10 CSV row {rows} column {SOURCE_COLUMNS[index]} "
                                "is non-finite"
                            )
    except StopIteration as exc:
        raise InputContractError("Forest10 CSV is missing its header") from exc
    if rows != expected_rows:
        raise InputContractError(f"expected {expected_rows} Forest10 rows, got {rows}")
    return {
        "sha256": actual_sha256,
        "rows": rows,
        "columns": len(SOURCE_COLUMNS),
        "null_counts": dict(zip(SOURCE_COLUMNS, null_counts, strict=True)),
    }


def _rewrite_sql_identifiers(sql: str) -> str:
    """Rewrite only delimited identifiers outside literals and comments."""

    output: list[str] = []
    state = "normal"
    block_depth = 0
    dollar_delimiter = ""
    index = 0
    while index < len(sql):
        character = sql[index]
        next_character = sql[index + 1] if index + 1 < len(sql) else ""
        if state == "single":
            output.append(character)
            if character == "\\" and next_character:
                output.append(next_character)
                index += 2
                continue
            if character == "'":
                if next_character == "'":
                    output.append(next_character)
                    index += 2
                    continue
                state = "normal"
            index += 1
            continue
        if state == "line-comment":
            output.append(character)
            index += 1
            if character == "\n":
                state = "normal"
            continue
        if state == "block-comment":
            if sql.startswith("/*", index):
                output.append("/*")
                block_depth += 1
                index += 2
            elif sql.startswith("*/", index):
                output.append("*/")
                block_depth -= 1
                index += 2
                if block_depth == 0:
                    state = "normal"
            else:
                output.append(character)
                index += 1
            continue
        if state == "dollar-quote":
            end = sql.find(dollar_delimiter, index)
            if end == -1:
                raise InputContractError("unterminated dollar-quoted SQL string")
            output.append(sql[index : end + len(dollar_delimiter)])
            index = end + len(dollar_delimiter)
            state = "normal"
            dollar_delimiter = ""
            continue
        if sql.startswith("--", index):
            output.append("--")
            state = "line-comment"
            index += 2
            continue
        if sql.startswith("/*", index):
            output.append("/*")
            state = "block-comment"
            block_depth = 1
            index += 2
            continue
        if character == "'":
            output.append(character)
            state = "single"
            index += 1
            continue
        if character == "$":
            dollar_match = re.match(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$", sql[index:])
            if dollar_match is not None:
                dollar_delimiter = dollar_match.group(0)
                output.append(dollar_delimiter)
                index += len(dollar_delimiter)
                state = "dollar-quote"
                continue
        if character != '"':
            output.append(character)
            index += 1
            continue

        identifier: list[str] = []
        index += 1
        while index < len(sql):
            character = sql[index]
            next_character = sql[index + 1] if index + 1 < len(sql) else ""
            if character == '"':
                if next_character == '"':
                    identifier.append('"')
                    index += 2
                    continue
                break
            if character in "\r\n":
                raise InputContractError("unterminated quoted SQL identifier")
            identifier.append(character)
            index += 1
        if index >= len(sql) or sql[index] != '"':
            raise InputContractError("unterminated quoted SQL identifier")
        source_name = "".join(identifier)
        if source_name not in SOURCE_TO_CATALOG:
            raise InputContractError(
                f"quoted SQL identifier is outside the Forest10 schema: {source_name}"
            )
        output.append('"' + SOURCE_TO_CATALOG[source_name] + '"')
        index += 1

    if state == "single":
        raise InputContractError("unterminated SQL string literal")
    if state == "block-comment":
        raise InputContractError("unterminated SQL block comment")
    if state == "dollar-quote":
        raise InputContractError("unterminated dollar-quoted SQL string")
    return "".join(output)


def adapt_query_sql(source_sql: str) -> str:
    """Convert audited COUNT truth SQL to SELECT * estimator SQL.

    Only the leading projection, audited relation identity, and quoted source
    column identifiers are changed.  Predicate text, literal values,
    operators, whitespace after the relation, and statement terminators are
    otherwise preserved.
    """

    if not isinstance(source_sql, str) or not source_sql.strip():
        raise InputContractError("source SQL must be a non-empty string")
    match = COUNT_FROM.match(source_sql)
    if match is None or match.group("relation") not in SOURCE_RELATIONS:
        raise InputContractError(
            "source SQL must begin with COUNT(*) FROM the audited relation"
        )
    tail = match.group("tail")
    projected = "SELECT * FROM " + RELATION + tail
    return _rewrite_sql_identifiers(projected)


def _canonical_records(
    path: Path, expected_sha256: str | None = None
) -> list[dict[str, Any]]:
    actual_sha256 = sha256_file(path)
    if expected_sha256 is not None and actual_sha256 != expected_sha256:
        raise InputContractError(
            f"canonical workload SHA256 mismatch: expected {expected_sha256}, got {actual_sha256}"
        )
    records: list[dict[str, Any]] = []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    raise InputContractError(
                        f"blank canonical workload line {line_number}"
                    )
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise InputContractError(
                        f"invalid canonical workload JSON at line {line_number}"
                    ) from exc
                if not isinstance(record, dict):
                    raise InputContractError(
                        f"canonical workload line {line_number} is not an object"
                    )
                split = record.get("split")
                if split not in EXPECTED_SPLIT_COUNTS:
                    raise InputContractError(
                        f"invalid Forest10 split at line {line_number}"
                    )
                index = record.get("index")
                if not isinstance(index, int) or isinstance(index, bool) or index < 0:
                    raise InputContractError(
                        f"invalid source index at line {line_number}"
                    )
                expected_id = f"arecel:forest10:{split}:{index:06d}"
                if record.get("query_id") != expected_id:
                    raise InputContractError(
                        f"query ID/index mismatch at line {line_number}"
                    )
                source_sql = record.get("sql")
                adapted_sql = adapt_query_sql(source_sql)
                label = record.get("source_label")
                if not isinstance(label, dict):
                    raise InputContractError(
                        f"missing source label at line {line_number}"
                    )
                truth = label.get("cardinality")
                if not isinstance(truth, int) or isinstance(truth, bool) or truth < 0:
                    raise InputContractError(
                        f"truth cardinality is not an exact nonnegative integer at line {line_number}"
                    )
                source_query_hash = _require_hex(
                    record.get("source_query_sha256"),
                    f"source query hash at line {line_number}",
                )
                source_query = record.get("source_query")
                if not isinstance(source_query, dict):
                    raise InputContractError(
                        f"source query provenance is missing at line {line_number}"
                    )
                weight = record.get("weight", 1.0)
                if not isinstance(weight, (int, float)) or isinstance(weight, bool):
                    raise InputContractError(
                        f"query weight is invalid at line {line_number}"
                    )
                try:
                    numeric_weight = float(weight)
                except (OverflowError, ValueError) as exc:
                    raise InputContractError(
                        f"query weight is invalid at line {line_number}"
                    ) from exc
                if not math.isfinite(numeric_weight) or numeric_weight <= 0:
                    raise InputContractError(
                        f"query weight must be finite and positive at line {line_number}"
                    )
                records.append(
                    {
                        "source_index": index,
                        "split": split,
                        "query_id": expected_id,
                        "source_sql": source_sql,
                        "estimator_sql": adapted_sql,
                        "source_query": source_query,
                        "source_query_sha256": source_query_hash,
                        "source_label": label,
                        "true_cardinality": truth,
                        "weight": numeric_weight,
                    }
                )
    except (OSError, EOFError) as exc:
        raise InputContractError(
            f"cannot read canonical workload gzip: {path}"
        ) from exc
    return records


def _validate_split(records: list[dict[str, Any]], split: str) -> list[dict[str, Any]]:
    selected = [record for record in records if record["split"] == split]
    if len(selected) != EXPECTED_SPLIT_COUNTS[split]:
        raise InputContractError(
            f"expected {EXPECTED_SPLIT_COUNTS[split]} Forest10 {split} queries, got {len(selected)}"
        )
    indices = [record["source_index"] for record in selected]
    if indices != list(range(EXPECTED_SPLIT_COUNTS[split])):
        raise InputContractError(
            f"Forest10 {split} query order is not contiguous and deterministic"
        )
    ids = [record["query_id"] for record in selected]
    if len(ids) != len(set(ids)):
        raise InputContractError(f"duplicate Forest10 {split} query IDs")
    return selected


def validate_source(data_root: Path | str | None) -> dict[str, Any]:
    """Validate all declared Forest10 source inputs without deserializing pickles."""

    paths = _paths(data_root)
    audit = _audit_metadata(paths["audit"])
    archive_sha256 = sha256_file(paths["archive"])
    if archive_sha256 != ARCHIVE_SHA256:
        raise InputContractError(
            f"archive SHA256 mismatch: expected {ARCHIVE_SHA256}, got {archive_sha256}"
        )
    archive_members = _archive_members(paths["archive"])
    csv = _csv_metadata(paths["csv"], EXPECTED_ROWS, CSV_SHA256)
    source_hashes = {
        "csv": csv["sha256"],
        "workload_pickle": sha256_file(paths["workload_pickle"]),
        "label_pickle": sha256_file(paths["label_pickle"]),
        "canonical_workload": sha256_file(paths["canonical"]),
    }
    expected_hashes = {
        "workload_pickle": WORKLOAD_PICKLE_SHA256,
        "label_pickle": LABEL_PICKLE_SHA256,
        "canonical_workload": audit["canonical_sha256"],
    }
    for name, expected in expected_hashes.items():
        if source_hashes[name] != expected:
            raise InputContractError(
                f"{name} SHA256 mismatch: expected {expected}, got {source_hashes[name]}"
            )
    records = _canonical_records(paths["canonical"], audit["canonical_sha256"])
    split_records = {
        split: _validate_split(records, split) for split in EXPECTED_SPLIT_COUNTS
    }
    return {
        "format": "arecel-source-validation-v1",
        "benchmark_id": BENCHMARK_ID,
        "source_present": True,
        "input_root_logical": "<explicit-data-root>",
        "upstream": {
            "repository": UPSTREAM_URL,
            "commit": UPSTREAM_COMMIT,
            "license": "MIT (upstream repository LICENSE at pinned commit)",
        },
        "archive": {
            "url": ARCHIVE_URL,
            "sha256": archive_sha256,
            "members": archive_members,
        },
        "schema_contract": schema_contract(),
        "csv": csv,
        "source_file_sha256": source_hashes,
        "canonical_workload_format": audit["canonical_format"],
        "historical_canonical_workload_sha256": audit["historical_canonical_sha256"],
        "split_counts": {split: len(rows) for split, rows in split_records.items()},
        "audit_metadata_sha256": sha256_file(paths["audit"]),
        "transformation_version": TRANSFORMATION_VERSION,
    }


def inspect_source(data_root: Path | str | None) -> dict[str, Any]:
    """Return a report, including a concrete blocker for absent inputs."""

    paths = _paths(data_root)
    missing = [
        str(path.relative_to(paths["root"]))
        for path in paths.values()
        if path != paths["root"] and not path.is_file()
    ]
    result: dict[str, Any] = {
        "format": "arecel-forest10-inspection-v1",
        "benchmark_id": BENCHMARK_ID,
        "source_present": not missing,
        "missing_inputs": missing,
        "input_root_logical": "<explicit-data-root>",
        "upstream_commit": UPSTREAM_COMMIT,
        "archive_sha256": ARCHIVE_SHA256,
        "csv_sha256": CSV_SHA256,
        "expected_rows": EXPECTED_ROWS,
        "expected_split_counts": EXPECTED_SPLIT_COUNTS,
        "schema_contract": schema_contract(),
    }
    if not missing:
        result["validation"] = validate_source(data_root)
    else:
        result["status"] = "BLOCKED_MISSING_INPUT"
    return result


def _source_contract(validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "benchmark_id": BENCHMARK_ID,
        "upstream_url": UPSTREAM_URL,
        "upstream_commit": UPSTREAM_COMMIT,
        "archive_url": ARCHIVE_URL,
        "archive_sha256": validation["archive"]["sha256"],
        "source_file_sha256": validation["source_file_sha256"],
        "schema_contract_id": SCHEMA_CONTRACT_ID,
        "canonical_workload_format": validation["canonical_workload_format"],
        "historical_canonical_workload_sha256": validation[
            "historical_canonical_workload_sha256"
        ],
        "transformation_version": TRANSFORMATION_VERSION,
    }


def _workload_artifact(
    records: list[dict[str, Any]], validation: dict[str, Any], split: str
) -> dict[str, Any]:
    return {
        "format": "cardinality-workload-v1",
        "workload_id": f"arecel_forest10_{split}_v1",
        "split": split,
        "source_contract": _source_contract(validation),
        "queries": [
            {
                "query_id": f"arecel_forest10_{split}_{record['source_index']:06d}",
                "source_query_id": record["query_id"],
                "source_index": record["source_index"],
                "source_sql": record["source_sql"],
                "estimator_sql": record["estimator_sql"],
                "source_query_sha256": record["source_query_sha256"],
                "weight": record["weight"],
            }
            for record in records
        ],
    }


def _truth_artifact(
    records: list[dict[str, Any]], validation: dict[str, Any], split: str
) -> dict[str, Any]:
    return {
        "format": "cardinality-truth-v1",
        "truth_id": f"arecel_forest10_{split}_truth_v1",
        "split": split,
        "source_contract": _source_contract(validation),
        "truth_provenance": {
            "authority": "AreCELearnedYet source_label.cardinality",
            "representation": "exact nonnegative JSON integer",
            "count_sql_is_preserved_as_source_sql": True,
        },
        "truth": [
            {
                "query_id": f"arecel_forest10_{split}_{record['source_index']:06d}",
                "source_query_id": record["query_id"],
                "source_index": record["source_index"],
                "truth_sql": record["source_sql"],
                "true_cardinality": record["true_cardinality"],
                "source_label": record["source_label"],
                "source_query_sha256": record["source_query_sha256"],
            }
            for record in records
        ],
    }


def _write_json(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_artifacts(
    data_root: Path | str | None,
    output_dir: Path | str,
    split: str = "test",
) -> dict[str, Any]:
    """Build workload, truth, and manifest artifacts without overwriting output."""

    if split not in EXPECTED_SPLIT_COUNTS:
        raise InputContractError("split must be valid or test")
    validation = validate_source(data_root)
    paths = _paths(data_root)
    records = _validate_split(
        _canonical_records(
            paths["canonical"], validation["source_file_sha256"]["canonical_workload"]
        ),
        split,
    )
    output = Path(output_dir).expanduser().resolve(strict=False)
    try:
        relative_output = output.relative_to(_root(data_root))
    except ValueError as exc:
        raise InputContractError(
            "output directory must be inside the explicit data root"
        ) from exc
    if not relative_output.parts or relative_output.parts[0] not in {
        "etl-output",
        "experiment-data",
    }:
        raise InputContractError(
            "output directory must be under data-root/etl-output or data-root/experiment-data"
        )
    if output.exists():
        raise InputContractError(
            f"refusing to overwrite existing output directory: {output}"
        )
    output.mkdir(parents=True, exist_ok=False)
    workload = _workload_artifact(records, validation, split)
    truth = _truth_artifact(records, validation, split)
    workload_path = output / "workload.json"
    truth_path = output / "truth.json"
    manifest_path = output / "manifest.json"
    _write_json(workload_path, workload)
    _write_json(truth_path, truth)
    manifest = {
        "format": "arecel-forest10-etl-manifest-v1",
        "benchmark_id": BENCHMARK_ID,
        "split": split,
        "transformation_version": TRANSFORMATION_VERSION,
        "schema_contract": schema_contract(),
        "source_contract": _source_contract(validation),
        "csv_identity": {
            "sha256": validation["csv"]["sha256"],
            "rows": validation["csv"]["rows"],
            "columns": validation["csv"]["columns"],
        },
        "record_count": len(records),
        "workload_artifact": {
            "path": "workload.json",
            "sha256": sha256_file(workload_path),
        },
        "truth_artifact": {"path": "truth.json", "sha256": sha256_file(truth_path)},
        "truth_is_not_in_workload": True,
    }
    _write_json(manifest_path, manifest)
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect")
    inspect_parser.add_argument("--data-root", type=Path, required=True)
    build_parser = subparsers.add_parser("build")
    build_parser.add_argument("--data-root", type=Path, required=True)
    build_parser.add_argument("--output-dir", type=Path, required=True)
    build_parser.add_argument(
        "--split", choices=sorted(EXPECTED_SPLIT_COUNTS), default="test"
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "inspect":
            result = inspect_source(args.data_root)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["source_present"] else 2
        result = build_artifacts(args.data_root, args.output_dir, args.split)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except InputContractError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
