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


def cramers_v(rows: list[tuple[int, int, int]], n: int) -> float:
    row_totals = Counter()
    column_totals = Counter()
    for left, right, count in rows:
        row_totals[left] += count
        column_totals[right] += count
    chi2 = 0.0
    for left, right, count in rows:
        expected = row_totals[left] * column_totals[right] / n
        chi2 += (count - expected) ** 2 / expected
    dimensions = min(len(row_totals), len(column_totals))
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--psql", type=Path, required=True)
    parser.add_argument("--host", required=True)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--database", required=True)
    parser.add_argument("--user", default="postgres")
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
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

    row_counts: dict[str, int] = {}
    grouped: dict[str, dict[str, list[tuple[int, int, int]]]] = {}
    for line in result.stdout.splitlines():
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
    output = args.output_dir / "fixture-metrics.json"
    output.write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
