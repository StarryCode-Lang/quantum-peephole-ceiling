"""E63: does the Qiskit optimization-level non-monotonicity survive 2.6.1?

E61 found that under the frozen basis ``{h, x, rz, cx}``, ``optimization_level=3``
produces strictly more gates than ``=2`` on 6 of 101 panel sources (+226 gates,
worst +57) and leaves 191 unmerged adjacent ``rz`` pairs that ``=2`` removes.
The evidence was pinned at qiskit 2.4.1.  Qiskit 2.6.0 shipped 2026-10-16 and
2.6.1 on 2026-10-22, so the finding is only useful if it is re-checked on the
current release.

This script runs in three stages so that two different interpreters can share
one input panel:

    dump    (repo env, qiskit 2.4.1)  -> panel_qasm.json
    sweep   (isolated env, 2.6.1)     -> sweep_261.csv
    compare (repo env)                -> cross_version.csv + summary.json

Contract
    Read-only on ``data/``, ``release/`` and ``docs/manuscript/``.  Root states
    are the hash-checked E46 roots; the basis and seed are E61's.
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

OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-25_qiskit_261"
E61_SWEEP = (
    ROOT / "docs" / "review" / "science_boost" / "2026-10-24_opt_level_monotonicity" / "level_sweep.csv"
)
BASIS = ["h", "x", "rz", "cx"]
LEVELS = (2, 3)
SIZE_CAP = 300
SEED = 42


def _to_qiskit(state):  # noqa: ANN001, ANN202
    from qiskit import QuantumCircuit

    circuit = QuantumCircuit(state.num_qubits)
    for gate in state.gates:
        name = gate.name
        if name == "rz":
            circuit.rz(gate.angle, gate.qubits[0])
        elif name == "cx":
            circuit.cx(gate.qubits[0], gate.qubits[1])
        elif name == "x":
            circuit.x(gate.qubits[0])
        elif name == "h":
            circuit.h(gate.qubits[0])
        else:
            return None
    return circuit


def stage_dump() -> int:
    from qiskit import qasm2
    from experiments.e45_development_grid.run import normalize_circuit
    from experiments.e46_window_landscape.run import load_root_states

    payload: dict[str, Any] = {}
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
        payload[root["source_id"]] = {
            "qasm": qasm2.dumps(canonical),
            "circuit_family": root["circuit_family"],
            "n_qubits": root["n_qubits"],
        }
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    (OUTPUT_ROOT / "panel_qasm.json").write_text(json.dumps(payload), encoding="utf-8")
    print(f"dumped {len(payload)} sources")
    return 0


def stage_sweep() -> int:
    import qiskit
    from qiskit import qasm2, transpile

    payload = json.loads((OUTPUT_ROOT / "panel_qasm.json").read_text(encoding="utf-8"))
    rows: list[dict[str, Any]] = []
    started = time.time()
    for source_id, item in payload.items():
        circuit = qasm2.loads(item["qasm"])
        for level in LEVELS:
            out = transpile(
                circuit,
                basis_gates=BASIS,
                optimization_level=level,
                seed_transpiler=SEED,
            )
            names = [instruction.operation.name for instruction in out.data]
            d0 = 0
            for index in range(len(out.data) - 1):
                left, right = out.data[index], out.data[index + 1]
                if (
                    left.operation.name == right.operation.name == "rz"
                    and left.qubits == right.qubits
                ):
                    d0 += 1
            rows.append(
                {
                    "source_id": source_id,
                    "circuit_family": item["circuit_family"],
                    "n_qubits": item["n_qubits"],
                    "qiskit_version": qiskit.__version__,
                    "level": level,
                    "total": len(names),
                    "two_qubit": names.count("cx"),
                    "d0_pairs": d0,
                }
            )
    fields = list(rows[0]) if rows else []
    with (OUTPUT_ROOT / "sweep_261.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    print(f"swept {len(payload)} sources on qiskit {qiskit.__version__} in {time.time()-started:.1f}s")
    return 0


def stage_compare() -> int:
    def load(path: Path) -> dict[str, dict[int, dict[str, Any]]]:
        table: dict[str, dict[int, dict[str, Any]]] = {}
        with path.open(newline="", encoding="utf-8") as handle:
            for row in csv.DictReader(handle):
                if row.get("status", "OK") != "OK":
                    continue
                # E61 emits two level-3 rows per source (frozen and default
                # basis).  Only the frozen-basis row is comparable here.
                if row.get("basis", "frozen") != "frozen":
                    continue
                table.setdefault(row["source_id"], {})[int(row["level"])] = row
        return table

    old = load(E61_SWEEP)
    new = load(OUTPUT_ROOT / "sweep_261.csv")
    rows: list[dict[str, Any]] = []
    for source_id in sorted(set(old) & set(new)):
        if 2 not in old[source_id] or 3 not in old[source_id]:
            continue
        if 2 not in new[source_id] or 3 not in new[source_id]:
            continue
        o2, o3 = old[source_id][2], old[source_id][3]
        n2, n3 = new[source_id][2], new[source_id][3]
        rows.append(
            {
                "source_id": source_id,
                "circuit_family": n2["circuit_family"],
                "n_qubits": n2["n_qubits"],
                "old_241_l2": int(o2["total"]),
                "old_241_l3": int(o3["total"]),
                "old_241_delta": int(o3["total"]) - int(o2["total"]),
                "new_261_l2": int(n2["total"]),
                "new_261_l3": int(n3["total"]),
                "new_261_delta": int(n3["total"]) - int(n2["total"]),
                "old_241_d0_l3": int(o3["d0_pairs"]),
                "new_261_d0_l3": int(n3["d0_pairs"]),
                "defect_reproduced": int(n3["total"]) > int(n2["total"]),
                "l2_changed": int(n2["total"]) != int(o2["total"]),
                "l3_changed": int(n3["total"]) != int(o3["total"]),
            }
        )
    fields = list(rows[0]) if rows else []
    with (OUTPUT_ROOT / "cross_version.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    summary = {
        "comparable_sources": len(rows),
        "defect_reproduced_on_261": sum(1 for row in rows if row["defect_reproduced"]),
        "defect_in_241": sum(1 for row in rows if row["old_241_delta"] > 0),
        "l2_output_changed": sum(1 for row in rows if row["l2_changed"]),
        "l3_output_changed": sum(1 for row in rows if row["l3_changed"]),
        "total_inflation_261": sum(row["new_261_delta"] for row in rows),
        "total_inflation_241": sum(row["old_241_delta"] for row in rows),
        "d0_pairs_l3_261": sum(row["new_261_d0_l3"] for row in rows),
        "d0_pairs_l3_241": sum(row["old_241_d0_l3"] for row in rows),
    }
    (OUTPUT_ROOT / "summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=["dump", "sweep", "compare"])
    args = parser.parse_args()
    return {"dump": stage_dump, "sweep": stage_sweep, "compare": stage_compare}[args.stage]()


if __name__ == "__main__":
    raise SystemExit(main())
