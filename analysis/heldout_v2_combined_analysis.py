"""Confirmatory heldout-v2 and combined v1+v2 nested-family analysis."""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score, balanced_accuracy_score, f1_score, roc_auc_score

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from experiments.heldout_v2_execute import MANIFEST, PROTOCOL_PATH, ROOT, _verify_immutable_packet
from src.provenance import file_sha256

KEY = ["circuit_id", "trial", "seed", "input_circuit_sha256"]
TOOLS = ["custom", "qiskit", "cirq", "tket"]


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _mcc(y: np.ndarray, pred: np.ndarray) -> float:
    y, pred = np.asarray(y, np.int8), np.asarray(pred, np.int8)
    tp = int(np.sum((y == 1) & (pred == 1)))
    tn = int(np.sum((y == 0) & (pred == 0)))
    fp = int(np.sum((y == 0) & (pred == 1)))
    fn = int(np.sum((y == 1) & (pred == 0)))
    denominator = math.sqrt((tp + fp) * (tp + fn) * (tn + fp) * (tn + fn))
    return float((tp * tn - fp * fn) / denominator) if denominator else float("nan")


def _latest_tool_csv(tool: str) -> Path:
    files = sorted((ROOT / "results" / "raw").glob(f"{tool}_default_*.csv"))
    files = [path for path in files if "checkpoint" not in path.name]
    if len(files) != 1:
        raise RuntimeError(f"expected exactly one completed {tool} result, found {len(files)}")
    return files[0]


def _load_tool(tool: str, manifest_sha: str, expected: int) -> tuple[pd.DataFrame, Path]:
    path = _latest_tool_csv(tool)
    frame = pd.read_csv(path)
    required = KEY + ["benchmark_manifest_sha256", "valid_equivalent_output",
                      "common_gate_reduction_pct", "analysis_common_gate_reduction_pct_itt",
                      "compiler_status", "fidelity_source", "common_basis"]
    missing = sorted(set(required) - set(frame))
    if missing or len(frame) != expected or frame.duplicated(KEY).any():
        raise RuntimeError(f"{tool} result integrity failure; missing={missing}, rows={len(frame)}")
    if set(frame.benchmark_manifest_sha256.astype(str)) != {manifest_sha}:
        raise RuntimeError(f"{tool} manifest hash mismatch")
    if frame.input_circuit_sha256.nunique() != expected:
        raise RuntimeError(f"{tool} result is not unique by input hash")
    # The manifest SHA is a per-file gate above, not a per-tool analysis
    # variable.  Drop it before the four one-to-one merges to avoid ambiguous
    # duplicate columns while retaining the verified hash in the audit JSON.
    renamed = frame[[column for column in required if column != "benchmark_manifest_sha256"]].rename(columns={
        "valid_equivalent_output": f"{tool}_valid",
        "common_gate_reduction_pct": f"{tool}_common_reduction_pct",
        "analysis_common_gate_reduction_pct_itt": f"{tool}_reduction_itt",
        "compiler_status": f"{tool}_status",
        "fidelity_source": f"{tool}_fidelity_source",
        "common_basis": f"{tool}_common_basis",
    })
    renamed[f"{tool}_valid"] = renamed[f"{tool}_valid"].astype(str).str.lower().eq("true")
    return renamed, path


