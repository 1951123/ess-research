"""Execute Gate A adapter checks before approximate-search comparisons."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from advisor_adapter import run_solver
from reference import exhaustive, load, verify_selected


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path(__file__).parent)
    parser.add_argument("--limit", type=float, default=5.0)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    root = args.root
    paths = sorted((root / "instances").glob("tiny_*.json"))
    records: list[dict[str, object]] = []
    failures: list[str] = []
    for path in paths:
        instance = load(path)
        truth = exhaustive(instance)
        row: dict[str, object] = {
            "instance": path.name,
            "fraction_truth": {
                "objective": str(truth["objective"]),
                "optimal_sets": [sorted(item) for item in truth["optimal_sets"]],
                "feasible_subsets": truth["feasible_subsets"],
                "evaluated_subsets": truth["evaluated_subsets"],
            },
            "methods": {},
        }
        for method in ("static", "master_oracle"):
            record = run_solver(path, method, args.limit, inner_time_limit=args.limit)
            result = record["result"]
            selected = result.get("selected")
            objective = result.get("objective")
            check = None
            if selected is not None and objective is not None:
                try:
                    check = verify_selected(instance, selected, objective)
                    if check["objective"] != str(truth["objective"]):
                        raise AssertionError("returned objective is not the independent optimum")
                except AssertionError as exc:
                    failures.append(f"{path.name}/{method}: {exc}")
            else:
                failures.append(f"{path.name}/{method}: no validated incumbent (status={result.get('status')})")
            row["methods"][method] = {"adapter": record, "independent_check": check}
        records.append(row)

    payload = {
        "gate": "A",
        "status": "PASS" if not failures else "FAIL",
        "independent_reference": "Fraction exhaustive outer and labeled maximal-matching evaluation",
        "records": records,
        "failures": failures,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit("Gate A failed: " + "; ".join(failures))
    print(json.dumps({"gate": "A", "status": "PASS", "instances": len(records)}, sort_keys=True))


if __name__ == "__main__":
    main()
