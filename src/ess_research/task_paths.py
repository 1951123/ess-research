"""Explicit machine roots; importing this module never consults configuration."""

from __future__ import annotations

import os
import re
from pathlib import Path


class ConfigurationError(ValueError):
    """A required root or explicit task identity is missing or invalid."""


def configured_root(name: str) -> Path:
    examples = {
        "ESS_DATA_ROOT": "ess-data",
        "ESS_WORKTREE_PARENT": "ess-worktrees",
        "ESS_RUNTIME_PARENT": "ess-runtime",
    }
    example = examples[name]
    hint = f'Configure explicitly in ~/.bashrc, for example: export {name}="$HOME/{example}"'
    value = os.environ.get(name, "")
    if not value.strip():
        raise ConfigurationError(f"{name} is unset or empty. {hint}")
    path = Path(value).expanduser()
    if not path.is_absolute() or path == Path("/"):
        raise ConfigurationError(
            f"{name} must be an absolute non-root directory. {hint}"
        )
    try:
        path = path.resolve()
        if path == Path("/"):
            raise ValueError("resolves to filesystem root")
        for parent in (path, *path.parents):
            if parent.exists():
                if not parent.is_dir():
                    raise ValueError(f"not a directory: {parent}")
                if not os.access(parent, os.W_OK | os.X_OK):
                    raise ValueError(f"directory is not writable/searchable: {parent}")
                break
    except (OSError, ValueError, RuntimeError) as exc:
        raise ConfigurationError(f"invalid {name}: {exc}. {hint}") from exc
    return path


def task_identity(repository: str, issue: int) -> str:
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", repository):
        raise ConfigurationError("provide a simple repository slug explicitly")
    if isinstance(issue, bool) or not isinstance(issue, int) or issue <= 0:
        raise ConfigurationError(
            "provide a positive Issue number explicitly (e.g. --issue 48)"
        )
    return f"{repository}-issue{issue}"


def worktree_path(repository: str, issue: int) -> Path:
    """Resolve only; Git owns creation and refuses an occupied destination."""
    identity = task_identity(repository, issue)
    return configured_root("ESS_WORKTREE_PARENT") / identity


def runtime_runs(repository: str, issue: int) -> Path:
    task_identity(repository, issue)
    root = configured_root("ESS_RUNTIME_PARENT")
    runs = root / repository / f"issue{issue}" / "runs"
    # A pre-existing task-directory symlink could redirect writes into another
    # Issue or the raw cache even though the configured roots are disjoint.
    for path in (runs, runs.parent, runs.parent.parent):
        if path.is_symlink():
            raise ConfigurationError(f"runtime task path must not be a symlink: {path}")
    return runs
