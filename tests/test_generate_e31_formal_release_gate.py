import csv
import json
from pathlib import Path

import pytest

from experiments.e31_formal_orchestrator import validate_release_gate
import scripts.generate_e31_formal_release_gate as gate_module
from scripts.generate_prepaper_release_manifest import (
    SOURCE_FILES as RELEASE_SOURCE_FILES,
    SUPERSEDED_EVIDENCE,
    _evidence_files,
)
from scripts.generate_e31_formal_release_gate import (
    DESIGN,
    GUOQ_ROOT,
    HELDOUT_ROOT,
    POWER,
    PROTOCOL,
    build_gate,
    generate_gate,
    sha256,
    validate_heldout,
    write_gate,
)


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _complete_heldout_fixture(root: Path) -> None:
    keys = [{"circuit_id": f"c{i}", "trial": str(i), "seed": str(1000 + i),
             "input_circuit_sha256": f"h{i:03d}"} for i in range(192)]
    manifest = root / "inputs/benchmark_manifest.csv"
    _write_csv(manifest, keys)
    manifest_sha = sha256(manifest)
    predictions = root / "sealed_predictions/heldout_v2_predictions.csv"
    _write_csv(predictions, keys)
    seal_path = root / "sealed_predictions/SEALED.json"
    _write_json(seal_path, {"status": "SEALED_BEFORE_HELDOUT_V2_OPTIMIZATION",
                            "n_rows": 192, "manifest_sha256": manifest_sha,
                            "predictions_sha256": sha256(predictions)})
    _write_json(root / "execution/START_GATE.json", {
        "status": "VERIFIED_BEFORE_FIRST_HELDOUT_V2_OPTIMIZER", "manifest_rows": 192,
        "seal_sha256": sha256(seal_path),
    })
    diagnostics = []
    contract_tools = {}
    for tool in gate_module.TOOLS:
        run_id = f"fresh-{tool}"
        rows = [{**key, "run_id": run_id, "benchmark_manifest_sha256": manifest_sha}
                for key in keys]
        for row in rows:
            row.update({"compiler_status": "ok", "valid_equivalent_output": "true",
                        "equivalence_status": "pass"})
        result = root / f"results/raw/{tool}_default_fresh.csv"
        _write_csv(result, rows)
        diagnostics.append({"tool": tool, "result_sha256": sha256(result)})
        metadata_path = root / f"results/metadata/{tool}_default_metadata.json"
        _write_json(metadata_path, {
            "canonical_data_file": result.name, "n_rows": 192, "run_id": run_id,
            "n_ok": 192, "n_valid_equivalent_outputs": 192,
            "benchmark_manifest_sha256": manifest_sha,
            "source_hashes": {
                "src/equivalence.py": sha256(gate_module.EQUIVALENCE_SOURCE),
                "src/circuits/real_benchmarks.py": sha256(gate_module.FIDELITY_SOURCE),
            },
            "equivalence_verifier": {
                "layout_aware_qiskit_final_layout": True,
                "source_sha256": sha256(gate_module.EQUIVALENCE_SOURCE),
                "exact_fidelity_source_sha256": sha256(gate_module.FIDELITY_SOURCE),
                "call_chain": "src/circuits/real_benchmarks.py::average_gate_fidelity",
            },
            "fresh_run_provenance": {"reason": "layout_aware_equivalence_rerun"},
        })
        contract_tools[tool] = {
            "result_sha256": sha256(result), "metadata_sha256": sha256(metadata_path),
            "rows": 192, "exact_equivalence_pass": 192, "valid_equivalent_outputs": 192,
        }
    analysis = root / "analysis"
    _write_csv(analysis / "heldout_v2_tool_diagnostics.csv", diagnostics)
    contract_path = analysis / "execution_contract_audit.json"
    _write_json(contract_path, {
        "status": "PASS_ALL_FRESH_EXECUTION_CONTRACT_GATES", "tool_gates": contract_tools,
        "manifest_sha256": manifest_sha,
        "start_gate_sha256": sha256(root / "execution/START_GATE.json"),
        "source_hashes": {
            "benchmark_runner_source_sha256": sha256(gate_module.PROJECT_ROOT / "experiments/sota_benchmark.py"),
            "equivalence_contract_source_sha256": sha256(gate_module.EQUIVALENCE_SOURCE),
            "exact_fidelity_source_sha256": sha256(gate_module.FIDELITY_SOURCE),
            "execution_protocol_sha256": sha256(gate_module.PROJECT_ROOT / "experiments/heldout_v2_execution_protocol.json"),
            "executor_source_sha256": sha256(gate_module.PROJECT_ROOT / "experiments/heldout_v2_execute.py"),
        },
    })
    files = {
        "merged_v2_sha256": "heldout_v2_predictions_outcomes.csv",
        "combined_data_sha256": "heldout_v1_v2_unique_inputs.csv",
        "bootstrap_sha256": "combined_mcc_nested_bootstrap_10000.csv",
        "family_diagnostics_sha256": "combined_generator_diagnostics.csv",
        "tool_diagnostics_sha256": "heldout_v2_tool_diagnostics.csv",
    }
    for name in list(files.values())[:-1]:
        (analysis / name).write_text("fixture\n", encoding="utf-8")
    metrics = {field: sha256(analysis / name) for field, name in files.items()}
    metrics.update({"seal_hashes_verified": True, "v2_unique_inputs": 192,
                    "bootstrap_replicates": 10000, "outer_clusters": 16,
                    "execution_contract_audit_sha256": sha256(contract_path)})
    _write_json(analysis / "combined_heldout_metrics.json", metrics)


