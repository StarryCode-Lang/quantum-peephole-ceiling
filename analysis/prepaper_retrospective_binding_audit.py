"""Retrospectively bind already-sealed evidence to audit metrics it directly answers.

This audit does not rerun any experiment.  It re-hashes sealed evidence files,
re-checks their internal status and design facts, and records one explicit,
item-specific disposition per metric whose question the sealed evidence already
answers.  The dispositions are intentionally bounded by each evidence file's own
claim boundary; nothing here upgrades a generalization claim.

Metrics bound:

- 13.14 cross-compiler-version generalization: bounded PARTIAL from the frozen
  7-environment / 15-family / 105-row version panel plus its independent replay.
- 16.23 mechanism conclusions after tool-version updates: bounded PARTIAL from
  the same panel; only the exact tested versions are covered.
- 3.12 direct listing/order-sensitivity experiment: PASS from the sealed E31
  full factorial, whose ``listing_model`` factor is exactly a listing/order
  manipulation, plus the sealed coefficient and marginal-contrast tables.
- 16.16 hardware-aware objectives: bounded PARTIAL from the fake-backend
  routing-overhead audit; no real-QPU objective is measured.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "release/prepaper_retrospective_binding_audit.json"

VERSION_AUDIT = ROOT / "data/v11/compiler_version_sensitivity/compiler_version_sensitivity_audit.json"
VERSION_VERIFICATION = ROOT / "data/v11/compiler_version_sensitivity/independent_verification.json"
E31_PROTOCOL = ROOT / "experiments/e31_factorial_pareto_protocol.json"
E31_DESIGN = ROOT / "data/v11/e31_factorial_pareto/design_metadata.json"
FRAGILITY_AUDIT = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/fragility_listing_audit.json"
COEFFICIENTS = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/full_factorial_model_coefficients.csv"
MARGINAL = ROOT / "data/v11/e31_factorial_pareto/formal_run/analysis/posthoc_marginal_contrasts.csv"
HARDWARE_AUDIT = ROOT / "data/v10/prepaper/analysis/hardware_routing_overhead/hardware_routing_overhead_audit.json"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build_audit(output: Path = DEFAULT_OUTPUT) -> dict:
    version_audit = _load_json(VERSION_AUDIT)
    if version_audit.get("status") != "PASS_BOUNDED_COMPILER_VERSION_PANEL":
        raise RuntimeError("compiler version panel audit is not PASS")
    if int(version_audit["artifacts"]["all_version_results.csv"]["rows"]) != 105:
        raise RuntimeError("compiler version panel is not the 105-row design")
    if len(version_audit["executed_environments"]) != 7:
        raise RuntimeError("compiler version panel lacks seven isolated environments")
    version_verification = _load_json(VERSION_VERIFICATION)
    if version_verification.get("status") != "PASS_INDEPENDENT_COMPILER_VERSION_REPLAY":
        raise RuntimeError("compiler version independent replay is not PASS")
    if int(version_verification.get("design_rows", -1)) != 105:
        raise RuntimeError("compiler version replay does not cover all 105 rows")

    protocol = _load_json(E31_PROTOCOL)
    listing_levels = protocol.get("factors", {}).get("listing_model")
    if listing_levels != ["LBL", "WCL", "RANDOM_TOPOLOGICAL"]:
        raise RuntimeError("E31 protocol listing_model factor drifted")
    design = _load_json(E31_DESIGN)
    if int(design.get("scheduled_rows", -1)) != 28152:
        raise RuntimeError("E31 design is not the sealed 28,152-row factorial")
    fragility = _load_json(FRAGILITY_AUDIT)
    if fragility.get("status") != "PASS_BOUNDED_E31_FRAGILITY_AND_LISTING_AUDIT":
        raise RuntimeError("E31 fragility/listing audit is not PASS")

    coefficients = pd.read_csv(COEFFICIENTS, index_col=0)
    listing_terms = coefficients.index[coefficients.index.str.contains("listing_model")]
    if len(listing_terms) == 0:
        raise RuntimeError("sealed factorial coefficients lack listing_model terms")
    marginal = pd.read_csv(MARGINAL)
    listing_marginals = marginal.loc[
        marginal["coefficient"].str.startswith("MARGINAL::listing_model")
    ]
    if len(listing_marginals) == 0:
        raise RuntimeError("sealed marginal contrasts lack listing_model contrasts")

    hardware = _load_json(HARDWARE_AUDIT)
    if hardware.get("status") != "PASS_BOUNDED_FAKE_BACKEND_ROUTING_AUDIT":
        raise RuntimeError("hardware routing overhead audit is not PASS")
    if "16.17" not in hardware.get("metric_dispositions", {}):
        raise RuntimeError("hardware routing audit lacks its 16.17 disposition")

    dispositions = {
        "13.14": (
            "PARTIAL: the frozen 7-environment, 15-family, 105-row panel shows all "
            "version pairs structurally identical and numerically exact-equivalent "
            "(Qiskit 2.3.1/2.4.1, Cirq 1.6.0/1.6.1, pytket 2.17.0/2.18.0), with an "
            "independent 105/105 QASM semantic replay, but this is not a full "
            "benchmark rerun, not cross-platform, and external tool versions are "
            "not varied"
        ),
        "16.23": (
            "PARTIAL: mechanism conclusions are version-stable across the exact "
            "tested compiler version pairs on the frozen 15-family panel, but the "
            "evidence covers only those versions on one Windows host; custom-current "
            "has a single version and future or external versions remain untested"
        ),
        "3.12": (
            "PASS: the sealed E31 full factorial is itself a direct listing/order "
            "sensitivity experiment; listing_model (LBL/WCL/RANDOM_TOPOLOGICAL) is a "
            "first-class factor in all 28,152 rows, with sealed coefficient and "
            "post-hoc marginal-contrast tables plus an exhaustive listing fragility "
            "audit"
        ),
        "16.16": (
            "PARTIAL: bounded fake-backend routing-overhead evidence shows mapped "
            "native two-qubit reductions for two optimizer variants in paired cells, "
            "but no real-QPU hardware-aware objective, duration, or calibration is "
            "measured"
        ),
    }

    payload = {
        "schema_version": "1.0.0",
        "status": "PASS_RETROSPECTIVE_EVIDENCE_BINDING",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "method": (
            "read-only retrospective binding: sealed evidence files are re-hashed "
            "and their internal status/design facts re-checked; no experiment is "
            "rerun and no sealed artifact is modified"
        ),
        "evidence_bindings": {
            "data/v11/compiler_version_sensitivity/compiler_version_sensitivity_audit.json": {
                "sha256": sha256(VERSION_AUDIT),
                "required_status": "PASS_BOUNDED_COMPILER_VERSION_PANEL",
                "metrics": ["13.14", "16.23"],
            },
            "data/v11/compiler_version_sensitivity/independent_verification.json": {
                "sha256": sha256(VERSION_VERIFICATION),
                "required_status": "PASS_INDEPENDENT_COMPILER_VERSION_REPLAY",
                "metrics": ["13.14", "16.23"],
            },
            "experiments/e31_factorial_pareto_protocol.json": {
                "sha256": sha256(E31_PROTOCOL),
                "required_fact": "factors.listing_model == [LBL, WCL, RANDOM_TOPOLOGICAL]",
                "metrics": ["3.12"],
            },
            "data/v11/e31_factorial_pareto/design_metadata.json": {
                "sha256": sha256(E31_DESIGN),
                "required_fact": "scheduled_rows == 28152",
                "metrics": ["3.12"],
            },
            "data/v11/e31_factorial_pareto/formal_run/analysis/fragility_listing/fragility_listing_audit.json": {
                "sha256": sha256(FRAGILITY_AUDIT),
                "required_status": "PASS_BOUNDED_E31_FRAGILITY_AND_LISTING_AUDIT",
                "metrics": ["3.12"],
            },
            "data/v11/e31_factorial_pareto/formal_run/analysis/full_factorial_model_coefficients.csv": {
                "sha256": sha256(COEFFICIENTS),
                "required_fact": f"{len(listing_terms)} listing_model coefficient terms present",
                "metrics": ["3.12"],
            },
            "data/v11/e31_factorial_pareto/formal_run/analysis/posthoc_marginal_contrasts.csv": {
                "sha256": sha256(MARGINAL),
                "required_fact": f"{len(listing_marginals)} MARGINAL::listing_model contrasts present",
                "metrics": ["3.12"],
            },
            "data/v10/prepaper/analysis/hardware_routing_overhead/hardware_routing_overhead_audit.json": {
                "sha256": sha256(HARDWARE_AUDIT),
                "required_status": "PASS_BOUNDED_FAKE_BACKEND_ROUTING_AUDIT",
                "metrics": ["16.16"],
            },
        },
        "metric_dispositions": dispositions,
        "claim_boundary": (
            "Retrospective binding only registers item-specific evidence that already "
            "exists; it does not extend any claim. 13.14/16.23 remain bounded PARTIAL "
            "because the version panel is small, single-platform, and excludes external "
            "tools; 3.12 is PASS only for the existence of a direct listing/order "
            "experiment on the fixed E31 panel, not for listing insensitivity in "
            "general; 16.16 remains PARTIAL without real-QPU hardware-aware evidence."
        ),
        "source_bindings": {
            "analysis/prepaper_retrospective_binding_audit.py": sha256(Path(__file__)),
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    audit = build_audit(args.output.resolve())
    print(json.dumps({"status": audit["status"],
                      "metrics_bound": sorted(audit["metric_dispositions"])},
                     sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
