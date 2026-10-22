"""E52: what actually carries the certified escapes?

Motivation
----------
The project's headline phenomenon is *Phase-1 gate cancellation* under two
listings (WCL vs LBL, 0.0000% -> 7.83%).  The v14/v15 certified landscape,
however, runs on a 149-rule Quartz core (``e44_core_v1``), not on cancellation.
Six review rounds have treated "the landscape" and "the peephole ceiling" as
one object without checking whether the escapes are produced by the same
mechanism as the headline claim.

This experiment answers that with frozen data only:

Part A (arithmetic on frozen certificates)
    For every one of the 128 IDA* certificates, decompose the escape witness
    into its action sequence: path length, neutral prefix length, the rule
    families used, and the rule that performs the cost-reducing step.  Report
    the census by circuit family and by rule family.

Part B (root census, recomputed and hash-checked)
    Count, on every hash-verified E45 root state, the identical self-inverse
    gate pairs and their commutation distance ``D`` (the number of adjacent
    swaps needed to bring the pair together).  ``D`` is the quantity that a
    pure cancellation optimizer would need to reach in order to see the pair.

Part C (the decomposition)
    Cross-tabulate: escapes whose reducing step is ``pair_v1`` (cancellation)
    versus escapes whose reducing step is a Quartz rule.  This is the number
    that decides whether the manuscript's two stories are one story.

Contract
    Frozen inputs only, read-only.  No search is re-run; Part B rebuilds root
    states through ``load_root_states`` which hash-checks every root against
    the v14 certificates and raises on mismatch.

Outputs (``docs/review/science_boost/2026-10-22_escape_mechanism/``):
    * ``escape_mechanism.csv``   -- one row per source
    * ``rule_family_census.csv`` -- one row per (circuit_family, rule_family)
    * ``summary.json``           -- aggregates, input hashes, contract
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e45_development_grid.run import RULE_LIBRARY  # noqa: E402
from experiments.e46_window_landscape.run import RULE_SCOPE, load_root_states  # noqa: E402
from src.optimisation.certified_landscape import LandscapeState, StateGate  # noqa: E402

EXPERIMENT_ID = "E52_ESCAPE_MECHANISM_CENSUS_2026_10_22"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-22_escape_mechanism"
IDASTAR_CERTIFICATES = ROOT / "data" / "v14" / "e45_idastar_escape" / "certificates.jsonl"
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"

TWO_PI = 2.0 * math.pi
SELF_INVERSE = frozenset({"h", "x", "y", "z", "cx", "cy", "cz", "swap"})


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --------------------------------------------------------------------------- Part A


def rule_family_of(rule_id: str) -> str:
    """Collapse a rule id to the library family that owns it."""

    if rule_id.startswith("quartz_v1:"):
        return "quartz_v1"
    head, _, _ = rule_id.partition(".")
    return head or rule_id


def decompose_escape(witness: list[dict[str, Any]]) -> dict[str, Any]:
    deltas = [int(step.get("cost_delta", 0)) for step in witness]
    rule_ids = [str(step.get("rule_id", "")) for step in witness]
    families = [str(step.get("family", "")) or rule_family_of(rule_id) for step, rule_id in zip(witness, rule_ids)]
    neutral_prefix = 0
    for delta in deltas:
        if delta != 0:
            break
        neutral_prefix += 1
    reducing_steps = [
        {"index": index, "rule_id": rule_id, "family": families[index], "cost_delta": deltas[index]}
        for index, (rule_id, delta) in enumerate(zip(rule_ids, deltas))
        if delta < 0
    ]
    return {
        "path_length": len(witness),
        "neutral_prefix_length": neutral_prefix,
        "cost_deltas": deltas,
        "rule_ids": rule_ids,
        "rule_families": families,
        "reducing_steps": reducing_steps,
        "reducing_families": [step["family"] for step in reducing_steps],
        "reducing_rule_ids": [step["rule_id"] for step in reducing_steps],
        "net_delta": sum(deltas),
    }


def load_classification() -> dict[str, dict[str, str]]:
    with CLASSIFICATION.open(encoding="utf-8", newline="") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle)}


def part_a() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    classification = load_classification()
    records: list[dict[str, Any]] = []
    for line in IDASTAR_CERTIFICATES.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        payload = json.loads(line)
        source_id = payload["source_id"]
        certificate = payload["certificate"]
        meta = classification.get(source_id, {})
        witness = (certificate.get("witnesses") or {}).get("escape") or []
        record: dict[str, Any] = {
            "source_id": source_id,
            "circuit_family": meta.get("circuit_family", ""),
            "source_kind": meta.get("source_kind", ""),
            "n_qubits": int(meta.get("n_qubits") or 0),
            "baseline_cost": int(certificate.get("baseline_cost") or 0),
            "status": str(certificate.get("status", "")),
            "escape_depth": certificate.get("escape_depth"),
            "admissible_max_single_step_reduction": certificate.get("admissible_max_single_step_reduction"),
            "has_witness": bool(witness),
        }
        if witness:
            record.update(decompose_escape(witness))
        else:
            record.update(
                {
                    "path_length": 0,
                    "neutral_prefix_length": None,
                    "cost_deltas": [],
                    "rule_ids": [],
                    "rule_families": [],
                    "reducing_steps": [],
                    "reducing_families": [],
                    "reducing_rule_ids": [],
                    "net_delta": 0,
                }
            )
        records.append(record)
    aggregate = {
        "source_count": len(records),
        "with_witness": sum(1 for record in records if record["has_witness"]),
        "by_status": dict(collections.Counter(record["status"] for record in records)),
        "reducing_family_counts": dict(
            collections.Counter(
                family for record in records for family in record["reducing_families"]
            )
        ),
        "reducing_rule_counts": dict(
            collections.Counter(
                rule_id for record in records for rule_id in record["reducing_rule_ids"]
            )
        ),
        "rule_family_usage_all_steps": dict(
            collections.Counter(
                family for record in records for family in record["rule_families"]
            )
        ),
        "neutral_prefix_histogram": dict(
            sorted(
                collections.Counter(
                    record["neutral_prefix_length"]
                    for record in records
                    if record["has_witness"]
                ).items(),
                key=lambda item: (-1 if item[0] is None else item[0]),
            )
        ),
        "path_length_histogram": dict(
            sorted(
                collections.Counter(
                    record["path_length"] for record in records if record["has_witness"]
                ).items()
            )
        ),
    }
    return records, aggregate


# --------------------------------------------------------------------------- Part B


def disjoint(left: StateGate, right: StateGate) -> bool:
    return set(left.qubits).isdisjoint(right.qubits)


def cancellation_kind(left: StateGate, right: StateGate) -> str | None:
    """Classify a pair against the three ``pair_v1`` reduction modes.

    The frozen witnesses use exactly three reducing rules, so the census must
    cover exactly those: ``self_inverse`` (two identical self-inverse gates),
    ``rotation_merge`` (any two ``rz`` on the same wire merge into one), and
    ``rotation_zero`` (an ``rz`` whose angle is zero is deleted).
    """

    if left.name == right.name and left.qubits == right.qubits and left.name in SELF_INVERSE:
        return "self_inverse"
    if left.name == "rz" and right.name == "rz" and left.qubits == right.qubits:
        return "rotation_merge"
    return None


def single_gate_reduction(gate: StateGate) -> str | None:
    """Rules that delete one gate outright."""

    if gate.name == "rz" and gate.angle is not None:
        total = abs(gate.angle) % TWO_PI
        if min(total, TWO_PI - total) <= 1e-9:
            return "rotation_zero"
    return None


def cancellation_census(state: LandscapeState) -> dict[str, Any]:
    """Enumerate reducible pairs and their commutation distance.

    ``D`` is the smallest number of adjacent swaps of *commuting* gates needed
    to bring a reducible pair together.  A pair at positions ``i < j`` is
    feasible exactly when no gate strictly between them shares a wire with
    both, and then ``D = j - i - 1`` (every swap shortens the gap by one).
    A single-gate deletion has ``D = 0`` by definition.
    """

    gates = state.gates
    total = 0
    by_kind: collections.Counter[str] = collections.Counter()
    distances: list[int] = []
    blocked = 0
    for gate in gates:
        kind = single_gate_reduction(gate)
        if kind is not None:
            total += 1
            by_kind[kind] += 1
            distances.append(0)
    for index in range(len(gates)):
        for other in range(index + 1, len(gates)):
            kind = cancellation_kind(gates[index], gates[other])
            if kind is None:
                continue
            total += 1
            by_kind[kind] += 1
            feasible = True
            for middle in range(index + 1, other):
                if not disjoint(gates[middle], gates[index]) and not disjoint(gates[middle], gates[other]):
                    feasible = False
                    break
            if feasible:
                distances.append(other - index - 1)
            else:
                blocked += 1
    return {
        "reducible_pair_count": total,
        "reducible_by_kind": dict(by_kind),
        "min_commutation_distance": min(distances) if distances else None,
        "feasible_pair_count": len(distances),
        "blocked_pair_count": blocked,
        "commutation_distance_histogram": dict(sorted(collections.Counter(distances).items())),
    }


PART_B_STATES: list[dict[str, Any]] = []


def part_b() -> tuple[list[dict[str, Any]], dict[str, Any]]:
    roots = load_root_states()
    PART_B_STATES.clear()
    PART_B_STATES.extend(roots)
    rows: list[dict[str, Any]] = []
    for root in roots:
        census = cancellation_census(root["state"])
        rows.append(
            {
                "source_id": root["source_id"],
                "circuit_family": root["circuit_family"],
                "source_kind": root["source_kind"],
                "n_qubits": root["n_qubits"],
                "root_kind": root["root_kind"],
                "root_gate_count": root["root_gate_count"],
                "root_state_sha256": root["root_state_sha256"],
                **census,
            }
        )
    aggregate = {
        "root_count": len(rows),
        "roots_with_no_reducible_pair": sum(1 for row in rows if row["reducible_pair_count"] == 0),
        "roots_with_zero_distance_pair": sum(1 for row in rows if row["min_commutation_distance"] == 0),
        "roots_with_distant_feasible_pair": sum(
            1 for row in rows if row["min_commutation_distance"] not in (None, 0)
        ),
        "roots_with_only_blocked_pairs": sum(
            1 for row in rows if row["reducible_pair_count"] > 0 and row["min_commutation_distance"] is None
        ),
        "root_kind_counts": dict(collections.Counter(row["root_kind"] for row in rows)),
    }
    return rows, aggregate


# --------------------------------------------------------------------------- Part C


def part_c(
    part_a_records: list[dict[str, Any]], part_b_rows: list[dict[str, Any]]
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_source_b = {row["source_id"]: row for row in part_b_rows}
    merged: list[dict[str, Any]] = []
    for record in part_a_records:
        census = by_source_b.get(record["source_id"], {})
        reducing_families = record["reducing_families"]
        if record["status"] != "EXACT_ESCAPE":
            mechanism = "NO_ESCAPE"
        elif reducing_families and all(family == "pair_v1" for family in reducing_families):
            mechanism = "CANCELLATION_ONLY"
        elif reducing_families and all(family != "pair_v1" for family in reducing_families):
            mechanism = "QUARTZ_ONLY"
        elif reducing_families:
            mechanism = "MIXED"
        else:
            mechanism = "UNCLASSIFIED"
        distance = census.get("min_commutation_distance")
        predicted_depth = None if distance in (None, "") else int(distance) + 1
        if record["status"] != "EXACT_ESCAPE":
            depth_prediction = "NO_ESCAPE_PREDICTED" if predicted_depth is None else "FALSE_POSITIVE"
        elif predicted_depth is None:
            depth_prediction = "MISSED_ESCAPE"
        elif predicted_depth == record["escape_depth"]:
            depth_prediction = "MATCH"
        else:
            depth_prediction = "DEPTH_MISMATCH"
        merged.append(
            {
                "source_id": record["source_id"],
                "circuit_family": record["circuit_family"],
                "source_kind": record["source_kind"],
                "n_qubits": record["n_qubits"],
                "baseline_cost": record["baseline_cost"],
                "root_kind": census.get("root_kind", ""),
                "status": record["status"],
                "escape_depth": record["escape_depth"],
                "neutral_prefix_length": record["neutral_prefix_length"],
                "mechanism": mechanism,
                "reducing_rule_ids": "|".join(record["reducing_rule_ids"]),
                "path_rule_families": "|".join(record["rule_families"]),
                "reducible_pair_count": census.get("reducible_pair_count", ""),
                "min_commutation_distance": census.get("min_commutation_distance", ""),
                "predicted_depth": predicted_depth,
                "depth_prediction": depth_prediction,
            }
        )
    aggregate = {
        "mechanism_counts": dict(collections.Counter(row["mechanism"] for row in merged)),
        "mechanism_by_circuit_family": {
            family: dict(collections.Counter(row["mechanism"] for row in merged if row["circuit_family"] == family))
            for family in sorted({row["circuit_family"] for row in merged})
        },
        "escape_count": sum(1 for row in merged if row["status"] == "EXACT_ESCAPE"),
        "depth_prediction_counts": dict(collections.Counter(row["depth_prediction"] for row in merged)),
        "depth_prediction_agreement": sum(
            1 for row in merged if row["depth_prediction"] in {"MATCH", "NO_ESCAPE_PREDICTED"}
        ),
        "depth_prediction_disagreements": [
            {
                "source_id": row["source_id"],
                "circuit_family": row["circuit_family"],
                "status": row["status"],
                "escape_depth": row["escape_depth"],
                "predicted_depth": row["predicted_depth"],
                "min_commutation_distance": row["min_commutation_distance"],
            }
            for row in merged
            if row["depth_prediction"] not in {"MATCH", "NO_ESCAPE_PREDICTED"}
        ],
    }
    return merged, aggregate


def _gate_multiset(state: LandscapeState) -> collections.Counter:
    return collections.Counter((gate.name, gate.qubits, gate.angle) for gate in state.gates)


def classify_neutral_steps(root: LandscapeState, witness: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Replay a witness and label each step as reorder-only or rewrite.

    A neutral step is ``PURE_REORDER`` when the multiset of gates is unchanged,
    i.e. the optimizer only moved gates past each other.  It is ``REWRITE``
    when the multiset changes, i.e. a gate was replaced or a CX was reoriented.
    This separates an *order* barrier from a *content* barrier.
    """

    from src.optimisation.certified_landscape import iter_legal_actions  # noqa: PLC0415

    current = root
    labels: list[dict[str, Any]] = []
    for index, step in enumerate(witness):
        match = None
        for action in iter_legal_actions(current, RULE_LIBRARY, RULE_SCOPE):
            if (
                action.rule_id == step["rule_id"]
                and action.location == step["location"]
                and action.post_state_sha256 == step["post_state_sha256"]
            ):
                match = action
                break
        if match is None:
            labels.append({"index": index, "rule_id": str(step["rule_id"]), "label": "UNRESOLVED"})
            break
        if int(step.get("cost_delta", 0)) != 0:
            label = "REDUCING"
        elif _gate_multiset(current) == _gate_multiset(match.post_state):
            label = "PURE_REORDER"
        else:
            label = "REWRITE"
        labels.append(
            {
                "index": index,
                "rule_id": str(step["rule_id"]),
                "family": str(step.get("family", "")) or rule_family_of(str(step["rule_id"])),
                "cost_delta": int(step.get("cost_delta", 0)),
                "label": label,
            }
        )
        current = match.post_state
    return labels


