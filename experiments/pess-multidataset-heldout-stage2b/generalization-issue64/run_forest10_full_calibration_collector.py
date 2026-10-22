"""Researcher-authorized, collection-only full-valid JSON runner; never performs selection."""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import shutil
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
ISSUE64_ROOT = HERE.parents[2]
sys.path.insert(0, str(ISSUE64_ROOT / "src"))
sys.path.insert(0, str(HERE))

import run_forest10_setup_pilot as pilot
import run_forest10_trace_probe as smoke
from ess_research.arecel.archive import _schema, prepare_valid_workload
from ess_research.arecel.candidates import discover_candidates
from ess_research.arecel.forest10 import EXPECTED_ROWS, SOURCE_COLUMNS
from ess_research.task_paths import configured_root, runtime_runs
from forest10_runner import PR58Forest10Backend, pr58_candidate_specs, validate_fresh_sample_identity

PLAN = HERE / "forest10-json-full-observation-plan-v1.json"
PLAN_SHA256 = "5483f55046e287594eb2090557c68d3334cefda8318c29a707a0631623284db2"
RUN_PREFIX = "f10full-"
MANIFEST = "collection-manifest.json"
SUMMARY = "collector-worker-summary.json"
APPROVED_PLAN_STATUS = "RESEARCHER_APPROVED_EXECUTION_2026-10-22"
PART_RECORD_LIMIT = 2048
PART_BYTES_LIMIT = 8 * 1024 * 1024
FSYNC_BATCH = 256
# Approved in the Issue #64 decision dated 2026-10-22; enforced by the run watchdog.
HARD_WALL_SECONDS = 8 * 60 * 60
SOFT_WALL_SECONDS = 7 * 60 * 60 + 30 * 60
HARD_DISK_BYTES = 4 * 1024**3
SOFT_DISK_BYTES = 3 * 1024**3


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def validate_approved_plan(plan: dict[str, Any], actual_sha256: str) -> None:
    if actual_sha256 != PLAN_SHA256:
        raise RuntimeError("frozen full-observation plan hash mismatch")
    if plan.get("status") != APPROVED_PLAN_STATUS:
        raise RuntimeError("full-valid collection plan is not researcher-approved")
    if plan.get("approved_limits", {}).get("status") != "RESEARCHER_APPROVED_2026-10-22":
        raise RuntimeError("full-valid collection limits do not match the researcher approval")
    if plan.get("retention", {}).get("status") != "RESEARCHER_APPROVED_2026-10-22":
        raise RuntimeError("full-valid observation retention does not match the researcher approval")


def atomic_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    payload = (json.dumps(value, sort_keys=True, indent=2) + "\n").encode("utf-8")
    with temporary.open("xb") as stream:
        stream.write(payload)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


