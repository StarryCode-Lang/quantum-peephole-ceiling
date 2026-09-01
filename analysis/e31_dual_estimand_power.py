#!/usr/bin/env python3
"""Prospective power and Type-I simulation for the two E31 estimands.

This script deliberately separates inference conditional on the frozen 391-input
benchmark from inference to a super-population of previously unseen families.
It never changes the frozen 1 percentage-point MCID.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import nct, norm, t


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "data/v11/e31_factorial_pareto/design_manifest.csv"
DEFAULT_PILOT = ROOT / "data/v11/e31_listing_phase2b/e31_listing_phase2b_pilot.csv"
DEFAULT_OUTPUT = ROOT / "data/v11/e31_factorial_pareto/dual_estimand_power.json"
DEFAULT_PROTOCOL = ROOT / "experiments/e31_factorial_pareto_protocol.json"

MCID_PP = 1.0
ALPHA = 0.05
TARGET_POWER = 0.80
GRID_REPEATS = 12  # 3 windows x 4 budgets in the frozen primary interaction.


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _family_sizes(manifest_path: Path) -> pd.Series:
    manifest = pd.read_csv(manifest_path, usecols=["input_circuit_sha256", "circuit_family"])
    unique = manifest.drop_duplicates("input_circuit_sha256")
    sizes = unique.groupby("circuit_family", sort=True).size()
    if int(sizes.sum()) != 391:
        raise ValueError(f"Expected 391 unique inputs, observed {int(sizes.sum())}")
    return sizes


def _pilot_variance_components(pilot_path: Path) -> dict[str, float | int]:
    pilot = pd.read_csv(pilot_path)
    required = {"circuit_id", "circuit_family", "listing_model", "phase", "reduction"}
    missing = sorted(required - set(pilot.columns))
    if missing:
        raise ValueError(f"Pilot is missing required columns: {missing}")
    pivot = pilot.pivot_table(
        index=["circuit_id", "circuit_family"],
        columns=["phase", "listing_model"],
        values="reduction",
        aggfunc="first",
    )
    needed = [("phase2a", "LBL"), ("phase2a", "WCL"),
              ("phase2b", "LBL"), ("phase2b", "WCL")]
    complete = pivot.dropna(subset=needed).copy()
    did = 100.0 * ((complete[("phase2b", "WCL")] - complete[("phase2b", "LBL")])
                   - (complete[("phase2a", "WCL")] - complete[("phase2a", "LBL")]))
    frame = pd.DataFrame({"did": did}).reset_index()
    family_means = frame.groupby("circuit_family", sort=True)["did"].mean()
    residual = frame["did"] - frame["circuit_family"].map(family_means)
    return {
        "pilot_complete_inputs": int(len(frame)),
        "pilot_families": int(frame["circuit_family"].nunique()),
        "did_mean_pp": float(frame["did"].mean()),
        "did_total_sd_pp": float(frame["did"].std(ddof=1)),
        "did_between_family_sd_pp": float(family_means.std(ddof=1)),
        "did_within_family_sd_pp": float(residual.std(ddof=1)),
    }


def _pooled_within_family_se(values: np.ndarray, family_index: np.ndarray, n_families: int) -> np.ndarray:
    """Conditional SE: family composition/effects are fixed, not sampled."""
    n_sim, n = values.shape
    family_sum = np.zeros((n_sim, n_families), dtype=float)
    family_count = np.bincount(family_index, minlength=n_families).astype(float)
    for family in range(n_families):
        family_sum[:, family] = values[:, family_index == family].sum(axis=1)
    family_mean = family_sum / family_count[None, :]
    residual = values - family_mean[:, family_index]
    pooled_var = np.square(residual).sum(axis=1) / (n - n_families)
    return np.sqrt(pooled_var / n)


def _simulate_one(
    *,
    rng: np.random.Generator,
    family_sizes: np.ndarray,
    family_sd: float,
    within_sd: float,
    grid_correlation: float,
    effect_pp: float,
    simulations: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Return rejection indicators for fixed-benchmark A and generalized B."""
    family_index = np.repeat(np.arange(len(family_sizes)), family_sizes)
    n = int(family_sizes.sum())
    # Variance of an equal-weight mean of 12 exchangeable cell contrasts.
    attenuation = math.sqrt(grid_correlation + (1.0 - grid_correlation) / GRID_REPEATS)
    averaged_within_sd = within_sd * attenuation
    averaged_family_sd = family_sd * attenuation

    family_effect_raw = rng.normal(0.0, averaged_family_sd,
                                   size=(simulations, len(family_sizes)))
    # For estimand A, these family effects are fixed heterogeneity in the frozen
    # benchmark. Recenter to the stipulated finite-population ATE before adding
    # independent execution/input residual variation.
    input_weight = family_sizes / family_sizes.sum()
    family_effect = family_effect_raw - (
        family_effect_raw * input_weight[None, :]
    ).sum(axis=1)[:, None]
    noise = rng.normal(0.0, averaged_within_sd, size=(simulations, n))
    values = effect_pp + family_effect[:, family_index] + noise

    estimate_a = values.mean(axis=1)
    se_a = _pooled_within_family_se(values, family_index, len(family_sizes))
    reject_a = np.abs(estimate_a / se_a) > norm.ppf(1.0 - ALPHA / 2.0)

    # Estimand B gives each observed family one exchangeable cluster-level unit;
    # family heterogeneity is therefore sampling variation, not removable noise.
    # Generate the generalized-family observations from the unrecentered family
    # distribution. Reusing the conditional-A recentering here would incorrectly
    # impose a finite-benchmark constraint on the super-population estimand.
    values_b = effect_pp + family_effect_raw[:, family_index] + noise
    family_means = np.empty((simulations, len(family_sizes)), dtype=float)
    for family in range(len(family_sizes)):
        family_means[:, family] = values_b[:, family_index == family].mean(axis=1)
    estimate_b = family_means.mean(axis=1)
    se_b = family_means.std(axis=1, ddof=1) / math.sqrt(len(family_sizes))
    reject_b = np.abs(estimate_b / se_b) > t.ppf(1.0 - ALPHA / 2.0, len(family_sizes) - 1)
    return reject_a, reject_b


