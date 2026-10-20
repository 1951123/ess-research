"""Fail-closed PR #58 code/validation-input hash verifier.

The whitelist intentionally excludes diagnostic outputs, held-out ledgers,
test truth and PostgreSQL measurement files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any


HERE = Path(__file__).resolve().parent
RELATIVE_PATHS = {
    "formal_runner_source_sha256": "run_formal.py",
    "independent_validation_source_sha256": "validate_log_coefficient_fix.py",
    "regression_test_source_sha256": "test_log_coefficient_validation.py",
    "frozen_protocol_v4_sha256": "protocol-v4.json",
    "validation_manifest_sha256": "runs/empty-selection-log-fix-20261020-v1/manifest.json",
    "forest10_validation_calibration_ledger": "runs/formal-20261020-v4/forest10/validation-calibration-ledger.jsonl",
    "forest10_validation_model": "runs/formal-20261020-v4/forest10/validation-model.json",
    "census13_validation_calibration_ledger": "runs/formal-20261020-v4/census13/validation-calibration-ledger.jsonl",
    "census13_validation_model": "runs/formal-20261020-v4/census13/validation-model.json",
}


def expected_hashes(protocol: dict[str, Any]) -> dict[str, str]:
    pin = protocol["provenance"]["corrected_log_reference_pin"]
    result = {
        "formal_runner_source_sha256": pin["formal_runner_source_sha256"],
        "independent_validation_source_sha256": pin["independent_validation_source_sha256"],
        "regression_test_source_sha256": pin["regression_test_source_sha256"],
        "frozen_protocol_v4_sha256": pin["frozen_protocol_v4_sha256"],
        "validation_manifest_sha256": pin["manifest_sha256"],
    }
    result.update(pin["validation_only_input_sha256"])
    return result


def verify_files(root: Path, expected: dict[str, str]) -> list[str]:
    errors: list[str] = []
    if set(expected) != set(RELATIVE_PATHS):
        return ["expected pin keys do not exactly match the read-only whitelist"]
    root = root.resolve(strict=True)
    for key, relative in RELATIVE_PATHS.items():
        path = root / relative
        try:
            resolved = path.resolve(strict=True)
            resolved.relative_to(root)
            actual = hashlib.sha256(resolved.read_bytes()).hexdigest()
        except (OSError, ValueError) as exc:
            errors.append(f"{key}: unavailable or outside whitelist root ({exc})")
            continue
        if actual != expected[key]:
            errors.append(f"{key}: SHA-256 mismatch (expected {expected[key]}, got {actual})")
    return errors


def verify_commit_ancestry(root: Path, commit: str) -> list[str]:
    try:
        repository = subprocess.check_output(
            ["git", "-C", str(root), "rev-parse", "--show-toplevel"], text=True
        ).strip()
        subprocess.run(
            ["git", "-C", repository, "merge-base", "--is-ancestor", commit, "HEAD"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        return [f"pinned corrected-log commit is not verified as an ancestor of this PR #58 checkout ({exc})"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--pr58-stage2b-root",
        required=True,
        type=Path,
        help="PR #58 experiments/pess-multidataset-heldout-stage2b directory",
    )
    args = parser.parse_args()
    protocol = json.loads((HERE / "protocol-v1.json").read_text(encoding="utf-8"))
    pin = protocol["provenance"]["corrected_log_reference_pin"]
    expected = expected_hashes(protocol)
    errors = verify_commit_ancestry(args.pr58_stage2b_root, pin["validation_diagnostic_code_commit"])
    errors.extend(verify_files(args.pr58_stage2b_root, expected))
    if errors:
        for error in errors:
            print(f"FAIL: {error}")
        return 1
    print("PASS: pinned PR #58 corrected-log source and validation-only inputs")
    print("SCOPE: no diagnostic output, held-out estimate, test truth or PG measurement file was read")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