class SegmentedJsonl:
    """Small gzip parts; checkpoint data bytes before atomically advancing manifest."""

    def __init__(self, root: Path, manifest: dict[str, Any], save_manifest) -> None:
        self.root = root
        self.manifest = manifest
        self.save_manifest = save_manifest
        self.parts: list[dict[str, Any]] = manifest["parts"]
        self.buffer: list[bytes] = []
        self.buffered_rows = 0
        self.total_rows = 0
        self.part_rows = 0
        self.part_index = len(self.parts) + 1
        self.raw = None
        self.part_path: Path | None = None
        self.part_bytes = 0
        self.part_compressed_bytes = 0
        self.part_first_sequence = 0

    def _open_part(self) -> None:
        self.part_path = self.root / f"observations-{self.part_index:04d}.jsonl.gz"
        self.raw = self.part_path.open("xb")
        self.part_rows = 0
        self.part_bytes = 0
        self.part_compressed_bytes = 0
        self.part_first_sequence = self.total_rows + 1

    def write(self, row: dict[str, Any]) -> None:
        line = (json.dumps(row, sort_keys=True, separators=(",", ":")) + "\n").encode()
        if len(line) > PART_BYTES_LIMIT:
            raise ValueError("one compact observation exceeds the part byte limit")
        if self.raw is not None and (
            self.part_rows >= PART_RECORD_LIMIT or self.part_bytes + len(line) > PART_BYTES_LIMIT
        ):
            self._finish_part()
        if self.raw is None:
            self._open_part()
        self.buffer.append(line)
        self.buffered_rows += 1
        self.total_rows += 1
        self.part_rows += 1
        self.part_bytes += len(line)
        if self.buffered_rows >= FSYNC_BATCH or self.part_rows >= PART_RECORD_LIMIT:
            self.sync()
        if self.part_rows >= PART_RECORD_LIMIT or self.part_bytes >= PART_BYTES_LIMIT:
            self._finish_part()

    def sync(self) -> None:
        if self.buffer:
            payload = b"".join(self.buffer)
            compressed = gzip.compress(payload, compresslevel=6, mtime=0)
            offset = self.part_compressed_bytes
            self.raw.write(compressed)
            self.raw.flush()
            os.fsync(self.raw.fileno())
            self.part_compressed_bytes += len(compressed)
            first_sequence = self.total_rows - self.buffered_rows + 1
            last_sequence = self.total_rows
            self.manifest.setdefault("durable_blocks", []).append({
                "part": self.part_path.name,
                "first_sequence": first_sequence,
                "last_sequence": last_sequence,
                "rows": self.buffered_rows,
                "byte_offset": offset,
                "compressed_bytes": len(compressed),
                "gzip_member_sha256": hashlib.sha256(compressed).hexdigest(),
                "uncompressed_sha256": hashlib.sha256(payload).hexdigest(),
            })
            self.buffer.clear()
            self.buffered_rows = 0
        if self.raw is not None:
            self.raw.flush()
            os.fsync(self.raw.fileno())
            self.manifest["committed_observation_count"] = self.total_rows
            if self.part_path is not None:
                self.manifest["active_part"] = {
                    "path": self.part_path.name,
                    "committed_rows": self.part_rows,
                    "uncompressed_bytes": self.part_bytes,
                    "committed_compressed_bytes": self.part_compressed_bytes,
                }
            self.save_manifest()

    def _finish_part(self) -> None:
        if self.raw is None:
            return
        self.sync()
        self.raw.flush()
        os.fsync(self.raw.fileno())
        self.raw.close()
        digest = sha256_file(self.part_path)
        self.parts.append({
            "path": self.part_path.name,
            "rows": self.part_rows,
            "uncompressed_bytes": self.part_bytes,
            "compressed_bytes": self.part_path.stat().st_size,
            "sha256": digest,
            "first_sequence": self.part_first_sequence,
            "last_sequence": self.total_rows,
        })
        self.part_index += 1
        self.raw = self.part_path = None
        self.manifest["active_part"] = None
        self.save_manifest()

    def close(self) -> None:
        if self.raw is not None:
            self._finish_part()
        elif self.buffer:
            self.sync()


def build_schedule(workload: dict[str, Any], discovery: dict[str, Any]):
    queries = workload.get("queries")
    candidates, support = smoke._candidate_rows(discovery)
    if workload.get("dataset") != "forest10" or workload.get("split") != "valid":
        raise RuntimeError("collector requires the official Forest10 valid split")
    if len(queries or []) != 10_000 or discovery.get("candidate_count") != 45 or support != 164_088:
        raise RuntimeError("valid workload/candidate support differs from the frozen full-run plan")
    ordered = sorted(queries, key=lambda row: int(row["source_index"]))
    indexes = [int(row["source_index"]) for row in ordered]
    if indexes != list(range(10_000)):
        raise RuntimeError("valid query source indexes must be unique and complete 0..9999")
    if any(row.get("query_id") != f"arecel:forest10:valid:{i:06d}" for i, row in enumerate(ordered)):
        raise RuntimeError("valid query IDs do not match the fixed official source-index ordering")
    per_candidate = derive_per_candidate(ordered, candidates)
    if sum(map(len, per_candidate.values())) != 164_088 or any(not ids for ids in per_candidate.values()):
        raise RuntimeError("per-query static eligibility does not reproduce the frozen 164088 pair count")
    return ordered, candidates, per_candidate


def derive_per_candidate(ordered: list[dict[str, Any]], candidates: list[tuple[str, tuple[str, str]]]) -> dict[str, tuple[str, ...]]:
    """Return only static workload eligibility; never consult cardinalities."""
    eligibility: dict[str, tuple[str, ...]] = {}
    for query in ordered:
        rows, _ = smoke._candidate_rows(discover_candidates([query], SOURCE_COLUMNS))
        eligibility[query["query_id"]] = tuple(edge for edge, _ in rows)
    return {
        edge: tuple(query["query_id"] for query in ordered if edge in eligibility[query["query_id"]])
        for edge, _ in candidates
    }