def _execution_contract_gate(manifest: pd.DataFrame, protocol: dict) -> tuple[dict, dict[str, Path]]:
    """Mechanically gate hashes, exact semantics, ITT, and formal metadata."""
    start_gate_path = ROOT / "execution" / "START_GATE.json"
    start_gate = json.loads(start_gate_path.read_text(encoding="utf-8"))
    source_paths = {
        "executor_source_sha256": PROJECT_ROOT / "experiments" / "heldout_v2_execute.py",
        "benchmark_runner_source_sha256": PROJECT_ROOT / "experiments" / "sota_benchmark.py",
        "exact_fidelity_source_sha256": PROJECT_ROOT / "src" / "circuits" / "real_benchmarks.py",
        "equivalence_contract_source_sha256": PROJECT_ROOT / "src" / "equivalence.py",
        "execution_protocol_sha256": PROTOCOL_PATH,
    }
    mismatches = {key: (start_gate.get(key), file_sha256(path)) for key, path in source_paths.items()
                  if start_gate.get(key) != file_sha256(path)}
    if mismatches:
        raise RuntimeError(f"fresh start-gate source mismatch: {mismatches}")
    if list(ROOT.glob("results/raw/*checkpoint*")):
        raise RuntimeError("canonical result directory contains a checkpoint")
    expected = int(protocol["expected_rows_per_tool"])
    expected_hashes = set(manifest.input_circuit_sha256.astype(str))
    threshold = float(protocol["fidelity_threshold"])
    tool_audits, paths = {}, {}
    for tool in TOOLS:
        path = _latest_tool_csv(tool)
        frame = pd.read_csv(path)
        metadata_path = ROOT / "results" / "metadata" / f"{tool}_default_metadata.json"
        metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        if len(frame) != expected or set(frame.input_circuit_sha256.astype(str)) != expected_hashes:
            raise RuntimeError(f"{tool}: row/hash coverage gate failed")
        if frame.input_circuit_sha256.duplicated().any() or frame.duplicated(KEY).any():
            raise RuntimeError(f"{tool}: duplicate independent input unit")
        if set(frame.common_basis.astype(str)) != {",".join(protocol["common_basis"])}:
            raise RuntimeError(f"{tool}: common-basis gate failed")
        if set(frame.fidelity_source.astype(str)) != {"exact"}:
            raise RuntimeError(f"{tool}: not every successful result used exact fidelity")
        fidelity = pd.to_numeric(frame.fidelity, errors="coerce").to_numpy(float)
        expected_pass = np.isfinite(fidelity) & (fidelity >= threshold)
        actual_pass = frame.equivalence_status.astype(str).eq("pass").to_numpy()
        valid = frame.valid_equivalent_output.astype(str).str.lower().eq("true").to_numpy()
        status_ok = frame.compiler_status.astype(str).eq("ok").to_numpy()
        if not np.array_equal(expected_pass, actual_pass):
            raise RuntimeError(f"{tool}: exact-fidelity/equivalence-status inconsistency")
        if not np.array_equal(valid, status_ok & expected_pass):
            raise RuntimeError(f"{tool}: valid-output/equivalence inconsistency")
        native = pd.to_numeric(frame.gate_reduction_pct, errors="raise").to_numpy(float)
        native_itt = pd.to_numeric(frame.analysis_gate_reduction_pct_itt, errors="raise").to_numpy(float)
        common = pd.to_numeric(frame.common_gate_reduction_pct, errors="raise").to_numpy(float)
        common_itt = pd.to_numeric(frame.analysis_common_gate_reduction_pct_itt, errors="raise").to_numpy(float)
        if not np.allclose(native_itt, np.where(valid, native, 0.0), atol=1e-12, rtol=0):
            raise RuntimeError(f"{tool}: native ITT gate failed")
        if not np.allclose(common_itt, np.where(valid, common, 0.0), atol=1e-12, rtol=0):
            raise RuntimeError(f"{tool}: common-basis ITT gate failed")
        equivalence_sha = file_sha256(source_paths["equivalence_contract_source_sha256"])
        exact_sha = file_sha256(source_paths["exact_fidelity_source_sha256"])
        equivalence = metadata.get("equivalence_verifier", {})
        source_hashes = metadata.get("source_hashes", {})
        if equivalence.get("layout_aware_qiskit_final_layout") is not True:
            raise RuntimeError(f"{tool}: layout-aware metadata gate failed")
        if equivalence.get("source_sha256") != equivalence_sha:
            raise RuntimeError(f"{tool}: equivalence source metadata mismatch")
        if equivalence.get("exact_fidelity_source_sha256") != exact_sha:
            raise RuntimeError(f"{tool}: exact fidelity source metadata mismatch")
        if source_hashes.get("src/equivalence.py") != equivalence_sha:
            raise RuntimeError(f"{tool}: source_hashes equivalence mismatch")
        if source_hashes.get("src/circuits/real_benchmarks.py") != exact_sha:
            raise RuntimeError(f"{tool}: source_hashes exact verifier mismatch")
        if metadata.get("fresh_run_provenance", {}).get("reason") != "layout_aware_equivalence_rerun":
            raise RuntimeError(f"{tool}: fresh-run provenance gate failed")
        if metadata.get("canonical_data_file") != path.name or int(metadata.get("n_rows", -1)) != expected:
            raise RuntimeError(f"{tool}: metadata/result binding failed")
        tool_audits[tool] = {
            "result_path": path.relative_to(PROJECT_ROOT).as_posix(),
            "result_sha256": file_sha256(path), "metadata_sha256": file_sha256(metadata_path),
            "rows": len(frame), "unique_input_hashes": frame.input_circuit_sha256.nunique(),
            "exact_fidelity_rows": int(np.isfinite(fidelity).sum()),
            "exact_equivalence_pass": int(actual_pass.sum()),
            "valid_equivalent_outputs": int(valid.sum()),
            "itt_rows_matching_contract": int(len(frame)),
            "minimum_exact_fidelity": float(np.min(fidelity)),
        }
        paths[tool] = path
    audit = {
        "status": "PASS_ALL_FRESH_EXECUTION_CONTRACT_GATES",
        "manifest_sha256": file_sha256(MANIFEST), "manifest_rows": len(manifest),
        "unique_input_hashes": manifest.input_circuit_sha256.nunique(),
        "start_gate_sha256": file_sha256(start_gate_path),
        "source_hashes": {key: file_sha256(path) for key, path in source_paths.items()},
        "equivalence_verifier": {
            "layout_aware_qiskit_final_layout": True,
            "source_sha256": file_sha256(PROJECT_ROOT / "src" / "equivalence.py"),
            "exact_fidelity_source_sha256": file_sha256(PROJECT_ROOT / "src" / "circuits" / "real_benchmarks.py"),
        },
        "fresh_run_provenance": {"reason": "layout_aware_equivalence_rerun"},
        "tool_gates": tool_audits,
    }
    return audit, paths


