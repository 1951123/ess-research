from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from verify_portable_manifest import verify_manifest


def item(kind: str, sha: str, **kwargs: str) -> dict[str, str]:
    return {"kind": kind, "source_id": "test-input", "sha256": sha, **kwargs}


class PortableManifestTests(unittest.TestCase):
    def test_repo_and_external_inputs_verify(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            data = Path(directory) / "data"
            (root / "docs").mkdir(parents=True)
            data.mkdir()
            (root / "docs" / "source.txt").write_bytes(b"repo bytes")
            (data / "archive.bin").write_bytes(b"archive bytes")
            manifest = {"inputs": [
                item("repo_file", hashlib.sha256(b"repo bytes").hexdigest(), path="docs/source.txt"),
                item("external_file", hashlib.sha256(b"archive bytes").hexdigest(), root_env="DATA_ROOT", relative_path="archive.bin"),
            ]}
            self.assertEqual(verify_manifest(root, manifest, {"DATA_ROOT": str(data)}), [])

    def test_git_blob_uses_injected_immutable_reader(self) -> None:
        manifest = {"inputs": [item("git_blob", hashlib.sha256(b"frozen").hexdigest(), commit="a" * 40, path="protocol-v4.json")]}
        self.assertEqual(verify_manifest(Path("."), manifest, {}, lambda _commit, _path: b"frozen"), [])

    def test_missing_external_root_and_hash_mismatch_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "source.txt").write_bytes(b"actual")
            manifest = {"inputs": [
                item("external_file", "0" * 64, root_env="MISSING_ROOT", relative_path="archive.bin"),
                item("repo_file", "0" * 64, path="source.txt"),
            ]}
            errors = verify_manifest(root, manifest, {})
            self.assertEqual(len(errors), 2)

    def test_absolute_traversal_and_symlink_escape_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "repo"
            outside = Path(directory) / "outside.txt"
            root.mkdir()
            outside.write_bytes(b"secret")
            (root / "escape").symlink_to(outside)
            manifest = {"inputs": [
                item("repo_file", "0" * 64, path="../outside.txt"),
                item("repo_file", "0" * 64, path=str(outside)),
                item("repo_file", "0" * 64, path="escape"),
            ]}
            self.assertEqual(len(verify_manifest(root, manifest, {})), 3)


if __name__ == "__main__":
    unittest.main()
