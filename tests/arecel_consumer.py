"""Read-only integration consumer for the documented real-archive CLI check.

Uses only generated files and Python's standard library. Does not import the
ETL, read historical derived data, or start PostgreSQL. Its concise result is
written outside derived, in this consuming run's results directory.
"""

import csv
import json
import os
from pathlib import Path


def main():
    root = Path(os.environ["ESS_ARECEL_DATASET_ROOT"])
    run = Path(os.environ["ESS_ISSUE_ROOT"])
    manifest = json.loads((root / "manifest.json").read_text())
    dataset = manifest["dataset"]
    expected = {
        "forest10": (581012, 10),
        "census13": (48842, 13),
        "dmv11": (11591877, 11),
        "power7": (2075259, 7),
    }
    rows, width = expected[dataset]
    with (root / "table.csv").open(newline="") as stream:
        reader = csv.reader(stream)
        assert len(next(reader)) == width
        actual_rows = 0
        for row in reader:
            assert len(row) == width
            actual_rows += 1
        assert actual_rows == rows, (actual_rows, rows)
    split_results = {}
    for split, count in manifest["splits"].items():
        workload = json.loads((root / split / "workload.json").read_text())
        truth = json.loads((root / split / "truth.json").read_text())
        assert workload["dataset"] == truth["dataset"] == dataset
        assert workload["split"] == truth["split"] == split
        assert len(workload["queries"]) == len(truth["queries"]) == count
        for index, (query, label) in enumerate(
            zip(workload["queries"], truth["queries"], strict=True)
        ):
            assert (
                query["query_id"]
                == label["query_id"]
                == f"arecel:{dataset}:{split}:{index:06d}"
            )
            assert query["source_index"] == label["source_index"] == index
            assert "true_cardinality" not in query
            assert query["sql"].startswith(f"SELECT * FROM public.{dataset} WHERE ")
            assert isinstance(label["true_cardinality"], int)
            assert 0 <= label["true_cardinality"] <= rows
        split_results[split] = count
    result = {
        "dataset": dataset,
        "rows": actual_rows,
        "columns": width,
        "splits": split_results,
        "status": "PASS",
        "pg_executed": False,
    }
    with (run / "results/consumer-check.json").open("x") as output:
        json.dump(result, output, sort_keys=True)
        output.write("\n")
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
