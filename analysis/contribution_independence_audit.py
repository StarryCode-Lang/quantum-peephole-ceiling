"""Determine whether the completed research increment is paper-scale, not an ablation."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COMPLETION = ROOT / "data/v11/e31_factorial_pareto/formal_run/final/formal_completion_manifest.json"
RECEIPT = ROOT / "release/e31_independent_release_verification_receipt.json"
HELDOUT = ROOT / "data/v10/prepaper/heldout_v2/analysis/combined_heldout_metrics.json"
EXTERNAL = ROOT / "data/v10/prepaper/analysis/external/audit.json"
NOVELTY = ROOT / "docs/review/prepaper_novelty_refresh_2026-08-24.md"
OUTPUT = ROOT / "release/contribution_independence_audit.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path = OUTPUT) -> dict[str, object]:
    completion = json.loads(COMPLETION.read_text(encoding="utf-8"))
    receipt = json.loads(RECEIPT.read_text(encoding="utf-8"))
    heldout = json.loads(HELDOUT.read_text(encoding="utf-8"))
    external = json.loads(EXTERNAL.read_text(encoding="utf-8"))
    novelty_text = NOVELTY.read_text(encoding="utf-8")

    criteria = {
        "formal_factorial_program_complete": (
            completion.get("formal_analysis_gate_passed") is True
            and completion.get("rows") == completion.get("scheduled_rows") == 28152
            and completion.get("unique_input_hashes") == 391
        ),
        "independent_release_verification_passed": (
            receipt.get("status") == "PASS_E31_INDEPENDENT_RELEASE_VERIFICATION"
        ),
        "independent_generator_validation_present": (
            heldout.get("outer_clusters") == 16
            and heldout.get("n_unique_inputs") == 378
            and heldout.get("model_refit") is False
            and heldout.get("feature_or_threshold_change") is False
        ),
        "formal_external_comparator_program_present": (
            external.get("status") == "complete"
            and set(external.get("methods", [])) == {"quasar", "quartz"}
            and external.get("n_per_method") == 520
        ),
        "narrow_novelty_boundary_explicit": (
            "The strongest currently defensible contribution" in novelty_text
            and "not establish:" in novelty_text
        ),
    }
    if not all(criteria.values()):
        raise RuntimeError(f"paper-scale contribution gate failed: {criteria}")

    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS_STANDALONE_EMPIRICAL_CONTRIBUTION_GATE",
        "criteria": criteria,
        "observed_scope": {
            "formal_factorial_rows": int(completion["rows"]),
            "formal_unique_inputs": int(completion["unique_input_hashes"]),
            "formal_outer_families": int(completion["outer_families"]),
            "semantic_cells_replayed": int(
                completion["semantic_replay"]["unique_semantic_cells_replayed"]
            ),
            "heldout_outer_generator_families": int(heldout["outer_clusters"]),
            "heldout_unique_inputs": int(heldout["n_unique_inputs"]),
            "formal_external_methods": sorted(external["methods"]),
            "external_inputs_per_method": int(external["n_per_method"]),
        },
        "metric_dispositions": {
            "3.27": (
                "PASS: the increment is a standalone empirical research package rather than "
                "a single ablation, combining a completed 28,152-row factorial program, "
                "independent 16-family held-out validation, and two formal external artifacts"
            )
        },
        "claim_boundary": (
            "This gate supports paper-scale independence of the research package. It does not "
            "establish priority over all related work, guarantee venue acceptance, permit "
            "unseen-family universality, or convert post-hoc analyses into confirmatory evidence."
        ),
        "source_bindings": {
            path.relative_to(ROOT).as_posix(): _sha(path)
            for path in (COMPLETION, RECEIPT, HELDOUT, EXTERNAL, NOVELTY, Path(__file__))
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    return payload


if __name__ == "__main__":
    result = build()
    print(json.dumps({"status": result["status"], **result["observed_scope"]}, sort_keys=True))
