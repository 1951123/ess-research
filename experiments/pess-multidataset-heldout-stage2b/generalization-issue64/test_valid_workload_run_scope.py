from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from ess_research.arecel import archive
from ess_research.task_paths import ConfigurationError


class ValidWorkloadRunScopeTests(unittest.TestCase):
    def test_explicit_run_root_must_be_the_issue_run_child(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            data_root = root / "read-only-input"
            runtime_parent = root / "runtime"
            runs = runtime_parent / "ess-research" / "issue64" / "runs"
            outside = root / "other-task"
            data_root.mkdir()
            outside.mkdir()
            runs.mkdir(parents=True)
            with (
                patch.object(archive, "configured_root", side_effect=lambda name: {
                    "ESS_DATA_ROOT": data_root,
                    "ESS_RUNTIME_PARENT": runtime_parent,
                }[name]),
                patch.object(archive, "runtime_runs", return_value=runs),
                self.assertRaisesRegex(ConfigurationError, "direct child"),
            ):
                with archive.prepare_valid_workload(issue=64, dataset="forest10", run_root=outside):
                    self.fail("out-of-run derived data path unexpectedly accepted")


if __name__ == "__main__":
    unittest.main()
