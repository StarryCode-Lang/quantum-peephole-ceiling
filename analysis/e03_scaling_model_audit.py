"""Bounded model comparison, bootstrap CIs, and held-out-size scaling audit for E03."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/v10/prepaper/e03/e03_scaling_v2_20260810_033256_revalidated.csv"
DEFAULT_OUTPUT = ROOT / "data/v10/prepaper/e03/e03_scaling_model_audit.json"
MODELS = ("quadratic_polynomial", "exponential", "piecewise_linear_hinge")
SEED = 310026


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _aicc(y: np.ndarray, predicted: np.ndarray, parameters: int) -> float:
    n = len(y)
    sse = max(float(np.sum((y - predicted) ** 2)), np.finfo(float).tiny)
    aic = n * np.log(sse / n) + 2 * parameters
    return float(aic + 2 * parameters * (parameters + 1) / (n - parameters - 1))


def _fit(model: str, x: np.ndarray, y: np.ndarray) -> dict[str, object]:
    if model == "quadratic_polynomial":
        matrix = np.column_stack((np.ones_like(x), x, x**2))
        coefficients = np.linalg.lstsq(matrix, y, rcond=None)[0]
        predicted = matrix @ coefficients
        return {"coefficients": coefficients, "aicc": _aicc(y, predicted, 3)}
    if model == "exponential":
        coefficients = np.linalg.lstsq(
            np.column_stack((np.ones_like(x), x)), np.log(y), rcond=None
        )[0]
        predicted = np.exp(coefficients[0] + coefficients[1] * x)
        return {"coefficients": coefficients, "aicc": _aicc(y, predicted, 2)}
    if model == "piecewise_linear_hinge":
        candidates = sorted(set(map(float, x)))[1:-1]
        fits: list[dict[str, object]] = []
        for breakpoint in candidates:
            matrix = np.column_stack((np.ones_like(x), x, np.maximum(0.0, x - breakpoint)))
            coefficients = np.linalg.lstsq(matrix, y, rcond=None)[0]
            predicted = matrix @ coefficients
            fits.append(
                {
                    "coefficients": coefficients,
                    "breakpoint": breakpoint,
                    "aicc": _aicc(y, predicted, 4),
                }
            )
        return min(fits, key=lambda item: item["aicc"])
    raise ValueError(model)


def _predict(model: str, fit: dict[str, object], x: np.ndarray) -> np.ndarray:
    coefficients = np.asarray(fit["coefficients"], dtype=float)
    if model == "quadratic_polynomial":
        return coefficients[0] + coefficients[1] * x + coefficients[2] * x**2
    if model == "exponential":
        return np.exp(coefficients[0] + coefficients[1] * x)
    breakpoint = float(fit["breakpoint"])
    return coefficients[0] + coefficients[1] * x + coefficients[2] * np.maximum(0.0, x - breakpoint)


def _quantiles(values: list[float]) -> dict[str, float]:
    q = np.quantile(np.asarray(values), [0.025, 0.5, 0.975])
    return {"q025": float(q[0]), "median": float(q[1]), "q975": float(q[2])}


def _load_grid() -> tuple[np.ndarray, np.ndarray, dict[int, np.ndarray]]:
    with SOURCE.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != 12000:
        raise RuntimeError("unexpected E03 row count")
    by_size_trial: dict[int, dict[int, list[float]]] = {}
    for row in rows:
        size = int(row["n_qubits"])
        trial = int(row["trial"])
        by_size_trial.setdefault(size, {}).setdefault(trial, []).append(float(row["runtime_seconds"]))
    sizes = np.asarray(sorted(by_size_trial), dtype=float)
    if list(map(int, sizes)) != list(range(3, 11)):
        raise RuntimeError("unexpected E03 qubit-size grid")
    trial_arrays: dict[int, np.ndarray] = {}
    means: list[float] = []
    for size in map(int, sizes):
        trials = by_size_trial[size]
        if sorted(trials) != list(range(50)) or {len(values) for values in trials.values()} != {30}:
            raise RuntimeError("E03 is not the expected 50-trial by 30-depth balanced grid")
        array = np.asarray([trials[trial] for trial in range(50)], dtype=float)
        trial_arrays[size] = array
        means.append(float(np.mean(array)))
    return sizes, np.asarray(means), trial_arrays


def build_audit(bootstrap_replicates: int = 2000) -> dict[str, object]:
    sizes, means, trial_arrays = _load_grid()
    observed = {str(int(size)): float(mean) for size, mean in zip(sizes, means)}
    fits: dict[str, dict[str, object]] = {}
    for model in MODELS:
        fit = _fit(model, sizes, means)
        fits[model] = {
            "aicc": float(fit["aicc"]),
            "coefficients": list(map(float, fit["coefficients"])),
            "breakpoint": fit.get("breakpoint"),
        }

    loocv: dict[str, float] = {}
    for model in MODELS:
        errors: list[float] = []
        for index in range(len(sizes)):
            keep = np.arange(len(sizes)) != index
            prediction = float(_predict(model, _fit(model, sizes[keep], means[keep]), sizes[index : index + 1])[0])
            errors.append((prediction - means[index]) ** 2)
        loocv[model] = float(np.sqrt(np.mean(errors)))

    train = sizes < 10
    out_of_range: dict[str, dict[str, object]] = {}
    for model in MODELS:
        fit = _fit(model, sizes[train], means[train])
        prediction = float(_predict(model, fit, np.asarray([10.0]))[0])
        out_of_range[model] = {
            "trained_sizes": list(map(int, sizes[train])),
            "held_out_size": 10,
            "predicted_mean_wall_runtime_seconds": prediction,
            "observed_mean_wall_runtime_seconds": float(means[-1]),
            "absolute_error_seconds": abs(prediction - float(means[-1])),
        }

    rng = np.random.RandomState(SEED)
    prediction_draws = {model: {str(int(size)): [] for size in sizes} for model in MODELS}
    extrapolation_draws = {model: [] for model in MODELS}
    coefficient_draws = {model: [] for model in MODELS}
    breakpoint_draws: list[float] = []
    observed_mean_draws = {str(int(size)): [] for size in sizes}
    for _ in range(bootstrap_replicates):
        sampled_trials = rng.randint(0, 50, size=50)
        boot_means = np.asarray(
            [np.mean(trial_arrays[int(size)][sampled_trials, :]) for size in sizes], dtype=float
        )
        for size, value in zip(sizes, boot_means):
            observed_mean_draws[str(int(size))].append(float(value))
        for model in MODELS:
            full_fit = _fit(model, sizes, boot_means)
            coefficient_draws[model].append(list(map(float, full_fit["coefficients"])))
            if model == "piecewise_linear_hinge":
                breakpoint_draws.append(float(full_fit["breakpoint"]))
            for size, value in zip(sizes, _predict(model, full_fit, sizes)):
                prediction_draws[model][str(int(size))].append(float(value))
            heldout_fit = _fit(model, sizes[train], boot_means[train])
            extrapolation_draws[model].append(
                float(_predict(model, heldout_fit, np.asarray([10.0]))[0])
            )

    for model in MODELS:
        coefficients = np.asarray(coefficient_draws[model], dtype=float)
        fits[model]["bootstrap_coefficient_ci95"] = [
            _quantiles(list(coefficients[:, index])) for index in range(coefficients.shape[1])
        ]
        fits[model]["fitted_mean_runtime_ci95_by_n_qubits"] = {
            size: _quantiles(values) for size, values in prediction_draws[model].items()
        }
        out_of_range[model]["bootstrap_mean_prediction_ci95"] = _quantiles(extrapolation_draws[model])
    fits["piecewise_linear_hinge"]["bootstrap_selected_breakpoint_counts"] = {
        str(int(value)): int(count)
        for value, count in zip(*np.unique(np.asarray(breakpoint_draws), return_counts=True))
    }

    best_loocv = min(loocv, key=loocv.get)
    best_aicc = min(fits, key=lambda model: fits[model]["aicc"])
    return {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_BOUNDED_SCALING_MODEL_CI_AND_EXTRAPOLATION_AUDIT",
        "source": SOURCE.relative_to(ROOT).as_posix(),
        "source_sha256": _sha256(SOURCE),
        "estimand": "mean wall runtime over the fixed balanced 30-depth grid at each qubit count",
        "rows": 12000,
        "n_qubit_levels": list(map(int, sizes)),
        "trials_per_size_depth_cell": 50,
        "depth_levels": 30,
        "observed_mean_wall_runtime_seconds_by_n_qubits": observed,
        "observed_mean_bootstrap_ci95_by_n_qubits": {
            size: _quantiles(values) for size, values in observed_mean_draws.items()
        },
        "bootstrap": {
            "replicates": bootstrap_replicates,
            "seed": SEED,
            "unit": "paired trial index with all 30 depth levels retained at every qubit size",
        },
        "models": fits,
        "model_comparison": {
            "loocv_rmse_seconds": loocv,
            "best_by_loocv": best_loocv,
            "best_by_aicc": best_aicc,
            "selection_agrees": best_loocv == best_aicc,
        },
        "out_of_range_extrapolation": out_of_range,
        "phase_transition_assessment": (
            "NO_DISCONTINUOUS_PHASE_TRANSITION_CLAIM_LICENSED: the eight-size wall-time series is "
            "non-monotone and timer-quantized; smooth and continuous-hinge comparisons plus one "
            "held-out largest size can diagnose model fragility but cannot establish a universal transition."
        ),
        "limitations": [
            "Wall time, not CPU time, memory, energy, or component-level timing, is available.",
            "Only eight qubit sizes (3 through 10) are observed, so model selection and extrapolation are bounded diagnostics.",
            "Bootstrap intervals quantify paired-trial uncertainty over the fixed depth grid and do not represent new circuit-family uncertainty.",
            "The held-out n=10 check is one-step extrapolation, not evidence for asymptotic behavior.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--bootstrap-replicates", type=int, default=2000)
    args = parser.parse_args()
    output = args.output if args.output.is_absolute() else ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = build_audit(args.bootstrap_replicates)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"output": output.relative_to(ROOT).as_posix(), "status": payload["status"]}, sort_keys=True))


if __name__ == "__main__":
    main()