def part_d_neutral_step_effects(part_a_records: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Classify the neutral prefix of every multi-step escape, plus the BV ladder."""

    from experiments.e45_development_grid.run import (  # noqa: PLC0415
        MAX_BASELINE_GATES,
        normalize_circuit,
        state_from_circuit,
    )
    from src.circuits.real_benchmarks import make_bernstein_vazirani  # noqa: PLC0415
    from src.optimisation.certified_landscape import search_landscape_horizons_compact  # noqa: PLC0415
    from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: PLC0415

    def run_case(label: str, state: LandscapeState, horizon: int) -> dict[str, Any] | None:
        result = search_landscape_horizons_compact(
            state,
            RULE_LIBRARY,
            [horizon],
            state_budget=200_000,
            rule_scope=RULE_SCOPE,
            time_budget_seconds=120.0,
        )
        entry = result[str(horizon)]
        witness = (entry.get("witnesses") or {}).get("escape") or []
        if not witness:
            return None
        labels = classify_neutral_steps(state, witness)
        neutral = [item for item in labels if item.get("label") in {"PURE_REORDER", "REWRITE"}]
        return {
            "case": label,
            "escape_depth": len(witness),
            "neutral_steps": len(neutral),
            "pure_reorder_steps": sum(1 for item in neutral if item["label"] == "PURE_REORDER"),
            "rewrite_steps": sum(1 for item in neutral if item["label"] == "REWRITE"),
            "neutral_rule_ids": "|".join(item["rule_id"] for item in neutral),
            "neutral_labels": "|".join(item["label"] for item in neutral),
            "barrier_kind": (
                "ORDER_ONLY"
                if neutral and all(item["label"] == "PURE_REORDER" for item in neutral)
                else "CONTENT"
                if neutral
                else "NONE"
            ),
        }

    rows: list[dict[str, Any]] = []
    for record in part_a_records:
        if record["status"] != "EXACT_ESCAPE" or int(record["escape_depth"] or 0) < 2:
            continue
        root = next((item for item in PART_B_STATES if item["source_id"] == record["source_id"]), None)
        if root is None:
            continue
        outcome = run_case(record["source_id"], root["state"], int(record["escape_depth"]))
        if outcome is not None:
            outcome["circuit_family"] = record["circuit_family"]
            rows.append(outcome)

    for n_qubits in (4, 6, 8, 10, 12, 14, 16):
        source = make_bernstein_vazirani(n_qubits, seed=42)
        normalized, _info = normalize_circuit(source)
        if normalized is None:
            continue
        if int(normalized.size()) > MAX_BASELINE_GATES:
            baseline = normalized
        else:
            baseline = GreedyGateCancellation(
                max_iterations=50, fidelity_threshold=1.0, success_reduction=0.0
            ).optimize(normalized).optimized_circuit
        state = state_from_circuit(baseline)
        for horizon in range(2, 9):
            outcome = run_case(f"bv_{n_qubits}", state, horizon)
            if outcome is not None:
                outcome["circuit_family"] = "BernsteinVazirani"
                outcome["n_qubits"] = n_qubits
                rows.append(outcome)
                break

    aggregate = {
        "cases": len(rows),
        "barrier_kind_counts": dict(collections.Counter(row["barrier_kind"] for row in rows)),
        "by_family": {
            family: dict(collections.Counter(row["barrier_kind"] for row in rows if row["circuit_family"] == family))
            for family in sorted({row["circuit_family"] for row in rows})
        },
        "neutral_rule_counts": dict(
            collections.Counter(
                rule_id for row in rows for rule_id in row["neutral_rule_ids"].split("|") if rule_id
            )
        ),
    }
    return rows, aggregate


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)

    part_a_records, part_a_aggregate = part_a()
    print(f"[E52] part A: {part_a_aggregate['source_count']} certificates, "
          f"{part_a_aggregate['with_witness']} witnesses", flush=True)
    print(f"[E52] part A reducing families: {part_a_aggregate['reducing_family_counts']}", flush=True)

    part_b_rows, part_b_aggregate = part_b()
    print(f"[E52] part B: {part_b_aggregate}", flush=True)

    merged, part_c_aggregate = part_c(part_a_records, part_b_rows)
    print(f"[E52] part C: {part_c_aggregate['mechanism_counts']}", flush=True)

    part_d_rows, part_d_aggregate = part_d_neutral_step_effects(part_a_records)
    print(f"[E52] part D: {part_d_aggregate['barrier_kind_counts']}", flush=True)
    write_csv(OUTPUT_ROOT / "neutral_step_effects.csv", part_d_rows)

    write_csv(OUTPUT_ROOT / "escape_mechanism.csv", merged)
    write_csv(
        OUTPUT_ROOT / "reduction_census.csv",
        [
            {key: (json.dumps(value) if isinstance(value, (dict, list)) else value) for key, value in row.items()}
            for row in part_b_rows
        ],
    )
    census_rows: list[dict[str, Any]] = []
    for (circuit_family, rule_family), count in sorted(
        collections.Counter(
            (record["circuit_family"], family)
            for record in part_a_records
            for family in record["reducing_families"]
        ).items()
    ):
        census_rows.append(
            {"circuit_family": circuit_family, "reducing_rule_family": rule_family, "escape_count": count}
        )
    write_csv(OUTPUT_ROOT / "rule_family_census.csv", census_rows)

    summary = {
        "experiment_id": EXPERIMENT_ID,
        "date": "2026-10-22",
        "contract": {
            "inputs": {
                "idastar_certificates": {
                    "path": str(IDASTAR_CERTIFICATES.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": sha256(IDASTAR_CERTIFICATES),
                },
                "classification_complete": {
                    "path": str(CLASSIFICATION.relative_to(ROOT)).replace("\\", "/"),
                    "sha256": sha256(CLASSIFICATION),
                },
            },
            "root_states": "rebuilt via experiments.e46_window_landscape.run.load_root_states (hash-checked)",
            "search_rerun": False,
            "writes": "docs/review/science_boost/2026-10-22_escape_mechanism/ only",
        },
        "part_a_escape_decomposition": part_a_aggregate,
        "part_b_cancellation_census": part_b_aggregate,
        "part_c_mechanism_split": part_c_aggregate,
        "part_d_neutral_step_effects": part_d_aggregate,
        "reading": (
            "Part C separates escapes whose reducing step is Phase-1 cancellation (pair_v1) from "
            "escapes whose reducing step is a Quartz rewrite. If the Quartz share dominates, the "
            "certified landscape measures rewrite-library reachability, not cancellation reachability, "
            "and the two narratives in the manuscript must be reported as two mechanisms."
        ),
    }
    (OUTPUT_ROOT / "summary.json").write_text(json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"[E52] wrote {OUTPUT_ROOT}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
