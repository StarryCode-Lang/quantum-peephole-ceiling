"""Audit and summarize the two independent external optimizer baselines."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from analysis.prepaper_rq3_tool_comparison import (
    _cluster_permutation,
    _hodges_lehmann,
    _holm,
    _rank_biserial,
)

BOOTSTRAP_REPLICATES = 10_000
BOOTSTRAP_SEED = 20260810
KEY = ["circuit_id", "trial", "seed"]


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def _sha256(path: Path) -> str:
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _as_bool(series: pd.Series) -> pd.Series:
    return series.astype(str).str.strip().str.lower().eq("true")


def _nested_bootstrap(frame: pd.DataFrame, column: str, seed: int) -> np.ndarray:
    if "input_circuit_sha256" in frame.columns:
        frame = (frame.groupby(
            ["circuit_family", "input_circuit_sha256"], as_index=False
        )[column].mean())
    families = np.asarray(sorted(frame.circuit_family.unique()), dtype=object)
    groups = {
        family: frame.loc[frame.circuit_family == family, column].to_numpy(float)
        for family in families
    }
    rng = np.random.default_rng(seed)
    values = np.empty(BOOTSTRAP_REPLICATES, dtype=float)
    for index in range(BOOTSTRAP_REPLICATES):
        sampled_families = rng.choice(families, len(families), replace=True)
        samples = [
            rng.choice(groups[family], len(groups[family]), replace=True)
            for family in sampled_families
        ]
        values[index] = float(np.mean(np.concatenate(samples)))
    return values


def _cluster_sign_permutation(frame: pd.DataFrame, seed: int) -> float:
    return _cluster_permutation(frame, BOOTSTRAP_REPLICATES, seed)


def _load_external(path: Path, method: str, expected: pd.DataFrame,
                   expected_manifest_sha256: str) -> pd.DataFrame:
    frame = pd.read_csv(path.resolve())
    if len(frame) != 520 or frame.duplicated(KEY).any():
        raise RuntimeError(f"{method}: expected 520 unique paired rows")
    input_hash = ("input_circuit_sha256" if method == "quasar"
                  else "source_common_input_circuit_sha256")
    manifest_hash = ("source_manifest_sha256" if method == "quasar"
                     else "source_common_manifest_sha256")
    reduction = ("analysis_gate_reduction_pct_itt" if method == "quasar"
                 else "analysis_common_gate_reduction_pct_itt")
    required = set(KEY + ["circuit_family", input_hash, manifest_hash,
                          "status", "fidelity_source",
                          "exact_equivalent", "valid_equivalent_output",
                          "exact_average_gate_fidelity", "fidelity_threshold", reduction,
                          "output_qasm_path", "output_qasm_sha256"])
    if not required.issubset(frame.columns):
        raise RuntimeError(f"{method}: missing columns {sorted(required - set(frame.columns))}")
    observed = frame[KEY + ["circuit_family", input_hash]].rename(
        columns={input_hash: "input_circuit_sha256"})
    check = expected.merge(observed, on=KEY, how="outer", suffixes=("_expected", "_observed"),
                           indicator=True, validate="one_to_one")
    mismatch = (check._merge.ne("both")
                | check.circuit_family_expected.ne(check.circuit_family_observed)
                | check.input_circuit_sha256_expected.ne(check.input_circuit_sha256_observed))
    if mismatch.any():
        raise RuntimeError(f"{method}: manifest key, family, or input hash mismatch")
    if not frame[manifest_hash].astype(str).eq(expected_manifest_sha256).all():
        raise RuntimeError(f"{method}: row-level source-manifest hash mismatch")
    frame["method"] = method
    frame["input_circuit_sha256"] = frame[input_hash].astype(str)
    frame["valid"] = _as_bool(frame.valid_equivalent_output).astype(int)
    exact_equivalent = _as_bool(frame.exact_equivalent).astype(int)
    if not frame.valid.equals(exact_equivalent):
        raise RuntimeError(f"{method}: validity differs from exact-equivalence flag")
    frame["gate_reduction_itt"] = pd.to_numeric(frame[reduction], errors="raise")
    if not np.isfinite(frame.gate_reduction_itt.to_numpy(float)).all():
        raise RuntimeError(f"{method}: non-finite ITT outcome")
    exact = frame.fidelity_source.astype(str).eq("exact")
    exact_fidelity = pd.to_numeric(frame.exact_average_gate_fidelity, errors="coerce")
    threshold = pd.to_numeric(frame.fidelity_threshold, errors="raise")
    threshold_valid = (
        frame.status.astype(str).eq("ok")
        & np.isfinite(exact_fidelity)
        & exact_fidelity.ge(threshold)
    ).astype(int)
    if not frame.valid.equals(threshold_valid):
        raise RuntimeError(f"{method}: validity differs from frozen exact-fidelity rule")
    if (frame.valid.eq(1) & ~exact).any():
        raise RuntimeError(f"{method}: valid output without exact equivalence evidence")
    if (frame.valid.eq(0) & ~np.isclose(frame.gate_reduction_itt, 0.0)).any():
        raise RuntimeError(f"{method}: invalid output has nonzero ITT outcome")
    output_paths = frame.output_qasm_path.fillna("").astype(str)
    for row in frame.loc[output_paths.ne("")].itertuples(index=False):
        output_path = PROJECT_ROOT / str(row.output_qasm_path)
        if not output_path.is_file() or _sha256(output_path) != str(row.output_qasm_sha256):
            raise RuntimeError(f"{method}: output file/hash mismatch for {row.circuit_id}")
    if output_paths.loc[frame.valid.eq(1)].eq("").any():
        raise RuntimeError(f"{method}: valid result lacks an immutable output artifact")
    return frame


def analyze(manifest_path: Path, quasar_path: Path, quartz_path: Path,
            output_dir: Path) -> None:
    manifest_path = manifest_path.resolve()
    manifest = pd.read_csv(manifest_path)
    expected_columns = KEY + ["circuit_family", "input_circuit_sha256",
                              "original_manifest_sha256"]
    if not set(expected_columns).issubset(manifest.columns):
        raise RuntimeError("external manifest lacks original-manifest lineage")
    expected = manifest[expected_columns].copy()
    if len(expected) != 520 or expected.duplicated(KEY).any():
        raise RuntimeError("external common-basis manifest integrity failure")
    manifest_sha256 = _sha256(manifest_path)
    upstream_hashes = expected.original_manifest_sha256.astype(str).unique()
    if len(upstream_hashes) != 1:
        raise RuntimeError("external manifest has multiple upstream source manifests")
    frames = {
        "quasar": _load_external(
            quasar_path, "quasar", expected, str(upstream_hashes[0])),
        "quartz": _load_external(quartz_path, "quartz", expected, manifest_sha256),
    }
    summaries: list[dict] = []
    bootstrap_rows: list[dict] = []
    for index, (method, frame) in enumerate(frames.items()):
        unique_frame = (frame.groupby(
            ["circuit_family", "input_circuit_sha256"], as_index=False
        ).agg(valid=("valid", "mean"),
              gate_reduction_itt=("gate_reduction_itt", "mean")))
        valid = _nested_bootstrap(frame, "valid", BOOTSTRAP_SEED + index)
        reduction = _nested_bootstrap(frame, "gate_reduction_itt", BOOTSTRAP_SEED + 10 + index)
        summaries.append({
            "method": method, "n_execution_rows": len(frame),
            "n_unique_inputs": len(unique_frame),
            "valid_equivalent_execution_rows": int(frame.valid.sum()),
            "valid_rate": float(unique_frame.valid.mean()),
            "valid_ci95_lower": float(np.percentile(valid, 2.5)),
            "valid_ci95_upper": float(np.percentile(valid, 97.5)),
            "gate_reduction_itt_mean": float(unique_frame.gate_reduction_itt.mean()),
            "gate_reduction_ci95_lower": float(np.percentile(reduction, 2.5)),
            "gate_reduction_ci95_upper": float(np.percentile(reduction, 97.5)),
            "timeout_n": int(frame.status.astype(str).str.contains("timeout").sum()),
            "error_n": int(frame.status.astype(str).eq("error").sum()),
        })
        bootstrap_rows.extend({
            "method": method, "replicate": replicate,
            "valid_rate": valid_value, "gate_reduction_itt_mean": reduction_value,
        } for replicate, (valid_value, reduction_value) in enumerate(zip(valid, reduction)))

    paired = frames["quasar"][KEY + ["circuit_family", "input_circuit_sha256", "valid", "gate_reduction_itt"]].merge(
        frames["quartz"][KEY + ["valid", "gate_reduction_itt"]], on=KEY,
        suffixes=("_quasar", "_quartz"), validate="one_to_one")
    contrast_rows = []
    for endpoint in ("valid", "gate_reduction_itt"):
        differences = paired[f"{endpoint}_quasar"] - paired[f"{endpoint}_quartz"]
        work = paired[["circuit_family", "input_circuit_sha256"]].copy()
        work["difference"] = differences
        work = (work.groupby(
            ["circuit_family", "input_circuit_sha256"], as_index=False
        ).difference.mean())
        differences = work.difference.to_numpy(float)
        bootstrap = _nested_bootstrap(work, "difference", BOOTSTRAP_SEED + 20 + len(contrast_rows))
        record = {
            "endpoint": endpoint, "quasar_minus_quartz": float(differences.mean()),
            "ci95_lower": float(np.percentile(bootstrap, 2.5)),
            "ci95_upper": float(np.percentile(bootstrap, 97.5)),
            "cluster_sign_permutation_p": _cluster_sign_permutation(
                work, BOOTSTRAP_SEED + 30 + len(contrast_rows)),
        }
        if endpoint == "valid":
            discordant = differences != 0
            quasar_only = differences > 0
            record.update({
                "discordant_pairs": int(np.sum(discordant)),
                "paired_test": "McNemar exact binomial",
                "paired_test_p": float(stats.binomtest(
                    int(np.sum(discordant & quasar_only)), int(np.sum(discordant)), 0.5
                ).pvalue) if np.any(discordant) else 1.0,
            })
        else:
            values = np.asarray(differences, dtype=float)
            record.update({
                "hodges_lehmann": _hodges_lehmann(values),
                "rank_biserial": _rank_biserial(values),
                "paired_test": "Wilcoxon signed-rank Pratt",
                "paired_test_p": (float(stats.wilcoxon(
                    values, alternative="two-sided", zero_method="pratt").pvalue)
                    if not np.allclose(values, 0.0) else 1.0),
            })
        contrast_rows.append(record)

    contrast_frame = pd.DataFrame(contrast_rows)
    contrast_frame["cluster_sign_permutation_p_holm"] = _holm(
        contrast_frame.cluster_sign_permutation_p.tolist())
    contrast_frame["paired_test_p_holm"] = _holm(
        contrast_frame.paired_test_p.tolist())

    long = pd.concat(frames.values(), ignore_index=True)
    family = (long.groupby(["circuit_family", "method"], as_index=False)
              .agg(n=("valid", "size"), valid_rate=("valid", "mean"),
                   gate_reduction_itt_mean=("gate_reduction_itt", "mean")))
    outputs = {
        "external_summary.csv": pd.DataFrame(summaries),
        "external_pairwise.csv": contrast_frame,
        "external_family_diagnostics.csv": family,
        "external_bootstrap_source_10000.csv": pd.DataFrame(bootstrap_rows),
    }
    for name, frame in outputs.items():
        _atomic_text(output_dir / name, frame.to_csv(index=False))
    audit = {
        "status": "complete", "n_per_method": 520, "methods": list(frames),
        "outer_cluster": "circuit_family",
        "inner_unit": "unique input_circuit_sha256 within family",
        "estimand": "unique-input-weighted mean; repeated executions remain operational rows",
        "bootstrap_replicates": BOOTSTRAP_REPLICATES, "bootstrap_seed": BOOTSTRAP_SEED,
        "multiple_testing": "Holm across validity and gate-reduction endpoints for the one external-method pair",
        "manifest_sha256": manifest_sha256,
        "upstream_source_manifest_sha256": str(upstream_hashes[0]),
        "input_sha256": {"quasar": _sha256(quasar_path.resolve()),
                         "quartz": _sha256(quartz_path.resolve())},
        "output_sha256": {name: _sha256(output_dir / name) for name in outputs},
        "source_sha256": _sha256(Path(__file__).resolve()),
    }
    _atomic_text(output_dir / "audit.json", json.dumps(audit, indent=2, sort_keys=True))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--quasar", type=Path, required=True)
    parser.add_argument("--quartz", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.manifest, args.quasar, args.quartz, args.output_dir.resolve())


if __name__ == "__main__":
    main()
