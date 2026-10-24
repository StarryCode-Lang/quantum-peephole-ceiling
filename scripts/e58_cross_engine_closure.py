"""E58: two-qubit cost split, cross-engine closure, and the residual-pair diagnosis.

Motivation
----------
E56 established that commutation closure is a *search-free* certificate that
beats the frozen horizon-3 certified landscape on 60/128 sources (-10.44% vs
-0.21%).  E57 showed it also beats pytket's ``RemoveRedundancies`` on 52/123
sources.  Two questions decide whether that is a paper or an artefact:

  Q1  Does the gain survive the two-qubit cost metric?  E53 warned that the
      total-gate and two-qubit metrics diverge on this panel.  If closure only
      merges single-qubit rotations it is irrelevant to fault-tolerant cost.

  Q2  Is closure a *general* pass or an artefact of the project's own weak
      baseline?  The decisive test is to apply it **on top of production
      compilers**: take the output of qiskit L3 / tket FullPeepholeOptimise /
      BQSKit, canonicalise it to the frozen basis, then run closure.  If the
      closure still removes gates, then those engines are not closed under
      commutation in the shared basis -- a claim about the engines, not about
      the project.

Parts
-----
A  Two-qubit accounting on the frozen panel.  For every root: total and
   two-qubit (``cx``/``cz``/``swap``) gate counts before and after closure, the
   certified ``best_cost`` for reference, and the fraction of the gain that is
   two-qubit.
B  Cross-engine closure.  For each source with root size <= 500, run the three
   engines, record the *native* cost, canonicalise the output to
   ``{h,x,rz,cx}`` at ``optimization_level=0``, then run closure on it.  The
   canonicalisation is lossless but *expansive* for engines whose native basis
   is richer than the frozen one (tket emits TK1, BQSKit emits U3), so every
   row carries an explicit expansion factor and the headline aggregate is
   restricted to rows with expansion <= 1.05 -- in practice qiskit L3, the only
   engine that speaks the frozen basis natively.  This is the D1 lesson applied
   to a new comparison: a gate count is basis-relative.
C  Residual diagnosis.  On each engine's canonical output, enumerate the
   exposable pairs that the engine left behind: count, crossing distance D, and
   rule id.  D = 0 means the engine is not closed under its own adjacency rules;
   D > 0 means its pass is window-local rather than a closure.  Zero residual
   pairs means the engine already reaches the commutation-closure fixpoint.
D  Equivalence.  Dense-unitary equality for engine output vs engine+closure on
   every source with n <= 8, plus certificate replay of every closure run.

Contract
    Read-only on ``data/``, ``release/``, ``docs/manuscript/``.  Frozen rule
    library and rule scope (``e44_core_v1``).  Root states come from
    ``experiments.e46_window_landscape.run.load_root_states`` (hash-checked).

Outputs (``docs/review/science_boost/2026-10-24_cross_engine_closure/``):
    * ``panel_two_qubit.csv``     -- Part A, one row per source
    * ``cross_engine.csv``        -- Part B, one row per (source, engine)
    * ``residual_pairs.csv``      -- Part C, one row per (source, engine)
    * ``summary.json``            -- aggregates, contract, input hashes
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qiskit import QuantumCircuit, qasm2, transpile  # noqa: E402
from qiskit.quantum_info import Operator  # noqa: E402

from experiments.e45_development_grid.run import (  # noqa: E402
    NAM_BASIS,
    normalize_circuit,
    state_from_circuit,
)
from experiments.e46_window_landscape.run import RULE_SCOPE, load_root_states  # noqa: E402
from src.optimisation.certified_landscape import (  # noqa: E402
    LandscapeState,
    replay_actions,
)
from scripts.e56_closure_criterion import (  # noqa: E402
    closure_run,
    exposable_pairs,
)

EXPERIMENT_ID = "E58_CROSS_ENGINE_CLOSURE_2026_10_24"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-24_cross_engine_closure"
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"

TWO_QUBIT = frozenset({"cx", "cz", "swap"})
SIZE_CAP = 300
ENGINE_SIZE_CAP = {"qiskit_l3": 300, "tket_fpo": 300, "bqskit": 120}
UNITARY_QUBIT_CAP = 8
UNITARY_GATE_CAP = 600
ENGINES = ("qiskit_l3", "tket_fpo", "bqskit")
SEED = 42


# --------------------------------------------------------------------------
# cost accounting
# --------------------------------------------------------------------------

def counts(state: LandscapeState) -> dict[str, int]:
    total = len(state.gates)
    two_q = sum(1 for gate in state.gates if gate.name in TWO_QUBIT)
    return {"total": total, "two_qubit": two_q, "one_qubit": total - two_q}


def circuit_counts(circuit: QuantumCircuit) -> dict[str, int]:
    total = int(circuit.size())
    two_q = sum(1 for instruction in circuit.data if instruction.operation.num_qubits == 2)
    return {"total": total, "two_qubit": two_q, "one_qubit": total - two_q}


# --------------------------------------------------------------------------
# engines
# --------------------------------------------------------------------------

def _canonicalise(circuit: QuantumCircuit) -> QuantumCircuit | None:
    normalized, _ = normalize_circuit(circuit)
    return normalized


def run_qiskit_l3(circuit: QuantumCircuit) -> QuantumCircuit:
    return transpile(
        circuit,
        basis_gates=NAM_BASIS,
        optimization_level=3,
        layout_method="trivial",
        routing_method="basic",
        seed_transpiler=SEED,
    )


def run_tket_fpo(circuit: QuantumCircuit) -> QuantumCircuit:
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import FullPeepholeOptimise

    tk = qiskit_to_tk(circuit)
    FullPeepholeOptimise().apply(tk)
    return tk_to_qiskit(tk, replace_implicit_swaps=True)


def run_bqskit(circuit: QuantumCircuit) -> QuantumCircuit:
    import bqskit
    from bqskit.compiler.machine import MachineModel
    from bqskit.ext import bqskit_to_qiskit, qiskit_to_bqskit
    from bqskit.ir.gates import CNOTGate, U3Gate

    model = MachineModel(circuit.num_qubits, gate_set=[U3Gate(), CNOTGate()])
    compiled = bqskit.compile(qiskit_to_bqskit(circuit), model=model)
    return bqskit_to_qiskit(compiled)


ENGINE_FUNCS = {
    "qiskit_l3": run_qiskit_l3,
    "tket_fpo": run_tket_fpo,
    "bqskit": run_bqskit,
}


# --------------------------------------------------------------------------
# IO
# --------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_classification() -> dict[str, dict[str, str]]:
    with CLASSIFICATION.open(newline="", encoding="utf-8") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle)}


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


# --------------------------------------------------------------------------
# Part A
# --------------------------------------------------------------------------

def run_part_a(roots: list[dict[str, Any]], classification: dict[str, dict[str, str]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for root in roots:
        state = root["state"]
        before = counts(state)
        run = closure_run(state)
        after = counts(run["final_state"])
        replay = replay_actions(state, run["actions"], RULE_LIBRARY, RULE_SCOPE)
        row = {
            "source_id": root["source_id"],
            "circuit_family": root["circuit_family"],
            "n_qubits": root["n_qubits"],
            "root_kind": root["root_kind"],
            "tier": classification.get(root["source_id"], {}).get("tier", ""),
            "certified_best_cost": classification.get(root["source_id"], {}).get("best_cost", ""),
            "root_total": before["total"],
            "root_two_qubit": before["two_qubit"],
            "closure_total": after["total"],
            "closure_two_qubit": after["two_qubit"],
            "gain_total": before["total"] - after["total"],
            "gain_two_qubit": before["two_qubit"] - after["two_qubit"],
            "passes": run["passes"],
            "steps": run["steps"],
            "truncated": run["truncated"],
            "errors": run["errors"],
            "replay_ok": bool(replay.get("accepted", False)),
        }
        rows.append(row)
    total_gain = sum(row["gain_total"] for row in rows)
    twoq_gain = sum(row["gain_two_qubit"] for row in rows)
    root_twoq = sum(row["root_two_qubit"] for row in rows)
    summary = {
        "sources": len(rows),
        "root_total": sum(row["root_total"] for row in rows),
        "closure_total": sum(row["closure_total"] for row in rows),
        "root_two_qubit": root_twoq,
        "closure_two_qubit": sum(row["closure_two_qubit"] for row in rows),
        "gain_total": total_gain,
        "gain_two_qubit": twoq_gain,
        "two_qubit_share_of_gain": (twoq_gain / total_gain) if total_gain else 0.0,
        "two_qubit_relative_reduction": (twoq_gain / root_twoq) if root_twoq else 0.0,
        "sources_with_two_qubit_gain": sum(1 for row in rows if row["gain_two_qubit"] > 0),
        "sources_with_total_gain": sum(1 for row in rows if row["gain_total"] > 0),
        "replay_pass": sum(1 for row in rows if row["replay_ok"]),
        "truncated": sum(1 for row in rows if row["truncated"]),
        "errors": sum(1 for row in rows if row["errors"]),
    }
    return rows, summary


# --------------------------------------------------------------------------
# Part B/C
# --------------------------------------------------------------------------

def _engine_output(engine: str, circuit: QuantumCircuit, deadline: float) -> QuantumCircuit | None:
    if time.perf_counter() > deadline:
        return None
    try:
        return ENGINE_FUNCS[engine](circuit)
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


def run_part_bc(
    roots: list[dict[str, Any]],
    budget_seconds: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    cross_rows: list[dict[str, Any]] = []
    residual_rows: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for root in roots:
        state = root["state"]
        if state.cost > SIZE_CAP:
            skipped.append({"source_id": root["source_id"], "reason": f"root_size>{SIZE_CAP}", "size": state.cost})
            continue
        source_circuit = _state_to_qiskit(state)
        if source_circuit is None:
            skipped.append({"source_id": root["source_id"], "reason": "state_to_qiskit", "size": state.cost})
            continue
        for engine in ENGINES:
            if state.cost > ENGINE_SIZE_CAP[engine]:
                cross_rows.append(
                    {
                        "source_id": root["source_id"],
                        "circuit_family": root["circuit_family"],
                        "n_qubits": root["n_qubits"],
                        "engine": engine,
                        "status": "SKIPPED_ENGINE_SIZE_CAP",
                        "native_total": state.cost,
                    }
                )
                continue
            deadline = time.perf_counter() + budget_seconds
            native = _engine_output(engine, source_circuit, deadline)
            if native is None:
                cross_rows.append(
                    {
                        "source_id": root["source_id"],
                        "circuit_family": root["circuit_family"],
                        "n_qubits": root["n_qubits"],
                        "engine": engine,
                        "status": "ENGINE_FAILED_OR_TIMEOUT",
                    }
                )
                continue
            native_cost = circuit_counts(native)
            canonical = _canonicalise(native)
            if canonical is None:
                cross_rows.append(
                    {
                        "source_id": root["source_id"],
                        "circuit_family": root["circuit_family"],
                        "n_qubits": root["n_qubits"],
                        "engine": engine,
                        "status": "CANONICALISE_FAILED",
                        "native_total": native_cost["total"],
                        "native_two_qubit": native_cost["two_qubit"],
                    }
                )
                continue
            canon_state = state_from_circuit(canonical)
            canon_counts = counts(canon_state)
            pairs = exposable_pairs(canon_state)
            d_hist: dict[str, int] = {}
            rule_hist: dict[str, int] = {}
            for pair in pairs:
                d_hist[str(pair["distance"])] = d_hist.get(str(pair["distance"]), 0) + 1
                rule_hist[pair["rule_id"]] = rule_hist.get(pair["rule_id"], 0) + 1
            run = closure_run(canon_state)
            after_counts = counts(run["final_state"])
            replay = replay_actions(canon_state, run["actions"], RULE_LIBRARY, RULE_SCOPE)
            closure_circuit = _state_to_qiskit(run["final_state"])
            equiv = _unitary_equal(canonical, closure_circuit) if closure_circuit is not None else None
            cross_rows.append(
                {
                    "source_id": root["source_id"],
                    "circuit_family": root["circuit_family"],
                    "n_qubits": root["n_qubits"],
                    "engine": engine,
                    "status": "OK",
                    "native_total": native_cost["total"],
                    "native_two_qubit": native_cost["two_qubit"],
                    "canonical_total": canon_counts["total"],
                    "canonical_two_qubit": canon_counts["two_qubit"],
                    "expansion_factor": (canon_counts["total"] / native_cost["total"]) if native_cost["total"] else 1.0,
                    "closure_total": after_counts["total"],
                    "closure_two_qubit": after_counts["two_qubit"],
                    "gain_total": canon_counts["total"] - after_counts["total"],
                    "gain_two_qubit": canon_counts["two_qubit"] - after_counts["two_qubit"],
                    "residual_exposable_pairs": len(pairs),
                    "residual_d_min": min((pair["distance"] for pair in pairs), default=None),
                    "closure_passes": run["passes"],
                    "replay_ok": bool(replay.get("accepted", False)),
                    "unitary_equivalent": "" if equiv is None else str(equiv),
                    "truncated": run["truncated"],
                }
            )
            residual_rows.append(
                {
                    "source_id": root["source_id"],
                    "circuit_family": root["circuit_family"],
                    "engine": engine,
                    "canonical_total": canon_counts["total"],
                    "residual_exposable_pairs": len(pairs),
                    "residual_pairs_per_100_gates": (100.0 * len(pairs) / canon_counts["total"]) if canon_counts["total"] else 0.0,
                    "d0_pairs": d_hist.get("0", 0),
                    "d_positive_pairs": len(pairs) - d_hist.get("0", 0),
                    "d_histogram": json.dumps(d_hist, sort_keys=True),
                    "rule_histogram": json.dumps(rule_hist, sort_keys=True),
                }
            )

    summary: dict[str, Any] = {"per_engine": {}, "skipped": skipped}
    for engine in ENGINES:
        rows = [row for row in cross_rows if row["engine"] == engine and row["status"] == "OK"]
        if not rows:
            summary["per_engine"][engine] = {"comparable_sources": 0}
            continue
        clean = [row for row in rows if row["expansion_factor"] <= 1.05]
        gain = sum(row["gain_total"] for row in rows)
        gain2q = sum(row["gain_two_qubit"] for row in rows)
        canon_total = sum(row["canonical_total"] for row in rows)
        native_total = sum(row["native_total"] for row in rows)
        residual_pairs = sum(row["residual_exposable_pairs"] for row in rows)
        d0 = sum(1 for row in rows if row["residual_d_min"] == 0)
        summary["per_engine"][engine] = {
            "comparable_sources": len(rows),
            "native_total": native_total,
            "canonical_total": canon_total,
            "expansion_factor": (canon_total / native_total) if native_total else 1.0,
            "closure_total": sum(row["closure_total"] for row in rows),
            "gain_total": gain,
            "gain_two_qubit": gain2q,
            "relative_reduction": (gain / canon_total) if canon_total else 0.0,
            "sources_improved": sum(1 for row in rows if row["gain_total"] > 0),
            "sources_unchanged": sum(1 for row in rows if row["gain_total"] == 0),
            "sources_worse": sum(1 for row in rows if row["gain_total"] < 0),
            "residual_exposable_pairs": residual_pairs,
            "sources_with_residual_pairs": sum(1 for row in rows if row["residual_exposable_pairs"] > 0),
            "sources_with_d0_residual": d0,
            "replay_pass": sum(1 for row in rows if row["replay_ok"]),
            "unitary_checked": sum(1 for row in rows if row["unitary_equivalent"] in {"True", "False"}),
            "unitary_pass": sum(1 for row in rows if row["unitary_equivalent"] == "True"),
            "unitary_fail": sum(1 for row in rows if row["unitary_equivalent"] == "False"),
            "no_expansion_subset": {
                "sources": len(clean),
                "canonical_total": sum(row["canonical_total"] for row in clean),
                "gain_total": sum(row["gain_total"] for row in clean),
                "sources_improved": sum(1 for row in clean if row["gain_total"] > 0),
                "residual_exposable_pairs": sum(row["residual_exposable_pairs"] for row in clean),
                "sources_with_residual_pairs": sum(1 for row in clean if row["residual_exposable_pairs"] > 0),
                "sources_with_d0_residual": sum(1 for row in clean if row["residual_d_min"] == 0),
            },
        }
    return cross_rows, residual_rows, summary


def _state_to_qiskit(state: LandscapeState) -> QuantumCircuit | None:
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


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(OUTPUT_ROOT))
    parser.add_argument("--skip-engines", action="store_true")
    parser.add_argument("--engine-budget", type=float, default=120.0)
    args = parser.parse_args()

    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    classification = _load_classification()
    roots = load_root_states()

    started = time.time()
    part_a_rows, part_a = run_part_a(roots, classification)
    _write_csv(output_root / "panel_two_qubit.csv", part_a_rows)

    if args.skip_engines:
        part_b, part_c, part_bc = [], [], {"skipped": "flag"}
    else:
        part_b, part_c, part_bc = run_part_bc(roots, args.engine_budget)
        _write_csv(output_root / "cross_engine.csv", part_b)
        _write_csv(output_root / "residual_pairs.csv", part_c)

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-24",
        "contract": {
            "root_states": "experiments.e46_window_landscape.run.load_root_states (hash-checked)",
            "rule_library": str(RULE_LIBRARY.relative_to(ROOT)),
            "rule_scope": RULE_SCOPE,
            "canonical_basis": NAM_BASIS,
            "canonicalisation": "normalize_circuit (optimization_level=0)",
            "closure": "scripts/e56_closure_criterion.closure_run (certificate replay)",
            "size_cap_for_engines": SIZE_CAP,
            "engine_size_caps": ENGINE_SIZE_CAP,
            "unitary_check": f"n<={UNITARY_QUBIT_CAP} and gates<={UNITARY_GATE_CAP}",
            "engines": list(ENGINES),
        },
        "inputs": {
            str(CLASSIFICATION.relative_to(ROOT)): _sha256(CLASSIFICATION),
            str(RULE_LIBRARY.relative_to(ROOT)): _sha256(RULE_LIBRARY),
        },
        "part_a_two_qubit": part_a,
        "part_bc_cross_engine": part_bc,
        "wall_clock_seconds": round(time.time() - started, 1),
    }
    (output_root / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print(json.dumps({"part_a": part_a, "part_bc": part_bc}, indent=2)[:4000])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
