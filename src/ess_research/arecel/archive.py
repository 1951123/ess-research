"""Archive-first AreCEL preparation, scoped to one consuming run.

Only the pinned whole archive is trusted. Pickle deserialization happens after
that gate; this is NOT a safe loader for arbitrary user-provided pickle files.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import pickle
import platform
import shutil
import stat
import subprocess
import tarfile
import tempfile
from collections import namedtuple
from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, BinaryIO
from urllib.request import urlopen

from ess_research.task_paths import ConfigurationError, configured_root, runtime_runs

# Reuse schema/provenance constants only. No legacy artifact reader is invoked.
from .forest10 import COLUMNS as FOREST_COLUMNS
from .forest10 import SOURCE_COLUMNS as FOREST_SOURCE_COLUMNS
from .real import ARCHIVE_SHA256, ARCHIVE_URL, SPECS, UPSTREAM_COMMIT

DOWNLOAD_URL = ARCHIVE_URL.replace("?dl=0", "?dl=1")
DATASETS = ("forest10", "census13", "dmv11", "power7")
Query = namedtuple("Query", "predicates ncols")
Label = namedtuple("Label", "cardinality selectivity")


class PreparationError(ValueError):
    """The archive or computed dataset has an invalid format."""


@dataclass(frozen=True)
class PreparedDataset:
    run_root: Path
    dataset_root: Path
    manifest: dict[str, Any]

    @property
    def csv(self) -> Path:
        return self.dataset_root / "table.csv"


@dataclass(frozen=True)
class PreparedValidWorkload:
    run_root: Path
    workload_path: Path
    manifest: dict[str, Any]


class _ArchiveUnpickler(pickle.Unpickler):
    def find_class(self, module: str, name: str) -> Any:
        if module == "lecarb.workload.workload" and name in {"Query", "Label"}:
            return {"Query": Query, "Label": Label}[name]
        return super().find_class(module, name)


def _sha256(stream: BinaryIO) -> str:
    digest = hashlib.sha256()
    for block in iter(lambda: stream.read(1024 * 1024), b""):
        digest.update(block)
    return digest.hexdigest()


def _open_verified(path: Path) -> BinaryIO:
    # Hash and deserialize from the same open file, even if a path is replaced.
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    stream = os.fdopen(fd, "rb")
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise PreparationError(f"archive cache is not a regular file: {path}")
        actual = _sha256(stream)
        if actual != ARCHIVE_SHA256:
            raise PreparationError(
                f"archive SHA-256 mismatch at {path}: expected {ARCHIVE_SHA256}, got {actual}; "
                "existing cache was not replaced"
            )
        stream.seek(0)
        return stream
    except BaseException:
        stream.close()
        raise


def _archive(cache_root: Path) -> BinaryIO:
    cache_root.mkdir(parents=True, exist_ok=True)
    target = cache_root / "arecel-data.tar.gz"
    try:
        return _open_verified(target)
    except FileNotFoundError:
        pass
    fd, temporary = tempfile.mkstemp(
        prefix=".arecel-download-", suffix=".part", dir=cache_root
    )
    temporary = Path(temporary)
    try:
        with os.fdopen(fd, "wb") as output:
            with urlopen(DOWNLOAD_URL, timeout=60) as response:
                shutil.copyfileobj(response, output, length=1024 * 1024)
            output.flush()
            os.fsync(output.fileno())
        with _open_verified(temporary):
            pass
        try:
            # Atomic publish, with no replacement if another worker won.
            os.link(temporary, target)
        except FileExistsError:
            pass
        return _open_verified(target)
    finally:
        temporary.unlink(missing_ok=True)


def _schema(dataset: str) -> tuple[tuple[str, ...], tuple[tuple[str, str], ...], str]:
    if dataset == "forest10":
        return FOREST_SOURCE_COLUMNS, FOREST_COLUMNS, 'public."forest10_original"'
    spec = SPECS[dataset]
    return spec.source_columns, spec.columns, spec.source_relation


def _scalar(value: Any) -> Any:
    # NumPy is needed only when the pinned archive actually contains its scalars.
    if type(value).__module__.startswith("numpy") and hasattr(value, "item"):
        value = value.item()
    if isinstance(value, bool) or not isinstance(value, (str, int, float)):
        raise PreparationError(
            f"invalid predicate/label scalar: {type(value).__name__}"
        )
    if isinstance(value, float) and not math.isfinite(value):
        raise PreparationError("nonfinite predicate/label scalar")
    return value


def _literal(value: Any, column_type: str) -> tuple[str, Any]:
    value = _scalar(value)
    if column_type == "DOUBLE PRECISION":
        if not isinstance(value, (int, float)):
            raise PreparationError("numeric predicate contains a string")
        return str(value), value
    if not isinstance(value, str):
        raise PreparationError("categorical predicate contains a non-string")
    # Explicit E strings preserve backslashes regardless of PG session settings.
    if "\\" in value:
        return "E'" + value.replace("\\", "\\\\").replace("'", "''") + "'", value
    return "'" + value.replace("'", "''") + "'", value


def _query(query: Query, dataset: str) -> dict[str, Any]:
    source_columns, columns, source_relation = _schema(dataset)
    schema = dict(zip(source_columns, columns, strict=True))
    if not isinstance(query, Query) or not isinstance(query.predicates, Mapping):
        raise PreparationError("invalid source Query or predicate mapping")
    source_parts, adapted_parts, predicates = [], [], []
    for name, expression in query.predicates.items():
        if name not in schema:
            raise PreparationError(f"unknown {dataset} predicate column: {name!r}")
        if expression is None:
            continue
        if not isinstance(expression, tuple) or len(expression) != 2:
            raise PreparationError("predicate must contain operator and value")
        operator, value = expression
        catalog, column_type = schema[name]
        if operator == "[]":
            if not isinstance(value, (tuple, list)) or len(value) != 2:
                raise PreparationError("range requires two inclusive bounds")
            left, low = _literal(value[0], column_type)
            right, high = _literal(value[1], column_type)
            tail, normalized = f"between {left} and {right}", [low, high]
        elif isinstance(operator, str) and operator in {"=", "<", "<=", ">", ">="}:
            literal, normalized = _literal(value, column_type)
            tail = f"{operator} {literal}"
        else:
            raise PreparationError(f"unsupported predicate operator: {operator!r}")
        source_parts.append(f'"{name}" {tail}')
        adapted_parts.append(f'"{catalog}" {tail}')
        predicates.append({"column": name, "operator": operator, "value": normalized})
    ncols = _scalar(query.ncols)
    if not isinstance(ncols, int) or not predicates or ncols != len(predicates):
        raise PreparationError("empty predicates or inconsistent source ncols")
    return {
        "source_sql": f"SELECT COUNT(*) FROM {source_relation} WHERE "
        + " AND ".join(source_parts)
        + ";",
        "sql": f"SELECT * FROM public.{dataset} WHERE "
        + " AND ".join(adapted_parts)
        + ";",
        "predicates": predicates,
        "weight": 1.0,
    }


def _write_json(path: Path, value: Any) -> None:
    with path.open("x", encoding="utf-8") as output:
        json.dump(
            value, output, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        )
        output.write("\n")


def _outputs(archive: BinaryIO, dataset: str, derived: Path) -> dict[str, int]:
    wanted = {
        f"data/{dataset}/original.csv": derived / "table.csv",
        f"data/{dataset}/workload/base.pkl": None,
        f"data/{dataset}/workload/base-original-label.pkl": None,
    }
    objects: dict[str, Any] = {}
    seen = set()
    # Streaming scan avoids materializing other datasets and rejects duplicate
    # selected members. Never extract tar paths onto the filesystem.
    with tarfile.open(fileobj=archive, mode="r|gz") as source:
        for member in source:
            name = member.name.removeprefix("./")
            if name not in wanted:
                continue
            if name in seen or not member.isfile():
                raise PreparationError(f"duplicate/nonregular archive member: {name}")
            seen.add(name)
            stream = source.extractfile(member)
            if stream is None:
                raise PreparationError(f"unreadable archive member: {name}")
            with stream:
                destination = wanted[name]
                if destination is not None:
                    with destination.open("xb") as output:
                        shutil.copyfileobj(stream, output, length=1024 * 1024)
                else:
                    objects[name] = _ArchiveUnpickler(stream).load()
    if seen != set(wanted):
        raise PreparationError(f"missing archive members: {sorted(set(wanted) - seen)}")
    source_columns, columns, _ = _schema(dataset)
    with (derived / "table.csv").open(newline="", encoding="utf-8") as stream:
        if next(csv.reader(stream), None) != list(source_columns):
            raise PreparationError(f"unexpected {dataset} CSV header")
    ddl = (
        f"CREATE TABLE public.{dataset} (\n"
        + ",\n".join(f'  "{name}" {type_}' for name, type_ in columns)
        + "\n);\n"
    )
    (derived / "schema.sql").write_text(ddl, encoding="utf-8")
    workload = objects[f"data/{dataset}/workload/base.pkl"]
    labels = objects[f"data/{dataset}/workload/base-original-label.pkl"]
    if (
        not isinstance(workload, dict)
        or not isinstance(labels, dict)
        or set(workload) != set(labels)
    ):
        raise PreparationError("workload/label split keys do not match")
    if not {"valid", "test"} <= set(workload) or set(workload) - {
        "train",
        "valid",
        "test",
    }:
        raise PreparationError("expected valid/test and optional train splits")
    counts = {}
    for split in ("train", "valid", "test"):
        if split not in workload:
            continue
        queries, split_labels = workload[split], labels[split]
        if (
            not isinstance(queries, list)
            or not isinstance(split_labels, list)
            or len(queries) != len(split_labels)
            or not queries
        ):
            raise PreparationError(f"empty or misaligned {split} split")
        records, truths = [], []
        for index, (query, label) in enumerate(zip(queries, split_labels, strict=True)):
            if not isinstance(label, Label):
                raise PreparationError("invalid source Label")
            cardinality, selectivity = (
                _scalar(label.cardinality),
                _scalar(label.selectivity),
            )
            if not isinstance(cardinality, int) or cardinality < 0:
                raise PreparationError(
                    "source cardinality must be a nonnegative integer"
                )
            if not isinstance(selectivity, (float, int)) or not 0 <= selectivity <= 1:
                raise PreparationError("source selectivity must be in [0, 1]")
            identity = {
                "query_id": f"arecel:{dataset}:{split}:{index:06d}",
                "source_index": index,
            }
            records.append({**identity, **_query(query, dataset)})
            truths.append(
                {
                    **identity,
                    "true_cardinality": cardinality,
                    "source_selectivity": selectivity,
                }
            )
        split_root = derived / split
        split_root.mkdir()
        common = {"format": "arecel-prepared-v1", "dataset": dataset, "split": split}
        _write_json(split_root / "workload.json", {**common, "queries": records})
        _write_json(split_root / "truth.json", {**common, "queries": truths})
        counts[split] = len(records)
    return counts


@contextmanager
def prepare_valid_workload(
    *, issue: int, dataset: str, run_root: Path | None = None
) -> Iterator[PreparedValidWorkload]:
    """Prepare only the official valid workload, without loading labels.

    This bounded path reads the pinned workload pickle and applies the existing
    schema/query adapter. It never opens the label pickle, table CSV, or writes
    truth files. Only the valid split workload JSON is materialized, then
    removed with this invocation's temporary run directory.
    """
    if dataset not in DATASETS:
        raise PreparationError(f"choose one dataset from {DATASETS}")
    cache = configured_root("ESS_DATA_ROOT")
    runs = runtime_runs("ess-research", issue)
    runtime_parent = configured_root("ESS_RUNTIME_PARENT")
    if (
        cache == runtime_parent
        or cache in runtime_parent.parents
        or runtime_parent in cache.parents
    ):
        raise ConfigurationError(
            "ESS_DATA_ROOT and ESS_RUNTIME_PARENT must be disjoint directories"
        )
    runs.mkdir(parents=True, exist_ok=True)

    scratch_parent = runs
    if run_root is not None:
        if run_root.is_symlink() or not run_root.is_dir():
            raise ConfigurationError(
                "run_root must be an existing, non-symlink run directory"
            )
        owned_root = run_root.resolve(strict=True)
        if owned_root.parent != runs.resolve(strict=True):
            raise ConfigurationError(
                "run_root must be one direct child of this Issue's runtime runs directory"
            )
        scratch_parent = owned_root

    with tempfile.TemporaryDirectory(
        prefix="arecel-valid-workload-", dir=scratch_parent
    ) as name:
        run = Path(name)
        workload_path = run / "valid" / "workload.json"
        workload_path.parent.mkdir()
        member_name = f"data/{dataset}/workload/base.pkl"
        source_workload = None
        with _archive(cache) as verified_archive:
            with tarfile.open(fileobj=verified_archive, mode="r|gz") as archive:
                for member in archive:
                    if member.name.removeprefix("./") != member_name:
                        continue
                    if source_workload is not None or not member.isfile():
                        raise PreparationError(
                            f"duplicate/nonregular archive member: {member_name}"
                        )
                    stream = archive.extractfile(member)
                    if stream is None:
                        raise PreparationError(
                            f"unreadable archive member: {member_name}"
                        )
                    with stream:
                        source_workload = _ArchiveUnpickler(stream).load()
        if not isinstance(source_workload, dict) or not isinstance(
            source_workload.get("valid"), list
        ):
            raise PreparationError("pinned archive has no valid workload list")

        source_queries = source_workload["valid"]
        records = []
        for index, query in enumerate(source_queries):
            identity = {
                "query_id": f"arecel:{dataset}:valid:{index:06d}",
                "source_index": index,
            }
            records.append({**identity, **_query(query, dataset)})
        _write_json(
            workload_path,
            {
                "format": "arecel-prepared-v1",
                "dataset": dataset,
                "split": "valid",
                "queries": records,
            },
        )
        manifest = {
            "format": "arecel-valid-workload-preparation-v1",
            "dataset": dataset,
            "split": "valid",
            "query_count": len(records),
            "archive_sha256": ARCHIVE_SHA256,
            "archive_url": ARCHIVE_URL,
            "upstream_commit": UPSTREAM_COMMIT,
            "issue": issue,
            "etl": _revision(),
            "python": platform.python_version(),
            "seed": None,
            "labels_loaded": False,
        }
        yield PreparedValidWorkload(run, workload_path, manifest)


def _revision() -> dict[str, Any]:
    repository = Path(__file__).resolve().parents[3]
    try:
        revision = subprocess.check_output(
            ["git", "-C", str(repository), "rev-parse", "HEAD"],
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
        dirty = bool(
            subprocess.check_output(
                ["git", "-C", str(repository), "status", "--porcelain"], text=True
            )
        )
    except (OSError, subprocess.CalledProcessError):
        revision, dirty = None, None
    return {"git_commit": revision, "worktree_dirty": dirty}


@contextmanager
def prepare(
    *, issue: int, dataset: str, keep_scratch: bool = False
) -> Iterator[PreparedDataset]:
    """Prepare and yield usable files; clean only this invocation's derived tree.

    Retain a small manifest and status/error diagnostic in results/logs. Callers
    must copy their scientific evidence out of derived before the context exits.
    No PGDATA, external outputs, or earlier run is removed.
    """
    if dataset not in DATASETS:
        raise PreparationError(f"choose one dataset from {DATASETS}")
    cache = configured_root("ESS_DATA_ROOT")
    runs = runtime_runs("ess-research", issue)
    runtime_parent = configured_root("ESS_RUNTIME_PARENT")
    if (
        cache == runtime_parent
        or cache in runtime_parent.parents
        or runtime_parent in cache.parents
    ):
        raise ConfigurationError(
            "ESS_DATA_ROOT and ESS_RUNTIME_PARENT must be disjoint directories"
        )
    runs.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="arecel-", dir=runs))
    derived = run / "derived"
    derived.mkdir()
    owned = derived.stat()
    (run / "logs").mkdir()
    (run / "results").mkdir()
    status = "failed"
    try:
        with _archive(cache) as archive:
            counts = _outputs(archive, dataset, derived)
        manifest = {
            "format": "arecel-preparation-v1",
            "dataset": dataset,
            "splits": counts,
            "archive_sha256": ARCHIVE_SHA256,
            "archive_url": ARCHIVE_URL,
            "upstream_commit": UPSTREAM_COMMIT,
            "issue": issue,
            "repository": "ess-research",
            "run_id": run.name,
            "etl": _revision(),
            "python": platform.python_version(),
            "config": {"weight": 1.0, "seed": None, "keep_scratch": keep_scratch},
            "table": "table.csv",
            "schema": "schema.sql",
        }
        _write_json(derived / "manifest.json", manifest)
        _write_json(run / "results" / "manifest.json", manifest)
        yield PreparedDataset(run, derived, manifest)
        status = "success"
    except BaseException as exc:
        _write_json(
            run / "logs" / "error.json",
            {"type": type(exc).__name__, "message": str(exc)[:2000]},
        )
        if isinstance(exc, Exception):
            exc.add_note(f"AreCEL diagnostics: {run / 'logs' / 'error.json'}")
        raise
    finally:
        cleaned = False
        if not keep_scratch and derived.exists():
            current = derived.lstat()
            if not derived.is_symlink() and (current.st_dev, current.st_ino) == (
                owned.st_dev,
                owned.st_ino,
            ):
                shutil.rmtree(derived)
                cleaned = True
        _write_json(
            run / "logs" / "status.json",
            {
                "status": status,
                "derived_removed": cleaned,
                "keep_scratch": keep_scratch,
            },
        )
