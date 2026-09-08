"""Generate the README overview from receipt-bound v13/v14 evidence."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "docs" / "assets" / "v14-overview.png"


def load_json(relative_path: str) -> dict:
    return json.loads((ROOT / relative_path).read_text(encoding="utf-8"))


def main() -> None:
    v13 = load_json("docs/review/v13_stage5_e45_receipt.json")
    screening = load_json("data/v14/e45_development_grid/receipt.json")
    exact = load_json("data/v14/e45_full_development/receipt.json")
    idastar = load_json("data/v14/e45_idastar_escape/receipt.json")
    verdict = load_json("release/v14_readiness_verdict.json")

    total_configs = int(screening["configuration_count"])
    eligible_v13 = int(
        v13["resource_gate"]["certificate_guided_escape_eligible_configurations"]
    )
    eligible_v14 = int(screening["selection"]["eligible_config_count"])

    v13_rate = 100 * float(
        v13["resource_gate"]["certificate_guided_escape_max_observed_failure_rate"]
    )
    v14_rate = 100 * float(
        verdict["blocking_evidence"]["guided_resource_or_error_rate_max"]
    )
    threshold = 100 * float(v13["resource_gate"]["required_max_failure_rate"])

    exact_total = int(exact["source_count"])
    exact_bounded = int(exact["guided_summary"]["resource_bounded_count"])
    exact_complete = exact_total - exact_bounded

    ida_total = int(idastar["source_count"])
    ida_escape = int(idastar["summary"]["exact_count"])
    ida_bounded = int(idastar["summary"]["resource_bounded_count"])
    ida_local = ida_total - ida_escape - ida_bounded

    colors = {
        "navy": "#17324D",
        "blue": "#2F6690",
        "teal": "#2A9D8F",
        "gold": "#E9C46A",
        "coral": "#E76F51",
        "paper": "#F7F8FA",
        "grid": "#D7DEE7",
    }

    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 11,
            "axes.titleweight": "bold",
            "axes.edgecolor": colors["grid"],
            "axes.labelcolor": colors["navy"],
            "xtick.color": colors["navy"],
            "ytick.color": colors["navy"],
        }
    )
    fig, axes = plt.subplots(1, 3, figsize=(15, 5.4), facecolor=colors["paper"])
    fig.subplots_adjust(left=0.06, right=0.98, top=0.78, bottom=0.17, wspace=0.34)
    fig.suptitle(
        "v14 certified-search evidence at a glance",
        x=0.06,
        y=0.94,
        ha="left",
        fontsize=22,
        fontweight="bold",
        color=colors["navy"],
    )
    fig.text(
        0.06,
        0.865,
        "Same 128-source screening panel; historical v13 evidence remains frozen.",
        ha="left",
        fontsize=11.5,
        color=colors["blue"],
    )

    ax = axes[0]
    bars = ax.bar(
        ["v13", "v14"],
        [eligible_v13, eligible_v14],
        color=[colors["coral"], colors["teal"]],
        width=0.58,
    )
    ax.set_title("Screening configurations\nmeeting the resource gate", loc="left")
    ax.set_ylim(0, total_configs + 3)
    ax.set_ylabel(f"Eligible configurations (of {total_configs})")
    ax.grid(axis="y", color=colors["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, [eligible_v13, eligible_v14], strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 0.5,
            f"{value}/{total_configs}",
            ha="center",
            va="bottom",
            fontsize=15,
            fontweight="bold",
            color=colors["navy"],
        )

    ax = axes[1]
    rate_bars = ax.bar(
        ["v13", "v14"],
        [v13_rate, v14_rate],
        color=[colors["coral"], colors["teal"]],
        width=0.58,
    )
    ax.axhline(
        threshold,
        color=colors["gold"],
        linewidth=2,
        linestyle="--",
        label=f"gate: {threshold:.0f}%",
    )
    ax.set_title("Maximum guided resource\nor error rate", loc="left")
    ax.set_ylabel("Rate (%) — lower is better")
    ax.set_ylim(0, max(v13_rate * 1.25, 10))
    ax.grid(axis="y", color=colors["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.legend(frameon=False, loc="upper right")
    for bar, value in zip(rate_bars, [v13_rate, v14_rate], strict=True):
        ax.text(
            bar.get_x() + bar.get_width() / 2,
            value + 1.2,
            f"{value:.2f}%",
            ha="center",
            va="bottom",
            fontsize=13,
            fontweight="bold",
            color=colors["navy"],
        )

    ax = axes[2]
    labels = ["Exact finite\nhorizon", "IDA* escape\ndepth"]
    first = [exact_complete, ida_escape]
    second = [exact_bounded, ida_local]
    ax.barh(labels, first, color=[colors["teal"], colors["blue"]], label="Exact result")
    ax.barh(
        labels,
        second,
        left=first,
        color=[colors["gold"], colors["navy"]],
        label="Boundary / local optimum",
    )
    ax.set_title("Selected 128-input\ndevelopment panel", loc="left")
    ax.set_xlim(0, 128)
    ax.set_xlabel("Inputs")
    ax.grid(axis="x", color=colors["grid"], linewidth=0.8)
    ax.set_axisbelow(True)
    ax.text(exact_complete / 2, 0, str(exact_complete), ha="center", va="center", color="white", fontweight="bold")
    ax.text(exact_complete + exact_bounded / 2, 0, str(exact_bounded), ha="center", va="center", color=colors["navy"], fontweight="bold")
    ax.text(ida_escape / 2, 1, str(ida_escape), ha="center", va="center", color="white", fontweight="bold")
    ax.text(ida_escape + ida_local / 2, 1, str(ida_local), ha="center", va="center", color="white", fontweight="bold")
    ax.text(
        0,
        -0.37,
        "Exact: 93  |  Resource-truncated: 35\nIDA*: 63 escapes  |  65 H-local optima",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9.5,
        color=colors["blue"],
    )

    for axis in axes:
        axis.set_facecolor(colors["paper"])
        axis.spines[["top", "right"]].set_visible(False)

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUTPUT, dpi=180, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    print(f"wrote {OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
