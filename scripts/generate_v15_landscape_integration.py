"""Generate the v15 landscape-integration package from frozen v14 evidence.

The v14 compact exact panel left 35 of 128 cells resource-truncated.  The
complementary IDA* panel classified all 128 inputs exactly.  This entrypoint
integrates the two frozen packages into one classification-complete statement
without rerunning any search:

- 65 local-optimum cells carry complete derived certificates: the IDA*
  certificate proves no improving state exists in the horizon ball, so
  best_cost = baseline_cost exactly and the barrier quantity is vacuous,
- 29 escape cells keep their enumerated complete compact certificates,
- 34 escape cells keep the exact IDA* minimum escape depth while their
  landscape extras (best cost, minimum barrier) are bounded above by a
  replayed certified witness.

Every derivation is fail-closed: a package identity mismatch, a status
contradiction, or a failed witness replay aborts the generation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import itertools
import json
import sys
from pathlib import Path
from typing import Any

from qiskit import qasm2

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e45_development_grid.run import (  # noqa: E402
    MAX_BASELINE_GATES,
    RULE_LIBRARY,
    state_from_circuit,
)
from src.optimisation.certified_landscape import replay_actions  # noqa: E402
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402

COMPACT_ROOT = ROOT / "data" / "v14" / "e45_full_development"
IDASTAR_ROOT = ROOT / "data" / "v14" / "e45_idastar_escape"
SCREENING_MANIFEST = ROOT / "data" / "v14" / "e45_development_grid" / "normalization_manifest.csv"
OUTPUT_ROOT = ROOT / "data" / "v15" / "e45_landscape_integration"
RULE_SCOPE = "e44_core_v1"
EXPERIMENT_ID = "E45_LANDSCAPE_INTEGRATION_V15"

STATUS_ESCAPE = "EXACT_ESCAPE"
STATUS_LOCAL = "EXACT_H_LOCAL_OPTIMUM"

TIER_ENUMERATED = "COMPACT_COMPLETE_ENUMERATED"
TIER_DERIVED = "COMPACT_COMPLETE_DERIVED"
TIER_BOUNDED = "CLASSIFICATION_EXACT_EXTRAS_BOUNDED"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def atomic_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value, encoding="utf-8", newline="\n")
    temporary.replace(path)


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        atomic_text(path, "")
        return
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    atomic_text(path, buffer.getvalue())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def witness_metrics(baseline_cost: int, witness: list[dict[str, Any]]) -> tuple[int, int, int]:
    """Return (steps, endpoint_cost, peak_cost) for a witness action list."""

    deltas = [int(step["cost_delta"]) for step in witness]
    endpoint = baseline_cost + sum(deltas)
    peak = baseline_cost + max([0, *itertools.accumulate(deltas)])
    return len(witness), endpoint, peak


def rebuild_root_state(source_id: str, normalized_qasm_path: Path, expected_hash: str):
    """Rebuild the search root state exactly as the v14 runners did."""

    circuit = qasm2.loads(normalized_qasm_path.read_text(encoding="utf-8"))
    if int(circuit.size()) > MAX_BASELINE_GATES:
        baseline = circuit
    else:
        baseline = GreedyGateCancellation(
            max_iterations=50,
            fidelity_threshold=1.0,
            success_reduction=0.0,
        ).optimize(circuit).optimized_circuit
    state = state_from_circuit(baseline)
    if state.state_hash != expected_hash:
        raise RuntimeError(f"root_state_hash_mismatch:{source_id}")
    return state


def classify(
    source_id: str,
    compact_certificate: dict[str, Any],
    idastar_certificate: dict[str, Any],
) -> dict[str, Any]:
    """Derive the integrated claims for one panel cell from frozen certificates."""

    compact_status = compact_certificate["status"]
    idastar_status = idastar_certificate["status"]
    baseline = int(compact_certificate["baseline_cost"])

    if compact_certificate["initial_state_sha256"] != idastar_certificate["initial_state_sha256"]:
        raise RuntimeError(f"root_state_mismatch:{source_id}")
    if baseline != int(idastar_certificate["baseline_cost"]):
        raise RuntimeError(f"baseline_cost_mismatch:{source_id}")

    if idastar_status == STATUS_LOCAL:
        if compact_status not in {STATUS_LOCAL, "RESOURCE_BOUNDED_NO_WITNESS"}:
            raise RuntimeError(f"inconsistent_local_classification:{source_id}:{compact_status}")
        return {
            "classification_status": STATUS_LOCAL,
            "escape_depth": "",
            "escape_depth_exactness": "NOT_APPLICABLE",
            "best_cost": baseline,
            "best_cost_exactness": "EXACT_DERIVED_NO_IMPROVING_STATE_IN_BALL",
            "barrier_height": "",
            "barrier_exactness": "VACUOUS_NO_ESCAPE_IN_BALL",
            "certificate_tier": TIER_ENUMERATED if compact_status == STATUS_LOCAL else TIER_DERIVED,
            "witness_source": "NONE",
            "witness_step_count": 0,
            "witness_endpoint_cost": "",
            "witness_peak_cost": "",
            "witness_compact": [],
            "witness_idastar": [],
        }
    if idastar_status == STATUS_ESCAPE:
        if compact_status not in {STATUS_ESCAPE, "WITNESS_CERTIFIED_SEARCH_INCOMPLETE"}:
            raise RuntimeError(f"inconsistent_escape_classification:{source_id}:{compact_status}")
        if compact_status == STATUS_ESCAPE and int(compact_certificate["escape_depth"]) != int(
            idastar_certificate["escape_depth"]
        ):
            raise RuntimeError(f"escape_depth_mismatch:{source_id}")
        witness_compact = list(compact_certificate["witnesses"]["escape"])
        witness_idastar = list(idastar_certificate["witnesses"]["escape"])
        if witness_compact:
            steps, endpoint, peak = witness_metrics(baseline, witness_compact)
            witness_source = "COMPACT"
        elif witness_idastar:
            steps, endpoint, peak = witness_metrics(baseline, witness_idastar)
            witness_source = "IDASTAR"
        else:
            raise RuntimeError(f"escape_cell_without_witness:{source_id}")
        if compact_status == STATUS_ESCAPE:
            return {
                "classification_status": STATUS_ESCAPE,
                "escape_depth": int(idastar_certificate["escape_depth"]),
                "escape_depth_exactness": "EXACT_MINIMUM_WITHIN_HORIZON",
                "best_cost": int(compact_certificate["best_cost"]),
                "best_cost_exactness": "EXACT_ENUMERATED_COMPLETE_BALL",
                "barrier_height": compact_certificate["barrier_height"],
                "barrier_exactness": "EXACT_ENUMERATED_COMPLETE_BALL",
                "certificate_tier": TIER_ENUMERATED,
                "witness_source": witness_source,
                "witness_step_count": steps,
                "witness_endpoint_cost": endpoint,
                "witness_peak_cost": peak,
                "witness_compact": witness_compact,
                "witness_idastar": witness_idastar,
            }
        if endpoint >= baseline:
            raise RuntimeError(f"witness_not_improving:{source_id}")
        return {
            "classification_status": STATUS_ESCAPE,
            "escape_depth": int(idastar_certificate["escape_depth"]),
            "escape_depth_exactness": "EXACT_MINIMUM_WITHIN_HORIZON",
            "best_cost": endpoint,
            "best_cost_exactness": "BOUNDED_ABOVE_BY_CERTIFIED_WITNESS",
            "barrier_height": peak,
            "barrier_exactness": "BOUNDED_ABOVE_BY_CERTIFIED_WITNESS",
            "certificate_tier": TIER_BOUNDED,
            "witness_source": witness_source,
            "witness_step_count": steps,
            "witness_endpoint_cost": endpoint,
            "witness_peak_cost": peak,
            "witness_compact": witness_compact,
            "witness_idastar": witness_idastar,
        }
    raise RuntimeError(f"unexpected_idastar_status:{source_id}:{idastar_status}")


def run(output_root: Path = OUTPUT_ROOT) -> dict[str, Any]:
    output_root = output_root.resolve()
    compact_records = load_jsonl(COMPACT_ROOT / "certificates.jsonl")
    idastar_records = load_jsonl(IDASTAR_ROOT / "certificates.jsonl")
    compact_by_id = {record["source_id"]: record for record in compact_records}
    idastar_by_id = {record["source_id"]: record for record in idastar_records}
    if len(compact_by_id) != 128 or len(idastar_by_id) != 128 or set(compact_by_id) != set(idastar_by_id):
        raise RuntimeError("panel_size_or_identity_mismatch")

    compact_receipt = json.loads((COMPACT_ROOT / "receipt.json").read_text(encoding="utf-8"))
    idastar_receipt = json.loads((IDASTAR_ROOT / "receipt.json").read_text(encoding="utf-8"))
    if idastar_receipt["status"] != "COMPLETE":
        raise RuntimeError(f"idastar_package_not_complete:{idastar_receipt['status']}")

    sources_meta: dict[str, dict[str, Any]] = {}
    normalized_paths: dict[str, str] = {}
    with (COMPACT_ROOT / "grid_results.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["arm"] == "certificate_guided_escape":
                sources_meta[row["source_id"]] = row
    with (COMPACT_ROOT / "normalization_manifest.csv").open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            normalized_paths[row["source_id"]] = row["normalized_path"]
    if set(sources_meta) != set(compact_by_id) or set(normalized_paths) != set(compact_by_id):
        raise RuntimeError("grid_results_source_coverage_mismatch")

    rows: list[dict[str, Any]] = []
    derivation_log: list[dict[str, Any]] = []
    for source_id in sorted(compact_by_id):
        compact_certificate = compact_by_id[source_id]["certificate"]
        idastar_certificate = idastar_by_id[source_id]["certificate"]
        meta = sources_meta[source_id]
        derived = classify(source_id, compact_certificate, idastar_certificate)
        witness_compact = derived.pop("witness_compact")
        witness_idastar = derived.pop("witness_idastar")

        expected_root = compact_certificate["initial_state_sha256"]
        normalized_path = ROOT / normalized_paths[source_id]
        root_state = rebuild_root_state(source_id, normalized_path, expected_root)

        replay_compact = "NO_WITNESS"
        if witness_compact:
            outcome = replay_actions(root_state, witness_compact, RULE_LIBRARY, RULE_SCOPE)
            replay_compact = "REPLAY_PASS" if outcome.get("accepted") else "REPLAY_FAIL"
            if replay_compact == "REPLAY_FAIL":
                raise RuntimeError(f"compact_witness_replay_failed:{source_id}:{outcome.get('reason')}")
        replay_idastar = "NO_WITNESS"
        if witness_idastar:
            outcome = replay_actions(root_state, witness_idastar, RULE_LIBRARY, RULE_SCOPE)
            replay_idastar = "REPLAY_PASS" if outcome.get("accepted") else "REPLAY_FAIL"
            if replay_idastar == "REPLAY_FAIL":
                raise RuntimeError(f"idastar_witness_replay_failed:{source_id}:{outcome.get('reason')}")

        row = {
            "experiment_id": EXPERIMENT_ID,
            "source_id": source_id,
            "source_kind": meta["source_kind"],
            "circuit_id": meta["circuit_id"],
            "circuit_family": meta["circuit_family"],
            "n_qubits": meta["n_qubits"],
            "input_circuit_sha256": meta["input_circuit_sha256"],
            "horizon": compact_certificate["horizon"],
            "rule_scope": compact_certificate["rule_scope"],
            "baseline_cost": compact_certificate["baseline_cost"],
            "compact_status": compact_certificate["status"],
            "compact_escape_depth": compact_certificate.get("escape_depth", ""),
            "compact_best_cost": compact_certificate.get("best_cost", ""),
            "compact_barrier_height": compact_certificate.get("barrier_height", ""),
            "compact_resource_reason": compact_certificate.get("resource_reason", ""),
            "idastar_status": idastar_certificate["status"],
            "idastar_escape_depth": idastar_certificate.get("escape_depth", ""),
            **derived,
            "witness_replay_compact": replay_compact,
            "witness_replay_idastar": replay_idastar,
        }
        rows.append(row)
        derivation_log.append(
            {
                "source_id": source_id,
                "compact_status": compact_certificate["status"],
                "idastar_status": idastar_certificate["status"],
                "certificate_tier": derived["certificate_tier"],
                "witness_replay_compact": replay_compact,
                "witness_replay_idastar": replay_idastar,
            }
        )

    tiers = {
        tier: sum(row["certificate_tier"] == tier for row in rows)
        for tier in (TIER_ENUMERATED, TIER_DERIVED, TIER_BOUNDED)
    }
    if tiers[TIER_ENUMERATED] + tiers[TIER_DERIVED] + tiers[TIER_BOUNDED] != len(rows):
        raise RuntimeError("tier_partition_incomplete")
    if tiers[TIER_ENUMERATED] != 93:
        raise RuntimeError(f"unexpected_enumerated_cell_count:{tiers[TIER_ENUMERATED]}")
    if tiers[TIER_DERIVED] != 1:
        raise RuntimeError(f"unexpected_derived_cell_count:{tiers[TIER_DERIVED]}")
    if tiers[TIER_BOUNDED] != 34:
        raise RuntimeError(f"unexpected_bounded_cell_count:{tiers[TIER_BOUNDED]}")

    protocol = {
        "experiment_id": EXPERIMENT_ID,
        "status": "DERIVATION_ONLY_NO_NEW_SEARCH",
        "purpose": (
            "Integrate the frozen v14 compact exact panel and the frozen v14 IDA* "
            "panel into one classification-complete statement for the same "
            "128-source panel.  No search is rerun and no frozen package is modified."
        ),
        "inputs": {
            "compact_package": COMPACT_ROOT.relative_to(ROOT).as_posix(),
            "compact_receipt_status": compact_receipt["status"],
            "compact_certificates_sha256": sha256(COMPACT_ROOT / "certificates.jsonl"),
            "compact_grid_results_sha256": sha256(COMPACT_ROOT / "grid_results.csv"),
            "idastar_package": IDASTAR_ROOT.relative_to(ROOT).as_posix(),
            "idastar_receipt_status": idastar_receipt["status"],
            "idastar_certificates_sha256": sha256(IDASTAR_ROOT / "certificates.jsonl"),
            "screening_manifest_sha256": sha256(SCREENING_MANIFEST),
            "rule_library_sha256": sha256(RULE_LIBRARY),
            "rule_scope": RULE_SCOPE,
        },
        "identity_checks": [
            "both packages cover exactly the same 128 source ids",
            "initial_state_sha256 agreement per source (root state also rebuilt and hash-checked)",
            "baseline_cost agreement per source",
            "compact EXACT_ESCAPE implies matching IDA* EXACT_ESCAPE with equal minimum escape depth",
            "a truncated compact cell with a recorded witness cannot be a local optimum",
        ],
        "derivation_rules": {
            "local_optimum": (
                "IDA* proves no improving state exists in the horizon ball.  The "
                "initial state is in the ball, so best_cost = baseline_cost exactly.  "
                "No improving path exists, so the barrier quantity is vacuous."
            ),
            "escape_enumerated": (
                "When the compact ball enumeration completed, best_cost and "
                "barrier_height are exact and the IDA* minimum escape depth must "
                "agree with the compact escape depth."
            ),
            "escape_bounded": (
                "For truncated compact cells the certified witness bounds the "
                "extras from above: best_cost <= witness endpoint cost and "
                "minimum barrier <= witness peak cost.  The witness endpoint "
                "must improve on the baseline."
            ),
            "witness_replay": "every replayed witness must reapply through replay_actions against the hash-checked root state",
        },
        "resource_contracts": "none; this package consumes frozen evidence only",
    }
    atomic_text(output_root / "protocol.json", json.dumps(protocol, indent=2, sort_keys=True) + "\n")

    write_csv(output_root / "classification_complete.csv", rows)
    atomic_text(
        output_root / "derivations.jsonl",
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in derivation_log),
    )

    escapes = [row for row in rows if row["classification_status"] == STATUS_ESCAPE]
    receipt = {
        "status": "CLASSIFICATION_COMPLETE",
        "experiment_id": EXPERIMENT_ID,
        "protocol_sha256": sha256(output_root / "protocol.json"),
        "classification_complete_sha256": sha256(output_root / "classification_complete.csv"),
        "derivations_sha256": sha256(output_root / "derivations.jsonl"),
        "source_count": len(rows),
        "classified_count": len(rows),
        "unclassified_count": 0,
        "escape_count": len(escapes),
        "local_optimum_count": len(rows) - len(escapes),
        "certificate_tiers": tiers,
        "exact_best_cost_count": sum(str(row["best_cost_exactness"]).startswith("EXACT") for row in rows),
        "bounded_best_cost_count": sum(str(row["best_cost_exactness"]).startswith("BOUNDED") for row in rows),
        "witness_replay_failure_count": sum(
            row["witness_replay_compact"] == "REPLAY_FAIL" or row["witness_replay_idastar"] == "REPLAY_FAIL"
            for row in rows
        ),
        "inputs": protocol["inputs"],
    }
    atomic_text(output_root / "receipt.json", json.dumps(receipt, indent=2, sort_keys=True) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    args = parser.parse_args()
    print(json.dumps(run(args.output_root), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
