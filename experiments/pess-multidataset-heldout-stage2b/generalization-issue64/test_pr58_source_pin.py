from __future__ import annotations

import hashlib
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
import sys

sys.path.insert(0, str(HERE))
import run_forest10_setup_pilot as pilot


class PR58PerRunSourceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.runs_root = self.root / "runtime" / "ess-research" / "issue64" / "runs"
        self.runs_root.mkdir(parents=True)
        self.run_root = self.runs_root / "run-test"
        self.run_root.mkdir()
        self.remote = self.root / "pinned-source"
        self.remote.mkdir()
        subprocess.run(["git", "init", "--quiet", str(self.remote)], check=True)
        self.files = {
            pilot.PR58_HELPER_FILES[0]: b"import gate_audit_v2\nSOURCE_MARKER = 'pinned-run-formal'\n",
            pilot.PR58_HELPER_FILES[1]: b"SOURCE_MARKER = 'pinned-gate-audit'\n",
            "unrelated/history-report.json": b"not checked out\n",
        }
        for relative, content in self.files.items():
            path = self.remote / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        subprocess.run(["git", "-C", str(self.remote), "add", "."], check=True)
        env = {
            "GIT_AUTHOR_NAME": "Synthetic Test",
            "GIT_AUTHOR_EMAIL": "test@example.invalid",
            "GIT_COMMITTER_NAME": "Synthetic Test",
            "GIT_COMMITTER_EMAIL": "test@example.invalid",
        }
        subprocess.run(
            ["git", "-C", str(self.remote), "commit", "--quiet", "-m", "synthetic pinned source"],
            check=True,
            env=env,
        )
        self.commit = subprocess.run(
            ["git", "-C", str(self.remote), "rev-parse", "HEAD"],
            check=True, capture_output=True, text=True,
        ).stdout.strip()
        self.hashes = {
            "run_formal": hashlib.sha256(self.files[pilot.PR58_HELPER_FILES[0]]).hexdigest(),
            "gate_audit": hashlib.sha256(self.files[pilot.PR58_HELPER_FILES[1]]).hexdigest(),
        }
        self.pins = patch.multiple(
            pilot,
            runtime_runs=lambda *_: self.runs_root,
            PR58_REPOSITORY_URL=str(self.remote),
            PR58_SOURCE_COMMIT=self.commit,
            PR58_RUN_FORMAL_SHA256=self.hashes["run_formal"],
            PR58_GATE_AUDIT_SHA256=self.hashes["gate_audit"],
        )
        self.pins.start()
        self.addCleanup(self.pins.stop)
        self.addCleanup(self.temp.cleanup)

    def test_fetches_only_pinned_helpers_inside_each_run(self) -> None:
        helper_dir = pilot._fetch_pinned_pr58_source(self.run_root)
        self.assertEqual(helper_dir, self.run_root / "pr58-source" / "experiments" / "pess-multidataset-heldout-stage2b")
        self.assertEqual(pilot._sha256(helper_dir / "run_formal.py"), self.hashes["run_formal"])
        self.assertEqual(pilot._sha256(helper_dir / "gate_audit_v2.py"), self.hashes["gate_audit"])
        checked_out = {
            path.relative_to(self.run_root / "pr58-source").as_posix()
            for path in (self.run_root / "pr58-source").rglob("*")
            if path.is_file() and ".git" not in path.parts
        }
        self.assertEqual(checked_out, set(pilot.PR58_HELPER_FILES))
        self.assertFalse((self.run_root / "pr58-source" / "unrelated" / "history-report.json").exists())

    def test_imports_helper_modules_from_this_run_checkout(self) -> None:
        try:
            helpers, runner, metadata = pilot._load_pinned_pr58_modules(self.run_root)
            self.assertEqual(helpers.SOURCE_MARKER, "pinned-gate-audit")
            self.assertEqual(runner.SOURCE_MARKER, "pinned-run-formal")
            self.assertEqual(Path(helpers.__file__).resolve(), pilot._pinned_pr58_root(self.run_root) / "gate_audit_v2.py")
            self.assertEqual(Path(runner.__file__).resolve(), pilot._pinned_pr58_root(self.run_root) / "run_formal.py")
            self.assertEqual(metadata["pr58_source_commit"], self.commit)
        finally:
            sys.modules.pop("run_formal", None)
            sys.modules.pop("gate_audit_v2", None)
            source_path = str(pilot._pinned_pr58_root(self.run_root))
            if source_path in sys.path:
                sys.path.remove(source_path)

    def test_refuses_a_fetched_commit_mismatch(self) -> None:
        actual_runner = pilot._run_pr58_git

        def wrong_fetch_head(source_root: Path, args: list[str]) -> str:
            output = actual_runner(source_root, args)
            if args == ["rev-parse", "FETCH_HEAD"]:
                return "f" * 40
            return output

        with patch.object(pilot, "_run_pr58_git", side_effect=wrong_fetch_head):
            with self.assertRaisesRegex(RuntimeError, "fetched commit mismatch"):
                pilot._fetch_pinned_pr58_source(self.run_root)

    def test_refuses_helper_hash_mismatch(self) -> None:
        with patch.object(pilot, "PR58_RUN_FORMAL_SHA256", "0" * 64):
            with self.assertRaisesRegex(RuntimeError, "run_formal.py SHA-256 mismatch"):
                pilot._fetch_pinned_pr58_source(self.run_root)

    def test_unavailable_source_fails_without_fallback(self) -> None:
        with patch.object(pilot, "PR58_REPOSITORY_URL", str(self.root / "missing-repository")):
            with self.assertRaisesRegex(RuntimeError, "source acquisition failed during git fetch"):
                pilot._fetch_pinned_pr58_source(self.run_root)

    def test_run_path_is_direct_child_and_never_sibling_worktree(self) -> None:
        other = self.runs_root / "run-other"
        other.mkdir()
        self.assertNotEqual(pilot._pinned_pr58_root(self.run_root), pilot._pinned_pr58_root(other))
        self.assertEqual(pilot._pinned_pr58_root(self.run_root).parents[2], self.run_root)
        source = (HERE / "run_forest10_setup_pilot.py").read_text(encoding="utf-8")
        self.assertNotIn("ess-research-issue48", source)
        with self.assertRaisesRegex(RuntimeError, "direct, non-symlink Issue #64 run directory"):
            pilot._fetch_pinned_pr58_source(self.root)

    def test_pinned_repository_identity_and_production_hashes_are_fixed(self) -> None:
        self.pins.stop()
        self.assertEqual(pilot.PR58_REPOSITORY_URL, "https://github.com/1951123/ess-research.git")
        self.assertEqual(pilot.PR58_SOURCE_COMMIT, "76106024611ae91505f1f05bdc35aed44d9c38c4")
        self.assertEqual(pilot.PR58_RUN_FORMAL_SHA256, "61300085320e97c057d26d1b354ad219253e34a3cb39f5ff783a9c8d446b4322")
        self.assertEqual(pilot.PR58_GATE_AUDIT_SHA256, "03823ad30b0ab4e7073b347ebfddb5578467cad28cb28f0ae8768dd233a855c4")


if __name__ == "__main__":
    unittest.main()
