"""Small write-once helpers for immutable experiment evidence."""

from __future__ import annotations

import os
from pathlib import Path


def write_text_exclusive(path: Path, text: str) -> None:
    """Create *path* exactly once and refuse existing files or symlinks."""

    path.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags, 0o644)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            descriptor = -1
            handle.write(text)
    finally:
        if descriptor != -1:
            os.close(descriptor)
