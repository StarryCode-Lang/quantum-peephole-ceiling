#!/usr/bin/env python3
"""Generate fig18: E30 direct validation of the corrected Theorem 1(a).

Reads the E30 canonical dataset and its derived per-cell summary, then plots
empirical mean adjacent-inverse-pair counts against the corrected theoretical
prediction for all 27 (n, d, rho) cells.

Output: analysis/figures/fig18_e30_thm1a_validation.pdf
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

CELL_CSV = PROJECT_ROOT / "data/v10/e30/derived/e30_thm1a_cell_summary.csv"
OUT_PDF = PROJECT_ROOT / "analysis/figures/fig18_e30_thm1a_validation.pdf"


def main() -> int:
    df = pd.read_csv(CELL_CSV)
    df = df.sort_values(["rho", "n_qubits", "depth"])

    fig, ax = plt.subplots(figsize=(5.2, 4.6))

    colors = {0.0: "#4c72b0", 0.3: "#dd8452", 0.6: "#55a868"}
    markers = {4: "o", 5: "s", 8: "^"}

    for _, row in df.iterrows():
        ax.scatter(row["theory_a_adj"], row["mean_a_adj"],
                   c=colors[row["rho"]], marker=markers[int(row["n_qubits"])],
                   s=34, alpha=0.9, edgecolors="k", linewidths=0.4)

    lim = max(df["theory_a_adj"].max(), df["mean_a_adj"].max()) * 1.12
    ax.plot([0, lim], [0, lim], "k--", linewidth=0.9, label="y = x (theory)")

    for rho, c in colors.items():
        ax.scatter([], [], c=c, s=30, edgecolors="k", linewidths=0.4,
                   label=rf"$\rho = {rho}$")
    for n, m in markers.items():
        ax.scatter([], [], c="0.65", marker=m, s=30, label=f"n = {n}")

    ax.set_xlabel(r"Theory: $\mathbb{E}[|\mathcal{A}_{\mathrm{adj}}|]$ (corrected Thm 1a)")
    ax.set_ylabel(r"Empirical mean of $|\mathcal{A}_{\mathrm{adj}}|$ (500 trials/cell)")
    ax.set_xlim(0, lim)
    ax.set_ylim(0, lim)
    ax.set_aspect("equal", adjustable="box")
    ax.text(0.03, 0.965,
            "E30: 27 cells, 13,500 trials\nmax $|z|$ = 2.86, median rel. err. = 1.4%",
            transform=ax.transAxes, fontsize=8.5, va="top", ha="left",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="0.7", lw=0.6))
    ax.legend(loc="lower right", fontsize=7.5, framealpha=0.9, ncol=1,
              handletextpad=0.4, borderpad=0.5)
    ax.grid(True, linewidth=0.4, alpha=0.5)
    ax.tick_params(labelsize=9)

    fig.tight_layout()
    OUT_PDF.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT_PDF, bbox_inches="tight")
    print(f"Wrote {OUT_PDF}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
