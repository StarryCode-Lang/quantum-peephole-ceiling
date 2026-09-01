"""Post-seal common-basis and gate-weight sensitivity for E31 cost conclusions."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit import qasm2, qpy, transpile
from scipy.stats import t as student_t


ROOT = Path(__file__).resolve().parents[1]
E31 = ROOT / "data/v11/e31_factorial_pareto"
RESULTS = E31 / "formal_run/final/formal_results.csv"
DESIGN = E31 / "design_manifest.csv"
REPLAY = E31 / "formal_run/semantic_replay/semantic_replay_manifest.json"
SOURCE_MANIFEST = ROOT / "data/v10/prepaper/sota/inputs/benchmark_manifest.csv"
DEFAULT_OUTPUT = E31 / "formal_run/analysis/basis_weight_sensitivity.json"
BASIS_SCHEMES = {
    "ibm_rz_sx_x_cx": ["rz", "sx", "x", "cx"],
    "u_cx": ["u", "cx"],
    "ibm_rz_sx_x_cz": ["rz", "sx", "x", "cz"],
}
CONFIGURATIONS = {
    "ibm_equal_weight": ("ibm_rz_sx_x_cx", "equal"),
    "u_cx_equal_weight": ("u_cx", "equal"),
    "cz_equal_weight": ("ibm_rz_sx_x_cz", "equal"),
    "ibm_two_qubit_weight_10": ("ibm_rz_sx_x_cx", "two_qubit_10"),
    "ibm_virtual_rz_two_qubit_weight_10": (
        "ibm_rz_sx_x_cx",
        "virtual_rz_two_qubit_10",
    ),
}
IGNORED = {"barrier", "delay"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _logical_count(circuit) -> int:
    return sum(str(item.operation.name).lower() not in IGNORED for item in circuit.data)


def _cost(circuit, profile: str) -> float:
    total = 0.0
    for item in circuit.data:
        name = str(item.operation.name).lower()
        if name in IGNORED:
            continue
        arity = len(item.qubits)
        if profile == "equal":
            total += 1.0
        elif profile == "two_qubit_10":
            total += 10.0 if arity >= 2 else 1.0
        elif profile == "virtual_rz_two_qubit_10":
            total += 10.0 if arity >= 2 else (0.0 if name == "rz" else 1.0)
        else:
            raise ValueError(profile)
    return total


def circuit_costs(circuit) -> dict[str, object]:
    basis_costs: dict[str, dict[str, float]] = {}
    for name, basis in BASIS_SCHEMES.items():
        translated = transpile(
            circuit,
            basis_gates=basis,
            optimization_level=0,
            seed_transpiler=0,
        )
        basis_costs[name] = {
            "equal": _cost(translated, "equal"),
            "two_qubit_10": _cost(translated, "two_qubit_10"),
            "virtual_rz_two_qubit_10": _cost(translated, "virtual_rz_two_qubit_10"),
        }
    return {"logical_gate_count": _logical_count(circuit), "basis_costs": basis_costs}


def _load_qasm(path: Path):
    return qasm2.load(path, custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS)


def _input_task(item: tuple[str, str, str]) -> tuple[str, dict[str, object]]:
    input_hash, relative, expected_qasm_sha = item
    path = ROOT / relative
    if _sha256(path) != expected_qasm_sha:
        raise RuntimeError(f"input QASM hash mismatch: {relative}")
    return input_hash, circuit_costs(_load_qasm(path))


def _output_task(item: tuple[str, str]) -> tuple[str, dict[str, object]]:
    qpy_sha, relative = item
    path = ROOT / relative
    if _sha256(path) != qpy_sha:
        raise RuntimeError(f"output QPY hash mismatch: {relative}")
    with path.open("rb") as stream:
        circuits = qpy.load(stream)
    if len(circuits) != 1:
        raise RuntimeError(f"unexpected QPY circuit count: {relative}")
    return qpy_sha, circuit_costs(circuits[0])


def _summary(values: pd.Series) -> dict[str, float]:
    return {
        "mean": float(values.mean()),
        "q05": float(values.quantile(0.05)),
        "median": float(values.median()),
        "q95": float(values.quantile(0.95)),
        "regression_probability": float((values < 0.0).mean()),
    }


def _primary_contrast(frame: pd.DataFrame, column: str) -> dict[str, object]:
    pivot = frame.pivot_table(
        index=["input_circuit_sha256", "circuit_family", "window_gates", "budget_seconds"],
        columns=["listing_model", "rule_set"],
        values=column,
        aggfunc="first",
    )
    required = [
        ("WCL", "COMMUTATION_PLUS_TEMPLATES"),
        ("LBL", "COMMUTATION_PLUS_TEMPLATES"),
        ("WCL", "COMMUTATION_ONLY"),
        ("LBL", "COMMUTATION_ONLY"),
    ]
    if any(key not in pivot.columns for key in required) or len(pivot) != 391 * 3 * 4:
        raise RuntimeError("incomplete primary-contrast pivot")
    did = (
        pivot[required[0]] - pivot[required[1]] - pivot[required[2]] + pivot[required[3]]
    ).rename("did_pp").reset_index()
    per_input = did.groupby(["input_circuit_sha256", "circuit_family"], as_index=False)[
        "did_pp"
    ].mean()
    family = per_input.groupby("circuit_family", as_index=False)["did_pp"].mean()
    if len(per_input) != 391 or len(family) != 15:
        raise RuntimeError("unexpected input/family counts in primary contrast")
    family_values = family["did_pp"].to_numpy(dtype=float)
    family_mean = float(np.mean(family_values))
    family_se = float(np.std(family_values, ddof=1) / np.sqrt(len(family_values)))
    critical = float(student_t.ppf(0.975, df=14))
    return {
        "fixed_panel_input_weighted_mean_pp": float(per_input["did_pp"].mean()),
        "equal_family_mean_pp": family_mean,
        "family_cluster_count": 15,
        "family_t14_ci95_low_pp": family_mean - critical * family_se,
        "family_t14_ci95_high_pp": family_mean + critical * family_se,
        "sign": "positive" if family_mean > 0 else ("negative" if family_mean < 0 else "zero"),
    }


def build_audit(workers: int = 8) -> dict[str, object]:
    results = pd.read_csv(RESULTS)
    design = pd.read_csv(DESIGN)
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    with SOURCE_MANIFEST.open("r", encoding="utf-8-sig", newline="") as stream:
        source_rows = list(csv.DictReader(stream))
    qasm_sha_by_path = {row["qasm_path"]: row["qasm_sha256"] for row in source_rows}
    input_inventory = (
        design[["input_circuit_sha256", "qasm_path"]].drop_duplicates("input_circuit_sha256")
    )
    input_tasks = [
        (row.input_circuit_sha256, row.qasm_path, qasm_sha_by_path[row.qasm_path])
        for row in input_inventory.itertuples(index=False)
    ]
    qpy_inventory: dict[str, str] = {}
    run_to_qpy: dict[str, str] = {}
    for binding in replay["semantic_cells"]:
        qpy_inventory.setdefault(binding["qpy_sha256"], binding["qpy_path"])
    for binding in replay["row_bindings"]:
        run_to_qpy[binding["run_id"]] = binding["qpy_sha256"]
    if len(input_tasks) != 391 or len(qpy_inventory) != 1802 or len(run_to_qpy) != 20314:
        raise RuntimeError("unexpected E31 circuit inventory")

    with ThreadPoolExecutor(max_workers=workers) as pool:
        input_costs = dict(pool.map(_input_task, input_tasks))
        output_costs = dict(pool.map(_output_task, sorted(qpy_inventory.items())))

    frame = results[[
        "run_id", "input_circuit_sha256", "circuit_family", "listing_model", "rule_set",
        "window_gates", "budget_seconds", "status", "original_common_basis_gate_count",
        "optimized_common_basis_gate_count",
    ]].copy()
    configurations: dict[str, dict[str, object]] = {}
    successful = frame["status"].eq("success")
    current_count_mismatches = 0
    for config, (basis, profile) in CONFIGURATIONS.items():
        values: list[float] = []
        success_values: list[float] = []
        for row in frame.itertuples(index=False):
            if row.status == "success":
                original_cost = float(input_costs[row.input_circuit_sha256]["basis_costs"][basis][profile])
                output_sha = run_to_qpy[row.run_id]
                optimized_cost = float(output_costs[output_sha]["basis_costs"][basis][profile])
                reduction = 0.0 if original_cost == 0 else 100.0 * (1.0 - optimized_cost / original_cost)
                success_values.append(reduction)
                if config == "ibm_equal_weight":
                    if (original_cost != float(row.original_common_basis_gate_count)
                            or optimized_cost != float(row.optimized_common_basis_gate_count)):
                        current_count_mismatches += 1
            else:
                reduction = 0.0
            values.append(reduction)
        column = f"reduction_{config}"
        frame[column] = values
        configurations[config] = {
            "basis": basis,
            "weight_profile": profile,
            "success_only_reduction_pp": _summary(pd.Series(success_values)),
            "itt_mean_reduction_pp": float(np.mean(values)),
            "primary_contrast": _primary_contrast(frame, column),
        }
    if current_count_mismatches:
        raise RuntimeError(f"current common-basis count mismatches: {current_count_mismatches}")

    translation: dict[str, dict[str, float]] = {}
    for basis in BASIS_SCHEMES:
        overhead = []
        ratios = []
        for input_hash in sorted(input_costs):
            logical = float(input_costs[input_hash]["logical_gate_count"])
            translated = float(input_costs[input_hash]["basis_costs"][basis]["equal"])
            overhead.append(translated - logical)
            ratios.append(translated / logical if logical else 1.0)
        translation[basis] = {
            "mean_added_gates": float(np.mean(overhead)),
            "median_added_gates": float(np.median(overhead)),
            "q95_added_gates": float(np.quantile(overhead, 0.95)),
            "mean_translation_ratio": float(np.mean(ratios)),
            "median_translation_ratio": float(np.median(ratios)),
        }

    signs = {name: item["primary_contrast"]["sign"] for name, item in configurations.items()}
    return {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_E31_COMMON_BASIS_AND_GATE_WEIGHT_SENSITIVITY_COMPLETE",
        "results_sha256": _sha256(RESULTS),
        "design_manifest_sha256": _sha256(DESIGN),
        "semantic_replay_manifest_sha256": _sha256(REPLAY),
        "formal_rows": len(results),
        "success_rows": int(successful.sum()),
        "unique_inputs": len(input_costs),
        "unique_successful_output_qpy_hashes": len(output_costs),
        "basis_schemes": BASIS_SCHEMES,
        "cost_configurations": configurations,
        "basis_translation_overhead_on_391_inputs": translation,
        "recorded_current_basis_counts_reproduced": current_count_mismatches == 0,
        "primary_contrast_signs": signs,
        "primary_contrast_sign_stable": len(set(signs.values())) == 1,
        "interpretation": (
            "The current-basis counts reproduce every successful sealed row exactly. Common-basis "
            "and gate-weight alternatives are post-seal sensitivity estimands; family-t14 intervals "
            "are supportive and do not replace the frozen confirmatory contrast."
        ),
        "limitations": [
            "Basis translation uses Qiskit optimization_level=0 without hardware coupling, routing, scheduling, or calibration.",
            "Two-qubit and virtual-RZ profiles are transparent cost sensitivities, not measured hardware durations or error rates.",
            "Timeout rows remain zero in the ITT estimand because no valid output circuit was retained.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_audit(args.workers)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.relative_to(ROOT).as_posix(), "status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
