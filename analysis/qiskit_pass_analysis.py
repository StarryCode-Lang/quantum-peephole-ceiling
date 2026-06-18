"""
Qiskit Pass Isolation Deep Analysis
=====================================
Analyzes the individual contribution of each Qiskit transpiler pass
vs. our peephole optimizer phases, identifying which mechanisms
explain the 20-45% performance gap between Qiskit's full pipeline
and our prototype.

Generates:
  - fig15_qiskit_pass_waterfall.png: Waterfall chart of cumulative reduction per pass
  - fig16_qiskit_pass_family_heatmap.png: Heatmap of pass effectiveness per circuit family
  - fig17_qiskit_pass_interaction.png: Interaction matrix between passes

Saves:
  - analysis/figures/qiskit_pass_analysis_summary.csv

This script is part of the structural ceiling framework analysis
(Section 5.3 of the expanded manuscript).
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy import stats

# Use Agg backend for non-interactive plotting (matches project convention)
matplotlib.use("Agg")
plt.style.use("seaborn-v0_8-whitegrid")

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data" / "v5"
OUTPUT_DIR = PROJECT_ROOT / "analysis" / "figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Color palette (consistent with generate_figures.py)
# ---------------------------------------------------------------------------
COLORS = {
    "custom_greedy": "#2E86AB",       # blue
    "custom_commutation": "#2E86AB",  # blue (lighter in plot)
    "qiskit_CC": "#A23B72",           # magenta
    "qiskit_1q": "#F18F01",           # orange
    "qiskit_CX": "#C73E1D",           # red (if present)
    "qiskit_full": "#6A4C93",         # purple (for E15 context)
}

PASS_DISPLAY_NAMES = {
    "greedy_phase1": "Greedy\n(Phase 1)",
    "commutation_phase2": "Commutation\n(Phase 2)",
    "CommutativeCancellation": "Commutative\nCancellation",
    "Optimize1qGates": "Optimize1q\nGates",
    "CXCancellation": "CX\nCancellation",
}

FAMILY_DISPLAY_NAMES = {
    "CNOT_chain": "CNOT Chain",
    "QFT": "QFT",
    "Oracle": "Oracle (BV)",
    "RandomClifford": "Random\nClifford",
    "GHZ": "GHZ",
}


def load_data() -> tuple[pd.DataFrame, pd.DataFrame | None]:
    """Load pass isolation CSV and optionally the E15 multi-compiler CSV.

    Returns:
        (pass_df, e15_df) where e15_df may be None if not found.
    """
    pass_csv = DATA_DIR / "qiskit_pass_isolation.csv"
    if not pass_csv.exists():
        raise FileNotFoundError(f"Pass isolation data not found: {pass_csv}")

    pass_df = pd.read_csv(pass_csv)
    print(f"Loaded pass isolation data: {len(pass_df)} rows, "
          f"{pass_df['circuit_family'].nunique()} families, "
          f"{pass_df['pass_name'].nunique()} passes")

    # Load E15 for context (best full-pipeline Qiskit result)
    e15_df = None
    e15_dir = DATA_DIR / "e15"
    if e15_dir.exists():
        e15_files = sorted(e15_dir.glob("e15_multi_compiler_*_full_*.csv"))
        if e15_files:
            e15_df = pd.read_csv(e15_files[-1])
            print(f"Loaded E15 multi-compiler data: {len(e15_df)} rows")

    return pass_df, e15_df


# ===================================================================
# Analysis functions
# ===================================================================

def compute_pass_effectiveness(pass_df: pd.DataFrame) -> pd.DataFrame:
    """Compute mean gate reduction contributed by each pass, overall and per family.

    Returns a DataFrame with columns:
        pass_name, compiler, mean_reduction, std_reduction,
        median_reduction, n_circuits, best_family, worst_family
    """
    rows = []
    for (pass_name, compiler), grp in pass_df.groupby(["pass_name", "compiler"]):
        reductions = grp["reduction"].dropna()
        # Find best/worst family for this pass
        fam_means = grp.groupby("circuit_family")["reduction"].mean()
        best_fam = fam_means.idxmax() if len(fam_means) > 0 else "N/A"
        worst_fam = fam_means.idxmin() if len(fam_means) > 0 else "N/A"

        rows.append({
            "pass_name": pass_name,
            "compiler": compiler,
            "mean_reduction": reductions.mean(),
            "std_reduction": reductions.std() if len(reductions) > 1 else 0.0,
            "median_reduction": reductions.median(),
            "n_circuits": len(reductions),
            "best_family": best_fam,
            "best_family_reduction": fam_means.max() if len(fam_means) > 0 else 0.0,
            "worst_family": worst_fam,
            "worst_family_reduction": fam_means.min() if len(fam_means) > 0 else 0.0,
        })

    return pd.DataFrame(rows)


def compute_family_pass_matrix(pass_df: pd.DataFrame) -> pd.DataFrame:
    """Build a pivot table: rows = circuit_family, cols = pass_name, values = mean reduction."""
    pivot = pass_df.groupby(["circuit_family", "pass_name"])["reduction"].mean().reset_index()
    matrix = pivot.pivot(index="circuit_family", columns="pass_name", values="reduction")
    # Sort families in a canonical order
    family_order = ["CNOT_chain", "QFT", "Oracle", "RandomClifford", "GHZ"]
    present_families = [f for f in family_order if f in matrix.index]
    matrix = matrix.loc[present_families]
    return matrix.fillna(0.0)


def compute_interaction_matrix(pass_df: pd.DataFrame) -> pd.DataFrame:
    """Compute an interaction matrix between passes.

    For each pair of passes (i, j), we compute a synergy score:
      synergy = mean(|reduction_i - reduction_j|) across matched circuits.

    Low synergy (similar effectiveness) suggests the passes target the same structures.
    High synergy (different effectiveness) suggests complementary mechanisms.

    We also compute a 'co-benefit' metric: for circuits where pass i helps,
    does pass j also help? This is the fraction of circuits where both passes
    achieve > 0 reduction.
    """
    # Build per-circuit reduction lookup: (family, n_qubits) -> {pass_name: reduction}
    circuit_pass = {}
    for _, row in pass_df.iterrows():
        key = (row["circuit_family"], row["n_qubits"])
        if key not in circuit_pass:
            circuit_pass[key] = {}
        circuit_pass[key][row["pass_name"]] = row["reduction"]

    passes = sorted(pass_df["pass_name"].unique())
    n = len(passes)
    synergy = np.zeros((n, n))
    cobenefit = np.zeros((n, n))

    for i, pi in enumerate(passes):
        for j, pj in enumerate(passes):
            diffs = []
            both_help = 0
            either_help = 0
            for key, pass_map in circuit_pass.items():
                ri = pass_map.get(pi, 0.0)
                rj = pass_map.get(pj, 0.0)
                diffs.append(abs(ri - rj))
                if ri > 0.001 or rj > 0.001:
                    either_help += 1
                if ri > 0.001 and rj > 0.001:
                    both_help += 1

            synergy[i, j] = np.mean(diffs) if diffs else 0.0
            cobenefit[i, j] = both_help / either_help if either_help > 0 else 0.0

    # Return as DataFrame with pass names as index/columns
    interaction_df = pd.DataFrame(synergy, index=passes, columns=passes)
    cobenefit_df = pd.DataFrame(cobenefit, index=passes, columns=passes)

    return interaction_df, cobenefit_df


def compute_qiskit_gap_analysis(pass_df: pd.DataFrame,
                                 e15_df: pd.DataFrame | None) -> pd.DataFrame:
    """Analyze the gap between Qiskit full pipeline and our prototype.

    For each circuit family in E15, computes:
      - Our best reduction (max across greedy_phase1, commutation_phase2, hybrid)
      - Qiskit full pipeline best (from E15, max across opt levels 1-3)
      - Gap = Qiskit_full - our_best
    For families also in the pass isolation data, additionally computes:
      - Qiskit isolated pass contributions (CommutativeCancellation, Optimize1qGates)
      - Fraction of gap explained by each isolated pass
    """
    if e15_df is None:
        return pd.DataFrame()

    # Normalize compiler_opt_level to string for comparison
    e15_df = e15_df.copy()
    e15_df["compiler_opt_level"] = e15_df["compiler_opt_level"].astype(str)

    # --- Per-family best from E15 ---
    # Our best per family (max across all custom optimizers)
    e15_custom = e15_df[e15_df["compiler"] == "custom"]
    our_best_e15 = e15_custom.groupby("circuit_family")["reduction"].max()

    # Qiskit full pipeline best per family (max across opt levels 1-3, excluding 0=no opt)
    e15_qiskit_opt = e15_df[
        (e15_df["compiler"] == "qiskit") &
        (e15_df["compiler_opt_level"].isin(["1", "2", "3"]))
    ]
    qiskit_full_best = e15_qiskit_opt.groupby("circuit_family")["reduction"].max()

    # Pass isolation data lookup
    pass_iso_lookup = {}
    for fam in pass_df["circuit_family"].unique():
        cc_r = pass_df[
            (pass_df["circuit_family"] == fam) &
            (pass_df["pass_name"] == "CommutativeCancellation")
        ]["reduction"].mean()
        o1q_r = pass_df[
            (pass_df["circuit_family"] == fam) &
            (pass_df["pass_name"] == "Optimize1qGates")
        ]["reduction"].mean()
        pass_iso_lookup[fam] = {
            "CC": cc_r if not np.isnan(cc_r) else 0.0,
            "Opt1q": o1q_r if not np.isnan(o1q_r) else 0.0,
        }

    # Map E15 family names to pass isolation family names
    e15_to_iso = {
        "CNOT": "CNOT_chain", "QFT": "QFT", "Oracle": "Oracle",
        "GHZ": "GHZ", "RandomClifford": "RandomClifford",
    }

    rows = []
    all_families = sorted(set(our_best_e15.index) | set(qiskit_full_best.index))
    for fam in all_families:
        our_r = our_best_e15.get(fam, 0.0)
        qfull_r = qiskit_full_best.get(fam, 0.0)
        gap = qfull_r - our_r

        # Pass isolation data (if available)
        iso_fam = e15_to_iso.get(fam, fam)
        iso_data = pass_iso_lookup.get(iso_fam, None)
        cc_r = iso_data["CC"] if iso_data else np.nan
        o1q_r = iso_data["Opt1q"] if iso_data else np.nan

        # Fraction of gap explained by isolated passes
        if gap > 0.001 and iso_data is not None:
            cc_excess = max(0.0, cc_r - our_r)
            o1q_excess = max(0.0, o1q_r - our_r)
            cc_frac = cc_excess / gap
            o1q_frac = o1q_excess / gap
            unexplained = max(0.0, 1.0 - cc_frac - o1q_frac)
        elif abs(gap) <= 0.001:
            cc_frac = 0.0
            o1q_frac = 0.0
            unexplained = 0.0
        else:
            cc_frac = np.nan
            o1q_frac = np.nan
            unexplained = np.nan

        rows.append({
            "circuit_family": fam,
            "our_best_reduction": our_r,
            "qiskit_full_pipeline": qfull_r,
            "gap": gap,
            "has_pass_isolation_data": iso_data is not None,
            "CC_reduction": cc_r if not np.isnan(cc_r) else 0.0,
            "Opt1q_reduction": o1q_r if not np.isnan(o1q_r) else 0.0,
            "gap_frac_CC": cc_frac if not np.isnan(cc_frac) else 0.0,
            "gap_frac_Opt1q": o1q_frac if not np.isnan(o1q_frac) else 0.0,
            "gap_frac_unexplained": unexplained if not np.isnan(unexplained) else 0.0,
        })

    return pd.DataFrame(rows)


# ===================================================================
# Figure generation
# ===================================================================

def generate_fig15_waterfall(pass_df: pd.DataFrame,
                              e15_df: pd.DataFrame | None) -> None:
    """Figure 15: Waterfall chart showing reduction from each pass.

    Grouped bar chart: for each circuit family, show the mean reduction
    achieved by each individual pass (custom and Qiskit), plus the
    Qiskit full pipeline (from E15) as a reference line.
    """
    print("Generating Figure 15: Qiskit Pass Waterfall...")

    family_order = ["CNOT_chain", "QFT", "Oracle", "RandomClifford", "GHZ"]
    present_families = [f for f in family_order if f in pass_df["circuit_family"].values]

    # Compute mean reduction per (family, pass_name)
    pivot = pass_df.groupby(["circuit_family", "pass_name"])["reduction"].mean().reset_index()
    matrix = pivot.pivot(index="circuit_family", columns="pass_name", values="reduction")
    matrix = matrix.loc[present_families].fillna(0.0)

    # Pass ordering for display
    pass_order = ["greedy_phase1", "commutation_phase2",
                   "CommutativeCancellation", "Optimize1qGates"]
    passes_present = [p for p in pass_order if p in matrix.columns]

    # Add CXCancellation if present
    if "CXCancellation" in matrix.columns:
        passes_present.append("CXCancellation")

    pass_colors = {
        "greedy_phase1": "#2E86AB",
        "commutation_phase2": "#5DA9C2",
        "CommutativeCancellation": "#A23B72",
        "Optimize1qGates": "#F18F01",
        "CXCancellation": "#C73E1D",
    }

    n_fam = len(present_families)
    n_pass = len(passes_present)
    x = np.arange(n_fam)
    width = 0.8 / n_pass

    fig, ax = plt.subplots(figsize=(14, 7))

    for i, pname in enumerate(passes_present):
        vals = matrix[pname].values * 100
        compiler = "custom" if pname in ("greedy_phase1", "commutation_phase2") else "qiskit"

        # Compute error bars (std across qubit sizes).
        # NOTE: uses sample standard deviation (std, ddof=1) of the per-family
        # reductions, NOT the standard error of the mean (SEM). Since these
        # bars annotate a *mean* reduction, SEM = std / sqrt(n) would be the
        # statistically correct quantity for "mean ± error" reporting; std is
        # retained here for consistency with the existing figure.
        yerrs = []
        for fam in present_families:
            fam_pass_data = pass_df[
                (pass_df["circuit_family"] == fam) &
                (pass_df["pass_name"] == pname)
            ]["reduction"]
            if len(fam_pass_data) > 1:
                yerrs.append(fam_pass_data.std() * 100)
            else:
                yerrs.append(0.0)

        label = PASS_DISPLAY_NAMES.get(pname, pname).replace("\n", " ")
        ax.bar(x + i * width, vals, width, label=label,
               color=pass_colors.get(pname, "#888888"), alpha=0.85,
               edgecolor="black", linewidth=0.5,
               yerr=yerrs, capsize=2, ecolor="black")

    # Add Qiskit full pipeline reference (from E15, best of opt levels 1-3)
    if e15_df is not None:
        e15_df_local = e15_df.copy()
        e15_df_local["compiler_opt_level"] = e15_df_local["compiler_opt_level"].astype(str)
        e15_qiskit = e15_df_local[
            (e15_df_local["compiler"] == "qiskit") &
            (e15_df_local["compiler_opt_level"].isin(["1", "2", "3"]))
        ]
        family_map = {"CNOT": "CNOT_chain", "QFT": "QFT", "Oracle": "Oracle",
                       "GHZ": "GHZ", "RandomClifford": "RandomClifford"}
        e15_qiskit = e15_qiskit.copy()
        e15_qiskit["family_mapped"] = e15_qiskit["circuit_family"].map(family_map)

        for idx, fam in enumerate(present_families):
            fam_data = e15_qiskit[e15_qiskit["family_mapped"] == fam]
            if len(fam_data) > 0:
                full_val = fam_data["reduction"].max() * 100
                if full_val > 0.5:  # Only draw if meaningful
                    ax.plot([idx - 0.4, idx + 0.4 + (n_pass - 1) * width],
                            [full_val, full_val],
                            color="#6A4C93", linewidth=2.5, linestyle="--",
                            alpha=0.9, zorder=10)

        # Add legend entry for the reference line
        ax.plot([], [], color="#6A4C93", linewidth=2.5, linestyle="--",
                label="Qiskit Full Pipeline (best opt 1-3)", alpha=0.9)

    ax.axhline(y=0, color="red", linestyle="--", linewidth=1, alpha=0.5)
    ax.set_xlabel("Circuit Family", fontsize=12)
    ax.set_ylabel("Mean Gate Reduction (%)", fontsize=12)
    ax.set_title(
        "Figure 15: Qiskit Pass Isolation — Individual Pass Effectiveness\n"
        "per Circuit Family (dashed line = Qiskit full pipeline, opt level 3)",
        fontsize=13,
    )
    ax.set_xticks(x + width * (n_pass - 1) / 2)
    ax.set_xticklabels(
        [FAMILY_DISPLAY_NAMES.get(f, f) for f in present_families],
        fontsize=10,
    )
    ax.legend(fontsize=9, loc="upper left", framealpha=0.9)

    # Annotate the gap
    ax.text(
        0.98, 0.02,
        "Gap between isolated passes and full pipeline\n"
        "reveals synergy from template matching, routing,\n"
        "and phase polynomial optimization.",
        transform=ax.transAxes, fontsize=9, verticalalignment="bottom",
        horizontalalignment="right",
        bbox=dict(boxstyle="round,pad=0.5", facecolor="#FFFACD",
                  edgecolor="#B8860B", alpha=0.9),
    )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig15_qiskit_pass_waterfall.png",
                dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "fig15_qiskit_pass_waterfall.pdf",
                bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / 'fig15_qiskit_pass_waterfall.png'}")


def generate_fig16_heatmap(pass_df: pd.DataFrame) -> None:
    """Figure 16: Heatmap of pass effectiveness per circuit family.

    Rows = circuit families, columns = individual passes.
    Cell value = mean gate reduction (%).
    """
    print("Generating Figure 16: Pass-Family Heatmap...")

    matrix = compute_family_pass_matrix(pass_df)

    # Rename columns and index for display
    col_labels = [PASS_DISPLAY_NAMES.get(c, c).replace("\n", " ") for c in matrix.columns]
    row_labels = [FAMILY_DISPLAY_NAMES.get(r, r).replace("\n", " ") for r in matrix.index]

    fig, ax = plt.subplots(figsize=(10, 6))
    sns.heatmap(
        matrix.values * 100,
        annot=True, fmt=".1f",
        cmap="YlOrRd",
        linewidths=0.8, linecolor="white",
        cbar_kws={"label": "Mean Gate Reduction (%)"},
        ax=ax,
        xticklabels=col_labels,
        yticklabels=row_labels,
        vmin=0,
    )

    ax.set_xlabel("Transpiler Pass", fontsize=12)
    ax.set_ylabel("Circuit Family", fontsize=12)
    ax.set_title(
        "Figure 16: Pass Effectiveness Heatmap\n"
        "Mean gate reduction (%) per circuit family per individual pass",
        fontsize=13,
    )
    plt.xticks(fontsize=10, rotation=0)
    plt.yticks(fontsize=10, rotation=0)

    # Add annotation box
    ax.text(
        0.5, -0.12,
        "Key finding: CommutativeCancellation matches our Phase 2 on Oracle/RandomClifford "
        "but both miss QFT/GHZ.\nNeither isolated pass explains the full-pipeline advantage "
        "(template matching + routing + phase polynomial).",
        transform=ax.transAxes, fontsize=9,
        horizontalalignment="center", verticalalignment="top",
        bbox=dict(boxstyle="round,pad=0.4", facecolor="lightyellow", alpha=0.8),
    )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig16_qiskit_pass_family_heatmap.png",
                dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "fig16_qiskit_pass_family_heatmap.pdf",
                bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / 'fig16_qiskit_pass_family_heatmap.png'}")


def generate_fig17_interaction(pass_df: pd.DataFrame) -> None:
    """Figure 17: Interaction matrix between passes.

    Two-panel figure:
      Left: Synergy score (mean absolute difference in reduction between passes)
      Right: Co-benefit score (fraction of circuits where both passes help)
    """
    print("Generating Figure 17: Pass Interaction Matrix...")

    synergy, cobenefit = compute_interaction_matrix(pass_df)

    pass_labels = [PASS_DISPLAY_NAMES.get(p, p).replace("\n", " ") for p in synergy.index]

    fig, axes = plt.subplots(1, 2, figsize=(14, 6))

    # Left: Synergy (divergence) matrix
    sns.heatmap(
        synergy.values * 100,
        annot=True, fmt=".1f",
        cmap="Blues",
        linewidths=0.8, linecolor="white",
        cbar_kws={"label": "Mean |Difference| in Reduction (%)"},
        ax=axes[0],
        xticklabels=pass_labels,
        yticklabels=pass_labels,
        vmin=0,
    )
    axes[0].set_title("Pass Divergence Matrix\n"
                       "(higher = more complementary mechanisms)", fontsize=11)
    axes[0].set_xlabel("Pass", fontsize=10)
    axes[0].set_ylabel("Pass", fontsize=10)
    axes[0].tick_params(axis="x", rotation=25)
    axes[0].tick_params(axis="y", rotation=0)

    # Right: Co-benefit matrix
    sns.heatmap(
        cobenefit.values,
        annot=True, fmt=".2f",
        cmap="Greens",
        linewidths=0.8, linecolor="white",
        cbar_kws={"label": "Co-benefit Fraction"},
        ax=axes[1],
        xticklabels=pass_labels,
        yticklabels=pass_labels,
        vmin=0, vmax=1,
    )
    axes[1].set_title("Pass Co-benefit Matrix\n"
                       "(fraction of circuits where both passes achieve > 0 reduction)",
                       fontsize=11)
    axes[1].set_xlabel("Pass", fontsize=10)
    axes[1].set_ylabel("Pass", fontsize=10)
    axes[1].tick_params(axis="x", rotation=25)
    axes[1].tick_params(axis="y", rotation=0)

    fig.suptitle(
        "Figure 17: Pass Interaction Analysis\n"
        "Divergence reveals complementary vs. redundant optimization mechanisms",
        fontsize=13, y=1.02,
    )

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / "fig17_qiskit_pass_interaction.png",
                dpi=300, bbox_inches="tight")
    plt.savefig(OUTPUT_DIR / "fig17_qiskit_pass_interaction.pdf",
                bbox_inches="tight")
    plt.close()
    print(f"  Saved: {OUTPUT_DIR / 'fig17_qiskit_pass_interaction.png'}")


# ===================================================================
# Summary CSV generation
# ===================================================================

def save_summary_csv(pass_df: pd.DataFrame,
                      effectiveness: pd.DataFrame,
                      gap_df: pd.DataFrame) -> None:
    """Save comprehensive analysis summary to CSV."""
    summary_rows = []

    # Section 1: Per-pass effectiveness
    for _, row in effectiveness.iterrows():
        summary_rows.append({
            "section": "pass_effectiveness",
            "pass_name": row["pass_name"],
            "compiler": row["compiler"],
            "metric": "mean_reduction",
            "value": row["mean_reduction"],
            "circuit_family": "all",
        })
        summary_rows.append({
            "section": "pass_effectiveness",
            "pass_name": row["pass_name"],
            "compiler": row["compiler"],
            "metric": "std_reduction",
            "value": row["std_reduction"],
            "circuit_family": "all",
        })
        summary_rows.append({
            "section": "pass_effectiveness",
            "pass_name": row["pass_name"],
            "compiler": row["compiler"],
            "metric": "best_family_reduction",
            "value": row["best_family_reduction"],
            "circuit_family": row["best_family"],
        })

    # Section 2: Per-family per-pass breakdown
    for (fam, pname), grp in pass_df.groupby(["circuit_family", "pass_name"]):
        summary_rows.append({
            "section": "family_pass_breakdown",
            "pass_name": pname,
            "compiler": grp["compiler"].iloc[0],
            "metric": "mean_reduction",
            "value": grp["reduction"].mean(),
            "circuit_family": fam,
        })

    # Section 3: Gap analysis
    if len(gap_df) > 0:
        for _, row in gap_df.iterrows():
            for metric in ["our_best_reduction", "qiskit_full_pipeline",
                            "gap", "CC_reduction", "Opt1q_reduction",
                            "gap_frac_CC", "gap_frac_Opt1q",
                            "gap_frac_unexplained"]:
                summary_rows.append({
                    "section": "gap_analysis",
                    "pass_name": "N/A",
                    "compiler": "N/A",
                    "metric": metric,
                    "value": row[metric],
                    "circuit_family": row["circuit_family"],
                })

    summary_df = pd.DataFrame(summary_rows)
    out_path = OUTPUT_DIR / "qiskit_pass_analysis_summary.csv"
    summary_df.to_csv(out_path, index=False)
    print(f"  Saved summary: {out_path}")


# ===================================================================
# Main
# ===================================================================

def main() -> None:
    """Run the full Qiskit pass isolation analysis."""
    print("=" * 60)
    print("QISKIT PASS ISOLATION DEEP ANALYSIS")
    print("=" * 60)

    # Load data
    pass_df, e15_df = load_data()

    # Compute analyses
    print("\nComputing pass effectiveness...")
    effectiveness = compute_pass_effectiveness(pass_df)
    print(effectiveness.to_string(index=False))

    print("\nComputing family-pass matrix...")
    family_matrix = compute_family_pass_matrix(pass_df)
    print(family_matrix.to_string())

    print("\nComputing interaction matrix...")
    synergy, cobenefit = compute_interaction_matrix(pass_df)
    print("\nSynergy (divergence):")
    print(synergy.to_string())
    print("\nCo-benefit:")
    print(cobenefit.to_string())

    print("\nComputing gap analysis...")
    gap_df = compute_qiskit_gap_analysis(pass_df, e15_df)
    if len(gap_df) > 0:
        print(gap_df.to_string(index=False))

    # Generate figures
    print("\n" + "=" * 60)
    print("GENERATING FIGURES")
    print("=" * 60)

    generate_fig15_waterfall(pass_df, e15_df)
    generate_fig16_heatmap(pass_df)
    generate_fig17_interaction(pass_df)

    # Save summary
    print("\nSaving summary CSV...")
    save_summary_csv(pass_df, effectiveness, gap_df)

    print("\n" + "=" * 60)
    print("ANALYSIS COMPLETE")
    print("=" * 60)
    print(f"Output directory: {OUTPUT_DIR}")
    for f in sorted(OUTPUT_DIR.glob("fig1[567]*.png")):
        print(f"  - {f.name}")
    print(f"  - qiskit_pass_analysis_summary.csv")


if __name__ == "__main__":
    main()
