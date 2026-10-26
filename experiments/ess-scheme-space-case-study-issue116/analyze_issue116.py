#!/usr/bin/env python3
"""Read-only Census13 Train scheme-space case study for Issue #116."""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
from decimal import Decimal
from fractions import Fraction
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
FROZEN_PATH = ROOT / "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json"
PROTOCOL_PATH = ROOT / "experiments/add-only-greedy-issue99/protocol-v4.json"
DATASET = "census13"
SCALE = 10**18
MAX_COMPACT_GAMMA = 8

CASE_TO_SET = {
    "census13-nominal-b3": "M3_shared",
    "census13-pess-b3": "M3_shared",
    "census13-nominal-b4": "M4_nominal",
    "census13-pess-b4": "M4_pess",
    "census13-nominal-b5": "M5_nominal",
    "census13-pess-b5": "M5_pess",
}
EXPECTED_SETS = {
    "M3_shared": ("e01_05", "e02_03", "e04_06"),
    "M4_nominal": ("e01_05", "e02_03", "e04_06", "e06_08"),
    "M4_pess": ("e00_11", "e01_05", "e02_03", "e04_06"),
    "M5_nominal": ("e01_05", "e02_03", "e04_06", "e04_08", "e06_08"),
    "M5_pess": ("e00_11", "e01_05", "e02_03", "e04_06", "e07_12"),
}


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def exact_units(value: str | Fraction) -> int:
    scaled = Fraction(value) * SCALE
    if scaled.denominator != 1:
        raise ValueError(f"coefficient is not quantized to 1e-18: {value}")
    return scaled.numerator