def _initial_manifest(root: Path, plan: dict[str, Any]) -> dict[str, Any]:
    return {
        "format": "ess-issue64-forest10-json-full-collection-v1",
        "status": "RUNNING",
        "completion": "INCOMPLETE_UNTIL_ALL_CALLS_AND_CONFIGURATIONS_PASS",
        "plan_sha256": PLAN_SHA256,
        "expected_calls": plan["schedule"]["total_structured_explain_calls"],
        "expected_configurations": plan["schedule"]["configuration_count"],
        "attempted_calls": 0,
        "completed_calls": 0,
        "failed_calls": 0,
        "attempted_configurations": [],
        "completed_configurations": [],
        "failed_configuration": None,
        "current_configuration": None,
        "current_configuration_committed_rows": 0,
        "committed_observation_count": 0,
        "parts": [],
        "active_part": None,
        "unattempted_calls": plan["schedule"]["total_structured_explain_calls"],
        "terminal_error": None,
        "sample": None,
        "root": str(root),
        "truth_objective_selection_test_access": False,
    }


def _record_error(exc: BaseException, phase: str) -> dict[str, str]:
    if isinstance(exc, pilot.PilotPostgreSQLFailure):
        return exc.record()
    return {"phase": phase, "error_class": type(exc).__name__}


