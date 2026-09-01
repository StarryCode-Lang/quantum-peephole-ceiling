"""Confirmatory RQ1 analysis of legal listing/representation sensitivity."""

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
    _nested_bootstrap,
    _normal_approx_mde,
    _rank_biserial,
)
from src.provenance import file_sha256

REPLICATES = 10000
SEED = 20260809
EQUIVALENCE_MARGIN_PP = 1.0


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    tmp.replace(path)


def _paired(frame: pd.DataFrame, keys: list[str], cluster: str) -> pd.DataFrame:
    if frame.duplicated(keys + ["listing_model"]).any():
        raise RuntimeError("duplicate listing pair key")
    left_columns = keys + ([] if cluster in keys else [cluster]) + ["reduction_itt"]
    lbl = frame[frame.listing_model == "LBL"][left_columns]
    wcl = frame[frame.listing_model == "WCL"][keys + ["reduction_itt"]]
    paired = lbl.merge(wcl, on=keys, how="inner", validate="one_to_one",
                       suffixes=("_lbl", "_wcl"))
    if len(paired) * 2 != len(frame):
        raise RuntimeError("unmatched LBL/WCL observations")
    if f"{cluster}_lbl" in paired:
        paired[cluster] = paired[f"{cluster}_lbl"]
    paired["difference"] = 100.0 * (
        paired.reduction_itt_wcl - paired.reduction_itt_lbl)
    return paired


def _summary(paired: pd.DataFrame, cluster: str, seed: int) -> tuple[dict, np.ndarray]:
    bootstrap_input = paired[[cluster, "difference"]].rename(
        columns={cluster: "circuit_family", "difference": "value"})
    boot = _nested_bootstrap(bootstrap_input, "value", REPLICATES, seed)
    differences = paired.difference.to_numpy(float)
    if np.allclose(differences, 0):
        wilcoxon_p = 1.0
    else:
        wilcoxon_p = float(stats.wilcoxon(
            differences, alternative="two-sided", zero_method="pratt").pvalue)
    ci95 = np.percentile(boot, [2.5, 97.5])
    ci90 = np.percentile(boot, [5.0, 95.0])
    return {
        "n_pairs": len(paired), "n_outer_clusters": paired[cluster].nunique(),
        "wcl_minus_lbl_mean_pp": float(differences.mean()),
        "wcl_minus_lbl_median_pp": float(np.median(differences)),
        "ci95_lower_pp": float(ci95[0]), "ci95_upper_pp": float(ci95[1]),
        "equivalence_ci90_lower_pp": float(ci90[0]),
        "equivalence_ci90_upper_pp": float(ci90[1]),
        "equivalent_within_plusminus_1pp": bool(
            ci90[0] > -EQUIVALENCE_MARGIN_PP and ci90[1] < EQUIVALENCE_MARGIN_PP),
        "hodges_lehmann_pp": _hodges_lehmann(differences),
        "rank_biserial": _rank_biserial(differences),
        "wilcoxon_p_two_sided": wilcoxon_p,
        "cluster_sign_permutation_p": _cluster_permutation(
            bootstrap_input.rename(columns={"value": "difference"}),
            REPLICATES, seed + 1),
        "cluster_aware_mde_80pct_power_pp": _normal_approx_mde(boot),
        "bootstrap_replicates": REPLICATES, "bootstrap_seed": seed,
        "outer_cluster": cluster, "inner_unit": "circuit_instance",
    }, boot


def _prepare_extended(path: Path) -> tuple[pd.DataFrame, list[str]]:
    frame = pd.read_csv(path.resolve())
    if len(frame) != 960:
        raise RuntimeError("extended E19 must contain the frozen 960 rows")
    if set(frame.listing_model) != {"LBL", "WCL"}:
        raise RuntimeError("extended E19 listing levels differ from LBL/WCL")
    fidelity = pd.to_numeric(frame.fidelity, errors="coerce")
    frame["valid"] = fidelity >= 0.9999999999
    frame["reduction_itt"] = np.where(
        frame.valid, pd.to_numeric(frame.reduction, errors="coerce"), 0.0)
    if not np.isfinite(frame.reduction_itt.to_numpy(float)).all():
        raise RuntimeError("extended E19 contains non-finite ITT reduction")
    keys = ["circuit_family", "n_qubits", "param_n", "depth", "trial", "seed"]
    return frame, keys


