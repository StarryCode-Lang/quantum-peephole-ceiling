"""E61: is Qiskit's ``optimization_level`` monotone in a restricted basis?

Motivation
----------
E58 found, almost by accident, that on one 4-qubit VQE source the Qiskit 2.4.1
pipeline gives

    optimization_level=2, basis {h,x,rz,cx}  ->  76 gates, 0 adjacent rz pairs
    optimization_level=3, basis {h,x,rz,cx}  -> 128 gates, 49 adjacent rz pairs

so a *higher* optimization level produced a *worse* circuit, and the level-3
output is not a fixed point of its own single-qubit pass.  A hand merge of the
49 adjacent pairs takes 128 -> 91 gates, and the merged circuit is unitarily
equal to the level-3 output.

That is a one-source anecdote.  This experiment turns it into a panel statement:
for every frozen source in the E58 comparable set, transpile at levels 0-3 in the
frozen basis and count (a) total gates, (b) two-qubit gates, (c) adjacent
same-qubit same-axis rotation pairs -- the exact pattern the closure criterion
flags at D = 0.

Parts
-----
A  Level sweep.  L0/L1/L2/L3 in ``{h,x,rz,cx}`` for every source with root size
   <= 300.  Report totals per level, the number of sources where L3 is worse
   than L2, and the residual D=0 pair count per level.
B  Fix check.  For every source where L3 has a residual D=0 pair, apply the
   closure (which is exactly the merge the level-3 pass missed) and confirm by
   dense unitary that the result is equivalent.  This is the constructive proof
   that the pairs are genuine missed optimisations, not bookkeeping artefacts.
C  Default-basis control.  Repeat L3 without ``basis_gates`` on the same sources
   and count residual pairs, so the effect can be attributed to the restricted
   basis rather than to Qiskit in general.

Contract
    Read-only on ``data/``, ``release/``, ``docs/manuscript/``.  Frozen root
    states (hash-checked).  No project source file is modified.

Outputs (``docs/review/science_boost/2026-10-24_opt_level_monotonicity/``):
    * ``level_sweep.csv``   -- one row per (source, level)
    * ``fix_check.csv``     -- Part B rows
    * ``summary.json``      -- aggregates, contract
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qiskit import QuantumCircuit, transpile  # noqa: E402
from qiskit.quantum_info import Operator  # noqa: E402

from experiments.e45_development_grid.run import NAM_BASIS, normalize_circuit, state_from_circuit  # noqa: E402
from experiments.e46_window_landscape.run import RULE_SCOPE, load_root_states  # noqa: E402
from src.optimisation.certified_landscape import LandscapeState  # noqa: E402
from scripts.e56_closure_criterion import closure_run, exposable_pairs  # noqa: E402

EXPERIMENT_ID = "E61_OPT_LEVEL_MONOTONICITY_2026_10_24"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-24_opt_level_monotonicity"
SIZE_CAP = 300
LEVELS = (0, 1, 2, 3)
SEED = 42
UNITARY_QUBIT_CAP = 8
UNITARY_GATE_CAP = 600
TWO_QUBIT = frozenset({"cx", "cz", "swap"})


def _to_qiskit(state: LandscapeState) -> QuantumCircuit | None:
    circuit = QuantumCircuit(state.num_qubits)
    for gate in state.gates:
        if gate.name == "h":
            circuit.h(gate.qubits[0])
        elif gate.name == "x":
            circuit.x(gate.qubits[0])
        elif gate.name == "rz":
            circuit.rz(float(gate.angle or 0.0), gate.qubits[0])
        elif gate.name == "cx":
            circuit.cx(gate.qubits[0], gate.qubits[1])
        else:
            return None
    return circuit


def _stats(state: LandscapeState) -> dict[str, int]:
    total = len(state.gates)
    two_q = sum(1 for gate in state.gates if gate.name in TWO_QUBIT)
    d0 = sum(1 for pair in exposable_pairs(state) if pair["distance"] == 0)
    return {"total": total, "two_qubit": two_q, "d0_pairs": d0}


def _transpile(circuit: QuantumCircuit, level: int, basis: bool) -> QuantumCircuit | None:
    kwargs: dict[str, Any] = {
        "optimization_level": level,
        "layout_method": "trivial",
        "routing_method": "basic",
        "seed_transpiler": SEED,
    }
    if basis:
        kwargs["basis_gates"] = NAM_BASIS
    try:
        return transpile(circuit, **kwargs)
    except Exception:
        return None


def _unitary_equal(left: QuantumCircuit, right: QuantumCircuit) -> bool | None:
    if left.num_qubits != right.num_qubits:
        return False
    if left.num_qubits > UNITARY_QUBIT_CAP or max(left.size(), right.size()) > UNITARY_GATE_CAP:
        return None
    try:
        return bool(Operator(left).equiv(Operator(right)))
    except Exception:
        return None


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(OUTPUT_ROOT))
    args = parser.parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    started = time.time()
    sweep: list[dict[str, Any]] = []
    fixes: list[dict[str, Any]] = []

    for root in load_root_states():
        state = root["state"]
        if state.cost > SIZE_CAP:
            continue
        source = _to_qiskit(state)
        if source is None:
            continue
        canonical, _ = normalize_circuit(source)
        if canonical is None:
            continue
        for level in LEVELS:
            out = _transpile(canonical, level, basis=True)
            if out is None:
                sweep.append(
                    {
                        "source_id": root["source_id"],
                        "circuit_family": root["circuit_family"],
                        "n_qubits": root["n_qubits"],
                        "level": level,
                        "basis": "frozen",
                        "status": "TRANSPILE_FAILED",
                    }
                )
                continue
            stats = _stats(state_from_circuit(out))
            sweep.append(
                {
                    "source_id": root["source_id"],
                    "circuit_family": root["circuit_family"],
                    "n_qubits": root["n_qubits"],
                    "level": level,
                    "basis": "frozen",
                    "status": "OK",
                    **stats,
                }
            )
            if level == 3 and stats["d0_pairs"] > 0:
                canonical_state = state_from_circuit(out)
                run = closure_run(canonical_state)
                fixed = _to_qiskit(run["final_state"])
                equiv = _unitary_equal(out, fixed) if fixed is not None else None
                fixes.append(
                    {
                        "source_id": root["source_id"],
                        "circuit_family": root["circuit_family"],
                        "n_qubits": root["n_qubits"],
                        "l3_total": stats["total"],
                        "l3_two_qubit": stats["two_qubit"],
                        "l3_d0_pairs": stats["d0_pairs"],
                        "after_closure_total": run["final_cost"],
                        "after_closure_two_qubit": sum(
                            1 for gate in run["final_state"].gates if gate.name in TWO_QUBIT
                        ),
                        "gates_removed": stats["total"] - run["final_cost"],
                        "closure_passes": run["passes"],
                        "unitary_equivalent": "" if equiv is None else str(equiv),
                    }
                )
        default_l3 = _transpile(canonical, 3, basis=False)
        if default_l3 is not None:
            # The default basis emits gates outside {h,x,rz,cx}, so the frozen
            # state builder cannot parse it.  Count the same pattern directly on
            # the Qiskit listing: adjacent same-name single-qubit rotations on the
            # same qubit -- the D=0 signature the criterion flags.
            data = default_l3.data
            adjacent = 0
            for index in range(len(data) - 1):
                left, right = data[index], data[index + 1]
                if (
                    left.operation.name == right.operation.name
                    and left.operation.num_qubits == 1
                    and left.qubits == right.qubits
                ):
                    adjacent += 1
            sweep.append(
                {
                    "source_id": root["source_id"],
                    "circuit_family": root["circuit_family"],
                    "n_qubits": root["n_qubits"],
                    "level": 3,
                    "basis": "default",
                    "status": "OK",
                    "total": int(default_l3.size()),
                    "two_qubit": sum(1 for item in data if item.operation.num_qubits == 2),
                    "d0_pairs": adjacent,
                }
            )

    per_level: dict[str, Any] = {}
    for level in LEVELS:
        rows = [row for row in sweep if row["level"] == level and row["basis"] == "frozen" and row["status"] == "OK"]
        per_level[f"L{level}_frozen"] = {
            "sources": len(rows),
            "total_gates": sum(row["total"] for row in rows),
            "two_qubit": sum(row["two_qubit"] for row in rows),
            "d0_pairs": sum(row["d0_pairs"] for row in rows),
            "sources_with_d0": sum(1 for row in rows if row["d0_pairs"] > 0),
        }
    default_rows = [row for row in sweep if row["basis"] == "default" and row["status"] == "OK"]
    per_level["L3_default"] = {
        "sources": len(default_rows),
        "total_gates": sum(row["total"] for row in default_rows),
        "two_qubit": sum(row["two_qubit"] for row in default_rows),
        "d0_pairs": sum(row["d0_pairs"] for row in default_rows),
        "sources_with_d0": sum(1 for row in default_rows if row["d0_pairs"] > 0),
    }

    l2 = {(row["source_id"]): row for row in sweep if row["level"] == 2 and row["basis"] == "frozen" and row["status"] == "OK"}
    l3 = {(row["source_id"]): row for row in sweep if row["level"] == 3 and row["basis"] == "frozen" and row["status"] == "OK"}
    shared = sorted(set(l2) & set(l3))
    monotonicity = {
        "comparable_sources": len(shared),
        "l3_worse_than_l2": sum(1 for sid in shared if l3[sid]["total"] > l2[sid]["total"]),
        "l3_better_than_l2": sum(1 for sid in shared if l3[sid]["total"] < l2[sid]["total"]),
        "equal": sum(1 for sid in shared if l3[sid]["total"] == l2[sid]["total"]),
        "worst_l3_minus_l2": max((l3[sid]["total"] - l2[sid]["total"] for sid in shared), default=0),
        "total_gate_inflation_l3_over_l2": sum(l3[sid]["total"] - l2[sid]["total"] for sid in shared),
    }

    fix_equiv = [row for row in fixes if row["unitary_equivalent"]]
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-24",
        "contract": {
            "root_states": "experiments.e46_window_landscape.run.load_root_states (hash-checked)",
            "basis": NAM_BASIS,
            "size_cap": SIZE_CAP,
            "levels": list(LEVELS),
            "seed_transpiler": SEED,
            "rule_scope": RULE_SCOPE,
            "qiskit_version": __import__("qiskit").__version__,
        },
        "per_level": per_level,
        "monotonicity": monotonicity,
        "fix_check": {
            "sources_with_l3_d0_pairs": len(fixes),
            "gates_removed_by_closure": sum(row["gates_removed"] for row in fixes),
            "unitary_checked": len(fix_equiv),
            "unitary_pass": sum(1 for row in fix_equiv if row["unitary_equivalent"] == "True"),
            "unitary_fail": sum(1 for row in fix_equiv if row["unitary_equivalent"] == "False"),
        },
        "wall_clock_seconds": round(time.time() - started, 1),
    }
    _write_csv(output_root / "level_sweep.csv", sweep)
    _write_csv(output_root / "fix_check.csv", fixes)
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps({k: summary[k] for k in ("per_level", "monotonicity", "fix_check")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
