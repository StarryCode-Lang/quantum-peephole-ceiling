"""Run the independent E31 verifier and persist a release-verification receipt."""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.verify_prepaper_release_manifest import _verify_e31_formal

E31 = ROOT / "data/v11/e31_factorial_pareto"
DEFAULT_OUTPUT = ROOT / "release/e31_independent_release_verification_receipt.json"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build_receipt(*, checked_artifacts: int | None = None) -> dict[str, object]:
    checked = _verify_e31_formal() if checked_artifacts is None else checked_artifacts
    if not isinstance(checked, int) or checked < 34_000:
        raise RuntimeError("E31 independent verifier did not cover the full certificate inventory")
    paths = {
        "formal_completion_manifest": E31 / "formal_run/final/formal_completion_manifest.json",
        "formal_results": E31 / "formal_run/final/formal_results.csv",
        "analysis_gate": E31 / "formal_run/analysis/analysis_gate_audit.json",
        "family_inference_correction_audit": (
            E31 / "formal_run/analysis/family_inference/family_inference_correction_audit.json"
        ),
        "semantic_replay_gate": E31 / "formal_run/semantic_replay/semantic_replay_gate.json",
        "semantic_replay_manifest": (
            E31 / "formal_run/semantic_replay/semantic_replay_manifest.json"
        ),
        "temporal_gate_binding_audit": ROOT / "release/e31_temporal_gate_binding_audit.json",
        "independent_verifier_source": ROOT / "scripts/verify_prepaper_release_manifest.py",
    }
    return {
        "schema_version": "1.0.0",
        "status": "PASS_E31_INDEPENDENT_RELEASE_VERIFICATION",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "checked_artifact_count": checked,
        "formal_rows": 28_152,
        "success_rows_semantically_replayed": 20_314,
        "unique_semantic_cells_replayed": 6_858,
        "semantic_identity_check": (
            "exact dense phase-aligned Uout^dagger Uin identity norm plus trace average-gate "
            "fidelity for every unique successful semantic cell"
        ),
        "outer_inference_cluster": "circuit_family",
        "n_independent_family_clusters": 15,
        "family_cluster_degrees_of_freedom": 14,
        "legacy_input_cluster_inference_valid": False,
        "unseen_family_generalization_status": "BLOCKED",
        "source_provenance_rating": "PARTIAL",
        "temporal_gate_provenance_rating": "PARTIAL",
        "artifacts": {
            name: {"path": path.relative_to(ROOT).as_posix(), "sha256": sha256(path),
                   "bytes": path.stat().st_size}
            for name, path in paths.items()
        },
        "independence_boundary": (
            "receipt is written only after the separate release verifier rehashes every bound "
            "success-row certificate, semantic-cell certificate, QPY artifact, sealed table, "
            "and independently recomputes the family-level statistics"
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    receipt = build_receipt()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
