"""Emit reproducible schema-only cohort stratum capacity evidence as JSON."""

from __future__ import annotations

import json
import hashlib
import argparse
from pathlib import Path

from schema_capacity import (
    ARECEL_GENERATOR_PIN,
    SCHEMA_SOURCE_PINS,
    capacity_table,
    revised_predicate_quota,
    verify_schema_source_pins,
)


HERE = Path(__file__).parent
ROOT = HERE.parents[2]
PROTOCOL = HERE / "protocol-v1.json"


def build_report() -> dict[str, object]:
    verify_schema_source_pins(ROOT)
    protocol = json.loads(PROTOCOL.read_text(encoding="utf-8"))
    datasets = {}
    for dataset in ("forest10", "census13", "dmv11", "power7"):
        table = capacity_table(dataset, protocol["candidate_universe"][dataset])
        table["provisional_split_quota"] = revised_predicate_quota(table)
        table["joint_bin_operator_graph_zero_cells_omitted"] = True
        table["joint_bin_operator_graph_capacity_upper_bound"] = {
            key: value
            for key, value in table["joint_bin_operator_graph_capacity_upper_bound"].items()
            if value > 0
        }
        datasets[dataset] = table
    return {
        "format": "issue64-schema-capacity-report-v2",
        "evidence_label": "OUTCOME_FREE_SCHEMA_ONLY_COMBINATORIAL_UPPER_BOUNDS",
        "source_pins": SCHEMA_SOURCE_PINS,
        "arecel_generator_pin": ARECEL_GENERATOR_PIN,
        "analysis_code_sha256": hashlib.sha256((HERE / "schema_capacity.py").read_bytes()).hexdigest(),
        "report_builder_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "operator_support": "numeric: =,<,<=,>,>=,[]; categorical: = only",
        "graph_classes": [
            "zero-edges", "one-edge", "multiple-disjoint-edges",
            "conflict-one-maximal-matching", "conflict-multiple-maximal-matchings",
        ],
        "split_rule": protocol["cohort_generation_recipe"]["split_assignment"],
        "datasets": datasets,
        "limitations": [
            "No source table rows, literals, historical outcome records, test truths, test estimates, or PostgreSQL traces were read.",
            "Capacities are pre-quarantine schema upper bounds; actual one-million-attempt split pools must independently satisfy quotas or freeze is BLOCKED. The complete historical fingerprint quarantine and fixed-attempt pool have not been run.",
            "The d=1 bin has no mandatory minimum; d=2 targets reserve at least half of each exact split capacity. Quotas in this report remain provisional until the outcome-free pool gate passes.",
            "The 1-predicate and 2-predicate finite spaces are exactly enumerated and split-hashed; larger-bin capacities are global combinatorial counts, not split-specific guarantees.",
            "No claim is made that a future cohort was generated or that data/literal feasibility is established.",
        ],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = json.dumps(build_report(), sort_keys=True, indent=2, ensure_ascii=False) + "\n"
    if args.output is None:
        print(payload, end="")
    else:
        with args.output.open("x", encoding="utf-8") as stream:
            stream.write(payload)