def _worker(root: Path) -> int:
    started = time.monotonic()
    plan = json.loads(PLAN.read_text(encoding="utf-8"))
    validate_approved_plan(plan, sha256_file(PLAN))
    if (plan["retention"]["max_records_per_part"], plan["retention"]["max_uncompressed_bytes_per_part"],
            plan["retention"]["flush_fsync_every_records"],
            plan["approved_limits"]["wall_seconds_hard"], plan["approved_limits"]["wall_seconds_early_stop"],
            plan["approved_limits"]["disk_bytes_hard"], plan["approved_limits"]["disk_bytes_early_stop"]) != (
            PART_RECORD_LIMIT, PART_BYTES_LIMIT, FSYNC_BATCH, HARD_WALL_SECONDS, SOFT_WALL_SECONDS,
            HARD_DISK_BYTES, SOFT_DISK_BYTES):
        raise RuntimeError("collector code limits differ from the committed approved plan")
    root.parent.resolve()
    manifest = _initial_manifest(root, plan)
    manifest_path = root / MANIFEST
    atomic_json(manifest_path, manifest)

    def save_manifest():
        atomic_json(manifest_path, manifest)

    writer = SegmentedJsonl(root / "observations", manifest, save_manifest)
    (root / "observations").mkdir(exist_ok=True)
    phase = "preflight"
    phases: dict[str, float] = {}
    cluster_context = None
    cluster_entered = False
    restore_helpers = None
    helpers = run_formal = backend = sample = None
    pg_failures: list[dict[str, Any]] = []
    all_calls_complete = False
    try:
        if root.parent.resolve() != runtime_runs("ess-research", 64).resolve() or root.is_symlink():
            raise RuntimeError("collector run root is not an isolated Issue #64 runtime child")
        pilot._validate_socket_path(root)
        data_root = configured_root("ESS_DATA_ROOT")
        helpers, run_formal, helper_pin = pilot._load_pinned_pr58_modules(root)
        manifest["source_pins"] = {
            "postgresql_commit": pilot.ESS_POSTGRESQL_COMMIT,
            **helper_pin,
            "collector_sha256": sha256_file(Path(__file__).resolve()),
            "protocol_sha256": sha256_file(HERE / "forest10-json-only-v2.json"),
        }
        with prepare_valid_workload(issue=64, dataset="forest10", run_root=root) as prepared:
            phase = "outcome_free_full_valid_schedule"
            workload = json.loads(prepared.workload_path.read_text(encoding="utf-8"))
            if prepared.manifest.get("labels_loaded") is not False:
                raise RuntimeError("workload loader did not attest labels_loaded=false")
            ordered, candidates, per_candidate = build_schedule(
                workload, discover_candidates(workload["queries"], SOURCE_COLUMNS)
            )
            if prepared.manifest.get("archive_sha256") != plan["source_pins"]["arecel_archive_sha256"]:
                raise RuntimeError("AreCEL archive digest differs from precommitted plan")
            candidate_ids = [edge for edge, _ in candidates]
            manifest["schedule"] = {
                "dataset": "forest10", "split": "valid", "query_count": len(ordered),
                "source_index_order": "ascending 0..9999",
                "candidate_ids": candidate_ids,
                "candidate_count": len(candidate_ids),
                "static_eligible_pairs": sum(map(len, per_candidate.values())),
                "call_count": len(ordered) + sum(map(len, per_candidate.values())),
                "configuration_count": 1 + sum(bool(ids) for ids in per_candidate.values()),
                "eligibility": "runtime recomputed with pinned static candidate discovery; no truth loaded",
            }
            if (manifest["schedule"]["call_count"], manifest["schedule"]["configuration_count"]) != (174_088, 46):
                raise RuntimeError("runtime schedule differs from the committed full-valid plan")
            if manifest["schedule"]["candidate_ids"] != plan["source_pins"]["candidate_ids"]:
                raise RuntimeError("candidate IDs differ from the committed plan")
            manifest["arecel_archive_sha256"] = prepared.manifest["archive_sha256"]
            save_manifest()

            source_columns, columns, _ = _schema("forest10")
            if tuple(source_columns) != SOURCE_COLUMNS:
                raise RuntimeError("Forest10 schema order differs from the pinned contract")
            input_root = root / "input"
            prepared_root = input_root / "prepared"
            prepared_root.mkdir(parents=True)
            schema_path = prepared_root / "schema.sql"
            schema_path.write_text(
                "CREATE TABLE public.forest10 (\n" + ",\n".join(
                    f'  "{name}" {type_}' for name, type_ in columns
                ) + "\n);\n", encoding="utf-8"
            )
            input_root.mkdir(exist_ok=True)
            csv_path = input_root / "forest10-original.csv"
            pilot._extract_csv(data_root, csv_path)
            phases["pinned_csv_extract_complete"] = time.monotonic() - started
            phase = "private_postgresql_build_install"
            current_build_phase = {"name": phase}

            def note_build_phase(name: str) -> None:
                current_build_phase["name"] = name
                manifest["current_build_phase"] = name
                save_manifest()

            prefix, pg_source, build = pilot._prepare_owned_postgresql(
                root, phase_sink=note_build_phase,
                phase_times=phases,
            )
            manifest["postgresql_build"] = build
            del pg_source
            restore_helpers = pilot._install_pinned_pg_diagnostics(
                helpers, phase_sink=lambda _: None, failure_sink=pg_failures
            )
            phase = "cluster_bootstrap_sample"
            cluster_context = helpers.owned_cluster(prefix, root / "cluster", os.environ.copy())
            cluster = cluster_context.__enter__()
            cluster_entered = True
            sample, identity = run_formal.bootstrap_cluster(
                prefix, cluster, prepared_root, "forest10",
                {"catalog_columns": [name for name, _ in columns], "source_rows": EXPECTED_ROWS},
                csv_path,
            )
            sample_identity = {key: identity[key] for key in ("table", "header", "sha256")}
            validate_fresh_sample_identity(sample, sample_identity, helpers)
            manifest["sample"] = {**sample_identity, "bytes": identity["bytes"]}
            manifest["cluster"] = {"socket_dir": str(cluster["socket_dir"]), "port": cluster["port"]}
            save_manifest()
            candidate_specs = pr58_candidate_specs(candidates)
            backend = PR58Forest10Backend(
                run_formal, prefix, cluster, candidate_specs, sample, sample_identity
            )

            config_sequence = [("Empty", ())] + [
                (edge, (edge,)) for edge, _ in candidates if per_candidate[edge]
            ]
            expected_calls = 0
            for config_id, selected in config_sequence:
                phase = "configure_" + config_id
                manifest["current_configuration"] = config_id
                manifest["current_configuration_committed_rows"] = 0
                manifest["attempted_configurations"].append(config_id)
                save_manifest()
                try:
                    config_started = time.monotonic()
                    ledger = backend.configure(selected)
                    phases["configuration_" + config_id] = time.monotonic() - config_started
                except BaseException as exc:
                    manifest["failed_configuration"] = {"config_id": config_id, **_record_error(exc, phase)}
                    manifest["terminal_error"] = manifest["failed_configuration"]
                    save_manifest()
                    raise
                query_ids = [q["query_id"] for q in ordered] if config_id == "Empty" else per_candidate[config_id]
                for query_id in query_ids:
                    query = ordered[int(query_id.rsplit(":", 1)[1])]
                    manifest["attempted_calls"] += 1
                    manifest["unattempted_calls"] = 174_088 - manifest["attempted_calls"]
                    manifest["current_configuration_committed_rows"] += 1
                    expected_calls += 1
                    row = {
                        "sequence": expected_calls,
                        "query_id": query_id,
                        "config_id": config_id,
                        "static_eligible": None if config_id == "Empty" else True,
                        "diagnostics_status": None,
                        "nrows_preclamp": None,
                        "mcv_diagnostics_status": None,
                        "relation_oid": None,
                        "mcv_events": [],
                        "status": "ERROR",
                    }
                    call_started = time.monotonic()
                    try:
                        estimate = backend.preclamp_estimate(query, ledger, "")
                        obs = backend.last_observation
                        if obs is None or obs.get("query_id") != query_id or obs.get("diagnostics_status") != "complete":
                            raise RuntimeError("structured observation missing or associated with another query")
                        row.update({
                            "diagnostics_status": obs["diagnostics_status"],
                            "nrows_preclamp": str(estimate),
                            "mcv_diagnostics_status": obs["mcv_diagnostics_status"],
                            "relation_oid": obs["relation_oid"],
                            "mcv_events": obs["mcv_records"],
                            "status": "SUCCESS",
                        })
                        if estimate <= 0 or not estimate.is_finite():
                            raise ValueError("nrows_preclamp must be finite and positive")
                    except BaseException as exc:
                        row["error_class"] = type(exc).__name__
                        manifest["failed_calls"] += 1
                        writer.write(row)
                        manifest["terminal_error"] = _record_error(exc, "structured_json_" + config_id)
                        raise
                    finally:
                        phases["structured_json_seconds"] = phases.get("structured_json_seconds", 0.0) + time.monotonic() - call_started
                    manifest["completed_calls"] += 1
                    writer.write(row)
                    if writer.buffered_rows == 0:
                        save_manifest()
                writer.sync()
                manifest["completed_configurations"].append(config_id)
                manifest["current_configuration"] = None
                manifest["current_configuration_committed_rows"] = 0
                save_manifest()
            if expected_calls != 174_088:
                raise RuntimeError("completed observations differ from exact planned call count")
            all_calls_complete = True
    except BaseException as exc:
        manifest["status"] = "INCOMPLETE"
        manifest["completion"] = "PREFIX_ONLY; NOT ELIGIBLE FOR MODEL FITTING OR SELECTION"
        if manifest["terminal_error"] is None:
            manifest["terminal_error"] = _record_error(exc, phase)
        manifest["unattempted_calls"] = max(0, 174_088 - manifest["attempted_calls"])
    finally:
        writer_closed = True
        try:
            writer.close()
        except BaseException as exc:
            writer_closed = False
            try:
                manifest.update(json.loads(manifest_path.read_text(encoding="utf-8")))
            except (OSError, json.JSONDecodeError):
                pass
            manifest["status"] = "INCOMPLETE"
            manifest["terminal_error"] = {"phase": "evidence_sync", "error_class": type(exc).__name__}
        if cluster_context is not None and cluster_entered:
            try:
                cluster_context.__exit__(None, None, None)
                manifest["postgresql_shutdown"] = "PASS"
            except BaseException as exc:
                manifest["postgresql_shutdown"] = "FAIL"
                manifest["status"] = "INCOMPLETE"
                manifest["terminal_error"] = _record_error(exc, "postgresql_shutdown")
        if restore_helpers is not None:
            restore_helpers()
        for path in (root / "input" / "forest10-original.csv", root / "input" / "prepared" / "schema.sql"):
            path.unlink(missing_ok=True)
        manifest["elapsed_seconds"] = round(time.monotonic() - started, 3)
        manifest["phases_seconds"] = phases
        if writer_closed:
            manifest["attempted_calls"] = writer.total_rows
            manifest["committed_observation_count"] = writer.total_rows
        else:
            manifest["attempted_calls"] = manifest["committed_observation_count"]
        manifest["unattempted_calls"] = max(0, 174_088 - manifest["attempted_calls"])
        if (all_calls_complete and writer_closed and manifest.get("postgresql_shutdown") == "PASS"
                and manifest["attempted_calls"] == 174_088
                and manifest["completed_calls"] == 174_088
                and len(manifest["completed_configurations"]) == 46):
            manifest["status"] = "SUCCESS"
            manifest["completion"] = "ALL_174088_CALLS_AND_46_CONFIGURATIONS_COMPLETE"
            manifest["unattempted_calls"] = 0
        else:
            manifest["status"] = "INCOMPLETE"
            manifest["completion"] = "PREFIX_ONLY; NOT ELIGIBLE FOR MODEL FITTING OR SELECTION"
        save_manifest()
        pilot._merge_pg_failures(manifest, pg_failures)
        atomic_json(root / SUMMARY, {
            "status": manifest["status"], "elapsed_seconds": manifest["elapsed_seconds"],
            "attempted_calls": manifest["attempted_calls"], "completed_calls": manifest["completed_calls"],
            "failed_calls": manifest["failed_calls"], "unattempted_calls": manifest["unattempted_calls"],
            "configuration_attempts": len(manifest["attempted_configurations"]),
            "completed_configurations": len(manifest["completed_configurations"]),
            "postgresql_shutdown": manifest.get("postgresql_shutdown"),
            "manifest_sha256": sha256_file(manifest_path), "phases_seconds": phases,
        })
    return 0 if manifest["status"] == "SUCCESS" else 2


