#!/usr/bin/env python3
"""Collect deterministic association diagnostics for the maintenance fixture.

This runs before the timing schedule.  Its SQL is deliberately outside every
timed ANALYZE interval and its grouped counts are retained as provenance.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import subprocess
from collections import Counter
from pathlib import Path


TABLES = {
    "weakassoc": "ess_mcv_weakassoc",
    "correlated": "ess_mcv_correlated",
}
PAIRS = {"ab": ("a", "b"), "bc": ("b", "c"), "cd": ("c", "d")}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def cramers_v(
    rows: list[tuple[int, int, int]],
    n: int,
    row_levels: list[int] | None = None,
    column_levels: list[int] | None = None,
) -> float:
    """Compute Cramer's V over the complete positive-marginal table support.

    ``rows`` is the sparse output of ``GROUP BY`` and therefore contains only
    nonzero cells.  The chi-square sum must still visit every row/column
    combination, assigning zero to absent cells.  The observed support is
    sufficient here because every listed level has a positive marginal.
    Explicit levels are accepted for the regression tests and for callers
    that retain a wider categorical domain.
    """
    if n <= 0:
        raise ValueError("Cramer's V requires a positive total count")
    row_totals = Counter()
    column_totals = Counter()
    observed = {}
    for left, right, count in rows:
        row_totals[left] += count
        column_totals[right] += count
        observed[(left, right)] = observed.get((left, right), 0) + count
    row_levels = sorted(row_totals if row_levels is None else set(row_levels))
    column_levels = sorted(
        column_totals if column_levels is None else set(column_levels)
    )
    row_levels = [level for level in row_levels if row_totals.get(level, 0) > 0]
    column_levels = [
        level for level in column_levels if column_totals.get(level, 0) > 0
    ]
    chi2_terms = []
    for left in row_levels:
        for right in column_levels:
            expected = row_totals[left] * column_totals[right] / n
            if expected <= 0:
                continue
            count = observed.get((left, right), 0)
            chi2_terms.append((count - expected) ** 2 / expected)
    chi2 = math.fsum(chi2_terms)
    dimensions = min(len(row_levels), len(column_levels))
    if dimensions <= 1:
        return 0.0
    return math.sqrt(chi2 / (n * (dimensions - 1)))


def sql_text() -> str:
    lines: list[str] = []
    for regime, table in TABLES.items():
        lines.append(f"SELECT 'ROWS|{regime}|' || count(*)::text FROM {table};")
        for pair, (left, right) in PAIRS.items():
            lines.append(
                f"SELECT 'PAIR|{regime}|{pair}|' || {left}::text || '|' || "
                f"{right}::text || '|' || count(*)::text FROM {table} "
                f"GROUP BY {left}, {right} ORDER BY {left}, {right};"
            )
    return "\n".join(lines) + "\n"


def parse_metrics_output(output: str) -> tuple[dict[str, int], dict[str, dict[str, list[tuple[int, int, int]]]]]:
    row_counts: dict[str, int] = {}
    grouped: dict[str, dict[str, list[tuple[int, int, int]]]] = {}
    for line in output.splitlines():
        fields = line.split("|")
        if fields[0] == "ROWS":
            row_counts[fields[1]] = int(fields[2])
        elif fields[0] == "PAIR":
            regime, pair = fields[1], fields[2]
            grouped.setdefault(regime, {}).setdefault(pair, []).append(
                (int(fields[3]), int(fields[4]), int(fields[5]))
            )
        else:
            raise SystemExit(f"unexpected metrics row: {line!r}")
    return row_counts, grouped


def build_metrics(output: str) -> dict[str, object]:
    row_counts, grouped = parse_metrics_output(output)
    metrics: dict[str, object] = {
        "schema_version": 1,
        "association_metric": (
            "Cramer's V computed from the exact categorical contingency table; "
            "pair_distinct is the number of distinct observed value pairs"
        ),
        "row_counts": row_counts,
        "regimes": {},
        "realized_sample_rows_observed": False,
    }
    regimes = metrics["regimes"]
    assert isinstance(regimes, dict)
    for regime in TABLES:
        pairs: dict[str, object] = {}
        for pair in PAIRS:
            rows = grouped.get(regime, {}).get(pair, [])
            n = row_counts[regime]
            pairs[pair] = {
                "pair_distinct": len(rows),
                "cramers_v": cramers_v(rows, n),
                "nonzero_cells": sum(1 for row in rows if row[2] > 0),
                "total_count_from_groups": sum(row[2] for row in rows),
            }
        regimes[regime] = {"pairs": pairs}
    return metrics


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--psql", type=Path)
    parser.add_argument("--host")
    parser.add_argument("--port", type=int)
    parser.add_argument("--database")
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument(
        "--offline-stdout",
        type=Path,
        help="rebuild only derived metrics from an existing psql.stdout.log",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.offline_stdout is not None:
        output_text = args.offline_stdout.read_text(encoding="utf-8")
        args.output_dir.mkdir(parents=True, exist_ok=True)
    else:
        if args.psql is None:
            raise SystemExit("--psql is required unless --offline-stdout is used")
        if args.host is None or args.port is None or args.database is None:
            raise SystemExit("--host, --port, and --database are required for live collection")
        args.output_dir.mkdir(parents=True, exist_ok=False)
        sql = sql_text()
        command = [
            str(args.psql),
            "-X",
            "-v",
            "ON_ERROR_STOP=1",
            "-At",
            "-F",
            "|",
            "-h",
            args.host,
            "-p",
            str(args.port),
            "-U",
            args.user,
            "-d",
            args.database,
        ]
        result = subprocess.run(
            command,
            input=sql,
            text=True,
            capture_output=True,
            check=False,
            env={**os.environ, "LC_ALL": "C"},
        )
        (args.output_dir / "psql-command.json").write_text(
            json.dumps(command, indent=2) + "\n", encoding="utf-8"
        )
        (args.output_dir / "metrics.sql").write_text(sql, encoding="utf-8")
        (args.output_dir / "psql.stdout.log").write_text(result.stdout, encoding="utf-8")
        (args.output_dir / "psql.stderr.log").write_text(result.stderr, encoding="utf-8")
        if result.returncode != 0:
            raise SystemExit(result.returncode)
        output_text = result.stdout

    metrics = build_metrics(output_text)
    output = args.output_dir / "fixture-metrics.json"
    output.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
