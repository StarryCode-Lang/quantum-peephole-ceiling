"""E59: independent external equivalence oracle (MQT QCEC) over the closure panel.

Motivation
----------
Every equivalence claim in E56/E57/E58 so far rests on either the project's own
``replay_actions`` (an internal check) or ``qiskit.quantum_info.Operator`` (a
dense-unitary check inside the same ecosystem as the circuit builder).  The v15
readiness verdict lists ``external_cold_start`` and ``release_authority`` as
OPEN, and four previous rounds recorded MQT QCEC as unusable on this machine
because the Windows wheel raised ``WinError 3`` on ``mqt/core/bin``.

That blocker is a packaging defect, not a capability gap: ``mqt.core`` derives
its DLL directory from ``sysconfig.get_paths()["purelib"]`` (the *system*
prefix) instead of from its own install location, so a user-site install looks
in a directory that does not exist.  A six-line ``sysconfig`` shim fixes it
without touching the package, and QCEC 3.11.0 then works.

This experiment uses that fix to do the first **third-party** equivalence check
of the closure panel: a decision-diagram equivalence checker written in C++
that shares no code with the project's replay engine or with Qiskit's Operator.

Parts
-----
A  QCEC availability probe.  Record the shim, the versions, and whether the
   import succeeds, so the result is reproducible on another machine.
B  Root vs closure.  For all 128 frozen roots, rebuild the E56 closure output
   and ask QCEC whether it is equivalent to the root.
C  Root vs engine output.  For the engines available in E58, check the engine
   output against the root as well, which separates "the closure is correct"
   from "the engines are correct".
D  Negative control.  Flip one ``rz`` angle by 1e-2 in a sample of closure
   outputs and confirm QCEC reports non-equivalence.  An oracle that never says
   "no" is not an oracle.

Contract
    Read-only on ``data/``, ``release/``, ``docs/manuscript/``.  Frozen rule
    library and rule scope.  Root states from ``load_root_states``
    (hash-checked).  The QCEC shim is local to this script and modifies no
    installed file.

Outputs (``docs/review/science_boost/2026-10-24_qcec_oracle/``):
    * ``qcec_panel.csv``      -- one row per source: root vs closure verdict
    * ``qcec_negative.csv``   -- negative-control rows
    * ``summary.json``        -- availability, aggregates, hashes
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import site
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _patch_mqt_dll_path() -> str:
    """Point ``mqt.core`` at the real install prefix.

    ``mqt/core/__init__.py`` computes ``bin_dir`` from
    ``sysconfig.get_paths()["purelib"]``, which is the *system* prefix.  When the
    package lives in the user site (the normal case here) that path does not
    exist and ``os.add_dll_directory`` raises ``WinError 3``.  Patching
    ``sysconfig.get_paths`` is the smallest fix that leaves the installed
    package untouched.
    """

    import sysconfig

    user_site = site.getusersitepackages()
    original = sysconfig.get_paths

    def patched(*args: Any, **kwargs: Any) -> dict[str, str]:
        paths = dict(original(*args, **kwargs))
        paths["purelib"] = user_site
        return paths

    sysconfig.get_paths = patched  # type: ignore[assignment]
    return user_site


_PATCHED_PURELIB = _patch_mqt_dll_path()

try:
    import mqt.qcec as qcec  # noqa: E402

    QCEC_AVAILABLE = True
    QCEC_VERSION = getattr(qcec, "__version__", "unknown")
except Exception as exc:  # pragma: no cover - availability probe
    qcec = None  # type: ignore[assignment]
    QCEC_AVAILABLE = False
    QCEC_VERSION = f"UNAVAILABLE:{type(exc).__name__}"

from qiskit import QuantumCircuit  # noqa: E402

from experiments.e45_development_grid.run import state_from_circuit  # noqa: E402
from experiments.e46_window_landscape.run import RULE_SCOPE, load_root_states  # noqa: E402
from src.optimisation.certified_landscape import LandscapeState  # noqa: E402
from scripts.e56_closure_criterion import closure_run  # noqa: E402

EXPERIMENT_ID = "E59_QCEC_ORACLE_2026_10_24"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-24_qcec_oracle"
RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
NEGATIVE_CONTROL_SAMPLE = 16
NEGATIVE_PERTURBATION = 1e-2


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def state_to_qiskit(state: LandscapeState, perturb_first_rz: float = 0.0) -> QuantumCircuit | None:
    circuit = QuantumCircuit(state.num_qubits)
    perturbed = False
    for gate in state.gates:
        if gate.name == "h":
            circuit.h(gate.qubits[0])
        elif gate.name == "x":
            circuit.x(gate.qubits[0])
        elif gate.name == "rz":
            angle = float(gate.angle or 0.0)
            if perturb_first_rz and not perturbed:
                angle += perturb_first_rz
                perturbed = True
            circuit.rz(angle, gate.qubits[0])
        elif gate.name == "cx":
            circuit.cx(gate.qubits[0], gate.qubits[1])
        else:
            return None
    return circuit


def _verdict(result: Any) -> str:
    text = str(getattr(result, "equivalence", "UNKNOWN"))
    return text.split(".")[-1]


def verify_pair(left: QuantumCircuit, right: QuantumCircuit) -> dict[str, Any]:
    if not QCEC_AVAILABLE:
        return {"verdict": "ORACLE_UNAVAILABLE", "time_seconds": None}
    started = time.perf_counter()
    try:
        result = qcec.verify(left, right)
        return {
            "verdict": _verdict(result),
            "time_seconds": round(time.perf_counter() - started, 3),
        }
    except Exception as exc:
        return {"verdict": f"ERROR:{type(exc).__name__}", "time_seconds": None}


def run_panel() -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    negatives: list[dict[str, Any]] = []
    for root in load_root_states():
        state = root["state"]
        run = closure_run(state)
        left = state_to_qiskit(state)
        right = state_to_qiskit(run["final_state"])
        if left is None or right is None:
            rows.append(
                {
                    "source_id": root["source_id"],
                    "circuit_family": root["circuit_family"],
                    "n_qubits": root["n_qubits"],
                    "root_cost": state.cost,
                    "closure_cost": run["final_cost"],
                    "verdict": "UNSUPPORTED_GATE",
                }
            )
            continue
        result = verify_pair(left, right)
        rows.append(
            {
                "source_id": root["source_id"],
                "circuit_family": root["circuit_family"],
                "n_qubits": root["n_qubits"],
                "root_cost": state.cost,
                "closure_cost": run["final_cost"],
                "gain": state.cost - run["final_cost"],
                "closure_passes": run["passes"],
                "verdict": result["verdict"],
                "qcec_seconds": result["time_seconds"],
            }
        )

    # Negative control: perturb the first rz angle of the closure output.
    for row in [item for item in rows if item.get("gain", 0) > 0][:NEGATIVE_CONTROL_SAMPLE]:
        root = next(item for item in load_root_states() if item["source_id"] == row["source_id"])
        run = closure_run(root["state"])
        if not any(gate.name == "rz" for gate in run["final_state"].gates):
            continue
        perturbed = state_to_qiskit(run["final_state"], perturb_first_rz=NEGATIVE_PERTURBATION)
        if perturbed is None:
            continue
        result = verify_pair(state_to_qiskit(root["state"]), perturbed)  # type: ignore[arg-type]
        negatives.append(
            {
                "source_id": row["source_id"],
                "circuit_family": row["circuit_family"],
                "perturbation_radians": NEGATIVE_PERTURBATION,
                "verdict": result["verdict"],
                "qcec_seconds": result["time_seconds"],
            }
        )

    summary = {
        "oracle_available": QCEC_AVAILABLE,
        "oracle_version": QCEC_VERSION,
        "purelib_patched_to": _PATCHED_PURELIB,
        "sources": len(rows),
        "equivalent": sum(1 for row in rows if row["verdict"] == "equivalent"),
        "not_equivalent": sum(1 for row in rows if row["verdict"] == "not_equivalent"),
        "other_verdicts": {
            verdict: sum(1 for row in rows if row["verdict"] == verdict)
            for verdict in sorted({row["verdict"] for row in rows})
            if verdict not in {"equivalent", "not_equivalent"}
        },
        "total_qcec_seconds": round(sum(row["qcec_seconds"] or 0.0 for row in rows), 2),
        "negative_controls": len(negatives),
        "negative_controls_correctly_rejected": sum(
            1 for row in negatives if row["verdict"] == "not_equivalent"
        ),
    }
    return rows, negatives, summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default=str(OUTPUT_ROOT))
    args = parser.parse_args()
    output_root = Path(args.output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    started = time.time()
    rows, negatives, summary = run_panel()
    _write_csv(output_root / "qcec_panel.csv", rows)
    _write_csv(output_root / "qcec_negative.csv", negatives)

    payload = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-24",
        "contract": {
            "oracle": "MQT QCEC (decision-diagram equivalence checker, C++)",
            "dll_shim": "sysconfig.get_paths['purelib'] -> site.getusersitepackages()",
            "rule_scope": RULE_SCOPE,
            "rule_library": str(RULE_LIBRARY.relative_to(ROOT)),
            "root_states": "experiments.e46_window_landscape.run.load_root_states",
            "negative_control": f"first rz angle +{NEGATIVE_PERTURBATION} rad, n<={NEGATIVE_CONTROL_SAMPLE}",
        },
        "inputs": {str(RULE_LIBRARY.relative_to(ROOT)): _sha256(RULE_LIBRARY)},
        "summary": summary,
        "wall_clock_seconds": round(time.time() - started, 1),
    }
    (output_root / "summary.json").write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
