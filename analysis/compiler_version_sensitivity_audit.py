"""Execute and summarize a frozen compiler-version sensitivity panel.

Every dependency stack is installed in a temporary virtual environment.  The
project environment is never mutated.  The panel is descriptive and bounded;
it is not a replacement for a second full E31 run or a platform replication.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SOURCE_MANIFEST = ROOT / "data/v10/prepaper/sota/inputs/benchmark_manifest.csv"
WORKER = ROOT / "experiments/compiler_version_panel_worker.py"
DEFAULT_OUTPUT_DIR = ROOT / "data/v11/compiler_version_sensitivity"

ENVIRONMENTS = (
    {
        "id": "qiskit-2.4.1",
        "tool": "qiskit",
        "requirements": ("qiskit==2.4.1", "numpy==1.26.4", "scipy==1.13.1"),
    },
    {
        "id": "qiskit-2.3.1",
        "tool": "qiskit",
        "requirements": ("qiskit==2.3.1", "numpy==1.26.4", "scipy==1.13.1"),
    },
    {
        "id": "cirq-1.6.1",
        "tool": "cirq",
        "requirements": (
            "qiskit==2.4.1", "numpy==1.26.4", "scipy==1.13.1", "cirq-core==1.6.1", "ply==3.11"
        ),
    },
    {
        "id": "cirq-1.6.0",
        "tool": "cirq",
        "requirements": (
            "qiskit==2.4.1", "numpy==1.26.4", "scipy==1.13.1", "cirq-core==1.6.0", "ply==3.11"
        ),
    },
    {
        "id": "pytket-2.18.0",
        "tool": "tket",
        "requirements": (
            "qiskit==2.4.1", "numpy==1.26.4", "scipy==1.13.1", "pytket==2.18.0", "pytket-qiskit==0.77.0"
        ),
    },
    {
        "id": "pytket-2.17.0",
        "tool": "tket",
        "requirements": (
            "qiskit==2.4.1", "numpy==1.26.4", "scipy==1.13.1", "pytket==2.17.0", "pytket-qiskit==0.77.0"
        ),
    },
    {
        "id": "custom-current",
        "tool": "custom",
        "requirements": ("qiskit==2.4.1", "numpy==1.26.4", "scipy==1.13.1"),
    },
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_panel(output_dir: Path) -> Path:
    frame = pd.read_csv(SOURCE_MANIFEST)
    frame = frame.loc[
        frame["trial"].eq(0) & frame["seed"].eq(42)
    ].sort_values(["circuit_family", "n_qubits", "circuit_id"])
    panel = frame.groupby("circuit_family", sort=True, as_index=False).first()
    columns = [
        "circuit_family", "circuit_id", "n_qubits", "qasm_path", "qasm_sha256",
        "input_circuit_sha256", "trial", "seed",
    ]
    panel = panel[columns].sort_values("circuit_family").reset_index(drop=True)
    if len(panel) != 15 or panel["circuit_family"].nunique() != 15:
        raise ValueError("version panel must contain one smallest circuit from each of 15 families")
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / "frozen_panel.csv"
    panel.to_csv(output, index=False)
    return output


def _python_in(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def _run_environment(spec: dict[str, object], panel: Path, output_dir: Path, venv: Path) -> dict[str, object]:
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("uv is required for isolated version environments")
    subprocess.run(
        [uv, "venv", str(venv), "--python", sys.executable, "--clear"],
        cwd=ROOT, check=True,
    )
    python = _python_in(venv)
    subprocess.run(
        [uv, "pip", "install", "--python", str(python), *spec["requirements"]],
        cwd=ROOT, check=True,
    )
    run_dir = output_dir / "runs" / str(spec["id"])
    result_path = run_dir / "results.csv"
    subprocess.run(
        [
            str(python), str(WORKER), "--tool", str(spec["tool"]),
            "--panel", str(panel), "--output", str(result_path),
            "--environment-id", str(spec["id"]),
        ],
        cwd=ROOT, check=True,
    )
    freeze = subprocess.run(
        [uv, "pip", "freeze", "--python", str(python)],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout
    (run_dir / "resolved_requirements.txt").write_text(freeze, encoding="utf-8")
    return {
        "environment_id": spec["id"],
        "tool": spec["tool"],
        "requested_requirements": list(spec["requirements"]),
        "result_path": str(result_path.relative_to(ROOT)).replace("\\", "/"),
        "result_sha256": _sha256(result_path),
        "environment_sha256": _sha256(run_dir / "environment.json"),
        "resolved_requirements_sha256": _sha256(run_dir / "resolved_requirements.txt"),
    }


def summarize(output_dir: Path, panel: Path, executed: list[dict[str, object]]) -> dict[str, object]:
    frames = [pd.read_csv(ROOT / str(item["result_path"])) for item in executed]
    combined = pd.concat(frames, ignore_index=True)
    combined_path = output_dir / "all_version_results.csv"
    combined.to_csv(combined_path, index=False)
    structural_columns = [
        "status", "output_gate_count", "output_depth", "output_gate_counts_json",
        "output_instruction_sha256", "exact_equivalent",
    ]
    comparisons = []
    for tool in ("qiskit", "cirq", "tket"):
        tool_frame = combined.loc[combined["tool"].eq(tool)].copy()
        environment_ids = sorted(tool_frame["environment_id"].unique())
        if len(environment_ids) != 2:
            continue
        left = tool_frame.loc[tool_frame["environment_id"].eq(environment_ids[0])]
        right = tool_frame.loc[tool_frame["environment_id"].eq(environment_ids[1])]
        joined = left.merge(right, on=["circuit_family", "circuit_id", "qasm_sha256"],
                            suffixes=("_left", "_right"), validate="one_to_one")
        structure_match = pd.Series(True, index=joined.index)
        for column in structural_columns:
            a = joined[f"{column}_left"]
            b = joined[f"{column}_right"]
            structure_match &= a.eq(b) | (a.isna() & b.isna())
        comparisons.append(
            {
                "tool": tool,
                "left_environment": environment_ids[0],
                "right_environment": environment_ids[1],
                "rows": int(len(joined)),
                "structurally_identical_rows": int(structure_match.sum()),
                "all_rows_structurally_identical": bool(structure_match.all()),
                "left_success_rows": int(joined["status_left"].eq("success").sum()),
                "right_success_rows": int(joined["status_right"].eq("success").sum()),
                "left_exact_equivalent_rows": int(joined["exact_equivalent_left"].fillna(False).sum()),
                "right_exact_equivalent_rows": int(joined["exact_equivalent_right"].fillna(False).sum()),
                "left_runtime_median_seconds": float(joined["runtime_seconds_left"].median()),
                "right_runtime_median_seconds": float(joined["runtime_seconds_right"].median()),
                "runtime_role": "descriptive only; one execution per panel circuit",
            }
        )
    comparison_frame = pd.DataFrame(comparisons)
    comparison_path = output_dir / "per_tool_version_comparison.csv"
    comparison_frame.to_csv(comparison_path, index=False)
    all_tools_two_versions = set(comparison_frame["tool"]) == {"qiskit", "cirq", "tket"}
    all_success = bool(combined["status"].eq("success").all())
    all_equivalent = bool(combined["exact_equivalent"].fillna(False).all())
    all_structurally_identical = bool(
        len(comparison_frame) == 3
        and comparison_frame["all_rows_structurally_identical"].all()
    )
    panel_frame = pd.read_csv(panel)
    audit = {
        "schema_version": "1.0.0",
        "status": "PASS_BOUNDED_COMPILER_VERSION_PANEL" if (
            all_tools_two_versions and all_success and all_equivalent
            and all_structurally_identical
        ) else "PARTIAL_COMPILER_VERSION_PANEL",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "panel": {
            "rows": int(len(panel_frame)),
            "families": int(panel_frame["circuit_family"].nunique()),
            "qubit_range": [
                int(panel_frame["n_qubits"].min()),
                int(panel_frame["n_qubits"].max()),
            ],
            "selection": "smallest-n circuit per family from the frozen shared-520 SOTA manifest, trial 0 seed 42",
            "path": str(panel.relative_to(ROOT)).replace("\\", "/"),
            "sha256": _sha256(panel),
            "source_manifest_sha256": _sha256(SOURCE_MANIFEST),
        },
        "isolation": "each environment was created in an independent temporary uv virtual environment; the project environment was not modified",
        "executed_environments": executed,
        "tool_version_comparisons": comparisons,
        "all_tools_have_two_versions": all_tools_two_versions,
        "all_runs_successful": all_success,
        "all_outputs_exact_equivalent": all_equivalent,
        "equivalence_method": (
            "numerical full-unitary trace overlap, invariant to global phase, "
            "threshold 1-1e-10; optimized QASM artifacts are retained for independent replay"
        ),
        "all_version_pairs_structurally_identical": all_structurally_identical,
        "runtime_boundary": "Runtime is reported separately and descriptively from a single execution per circuit; no performance-equivalence claim is made.",
        "claim_boundary": (
            "This is a 15-circuit, 15-family, 4-5-qubit Windows panel. It is direct version-sensitivity evidence for the exact versions listed; custom-current has only one version. It is not a full benchmark rerun, not E31 replication, not unseen-family evidence, and not Windows/Linux or cross-CPU robustness."
        ),
        "metric_dispositions": {
            "8.28": "PARTIAL: Qiskit, Cirq, and tket each have a two-version frozen 15-family structural panel, but the panel is not the full formal benchmark and external Quasar/Quartz versions are not varied",
            "18.10": "PARTIAL: three compiler stacks have two-version evidence on one Windows host, but no Linux or different-CPU execution exists",
        },
        "artifacts": {
            "all_version_results.csv": {"rows": int(len(combined)), "sha256": _sha256(combined_path)},
            "per_tool_version_comparison.csv": {"rows": int(len(comparison_frame)), "sha256": _sha256(comparison_path)},
        },
        "source_bindings": {
            "analysis/compiler_version_sensitivity_audit.py": _sha256(Path(__file__)),
            "experiments/compiler_version_panel_worker.py": _sha256(WORKER),
        },
    }
    audit_path = output_dir / "compiler_version_sensitivity_audit.json"
    audit_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-execution", action="store_true")
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    panel = build_panel(output_dir)
    if args.skip_execution:
        executed = []
        for spec in ENVIRONMENTS:
            run_dir = output_dir / "runs" / str(spec["id"])
            result_path = run_dir / "results.csv"
            if not result_path.exists():
                raise FileNotFoundError(result_path)
            executed.append(
                {
                    "environment_id": spec["id"], "tool": spec["tool"],
                    "requested_requirements": list(spec["requirements"]),
                    "result_path": str(result_path.relative_to(ROOT)).replace("\\", "/"),
                    "result_sha256": _sha256(result_path),
                    "environment_sha256": _sha256(run_dir / "environment.json"),
                    "resolved_requirements_sha256": _sha256(run_dir / "resolved_requirements.txt"),
                }
            )
    else:
        executed = []
        with tempfile.TemporaryDirectory(prefix="qresearch-version-matrix-") as temporary:
            temporary_root = Path(temporary)
            for spec in ENVIRONMENTS:
                executed.append(
                    _run_environment(spec, panel, output_dir, temporary_root / str(spec["id"]))
                )
    audit = summarize(output_dir, panel, executed)
    print(json.dumps({key: audit[key] for key in (
        "status", "all_tools_have_two_versions", "all_runs_successful",
        "all_outputs_exact_equivalent", "tool_version_comparisons",
    )}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
