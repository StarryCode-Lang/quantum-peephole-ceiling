"""Run a bounded E31 primary-contrast specification curve and family influence audit."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import t as student_t


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/v11/e31_factorial_pareto/formal_run/final/formal_results.csv"
DEFAULT_OUTPUT_DIR = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/specification_influence"
BUDGET_SPECS = {
    "all_1_10_30_120": [1, 10, 30, 120],
    "executable_10_30_120": [10, 30, 120],
    "long_30_120": [30, 120],
    "terminal_120": [120],
}
WINDOW_SPECS = {
    "all_4_16_64": [4, 16, 64],
    "window_4": [4],
    "window_16": [16],
    "window_64": [64],
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _per_input_contrast(frame: pd.DataFrame, budgets: list[int], windows: list[int]) -> pd.DataFrame:
    subset = frame.loc[
        frame["budget_seconds"].isin(budgets) & frame["window_gates"].isin(windows)
    ]
    pivot = subset.pivot_table(
        index=["input_circuit_sha256", "circuit_family", "window_gates", "budget_seconds"],
        columns=["listing_model", "rule_set"],
        values="itt_reduction_pp",
        aggfunc="first",
    )
    keys = [
        ("WCL", "COMMUTATION_PLUS_TEMPLATES"),
        ("LBL", "COMMUTATION_PLUS_TEMPLATES"),
        ("WCL", "COMMUTATION_ONLY"),
        ("LBL", "COMMUTATION_ONLY"),
    ]
    expected = 391 * len(budgets) * len(windows)
    if len(pivot) != expected or any(key not in pivot.columns for key in keys):
        raise RuntimeError("incomplete specification cell")
    did = (pivot[keys[0]] - pivot[keys[1]] - pivot[keys[2]] + pivot[keys[3]]).rename("did_pp")
    return did.reset_index().groupby(
        ["input_circuit_sha256", "circuit_family"], as_index=False
    )["did_pp"].mean()


def derive(output_dir: Path = DEFAULT_OUTPUT_DIR) -> dict[str, object]:
    frame = pd.read_csv(SOURCE)
    if len(frame) != 28152:
        raise RuntimeError("unexpected E31 row count")
    frame["itt_reduction_pp"] = np.where(
        frame["status"].eq("success"), frame["common_basis_gate_reduction_pct"], 0.0
    )
    records: list[dict[str, object]] = []
    per_input_cache: dict[tuple[str, str], pd.DataFrame] = {}
    critical = float(student_t.ppf(0.975, df=14))
    for budget_name, budgets in BUDGET_SPECS.items():
        for window_name, windows in WINDOW_SPECS.items():
            per_input = _per_input_contrast(frame, budgets, windows)
            per_input_cache[(budget_name, window_name)] = per_input
            family = per_input.groupby("circuit_family", as_index=False)["did_pp"].mean()
            values = family["did_pp"].to_numpy(dtype=float)
            mean = float(np.mean(values))
            se = float(np.std(values, ddof=1) / np.sqrt(15))
            records.extend(
                [
                    {
                        "budget_spec": budget_name,
                        "window_spec": window_name,
                        "weighting": "fixed_input_weighted_descriptive",
                        "estimate_pp": float(per_input["did_pp"].mean()),
                        "ci95_low_pp": None,
                        "ci95_high_pp": None,
                        "inference_role": "FIXED_PANEL_DESCRIPTIVE_NO_POPULATION_CI",
                    },
                    {
                        "budget_spec": budget_name,
                        "window_spec": window_name,
                        "weighting": "equal_family_supportive",
                        "estimate_pp": mean,
                        "ci95_low_pp": mean - critical * se,
                        "ci95_high_pp": mean + critical * se,
                        "inference_role": "SUPPORTIVE_T14_OVER_15_OBSERVED_FAMILY_MEANS",
                    },
                ]
            )
    specifications = pd.DataFrame(records)
    if len(specifications) != 32:
        raise RuntimeError("unexpected specification count")

    primary = per_input_cache[("all_1_10_30_120", "all_4_16_64")]
    family_primary = primary.groupby("circuit_family", as_index=False)["did_pp"].mean()
    base = float(family_primary["did_pp"].mean())
    influence = []
    for family in sorted(family_primary["circuit_family"]):
        leave = family_primary.loc[family_primary["circuit_family"].ne(family), "did_pp"]
        estimate = float(leave.mean())
        influence.append(
            {
                "left_out_family": family,
                "leave_one_family_out_equal_family_mean_pp": estimate,
                "delta_from_all_families_pp": estimate - base,
                "sign_changed": np.sign(estimate) != np.sign(base),
            }
        )
    maximum = max(influence, key=lambda row: abs(row["delta_from_all_families_pp"]))

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "specification_curve.csv"
    influence_path = output_dir / "leave_one_family_out.csv"
    json_path = output_dir / "specification_influence_audit.json"
    png_path = output_dir / "specification_curve.png"
    pdf_path = output_dir / "specification_curve.pdf"
    specifications.to_csv(csv_path, index=False)
    pd.DataFrame(influence).to_csv(influence_path, index=False)

    plotted = specifications.loc[
        specifications["weighting"].eq("equal_family_supportive")
    ].sort_values("estimate_pp").reset_index(drop=True)
    x = np.arange(len(plotted))
    y = plotted["estimate_pp"].to_numpy(dtype=float)
    low = y - plotted["ci95_low_pp"].to_numpy(dtype=float)
    high = plotted["ci95_high_pp"].to_numpy(dtype=float) - y
    colors = [f"C{list(BUDGET_SPECS).index(value)}" for value in plotted["budget_spec"]]
    fig, axis = plt.subplots(figsize=(11.5, 5.2), constrained_layout=True)
    axis.errorbar(x, y, yerr=[low, high], fmt="none", ecolor="0.55", capsize=2, zorder=1)
    axis.scatter(x, y, c=colors, s=42, zorder=2)
    axis.axhline(0.0, color="black", linewidth=1, linestyle="--")
    axis.set_xticks(x)
    axis.set_xticklabels(
        [f"{row.budget_spec}\n{row.window_spec}" for row in plotted.itertuples()],
        rotation=55,
        ha="right",
        fontsize=8,
    )
    axis.set_ylabel("Equal-family primary contrast (pp), t14 95% CI")
    axis.set_title("E31 post-seal specification curve (16 defensible budget/window specifications)")
    axis.grid(axis="y", alpha=0.25)
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)

    signs = set(np.sign(specifications["estimate_pp"].to_numpy(dtype=float)))
    payload = {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_E31_SPECIFICATION_CURVE_AND_FAMILY_INFLUENCE_COMPLETE",
        "source_sha256": _sha256(SOURCE),
        "specification_count": len(specifications),
        "budget_specifications": BUDGET_SPECS,
        "window_specifications": WINDOW_SPECS,
        "weighting_specifications": [
            "fixed_input_weighted_descriptive",
            "equal_family_supportive",
        ],
        "estimate_min_pp": float(specifications["estimate_pp"].min()),
        "estimate_max_pp": float(specifications["estimate_pp"].max()),
        "estimate_sign_stable": len(signs) == 1,
        "specification_csv": _artifact_path(csv_path),
        "specification_csv_sha256": _sha256(csv_path),
        "leave_one_family_out_csv": _artifact_path(influence_path),
        "leave_one_family_out_csv_sha256": _sha256(influence_path),
        "figure_png": _artifact_path(png_path),
        "figure_png_sha256": _sha256(png_path),
        "figure_pdf": _artifact_path(pdf_path),
        "figure_pdf_sha256": _sha256(pdf_path),
        "family_influence": {
            "all_family_equal_family_mean_pp": base,
            "leave_one_family_out_checks": len(influence),
            "sign_change_count": sum(bool(row["sign_changed"]) for row in influence),
            "maximum_absolute_delta_family": maximum["left_out_family"],
            "maximum_absolute_delta_pp": abs(float(maximum["delta_from_all_families_pp"])),
        },
        "interpretation": (
            "The curve varies frozen budget inclusion, window inclusion, and population weighting. "
            "It is a post-seal robustness multiverse; no row is a new confirmatory test."
        ),
        "limitations": [
            "The multiverse is bounded to 32 prespecified-by-construction defensible summaries and is not exhaustive.",
            "Equal-family t14 intervals cover only the 15 observed families and do not license unseen-family claims.",
            "Fixed-input-weighted rows are descriptive and intentionally omit a pseudo-population confidence interval.",
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    payload = derive(output)
    print(json.dumps({"output": _artifact_path(output / "specification_influence_audit.json"), "status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
