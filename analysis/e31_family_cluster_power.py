"""Prospective family-cluster power/MDE simulation for E31 primary contrasts."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PILOT = PROJECT_ROOT / "data" / "v11" / "e31_listing_phase2b" / "e31_listing_phase2b_pilot.csv"
DEFAULT_DESIGN = PROJECT_ROOT / "data" / "v11" / "e31_factorial_pareto" / "design_manifest.csv"
DEFAULT_OUTPUT = PROJECT_ROOT / "data" / "v11" / "e31_factorial_pareto" / "power_mde_recommendation.json"
SEED = 20260811
SIMULATIONS = 20000
TARGET_POWER = 0.80
MCID_PP = 1.0
FAMILY_SD_FLOOR_PP = 2.0
RESIDUAL_SD_FLOOR_PP = 5.0
PRIMARY_CONTRASTS = 2 * 3 * 4  # rule sets x windows x budgets


def estimate_variance_components(pilot: pd.DataFrame) -> tuple[float, float]:
    """Use pilot Phase2b WCL-LBL differences only as a conservative anchor."""
    subset = pilot[pilot["phase"].eq("phase2b")]
    wide = subset.pivot(index=["circuit_id", "circuit_family"],
                        columns="listing_model", values="reduction").reset_index()
    if not {"WCL", "LBL"}.issubset(wide.columns):
        raise ValueError("pilot lacks paired Phase2b WCL/LBL rows")
    wide["difference_pp"] = 100.0 * (wide["WCL"] - wide["LBL"])
    family_mean = wide.groupby("circuit_family")["difference_pp"].mean()
    residual = wide["difference_pp"] - wide.groupby("circuit_family")["difference_pp"].transform("mean")
    return float(family_mean.std(ddof=1)), float(residual.std(ddof=1))


def simulate_power(effect_pp: float, family_sizes: np.ndarray, family_sd_pp: float,
                   residual_sd_pp: float, alpha: float, *, simulations: int,
                   seed: int) -> float:
    """Power of a two-sided family-level paired t test under a nested model."""
    rng = np.random.default_rng(seed)
    sizes = np.asarray(family_sizes, dtype=float)
    family_effect = rng.normal(0.0, family_sd_pp, size=(simulations, len(sizes)))
    residual_mean = rng.normal(
        0.0, residual_sd_pp / np.sqrt(sizes), size=(simulations, len(sizes))
    )
    values = effect_pp + family_effect + residual_mean
    mean = values.mean(axis=1)
    standard_error = values.std(axis=1, ddof=1) / np.sqrt(len(sizes))
    statistic = np.divide(mean, standard_error, out=np.zeros_like(mean), where=standard_error > 0)
    critical = stats.t.ppf(1.0 - alpha / 2.0, df=len(sizes) - 1)
    return float(np.mean(np.abs(statistic) >= critical))


def find_mde(family_sizes: np.ndarray, family_sd_pp: float, residual_sd_pp: float,
             alpha: float, *, simulations: int = SIMULATIONS) -> float:
    low, high = 0.0, 20.0
    for iteration in range(24):
        midpoint = (low + high) / 2.0
        power = simulate_power(midpoint, family_sizes, family_sd_pp, residual_sd_pp,
                               alpha, simulations=simulations, seed=SEED + iteration)
        if power >= TARGET_POWER:
            high = midpoint
        else:
            low = midpoint
    return float(high)


def recommend(pilot: pd.DataFrame, design: pd.DataFrame,
              *, simulations: int = SIMULATIONS) -> dict[str, object]:
    per_family = (design.drop_duplicates("input_circuit_sha256")
                  .groupby("circuit_family").size().to_numpy(int))
    pilot_family_sd, pilot_residual_sd = estimate_variance_components(pilot)
    family_sd = max(pilot_family_sd, FAMILY_SD_FLOOR_PP)
    residual_sd = max(pilot_residual_sd, RESIDUAL_SD_FLOOR_PP)
    alpha = 0.05 / PRIMARY_CONTRASTS
    power_at_mcid = simulate_power(
        MCID_PP, per_family, family_sd, residual_sd, alpha,
        simulations=simulations, seed=SEED,
    )
    mde = find_mde(per_family, family_sd, residual_sd, alpha, simulations=simulations)
    median_size = int(np.median(per_family))
    required_families = None
    for count in range(len(per_family), 129):
        sizes = np.full(count, median_size, dtype=int)
        candidate = simulate_power(
            MCID_PP, sizes, family_sd, residual_sd, alpha,
            simulations=simulations, seed=SEED + 1000 + count,
        )
        if candidate >= TARGET_POWER:
            required_families = count
            break
    return {
        "status": "PROSPECTIVE_DESIGN_GATE_NOT_RESULT",
        "simulation_seed": SEED,
        "simulations": simulations,
        "test": "two-sided family-level paired t sensitivity under nested normal simulation",
        "multiplicity": "Bonferroni planning bound for 24 prespecified WCL-LBL contrasts; formal analysis uses Holm",
        "alpha_per_contrast": alpha,
        "target_power": TARGET_POWER,
        "mcid_pp": MCID_PP,
        "current_outer_families": int(len(per_family)),
        "current_unique_inputs": int(design.input_circuit_sha256.nunique()),
        "family_size_min": int(per_family.min()),
        "family_size_median": median_size,
        "family_size_max": int(per_family.max()),
        "pilot_family_sd_pp": pilot_family_sd,
        "pilot_residual_sd_pp": pilot_residual_sd,
        "planning_family_sd_pp": family_sd,
        "planning_residual_sd_pp": residual_sd,
        "variance_floor_reason": "smoke pilot is zero-inflated and cannot justify near-zero planning variance",
        "simulated_power_at_mcid": power_at_mcid,
        "simulated_mde_pp_at_80pct_power": mde,
        "families_needed_for_1pp_at_median_family_size": required_families,
        "freeze_recommendation": (
            "BLOCK formal execution until simulated power at the 1 pp MCID is at least 0.80; "
            "increase genuinely independent families or explicitly narrow the confirmatory claim."
            if power_at_mcid < TARGET_POWER else
            "Power gate passes under the frozen conservative variance floors."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--design", type=Path, default=DEFAULT_DESIGN)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--simulations", type=int, default=SIMULATIONS)
    args = parser.parse_args()
    result = recommend(pd.read_csv(args.pilot), pd.read_csv(args.design),
                       simulations=args.simulations)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
