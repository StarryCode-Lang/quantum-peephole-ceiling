"""Generate the sealed E31 budget-response AUC and validity-runtime frontier."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/v11/e31_factorial_pareto/formal_run/final/formal_results.csv"
DEFAULT_OUTPUT_DIR = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/validity_runtime_frontier"
SEED = 951032
BUDGETS = [1, 10, 30, 120]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _artifact_path(path: Path) -> str:
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _ci(values: list[float]) -> tuple[float, float]:
    q = np.quantile(np.asarray(values), [0.025, 0.975])
    return float(q[0]), float(q[1])


def derive(output_dir: Path = DEFAULT_OUTPUT_DIR, bootstrap_replicates: int = 2000) -> dict[str, object]:
    frame = pd.read_csv(SOURCE)
    if len(frame) != 28152 or sorted(frame["budget_seconds"].unique().tolist()) != BUDGETS:
        raise RuntimeError("unexpected sealed E31 budget grid")
    frame["valid"] = frame["status"].eq("success").astype(float)
    frame["itt_reduction_pp"] = np.where(
        frame["status"].eq("success"), frame["common_basis_gate_reduction_pct"], 0.0
    )
    per_input = frame.groupby(["input_circuit_sha256", "budget_seconds"], as_index=False).agg(
        validity_rate=("valid", "mean"),
        itt_mean_reduction_pp=("itt_reduction_pp", "mean"),
    )
    if len(per_input) != 391 * 4:
        raise RuntimeError("incomplete input-by-budget frontier grid")

    rng = np.random.RandomState(SEED)
    inputs = sorted(per_input["input_circuit_sha256"].unique())
    input_index = {value: index for index, value in enumerate(inputs)}
    validity_matrix = np.empty((391, 4), dtype=float)
    reduction_matrix = np.empty((391, 4), dtype=float)
    for row in per_input.itertuples(index=False):
        left = input_index[row.input_circuit_sha256]
        right = BUDGETS.index(int(row.budget_seconds))
        validity_matrix[left, right] = row.validity_rate
        reduction_matrix[left, right] = row.itt_mean_reduction_pp
    validity_draws = [[] for _ in BUDGETS]
    reduction_draws = [[] for _ in BUDGETS]
    for _ in range(bootstrap_replicates):
        sampled = rng.randint(0, 391, size=391)
        for index in range(4):
            validity_draws[index].append(float(validity_matrix[sampled, index].mean()))
            reduction_draws[index].append(float(reduction_matrix[sampled, index].mean()))

    rows: list[dict[str, object]] = []
    for index, budget in enumerate(BUDGETS):
        subset = frame.loc[frame["budget_seconds"].eq(budget)]
        valid_ci = _ci(validity_draws[index])
        reduction_ci = _ci(reduction_draws[index])
        rows.append(
            {
                "budget_seconds": budget,
                "rows": int(len(subset)),
                "success_rows": int(subset["valid"].sum()),
                "validity_rate": float(subset["valid"].mean()),
                "validity_cluster_bootstrap_ci95_low": valid_ci[0],
                "validity_cluster_bootstrap_ci95_high": valid_ci[1],
                "mean_wall_seconds_end_to_end": float(subset["wall_seconds_end_to_end"].mean()),
                "median_wall_seconds_end_to_end": float(subset["wall_seconds_end_to_end"].median()),
                "p95_wall_seconds_end_to_end": float(subset["wall_seconds_end_to_end"].quantile(0.95)),
                "itt_mean_reduction_pp": float(subset["itt_reduction_pp"].mean()),
                "itt_reduction_cluster_bootstrap_ci95_low_pp": reduction_ci[0],
                "itt_reduction_cluster_bootstrap_ci95_high_pp": reduction_ci[1],
            }
        )
    frontier = pd.DataFrame(rows)
    nondominated = []
    for index, row in frontier.iterrows():
        dominated = False
        for other_index, other in frontier.iterrows():
            if other_index == index:
                continue
            no_worse = (
                other["mean_wall_seconds_end_to_end"] <= row["mean_wall_seconds_end_to_end"]
                and other["validity_rate"] >= row["validity_rate"]
                and other["itt_mean_reduction_pp"] >= row["itt_mean_reduction_pp"]
            )
            strictly_better = (
                other["mean_wall_seconds_end_to_end"] < row["mean_wall_seconds_end_to_end"]
                or other["validity_rate"] > row["validity_rate"]
                or other["itt_mean_reduction_pp"] > row["itt_mean_reduction_pp"]
            )
            if no_worse and strictly_better:
                dominated = True
                break
        nondominated.append(not dominated)
    frontier["pareto_nondominated"] = nondominated

    log_budget = np.log10(frontier["budget_seconds"].to_numpy(dtype=float))
    width = float(log_budget[-1] - log_budget[0])
    validity_auc = float(np.trapz(frontier["validity_rate"], log_budget) / width)
    reduction_auc = float(np.trapz(frontier["itt_mean_reduction_pp"], log_budget) / width)

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "frontier_by_budget.csv"
    json_path = output_dir / "frontier_audit.json"
    png_path = output_dir / "validity_runtime_frontier.png"
    pdf_path = output_dir / "validity_runtime_frontier.pdf"
    frontier.to_csv(csv_path, index=False)

    fig, axes = plt.subplots(1, 2, figsize=(11.5, 4.6), constrained_layout=True)
    x = frontier["mean_wall_seconds_end_to_end"].to_numpy(dtype=float)
    validity = frontier["validity_rate"].to_numpy(dtype=float)
    validity_low = validity - frontier["validity_cluster_bootstrap_ci95_low"].to_numpy(dtype=float)
    validity_high = frontier["validity_cluster_bootstrap_ci95_high"].to_numpy(dtype=float) - validity
    reduction = frontier["itt_mean_reduction_pp"].to_numpy(dtype=float)
    reduction_low = reduction - frontier["itt_reduction_cluster_bootstrap_ci95_low_pp"].to_numpy(dtype=float)
    reduction_high = frontier["itt_reduction_cluster_bootstrap_ci95_high_pp"].to_numpy(dtype=float) - reduction
    axes[0].errorbar(x, validity, yerr=[validity_low, validity_high], marker="o", capsize=3)
    axes[1].errorbar(x, reduction, yerr=[reduction_low, reduction_high], marker="o", capsize=3)
    for axis, yvalues in ((axes[0], validity), (axes[1], reduction)):
        for xvalue, yvalue, budget in zip(x, yvalues, BUDGETS):
            axis.annotate(f"{budget}s", (xvalue, yvalue), xytext=(5, 5), textcoords="offset points")
        axis.grid(alpha=0.25)
        axis.set_xlabel("Mean end-to-end wall time (s)")
    axes[0].set_ylabel("Valid-output rate")
    axes[0].set_title("Validity–runtime frontier")
    axes[1].set_ylabel("ITT mean gate reduction (pp)")
    axes[1].set_title("Quality–runtime frontier")
    fig.suptitle("E31 sealed fixed-panel budget response (input-cluster 95% CIs)")
    fig.savefig(png_path, dpi=300)
    fig.savefig(pdf_path)
    plt.close(fig)

    payload = {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_E31_VALIDITY_RUNTIME_FRONTIER_AND_BUDGET_AUC_COMPLETE",
        "source_sha256": _sha256(SOURCE),
        "formal_rows": len(frame),
        "budgets_seconds": BUDGETS,
        "bootstrap": {
            "replicates": bootstrap_replicates,
            "seed": SEED,
            "unit": "input circuit hash across the complete factorial grid within budget",
        },
        "frontier_csv": _artifact_path(csv_path),
        "frontier_csv_sha256": _sha256(csv_path),
        "figure_png": _artifact_path(png_path),
        "figure_png_sha256": _sha256(png_path),
        "figure_pdf": _artifact_path(pdf_path),
        "figure_pdf_sha256": _sha256(pdf_path),
        "log10_budget_normalized_auc": {
            "validity_rate": validity_auc,
            "itt_mean_reduction_pp": reduction_auc,
        },
        "pareto_nondominated_budgets_seconds": list(
            map(int, frontier.loc[frontier["pareto_nondominated"], "budget_seconds"])
        ),
        "interpretation": (
            "This is a four-point independent-budget response profile over the sealed fixed panel. "
            "It is a reproducible anytime-style AUC proxy, not a within-run incumbent trajectory."
        ),
        "limitations": [
            "The profile cannot identify time-to-first-valid or time-to-best within a run.",
            "Wall time includes orchestration overhead and is not CPU time.",
            "AUC uses log10 budget spacing and is descriptive for the four frozen budgets only.",
        ],
    }
    json_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    args = parser.parse_args()
    output = args.output_dir if args.output_dir.is_absolute() else ROOT / args.output_dir
    payload = derive(output, args.bootstrap_replicates)
    print(json.dumps({"output": (output / "frontier_audit.json").relative_to(ROOT).as_posix(), "status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
