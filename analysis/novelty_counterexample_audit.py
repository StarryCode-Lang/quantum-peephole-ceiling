"""Bind the targeted identical-counterexample search to an explicit disposition."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MATRIX = ROOT / "docs/review/prepaper_novelty_matrix_2026-08-10.md"
REFRESH = ROOT / "docs/review/prepaper_novelty_refresh_2026-08-24.md"
FORWARD = ROOT / "docs/review/prepaper_forward_negative_citation_audit_2026-08-24.md"
OUTPUT = ROOT / "release/novelty_counterexample_audit.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def build(output: Path = OUTPUT) -> dict[str, object]:
    matrix = MATRIX.read_text(encoding="utf-8")
    refresh = REFRESH.read_text(encoding="utf-8")
    forward = FORWARD.read_text(encoding="utf-8")
    required = {
        "representation_collision_catalogued": "Q-PreSyn" in matrix and "Quasar" in matrix,
        "latest_close_methods_refreshed": "randomized replacements" in refresh,
        "identical_counterexample_answered": (
            "not an identical minimal" in forward
            and "It remains fail-closed" in forward
        ),
    }
    if not all(required.values()):
        raise RuntimeError(f"novelty counterexample source contract failed: {required}")
    payload: dict[str, object] = {
        "schema_version": "1.0.0",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PARTIAL_TARGETED_NO_IDENTICAL_COUNTEREXAMPLE_FOUND",
        "checks": required,
        "closest_collisions": [
            "Q-PreSyn: representation-dependent learned pre-synthesis",
            "Quasar: sequence/graph equality-saturation representation sensitivity",
            "cut-and-meld: oracle-parametric local optimality",
            "GUOQ: rewrite and resynthesis composition",
        ],
        "metric_dispositions": {
            "3.13": (
                "PARTIAL: targeted primary-source searches found close representation, local-"
                "optimality, and scalability collisions but no identical minimal counterexample; "
                "absence cannot be established exhaustively"
            )
        },
        "claim_boundary": (
            "The search supports a narrow statement that no identical counterexample was found "
            "in the documented comparator set. It is not proof that none exists, and broader "
            "representation-dependence is explicitly prior art."
        ),
        "source_bindings": {
            path.relative_to(ROOT).as_posix(): _sha(path)
            for path in (MATRIX, REFRESH, FORWARD, Path(__file__))
        },
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(output)
    return payload


if __name__ == "__main__":
    audit = build()
    print(json.dumps({"status": audit["status"], "checks": audit["checks"]}, sort_keys=True))

