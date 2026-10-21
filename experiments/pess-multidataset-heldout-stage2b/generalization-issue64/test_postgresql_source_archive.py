from __future__ import annotations

import hashlib
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(HERE))
import run_forest10_setup_pilot as pilot


class PinnedPostgreSQLArchiveTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.runs_root = self.root / "runtime" / "ess-research" / "issue64" / "runs"
        self.runs_root.mkdir(parents=True)
        self.run_root = self.runs_root / "run-test"
        self.run_root.mkdir()
        self.object_store = self.root / "ess-postgresql"
        self.object_store.mkdir()
        subprocess.run(["git", "init", "--quiet", str(self.object_store)], check=True)
        self.source_bytes = b"pinned synthetic PostgreSQL source\n"
        (self.object_store / "configure").write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
        source_file = self.object_store / "src/backend/commands/analyze_sample_cache.c"
        source_file.parent.mkdir(parents=True)
        source_file.write_bytes(self.source_bytes)
        subprocess.run(["git", "-C", str(self.object_store), "add", "configure", "src"], check=True)
        env = dict(os.environ, GIT_AUTHOR_NAME="Source Test", GIT_AUTHOR_EMAIL="source@test.invalid",
                   GIT_COMMITTER_NAME="Source Test", GIT_COMMITTER_EMAIL="source@test.invalid")
        subprocess.run(
            ["git", "-C", str(self.object_store), "commit", "--quiet", "-m", "synthetic source"],
            check=True, env=env,
        )
        self.commit = subprocess.run(
            ["git", "-C", str(self.object_store), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        self.sample_hash = hashlib.sha256(self.source_bytes).hexdigest()
        self.pins = patch.multiple(
            pilot,
            runtime_runs=lambda *_: self.runs_root,
            ESS_POSTGRESQL_OBJECT_STORE=self.object_store,
            ESS_POSTGRESQL_COMMIT=self.commit,
            SAMPLE_IMPORT_SOURCE_SHA256=self.sample_hash,
        )
        self.pins.start()
        self.addCleanup(self.pins.stop)

    def test_exports_exact_commit_inside_the_run_without_git_metadata(self) -> None:
        (self.object_store / "untracked-local-file").write_text("must not be exported\n", encoding="utf-8")
        source, commit = pilot._materialize_pinned_postgresql_source(self.run_root)
        self.assertEqual(commit, self.commit)
        self.assertEqual(source, self.run_root / "postgresql" / "source")
        self.assertEqual((source / "src/backend/commands/analyze_sample_cache.c").read_bytes(), self.source_bytes)
        self.assertTrue((source / "configure").is_file())
        self.assertFalse((source / ".git").exists())
        self.assertFalse((source / "untracked-local-file").exists())

    def test_missing_commit_fails_without_remote_fallback(self) -> None:
        commands: list[list[str]] = []
        real_run = subprocess.run

        def record_run(command: list[str], *args, **kwargs):
            commands.append(command)
            return real_run(command, *args, **kwargs)

        with patch.object(pilot, "ESS_POSTGRESQL_COMMIT", "0" * 40), patch.object(
            pilot.subprocess, "run", side_effect=record_run
        ):
            with self.assertRaisesRegex(RuntimeError, "failed during rev-parse"):
                pilot._materialize_pinned_postgresql_source(self.run_root)
        self.assertEqual(len(commands), 1)
        self.assertIn(str(self.object_store), commands[0])
        self.assertNotIn("fetch", commands[0])
        self.assertFalse((self.run_root / "postgresql" / "source").exists())

    def test_wrong_resolved_commit_fails_closed(self) -> None:
        real_run = subprocess.run

        def wrong_resolution(command: list[str], *args, **kwargs):
            if len(command) > 3 and command[3] == "rev-parse":
                return subprocess.CompletedProcess(command, 0, stdout="f" * 40 + "\n", stderr="")
            return real_run(command, *args, **kwargs)

        with patch.object(pilot.subprocess, "run", side_effect=wrong_resolution):
            with self.assertRaisesRegex(RuntimeError, "different commit"):
                pilot._materialize_pinned_postgresql_source(self.run_root)
        self.assertFalse((self.run_root / "postgresql" / "source").exists())

    def test_archive_extraction_failure_is_explicit(self) -> None:
        real_run = subprocess.run

        def corrupt_archive(command: list[str], *args, **kwargs):
            if len(command) > 3 and command[3] == "archive":
                return subprocess.CompletedProcess(command, 0, stdout=b"not a tar archive", stderr=b"")
            return real_run(command, *args, **kwargs)

        with patch.object(pilot.subprocess, "run", side_effect=corrupt_archive):
            with self.assertRaisesRegex(RuntimeError, "archive extraction failed"):
                pilot._materialize_pinned_postgresql_source(self.run_root)

    def test_source_hash_mismatch_fails_closed(self) -> None:
        with patch.object(pilot, "SAMPLE_IMPORT_SOURCE_SHA256", "0" * 64):
            with self.assertRaisesRegex(RuntimeError, "source SHA-256 mismatch"):
                pilot._materialize_pinned_postgresql_source(self.run_root)


if __name__ == "__main__":
    unittest.main()
