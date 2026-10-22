"""E48: external-optimizer falsification of the surviving structural ceilings.

Question
--------
After E47 (2026-10-19) the project's "genuine structural ceiling" claim survives
only for GHZ and SurfaceCode.  That claim is a statement about the project's
*own* greedy baseline plus a bounded rewrite library.  A reviewer's cheapest
objection is: "your ceiling is your optimizer's weakness, not the circuit's".

This experiment attacks that objection with optimizers that share no code, no
rule library and no search contract with the project:

* ``qiskit_l3``        -- Qiskit transpiler, optimization_level=3;
* ``pytket_fpo``       -- tket FullPeepholeOptimise (allow_swaps=True);
* ``pytket_remove``    -- tket RemoveRedundancies only;
* ``pyzx_full_reduce`` -- ZX-calculus full_reduce (Clifford inputs only).

Two panels
----------
Part A (scaling): GHZ_n for n = 4..20.  The GHZ bound is a statement for all n,
so the falsifier has to run across n, not on the single n=8 panel source.

Part B (panel): all 96 real (``e39``) panel sources.  For every source the
external cost is compared with the frozen ``baseline_cost``.  This is the
panel-level version of the family-level S1-S5 comparison and is the control
that backs the v15 classification.

Cost model
----------
Three metrics, all computed by the same neutral basis translation
(``optimization_level=0``: decomposition only, no routing, no re-optimisation):

``cost_fair``
    Primary.  Target basis admits one general single-qubit gate (``u``), so a
    1q operation costs 1 gate for every tool.  This is the only metric that does
    not penalise tket for emitting ``u``/``tk1`` instead of ``rz``.
``cost_declared``
    Strict project gate set (``h,x,y,z,s,sdg,t,tdg,rz,cx,cz,swap``).  Reported
    for continuity with the frozen receipts; it inflates any tool that emits a
    general 1q gate.
``two_qubit``
    Count of operations acting on >= 2 qubits.  The field-standard metric and
    the one that is genuinely representation-independent.

The normaliser is validated first: on all 128 panel sources it must reproduce
``normalized_gate_count`` under ``cost_declared``, and on every root it must
reproduce ``baseline_cost``.

Read-only with respect to ``data/`` and ``release/``.  Outputs go to
``docs/review/science_boost/2026-10-20_external_falsifier/``.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
import time
import traceback
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qiskit import QuantumCircuit, transpile  # noqa: E402
from qiskit.quantum_info import Operator  # noqa: E402

EXPERIMENT_ID = "E48_EXTERNAL_FALSIFIER_2026_10_20"
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"
MANIFEST = ROOT / "data" / "v14" / "e45_full_development" / "normalization_manifest.csv"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-20_external_falsifier"

DECLARED = ["h", "x", "y", "z", "s", "sdg", "t", "tdg", "rz", "cx", "cz", "swap"]
FAIR = DECLARED + ["u"]
TWO_Q = {"cx", "cz", "swap", "rzz", "ecr", "iswap", "zz", "cy", "ch"}
SEED = 20261020
GHZ_SIZES = (4, 6, 8, 10, 12, 14, 16, 20)
CLIFFORD_FAMILIES = {"GHZ", "SurfaceCode", "CNOT", "RandomClifford"}


# --------------------------------------------------------------------------- #
# neutral normalisers
# --------------------------------------------------------------------------- #
def neutral(circuit: QuantumCircuit, basis: list[str]) -> QuantumCircuit:
    return transpile(circuit, basis_gates=basis, optimization_level=0, seed_transpiler=SEED)


def metrics(circuit: QuantumCircuit) -> dict[str, int]:
    fair = neutral(circuit, FAIR)
    counts = fair.count_ops()
    return {
        "cost_fair": int(sum(counts.values())),
        "cost_declared": int(neutral(circuit, DECLARED).size()),
        "two_qubit": int(sum(v for k, v in counts.items() if k in TWO_Q)),
    }


MAX_OPERATOR_QUBITS = 10
MAX_OPERATOR_GATES = 2000


def equivalent(a: QuantumCircuit, b: QuantumCircuit) -> bool | None:
    """Exact unitary equality up to global phase.

    Dense ``Operator`` construction costs O(4^n) memory and O(gates * 8^n) time,
    so the check is capped on both qubit count and gate count.  Above either cap
    the field is left empty and the result is *not* used as evidence either way.
    """

    if a.num_qubits != b.num_qubits:
        return False
    if a.num_qubits > MAX_OPERATOR_QUBITS:
        return None
    if max(a.size(), b.size()) > MAX_OPERATOR_GATES:
        return None
    return bool(Operator(a).equiv(Operator(b)))


# --------------------------------------------------------------------------- #
# external optimizers
# --------------------------------------------------------------------------- #
def run_qiskit_l3(circuit: QuantumCircuit) -> QuantumCircuit:
    return transpile(circuit, basis_gates=FAIR, optimization_level=3, seed_transpiler=SEED)


def run_pytket_fpo(circuit: QuantumCircuit) -> QuantumCircuit:
    from pytket._tket.circuit import OpType
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import FullPeepholeOptimise

    tk = qiskit_to_tk(circuit)
    FullPeepholeOptimise(target_2qb_gate=OpType.CX, allow_swaps=True).apply(tk)
    # allow_swaps=True leaves implicit wire swaps in the circuit; without this
    # flag tk_to_qiskit silently drops them and the output is not equivalent.
    return tk_to_qiskit(tk, replace_implicit_swaps=True)


def run_pytket_remove(circuit: QuantumCircuit) -> QuantumCircuit:
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import RemoveRedundancies

    tk = qiskit_to_tk(circuit)
    RemoveRedundancies().apply(tk)
    return tk_to_qiskit(tk, replace_implicit_swaps=True)


def _pyzx_qubits(gate: Any) -> list[int]:
    if hasattr(gate, "targets"):
        return [int(q) for q in gate.targets]
    if hasattr(gate, "target") and hasattr(gate, "control"):
        return [int(gate.control), int(gate.target)]
    if hasattr(gate, "target"):
        return [int(gate.target)]
    raise ValueError(f"pyzx_gate_shape:{type(gate).__name__}")


def run_pyzx_full_reduce(circuit: QuantumCircuit) -> QuantumCircuit:
    import pyzx as zx
    from qiskit import qasm2

    graph = zx.Circuit.from_qasm(qasm2.dumps(circuit)).to_graph()
    zx.full_reduce(graph, quiet=True)
    reduced = zx.extract_circuit(graph).to_basic_gates()

    out = QuantumCircuit(circuit.num_qubits)
    for gate in reduced.gates:
        name = str(gate.name).upper()
        qs = _pyzx_qubits(gate)
        if name in {"H", "HAD"}:
            out.h(qs[0])
        elif name in {"X", "NOT"}:
            out.x(qs[0])
        elif name == "Z":
            out.z(qs[0])
        elif name == "S":
            out.s(qs[0])
        elif name in {"SDG", "SDAG"}:
            out.sdg(qs[0])
        elif name == "T":
            out.t(qs[0])
        elif name in {"TDG", "TDAG"}:
            out.tdg(qs[0])
        elif name in {"CNOT", "CX"}:
            out.cx(qs[0], qs[1])
        elif name == "CZ":
            out.cz(qs[0], qs[1])
        elif name == "SWAP":
            out.swap(qs[0], qs[1])
        elif name in {"ZPHASE", "Z_PHASE"}:
            # pyzx stores phases in units of pi.
            out.rz(float(gate.phase) * math.pi, qs[0])
        elif name in {"XPHASE", "X_PHASE"}:
            out.h(qs[0])
            out.rz(float(gate.phase) * math.pi, qs[0])
            out.h(qs[0])
        elif name == "CCZ":
            out.ccz(qs[0], qs[1], qs[2])
        else:
            raise ValueError(f"pyzx_gate_unmapped:{name}")
    return out


OPTIMIZERS = {
    "qiskit_l3": run_qiskit_l3,
    "pytket_fpo": run_pytket_fpo,
    "pytket_remove": run_pytket_remove,
    "pyzx_full_reduce": run_pyzx_full_reduce,
}


# --------------------------------------------------------------------------- #
def build_ghz(n: int) -> QuantumCircuit:
    circuit = QuantumCircuit(n)
    circuit.h(0)
    for q in range(n - 1):
        circuit.cx(q, q + 1)
    return circuit


def normalizer_audit() -> dict[str, Any]:
    failures: list[dict[str, Any]] = []
    checked = 0
    for row in csv.DictReader(MANIFEST.open(encoding="utf-8", newline="")):
        circuit = QuantumCircuit.from_qasm_file(str(ROOT / row["normalized_path"]))
        got = metrics(circuit)["cost_declared"]
        want = int(row["normalized_gate_count"])
        checked += 1
        if got != want:
            failures.append(
                {
                    "source_id": row["source_id"],
                    "circuit_id": row["circuit_id"],
                    "expected": want,
                    "got": got,
                }
            )
    return {"checked": checked, "failures": failures, "status": "PASS" if not failures else "FAIL"}


def part_a_scaling() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for n in GHZ_SIZES:
        base = build_ghz(n)
        bm = metrics(base)
        for name, fn in OPTIMIZERS.items():
            record: dict[str, Any] = {
                "panel": "A_ghz_scaling",
                "n_qubits": n,
                "circuit_family": "GHZ",
                "circuit_id": f"ghz_{n}_synthetic",
                "optimizer": name,
                "theorem_bound": n,
                "baseline_cost_fair": bm["cost_fair"],
                "baseline_two_qubit": bm["two_qubit"],
                "status": "OK",
                "cost_fair": None,
                "cost_declared": None,
                "two_qubit": None,
                "delta_vs_baseline": None,
                "beats_baseline": None,
                "beats_theorem": None,
                "equivalent": None,
                "seconds": None,
            }
            start = time.time()
            try:
                out = fn(base)
                m = metrics(out)
                record.update(m)
                record["delta_vs_baseline"] = bm["cost_fair"] - m["cost_fair"]
                record["beats_baseline"] = bool(m["cost_fair"] < bm["cost_fair"])
                record["beats_theorem"] = bool(m["cost_fair"] < n)
                record["equivalent"] = equivalent(base, out)
            except Exception as exc:  # noqa: BLE001
                record["status"] = f"ERROR:{type(exc).__name__}:{exc}"[:200]
            record["seconds"] = round(time.time() - start, 2)
            rows.append(record)
            print(f"  A n={n:2d} {name:18s} {record['status'][:28]:28s} fair={record['cost_fair']}", flush=True)
    return rows


def part_b_panel(out_path: Path, max_gates: int | None = None) -> list[dict[str, Any]]:
    classification = {
        row["source_id"]: row
        for row in csv.DictReader(CLASSIFICATION.open(encoding="utf-8", newline=""))
    }
    manifest = [
        row
        for row in csv.DictReader(MANIFEST.open(encoding="utf-8", newline=""))
        if row["source_kind"] == "e39"
    ]
    manifest.sort(key=lambda r: int(r["normalized_gate_count"]))
    rows: list[dict[str, Any]] = []
    fields = [
        "panel", "source_id", "circuit_id", "circuit_family", "n_qubits", "optimizer",
        "classification_status", "baseline_cost", "baseline_cost_fair", "baseline_two_qubit",
        "input_cost", "status", "cost_fair", "cost_declared", "two_qubit",
        "delta_vs_baseline", "beats_baseline", "equivalent", "seconds",
    ]
    handle = out_path.open("w", encoding="utf-8", newline="")
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    for i, meta in enumerate(manifest, 1):
        source_id = meta["source_id"]
        cls = classification.get(source_id, {})
        baseline_cost = int(cls["baseline_cost"])
        circuit = QuantumCircuit.from_qasm_file(str(ROOT / meta["normalized_path"]))
        bm = metrics(circuit)
        family = meta["circuit_family"]
        for name, fn in OPTIMIZERS.items():
            record: dict[str, Any] = {
                "panel": "B_fixed_panel",
                "source_id": source_id,
                "circuit_id": meta["circuit_id"],
                "circuit_family": family,
                "n_qubits": int(meta["n_qubits"]),
                "optimizer": name,
                "classification_status": cls.get("classification_status", ""),
                "baseline_cost": baseline_cost,
                "baseline_cost_fair": bm["cost_fair"],
                "baseline_two_qubit": bm["two_qubit"],
                "input_cost": int(meta["normalized_gate_count"]),
                "status": "OK",
                "cost_fair": None,
                "cost_declared": None,
                "two_qubit": None,
                "delta_vs_baseline": None,
                "beats_baseline": None,
                "equivalent": None,
                "seconds": None,
            }
            if name == "pyzx_full_reduce" and family not in CLIFFORD_FAMILIES:
                record["status"] = "SKIPPED_NON_CLIFFORD"
            elif max_gates is not None and int(meta["normalized_gate_count"]) > max_gates and name != "pytket_remove":
                record["status"] = "SKIPPED_OVERSIZE"
            else:
                start = time.time()
                try:
                    out = fn(circuit)
                    m = metrics(out)
                    record.update(m)
                    # Compare against the project's frozen baseline (the greedy
                    # fixed point), NOT against the raw input: the question is
                    # whether an external optimizer beats the certified baseline.
                    record["delta_vs_baseline"] = baseline_cost - m["cost_fair"]
                    record["beats_baseline"] = bool(m["cost_fair"] < baseline_cost)
                    record["equivalent"] = equivalent(circuit, out)
                except Exception as exc:  # noqa: BLE001
                    record["status"] = f"ERROR:{type(exc).__name__}:{exc}"[:200]
                record["seconds"] = round(time.time() - start, 2)
            rows.append(record)
            writer.writerow(record)
        handle.flush()
        print(
            f"  B [{i:2d}/{len(manifest)}] {meta['circuit_id'][:26]:26s} base={bm['cost_fair']:4d} "
            f"best={min((r['cost_fair'] for r in rows[-4:] if r['cost_fair'] is not None), default=None)}",
            flush=True,
        )
    handle.close()
    return rows


def gate_set_probe() -> list[dict[str, Any]]:
    """Is the GHZ >= n bound specific to the declared gate set?"""

    bases = {
        "cx_only": ["h", "x", "rz", "cx"],
        "cz_only": ["h", "x", "rz", "cz"],
        "rzz_native": ["h", "x", "rz", "rzz"],
        "ecr_native": ["h", "x", "rz", "ecr"],
        "iswap_native": ["h", "x", "rz", "iswap"],
        "swap_allowed": ["h", "x", "rz", "cx", "swap", "cz"],
        "one_2q_gate_u_1q": ["u", "cx"],
    }
    rows = []
    for n in (8, 12):
        base = build_ghz(n)
        for label, basis in bases.items():
            record = {"n_qubits": n, "basis": label, "status": "OK", "cost": None, "two_qubit": None}
            try:
                out = transpile(base, basis_gates=basis, optimization_level=3, seed_transpiler=SEED)
                counts = dict(out.count_ops())
                record["cost"] = int(sum(counts.values()))
                record["two_qubit"] = int(
                    sum(v for k, v in counts.items() if k in TWO_Q)
                )
            except Exception as exc:  # noqa: BLE001
                record["status"] = f"ERROR:{type(exc).__name__}:{exc}"[:160]
            rows.append(record)
    return rows


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def summarise(panel: list[dict[str, Any]]) -> dict[str, Any]:
    per_family: dict[str, dict[str, Any]] = {}
    for row in panel:
        fam = row["circuit_family"]
        slot = per_family.setdefault(
            fam, {"sources": set(), "beaten": 0, "max_gain": 0, "errors": 0, "skipped": 0}
        )
        slot["sources"].add(row["source_id"])
        if row["status"] == "SKIPPED_NON_CLIFFORD":
            slot["skipped"] += 1
            continue
        if row["status"] != "OK":
            slot["errors"] += 1
            continue
        if row["beats_baseline"]:
            slot["beaten"] += 1
        slot["max_gain"] = max(slot["max_gain"], row["delta_vs_baseline"] or 0)
    return {
        fam: {
            "sources": len(slot["sources"]),
            "rows_beating_baseline": slot["beaten"],
            "largest_gain_over_baseline": slot["max_gain"],
            "errors": slot["errors"],
            "skipped": slot["skipped"],
        }
        for fam, slot in sorted(per_family.items())
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default=str(OUTPUT_ROOT))
    parser.add_argument("--skip-audit", action="store_true")
    parser.add_argument("--max-gates", type=int, default=None)
    parser.add_argument("--only", default=None, help="comma-separated optimizer subset")
    args = parser.parse_args()
    out_root = Path(args.out)
    out_root.mkdir(parents=True, exist_ok=True)

    audit = {"status": "SKIPPED"} if args.skip_audit else normalizer_audit()
    print(f"normaliser audit: {audit['status']} ({audit.get('checked')} sources, {len(audit.get('failures', []))} failures)", flush=True)

    global OPTIMIZERS
    if args.only:
        keep = {k.strip() for k in args.only.split(",")}
        OPTIMIZERS = {k: v for k, v in OPTIMIZERS.items() if k in keep}

    print("part A: GHZ scaling", flush=True)
    scaling = part_a_scaling()
    write_csv(out_root / "ghz_scaling_rows.csv", scaling)

    print("part B: fixed panel", flush=True)
    panel_name = "panel_rows.csv" if not args.only else f"panel_rows_subset_{args.only.replace(',', '_')}.csv"
    panel = part_b_panel(out_root / panel_name, max_gates=args.max_gates)

    probe = gate_set_probe()
    write_csv(out_root / "gate_set_probe.csv", probe)

    fam = summarise(panel)
    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-20",
        "qiskit_version": __import__("qiskit").__version__,
        "pytket_version": __import__("pytket").__version__,
        "pyzx_version": __import__("pyzx").__version__,
        "normalizer_audit": audit,
        "part_a": {
            "sizes": list(GHZ_SIZES),
            "rows": len(scaling),
            "theorem_violations": sum(1 for r in scaling if r.get("beats_theorem")),
            "baseline_beaten": sum(1 for r in scaling if r.get("beats_baseline")),
            "equivalence_failures": sum(1 for r in scaling if r.get("equivalent") is False),
            "min_cost_by_n": {
                str(n): min(
                    (r["cost_fair"] for r in scaling if r["n_qubits"] == n and r.get("cost_fair") is not None),
                    default=None,
                )
                for n in GHZ_SIZES
            },
        },
        "part_b": {
            "rows": len(panel),
            "real_sources": len({r["source_id"] for r in panel}),
            "by_family": fam,
            "ceiling_families": {k: v for k, v in fam.items() if k in {"GHZ", "SurfaceCode"}},
            "equivalence_failures": sum(1 for r in panel if r.get("equivalent") is False),
            "rows_beating_baseline": sum(1 for r in panel if r.get("beats_baseline")),
            "sources_beaten_by_any_tool": len(
                {r["source_id"] for r in panel if r.get("beats_baseline")}
            ),
        },
        "gate_set_probe": probe,
    }
    (out_root / "summary.json").write_text(json.dumps(summary, indent=1, default=str), encoding="utf-8")
    print(json.dumps(summary["part_a"], indent=1, default=str))
    print(json.dumps(summary["part_b"]["ceiling_families"], indent=1, default=str))
    print(json.dumps({"beaten_sources": summary["part_b"]["sources_beaten_by_any_tool"],
                      "equivalence_failures": summary["part_b"]["equivalence_failures"]}, indent=1))
    print(json.dumps(probe, indent=1))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        raise SystemExit(1)
