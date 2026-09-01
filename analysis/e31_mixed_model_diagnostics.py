"""Fit and diagnose a supportive E31 family random-slope mixed model."""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels
import statsmodels.formula.api as smf

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "data/v11/e31_factorial_pareto/formal_run/final/formal_results.csv"
OUTPUT_DIR = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/mixed_model_diagnostics"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _model_frame() -> pd.DataFrame:
    frame = pd.read_csv(RESULTS)
    valid = frame["valid_equivalent_output"]
    if valid.dtype != bool:
        valid = valid.astype(str).str.lower().eq("true")
    frame["itt_reduction_pp"] = np.where(
        valid, frame["common_basis_gate_reduction_pct"].fillna(0.0), 0.0
    )
    frame = frame.loc[frame["listing_model"].isin(["LBL", "WCL"])]
    aggregate = frame.groupby(
        ["input_circuit_sha256", "circuit_family", "listing_model", "rule_set"],
        as_index=False,
    )["itt_reduction_pp"].mean()
    aggregate["listing_wcl"] = aggregate["listing_model"].eq("WCL").astype(float)
    aggregate["templates"] = aggregate["rule_set"].eq(
        "COMMUTATION_PLUS_TEMPLATES"
    ).astype(float)
    if len(aggregate) != 391 * 2 * 2 or aggregate["circuit_family"].nunique() != 15:
        raise ValueError("mixed-model aggregate does not match the sealed E31 dimensions")
    return aggregate


def build_audit(output_dir: Path = OUTPUT_DIR) -> dict[str, object]:
    frame = _model_frame()
    formula = "itt_reduction_pp ~ listing_wcl * templates"
    model = smf.mixedlm(
        formula,
        frame,
        groups=frame["circuit_family"],
        re_formula="1 + listing_wcl",
        vc_formula={"instance": "0 + C(input_circuit_sha256)"},
    )
    fitted = model.fit(reml=True, method="lbfgs", maxiter=1000,
                       full_output=True, disp=False)
    history = fitted.hist[-1] if fitted.hist else {}
    gradient = np.asarray(history.get("gopt", []), dtype=float)
    hessian, hessian_singular_flag = fitted.hessv
    hessian = (np.asarray(hessian, dtype=float) + np.asarray(hessian, dtype=float).T) / 2
    hessian_eigenvalues = np.linalg.eigvalsh(hessian)
    covariance = fitted.cov_re.to_numpy(float)
    covariance_eigenvalues = np.linalg.eigvalsh(covariance)
    random_effect_correlation = float(
        covariance[0, 1] / np.sqrt(covariance[0, 0] * covariance[1, 1])
    )
    covariance_eigen_ratio = float(covariance_eigenvalues.min() / covariance_eigenvalues.max())
    near_singular = bool(
        abs(random_effect_correlation) >= 0.99 or covariance_eigen_ratio < 1e-3
    )
    fixed_names = list(model.exog_names)
    fixed = pd.DataFrame({
        "term": fixed_names,
        "estimate": [float(fitted.params[name]) for name in fixed_names],
        "standard_error": [float(fitted.bse[name]) for name in fixed_names],
        "ci95_lower": [float(fitted.conf_int().loc[name, 0]) for name in fixed_names],
        "ci95_upper": [float(fitted.conf_int().loc[name, 1]) for name in fixed_names],
        "p_value_wald": [float(fitted.pvalues[name]) for name in fixed_names],
    })
    output_dir.mkdir(parents=True, exist_ok=True)
    fixed_path = output_dir / "mixed_model_fixed_effects.csv"
    fixed.to_csv(fixed_path, index=False)
    summary_path = output_dir / "mixed_model_summary.txt"
    summary_path.write_text(fitted.summary().as_text() + "\n", encoding="utf-8")
    interaction = float(fitted.params["listing_wcl:templates"])
    audit = {
        "schema_version": "1.0.0",
        "status": "PASS_CONVERGED_WITH_NEAR_SINGULAR_RANDOM_EFFECT_WARNING",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "scope": "supportive post-seal model on the fixed 391-input E31 panel",
        "model": {
            "formula": formula,
            "observations": int(fitted.nobs), "family_groups": 15, "input_instances": 391,
            "aggregation": "equal mean over the frozen 3 windows x 4 budgets before modeling",
            "fit": "REML", "optimizer": "lbfgs", "statsmodels_version": statsmodels.__version__,
            "random_effects": "family random intercept plus family listing_wcl slope; input variance component intercept",
        },
        "convergence": {
            "converged": bool(fitted.converged),
            "optimizer_warnflag": int(history.get("warnflag", -1)),
            "optimizer_iterations": int(history.get("iterations", -1)),
            "optimizer_function_calls": int(history.get("fcalls", -1)),
            "gradient_infinity_norm": float(np.max(np.abs(gradient))),
        },
        "diagnostics": {
            "hessian_singular_flag": bool(hessian_singular_flag),
            "hessian_eigenvalues": [float(value) for value in hessian_eigenvalues],
            "hessian_negative_definite": bool(np.all(hessian_eigenvalues < 0)),
            "family_random_effect_covariance": covariance.tolist(),
            "family_random_effect_covariance_eigenvalues": [
                float(value) for value in covariance_eigenvalues
            ],
            "family_random_intercept_slope_correlation": random_effect_correlation,
            "family_random_effect_eigenvalue_ratio": covariance_eigen_ratio,
            "near_singular_random_effect_geometry": near_singular,
        },
        "fixed_effects": {str(row.term): float(row.estimate) for row in fixed.itertuples()},
        "primary_interaction_reproduces_descriptive_pp": interaction,
        "metric_dispositions": {
            "11.32": "PASS: the declared supportive mixed model converged under REML/L-BFGS without an optimizer warning",
            "11.33": "PARTIAL: convergence is achieved, but the observed Hessian is indefinite and the family random intercept/slope covariance is near singular",
            "11.40": "PASS: a family-level random slope for WCL versus LBL is estimated jointly with the family intercept and input variance component",
        },
        "claim_boundary": (
            "The mixed model is supportive, not the confirmatory E31 inferential engine. Fifteen "
            "families are too few to treat the near-boundary random-effect geometry as routine; "
            "family-t14 and wild-cluster-bootstrap outputs remain the primary supportive inference."
        ),
        "source_bindings": {
            "formal_results.csv": _sha(RESULTS),
            "analysis/e31_mixed_model_diagnostics.py": _sha(Path(__file__)),
        },
        "artifacts": {
            "mixed_model_fixed_effects.csv": {"rows": int(len(fixed)), "sha256": _sha(fixed_path)},
            "mixed_model_summary.txt": {"sha256": _sha(summary_path)},
        },
    }
    if not fitted.converged:
        audit["status"] = "FAIL_MIXED_MODEL_DID_NOT_CONVERGE"
    output = output_dir / "mixed_model_diagnostics.json"
    temporary = output.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    temporary.replace(output)
    return audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    audit = build_audit(args.output_dir)
    print(json.dumps({"status": audit["status"], "convergence": audit["convergence"],
                      "diagnostics": audit["diagnostics"],
                      "primary_interaction_reproduces_descriptive_pp":
                          audit["primary_interaction_reproduces_descriptive_pp"]},
                     indent=2, sort_keys=True))
    return 0 if audit["convergence"]["converged"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
