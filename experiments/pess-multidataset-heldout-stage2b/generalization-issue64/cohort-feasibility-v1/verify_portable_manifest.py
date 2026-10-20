#!/usr/bin/env python3
"""Verify portable, outcome-free Issue #64 source pins.

The manifest intentionally contains no machine-specific absolute paths. Git
objects and external inputs are addressed by immutable source identifiers.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Any, Callable


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def safe_repo_path(root: Path, relative: str) -> Path:
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts or not relative:
        raise ValueError(f"unsafe non-relative repository path: {relative!r}")
    resolved_root = root.resolve()
    resolved = (resolved_root / candidate).resolve(strict=True)
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"repository path escapes root: {relative!r}")
    return resolved


def git_blob(commit: str, path: str) -> bytes:
    if not commit or any(ch not in "0123456789abcdef" for ch in commit.lower()):
        raise ValueError("git object commit must be hexadecimal")
    if Path(path).is_absolute() or ".." in Path(path).parts:
        raise ValueError("unsafe git object path")
    return subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout


def verify_manifest(
    root: Path,
    manifest: dict[str, Any],
    environ: dict[str, str] | None = None,
    git_reader: Callable[[str, str], bytes] = git_blob,
) -> list[str]:
    env = os.environ if environ is None else environ
    errors: list[str] = []
    for item in manifest.get("inputs", []):
        name = item.get("source_id", "<unnamed>")
        try:
            kind = item["kind"]
            expected = item["sha256"]
            if len(expected) != 64 or any(ch not in "0123456789abcdef" for ch in expected):
                raise ValueError("invalid expected SHA-256")
            if kind == "repo_file":
                data = safe_repo_path(root, item["path"]).read_bytes()
            elif kind == "external_file":
                variable = item["root_env"]
                if variable not in env or not env[variable]:
                    raise ValueError(f"required environment variable {variable} is unset")
                relative = Path(item["relative_path"])
                if relative.is_absolute() or ".." in relative.parts:
                    raise ValueError("unsafe external relative path")
                base = Path(env[variable]).resolve(strict=True)
                candidate = (base / relative).resolve(strict=True)
                if candidate != base and base not in candidate.parents:
                    raise ValueError("external input escapes configured root")
                data = candidate.read_bytes()
            elif kind == "git_blob":
                data = git_reader(item["commit"], item["path"])
            else:
                raise ValueError(f"unsupported input kind {kind!r}")
            actual = sha256_bytes(data)
            if actual != expected:
                raise ValueError(f"SHA-256 mismatch: expected {expected}, got {actual}")
        except (KeyError, OSError, ValueError, subprocess.CalledProcessError) as exc:
            errors.append(f"{name}: {exc}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--repo-root", type=Path)
    args = parser.parse_args()
    root = args.repo_root or Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"], check=True, text=True, capture_output=True
        ).stdout.strip()
    )
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    errors = verify_manifest(root, manifest)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