def test_builder_output_is_validator_compatible(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(gate_module, "validate_guoq", lambda _: {"guoq": "hash"})
    monkeypatch.setattr(gate_module, "validate_heldout", lambda _: {"heldout": "hash"})
    payload = build_gate()
    output = tmp_path / "formal_release_gate.json"
    write_gate(payload, output)
    validated = validate_release_gate(output, {
        "protocol_sha256": sha256(PROTOCOL),
        "design_manifest_sha256": sha256(DESIGN),
        "power_sha256": sha256(POWER),
    })
    assert validated["guoq_status"] == "COMPLETE"
    assert validated["heldout_status"] == "COMPLETE"
    assert validated["guoq_evidence_sha256"]
    assert validated["heldout_evidence_sha256"]


def test_complete_fresh_layout_aware_fixture_passes(tmp_path: Path) -> None:
    _complete_heldout_fixture(tmp_path)
    assert validate_heldout(tmp_path)


def test_mixed_run_id_is_rejected(tmp_path: Path) -> None:
    _complete_heldout_fixture(tmp_path)
    path = tmp_path / "results/raw/qiskit_default_fresh.csv"
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    rows[0]["run_id"] = "old-batch"
    _write_csv(path, rows)
    with pytest.raises(ValueError, match="run_id"):
        validate_heldout(tmp_path)


def test_active_checkpoint_is_rejected_before_missing_evidence(tmp_path: Path) -> None:
    checkpoint = tmp_path / "results/raw/tket_default_checkpoint.csv"
    checkpoint.parent.mkdir(parents=True)
    checkpoint.write_text("partial\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unfinished checkpoints"):
        validate_heldout(tmp_path)


def test_failed_generation_removes_stale_gate(tmp_path: Path) -> None:
    output = tmp_path / "formal_release_gate.json"
    output.write_text('{"stale": true}', encoding="utf-8")
    incomplete = tmp_path / "incomplete-heldout"
    incomplete.mkdir()
    with pytest.raises(ValueError):
        generate_gate(output, guoq_root=GUOQ_ROOT, heldout_root=incomplete,
                      protocol=PROTOCOL, design=DESIGN, power=POWER)
    assert not output.exists()


def test_release_manifest_sources_are_unique_and_superseded_hardware_is_excluded() -> None:
    assert len(RELEASE_SOURCE_FILES) == len(set(RELEASE_SOURCE_FILES))
    included = {path.relative_to(HELDOUT_ROOT.parent).as_posix() for path in _evidence_files()}
    assert not {f"hardware_validation/{Path(name).name}" for name in SUPERSEDED_EVIDENCE} & included
