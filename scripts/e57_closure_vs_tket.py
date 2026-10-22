"""E57: is the closure pass an industry-standard operation, and does it match?

Motivation
----------
E56 (2026-10-23) showed that a pure commutation-closure fixpoint removes 1,997
gates from the 128-source certified panel at zero search cost and beats the
frozen h=3 ``best_cost`` on 48 of 128 sources.  Before that result can be
claimed as new, one question has to be answered:

    Does a production compiler's redundancy-removal pass already do this?

tket's ``RemoveRedundancies`` is the canonical implementation of "cancel and
merge gates through commuting ones".  This experiment runs it on the *same*
128 hash-verified roots and compares three numbers per source: the frozen
``baseline_cost``, the E56 closure cost, and the tket cost.

Reading
-------
* tket == closure  -> the operation is standard; the novelty is the exact
  criterion (E56) and the measurement that the certified landscape is
  horizon-limited, not the pass itself.
* tket <  closure  -> the greedy closure selection order is leaving gates on
  the table; the criterion is still exact but the algorithm needs work.
* tket >  closure  -> the closure finds reductions a production pass misses.

Contract
    Read-only on ``data/`` and ``release/``.  Roots come from
    ``load_root_states`` (hash-checked against the v14 certificates).  Only the
    normalised gate set ``{h, x, rz, cx}`` occurs in the panel, so the qiskit
    round-trip is exact.

Outputs (``docs/review/science_boost/2026-10-23_closure_criterion/``):
    * ``tket_remove_redundancies.csv``
    * ``summary_tket.json``
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qiskit import QuantumCircuit  # noqa: E402
from qiskit.transpiler.passes import RemoveBarriers  # noqa: E402,F401
from pytket.extensions.qiskit import qiskit_to_tk  # noqa: E402
from pytket.passes import RemoveRedundancies  # noqa: E402

from experiments.e46_window_landscape.run import load_root_states  # noqa: E402

EXPERIMENT_ID = "E57_CLOSURE_VS_TKET_2026_10_23"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-23_closure_criterion"
SKIP_ABOVE = 2000


def to_qiskit(state) -> QuantumCircuit:
    circuit = QuantumCircuit(state.num_qubits)
    for gate in state.gates:
        if gate.name == "h":
            circuit.h(gate.qubits[0])
        elif gate.name == "x":
            circuit.x(gate.qubits[0])
        elif gate.name == "rz":
            circuit.rz(gate.angle or 0.0, gate.qubits[0])
        elif gate.name == "cx":
            circuit.cx(gate.qubits[0], gate.qubits[1])
        else:
            raise ValueError(f"unexpected gate {gate.name}")
    return circuit


def tket_cost(state) -> dict[str, Any]:
    circuit = to_qiskit(state)
    tkc = qiskit_to_tk(circuit)
    RemoveRedundancies().apply(tkc)
    ops = tkc.n_gates
    two_q = tkc.n_gates_of_type(next(iter(tkc.gate_types))) if False else sum(
        1 for command in tkc if command.op.n_qubits == 2
    )
    return {"tket_cost": int(ops), "tket_two_qubit": int(two_q)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    args.output_root.mkdir(parents=True, exist_ok=True)

    closure = {}
    closure_path = args.output_root / "closure_results.csv"
    if closure_path.exists():
        with closure_path.open(newline="", encoding="utf-8") as handle:
            closure = {row["source_id"]: row for row in csv.DictReader(handle)}

    rows: list[dict[str, Any]] = []
    for index, root in enumerate(load_root_states(), start=1):
        state = root["state"]
        record = closure.get(root["source_id"], {})
        base = {
            "source_id": root["source_id"],
            "circuit_family": record.get("circuit_family", ""),
            "root_cost": state.cost,
            "baseline_cost": record.get("baseline_cost", ""),
            "certified_best_cost": record.get("certified_best_cost", ""),
            "closure_cost": record.get("closure_cost", ""),
        }
        if state.cost > SKIP_ABOVE:
            base.update({"tket_cost": "", "tket_two_qubit": "", "status": "SKIPPED_LARGE"})
            rows.append(base)
            print(f"[{index:3d}] {root['source_id'][:20]} SKIPPED (cost={state.cost})", flush=True)
            continue
        started = time.perf_counter()
        try:
            measured = tket_cost(state)
            status = "OK"
        except Exception as exc:  # noqa: BLE001 - recorded, not hidden
            measured = {"tket_cost": "", "tket_two_qubit": ""}
            status = f"ERROR:{type(exc).__name__}"
        base.update(measured)
        base["status"] = status
        base["elapsed_seconds"] = round(time.perf_counter() - started, 3)
        rows.append(base)
        print(
            f"[{index:3d}] {root['source_id'][:20]} root={state.cost:5d} "
            f"closure={base['closure_cost']:>5} tket={base['tket_cost']:>5} {status}",
            flush=True,
        )

    with (args.output_root / "tket_remove_redundancies.csv").open("w", newline="", encoding="utf-8") as handle:
        fields = ["source_id", "circuit_family", "root_cost", "baseline_cost",
                  "certified_best_cost", "closure_cost", "tket_cost", "tket_two_qubit",
                  "status", "elapsed_seconds"]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    ok = [row for row in rows if row["status"] == "OK" and row["tket_cost"] != "" and row["closure_cost"] != ""]
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-23",
        "sources": len(rows),
        "compared": len(ok),
        "skipped_large": sum(1 for row in rows if row["status"] == "SKIPPED_LARGE"),
        "errors": sum(1 for row in rows if row["status"].startswith("ERROR")),
        "tket_equals_closure": sum(1 for row in ok if int(row["tket_cost"]) == int(row["closure_cost"])),
        "tket_better": sum(1 for row in ok if int(row["tket_cost"]) < int(row["closure_cost"])),
        "closure_better": sum(1 for row in ok if int(row["tket_cost"]) > int(row["closure_cost"])),
        "tket_total": sum(int(row["tket_cost"]) for row in ok),
        "closure_total": sum(int(row["closure_cost"]) for row in ok),
        "baseline_total": sum(int(row["root_cost"]) for row in ok),
        "tket_beats_certified": sum(
            1 for row in ok
            if row["certified_best_cost"] != "" and int(row["tket_cost"]) < int(row["certified_best_cost"])
        ),
    }
    (args.output_root / "summary_tket.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
