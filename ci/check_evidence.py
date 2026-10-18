#!/usr/bin/env python3
"""Read-only integrity checks for committed experiment evidence.

The historical manifests use two path conventions: paths relative to the
manifest's directory, and repository-root-relative paths beginning with
"experiments/". Both are supported; paths outside the repository are rejected.
This script never regenerates results or alters historical evidence.
"""

from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

EXPECTED_MANIFESTS = (
    "experiments/pg-maintenance/runs/20261017-issue7-v4/SHA256SUMS",
    "experiments/pg-maintenance/runs/20261017-issue7-v5-target300-20rep/SHA256SUMS",
    "experiments/pg-maintenance/fixed-target-cpu/runs/20261018-issue9-v1/SHA256SUMS",
    "experiments/pg-tracing/runs/20261017-numeric/review-followup-20261017/SHA256SUMS",
)
COMPLETE_RUN = EXPECTED_MANIFESTS[2]
IGNORED_IN_COMPLETE_RUN = frozenset({"SHA256SUMS", "checksums-verify.txt"})
ENTRY = re.compile(r"^([0-9a-fA-F]{64})  (.+)$")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def verify_manifest(manifest: Path, root: Path, *, complete: bool = False) -> tuple[int, list[str]]:
    """Return (number of checked files, errors), without modifying files."""
    root = root.resolve()
    manifest = manifest.resolve()
    errors: list[str] = []
    checked: set[Path] = set()

    try:
        manifest.relative_to(root)
    except ValueError:
        return 0, [f"manifest outside repository: {manifest}"]

    if not manifest.is_file():
        return 0, [f"missing manifest: {manifest}"]

    for line_number, line in enumerate(manifest.read_text(encoding="utf-8").splitlines(), 1):
        match = ENTRY.fullmatch(line)
        if not match:
            errors.append(f"{manifest}:{line_number}: invalid checksum line")
            continue
        expected, name = match.groups()
        relative = Path(name)
        if relative.is_absolute() or ".." in relative.parts or "\\" in name:
            errors.append(f"{manifest}:{line_number}: unsafe path {name!r}")
            continue

        # Only the legacy PG tracing manifest uses repository-relative names.
        candidate = (root / relative if name.startswith("experiments/") else manifest.parent / relative)
        resolved = candidate.resolve()
        try:
            resolved.relative_to(root)
        except ValueError:
            errors.append(f"{manifest}:{line_number}: path escapes repository: {name!r}")
            continue

        if resolved in checked:
            errors.append(f"{manifest}:{line_number}: duplicate entry {name!r}")
            continue
        checked.add(resolved)
        if not resolved.is_file():
            errors.append(f"{manifest}:{line_number}: missing file {name!r}")
        elif sha256(resolved).lower() != expected.lower():
            errors.append(f"{manifest}:{line_number}: checksum mismatch {name!r}")

    if not checked:
        errors.append(f"{manifest}: empty checksum manifest")

    if complete:
        actual = {
            path.resolve()
            for path in manifest.parent.rglob("*")
            if path.is_file() and path.name not in IGNORED_IN_COMPLETE_RUN
        }
        missing_entries = actual - checked
        for path in sorted(missing_entries):
            errors.append(f"{manifest}: unlisted evidence file {path.relative_to(root)}")
    return len(checked), errors


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    historical = [root / path for path in EXPECTED_MANIFESTS]
    discovered = sorted((root / "experiments").rglob("*SHA256SUMS"))
    manifests = sorted(set(historical).union(discovered))
    errors: list[str] = []
    files_checked = 0
    for manifest in manifests:
        relative = manifest.relative_to(root).as_posix()
        count, problems = verify_manifest(manifest, root, complete=relative == COMPLETE_RUN)
        files_checked += count
        if problems:
            errors.extend(problems)
            print(f"FAIL {relative} ({count} entries, {len(problems)} problems)")
        else:
            print(f"OK   {relative} ({count} files)")
    if errors:
        for problem in errors:
            print(problem, file=sys.stderr)
        print(f"FAILED: {len(errors)} integrity errors", file=sys.stderr)
        return 1
    print(f"PASS: {len(manifests)} manifests; {files_checked} committed evidence files verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