def mask_ids(mask: int, selected: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(selected[index] for index in range(len(selected)) if mask & (1 << index))


def scheme_changed(left: dict[tuple[str, ...], int], right: dict[tuple[str, ...], int]) -> bool:
    return set(left) != set(right) or any(left[key] != right[key] for key in set(left) & set(right))


def primary_eligible(ambiguous: bool, positive_risk: bool, changed: bool, gamma_size: int) -> bool:
    return ambiguous and positive_risk and changed and gamma_size <= MAX_COMPACT_GAMMA


def load_issue103(source_root: Path, advisor_source: Path):
    script_path = source_root / "experiments/oid-priority-permutation-issue103/run_issue103.py"
    summary_path = script_path.with_name("summary-v1.json")
    summary_bytes = summary_path.read_bytes()
    summary = json.loads(summary_bytes)
    script_sha = sha256_file(script_path)
    if (
        summary.get("issue") != 103
        or summary.get("status") != "COMPLETE"
        or summary.get("analysis_script_sha256") != script_sha
    ):
        raise ValueError("Issue #103 script/summary provenance is not internally consistent")
    pinned_script = subprocess.run(
        [
            "git",
            "show",
            f"{summary['analysis_source_commit']}:experiments/oid-priority-permutation-issue103/run_issue103.py",
        ],
        cwd=source_root,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    ).stdout
    if sha256_bytes(pinned_script) != script_sha:
        raise ValueError("Issue #103 script differs from its recorded analysis source commit")
    if (
        sha256_file(source_root / "experiments/add-only-greedy-issue99/frozen-train-resources-issue96-v1.json")
        != sha256_file(FROZEN_PATH)
        or sha256_file(source_root / "experiments/add-only-greedy-issue99/protocol-v4.json")
        != sha256_file(PROTOCOL_PATH)
        or sha256_file(source_root / "experiments/add-only-greedy-issue99/run_issue99.py")
        != sha256_file(ROOT / "experiments/add-only-greedy-issue99/run_issue99.py")
    ):
        raise ValueError("Issue #103 worktree inputs differ from the current frozen Issue #99 inputs")

    spec = importlib.util.spec_from_file_location("issue103_readonly", script_path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load the read-only Issue #103 helpers")
    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(script_path.parent))
    spec.loader.exec_module(module)
    return module, summary, sha256_bytes(summary_bytes), script_sha


def render_task_set(name: str, row: dict[str, Any], candidates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    selected = row["selected"]
    gamma = []
    for matching, loss in sorted(row["losses"].items()):
        gamma.append(
            {
                "matching_ids": list(matching),
                "matching_endpoints": {edge: candidates[edge]["endpoints"] for edge in matching},
                "loss_fraction": str(Fraction(loss, SCALE)),
                "is_nominal": matching == row["nominal_matching"],
                "is_pess_maximizer": loss == row["pess_units"],
            }
        )
    return {
        "selected_ids": list(selected),
        "task_applicable_edges": [
            {"id": edge, "endpoints": candidates[edge]["endpoints"]} for edge in row["active"]
        ],
        "conflict_pairs": [list(pair) for pair in row["conflicts"]],
        "gamma_size": len(gamma),
        "gamma_definition": "all labeled inclusion-wise maximal matchings of M intersect E_i",
        "gamma": gamma,
        "nominal_matching_ids": list(row["nominal_matching"]),
        "nominal_loss_fraction": str(Fraction(row["nominal_units"], SCALE)),
        "pess_loss_fraction": str(Fraction(row["pess_units"], SCALE)),
        "pess_maximizer_matching_ids": [list(matching) for matching in row["pess_ties"]],
        "risk_fraction": str(Fraction(row["risk_units"], SCALE)),
    }


def analyze(args: argparse.Namespace) -> dict[str, Any]:
    issue103, prior_summary, prior_summary_sha, prior_script_sha = load_issue103(
        args.issue103_source, args.advisor_source
    )
    runner = issue103._load_issue99_runner()
    frozen, all_cases = issue103._load_frozen_inputs(runner)
    cases = all_cases[DATASET]
    frozen_ds = frozen["datasets"][DATASET]
    issue103._verify_selection_run(
        DATASET,
        frozen_ds,
        cases,
        (args.runtime_parent / "ess-research/issue99/runs").resolve(strict=True),
    )
    (collection_root, collection, queries, candidate_rows, eligible, truth, empty,
     singleton, observation_aggregate) = issue103._load_train_inputs(
        DATASET,
        frozen_ds,
        cases,
        runner,
        (args.runtime_parent / "ess-research/issue99/runs").resolve(strict=True),
    )
    model, reference, advisor_hashes = issue103._load_pinned_reference(
        args.advisor_source, runner.PROTOCOL["source_pins"]["advisor_source_commit"]
    )

    archive_path = args.data_root / "arecel-data.tar.gz"
    archive_sha = sha256_file(archive_path)
    if archive_sha != runner.PROTOCOL["source_pins"]["arecel_archive_sha256"]:
        raise ValueError("configured AreCEL archive hash differs from the frozen Issue #99 pin")
    if sha256_file(FROZEN_PATH) != prior_summary["frozen_selection_sha256"]:
        raise ValueError("Issue #103 summary uses a different frozen selection file")
    protocol_sha = sha256_file(PROTOCOL_PATH)
    if protocol_sha != prior_summary["issue99_protocol_sha256"]:
        raise ValueError("Issue #103 summary uses a different Issue #99 protocol")

    candidates = {row["id"]: row for row in candidate_rows}
    candidate_ids = [row["id"] for row in candidate_rows]
    cases_by_id = {row["case_id"]: row for row in cases}
    sets = {}
    for name, case_id in (
        ("M3_shared", "census13-nominal-b3"),
        ("M4_nominal", "census13-nominal-b4"),
        ("M4_pess", "census13-pess-b4"),
        ("M5_nominal", "census13-nominal-b5"),
        ("M5_pess", "census13-pess-b5"),
    ):
        selected = tuple(edge for edge in candidate_ids if edge in set(cases_by_id[case_id]["selected_ids"]))
        if selected != EXPECTED_SETS[name]:
            raise ValueError(f"frozen Issue #99 set changed for {case_id}")
        sets[name] = selected

    expected_coefficient = frozen_ds["model_fit"]["coefficient_digest_sha256"]
    model_digest = hashlib.sha256()
    coefficient_count = 0
    stats = {
        name: {
            "selected_ids": list(selected),
            "task_count": 0,
            "active_edge_incidence_count": 0,
            "tasks_with_any_selected_edge": 0,
            "conflict_bearing_task_count": 0,
            "ambiguous_gamma_task_count": 0,
            "positive_risk_task_count": 0,
            "positive_risk_without_conflict_task_count": 0,
            "conflict_bearing_zero_risk_task_count": 0,
            "nonconflicting_zero_risk_task_count": 0,
            "max_gamma_size": 0,
            "gamma_size_counts": {},
            "nominal_units": 0,
            "pess_units": 0,
            "risk_units": 0,
        }
        for name, selected in sets.items()
    }
    first_primary = first_ambiguous_positive = first_scheme_change = first_conflict_zero = None
    criteria_counts = {key: 0 for key in (
        "ambiguous_gamma", "positive_nominal_set_risk", "both", "B5_set_scheme_or_loss_change", "all_primary_conditions"
    )}

    for index, query in enumerate(queries):
        query_id = query["query_id"]
        n0 = max(Decimal(1), Decimal(empty[index]))
        alpha = runner._log_ratio(n0, max(1, truth[query_id]))
        alpha_units = issue103.exact_units(alpha)
        available = eligible[query_id]
        correction_text = {}
        correction_units = {}
        for edge in available:
            value = runner._log_ratio(max(Decimal(1), Decimal(singleton[edge][index])), n0)
            correction_text[edge] = value
            correction_units[edge] = issue103.exact_units(value)
            coefficient_count += 1
        model_row = {
            "query_id": query_id,
            "alpha": alpha,
            "b": correction_text,
            "available_edges": list(available),
        }
        model_digest.update((json.dumps(model_row, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode())

        task_rows = {}
        for name, selected in sets.items():
            active_mask = sum(1 << position for position, edge in enumerate(selected) if edge in correction_units)
            endpoints = [tuple(candidates[edge]["endpoints"]) for edge in selected]
            coefficients = tuple(correction_units.get(edge, 0) for edge in selected)
            masks = issue103.maximal_matching_masks(active_mask, endpoints)
            losses = {mask_ids(mask, selected): issue103.task_loss_units(alpha_units, coefficients, mask) for mask in masks}
            nominal_mask = issue103.priority_matching_masks(
                active_mask, (tuple(range(len(selected))),), endpoints
            )[0]
            nominal_matching = mask_ids(nominal_mask, selected)
            if nominal_matching not in losses:
                raise AssertionError(f"Nominal priority did not produce a maximal scheme: {query_id}/{name}")
            nominal_units = losses[nominal_matching]
            pess_units = max(losses.values())
            pess_ties = tuple(sorted(matching for matching, loss in losses.items() if loss == pess_units))
            active = tuple(edge for edge in selected if edge in correction_units)
            conflicts = tuple(
                (left, right)
                for i, left in enumerate(active)
                for right in active[i + 1:]
                if set(candidates[left]["endpoints"]) & set(candidates[right]["endpoints"])
            )
            risk_units = pess_units - nominal_units
            if risk_units < 0 or (risk_units and not conflicts):
                raise AssertionError(f"invalid PESS-minus-Nominal task risk: {query_id}/{name}")
            row = {
                "selected": selected,
                "active": active,
                "conflicts": conflicts,
                "losses": losses,
                "nominal_matching": nominal_matching,
                "nominal_units": nominal_units,
                "pess_units": pess_units,
                "pess_ties": pess_ties,
                "risk_units": risk_units,
            }
            task_rows[name] = row
            item = stats[name]
            item["task_count"] += 1
            item["active_edge_incidence_count"] += len(active)
            item["tasks_with_any_selected_edge"] += bool(active)
            item["conflict_bearing_task_count"] += bool(conflicts)
            item["ambiguous_gamma_task_count"] += len(losses) > 1
            item["positive_risk_task_count"] += risk_units > 0
            item["positive_risk_without_conflict_task_count"] += risk_units > 0 and not conflicts
            item["conflict_bearing_zero_risk_task_count"] += bool(conflicts) and risk_units == 0
            item["nonconflicting_zero_risk_task_count"] += not conflicts and risk_units == 0
            item["max_gamma_size"] = max(item["max_gamma_size"], len(losses))
            gamma_size = str(len(losses))
            item["gamma_size_counts"][gamma_size] = item["gamma_size_counts"].get(gamma_size, 0) + 1
            item["nominal_units"] += nominal_units
            item["pess_units"] += pess_units
            item["risk_units"] += risk_units

        nominal = task_rows["M5_nominal"]
        pess_set = task_rows["M5_pess"]
        ambiguous = len(nominal["losses"]) >= 2
        positive = nominal["risk_units"] > 0
        changed = scheme_changed(nominal["losses"], pess_set["losses"])
        all_conditions = primary_eligible(ambiguous, positive, changed, len(nominal["losses"]))
        criteria_counts["ambiguous_gamma"] += ambiguous
        criteria_counts["positive_nominal_set_risk"] += positive
        criteria_counts["both"] += ambiguous and positive
        criteria_counts["B5_set_scheme_or_loss_change"] += changed
        criteria_counts["all_primary_conditions"] += all_conditions
        detail = {"task_id": query_id, "rows": task_rows}
        if ambiguous and positive and first_ambiguous_positive is None:
            first_ambiguous_positive = detail
        if changed and first_scheme_change is None:
            first_scheme_change = detail
        if nominal["conflicts"] and not positive and first_conflict_zero is None:
            first_conflict_zero = detail
        if all_conditions and first_primary is None:
            first_primary = detail
        if (index + 1) % 25_000 == 0:
            print(json.dumps({"event": "train_progress", "tasks": index + 1}), flush=True)

    if model_digest.hexdigest() != expected_coefficient:
        raise ValueError("reconstructed full Census13 coefficient digest differs from Issue #99")
    if coefficient_count != frozen_ds["model_fit"]["coefficient_count"]:
        raise ValueError("reconstructed coefficient count differs from Issue #99")

    for name, item in stats.items():
        if item["task_count"] != 100_000:
            raise AssertionError(f"{name} did not cover all frozen Train tasks")
        nominal = Fraction(item.pop("nominal_units"), SCALE)
        pess = Fraction(item.pop("pess_units"), SCALE)
        risk = Fraction(item.pop("risk_units"), SCALE)
        if nominal + risk != pess or item["positive_risk_without_conflict_task_count"] != 0:
            raise AssertionError(f"whole-Train aggregate identity or conflict implication failed: {name}")
        item.update({
            "nominal_loss_sum_fraction": str(nominal),
            "pess_loss_sum_fraction": str(pess),
            "weighted_task_risk_sum_fraction": str(risk),
            "whole_train_nominal_plus_risk_equals_pess": True,
            "positive_risk_only_on_conflict_bearing_tasks": True,
        })

    prior_census = next(row for row in prior_summary["datasets"] if row["dataset"] == DATASET)
    prior_sets = {tuple(row["selected_ids"]): row for row in prior_census["sets"]}
    prior_crosschecks = {}
    for name, selected in sets.items():
        prior = prior_sets[tuple(selected)]
        if (
            Fraction(stats[name]["nominal_loss_sum_fraction"]) != Fraction(prior["nominal_fraction"])
            or Fraction(stats[name]["pess_loss_sum_fraction"]) != Fraction(prior["pess_fraction"])
        ):
            raise AssertionError(f"whole-Train totals differ from Issue #103 exact result: {name}")
        prior_crosschecks[name] = {
            "nominal_fraction_matches": True,
            "pess_fraction_matches": True,
            "issue103_nominal_fraction": prior["nominal_fraction"],
            "issue103_pess_fraction": prior["pess_fraction"],
        }

    if first_primary:
        displayed_witnesses = [first_primary]
        witness_mode = "single_predeclared_witness"
    else:
        displayed_witnesses = []
        for candidate in (first_ambiguous_positive, first_scheme_change):
            if candidate and all(candidate["task_id"] != row["task_id"] for row in displayed_witnesses):
                displayed_witnesses.append(candidate)
        witness_mode = "two_part_fallback_or_negative"
    witness_rows = []
    for witness in displayed_witnesses:
        witness_id = witness["task_id"]
        witness_sets = {
            name: render_task_set(name, row, candidates)
            for name, row in witness["rows"].items()
        }
        # Independently recheck each displayed task/set witness with pinned Advisor Fraction routines.
        for name, row in witness["rows"].items():
            selected = sets[name]
            active = row["active"]
            idx = int(witness_id.rsplit(":", 1)[1])
            n0 = max(Decimal(1), Decimal(empty[idx]))
            alpha = runner._log_ratio(n0, max(1, truth[witness_id]))
            corrections = {
                edge: Fraction(
                    exact_units(runner._log_ratio(max(Decimal(1), Decimal(singleton[edge][idx])), n0)),
                    SCALE,
                )
                for edge in active
            }
            advisor_candidates = tuple(
                model.Candidate(edge, f"public.{DATASET}", tuple(candidates[edge]["endpoints"]), Fraction(1))
                for edge in selected
            )
            instance = model.Instance(advisor_candidates, (), Fraction(0))
            task = model.Task(
                witness_id,
                f"public.{DATASET}",
                Fraction(1),
                Fraction(exact_units(alpha), SCALE),
                active,
                corrections,
            )
            nominal_loss, nominal_matching = reference.reference_nominal_task_loss(
                instance, task, frozenset(selected), selected
            )
            pess_loss, pess_matching = reference.reference_task_loss(instance, task, frozenset(selected))
            if (
                nominal_loss != Fraction(row["nominal_units"], SCALE)
                or pess_loss != Fraction(row["pess_units"], SCALE)
                or nominal_matching != frozenset(row["nominal_matching"])
                or tuple(sorted(pess_matching)) not in row["pess_ties"]
            ):
                raise AssertionError(f"pinned Advisor witness mismatch: {witness_id}/{name}")
        witness_rows.append({
            "task_id": witness_id,
            "sets": witness_sets,
            "pinned_advisor_reference_checks": "all five displayed set evaluations matched",
        })
    witness_detail = {
        "selection_mode": witness_mode,
        "primary_task_id": first_primary["task_id"] if first_primary else None,
        "selection_rule_counts": criteria_counts,
        "displayed_tasks": witness_rows,
    }

    frozen_objective_checks = {}
    for case_id, set_name in CASE_TO_SET.items():
        case = cases_by_id[case_id]
        metric = "pess_loss_sum_fraction" if case["objective"] == "pess" else "nominal_loss_sum_fraction"
        actual = stats[set_name][metric]
        if Fraction(actual) != Fraction(case["objective_fraction"]):
            raise AssertionError(f"frozen greedy objective differs for {case_id}")
        frozen_objective_checks[case_id] = {
            "objective": case["objective"],
            "frozen_objective_fraction": case["objective_fraction"],
            "recomputed_fraction": actual,
            "exact_match": True,
            "addition_order": case["addition_order"],
            "objective_trace": case["objective_trace"],
            "budget_used": case["budget_used"],
            "budget_unused": case["budget_unused"],
            "termination_reason": case.get("termination_reason"),
            "outer_global_optimum_claim": case.get("outer_global_optimum_claim"),
        }

    change = None
    if displayed_witnesses:
        witness = displayed_witnesses[0]
        before = set(witness["rows"]["M3_shared"]["losses"])
        after = set(witness["rows"]["M4_nominal"]["losses"])
        change = {
            "nested_transition": "Census13 Nominal B3 -> B4 adds e06_08",
            "newly_admissible_matchings": [list(row) for row in sorted(after - before)],
            "no_longer_admissible_matchings": [list(row) for row in sorted(before - after)],
            "B5_policy_sets_are_nonnested": True,
            "M5_shared_resource_ids": sorted(set(sets["M5_nominal"]) & set(sets["M5_pess"])),
            "M5_nominal_only_ids": sorted(set(sets["M5_nominal"]) - set(sets["M5_pess"])),
            "M5_pess_only_ids": sorted(set(sets["M5_pess"]) - set(sets["M5_nominal"])),
        }

    return {
        "format": "ess-issue116-train-scheme-space-case-study-v1",
        "issue": 116,
        "status": "COMPLETE",
        "analysis_source_commit": subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, check=True, capture_output=True, text=True
        ).stdout.strip(),
        "analysis_script_sha256": sha256_file(Path(__file__).resolve()),
        "python_version": platform.python_version(),
        "scope": {
            "dataset": DATASET,
            "split": "train",
            "task_count": len(queries),
            "fixed_sets_only": True,
            "no_resource_reselection_or_refit": True,
            "no_valid_test_or_postgresql_access": True,
            "workload_and_label_pickles_opened": False,
        },
        "provenance": {
            "frozen_selection_sha256": sha256_file(FROZEN_PATH),
            "issue99_protocol_sha256": protocol_sha,
            "collection_run_id": frozen_ds["collection_run_id"],
            "collection_manifest_sha256": frozen_ds["collection_manifest_sha256"],
            "selection_run_id": frozen_ds["selection_run_id"],
            "selection_manifest_sha256": frozen_ds["selection_manifest_sha256"],
            "arecel_archive_sha256": archive_sha,
            "arecel_source_csv_sha256_recorded": collection["source_csv_sha256"],
            "train_workload_pickle_sha256_recorded": collection["workload_pickle_sha256"],
            "train_label_pickle_sha256_recorded": collection["label_pickle_sha256"],
            "train_truth_sha256": collection["train_truth"]["sha256"],
            "train_truth_values_sha256": collection["train_truth"]["canonical_values_sha256"],
            "fixed_sample_sha256": collection["sample"]["sha256"],
            "candidate_map_sha256": collection["candidate_map_sha256"],
            "candidate_order_sha256": collection["candidate_order_sha256"],
            "train_support_map_sha256": collection["train_support_map_sha256"],
            "observation_aggregate_sha256": observation_aggregate,
            "model_version": frozen_ds["model_fit"]["model_version"],
            "model_transform": frozen_ds["model_fit"]["transform"],
            "coefficient_count": coefficient_count,
            "coefficient_digest_sha256": model_digest.hexdigest(),
            "coefficient_digest_matches_issue99": True,
            "advisor_source_commit": runner.PROTOCOL["source_pins"]["advisor_source_commit"],
            "advisor_source_sha256": advisor_hashes,
        },
        "issue103_reuse_audit": {
            "pr_url": "https://github.com/1951123/ess-research/pull/104",
            "state": "open-draft-unmerged-at-analysis",
            "summary_run_id": prior_summary["run_id"],
            "analysis_source_commit": prior_summary["analysis_source_commit"],
            "script_sha256": prior_script_sha,
            "summary_sha256": prior_summary_sha,
            "per_task_exact_reference_checks_were_recorded_by_issue103": True,
            "aggregate_crosschecks": prior_crosschecks,
        },
        "fixed_selection_sets": {name: list(selected) for name, selected in sets.items()},
        "whole_train_aggregates": stats,
        "predeclared_witness_rule": {
            "max_gamma_for_compact_display": MAX_COMPACT_GAMMA,
            "criterion_counts": criteria_counts,
            "primary_task_id": first_primary["task_id"] if first_primary else None,
            "lowest_ambiguous_positive_risk_task_id": first_ambiguous_positive["task_id"] if first_ambiguous_positive else None,
            "lowest_scheme_change_task_id": first_scheme_change["task_id"] if first_scheme_change else None,
            "lowest_conflict_bearing_zero_risk_task_id": first_conflict_zero["task_id"] if first_conflict_zero else None,
            "selected_witness": witness_detail,
            "scheme_space_transition": change,
        },
        "frozen_greedy_objective_checks": frozen_objective_checks,
        "interpretation_limits": [
            "This is an exact/model-internal Train illustration, not physical PostgreSQL or held-out evidence.",
            "The task witness explains a mechanism; it does not cause or explain the global greedy decision by itself.",
            "Frozen selections are add-only greedy heuristics, not globally optimal sets.",
            "The earlier Issue #95 Valid-only witness and its loss transform were not reused.",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-parent", type=Path, default=Path(os.environ.get("ESS_RUNTIME_PARENT", "")))
    parser.add_argument("--data-root", type=Path, default=Path(os.environ.get("ESS_DATA_ROOT", "")))
    parser.add_argument("--issue103-source", type=Path, required=True, help="read-only Issue #103 Worktree")
    parser.add_argument("--advisor-source", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, default=HERE / "summary.json")
    args = parser.parse_args()
    if not args.runtime_parent.is_absolute() or not args.data_root.is_absolute():
        raise ValueError("ESS_RUNTIME_PARENT and ESS_DATA_ROOT must be initialized absolute paths")
    summary = analyze(args)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"event": "analysis_complete", "status": summary["status"],
                      "primary_task_id": summary["predeclared_witness_rule"]["primary_task_id"],
                      "output": str(args.output_json)}, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
