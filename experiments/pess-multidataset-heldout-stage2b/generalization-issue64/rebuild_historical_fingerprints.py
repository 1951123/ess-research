#!/usr/bin/env python3
"""Rebuild outcome-free AreCEL and frozen-protocol query identity fingerprints.

Only the four pinned workload ``base.pkl`` members are decoded. Label pickles,
CSV rows, held-out result files and PostgreSQL artifacts are never opened.
The output ledger contains identifiers and digests, not SQL or cardinalities.
"""

from __future__ import annotations

import argparse
import gzip
import hashlib
import importlib.util
import io
import json
import os
import tarfile
import tempfile
from collections import Counter, defaultdict
from pathlib import Path, PurePosixPath
from typing import Any, Iterable

from cohort_recipe import exact_predicate_fingerprint, template_fingerprint

ARCHIVE_SHA256 = "5cd33cba7f3d7182ef497e60e7346fb2a7546941590a90a4444913a944958f79"
PR58_V4_SHA256 = "54867e0bf3ca116b044d77da14efe1b12d06851af522cfbeb49af14ae33733ad"
DATASETS = ("forest10", "census13", "dmv11", "power7")
SPLITS = ("train", "valid", "test")
SOURCE_ARCHIVE_COMMIT = "aa52da7768023270bad884232972e0b77ec6534a"


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def protocol_v4_exact_fingerprint(predicates: list[dict[str, Any]]) -> str:
    """Reproduce PR #58's frozen sorted-tuple exact hash contract."""
    canonical = json.dumps(
        sorted((p["column"], p["operator"], p["value"]) for p in predicates),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return sha256_bytes(canonical.encode("utf-8"))


def load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"expected JSON object: {path}")
    return value


