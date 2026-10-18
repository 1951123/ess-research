#!/usr/bin/env python3
"""Create and verify a complete checksum manifest for one Issue #9 run.

The manifest covers every regular file in the run directory except the
manifest itself and this verifier's transcript.  Raw measurement bytes are
read only; only derived validation files are written.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import tempfile
from pathlib import Path


MANIFEST_NAME = "SHA256SUMS"
TRANSCRIPT_NAME = "checksums-verify.txt"


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def manifest_lines(run_dir: Path) -> list[str]:
    paths = sorted(
        path.relative_to(run_dir).as_posix()
        for path in run_dir.rglob("*")
        if path.is_file() and path.name not in {MANIFEST_NAME, TRANSCRIPT_NAME}
    )
    return [f"{digest(run_dir / relative)}  {relative}" for relative in paths]


def atomic_write(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", delete=False
    ) as handle:
        temporary = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("run_dir", type=Path)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    run_dir = args.run_dir.resolve()
    if not run_dir.is_dir():
        raise SystemExit(f"missing run directory: {run_dir}")

    manifest = run_dir / MANIFEST_NAME
    atomic_write(manifest, "\n".join(manifest_lines(run_dir)) + "\n")
    print(f"wrote {manifest}")
    if not args.verify:
        return 0

    completed = subprocess.run(
        ["sha256sum", "-c", MANIFEST_NAME],
        cwd=run_dir,
        text=True,
        capture_output=True,
        check=False,
    )
    transcript = (
        "$ sha256sum -c SHA256SUMS\n"
        + completed.stdout
        + completed.stderr
        + f"exit_status={completed.returncode}\n"
    )
    atomic_write(run_dir / TRANSCRIPT_NAME, transcript)
    print(transcript, end="")
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
