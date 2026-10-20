import hashlib
import json
import unittest
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory

from reclassify_v8 import require_fresh_outputs


ROOT = Path(__file__).parent
SUMMARY = ROOT / "eligibility-reclassification-summary.json"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


class ReclassificationEvidenceTests(unittest.TestCase):
    def test_committed_ledger_hash_and_status_totals(self):
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        ledger = ROOT / "eligibility-reclassification-ledger.jsonl"
        self.assertEqual(sha256_file(ledger), summary["redacted_ledger_sha256"])
        rows = [json.loads(line) for line in ledger.read_text(encoding="utf-8").splitlines() if line]
        self.assertEqual(len(rows), summary["redacted_ledger_row_count"])
        self.assertEqual(
            Counter(row["status"] for row in rows),
            Counter(summary["reclassified_status_counts"]),
        )
        self.assertEqual(sum(row["legacy_graph_failed"] for row in rows), summary["legacy_graph_failed_count"])

    def test_external_hashes_when_preserved_runtime_is_available(self):
        summary = json.loads(SUMMARY.read_text(encoding="utf-8"))
        external = [
            (Path(summary["source_observations_path"]), summary["source_observations_sha256"]),
            (Path(summary["reclassification_output_path"]), summary["reclassification_output_sha256"]),
        ]
        missing = [str(path) for path, _ in external if not path.is_file()]
        if missing:
            self.skipTest("preserved external runtime artifacts unavailable: " + ", ".join(missing))
        for path, expected in external:
            self.assertEqual(sha256_file(path), expected)

    def test_derived_outputs_must_be_fresh(self):
        with TemporaryDirectory() as directory:
            existing = Path(directory) / "derived.json"
            existing.write_text("prior\n", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                require_fresh_outputs([existing, Path(directory) / "ledger.jsonl"])


if __name__ == "__main__":
    unittest.main()