def _nested_bootstrap(data: pd.DataFrame, replicates: int, seed: int) -> np.ndarray:
    families = np.asarray(sorted(data.circuit_family.unique()), object)
    groups = {family: np.flatnonzero(data.circuit_family.to_numpy() == family) for family in families}
    y = data.observed_joint_external_headroom.to_numpy(np.int8)
    pred = data.predicted_joint_external_headroom.to_numpy(np.int8)
    rng = np.random.default_rng(seed)
    values = np.full(replicates, np.nan)
    for replicate in range(replicates):
        sampled = rng.choice(families, size=len(families), replace=True)
        take = np.concatenate([rng.choice(groups[family], size=len(groups[family]), replace=True)
                               for family in sampled])
        values[replicate] = _mcc(y[take], pred[take])
    return values


def analyze() -> Path:
    seal, protocol = _verify_immutable_packet()
    expected = int(protocol["expected_rows_per_tool"])
    manifest_sha = file_sha256(MANIFEST)
    manifest = pd.read_csv(MANIFEST)
    execution_audit, gated_result_paths = _execution_contract_gate(manifest, protocol)
    predictions_path = ROOT / "sealed_predictions" / "heldout_v2_predictions.csv"
    predictions = pd.read_csv(predictions_path)
    if len(predictions) != expected or predictions.duplicated(KEY).any():
        raise RuntimeError("sealed v2 prediction integrity failure")
    data = predictions.merge(manifest[KEY + ["circuit_family", "n_qubits"]], on=KEY,
                             validate="one_to_one", suffixes=("", "_manifest"))
    if not (data.circuit_family == data.circuit_family_manifest).all():
        raise RuntimeError("v2 prediction family mismatch")
    data = data.drop(columns="circuit_family_manifest")
    result_paths: dict[str, Path] = {}
    for tool in TOOLS:
        frame, path = _load_tool(tool, manifest_sha, expected)
        data = data.merge(frame, on=KEY, validate="one_to_one")
        result_paths[tool] = path
        if path != gated_result_paths[tool]:
            raise RuntimeError(f"{tool}: result changed after execution contract gate")
    if len(data) != expected or data.input_circuit_sha256.nunique() != expected:
        raise RuntimeError("v2 joined data is not one row per sealed input hash")
    threshold = 1.0
    data["observed_joint_external_headroom"] = (
        data.qiskit_valid & data.tket_valid
        & (data.qiskit_common_reduction_pct > threshold)
        & (data.tket_common_reduction_pct > threshold)
    ).astype(np.int8)
    data["heldout_version"] = "v2"

    v1_path = PROJECT_ROOT / "data" / "v10" / "prepaper" / "heldout" / "analysis" / "heldout_predictions_outcomes.csv"
    v1_metrics_path = v1_path.with_name("heldout_metrics.json")
    v1 = pd.read_csv(v1_path)
    v1_unique = v1.drop_duplicates("input_circuit_sha256", keep="first").copy()
    consistency = v1.groupby("input_circuit_sha256")[["observed_joint_external_headroom",
        "predicted_joint_external_headroom", "predicted_probability_joint_external_headroom"]].nunique(dropna=False)
    if (consistency > 1).any().any():
        raise RuntimeError("v1 duplicate input hash has inconsistent outcome or prediction")
    v1_unique["heldout_version"] = "v1"
    columns = ["heldout_version", "circuit_family", "input_circuit_sha256", "n_qubits",
               "observed_joint_external_headroom", "predicted_joint_external_headroom",
               "predicted_probability_joint_external_headroom"]
    combined = pd.concat([v1_unique[columns], data[columns]], ignore_index=True)
    if combined.input_circuit_sha256.duplicated().any():
        raise RuntimeError("v1+v2 contains a cross-packet duplicate input hash")
    if combined.circuit_family.nunique() != int(protocol["analysis"]["combined_outer_families"]):
        raise RuntimeError("combined analysis does not contain the frozen 16 outer families")

    y = combined.observed_joint_external_headroom.to_numpy(np.int8)
    pred = combined.predicted_joint_external_headroom.to_numpy(np.int8)
    probability = combined.predicted_probability_joint_external_headroom.to_numpy(float)
    replicates = int(protocol["analysis"]["bootstrap_replicates"])
    seed = int(protocol["analysis"]["bootstrap_seed"])
    bootstrap = _nested_bootstrap(combined, replicates, seed)
    finite = bootstrap[np.isfinite(bootstrap)]
    if len(finite) < int(0.95 * replicates):
        raise RuntimeError("too many non-identifiable combined MCC bootstrap replicates")
    ci_low, ci_high = np.percentile(finite, [2.5, 97.5])
    v1_metrics = json.loads(v1_metrics_path.read_text(encoding="utf-8"))
    old_low, old_high = float(v1_metrics["mcc_ci95_lower"]), float(v1_metrics["mcc_ci95_upper"])
    old_half, new_half = (old_high - old_low) / 2, (ci_high - ci_low) / 2

    family_rows = []
    for family, group in combined.groupby("circuit_family", sort=True):
        gy = group.observed_joint_external_headroom.to_numpy(np.int8)
        gp = group.predicted_joint_external_headroom.to_numpy(np.int8)
        family_rows.append({
            "heldout_version": group.heldout_version.iloc[0], "circuit_family": family,
            "n_unique_inputs": len(group), "observed_positive_rate": float(gy.mean()),
            "predicted_positive_rate": float(gp.mean()), "mcc": _mcc(gy, gp),
            "accuracy": float(accuracy_score(gy, gp)),
            "true_positive": int(np.sum((gy == 1) & (gp == 1))),
            "true_negative": int(np.sum((gy == 0) & (gp == 0))),
            "false_positive": int(np.sum((gy == 0) & (gp == 1))),
            "false_negative": int(np.sum((gy == 1) & (gp == 0))),
        })
    family = pd.DataFrame(family_rows)
    v2_tool_rows = []
    for tool in TOOLS:
        v2_tool_rows.append({
            "tool": tool, "n_rows": len(data),
            "valid_equivalent_rate": float(data[f"{tool}_valid"].mean()),
            "timeout_count": int(data[f"{tool}_status"].astype(str).eq("timeout").sum()),
            "error_count": int(data[f"{tool}_status"].astype(str).str.contains("error").sum()),
            "mean_common_reduction_pct_itt": float(data[f"{tool}_reduction_itt"].mean()),
            "result_sha256": file_sha256(result_paths[tool]),
        })
    metrics = {
        "primary_metric": "generator_clustered_nested_bootstrap_mcc",
        "instance_unit": "globally unique input_circuit_sha256",
        "outer_clusters": int(combined.circuit_family.nunique()),
        "n_unique_inputs": int(len(combined)), "v1_unique_inputs": int(len(v1_unique)),
        "v2_unique_inputs": int(len(data)), "mcc_point": _mcc(y, pred),
        "mcc_ci95_lower": float(ci_low), "mcc_ci95_upper": float(ci_high),
        "bootstrap_replicates": replicates, "bootstrap_finite_replicates": int(len(finite)),
        "bootstrap_seed": seed, "success_ci_lower_gt_zero": bool(ci_low > 0),
        "accuracy": float(accuracy_score(y, pred)),
        "balanced_accuracy": float(balanced_accuracy_score(y, pred)),
        "f1": float(f1_score(y, pred, zero_division=0)),
        "auroc": float(roc_auc_score(y, probability)) if len(np.unique(y)) == 2 else None,
        "v1_interval": {"lower": old_low, "upper": old_high, "half_width": old_half},
        "combined_interval": {"lower": float(ci_low), "upper": float(ci_high), "half_width": float(new_half)},
        "interval_half_width_fractional_change_vs_v1": float((new_half - old_half) / old_half),
        "classifier_threshold": 0.5, "headroom_threshold_pct": threshold,
        "model_refit": False, "feature_or_threshold_change": False,
        "seal_sha256": file_sha256(ROOT / "sealed_predictions" / "SEALED.json"),
        "seal_hashes_verified": True, "execution_protocol_sha256": file_sha256(PROTOCOL_PATH),
        "predictions_sha256": file_sha256(predictions_path),
        "v1_analysis_sha256": file_sha256(v1_path),
        "v1_metrics_sha256": file_sha256(v1_metrics_path),
        "source_sha256": file_sha256(Path(__file__).resolve()),
        "metric_dispositions": {
            "18.03": (
                "PASS: the sealed v1+v2 held-out program contains 16 independent generator "
                "families and 378 globally unique inputs, with no model refit or feature/threshold change"
            )
        },
        "claim_boundary": (
            "This expands outer generator mechanisms from eight to sixteen under the frozen "
            "classifier contract. It does not establish unseen-family universality; the finite "
            "family-clustered interval remains the supported inferential boundary."
        ),
    }
    output = ROOT / "analysis"
    verifier_comparison_path = output / "layout_verifier_before_after.json"
    if not verifier_comparison_path.exists():
        raise RuntimeError("layout-aware rerun is missing the frozen before/after comparison")
    merged_path = output / "heldout_v2_predictions_outcomes.csv"
    combined_path = output / "heldout_v1_v2_unique_inputs.csv"
    bootstrap_path = output / "combined_mcc_nested_bootstrap_10000.csv"
    family_path = output / "combined_generator_diagnostics.csv"
    tools_path = output / "heldout_v2_tool_diagnostics.csv"
    execution_audit_path = output / "execution_contract_audit.json"
    _atomic_text(merged_path, data.to_csv(index=False))
    _atomic_text(combined_path, combined.to_csv(index=False))
    _atomic_text(bootstrap_path, pd.DataFrame({"replicate": np.arange(replicates), "mcc": bootstrap}).to_csv(index=False))
    _atomic_text(family_path, family.to_csv(index=False))
    _atomic_text(tools_path, pd.DataFrame(v2_tool_rows).to_csv(index=False))
    _atomic_text(execution_audit_path, json.dumps(execution_audit, indent=2, sort_keys=True))
    metrics.update({"merged_v2_sha256": file_sha256(merged_path), "combined_data_sha256": file_sha256(combined_path),
                    "bootstrap_sha256": file_sha256(bootstrap_path), "family_diagnostics_sha256": file_sha256(family_path),
                    "tool_diagnostics_sha256": file_sha256(tools_path),
                    "layout_verifier_before_after_sha256": file_sha256(verifier_comparison_path)})
    metrics["execution_contract_audit_sha256"] = file_sha256(execution_audit_path)
    metrics_path = output / "combined_heldout_metrics.json"
    _atomic_text(metrics_path, json.dumps(metrics, indent=2, sort_keys=True))
    print(json.dumps(metrics, indent=2, sort_keys=True))
    return metrics_path


def main() -> None:
    argparse.ArgumentParser().parse_args()
    analyze()


if __name__ == "__main__":
    main()
