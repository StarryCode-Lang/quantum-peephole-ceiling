"""Audit when the E31 method/host limitation gates were fixed relative to rows."""

from __future__ import annotations

import argparse
import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E31 = ROOT / "data/v11/e31_factorial_pareto"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def prefix_boundary(checkpoint: Path, *, rows: int) -> dict[str, object]:
    with sqlite3.connect(f"file:{checkpoint.resolve()}?mode=ro", uri=True) as connection:
        if connection.execute("PRAGMA integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("E31 checkpoint integrity_check failed")
        records = connection.execute(
            "SELECT run_order, committed_utc, json_extract(result_json, '$.status') "
            "FROM results WHERE run_order < ? ORDER BY run_order", (rows,),
        ).fetchall()
    if len(records) != rows or [int(row[0]) for row in records] != list(range(rows)):
        raise RuntimeError("E31 temporal boundary is not a contiguous prefix")
    status_counts: dict[str, int] = {}
    for _, _, status in records:
        status_counts[str(status)] = status_counts.get(str(status), 0) + 1
    return {
        "rows": rows,
        "max_run_order": rows - 1,
        "last_committed_utc": str(records[-1][1]),
        "status_counts_only": status_counts,
    }


def build_audit(root: Path = ROOT) -> dict[str, object]:
    e31 = root / "data/v11/e31_factorial_pareto"
    checkpoint = e31 / "formal_run/checkpoint.sqlite3"
    method_path = e31 / "preanalysis_method_erratum_gate.json"
    host_path = e31 / "host_environment_limitation_gate.json"
    method = json.loads(method_path.read_text(encoding="utf-8"))
    host = json.loads(host_path.read_text(encoding="utf-8"))
    method_rows = int(method["checkpoint_boundary"]["committed_rows"])
    host_rows = int(host["checkpoint_boundary"]["rows"])
    method_boundary = prefix_boundary(checkpoint, rows=method_rows)
    host_boundary = prefix_boundary(checkpoint, rows=host_rows)
    if (method["checkpoint_boundary"].get("max_run_order")
            != method_boundary["max_run_order"]
            or method["checkpoint_boundary"].get("last_committed_utc")
            != method_boundary["last_committed_utc"]):
        raise RuntimeError("E31 method-gate checkpoint boundary differs from SQLite")
    if (host["checkpoint_boundary"].get("max_run_order") != host_boundary["max_run_order"]
            or host["checkpoint_boundary"].get("status_counts_only")
            != host_boundary["status_counts_only"]):
        raise RuntimeError("E31 host-gate checkpoint boundary differs from SQLite")
    method_mtime = datetime.fromtimestamp(method_path.stat().st_mtime, timezone.utc)
    method_last = datetime.fromisoformat(str(method_boundary["last_committed_utc"]))
    host_created = datetime.fromisoformat(str(host["created_utc"]))
    host_last = datetime.fromisoformat(str(host_boundary["last_committed_utc"]))
    if method_mtime <= method_last or host_created <= host_last:
        raise RuntimeError("an E31 limitation gate does not postdate its stated row boundary")
    return {
        "schema_version": "1.0.0",
        "status": "PASS_LIMITATION_BOUND_NO_RETROACTIVE_PRECOMMIT_CLAIM",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "overall_temporal_provenance_rating": "PARTIAL",
        "formal_checkpoint_sha256": sha256(checkpoint),
        "method_gate": {
            "path": method_path.relative_to(root).as_posix(),
            "sha256": sha256(method_path),
            "boundary_recomputed_from_sqlite": method_boundary,
            "gate_file_last_write_utc": method_mtime.isoformat(),
            "temporal_evidence": "PARTIAL_FILESYSTEM_MTIME_NOT_CRYPTOGRAPHIC_CREATION_PROOF",
            "created_utc_embedded_in_original_gate": False,
        },
        "host_gate": {
            "path": host_path.relative_to(root).as_posix(),
            "sha256": sha256(host_path),
            "boundary_recomputed_from_sqlite": host_boundary,
            "gate_created_utc": host_created.isoformat(),
            "temporal_evidence": "PASS_EMBEDDED_CREATED_UTC_AFTER_RECOMPUTED_BOUNDARY",
            "continuous_host_exclusivity_verified": False,
            "continuous_host_telemetry_recorded": False,
        },
        "claim_limits": [
            "does not upgrade the method gate filesystem timestamp into a cryptographic precommit",
            "does not establish continuous host exclusivity or continuous host telemetry",
            "does not alter frozen execution rows or authorize row exclusion or rerun",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output", type=Path,
        default=ROOT / "release/e31_temporal_gate_binding_audit.json",
    )
    args = parser.parse_args()
    audit = build_audit()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(audit, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(args.output.resolve())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
