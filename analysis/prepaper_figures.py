"""Publication-gate figures with source data and vector/600-dpi outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

OKABE_ITO = {
    "blue": "#0072B2", "orange": "#E69F00", "green": "#009E73",
    "vermillion": "#D55E00", "purple": "#CC79A7", "sky": "#56B4E9",
    "yellow": "#F0E442", "black": "#000000",
}


def _configure() -> None:
    mpl.rcParams.update({
        "font.family": "DejaVu Sans", "font.size": 9,
        "axes.labelsize": 9, "axes.titlesize": 10,
        "xtick.labelsize": 8, "ytick.labelsize": 8,
        "legend.fontsize": 8, "axes.spines.top": False,
        "axes.spines.right": False, "pdf.fonttype": 42,
        "ps.fonttype": 42, "svg.fonttype": "none",
    })


def _save(fig: plt.Figure, stem: Path) -> None:
    stem.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(stem.with_suffix(".pdf"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".svg"), bbox_inches="tight")
    fig.savefig(stem.with_suffix(".png"), dpi=600, bbox_inches="tight")
    plt.close(fig)


def _atomic_csv(frame: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    frame.to_csv(tmp, index=False)
    tmp.replace(path)


def figure_rq1(rq1_dir: Path, output: Path) -> None:
    results = json.loads((rq1_dir / "rq1_results.json").read_text(encoding="utf-8"))
    family = pd.read_csv(rq1_dir / "family_contrasts.csv")
    primary = results["multifamily_primary"]
    replication = results["random_depth_replication"]
    rows = family.rename(columns={
        "circuit_family": "label", "mean_difference_pp": "estimate_pp",
        "ci95_lower_pp": "lower_pp", "ci95_upper_pp": "upper_pp",
    })[["label", "estimate_pp", "lower_pp", "upper_pp"]]
    rows["evidence"] = "family"
    aggregate = pd.DataFrame([
        {"label": "Overall (family-clustered)",
         "estimate_pp": primary["wcl_minus_lbl_mean_pp"],
         "lower_pp": primary["ci95_lower_pp"],
         "upper_pp": primary["ci95_upper_pp"], "evidence": "primary"},
        {"label": "Random-depth replication",
         "estimate_pp": replication["wcl_minus_lbl_mean_pp"],
         "lower_pp": replication["ci95_lower_pp"],
         "upper_pp": replication["ci95_upper_pp"], "evidence": "supporting"},
    ])
    source = pd.concat([rows, aggregate], ignore_index=True)
    _atomic_csv(source, output / "source_data" / "fig01_rq1_listing_forest.csv")
    source = source.iloc[::-1].reset_index(drop=True)
    colors = source.evidence.map({
        "family": OKABE_ITO["blue"], "primary": OKABE_ITO["vermillion"],
        "supporting": OKABE_ITO["orange"],
    })
    fig, ax = plt.subplots(figsize=(7.2, max(3.8, 0.34 * len(source) + 1.2)))
    y = np.arange(len(source))
    ax.axvspan(-1, 1, color="#DDDDDD", alpha=0.55, label="Equivalence margin ±1 pp")
    ax.axvline(0, color="black", lw=0.8)
    for i, row in source.iterrows():
        ax.errorbar(row.estimate_pp, i,
                    xerr=[[row.estimate_pp - row.lower_pp],
                          [row.upper_pp - row.estimate_pp]],
                    fmt="o", color=colors.iloc[i], ecolor=colors.iloc[i],
                    capsize=2.5, markersize=4.5)
    ax.set_yticks(y, source.label)
    ax.set_xlabel("WCL − LBL gate reduction (percentage points; 95% CI)")
    ax.set_title("Representation sensitivity under the frozen Greedy rule set")
    ax.legend(frameon=False, loc="lower right")
    _save(fig, output / "fig01_rq1_listing_forest")


def figure_heldout(heldout_dir: Path, output: Path) -> None:
    source = pd.read_csv(heldout_dir / "generator_diagnostics.csv").sort_values(
        "circuit_family")
    _atomic_csv(source, output / "source_data" / "fig02_heldout_generator_rates.csv")
    metrics = json.loads((heldout_dir / "heldout_metrics.json").read_text(encoding="utf-8"))
    x = np.arange(len(source))
    width = 0.38
    fig, ax = plt.subplots(figsize=(8.4, 4.2))
    ax.bar(x - width / 2, source.observed_positive_rate, width,
           label="Observed joint headroom", color=OKABE_ITO["blue"],
           edgecolor="black", linewidth=0.5, hatch="///")
    ax.bar(x + width / 2, source.predicted_positive_rate, width,
           label="Sealed prediction", color=OKABE_ITO["orange"],
           edgecolor="black", linewidth=0.5, hatch="...")
    ax.set_xticks(x, source.circuit_family, rotation=35, ha="right")
    ax.set_ylim(0, 1.08)
    ax.set_ylabel("Positive rate")
    ax.set_title("Sealed out-of-family structural prediction by generator")
    ax.legend(frameon=False, loc="center left", bbox_to_anchor=(1.01, 0.5))
    mcc = metrics.get("mcc_point", metrics.get("mcc", float("nan")))
    lower = metrics.get("mcc_ci95_lower", float("nan"))
    upper = metrics.get("mcc_ci95_upper", float("nan"))
    ax.text(0.01, 0.98, f"MCC={mcc:.3f} (nested 95% CI {lower:.3f}–{upper:.3f})",
            transform=ax.transAxes, va="top")
    _save(fig, output / "fig02_heldout_generator_rates")


def figure_rq3(rq3_dir: Path, output: Path) -> None:
    source = pd.read_csv(rq3_dir / "tool_summary.csv")
    _atomic_csv(source, output / "source_data" / "fig03_tool_summary.csv")
    x = np.arange(len(source))
    colors = [OKABE_ITO["blue"], OKABE_ITO["orange"],
              OKABE_ITO["green"], OKABE_ITO["purple"]]
    hatches = ["///", "...", "xxx", "\\\\"]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
    valid = 100.0 * source.valid_rate.to_numpy(float)
    valid_lo = 100.0 * source.valid_rate_ci95_lower.to_numpy(float)
    valid_hi = 100.0 * source.valid_rate_ci95_upper.to_numpy(float)
    bars = axes[0].bar(x, valid, color=colors, edgecolor="black", linewidth=0.5)
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)
    axes[0].errorbar(x, valid, yerr=[valid - valid_lo, valid_hi - valid],
                     fmt="none", ecolor="black", capsize=2.5)
    axes[0].set_ylabel("Valid equivalent output rate (%)")
    axes[0].set_ylim(0, 105)
    axes[0].set_title("ITT validity")
    reduction = source.common_reduction_pct_itt_mean.to_numpy(float)
    red_lo = source.common_reduction_ci95_lower.to_numpy(float)
    red_hi = source.common_reduction_ci95_upper.to_numpy(float)
    bars = axes[1].bar(x, reduction, color=colors, edgecolor="black", linewidth=0.5)
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)
    axes[1].errorbar(x, reduction, yerr=[reduction - red_lo, red_hi - reduction],
                     fmt="none", ecolor="black", capsize=2.5)
    axes[1].axhline(0, color="black", lw=0.8)
    axes[1].set_ylabel("Common-basis gate reduction, ITT (pp)")
    axes[1].set_title("Fixed-version outcome")
    for ax in axes:
        ax.set_xticks(x, source.tool, rotation=25, ha="right")
    fig.suptitle("Shared 520-input compiler comparison")
    fig.tight_layout()
    _save(fig, output / "fig03_tool_summary")


def figure_external(external_summary: Path, output: Path) -> None:
    source = pd.read_csv(external_summary)
    required = {
        "method", "valid_rate", "valid_ci95_lower", "valid_ci95_upper",
        "gate_reduction_itt_mean", "gate_reduction_ci95_lower",
        "gate_reduction_ci95_upper",
    }
    if not required.issubset(source.columns):
        raise RuntimeError(f"external summary missing {sorted(required - set(source.columns))}")
    _atomic_csv(source, output / "source_data" / "fig04_external_baselines.csv")
    x = np.arange(len(source))
    colors = [OKABE_ITO["vermillion"], OKABE_ITO["sky"],
              OKABE_ITO["green"], OKABE_ITO["purple"]][:len(source)]
    hatches = ["///", "...", "xxx", "\\\\"][:len(source)]
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.4))
    valid = 100 * source.valid_rate.to_numpy(float)
    vlo = 100 * source.valid_ci95_lower.to_numpy(float)
    vhi = 100 * source.valid_ci95_upper.to_numpy(float)
    bars = axes[0].bar(x, valid, color=colors, edgecolor="black")
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)
    axes[0].errorbar(x, valid, yerr=[valid - vlo, vhi - valid], fmt="none",
                     ecolor="black", capsize=2.5)
    axes[0].set_ylim(0, 105)
    axes[0].set_ylabel("Valid equivalent output rate (%)")
    reduction = source.gate_reduction_itt_mean.to_numpy(float)
    rlo = source.gate_reduction_ci95_lower.to_numpy(float)
    rhi = source.gate_reduction_ci95_upper.to_numpy(float)
    bars = axes[1].bar(x, reduction, color=colors, edgecolor="black")
    for bar, hatch in zip(bars, hatches):
        bar.set_hatch(hatch)
    axes[1].errorbar(x, reduction, yerr=[reduction - rlo, rhi - reduction],
                     fmt="none", ecolor="black", capsize=2.5)
    axes[1].axhline(0, color="black", lw=0.8)
    axes[1].set_ylabel("Common-basis gate reduction, ITT (pp)")
    for ax in axes:
        ax.set_xticks(x, source.method, rotation=25, ha="right")
    fig.suptitle("Strong external methods under the shared logical-input contract")
    fig.tight_layout()
    _save(fig, output / "fig04_external_baselines")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rq1-dir", type=Path, required=True)
    parser.add_argument("--heldout-dir", type=Path, required=True)
    parser.add_argument("--rq3-dir", type=Path, required=True)
    parser.add_argument("--external-summary", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    _configure()
    figure_rq1(args.rq1_dir, args.output_dir)
    figure_heldout(args.heldout_dir, args.output_dir)
    figure_rq3(args.rq3_dir, args.output_dir)
    if args.external_summary is not None:
        figure_external(args.external_summary, args.output_dir)


if __name__ == "__main__":
    main()
