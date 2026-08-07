"""Mechanism-based monotone analysis for the RepetitionCode LOFO failure.

The analysis treats ``2 * phase1_action_density`` as a mechanism-derived
reduction lower bound when the extracted opportunities are non-overlapping.
It verifies that bound on the existing E21/E27 evidence and compares it with
one-dimensional isotonic regression. The script does not promote either rule
to a universal theorem; it records violations if a future dataset breaks the
certificate assumptions.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import mean_absolute_error

PROJECT_ROOT = Path(__file__).resolve().parents[1]
E21_CSV = PROJECT_ROOT / "data" / "v6" / "e21" / "ceiling_aware_comparison.csv"
E21_FEATURES_CSV = PROJECT_ROOT / "data" / "v6" / "ceiling_repair" / "mechanism_features.csv"
E27_FEATURES_CSV = PROJECT_ROOT / "data" / "v6" / "ceiling_repair" / "part5_e27_features.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "v6" / "ceiling_repair"


def phase1_lower_bound(action_density: np.ndarray | pd.Series) -> np.ndarray:
    """Return the clipped ``2d`` mechanism bound for action density ``d``."""
    density = np.asarray(action_density, dtype=float)
    return np.clip(2.0 * density, 0.0, 1.0)


def _safe_pearson(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    if np.std(actual) <= 1e-12 or np.std(predicted) <= 1e-12:
        return None
    return float(np.corrcoef(actual, predicted)[0, 1])


def load_combined_evidence() -> pd.DataFrame:
    """Load E21 naive labels and E27 recomputed labels into one table."""
    e21 = pd.read_csv(E21_CSV)
    e21 = e21[e21["strategy_name"] == "naive"].reset_index(drop=True)
    features = pd.read_csv(E21_FEATURES_CSV)
    if len(e21) != len(features):
        raise ValueError(f"E21 feature/label row mismatch: {len(features)} != {len(e21)}")
    e21_features = features.copy()
    e21_features["gate_reduction"] = e21["gate_reduction"].to_numpy()
    e21_features["source"] = "E21"

    e27_features = pd.read_csv(E27_FEATURES_CSV).copy()
    e27_features["source"] = "E27"
    return pd.concat([e21_features, e27_features], ignore_index=True)


def check_lower_bound(data: pd.DataFrame) -> dict[str, Any]:
    """Check empirical target values against the mechanism-derived bound."""
    bound = phase1_lower_bound(data["phase1_action_density"])
    margin = data["gate_reduction"].to_numpy(dtype=float) - bound
    violations = np.flatnonzero(margin < -1e-12)
    return {
        "n_rows": int(len(data)),
        "n_violations": int(len(violations)),
        "min_margin": float(margin.min()) if len(margin) else None,
        "max_margin": float(margin.max()) if len(margin) else None,
        "bound_mae": float(mean_absolute_error(data["gate_reduction"], bound)),
    }


def evaluate_isotonic_lofo(data: pd.DataFrame) -> pd.DataFrame:
    """Evaluate one-dimensional isotonic regression by held-out family."""
    rows: list[dict[str, Any]] = []
    for family in sorted(data["family"].unique()):
        train = data["family"] != family
        test = ~train
        model = IsotonicRegression(increasing=True, out_of_bounds="clip")
        model.fit(
            data.loc[train, "phase1_action_density"],
            data.loc[train, "gate_reduction"],
        )
        predicted = model.predict(data.loc[test, "phase1_action_density"])
        actual = data.loc[test, "gate_reduction"].to_numpy(dtype=float)
        rows.append({
            "held_out_family": family,
            "n_test": int(test.sum()),
            "mae": float(mean_absolute_error(actual, predicted)),
            "pearson_r": _safe_pearson(actual, predicted),
            "actual_mean": float(actual.mean()),
            "predicted_mean": float(predicted.mean()),
        })
    return pd.DataFrame(rows)


def build_summary(data: pd.DataFrame, isotonic: pd.DataFrame) -> dict[str, Any]:
    """Build compact P7 evidence summary without hiding degenerate folds."""
    bound = phase1_lower_bound(data["phase1_action_density"])
    actual = data["gate_reduction"].to_numpy(dtype=float)
    repetition = data["family"] == "RepetitionCode"
    structural = data["structural_upper_bound"].to_numpy(dtype=float)
    return {
        "protocol": "E21 naive labels + E27 recomputed labels; seed 42 artifacts",
        "lower_bound": check_lower_bound(data),
        "isotonic_pooled_mae": float(
            np.average(isotonic["mae"], weights=isotonic["n_test"])
        ),
        "repetition_code": {
            "n": int(repetition.sum()),
            "phase1_density_min": float(data.loc[repetition, "phase1_action_density"].min()),
            "phase1_density_max": float(data.loc[repetition, "phase1_action_density"].max()),
            "bound_mae": float(mean_absolute_error(actual[repetition], bound[repetition])),
            "structural_upper_bound_mae": float(
                mean_absolute_error(actual[repetition], structural[repetition])
            ),
            "isotonic_mae": float(
                isotonic.loc[isotonic["held_out_family"] == "RepetitionCode", "mae"].iloc[0]
            ),
        },
    }


def main() -> int:
    data = load_combined_evidence()
    isotonic = evaluate_isotonic_lofo(data)
    summary = build_summary(data, isotonic)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    isotonic.to_csv(OUTPUT_DIR / "p7_monotone_lofo.csv", index=False)
    (OUTPUT_DIR / "p7_monotone_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