def run_simulation(
    manifest_path: Path,
    pilot_path: Path,
    simulations: int,
    seed: int,
) -> dict[str, object]:
    sizes = _family_sizes(manifest_path)
    anchor = _pilot_variance_components(pilot_path)
    family_sd = float(anchor["did_between_family_sd_pp"])
    within_sd = float(anchor["did_within_family_sd_pp"])
    scenarios = []
    for rho in (0.0, 0.5, 1.0):
        # Separate streams make the null and alternative estimates reproducible.
        null_a, null_b = _simulate_one(
            rng=np.random.default_rng(seed + int(100 * rho)),
            family_sizes=sizes.to_numpy(), family_sd=family_sd, within_sd=within_sd,
            grid_correlation=rho, effect_pp=0.0, simulations=simulations,
        )
        alt_a, alt_b = _simulate_one(
            rng=np.random.default_rng(seed + 10_000 + int(100 * rho)),
            family_sizes=sizes.to_numpy(), family_sd=family_sd, within_sd=within_sd,
            grid_correlation=rho, effect_pp=MCID_PP, simulations=simulations,
        )
        scenarios.append({
            "within_input_grid_correlation": rho,
            "averaged_within_family_sd_pp": within_sd * math.sqrt(rho + (1-rho)/GRID_REPEATS),
            "averaged_between_family_sd_pp": family_sd * math.sqrt(rho + (1-rho)/GRID_REPEATS),
            "fixed_benchmark_A": {
                "type_i_error": float(null_a.mean()),
                "power_at_1pp": float(alt_a.mean()),
            },
            "new_family_generalized_B": {
                "type_i_error": float(null_b.mean()),
                "power_at_1pp": float(alt_b.mean()),
            },
        })
    a_power_floor = min(s["fixed_benchmark_A"]["power_at_1pp"] for s in scenarios)
    a_type1_ceiling = max(s["fixed_benchmark_A"]["type_i_error"] for s in scenarios)
    b_power_floor = min(s["new_family_generalized_B"]["power_at_1pp"] for s in scenarios)
    b_type1_ceiling = max(s["new_family_generalized_B"]["type_i_error"] for s in scenarios)
    fixed_pass = a_power_floor >= TARGET_POWER and a_type1_ceiling <= 0.06
    generalized_pass = b_power_floor >= TARGET_POWER and b_type1_ceiling <= 0.06
    conservative_family_sd = math.sqrt(
        family_sd ** 2 + within_sd ** 2 / float(np.median(sizes.to_numpy()))
    )
    families_for_80 = None
    # Very small-df noncentral-t evaluation is numerically unstable and cannot
    # plausibly meet 80% here; start at 10 independent families.
    for candidate in range(10, 5001):
        critical = t.ppf(1 - ALPHA / 2, candidate - 1)
        delta = MCID_PP * math.sqrt(candidate) / conservative_family_sd
        candidate_power = float(nct.cdf(-critical, candidate - 1, delta)
                                + 1 - nct.cdf(critical, candidate - 1, delta))
        if candidate_power >= TARGET_POWER:
            families_for_80 = candidate
            break
    return {
        "status": "PROSPECTIVE_DUAL_ESTIMAND_SIMULATION",
        "formal_results_used": False,
        "design_manifest_sha256": _sha256(manifest_path),
        "protocol_sha256": _sha256(DEFAULT_PROTOCOL),
        "mcid_pp": MCID_PP,
        "alpha_two_sided": ALPHA,
        "target_power": TARGET_POWER,
        "simulations_per_null_or_alternative_scenario": simulations,
        "seed": seed,
        "primary_contrast": (
            "equal-weight mean over the complete 3-window x 4-budget grid of "
            "[(WCL-LBL)_COMMUTATION_PLUS_TEMPLATES - "
            "(WCL-LBL)_COMMUTATION_ONLY]"
        ),
        "multiplicity": {
            "confirmatory_tests": 1,
            "primary_alpha": ALPHA,
            "remaining_main_effects": "supportive",
            "remaining_interactions": "supportive_or_exploratory",
        },
        "variance_anchor": anchor,
        "benchmark": {
            "unique_inputs": int(sizes.sum()),
            "families": int(len(sizes)),
            "family_sizes": {str(k): int(v) for k, v in sizes.items()},
        },
        "scenarios": scenarios,
        "decision": {
            "fixed_benchmark_A": "PASS" if fixed_pass else "BLOCK",
            "new_family_generalized_B": "PASS" if generalized_pass else "BLOCK",
            "formal_28152_execution": "PASS" if fixed_pass else "BLOCK",
            "new_family_claims": "ALLOWED" if generalized_pass else "BLOCKED_UNTIL_MORE_FAMILIES",
            "fixed_power_floor": a_power_floor,
            "fixed_type_i_ceiling": a_type1_ceiling,
            "generalized_power_floor": b_power_floor,
            "generalized_type_i_ceiling": b_type1_ceiling,
            "approximate_families_required_for_80pct_at_1pp_conservative_rho1": families_for_80,
            "rationale": (
                "Formal execution is licensed only by the prospectively frozen fixed-benchmark "
                "primary. New-family claims remain separately gated and cannot borrow 391 inputs "
                "as independent family replications."
            ),
        },
        "limitations": [
            "The 12-cell correlation is not identified by the earlier pilot; 0, 0.5, and 1 are sensitivity bounds.",
            "Fixed-benchmark inference conditions on these 391 hashes and their observed family composition.",
            "Generalized inference has only 15 family clusters and must not use input-level degrees of freedom.",
            "The pilot variance anchor is prospective for E31 but comes from the earlier E31 phase2a/phase2b comparison.",
        ],
        "inference_methods": {
            "fixed_benchmark_A_power_test": "family-blocked conditional pooled test, the large-sample approximation to the frozen paired-label randomization analysis",
            "fixed_benchmark_A_formal_test": "20,000-draw family-restricted paired-label Monte Carlo randomization with a fixed seed",
            "new_family_generalized_B": "two-sided one-sample t test over equal-weight family means",
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--simulations", type=int, default=20_000)
    parser.add_argument("--seed", type=int, default=310731)
    args = parser.parse_args()
    report = run_simulation(args.manifest, args.pilot, args.simulations, args.seed)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps(report["decision"], indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
