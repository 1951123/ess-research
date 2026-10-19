"""Explicit protocol/input catalog and fail-closed evidence helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

MANIFEST_NAME = "protocol-v3.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(root: Path) -> dict[str, Any]:
    return json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))


def input_paths(root: Path, protocol_id: str, *, gate_a: bool = False) -> list[Path]:
    manifest = load_manifest(root)
    corpus = manifest["corpora"][protocol_id]
    files = corpus["gate_a_files"] if gate_a else corpus["files"]
    expected = corpus["hashes"]
    result: list[Path] = []
    for name in files:
        path = root / "instances" / name
        if not path.is_file():
            raise FileNotFoundError(f"manifest input is missing: {path}")
        actual = sha256(path)
        if actual != expected[name]:
            raise ValueError(
                f"manifest input hash mismatch for {name}: expected {expected[name]}, got {actual}"
            )
        result.append(path)
    if len(result) != len(set(result)):
        raise ValueError("manifest contains duplicate input paths")
    return result


def write_json_once(path: Path, payload: Any) -> None:
    """Write a new evidence file only; reruns must choose a new path."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
