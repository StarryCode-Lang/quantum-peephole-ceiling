"""Recompute GUOQ pilot common-basis metrics without rerunning GUOQ.

The first pilot execution incorrectly counted a Nam-to-common adapter
transpilation as its common-basis input.  This revalidation preserves the raw
CSV and per-run JSON, then replaces only common-basis metric/reduction fields
using the frozen source common QASM and the already-emitted incumbent.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import time
from pathlib import Path

import pandas as pd
from qiskit import qasm2, transpile
from qiskit.quantum_info import Operator

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PILOT_ROOT = (
    PROJECT_ROOT / "data" / "v10" / "prepaper" / "external_baselines" /
    "guoq" / "bqskit_pilot"
)
COMMON_BASIS = ["rz", "sx", "x", "cx"]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _load(path: Path):
    return qasm2.loads(
        path.read_text(encoding="utf-8"),
        custom_instructions=qasm2.LEGACY_CUSTOM_INSTRUCTIONS,
    )


def _metrics(circuit) -> dict[str, int]:
    return {
        "gate_count": int(circuit.size()),
        "two_qubit_gate_count": int(sum(
            item.operation.num_qubits == 2 for item in circuit.data
        )),
        "depth": int(circuit.depth() or 0),
        "two_qubit_depth": int(circuit.depth(
            filter_function=lambda item: item.operation.num_qubits == 2
        ) or 0),
    }


def main() -> None:
    result_path = PILOT_ROOT / "guoq_bqskit_pilot.csv"
    metadata_path = PILOT_ROOT / "metadata.json"
    raw_root = PILOT_ROOT / "raw_pre_metric_revalidation"
    raw_csv = raw_root / result_path.name
    raw_metadata = raw_root / metadata_path.name
    if not raw_csv.exists():
        raw_root.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(result_path, raw_csv)
        shutil.copyfile(metadata_path, raw_metadata)
    frame = pd.read_csv(raw_csv)
    audit_rows = []
    updated_rows = []
    for row in frame.to_dict(orient="records"):
        source_path = PROJECT_ROOT / str(row["source_common_qasm_path"])
        output_path = PROJECT_ROOT / str(row["output_qasm_path"])
        source = _load(source_path)
        optimized = _load(output_path)
        output_common = transpile(
            optimized, basis_gates=COMMON_BASIS, optimization_level=0,
            seed_transpiler=0,
        )
        input_metrics = _metrics(source)
        output_metrics = _metrics(output_common)
        exact_equivalent = bool(Operator(source).equiv(Operator(optimized)))
        updated = dict(row)
        updated["exact_equivalent"] = exact_equivalent
        updated["valid_equivalent_output"] = exact_equivalent
        for key, value in input_metrics.items():
            updated[f"common_input_{key}"] = value
        for key, value in output_metrics.items():
            updated[f"common_output_{key}"] = value
        for key, before in input_metrics.items():
            after = output_metrics[key]
            updated[f"common_{key}_reduction_pct"] = (
                100.0 * (1.0 - after / before)
                if before else (0.0 if after == 0 else None)
            )
        updated["common_metric_revalidated"] = True
        updated["common_metric_input_definition"] = (
            "frozen source common-basis QASM; no Nam adapter retranspilation"
        )
        updated_rows.append(updated)
        audit_rows.append({
            "circuit_id": row["circuit_id"],
            "source_common_qasm_sha256": _sha256(source_path),
            "output_qasm_sha256": _sha256(output_path),
            "exact_equivalent": exact_equivalent,
            "old_common_input_gate_count": row["common_input_gate_count"],
            "new_common_input_gate_count": input_metrics["gate_count"],
        })
        run_result = output_path.parent / "result.json"
        raw_run_result = raw_root / f"{output_path.parent.name}_result.json"
        if run_result.exists() and not raw_run_result.exists():
            shutil.copyfile(run_result, raw_run_result)
        if run_result.exists():
            run_payload = json.loads(run_result.read_text(encoding="utf-8"))
            for key in input_metrics:
                run_payload[f"common_input_{key}"] = input_metrics[key]
                run_payload[f"common_output_{key}"] = output_metrics[key]
                run_payload[f"common_{key}_reduction_pct"] = updated[
                    f"common_{key}_reduction_pct"
                ]
            run_payload["common_metric_revalidated"] = True
            run_payload["common_metric_input_definition"] = updated[
                "common_metric_input_definition"
            ]
            _atomic_text(
                run_result,
                json.dumps(run_payload, indent=2, sort_keys=True) + "\n",
            )
    _atomic_text(result_path, pd.DataFrame(updated_rows).to_csv(index=False))
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata.update({
        "result_sha256": _sha256(result_path),
        "raw_pre_metric_revalidation_sha256": _sha256(raw_csv),
        "common_metric_revalidated": True,
        "common_metric_revalidation_script_sha256": _sha256(Path(__file__)),
        "resource_interpretation": (
            "BQSKit compiler workers=1 and BLAS threads=1; GUOQ rewrite and "
            "BQSKit resynthesis execute asynchronously, so the full pipeline "
            "was not restricted to one logical CPU"
        ),
        "formal_comparison_eligible": False,
    })
    _atomic_text(metadata_path, json.dumps(metadata, indent=2, sort_keys=True) + "\n")
    audit = {
        "recorded_at_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "status": "pass" if all(row["exact_equivalent"] for row in audit_rows) else "fail",
        "scope": "metric-only revalidation; GUOQ and BQSKit were not executed",
        "raw_result_sha256": _sha256(raw_csv),
        "revalidated_result_sha256": _sha256(result_path),
        "rows": audit_rows,
    }
    _atomic_text(
        PILOT_ROOT / "metric_revalidation.json",
        json.dumps(audit, indent=2, sort_keys=True) + "\n",
    )
    print(json.dumps(audit, sort_keys=True))


if __name__ == "__main__":
    main()
