"""Execute and bind the Qiskit PassManager integration contract."""

from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.transpiler import PassManager

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.integrations import QResearchOptimizationPass  # noqa: E402
from src.optimisation import GreedyGateCancellation  # noqa: E402

OUTPUT = ROOT / "release/compiler_integration_audit.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path = OUTPUT) -> dict[str, object]:
    circuit = QuantumCircuit(3)
    circuit.h(0)
    circuit.h(0)
    circuit.cx(0, 1)
    circuit.cx(0, 1)
    circuit.rz(0.25, 2)
    circuit.rz(-0.25, 2)
    adapter = QResearchOptimizationPass(GreedyGateCancellation())
    manager = PassManager([adapter])
    optimized = manager.run(circuit)
    metadata = manager.property_set["qresearch_optimization"]
    if optimized.size() != 0 or metadata["certificate"]["accepted"] is not True:
        raise RuntimeError("Qiskit PassManager sentinel integration failed")
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_QISKIT_PASSMANAGER_DIRECT_INTEGRATION",
        "sentinel": {
            "original_size": circuit.size(),
            "optimized_size": optimized.size(),
            "certificate_status": metadata["certificate"]["status"],
            "certificate_accepted": metadata["certificate"]["accepted"],
        },
        "metric_dispositions": {
            "16.13": (
                "PARTIAL: Q-research optimizers now integrate directly as a fail-closed Qiskit "
                "TransformationPass, but native Cirq and tket pass adapters are not implemented"
            )
        },
        "claim_boundary": (
            "The adapter proves direct Qiskit PassManager interoperability for BaseOptimizer "
            "implementations and independently rejects semantically invalid output. It is not "
            "a Cirq, tket, MLIR, QIR, or production-plugin integration."
        ),
        "source_bindings": {
            path.relative_to(ROOT).as_posix(): _sha(path)
            for path in (
                ROOT / "src/integrations/qiskit_pass.py",
                ROOT / "src/integrations/__init__.py",
                ROOT / "analysis/compiler_integration_audit.py",
            )
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    return payload


if __name__ == "__main__":
    audit = build()
    print(json.dumps({"status": audit["status"], "sentinel": audit["sentinel"]}, sort_keys=True))
