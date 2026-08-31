"""Freeze and materialize a bounded official MQT Bench four-level panel."""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path

from mqt.bench import BenchmarkLevel, get_benchmark
from mqt.bench.targets import get_device
from qiskit import qasm2

ROOT = Path(__file__).resolve().parents[1]
PROTOCOL = ROOT / "experiments/e34_mqt_cross_abstraction_protocol.json"
OUTPUT = ROOT / "data/v11/e34_mqt_cross_abstraction"
CASES = (("qft", 5), ("ghz", 8), ("qwalk", 5))
LEVELS = (BenchmarkLevel.ALG, BenchmarkLevel.INDEP, BenchmarkLevel.NATIVEGATES, BenchmarkLevel.MAPPED)
TARGET_NAME = "ibm_falcon_27"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def freeze(path: Path) -> dict[str, object]:
    if importlib.metadata.version("mqt.bench") != "2.2.3":
        raise ValueError("freeze requires mqt.bench 2.2.3")
    payload = {
        "schema_version": "1.1.0", "experiment_id": "E34_MQT_CROSS_ABSTRACTION_V1_1", "design_status": "FROZEN_BEFORE_EXECUTION", "freeze_date": "2026-08-31",
        "pre_execution_amendment": {"reason": "The first materialization generated all 12 artifacts and valid mapped edges but the local native-alphabet gate incorrectly treated the QASM barrier compiler directive as a device operation. The incomplete summary is preserved under data/v11/e34_mqt_cross_abstraction_preflight_invalid_barrier. The invariant now ignores only barrier; sample, levels, target, estimand, and generated-circuit settings are unchanged.", "scientific_question_changed": False, "sample_changed": False, "estimand_changed": False},
        "research_question": "Can the repository ingest and characterize the same official MQT Bench algorithms across ALG, INDEP, NATIVEGATES, and MAPPED representations without conflating representation-level metrics?",
        "sample": [{"benchmark": name, "circuit_size": size} for name, size in CASES],
        "levels": [level.name for level in LEVELS], "target": TARGET_NAME, "opt_level": 2, "random_parameters": False,
        "selection_rule": "three named algorithms and sizes fixed before materialization; all four official abstraction levels required for every case; no outcome-dependent substitution",
        "estimand": "descriptive representation-specific gate count, depth, gate alphabet, width, and mapped two-qubit edge validity for each same-case four-level block",
        "failure_semantics": "any missing/error level makes the 12-artifact panel incomplete; no cross-level gate-count effect is interpreted as algorithmic optimization gain",
        "claim_boundary": "Bounded MQT Bench 2.2.3 alignment on three fixed algorithms and one IBM Falcon-27 target; not exhaustive over MQT algorithms, targets, versions, mappings, or compiler seeds.",
        "source_sha256": {"experiments/e34_mqt_cross_abstraction.py": sha256(Path(__file__).resolve()), "scripts/verify_e34_mqt_cross_abstraction.py": sha256(ROOT / "scripts/verify_e34_mqt_cross_abstraction.py")},
    }
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return payload