def _mark_supervisor_exit(root: Path, return_code: int) -> None:
    path = root / MANIFEST
    if not path.exists():
        return
    manifest = json.loads(path.read_text())
    if manifest.get("status") == "RUNNING" or (return_code != 0 and manifest.get("status") == "SUCCESS"):
        manifest["status"] = "INCOMPLETE"
        manifest["completion"] = "SUPERVISOR_STOPPED_WORKER; PREFIX_ONLY"
        manifest["terminal_error"] = {"phase": "supervisor", "return_code": return_code}
        manifest["unattempted_calls"] = max(0, 174_088 - manifest.get("committed_observation_count", 0))
        atomic_json(path, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(description="Full-valid JSON observation collector; collection only.")
    parser.add_argument("--researcher-approved", action="store_true")
    parser.add_argument("--worker", type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        return _worker(args.worker.resolve())
    if not args.researcher_approved:
        raise SystemExit("refusing collector execution without explicit --researcher-approved")
    try:
        plan = json.loads(PLAN.read_text(encoding="utf-8"))
        validate_approved_plan(plan, sha256_file(PLAN))
    except (OSError, json.JSONDecodeError, RuntimeError) as exc:
        raise SystemExit(f"refusing full-valid collection before runtime allocation: {exc}") from exc
    runs = runtime_runs("ess-research", 64)
    runs.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(runs).free < HARD_DISK_BYTES:
        raise SystemExit("insufficient free space for the proposed 4-GiB cap")
    root = Path(tempfile.mkdtemp(prefix=RUN_PREFIX, dir=runs))
    (root / "observations").mkdir()
    manifest = _initial_manifest(root, plan)
    atomic_json(root / MANIFEST, manifest)
    print(f"FULL_VALID_COLLECTOR_RUN_ROOT={root}", flush=True)
    rc = pilot._supervise(
        root,
        worker_command=[sys.executable, str(Path(__file__).resolve()), "--worker", str(root)],
        soft_wall_seconds=SOFT_WALL_SECONDS, hard_wall_seconds=HARD_WALL_SECONDS,
        soft_disk_bytes=SOFT_DISK_BYTES, hard_disk_bytes=HARD_DISK_BYTES,
        worker_summary_name=SUMMARY,
        summary_format="ess-issue64-forest10-full-collector-supervisor-v1",
    )
    _mark_supervisor_exit(root, rc)
    return rc


if __name__ == "__main__":
    raise SystemExit(main())