def _prepare_replication(path: Path) -> tuple[pd.DataFrame, list[str]]:
    frame = pd.read_csv(path.resolve())
    if len(frame) != 10000:
        raise RuntimeError("random-depth E19 must contain the frozen 10000 rows")
    if set(frame.listing_model) != {"LBL", "WCL"}:
        raise RuntimeError("random-depth E19 listing levels differ from LBL/WCL")
    fidelity = pd.to_numeric(frame.fidelity, errors="coerce")
    frame["valid"] = fidelity >= 0.9999999999
    frame["reduction_itt"] = np.where(
        frame.valid, pd.to_numeric(frame.reduction, errors="coerce"), 0.0)
    if not np.isfinite(frame.reduction_itt.to_numpy(float)).all():
        raise RuntimeError("random-depth E19 contains non-finite ITT reduction")
    frame["depth_cluster"] = "depth_" + frame.depth.astype(str)
    keys = ["n_qubits", "depth", "trial", "seed"]
    return frame, keys


def analyze(extended_path: Path, replication_path: Path,
            pilot_path: Path | None, output_dir: Path) -> Path:
    extended, extended_keys = _prepare_extended(extended_path)
    paired = _paired(extended, extended_keys, "circuit_family")
    overall, overall_boot = _summary(paired, "circuit_family", SEED)
    overall["evidence"] = "multi-family canonical E19 extended"

    replication, replication_keys = _prepare_replication(replication_path)
    replication_paired = _paired(replication, replication_keys, "depth_cluster")
    replication_summary, replication_boot = _summary(
        replication_paired, "depth_cluster", SEED + 10)
    replication_summary["evidence"] = "independent 5000-pair random-depth replication"
    replication_summary["cluster_caveat"] = (
        "single generator family: depth strata are a sensitivity resampling unit, "
        "not independent generator-family clusters"
    )

    family_rows = []
    for family_index, (family, group) in enumerate(paired.groupby("circuit_family", sort=True)):
        values = group.difference.to_numpy(float)
        rng = np.random.default_rng(SEED + 100 + family_index)
        boot = np.asarray([
            np.mean(rng.choice(values, size=len(values), replace=True))
            for _ in range(REPLICATES)
        ])
        p_value = (1.0 if np.allclose(values, 0) else float(stats.wilcoxon(
            values, alternative="two-sided", zero_method="pratt").pvalue))
        family_rows.append({
            "circuit_family": family, "n_pairs": len(values),
            "mean_difference_pp": float(values.mean()),
            "median_difference_pp": float(np.median(values)),
            "ci95_lower_pp": float(np.percentile(boot, 2.5)),
            "ci95_upper_pp": float(np.percentile(boot, 97.5)),
            "rank_biserial": _rank_biserial(values),
            "wilcoxon_p_two_sided": p_value,
        })
    family_frame = pd.DataFrame(family_rows)
    family_frame["wilcoxon_p_holm"] = _holm(
        family_frame.wilcoxon_p_two_sided.tolist())

    lofo_rows = []
    for family in sorted(paired.circuit_family.unique()):
        subset = paired[paired.circuit_family != family]
        lofo_rows.append({
            "left_out_family": family, "n_pairs": len(subset),
            "mean_difference_pp": float(subset.difference.mean()),
            "median_difference_pp": float(subset.difference.median()),
        })
    lofo = pd.DataFrame(lofo_rows)

    model_record: dict[str, object] = {}
    try:
        import statsmodels.formula.api as smf
        model_frame = extended.copy()
        model_frame["listing_wcl"] = (model_frame.listing_model == "WCL").astype(int)
        model_frame["instance_key"] = model_frame[extended_keys].astype(str).agg("|".join, axis=1)
        model = smf.mixedlm(
            "reduction_itt ~ listing_wcl", model_frame,
            groups=model_frame["circuit_family"], re_formula="1",
            vc_formula={
                "instance": "0+C(instance_key)",
                "seed": "0+C(seed)",
            },
        ).fit(reml=True, method="lbfgs", maxiter=1000)
        model_record = {
            "converged": bool(model.converged),
            "formula": "reduction_itt ~ listing_wcl",
            "random_intercepts": ["circuit_family", "instance", "seed"],
            "parameters": {str(k): float(v) for k, v in model.params.items()},
        }
        if not model.converged:
            model_record["fallback"] = (
                "family-outer instance-inner bootstrap plus cluster sign permutation"
            )
        _atomic_text(output_dir / "rq1_mixed_model.txt", model.summary().as_text())
    except Exception as exc:
        model_record = {
            "converged": False, "error": f"{type(exc).__name__}: {exc}",
            "fallback": "family-outer instance-inner bootstrap plus cluster sign permutation",
        }

    pilot_record: dict[str, object] | None = None
    if pilot_path is not None:
        pilot = pd.read_csv(pilot_path.resolve())
        pilot_record = {
            "status": "supporting_noncanonical_pilot_only",
            "n_rows": len(pilot), "n_source_circuits": pilot.circuit_id.nunique(),
            "listings": sorted(pilot.listing_model.unique().tolist()),
            "phases": sorted(pilot.phase.unique().tolist()),
            "input_sha256": file_sha256(pilot_path.resolve()),
            "interpretation": "may probe listing-by-phase interaction but cannot confirm it",
        }

    bootstrap_source = pd.DataFrame({
        "replicate": np.arange(REPLICATES),
        "multifamily_wcl_minus_lbl_pp": overall_boot,
        "random_depth_replication_wcl_minus_lbl_pp": replication_boot,
    })
    output_dir.mkdir(parents=True, exist_ok=True)
    _atomic_text(output_dir / "family_contrasts.csv", family_frame.to_csv(index=False))
    _atomic_text(output_dir / "leave_one_family_out.csv", lofo.to_csv(index=False))
    _atomic_text(output_dir / "bootstrap_source_10000.csv", bootstrap_source.to_csv(index=False))
    result = {
        "status": "complete", "equivalence_margin_pp": EQUIVALENCE_MARGIN_PP,
        "multifamily_primary": overall,
        "random_depth_replication": replication_summary,
        "mixed_model": model_record,
        "pilot": pilot_record,
        "multiple_testing": "Holm across family-specific listing contrasts",
        "estimand": "instance-weighted mean; cluster sign flips use cluster sums over fixed total n",
        "power_analysis": {
            "type": "normal approximation using cluster-bootstrap standard error",
            "alpha_two_sided": 0.05, "target_power": 0.80,
            "caveat": "random-depth replication has one generator family and is supporting evidence",
        },
        "input_sha256": {
            "extended": file_sha256(extended_path.resolve()),
            "replication": file_sha256(replication_path.resolve()),
        },
        "output_sha256": {
            "family_contrasts": file_sha256(output_dir / "family_contrasts.csv"),
            "leave_one_family_out": file_sha256(output_dir / "leave_one_family_out.csv"),
            "bootstrap_source": file_sha256(output_dir / "bootstrap_source_10000.csv"),
        },
        "source_sha256": file_sha256(Path(__file__).resolve()),
        "protocol_sha256": file_sha256(PROJECT_ROOT / "experiments" / "prepaper_protocol.json"),
    }
    result_path = output_dir / "rq1_results.json"
    serialized = json.dumps(result, indent=2, sort_keys=True)
    _atomic_text(result_path, serialized)
    _atomic_text(output_dir / "audit.json", serialized)
    print(json.dumps({"multifamily": overall, "replication": replication_summary},
                     indent=2, sort_keys=True))
    return result_path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--extended", type=Path, required=True)
    parser.add_argument("--replication", type=Path, required=True)
    parser.add_argument("--pilot", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    analyze(args.extended, args.replication, args.pilot,
            args.output_dir.resolve())


if __name__ == "__main__":
    main()
