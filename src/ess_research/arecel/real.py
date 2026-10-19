"""Validated ETL for the three non-Forest10 AreCEL real datasets.

The normal path treats the two upstream pickle files as opaque, hash-checked
bytes.  A separate, explicitly gated converter creates a derived canonical
JSONL artifact; this module only consumes that canonical artifact and never
deserializes pickle data.
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
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

UPSTREAM_URL = "https://github.com/sfu-db/AreCELearnedYet"
UPSTREAM_COMMIT = "aa52da7768023270bad884232972e0b77ec6534a"
ARCHIVE_URL = "https://www.dropbox.com/s/5bmvc1si5hysapf/data.tar.gz?dl=0"
ARCHIVE_SHA256 = "5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79"
DERIVED_CANONICAL_FORMAT = "arecel-derived-canonical-v1"
AUDIT_FORMAT = "arecel-source-audit-derived-canonical-v1"
TRANSFORMATION_VERSION = "arecel-real-etl-v1"
# The pinned AreCEL workload roots contain a 100,000-query train split in
# addition to the 10,000-query valid and test splits.  The ETL must not silently
# discard an observed split; downstream experiments may choose their split.
SPLITS = ("train", "valid", "test")
SUPPORTED_OPERATORS = {"=", "<", "<=", ">", ">=", "[]"}
HEX64 = re.compile(r"^[0-9a-fA-F]{64}$")
COUNT_FROM = re.compile(
    r"\A(?P<prefix>\s*SELECT\s+COUNT\s*\(\s*\*\s*\)\s+FROM\s+)"
    r"(?P<relation>[^\s]+)(?P<tail>.*)\Z",
    re.IGNORECASE | re.DOTALL,
)


@dataclass(frozen=True)
class DatasetSpec:
    slug: str
    benchmark_id: str
    relation: str
    source_relation: str
    source_relations: frozenset[str]
    expected_rows: int
    csv_sha256: str
    workload_pickle_sha256: str
    label_pickle_sha256: str
    historical_canonical_sha256: str
    schema_contract_id: str
    source_columns: tuple[str, ...]
    columns: tuple[tuple[str, str], ...]
    not_null: bool


SPECS: dict[str, DatasetSpec] = {
    "census13": DatasetSpec(
        slug="census13",
        benchmark_id="arecel-census13",
        relation="public.census13",
        source_relation="public.census13",
        source_relations=frozenset({"public.census13", 'public."census13"'}),
        expected_rows=48_842,
        csv_sha256="f751fc7ecd5bd5e62acd9868a0bbe36413528b6eb2de9c2fc8fcf71d9ef2c13a",
        workload_pickle_sha256="492faa529ecc6b212733602fd140a42182439a89d22bcf9c8e8b82db1a5154ba",
        label_pickle_sha256="5fd6d187830681b16b3c561f7d0a2a014a7fdbabfa1579db655de8131b0ba451",
        historical_canonical_sha256="9bcfc868effee9a796fff08454eeb85f135049e862ee0eb2dd801831d7df9388",
        schema_contract_id="arecel-census13-postgres-schema-v1",
        source_columns=(
            "age",
            "workclass",
            "education",
            "education_num",
            "marital_status",
            "occupation",
            "relationship",
            "race",
            "sex",
            "capital_gain",
            "capital_loss",
            "hours_per_week",
            "native_country",
        ),
        columns=(
            ("age", "DOUBLE PRECISION"),
            ("workclass", "VARCHAR(64)"),
            ("education", "VARCHAR(64)"),
            ("education_num", "DOUBLE PRECISION"),
            ("marital_status", "VARCHAR(64)"),
            ("occupation", "VARCHAR(64)"),
            ("relationship", "VARCHAR(64)"),
            ("race", "VARCHAR(64)"),
            ("sex", "VARCHAR(64)"),
            ("capital_gain", "DOUBLE PRECISION"),
            ("capital_loss", "DOUBLE PRECISION"),
            ("hours_per_week", "DOUBLE PRECISION"),
            ("native_country", "VARCHAR(64)"),
        ),
        not_null=True,
    ),
    "dmv11": DatasetSpec(
        slug="dmv11",
        benchmark_id="arecel-dmv11",
        relation="public.dmv11",
        source_relation='public."dmv11_original"',
        source_relations=frozenset(
            {
                'public."dmv11_original"',
                'public."dmv11"',
                "public.dmv11_original",
                "public.dmv11",
            }
        ),
        expected_rows=11_591_877,
        csv_sha256="ae310972b7ac08629d135a1da7c580e3fe603bfc2e665e1969005bd481d4605a",
        workload_pickle_sha256="e37136725ace8f60a6dfcf55529da328ab202d74988538726cff8589ccec65dc",
        label_pickle_sha256="14b29cc7f28aab5dd85f3bec2e49fe841d4194b7417dcc881459a1d9d9f98d65",
        historical_canonical_sha256="71bb6e3c61da5ab1096cc52d41e7f696d486e4a3ba1c4586c01119df26fe9f40",
        schema_contract_id="arecel-dmv11-postgres-schema-v1",
        source_columns=(
            "Record_Type",
            "Registration_Class",
            "State",
            "County",
            "Body_Type",
            "Fuel_Type",
            "Reg_Valid_Date",
            "Color",
            "Scofflaw_Indicator",
            "Suspension_Indicator",
            "Revocation_Indicator",
        ),
        columns=(
            ("record_type", "VARCHAR(64)"),
            ("registration_class", "VARCHAR(64)"),
            ("state", "VARCHAR(64)"),
            ("county", "VARCHAR(64)"),
            ("body_type", "VARCHAR(64)"),
            ("fuel_type", "VARCHAR(64)"),
            ("reg_valid_date", "DOUBLE PRECISION"),
            ("color", "VARCHAR(64)"),
            ("scofflaw_indicator", "VARCHAR(64)"),
            ("suspension_indicator", "VARCHAR(64)"),
            ("revocation_indicator", "VARCHAR(64)"),
        ),
        not_null=False,
    ),
    "power7": DatasetSpec(
        slug="power7",
        benchmark_id="arecel-power7",
        relation="public.power7",
        source_relation='public."power7"',
        source_relations=frozenset({'public."power7"', "public.power7"}),
        expected_rows=2_075_259,
        csv_sha256="a58a43b0e9f26e92744c2130053dd343fb6b3bb9f73b05fd39f6a44d355ddba9",
        workload_pickle_sha256="1f270912f529e362545b6da519492a5aff63bdc65ecc10f71674e5779a7247a5",
        label_pickle_sha256="d7369b34d2ddc866dbb16c3b2f5147cb10a86832dba54c905ef400bc3514cdf5",
        historical_canonical_sha256="9f1b11d72bcefe9d76cd83b1f995a6d6f4e0922434975550e2d5783425152327",
        schema_contract_id="arecel-power7-postgres-schema-v1",
        source_columns=(
            "Global_active_power",
            "Global_reactive_power",
            "Voltage",
            "Global_intensity",
            "Sub_metering_1",
            "Sub_metering_2",
            "Sub_metering_3",
        ),
        columns=(
            ("global_active_power", "DOUBLE PRECISION"),
            ("global_reactive_power", "DOUBLE PRECISION"),
            ("voltage", "DOUBLE PRECISION"),
            ("global_intensity", "DOUBLE PRECISION"),
            ("sub_metering_1", "DOUBLE PRECISION"),
            ("sub_metering_2", "DOUBLE PRECISION"),
            ("sub_metering_3", "DOUBLE PRECISION"),
        ),
        not_null=False,
    ),
}


class InputContractError(ValueError):
    """A supplied source root or artifact violates the frozen contract."""


def spec_for(value: str) -> DatasetSpec:
    try:
        return SPECS[value]
    except KeyError as exc:
        raise InputContractError(f"unsupported AreCEL dataset: {value}") from exc


def _root(value: Path | str | None) -> Path:
    if value is None:
        value = os.environ.get("ESS_DATA_ROOT")
    if value is None or not str(value).strip():
        raise InputContractError(
            "provide --data-root or ESS_DATA_ROOT; no other default is used"
        )
    root = Path(value).expanduser().resolve()
    if root == Path("/"):
        raise InputContractError("the data root may not be the filesystem root")
    projects_root = Path(__file__).resolve().parents[3].parent
    protected_names = {
        "ess-advisor",
        "ess-postgresql",
        "extstats-advisor",
        "extstats-advisor-research",
        "postgresql-pgextadv",
    }
    protected = {(projects_root / name).resolve() for name in protected_names}
    if any(root == path or path in root.parents for path in protected):
        raise InputContractError("the data root may not be inside another project")
    return root


def _contained(root: Path, path: Path, label: str) -> Path:
    resolved = path.resolve(strict=False)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise InputContractError(
            f"{label} resolves outside the explicit data root"
        ) from exc
    return resolved


def paths(data_root: Path | str | None, spec: DatasetSpec) -> dict[str, Path]:
    root = _root(data_root)
    source = root / "arecel" / "raw" / "data" / spec.slug
    raw_paths = {
        "root": root,
        "archive": root / "arecel" / "incoming" / "arecel-data.tar.gz",
        "audit": root / "arecel" / "audit-v1" / "audit.json",
        "canonical": root / "arecel" / "audit-v1" / f"{spec.slug}.canonical.jsonl.gz",
        "csv": source / "original.csv",
        "workload_pickle": source / "workload" / "base.pkl",
        "label_pickle": source / "workload" / "base-original-label.pkl",
    }
    return {
        key: value if key == "root" else _contained(root, value, key)
        for key, value in raw_paths.items()
    }


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
    except FileNotFoundError as exc:
        raise InputContractError(f"missing required input: {path}") from exc
    return digest.hexdigest()


def schema_contract(spec: DatasetSpec) -> dict[str, Any]:
    return {
        "id": spec.schema_contract_id,
        "relation": spec.relation,
        "columns": [
            {"source_name": source, "catalog_name": catalog, "postgres_type": type_}
            for source, (catalog, type_) in zip(
                spec.source_columns, spec.columns, strict=True
            )
        ],
        "column_count": len(spec.columns),
        "not_null": spec.not_null,
        "identifier_contract": (
            "source identifiers fold to lowercase catalog names"
            if spec.slug != "census13"
            else "source identifiers are already lowercase catalog names"
        ),
    }


def _require_hex(value: Any, label: str) -> str:
    if not isinstance(value, str) or HEX64.fullmatch(value) is None:
        raise InputContractError(f"{label} must be a 64-character hexadecimal SHA256")
    return value.lower()


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise InputContractError(f"missing audit metadata: {path}") from exc
    except json.JSONDecodeError as exc:
        raise InputContractError(f"invalid audit metadata: {path}") from exc
    if not isinstance(value, dict):
        raise InputContractError("audit metadata must be a JSON object")
    return value


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
                if not (member.isdir() or member.isreg()):
                    raise InputContractError(
                        f"archive member is not a directory or regular file: {member.name}"
                    )
                names.append(pure.as_posix())
    except (FileNotFoundError, tarfile.TarError) as exc:
        raise InputContractError(f"invalid or missing source archive: {path}") from exc
    required = {f"data/{slug}/original.csv" for slug in SPECS} | {
        f"data/{slug}/workload/{name}"
        for slug in SPECS
        for name in ("base.pkl", "base-original-label.pkl")
    }
    missing = sorted(required.difference(names))
    if missing:
        raise InputContractError(f"source archive is incomplete; missing {missing}")
    return sorted(names)


def _csv_metadata(path: Path, spec: DatasetSpec) -> dict[str, Any]:
    actual = sha256_file(path)
    if actual != spec.csv_sha256:
        raise InputContractError(
            f"{spec.slug} CSV SHA256 mismatch: expected {spec.csv_sha256}, got {actual}"
        )
    null_counts = [0] * len(spec.source_columns)
    rows = 0
    try:
        with path.open("r", encoding="utf-8", newline="") as stream:
            reader = csv.reader(stream)
            header = next(reader)
            if header != list(spec.source_columns):
                raise InputContractError(f"{spec.slug} CSV header/order mismatch")
            numeric_indexes = {
                index
                for index, (_, type_) in enumerate(spec.columns)
                if type_ == "DOUBLE PRECISION"
            }
            for row in reader:
                rows += 1
                if len(row) != len(spec.source_columns):
                    raise InputContractError(
                        f"{spec.slug} CSV row {rows} has {len(row)} columns"
                    )
                for index, value in enumerate(row):
                    if value == "":
                        null_counts[index] += 1
                        if spec.not_null:
                            raise InputContractError(
                                f"{spec.slug} CSV row {rows} contains a NULL in a not-null column"
                            )
                    elif index in numeric_indexes:
                        try:
                            parsed = float(value)
                        except ValueError as exc:
                            raise InputContractError(
                                f"{spec.slug} CSV numeric value is invalid at row {rows}"
                            ) from exc
                        if not math.isfinite(parsed):
                            raise InputContractError(
                                f"{spec.slug} CSV numeric value is non-finite at row {rows}"
                            )
    except StopIteration as exc:
        raise InputContractError(f"{spec.slug} CSV is missing its header") from exc
    if rows != spec.expected_rows:
        raise InputContractError(
            f"expected {spec.expected_rows} {spec.slug} rows, got {rows}"
        )
    return {
        "sha256": actual,
        "rows": rows,
        "columns": len(spec.source_columns),
        "null_counts": dict(zip(spec.source_columns, null_counts, strict=True)),
    }


def _audit_dataset(audit: dict[str, Any], spec: DatasetSpec) -> dict[str, Any]:
    if audit.get("format") != AUDIT_FORMAT:
        raise InputContractError("audit format is not the derived-canonical contract")
    upstream = audit.get("upstream")
    archive = audit.get("archive")
    if not isinstance(upstream, dict) or upstream.get("commit") != UPSTREAM_COMMIT:
        raise InputContractError(
            "audit upstream commit does not match the frozen contract"
        )
    if upstream.get("repository") != UPSTREAM_URL:
        raise InputContractError(
            "audit upstream repository does not match the frozen contract"
        )
    if not isinstance(archive, dict) or archive.get("sha256") != ARCHIVE_SHA256:
        raise InputContractError(
            "audit archive SHA256 does not match the frozen contract"
        )
    dataset = audit.get("datasets", {}).get(spec.slug)
    if not isinstance(dataset, dict):
        raise InputContractError(f"audit metadata for {spec.slug} is missing")
    csv_meta = dataset.get("csv")
    if not isinstance(csv_meta, dict) or csv_meta.get("sha256") != spec.csv_sha256:
        raise InputContractError(f"audit {spec.slug} CSV identity does not match")
    if csv_meta.get("rows") != spec.expected_rows:
        raise InputContractError(f"audit {spec.slug} row count does not match")
    if csv_meta.get("columns") != len(spec.columns):
        raise InputContractError(f"audit {spec.slug} column count does not match")
    workload = dataset.get("workload")
    if not isinstance(workload, dict):
        raise InputContractError(f"audit {spec.slug} workload metadata is missing")
    if workload.get("pickle_sha256") != spec.workload_pickle_sha256:
        raise InputContractError(
            f"audit {spec.slug} workload pickle identity does not match"
        )
    if workload.get("label_pickle_sha256") != spec.label_pickle_sha256:
        raise InputContractError(
            f"audit {spec.slug} label pickle identity does not match"
        )
    if workload.get("historical_canonical_sha256") != spec.historical_canonical_sha256:
        raise InputContractError(
            f"audit {spec.slug} historical canonical reference does not match"
        )
    if workload.get("canonical_format") != DERIVED_CANONICAL_FORMAT:
        raise InputContractError(
            f"audit {spec.slug} canonical format is not derived-v1"
        )
    splits = workload.get("splits")
    if not isinstance(splits, dict) or set(splits) != set(SPLITS):
        raise InputContractError(f"audit {spec.slug} split contract is incomplete")
    if any(not isinstance(value, int) or value <= 0 for value in splits.values()):
        raise InputContractError(f"audit {spec.slug} split counts are invalid")
    return dataset


def _rewrite_sql_identifiers(sql: str, spec: DatasetSpec) -> str:
    output: list[str] = []
    state = "normal"
    block_depth = 0
    dollar_delimiter = ""
    index = 0
    source_to_catalog = dict(
        zip(spec.source_columns, (name for name, _ in spec.columns), strict=True)
    )
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
            match = re.match(r"\$(?:[A-Za-z_][A-Za-z0-9_]*)?\$", sql[index:])
            if match is not None:
                dollar_delimiter = match.group(0)
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
        if source_name not in source_to_catalog:
            raise InputContractError(
                f"quoted SQL identifier is outside the {spec.slug} schema: {source_name}"
            )
        output.append('"' + source_to_catalog[source_name] + '"')
        index += 1
    if state == "single":
        raise InputContractError("unterminated SQL string literal")
    if state == "block-comment":
        raise InputContractError("unterminated SQL block comment")
    if state == "dollar-quote":
        raise InputContractError("unterminated dollar-quoted SQL string")
    return "".join(output)


def adapt_query_sql(source_sql: str, spec: DatasetSpec) -> str:
    if not isinstance(source_sql, str) or not source_sql.strip():
        raise InputContractError("source SQL must be a non-empty string")
    match = COUNT_FROM.match(source_sql)
    if match is None or match.group("relation") not in spec.source_relations:
        raise InputContractError(
            f"{spec.slug} source SQL must begin with COUNT(*) FROM an audited relation"
        )
    projected = "SELECT * FROM " + spec.relation + match.group("tail")
    return _rewrite_sql_identifiers(projected, spec)


def _canonical_records(
    path: Path, spec: DatasetSpec, expected_sha256: str | None = None
) -> list[dict[str, Any]]:
    actual = sha256_file(path)
    if expected_sha256 is not None and actual != expected_sha256:
        raise InputContractError(
            f"{spec.slug} canonical SHA256 mismatch: expected {expected_sha256}, got {actual}"
        )
    records: list[dict[str, Any]] = []
    try:
        with gzip.open(path, "rt", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.strip():
                    raise InputContractError(
                        f"blank {spec.slug} canonical line {line_number}"
                    )
                try:
                    record = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise InputContractError(
                        f"invalid {spec.slug} canonical JSON at line {line_number}"
                    ) from exc
                if not isinstance(record, dict):
                    raise InputContractError(
                        f"canonical line {line_number} is not an object"
                    )
                split = record.get("split")
                if split not in SPLITS:
                    raise InputContractError(
                        f"invalid {spec.slug} split at line {line_number}"
                    )
                index = record.get("index")
                if not isinstance(index, int) or isinstance(index, bool) or index < 0:
                    raise InputContractError(
                        f"invalid {spec.slug} source index at line {line_number}"
                    )
                expected_id = f"arecel:{spec.slug}:{split}:{index:06d}"
                if record.get("query_id") != expected_id:
                    raise InputContractError(
                        f"{spec.slug} query ID/index mismatch at line {line_number}"
                    )
                source_sql = record.get("sql")
                adapted_sql = adapt_query_sql(source_sql, spec)
                query = record.get("source_query")
                if (
                    not isinstance(query, dict)
                    or query.get("format") != "arecel-source-query-v1"
                    or query.get("table") != spec.slug
                ):
                    raise InputContractError(
                        f"missing {spec.slug} source query provenance at line {line_number}"
                    )
                predicates = query.get("predicates")
                if not isinstance(predicates, list) or not predicates:
                    raise InputContractError(
                        f"{spec.slug} source predicates are missing at line {line_number}"
                    )
                for predicate in predicates:
                    if not isinstance(predicate, dict):
                        raise InputContractError(
                            f"invalid {spec.slug} predicate at line {line_number}"
                        )
                    if predicate.get("column") not in spec.source_columns:
                        raise InputContractError(
                            f"unknown {spec.slug} predicate column at line {line_number}"
                        )
                    if predicate.get("operator") not in SUPPORTED_OPERATORS:
                        raise InputContractError(
                            f"unsupported {spec.slug} predicate operator at line {line_number}"
                        )
                label = record.get("source_label")
                if not isinstance(label, dict):
                    raise InputContractError(
                        f"missing {spec.slug} source label at line {line_number}"
                    )
                truth = label.get("cardinality")
                if not isinstance(truth, int) or isinstance(truth, bool) or truth < 0:
                    raise InputContractError(
                        f"{spec.slug} truth is not an exact nonnegative integer"
                    )
                selectivity = label.get("selectivity")
                if (
                    not isinstance(selectivity, (int, float))
                    or isinstance(selectivity, bool)
                    or not math.isfinite(float(selectivity))
                ):
                    raise InputContractError(
                        f"{spec.slug} source selectivity is not finite"
                    )
                source_query_hash = _require_hex(
                    record.get("source_query_sha256"),
                    f"{spec.slug} source query hash at line {line_number}",
                )
                if (
                    hashlib.sha256(source_sql.encode("utf-8")).hexdigest()
                    != source_query_hash
                ):
                    raise InputContractError(
                        f"{spec.slug} source query hash mismatch at line {line_number}"
                    )
                weight = record.get("weight", 1.0)
                if (
                    not isinstance(weight, (int, float))
                    or isinstance(weight, bool)
                    or not math.isfinite(float(weight))
                    or float(weight) <= 0
                ):
                    raise InputContractError(
                        f"{spec.slug} weight is invalid at line {line_number}"
                    )
                records.append(
                    {
                        "source_index": index,
                        "split": split,
                        "query_id": expected_id,
                        "source_sql": source_sql,
                        "estimator_sql": adapted_sql,
                        "source_query": query,
                        "source_query_sha256": source_query_hash,
                        "source_label": label,
                        "true_cardinality": truth,
                        "weight": float(weight),
                    }
                )
    except (OSError, EOFError) as exc:
        raise InputContractError(
            f"cannot read {spec.slug} canonical workload: {path}"
        ) from exc
    return records


def _split_records(
    records: list[dict[str, Any]], spec: DatasetSpec
) -> dict[str, list[dict[str, Any]]]:
    result: dict[str, list[dict[str, Any]]] = {}
    for split in SPLITS:
        selected = [record for record in records if record["split"] == split]
        if not selected:
            raise InputContractError(f"{spec.slug} {split} split is empty")
        indices = [record["source_index"] for record in selected]
        if indices != list(range(len(selected))):
            raise InputContractError(
                f"{spec.slug} {split} source order is not contiguous"
            )
        ids = [record["query_id"] for record in selected]
        if len(ids) != len(set(ids)):
            raise InputContractError(f"duplicate {spec.slug} {split} query IDs")
        result[split] = selected
    return result


def _dataset_audit(audit: dict[str, Any], spec: DatasetSpec) -> dict[str, Any]:
    return _audit_dataset(audit, spec)


def validate_source(data_root: Path | str | None, dataset: str) -> dict[str, Any]:
    spec = spec_for(dataset)
    paths_for_dataset = paths(data_root, spec)
    audit = _read_json(paths_for_dataset["audit"])
    dataset_audit = _dataset_audit(audit, spec)
    archive_sha = sha256_file(paths_for_dataset["archive"])
    if archive_sha != ARCHIVE_SHA256:
        raise InputContractError(
            f"archive SHA256 mismatch: expected {ARCHIVE_SHA256}, got {archive_sha}"
        )
    archive_members = _archive_members(paths_for_dataset["archive"])
    csv_meta = _csv_metadata(paths_for_dataset["csv"], spec)
    source_hashes = {
        "csv": csv_meta["sha256"],
        "workload_pickle": sha256_file(paths_for_dataset["workload_pickle"]),
        "label_pickle": sha256_file(paths_for_dataset["label_pickle"]),
        "canonical_workload": sha256_file(paths_for_dataset["canonical"]),
    }
    expected = {
        "workload_pickle": spec.workload_pickle_sha256,
        "label_pickle": spec.label_pickle_sha256,
        "canonical_workload": dataset_audit["workload"]["canonical_sha256"],
    }
    for name, expected_hash in expected.items():
        if source_hashes[name] != expected_hash:
            raise InputContractError(f"{spec.slug} {name} SHA256 mismatch")
    records = _canonical_records(
        paths_for_dataset["canonical"], spec, source_hashes["canonical_workload"]
    )
    split_records = _split_records(records, spec)
    audit_splits = dataset_audit["workload"]["splits"]
    split_counts = {split: len(rows) for split, rows in split_records.items()}
    if split_counts != audit_splits:
        raise InputContractError(
            f"{spec.slug} audit split counts do not match canonical records"
        )
    return {
        "format": "arecel-source-validation-v1",
        "benchmark_id": spec.benchmark_id,
        "source_present": True,
        "input_root_logical": "<explicit-data-root>",
        "upstream": {
            "repository": UPSTREAM_URL,
            "commit": UPSTREAM_COMMIT,
            "license": "MIT (code only; data terms not stated)",
        },
        "archive": {
            "url": ARCHIVE_URL,
            "sha256": archive_sha,
            "members": archive_members,
        },
        "schema_contract": schema_contract(spec),
        "csv": csv_meta,
        "source_file_sha256": source_hashes,
        "canonical_workload_format": DERIVED_CANONICAL_FORMAT,
        "historical_canonical_workload_sha256": spec.historical_canonical_sha256,
        "split_counts": split_counts,
        "audit_metadata_sha256": sha256_file(paths_for_dataset["audit"]),
        "transformation_version": TRANSFORMATION_VERSION,
        "source_sql_contract": dataset_audit["workload"].get("source_sql_contract"),
    }


def inspect_source(data_root: Path | str | None, dataset: str) -> dict[str, Any]:
    spec = spec_for(dataset)
    paths_for_dataset = paths(data_root, spec)
    missing = [
        str(path.relative_to(paths_for_dataset["root"]))
        for key, path in paths_for_dataset.items()
        if key != "root" and not path.is_file()
    ]
    result: dict[str, Any] = {
        "format": "arecel-real-inspection-v1",
        "benchmark_id": spec.benchmark_id,
        "dataset": spec.slug,
        "source_present": not missing,
        "missing_inputs": missing,
        "input_root_logical": "<explicit-data-root>",
        "upstream_commit": UPSTREAM_COMMIT,
        "archive_sha256": ARCHIVE_SHA256,
        "expected_rows": spec.expected_rows,
        "schema_contract": schema_contract(spec),
    }
    if missing:
        result["status"] = "BLOCKED_MISSING_INPUT"
    else:
        result["validation"] = validate_source(data_root, dataset)
    return result


def _source_contract(validation: dict[str, Any]) -> dict[str, Any]:
    return {
        "benchmark_id": validation["benchmark_id"],
        "upstream_url": UPSTREAM_URL,
        "upstream_commit": UPSTREAM_COMMIT,
        "archive_url": ARCHIVE_URL,
        "archive_sha256": validation["archive"]["sha256"],
        "source_file_sha256": validation["source_file_sha256"],
        "schema_contract_id": validation["schema_contract"]["id"],
        "canonical_workload_format": validation["canonical_workload_format"],
        "historical_canonical_workload_sha256": validation[
            "historical_canonical_workload_sha256"
        ],
        "transformation_version": TRANSFORMATION_VERSION,
        "source_sql_contract": validation["source_sql_contract"],
    }


def _workload_artifact(
    records: list[dict[str, Any]],
    validation: dict[str, Any],
    spec: DatasetSpec,
    split: str,
) -> dict[str, Any]:
    return {
        "format": "cardinality-workload-v1",
        "workload_id": f"arecel_{spec.slug}_{split}_v1",
        "split": split,
        "source_contract": _source_contract(validation),
        "queries": [
            {
                "query_id": f"arecel_{spec.slug}_{split}_{record['source_index']:06d}",
                "source_query_id": record["query_id"],
                "source_index": record["source_index"],
                "source_sql": record["source_sql"],
                "estimator_sql": record["estimator_sql"],
                "source_query": record["source_query"],
                "source_query_sha256": record["source_query_sha256"],
                "weight": record["weight"],
            }
            for record in records
        ],
    }


def _truth_artifact(
    records: list[dict[str, Any]],
    validation: dict[str, Any],
    spec: DatasetSpec,
    split: str,
) -> dict[str, Any]:
    return {
        "format": "cardinality-truth-v1",
        "truth_id": f"arecel_{spec.slug}_{split}_truth_v1",
        "split": split,
        "source_contract": _source_contract(validation),
        "truth_provenance": {
            "authority": "AreCELearnedYet source_label.cardinality",
            "representation": "exact nonnegative JSON integer",
            "count_sql_is_preserved_as_source_sql": True,
            "database_recomputed": False,
        },
        "truth": [
            {
                "query_id": f"arecel_{spec.slug}_{split}_{record['source_index']:06d}",
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
    fd, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True, ensure_ascii=False)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def build_artifacts(
    data_root: Path | str | None, output_dir: Path | str, dataset: str, split: str
) -> dict[str, Any]:
    spec = spec_for(dataset)
    if split not in SPLITS:
        raise InputContractError("split must be train, valid, or test")
    validation = validate_source(data_root, dataset)
    paths_for_dataset = paths(data_root, spec)
    records = _canonical_records(
        paths_for_dataset["canonical"],
        spec,
        validation["source_file_sha256"]["canonical_workload"],
    )
    selected = _split_records(records, spec)[split]
    output = Path(output_dir).expanduser().resolve(strict=False)
    try:
        relative = output.relative_to(_root(data_root))
    except ValueError as exc:
        raise InputContractError(
            "output directory must be inside the explicit data root"
        ) from exc
    if not relative.parts or relative.parts[0] not in {"etl-output", "experiment-data"}:
        raise InputContractError(
            "output directory must be under data-root/etl-output or data-root/experiment-data"
        )
    if output.exists():
        raise InputContractError(
            f"refusing to overwrite existing output directory: {output}"
        )
    output.mkdir(parents=True, exist_ok=False)
    workload_path = output / "workload.json"
    truth_path = output / "truth.json"
    _write_json(workload_path, _workload_artifact(selected, validation, spec, split))
    _write_json(truth_path, _truth_artifact(selected, validation, spec, split))
    manifest = {
        "format": f"arecel-{spec.slug}-etl-manifest-v1",
        "benchmark_id": spec.benchmark_id,
        "split": split,
        "transformation_version": TRANSFORMATION_VERSION,
        "schema_contract": schema_contract(spec),
        "source_contract": _source_contract(validation),
        "csv_identity": {
            "sha256": validation["csv"]["sha256"],
            "rows": validation["csv"]["rows"],
            "columns": validation["csv"]["columns"],
            "null_counts": validation["csv"]["null_counts"],
        },
        "record_count": len(selected),
        "workload_artifact": {
            "path": "workload.json",
            "sha256": sha256_file(workload_path),
        },
        "truth_artifact": {"path": "truth.json", "sha256": sha256_file(truth_path)},
        "truth_is_not_in_workload": True,
    }
    _write_json(output / "manifest.json", manifest)
    return manifest


def _write_audit(data_root: Path | str | None) -> dict[str, Any]:
    root = _root(data_root)
    archive = _contained(
        root, root / "arecel" / "incoming" / "arecel-data.tar.gz", "archive"
    )
    if sha256_file(archive) != ARCHIVE_SHA256:
        raise InputContractError("archive SHA256 does not match the frozen contract")
    archive_members = _archive_members(archive)
    datasets: dict[str, Any] = {}
    for slug, spec in SPECS.items():
        paths_for_dataset = paths(root, spec)
        csv_meta = _csv_metadata(paths_for_dataset["csv"], spec)
        canonical = paths_for_dataset["canonical"]
        records = _canonical_records(canonical, spec)
        split_records = _split_records(records, spec)
        workload_pickle_sha256 = sha256_file(paths_for_dataset["workload_pickle"])
        label_pickle_sha256 = sha256_file(paths_for_dataset["label_pickle"])
        if workload_pickle_sha256 != spec.workload_pickle_sha256:
            raise InputContractError(
                f"{slug} workload pickle SHA256 does not match the frozen contract"
            )
        if label_pickle_sha256 != spec.label_pickle_sha256:
            raise InputContractError(
                f"{slug} label pickle SHA256 does not match the frozen contract"
            )
        datasets[slug] = {
            "benchmark_id": spec.benchmark_id,
            "relation": spec.relation,
            "csv": csv_meta,
            "workload": {
                "pickle_sha256": workload_pickle_sha256,
                "label_pickle_sha256": label_pickle_sha256,
                "canonical_sha256": sha256_file(canonical),
                "historical_canonical_sha256": spec.historical_canonical_sha256,
                "canonical_format": DERIVED_CANONICAL_FORMAT,
                "splits": {split: len(rows) for split, rows in split_records.items()},
                "source_sql_contract": {
                    "renderer": "pinned AreCELearnedYet query_2_sql semantics reconstructed from Query objects",
                    "source_relation": spec.source_relation,
                    "adaptation": "COUNT(*) to SELECT *, audited relation, and audited identifiers only",
                    "original_sql_bytes_available": False,
                },
                "conversion": {
                    "format": DERIVED_CANONICAL_FORMAT,
                    "pickle_deserialization": "one-time gated conversion only",
                    "regular_etl_deserializes_pickle": False,
                },
            },
            "schema_contract_id": spec.schema_contract_id,
        }
    audit = {
        "format": AUDIT_FORMAT,
        "upstream": {
            "repository": UPSTREAM_URL,
            "commit": UPSTREAM_COMMIT,
            "code_license": "MIT",
            "data_license_status": "not stated by pinned upstream",
        },
        "archive": {
            "url": ARCHIVE_URL,
            "sha256": ARCHIVE_SHA256,
            "members": archive_members,
        },
        "datasets": datasets,
        "raw_data_policy": "local validation only; raw and derived large artifacts are not committed",
        "transformation_version": TRANSFORMATION_VERSION,
    }
    audit_path = root / "arecel" / "audit-v1" / "audit.json"
    if audit_path.exists():
        raise InputContractError(f"refusing to overwrite existing audit: {audit_path}")
    _write_json(audit_path, audit)
    return audit


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    audit = subparsers.add_parser("audit")
    audit.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="AreCEL data root; overrides ESS_DATA_ROOT",
    )
    inspect = subparsers.add_parser("inspect")
    inspect.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="AreCEL data root; overrides ESS_DATA_ROOT",
    )
    inspect.add_argument("--dataset", choices=sorted(SPECS), required=True)
    build = subparsers.add_parser("build")
    build.add_argument(
        "--data-root",
        type=Path,
        default=None,
        help="AreCEL data root; overrides ESS_DATA_ROOT",
    )
    build.add_argument("--dataset", choices=sorted(SPECS), required=True)
    build.add_argument("--output-dir", type=Path, required=True)
    build.add_argument("--split", choices=SPLITS, required=True)
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    args = _parser().parse_args(list(argv) if argv is not None else None)
    try:
        if args.command == "audit":
            print(json.dumps(_write_audit(args.data_root), indent=2, sort_keys=True))
            return 0
        if args.command == "inspect":
            result = inspect_source(args.data_root, args.dataset)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0 if result["source_present"] else 2
        result = build_artifacts(
            args.data_root, args.output_dir, args.dataset, args.split
        )
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0
    except InputContractError as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
