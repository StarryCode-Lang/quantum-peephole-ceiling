"""E55: does the industry implement diagonal-through-control commutation?

Why
---
E52 (2026-10-22) found that the dominant neutral step in the project's genuine
panel escapes is `exchange.cx_control_z`: moving a diagonal gate past the
*control* wire of a CX.  That is a commutation law which "disjoint support"
cannot derive, so an engine that only implements disjoint-wire commutation is
blind to it at *any* window width.

The scientific weight of that finding depends entirely on one question:

    Is this the project's engine gap, or the field's?

If qiskit / tket / BQSKit all collapse these circuits to zero gates, the result
is an engineering defect in one prototype engine.  If some of them fail, the
blind spot is a property of a *class* of engines and the statement becomes a
theorem about that class, independent of search budget.

Circuits
--------
All are written directly in `{h, x, rz, cx}` so no basis translation is needed
before the project's own engine sees them.

* `A_control_k1`    rz(t) q0; cx q0,q1; rz(-t) q0            -> 0 gates expected
* `B_control_k6`    rz(t) q0; cx q0,q1..q6; rz(-t) q0        -> 0 gates expected
* `C_target_neg`    rz(t) q1; cx q0,q1; rz(-t) q1            -> 2 gates expected
* `D_control_h_mid` rz(t) q0; cx q0,q1; h q0; rz(-t) q0      -> h survives, rz merges
* `E_control_x_mid` rz(t) q0; x q1; cx q0,q1; rz(-t) q0      -> 0 gates expected

Tools
-----
`qiskit_l3`, `tket_fpo`, `tket_remove`, `bqskit`, and the project's own engine
(`e44_core_v1`) at horizons 1 and 3.

Outputs (`docs/review/science_boost/2026-10-22_commutation_gap/`):
    * `commutation_gap_rows.csv`
    * `summary.json`
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import warnings
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for extra in (ROOT, ROOT / "scripts"):
    if str(extra) not in sys.path:
        sys.path.insert(0, str(extra))

warnings.filterwarnings("ignore")

from e48_external_falsifier import metrics, neutral  # noqa: E402

EXPERIMENT_ID = "E55_COMMUTATION_GAP_2026_10_22"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-22_commutation_gap"
THETA = 0.7853981633974483  # pi/4


def build_cases() -> dict[str, tuple[Any, int]]:
    """Return {case_name: (circuit, expected_gate_count_after_optimal)}."""

    from qiskit import QuantumCircuit  # noqa: PLC0415

    cases: dict[str, tuple[Any, int]] = {}

    circuit = QuantumCircuit(2)
    circuit.rz(THETA, 0)
    circuit.cx(0, 1)
    circuit.rz(-THETA, 0)
    cases["A_control_k1"] = (circuit, 1)

    n = 7
    circuit = QuantumCircuit(n)
    circuit.rz(THETA, 0)
    for q in range(1, n):
        circuit.cx(0, q)
    circuit.rz(-THETA, 0)
    cases["B_control_k6"] = (circuit, 6)

    circuit = QuantumCircuit(2)
    circuit.rz(THETA, 1)
    circuit.cx(0, 1)
    circuit.rz(-THETA, 1)
    cases["C_target_neg"] = (circuit, 3)

    circuit = QuantumCircuit(2)
    circuit.rz(THETA, 0)
    circuit.x(1)
    circuit.cx(0, 1)
    circuit.rz(-THETA, 0)
    cases["E_control_x_mid"] = (circuit, 2)

    return cases


def run_qiskit_l3(circuit: Any) -> Any:
    from qiskit import transpile  # noqa: PLC0415

    from e48_external_falsifier import FAIR, SEED  # noqa: PLC0415

    return transpile(circuit, basis_gates=FAIR, optimization_level=3, seed_transpiler=SEED)


def run_tket_fpo(circuit: Any) -> Any:
    from pytket.passes import FullPeepholeOptimise  # noqa: PLC0415
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit  # noqa: PLC0415

    tk = qiskit_to_tk(circuit)
    FullPeepholeOptimise(allow_swaps=True).apply(tk)
    return tk_to_qiskit(tk, replace_implicit_swaps=True)


def run_tket_remove(circuit: Any) -> Any:
    from pytket.passes import RemoveRedundancies  # noqa: PLC0415
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit  # noqa: PLC0415

    tk = qiskit_to_tk(circuit)
    RemoveRedundancies().apply(tk)
    return tk_to_qiskit(tk, replace_implicit_swaps=True)


def run_bqskit(circuit: Any) -> Any:
    from bqskit import compile as bqskit_compile  # noqa: PLC0415
    from bqskit.compiler import MachineModel  # noqa: PLC0415
    from bqskit.ext import bqskit_to_qiskit, qiskit_to_bqskit  # noqa: PLC0415
    from bqskit.ir.gates import CNOTGate, U3Gate  # noqa: PLC0415

    inner = qiskit_to_bqskit(circuit)
    model = MachineModel(inner.num_qudits, gate_set=[U3Gate(), CNOTGate()])
    return bqskit_to_qiskit(bqskit_compile(inner, model=model))


def run_project_engine(circuit: Any, horizon: int) -> Any:
    """Run the frozen `e44_core_v1` landscape search and rebuild the best circuit."""

    from experiments.e45_development_grid.run import RULE_LIBRARY, state_from_circuit  # noqa: PLC0415
    from experiments.e46_window_landscape.run import RULE_SCOPE  # noqa: PLC0415
    from src.optimisation.certified_landscape import search_landscape_horizons_compact  # noqa: PLC0415

    state = state_from_circuit(circuit)
    result = search_landscape_horizons_compact(
        state,
        RULE_LIBRARY,
        [horizon],
        state_budget=200_000,
        rule_scope=RULE_SCOPE,
        time_budget_seconds=30.0,
    )
    entry = result[str(horizon)]
    best = entry.get("best_cost")
    return {
        "status": str(entry.get("status", "")),
        "best_cost": None if best is None else int(best),
        "root_cost": state.cost,
    }


EXTERNAL = {
    "qiskit_l3": run_qiskit_l3,
    "tket_fpo": run_tket_fpo,
    "tket_remove": run_tket_remove,
    "bqskit": run_bqskit,
}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    for name, (circuit, expected) in build_cases().items():
        base = metrics(circuit)
        for tool, fn in EXTERNAL.items():
            record: dict[str, Any] = {
                "case": name,
                "expected_cost": expected,
                "input_cost": base["cost_fair"],
                "engine": tool,
                "status": "OK",
                "cost_fair": None,
                "solved": None,
                "seconds": None,
            }
            start = time.time()
            try:
                out = fn(circuit)
                measured = metrics(out)
                record["cost_fair"] = measured["cost_fair"]
                record["solved"] = bool(measured["cost_fair"] <= expected)
            except Exception as exc:  # noqa: BLE001
                record["status"] = f"ERROR:{type(exc).__name__}:{exc}"[:160]
            record["seconds"] = round(time.time() - start, 2)
            rows.append(record)
            print(f"[E55] {name:18s} {tool:14s} {record['status'][:20]:20s} cost={record['cost_fair']} exp={expected}", flush=True)

        for horizon in (1, 3):
            record = {
                "case": name,
                "expected_cost": expected,
                "input_cost": base["cost_fair"],
                "engine": f"project_e44_core_v1_h{horizon}",
                "status": "OK",
                "cost_fair": None,
                "solved": None,
                "seconds": None,
            }
            start = time.time()
            try:
                out = run_project_engine(circuit, horizon)
                record["status"] = out["status"]
                record["cost_fair"] = out["best_cost"]
                record["solved"] = bool(out["best_cost"] is not None and out["best_cost"] <= expected)
            except Exception as exc:  # noqa: BLE001
                record["status"] = f"ERROR:{type(exc).__name__}:{exc}"[:160]
            record["seconds"] = round(time.time() - start, 2)
            rows.append(record)
            print(f"[E55] {name:18s} project_h{horizon}     {record['status'][:20]:20s} cost={record['cost_fair']} exp={expected}", flush=True)

    write_csv(OUTPUT_ROOT / "commutation_gap_rows.csv", rows)

    by_case: dict[str, dict[str, Any]] = {}
    for row in rows:
        by_case.setdefault(row["case"], {})[row["engine"]] = {
            "cost": row["cost_fair"],
            "solved": row["solved"],
            "status": row["status"],
        }
    solved_counts = {
        engine: sum(1 for row in rows if row["engine"] == engine and row["solved"])
        for engine in {row["engine"] for row in rows}
    }
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-22",
        "theta": THETA,
        "cases": list(build_cases().keys()),
        "by_case": by_case,
        "solved_counts": solved_counts,
        "reading": (
            "Case C is the negative control: a tool that 'solves' it is wrong, not good. "
            "If every external engine solves A/B/E and the project engine does not, the gap is "
            "the project's engine implementation, not the field's. If some external engine also "
            "fails, the blind spot is a property of a class of engines and the statement survives "
            "as an engine-class theorem."
        ),
    }
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"[E55] wrote {OUTPUT_ROOT}", flush=True)
    return 0


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


if __name__ == "__main__":
    raise SystemExit(main())