def _load_module(name: str, path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ValueError(f"cannot import pinned converter module: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def workload_expectations(repo_root: Path) -> dict[str, tuple[str, Any, Any]]:
    """Return expected workload SHA, restricted unpickler, and SQL renderer."""
    arecel = repo_root / "experiments/arecel"
    source = repo_root / "src"
    import sys

    sys.path.insert(0, str(source))
    common = _load_module(
        "issue64_convert_verified_pickles",
        arecel / "convert_verified_pickles.py",
    )
    forest = _load_module(
        "issue64_convert_verified_forest_pickle",
        arecel / "convert_verified_pickle.py",
    )
    result: dict[str, tuple[str, Any, Any]] = {
        "forest10": (
            forest.WORKLOAD_SHA256,
            forest.RestrictedUnpickler,
            lambda query, _spec: forest._source_sql(query),
        )
    }
    for dataset in ("census13", "dmv11", "power7"):
        dataset_spec = common.SPECS[dataset]
        result[dataset] = (
            dataset_spec.workload_pickle_sha256,
            common.RestrictedUnpickler,
            lambda query, _ignored, spec=dataset_spec, render=common._source_sql: render(query, spec),
        )
    return result


def read_workload_members(
    archive_path: Path, expected: dict[str, tuple[str, Any, Any]]
) -> dict[str, bytes]:
    """Read only exact, regular, pinned workload members from the source archive."""
    if archive_path.is_symlink() or not archive_path.is_file():
        raise ValueError("AreCEL archive must be a regular non-symlink file")
    archive_sha = sha256_file(archive_path)
    if archive_sha != ARCHIVE_SHA256:
        raise ValueError(f"AreCEL archive SHA-256 mismatch: {archive_sha}")
    payloads: dict[str, bytes] = {}
    with tarfile.open(archive_path, mode="r:gz") as archive:
        members = archive.getmembers()
        names: set[str] = set()
        for member in members:
            pure = PurePosixPath(member.name)
            if pure.is_absolute() or ".." in pure.parts:
                raise ValueError(f"unsafe AreCEL archive member: {member.name}")
            if not (member.isdir() or member.isreg()):
                raise ValueError(f"non-regular AreCEL archive member: {member.name}")
            normalized = pure.as_posix()
            if normalized in names:
                raise ValueError(f"duplicate AreCEL archive member: {normalized}")
            names.add(normalized)
        by_name = {PurePosixPath(member.name).as_posix(): member for member in members}
        for dataset in DATASETS:
            name = f"data/{dataset}/workload/base.pkl"
            member = by_name.get(name)
            if member is None or not member.isreg():
                raise ValueError(f"missing regular workload member: {name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"cannot read workload member: {name}")
            payload = stream.read()
            expected_sha = expected[dataset][0]
            actual_sha = sha256_bytes(payload)
            if actual_sha != expected_sha:
                raise ValueError(
                    f"{dataset} workload pickle SHA-256 mismatch: {actual_sha}"
                )
            payloads[dataset] = payload
    return payloads


def decode_workload(dataset: str, payload: bytes, expected: dict[str, tuple[str, Any, Any]]) -> dict[str, Any]:
    unpickler = expected[dataset][1](io.BytesIO(payload))
    workload = unpickler.load()
    if not isinstance(workload, dict):
        raise ValueError(f"{dataset} workload root is not a dict")
    if not set(workload).issubset(SPLITS) or not workload:
        raise ValueError(f"{dataset} workload split keys are invalid")
    for split, queries in workload.items():
        if split not in SPLITS or not isinstance(queries, list):
            raise ValueError(f"{dataset}/{split} workload is not a query list")
    return workload


def fingerprint_query(dataset: str, split: str, index: int, query: Any, expected: dict[str, tuple[str, Any, Any]]) -> dict[str, Any]:
    sql, predicates = expected[dataset][2](query, None)
    normalized = {"predicates": predicates}
    # PR #58 protocol-v4 used a distinct exact-hash contract: sorted
    # (column, operator, value) tuples. Issue #59 preserves canonical SQL
    # predicate order. Keep both; never compare one contract as the other.
    protocol_v4_exact = protocol_v4_exact_fingerprint(predicates)
    return {
        "dataset": dataset,
        "split": split,
        "query_id": f"arecel:{dataset}:{split}:{index:06d}",
        "source_index": index,
        "source_sql_sha256": sha256_bytes(sql.strip().encode("utf-8")),
        "exact_fingerprint_sha256": exact_predicate_fingerprint(normalized),
        "protocol_v4_exact_fingerprint_sha256": protocol_v4_exact,
        "template_fingerprint_sha256": template_fingerprint(normalized),
        "historical_sources": [f"arecel:{split}"],
    }


def protocol_claims(
    pr58_protocol: dict[str, Any], stage1a_protocol: dict[str, Any]
) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for dataset in ("forest10", "census13"):
        for cohort in ("test_cohort", "validation_calibration"):
            for record in pr58_protocol["datasets"][dataset][cohort]["records"]:
                claims.append(
                    {
                        "source": f"issue48:{cohort}",
                        "dataset": dataset,
                        "query_id": record["query_id"],
                        "source_index": record["source_index"],
                        "source_sql_sha256": record["source_sql_sha256"],
                        "protocol_v4_exact_fingerprint_sha256": record.get("exact_fingerprint_sha256"),
                        "template_fingerprint_sha256": record.get("template_fingerprint_sha256"),
                    }
                )
    for record in stage1a_protocol["heldout_selection"]["selected"]:
        claims.append(
            {
                "source": "stage1a-issue38:heldout_selection",
                "dataset": "forest10",
                "query_id": record["query_id"],
                "source_index": record["source_index_within_test_split"],
                "source_sql_sha256": record["source_query_sha256"],
                        "protocol_v4_exact_fingerprint_sha256": None,
                "template_fingerprint_sha256": None,
            }
        )
    return claims


def reconcile_claims(
    ledger: list[dict[str, Any]], claims: list[dict[str, Any]]
) -> dict[str, Any]:
    by_id = {record["query_id"]: record for record in ledger}
    if len(by_id) != len(ledger):
        raise ValueError("duplicate source query IDs in rebuilt AreCEL ledger")
    checked: list[dict[str, Any]] = []
    errors: list[dict[str, str]] = []
    claim_counts = Counter((claim["source"], claim["query_id"]) for claim in claims)
    for claim in claims:
        key = (claim["source"], claim["query_id"])
        source = by_id.get(claim["query_id"])
        mismatch = None
        if source is None:
            mismatch = "query_id_not_found_in_pinned_workload"
        elif source["dataset"] != claim["dataset"]:
            mismatch = "dataset_mismatch"
        elif source["split"] not in ("test", "valid"):
            mismatch = "split_mismatch"
        elif source["source_index"] != claim["source_index"]:
            mismatch = "source_index_mismatch"
        elif source["source_sql_sha256"] != claim["source_sql_sha256"]:
            mismatch = "source_sql_sha256_mismatch"
        elif claim["protocol_v4_exact_fingerprint_sha256"] and source["protocol_v4_exact_fingerprint_sha256"] != claim["protocol_v4_exact_fingerprint_sha256"]:
            mismatch = "protocol_v4_exact_fingerprint_mismatch"
        elif claim["template_fingerprint_sha256"] and source["template_fingerprint_sha256"] != claim["template_fingerprint_sha256"]:
            mismatch = "template_fingerprint_mismatch"
        if claim_counts[key] > 1:
            mismatch = "duplicate_claim_within_source"
        checked.append(
            {
                "source": claim["source"],
                "query_id": claim["query_id"],
                "source_index": claim["source_index"],
                "verified": mismatch is None,
                "mismatch": mismatch,
                "issue59_ordered_equals_protocol_v4_sorted": (
                    source["exact_fingerprint_sha256"]
                    == claim["protocol_v4_exact_fingerprint_sha256"]
                    if source is not None and claim["protocol_v4_exact_fingerprint_sha256"]
                    else None
                ),
            }
        )
        if mismatch:
            errors.append({"source": claim["source"], "query_id": claim["query_id"], "reason": mismatch})
        elif source is not None:
            source["historical_sources"].append(claim["source"])
    return {"claims": checked, "claim_count": len(claims), "verified_count": len(claims) - len(errors), "errors": errors}


def split_overlap_summary(ledger: Iterable[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for record in ledger:
        grouped[(record["dataset"], record["split"])].append(record)
    result: dict[str, Any] = {}
    for dataset in DATASETS:
        result[dataset] = {}
        present = [split for split in SPLITS if (dataset, split) in grouped]
        for left_index, left in enumerate(present):
            for right in present[left_index + 1 :]:
                left_rows, right_rows = grouped[(dataset, left)], grouped[(dataset, right)]
                row = {}
                for field in (
                    "exact_fingerprint_sha256",
                    "protocol_v4_exact_fingerprint_sha256",
                    "template_fingerprint_sha256",
                ):
                    a = {item[field] for item in left_rows}
                    b = {item[field] for item in right_rows}
                    row[field.removesuffix("_sha256")] = {
                        "distinct_left": len(a),
                        "distinct_right": len(b),
                        "shared_distinct_fingerprints": len(a & b),
                    }
                result[dataset][f"{left}__{right}"] = row
    return result


def analyze(
    repo_root: Path,
    archive_path: Path,
    pr58_protocol_path: Path,
    stage1a_protocol_path: Path,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    expected = workload_expectations(repo_root)
    payloads = read_workload_members(archive_path, expected)
    ledger: list[dict[str, Any]] = []
    split_counts: dict[str, dict[str, int]] = {}
    workload_hashes = {dataset: expected[dataset][0] for dataset in DATASETS}
    for dataset in DATASETS:
        workload = decode_workload(dataset, payloads[dataset], expected)
        split_counts[dataset] = {}
        for split in SPLITS:
            queries = workload.get(split, [])
            split_counts[dataset][split] = len(queries)
            for index, query in enumerate(queries):
                ledger.append(fingerprint_query(dataset, split, index, query, expected))
        del workload

    pr58_bytes = pr58_protocol_path.read_bytes()
    if sha256_bytes(pr58_bytes) != PR58_V4_SHA256:
        raise ValueError("frozen PR #58 protocol-v4 SHA-256 mismatch")
    pr58_protocol = json.loads(pr58_bytes)
    stage1a_bytes = stage1a_protocol_path.read_bytes()
    stage1a_protocol = json.loads(stage1a_bytes)
    claims = protocol_claims(pr58_protocol, stage1a_protocol)
    reconciliation = reconcile_claims(ledger, claims)

    missing_splits = [
        f"{dataset}/{split}"
        for dataset in DATASETS
        for split in SPLITS
        if split_counts[dataset][split] == 0
    ]
    bad_claims = reconciliation["errors"]
    source_coverage = {
        "arecel_all_dataset_splits_present": not missing_splits,
        "arecel_missing_splits": missing_splits,
        "issue48_claims_complete_match": not any("issue48" in row["source"] for row in bad_claims),
        "stage1a_claims_complete_match": not any("stage1a" in row["source"] for row in bad_claims),
        "all_frozen_identity_claims_match": not bad_claims,
    }
    report = {
        "format": "issue64-historical-fingerprint-rebuild-report-v7",
        "evidence_label": "OUTCOME_FREE_SOURCE_IDENTITY_RECONSTRUCTION",
        "status": "PASS_HISTORICAL_IDENTITY_RECONSTRUCTION" if not missing_splits and not bad_claims else "BLOCKED_SOURCE_COVERAGE_OR_IDENTITY_MISMATCH",
        "sources": {
            "arecel_upstream_commit": SOURCE_ARCHIVE_COMMIT,
            "archive_sha256_expected_and_verified": ARCHIVE_SHA256,
            "workload_pickle_sha256_by_dataset": workload_hashes,
            "issue48_protocol_v4_path": str(pr58_protocol_path),
            "issue48_protocol_v4_sha256_expected_and_verified": PR58_V4_SHA256,
            "stage1a_protocol_path": str(stage1a_protocol_path),
            "stage1a_protocol_sha256": sha256_bytes(stage1a_bytes),
            "fingerprint_contract_source": "Issue #59 audit_structure.py pinned in Issue #64 schema_capacity.py source pins; PR #58 protocol-v4 exact hash reconstructed separately as sorted predicate tuples",
        },
        "scope": {
            "opened_artifacts": ["AreCEL archive metadata", "four workload/base.pkl members", "Issue #48 frozen protocol-v4 identity fields", "Stage 1A frozen protocol identity fields"],
            "not_opened": ["base-original-label.pkl", "truth files", "estimate files", "PostgreSQL traces", "EXPLAIN or measurement results", "result summaries"],
            "stage1a_canonical_record_sha256_ignored": True,
            "ledger_fields": ["dataset", "split", "query_id", "source_index", "source_sql_sha256", "exact_fingerprint_sha256 (Issue #59 ordered)", "protocol_v4_exact_fingerprint_sha256 (sorted tuple contract)", "template_fingerprint_sha256", "historical_sources"],
            "exact_hash_contract_note": "Issue #59 canonical exact preserves source predicate order; PR #58 protocol-v4 sorts (column, operator, value) tuples before hashing. Both are retained and independently checked; hashes are not interchangeable.",
            "raw_sql_or_literals_written": False,
        },
        "arecel_workload_coverage": {
            "split_counts": split_counts,
            "total_queries": len(ledger),
            "source_coverage": source_coverage,
            "cross_split_overlap": split_overlap_summary(ledger),
            "interpretation": "Historical exact/template overlap is retained and added to the quarantine union; it is not treated as a new-cohort collision. No prospective candidate pool was generated.",
        },
        "frozen_protocol_claims": reconciliation,
        "exact_fingerprint_contract_comparison": {
            "scope": "claims with both Issue #59 reconstruction and PR #58 frozen exact hashes",
            "by_source": {
                source: {
                    "claims": sum(row["source"] == source and row["issue59_ordered_equals_protocol_v4_sorted"] is not None for row in reconciliation["claims"]),
                    "same_digest": sum(row["source"] == source and row["issue59_ordered_equals_protocol_v4_sorted"] is True for row in reconciliation["claims"]),
                    "different_digest_due_to_contract": sum(row["source"] == source and row["issue59_ordered_equals_protocol_v4_sorted"] is False for row in reconciliation["claims"]),
                }
                for source in sorted({row["source"] for row in reconciliation["claims"]})
            },
            "interpretation": "Different digests are not identity failures: v4 sorts predicate tuples while Issue #59 preserves source predicate order. Each is verified against its own frozen/reconstructed contract.",
        },
        "historical_quarantine": {
            "status": "PASS_SOURCE_IDENTITY_COVERAGE" if not missing_splits and not bad_claims else "BLOCKED",
            "arecel_query_identity_count": len(ledger),
            "issue48_frozen_identity_claims": sum(row["source"].startswith("issue48:") for row in claims),
            "stage1a_frozen_identity_claims": sum(row["source"].startswith("stage1a") for row in claims),
            "unique_quarantine_template_fingerprints": len({row["template_fingerprint_sha256"] for row in ledger}),
            "unique_quarantine_issue59_ordered_exact_fingerprints": len({row["exact_fingerprint_sha256"] for row in ledger}),
            "unique_quarantine_protocol_v4_sorted_exact_fingerprints": len({row["protocol_v4_exact_fingerprint_sha256"] for row in ledger}),
            "unique_quarantine_exact_fingerprint_digest_union": len(
                {
                    row[field]
                    for row in ledger
                    for field in ("exact_fingerprint_sha256", "protocol_v4_exact_fingerprint_sha256")
                }
            ),
            "prospective_candidate_pool_status": "NOT_RUN_BY_TASK_BOUNDARY; candidate-level zero-collision gate remains untested",
        },
        "limitations": [
            "Reconstructing historical identities and the quarantine union does not prove a future fixed-attempt candidate pool can meet quotas.",
            "If any source split is absent or any frozen identity claim mismatches, the historical identity gate is BLOCKED.",
            "No new cohort was generated, and no PostgreSQL or held-out measurement was run.",
        ],
    }
    return ledger, report


def write_gzip_jsonl_exclusive(path: Path, records: Iterable[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite ledger: {path}")
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as raw:
            with gzip.GzipFile(fileobj=raw, mode="wb", filename="", mtime=0) as compressed:
                for record in records:
                    line = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
                    compressed.write((line + "\n").encode("utf-8"))
            raw.flush()
            os.fsync(raw.fileno())
        os.link(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def write_json_exclusive(path: Path, value: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, sort_keys=True, indent=2)
        stream.write("\n")


def write_sha256_manifest_exclusive(path: Path, files: Iterable[tuple[str, Path]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        for _label, source in files:
            stream.write(f"{sha256_file(source)}  {source.resolve()}\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--archive", type=Path, required=True)
    parser.add_argument("--issue48-protocol-v4", type=Path, required=True)
    parser.add_argument("--stage1a-protocol", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    ledger, report = analyze(
        args.repo_root.resolve(),
        args.archive.resolve(),
        args.issue48_protocol_v4.resolve(),
        args.stage1a_protocol.resolve(),
    )
    output_dir = args.output_dir.resolve()
    repo_root = args.repo_root.resolve()
    write_gzip_jsonl_exclusive(output_dir / "historical-fingerprint-ledger-v7.jsonl.gz", ledger)
    write_json_exclusive(output_dir / "historical-fingerprint-rebuild-report-v7.json", report)
    source_paths = [
        ("ledger", output_dir / "historical-fingerprint-ledger-v7.jsonl.gz"),
        ("report", output_dir / "historical-fingerprint-rebuild-report-v7.json"),
        ("rebuild_script", Path(__file__).resolve()),
        ("unit_tests", Path(__file__).with_name("test_rebuild_historical_fingerprints.py").resolve()),
        ("issue64_fingerprint_contract", Path(__file__).with_name("cohort_recipe.py").resolve()),
        ("issue59_reference", repo_root / "experiments/workload-structure-audit-issue59/audit_structure.py"),
        ("arecel_converter_common", repo_root / "experiments/arecel/convert_verified_pickles.py"),
        ("arecel_converter_forest10", repo_root / "experiments/arecel/convert_verified_pickle.py"),
        ("arecel_schema_real", repo_root / "src/ess_research/arecel/real.py"),
        ("arecel_schema_forest10", repo_root / "src/ess_research/arecel/forest10.py"),
        ("arecel_archive", args.archive.resolve()),
        ("issue48_protocol_v4", args.issue48_protocol_v4.resolve()),
        ("stage1a_protocol", args.stage1a_protocol.resolve()),
    ]
    write_sha256_manifest_exclusive(output_dir / "SHA256SUMS-v7", source_paths)
    print(json.dumps({"status": report["status"], "ledger_records": len(ledger), "claim_count": report["frozen_protocol_claims"]["claim_count"], "verified_claims": report["frozen_protocol_claims"]["verified_count"], "missing_splits": report["arecel_workload_coverage"]["source_coverage"]["arecel_missing_splits"], "claim_errors": len(report["frozen_protocol_claims"]["errors"])}, sort_keys=True))
    return 0 if report["status"] == "PASS_HISTORICAL_IDENTITY_RECONSTRUCTION" else 2


if __name__ == "__main__":
    raise SystemExit(main())
