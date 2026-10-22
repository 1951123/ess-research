from __future__ import annotations

import io
import pickle
import sys
import tarfile
import unittest
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from ess_research.arecel import archive as arecel_archive
import fit_forest10_valid_and_freeze as fitter


def label_archive(test_first_cardinality: int) -> bytes:
    values = {
        "valid": [arecel_archive.Label(index % 17, 0.5) for index in range(10_000)],
        "test": [arecel_archive.Label(test_first_cardinality, 0.99)],
    }
    payload = pickle.dumps(values, protocol=4)
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
        info = tarfile.TarInfo("data/forest10/workload/base-original-label.pkl")
        info.size = len(payload)
        tar.addfile(info, io.BytesIO(payload))
    return buffer.getvalue()


class ValidTruthIsolationTests(unittest.TestCase):
    def test_only_valid_labels_affect_returned_truth_and_hash(self):
        observed = []
        for test_truth in (1, 999_999_999):
            payload = label_archive(test_truth)

            @contextmanager
            def open_fake_archive(_cache):
                yield io.BytesIO(payload)

            with patch.object(arecel_archive, "_archive", side_effect=open_fake_archive):
                truth, summary = fitter.load_valid_truth(Path("unused"))
            observed.append((truth, summary))

        self.assertEqual(observed[0], observed[1])
        truth, summary = observed[0]
        self.assertEqual(len(truth), 10_000)
        self.assertEqual(truth["arecel:forest10:valid:000000"], 0)
        self.assertEqual(summary["valid_truth_zero_count"], "589")
        self.assertEqual(summary["valid_truth_values_sha256"], observed[1][1]["valid_truth_values_sha256"])


if __name__ == "__main__":
    unittest.main()
