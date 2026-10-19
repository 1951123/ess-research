"""Read-only adapter to the pinned ess-advisor APIs for Gate A and baselines."""

from __future__ import annotations

import dataclasses
import json
import platform
import time
from fractions import Fraction
from pathlib import Path
from typing import Any

import networkx
import numpy
import scipy

from pess_ess.model import read_instance
from pess_ess.solvers_v2 import MasterOracleOptions, solve_master_oracle, solve_static


ADVISOR_SHA = "1052ff4a46270c90414d76b32d6f6b37e5908f6a"


def jsonable(value: Any) -> Any:
    if isinstance(value, Fraction):
        return str(value)
    if dataclasses.is_dataclass(value):
        return {key: jsonable(item) for key, item in dataclasses.asdict(value).items()}
    if isinstance(value, frozenset | set | tuple):
        return [jsonable(item) for item in value]
    if isinstance(value, dict):
        return {str(key): jsonable(item) for key, item in value.items()}
    return value


def environment() -> dict[str, Any]:
    return {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "numpy": numpy.__version__,
        "scipy": scipy.__version__,
        "networkx": networkx.__version__,
        "advisor_sha": ADVISOR_SHA,
        "highs": "SciPy 1.18.1 bundled HiGHS; standalone HiGHS version is not exposed by the SciPy Python API",
    }


def run_solver(
    instance_path: str | Path,
    method: str,
    total_time_limit: float,
    inner_time_limit: float | None = None,
    options: MasterOracleOptions | None = None,
) -> dict[str, Any]:
    instance = read_instance(instance_path)
    started = time.perf_counter()
    if method == "static":
        result = solve_static(instance, total_time_limit=total_time_limit)
    elif method == "master_oracle":
        result = solve_master_oracle(
            instance,
            total_time_limit=total_time_limit,
            inner_time_limit=inner_time_limit,
            certification_tolerance=0.0,
            cut_tolerance=1e-6,
            options=options or MasterOracleOptions(),
        )
    else:
        raise ValueError(f"unknown advisor method: {method}")
    wall = time.perf_counter() - started
    return {
        "instance": str(instance_path),
        "method": method,
        "options": jsonable(options or MasterOracleOptions()) if method == "master_oracle" else {},
        "limits": {
            "total_time_limit": total_time_limit,
            "inner_time_limit": inner_time_limit,
            "certification_tolerance": 0.0,
            "cut_tolerance": 1e-6,
        },
        "wall_seconds": wall,
        "within_total_limit": wall <= total_time_limit + 0.25,
        "environment": environment(),
        "result": jsonable(result),
    }


def write_result(path: str | Path, record: dict[str, Any]) -> None:
    Path(path).write_text(json.dumps(record, indent=2, sort_keys=True) + "\n", encoding="utf-8")