def formal(protocol_path: Path, output_dir: Path) -> dict[str, object]:
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("design_status") != "FROZEN_BEFORE_EXECUTION" or protocol["source_sha256"]["experiments/e34_mqt_cross_abstraction.py"] != sha256(Path(__file__).resolve()):
        raise ValueError("E34 protocol/source binding failed")
    if importlib.metadata.version("mqt.bench") != "2.2.3":
        raise ValueError("formal run requires frozen mqt.bench version")
    target = get_device(protocol["target"])
    coupling = sorted([list(map(int, edge)) for edge in target.build_coupling_map().get_edges()])
    operations = sorted(target.operation_names)
    output_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in protocol["sample"]:
        for level_name in protocol["levels"]:
            level = BenchmarkLevel[level_name]
            kwargs = {"target": target} if level in (BenchmarkLevel.NATIVEGATES, BenchmarkLevel.MAPPED) else {}
            circuit = get_benchmark(case["benchmark"], level, int(case["circuit_size"]), opt_level=int(protocol["opt_level"]), random_parameters=False, **kwargs)
            qasm_path = output_dir / "qasm" / f"{case['benchmark']}_{case['circuit_size']}_{level_name.lower()}.qasm"
            qasm_path.parent.mkdir(parents=True, exist_ok=True)
            qasm2.dump(circuit, qasm_path)
            two_q_edges = sorted({tuple(sorted(circuit.find_bit(bit).index for bit in instruction.qubits)) for instruction in circuit.data if len(instruction.qubits) == 2})
            row = {
                "case_id": f"{case['benchmark']}_{case['circuit_size']}", "benchmark": case["benchmark"], "circuit_size": int(case["circuit_size"]), "level": level_name,
                "n_qubits": int(circuit.num_qubits), "gate_count": int(circuit.size()), "depth": int(circuit.depth() or 0), "gate_alphabet": sorted(circuit.count_ops()),
                "qasm_path": str(qasm_path.relative_to(ROOT)).replace("\\", "/"), "qasm_sha256": sha256(qasm_path),
                "all_native_operations": level not in (BenchmarkLevel.NATIVEGATES, BenchmarkLevel.MAPPED) or (set(circuit.count_ops()) - {"barrier"}).issubset(set(operations)),
                "all_mapped_two_qubit_edges_valid": level != BenchmarkLevel.MAPPED or all(list(edge) in coupling or list(reversed(edge)) in coupling for edge in two_q_edges),
                "layout_present": getattr(circuit, "layout", None) is not None,
            }
            rows.append(row)
            print(f"[{len(rows):02d}/12] {row['case_id']} {level_name} gates={row['gate_count']}", flush=True)
    blocks = {case["case_id"]: sorted(row["level"] for row in rows if row["case_id"] == case["case_id"]) for case in rows}
    complete = len(rows) == 12 and all(levels == sorted(protocol["levels"]) for levels in blocks.values()) and all(row["all_native_operations"] and row["all_mapped_two_qubit_edges_valid"] for row in rows)
    summary = {
        "schema_version": "1.0.0", "status": "FORMAL_BOUNDED_PANEL_COMPLETE" if complete else "INCOMPLETE_OR_INVALID", "protocol_sha256": sha256(protocol_path), "rows": rows,
        "target_operation_names": operations, "target_coupling_edges": coupling,
        "environment": {"python": sys.version, "executable": str(Path(sys.executable).resolve()), "executable_sha256": sha256(Path(sys.executable).resolve()), "platform": platform.platform(), "mqt.bench": importlib.metadata.version("mqt.bench"), "qiskit": importlib.metadata.version("qiskit")},
        "metric_dispositions": {"5.28": {"status": "PASS" if complete else "PARTIAL", "disposition": "All three frozen same-algorithm blocks materialize at all four official MQT Bench abstraction levels with native-gate and mapped-edge invariants; scope remains the bounded panel."}},
        "claim_boundary": protocol["claim_boundary"],
    }
    summary_path = output_dir / "summary.json"; summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    artifacts = [protocol_path, Path(__file__).resolve(), ROOT / "scripts/verify_e34_mqt_cross_abstraction.py", summary_path] + sorted((output_dir / "qasm").glob("*.qasm"))
    manifest = {"schema_version": "1.0.0", "artifact_count": len(artifacts), "artifacts": [{"path": str(path.relative_to(ROOT)).replace("\\", "/"), "bytes": path.stat().st_size, "sha256": sha256(path)} for path in artifacts]}
    (output_dir / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", type=Path, default=PROTOCOL); parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    parser.add_argument("--freeze", action="store_true"); parser.add_argument("--formal", action="store_true")
    args = parser.parse_args()
    if args.freeze:
        print(json.dumps(freeze(args.protocol.resolve()), indent=2, sort_keys=True)); return 0
    if not args.formal:
        raise SystemExit("choose --freeze or --formal")
    summary = formal(args.protocol.resolve(), args.output_dir.resolve())
    print(json.dumps({"status": summary["status"], "rows": len(summary["rows"]), "protocol_sha256": summary["protocol_sha256"]}, indent=2)); return 0


if __name__ == "__main__":
    raise SystemExit(main())
