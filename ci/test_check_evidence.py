"""Negative and positive checks for the read-only evidence manifest validator."""

from __future__ import annotations

import hashlib
from pathlib import Path

from ci.check_evidence import verify_manifest


def fixture(tmp_path: Path) -> tuple[Path, Path, Path, str]:
    root = tmp_path
    run_dir = root / "experiments" / "pg-maintenance" / "runs" / "demo"
    run_dir.mkdir(parents=True)
    data = run_dir / "sample.txt"
    data.write_bytes(b"unchanged raw observation\n")
    digest = hashlib.sha256(data.read_bytes()).hexdigest()
    manifest = run_dir / "SHA256SUMS"
    return root, manifest, data, digest


def test_manifest_accepts_local_paths_without_modifying_evidence(tmp_path: Path) -> None:
    root, manifest, data, digest = fixture(tmp_path)
    manifest.write_text(f"{digest}  ./sample.txt\n", encoding="utf-8")
    before = data.read_bytes()
    count, errors = verify_manifest(manifest, root, complete=True)
    assert (count, errors) == (1, [])
    assert data.read_bytes() == before


def test_manifest_accepts_repository_relative_paths(tmp_path: Path) -> None:
    root, manifest, data, digest = fixture(tmp_path)
    name = data.relative_to(root).as_posix()
    manifest.write_text(f"{digest}  {name}\n", encoding="utf-8")
    count, errors = verify_manifest(manifest, root)
    assert (count, errors) == (1, [])


def test_modified_evidence_is_rejected(tmp_path: Path) -> None:
    root, manifest, data, digest = fixture(tmp_path)
    manifest.write_text(f"{digest}  sample.txt\n", encoding="utf-8")
    data.write_text("tampered\n", encoding="utf-8")
    _, errors = verify_manifest(manifest, root)
    assert any("checksum mismatch" in error for error in errors)


def test_missing_evidence_and_unlisted_files_are_rejected(tmp_path: Path) -> None:
    root, manifest, _, digest = fixture(tmp_path)
    manifest.write_text(f"{digest}  missing.txt\n", encoding="utf-8")
    _, errors = verify_manifest(manifest, root, complete=True)
    assert any("missing file" in error for error in errors)
    assert any("unlisted evidence file" in error for error in errors)


def test_duplicate_entries_are_rejected(tmp_path: Path) -> None:
    root, manifest, _, digest = fixture(tmp_path)
    manifest.write_text(f"{digest}  sample.txt\n{digest}  ./sample.txt\n", encoding="utf-8")
    _, errors = verify_manifest(manifest, root)
    assert any("duplicate entry" in error for error in errors)


def test_parent_directory_escape_is_rejected(tmp_path: Path) -> None:
    root, manifest, _, digest = fixture(tmp_path)
    manifest.write_text(f"{digest}  ../../outside.txt\n", encoding="utf-8")
    _, errors = verify_manifest(manifest, root)
    assert any("unsafe path" in error for error in errors)
