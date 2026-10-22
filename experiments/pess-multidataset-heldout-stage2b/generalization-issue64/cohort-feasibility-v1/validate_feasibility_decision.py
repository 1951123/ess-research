"""Check that the BLOCKED record preserves frozen seeds and quota targets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def validate(protocol: dict[str, Any], decision: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    recipe = protocol["cohort_generation_recipe"]
    selection = recipe["selection_and_size"]
    if decision.get("status") != "BLOCKED_SPECIFICATION_AMBIGUITY":
        errors.append("decision must remain BLOCKED_SPECIFICATION_AMBIGUITY")
    if decision.get("block_point") != "before_attempt_0" or decision.get("attempts_executed") != 0:
        errors.append("blocked evidence must certify zero attempted candidates")
    if decision.get("seeds") != recipe["seed_by_dataset"]:
        errors.append("dataset seeds differ from frozen protocol")
    if decision.get("maximum_attempts_per_dataset") != selection["maximum_template_attempts_per_dataset"]:
        errors.append("attempt cap differs from frozen protocol")
    quotas = selection["schema_capacity_gate"]["quota_by_dataset_split"]
    for dataset, splits in quotas.items():
        recorded = decision.get("datasets", {}).get(dataset, {})
        for split, expected_bins in splits.items():
            row = recorded.get(split)
            if row is None:
                errors.append(f"missing {dataset}/{split} record")
                continue
            if row.get("predicate_bin_targets") != expected_bins:
                errors.append(f"quota changed for {dataset}/{split}")
            if row.get("actual_groups") is not None or row.get("actual_predicate_bin_counts") is not None:
                errors.append(f"unrun candidate counts must remain NOT EVALUATED for {dataset}/{split}")
    if decision.get("prospective_zero_collision_gate") != "BLOCKED_NOT_RUN":
        errors.append("prospective zero-collision gate must remain blocked/not run")
    return errors


def main() -> int:
    base = Path(__file__).parent.parent
    protocol = json.loads((base / "protocol-v1.json").read_text(encoding="utf-8"))
    decision = json.loads((Path(__file__).parent / "cohort-feasibility-decision-v1.json").read_text(encoding="utf-8"))
    errors = validate(protocol, decision)
    print(json.dumps({"status": "PASS" if not errors else "FAIL", "errors": errors}, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
