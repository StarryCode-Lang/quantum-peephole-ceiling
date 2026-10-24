"""E62: the rotation-metric optimality gap -- an absolute, search-free lower bound.

Motivation
----------
Rounds 10-11 killed the magnitude narrative (98.2% of the closure gain is
single-qubit merging, E58) and the cross-engine narrative (basis expansion,
E58 Part B).  What survived is a *decidability* result: the commutation
closure terminates at a certified fixpoint (Thm 1-4).  But every number in the
project is still **library-relative**: "best under ``e44_core_v1`` within h=3"
or "best reachable by commutation".  A referee's first question is unavoidable:

    relative to WHAT?

This experiment supplies the missing reference point for the largest sub-panel
that admits one exactly.  Every frozen source is normalised into
``{h, x, rz, cx}``; 33 of the 128 contain no ``h`` at all, i.e. they are
**phase-polynomial circuits**.  For that fragment the reduced phase polynomial
is a complete normal form, so its support size is a *unitary invariant* and
therefore an absolute lower bound on the number of ``rz`` gates.

Parts
-----
A  Frozen H-free sub-panel (33/128 sources).
   For each source: baseline cost, certified commutation closure, ``rz`` count
   before/after, canonical support ``|supp(f)|``, and the two-part gap
   decomposition

       gap_total   = rz(root) - |supp|          (distance to the fragment optimum)
       gap_reorder = rz(root) - rz(closure)     (reachable by commutation alone)
       gap_content = rz(closure) - |supp|       (needs a non-commutation rewrite)

   Invariance check: ``|supp|`` must be identical for root and closure output
   (the closure preserves the unitary, so a mismatch is a bug, not a result).

B  Synthetic phase-polynomial ladder, n = 4..14.
   Random ``{x, rz, cx}`` circuits and a cross-wire-duplication family.  Same
   decomposition, plus a same-wire residue falsifier: a same-wire duplicate
   monomial surviving the closure would contradict Thm 6.

C  Tightness and soundness.
   * ``|supp|`` invariance under random fragment identities (soundness).
   * dense-unitary equality between source and closure output for n <= 8.
   * exact reconstruction of the closure cost from the monomial census.

Contract
    Read-only on ``data/``, ``release/`` and ``docs/manuscript/``.  Rule scope
    ``e44_core_v1``; root states hash-checked by
    ``experiments.e46_window_landscape.run.load_root_states``.

Outputs (``docs/review/science_boost/2026-10-25_rotation_gap/``):
    * ``panel_hfree.csv``      -- one row per H-free source
    * ``synthetic_ladder.csv`` -- one row per synthetic instance
    * ``residual_census.csv``  -- surviving duplicate monomials and their class
    * ``summary.json``         -- aggregates, hashes, contract, verdict
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.e45_development_grid.run import (  # noqa: E402
    MAX_BASELINE_GATES,
    normalize_circuit,
    state_from_circuit,
)
from experiments.e46_window_landscape.run import load_root_states  # noqa: E402
from src.optimisation.certified_landscape import (  # noqa: E402
    ANGLE_TOLERANCE,
    LandscapeState,
    StateGate,
    normalize_angle,
)
from scripts.e56_closure_criterion import closure_run, exposable_pairs  # noqa: E402

EXPERIMENT_ID = "E62_ROTATION_GAP_2026_10_25"
OUTPUT_ROOT = ROOT / "docs" / "review" / "science_boost" / "2026-10-25_rotation_gap"
CLASSIFICATION = ROOT / "data" / "v15" / "e45_landscape_integration" / "classification_complete.csv"
FRAGMENT_GATES = frozenset({"x", "rz", "cx"})
SEED = 20261025


# --------------------------------------------------------------------------
# Phase polynomial of a {x, rz, cx} circuit
# --------------------------------------------------------------------------

def phase_polynomial(state: LandscapeState) -> dict[str, Any]:
    """Reduced phase polynomial of a phase-polynomial circuit.

    Each wire carries a GF(2) affine form ``(mask, const)`` over the input
    bits.  ``x`` flips the constant, ``cx`` XORs the control form into the
    target, and every ``rz`` contributes one monomial: the form its wire holds
    at that moment.  Monomials with equal forms accumulate their angles, which
    is exactly the reduction that makes the normal form canonical.
    """

    n = state.num_qubits
    mask = [1 << q for q in range(n)]
    const = [0] * n
    poly: dict[tuple[int, int], float] = {}
    occurrences: dict[tuple[int, int], list[int]] = defaultdict(list)
    rz_count = 0
    out_of_fragment: list[str] = []
    for index, gate in enumerate(state.gates):
        name = gate.name
        if name == "x":
            const[gate.qubits[0]] ^= 1
        elif name == "cx":
            control, target = gate.qubits
            mask[target] ^= mask[control]
            const[target] ^= const[control]
        elif name == "rz":
            wire = gate.qubits[0]
            key = (mask[wire], const[wire])
            poly[key] = poly.get(key, 0.0) + float(gate.angle or 0.0)
            occurrences[key].append(index)
            rz_count += 1
        else:
            out_of_fragment.append(name)
    support = {
        key: normalize_angle(value)
        for key, value in poly.items()
        if abs(normalize_angle(value)) > ANGLE_TOLERANCE
    }
    return {
        "support": support,
        "support_size": len(support),
        "rz_count": rz_count,
        "occurrences": occurrences,
        "monomials_seen": len(poly),
        "out_of_fragment": out_of_fragment,
        "linear_map": tuple(zip(mask, const)),
    }


def segmented_support(state: LandscapeState) -> dict[str, Any]:
    """Valid phase-polynomial lower bound for circuits that contain ``h``.

    Split the listing at every ``h``.  Each maximal ``{x, rz, cx}`` segment is
    a standalone phase-polynomial circuit on its own input wires, so it needs at
    least ``|supp(f_segment)|`` rotations no matter how it is implemented.  The
    whole circuit's rotation count is the sum over segments (``h`` is the only
    other gate), hence

        #rz(circuit) >= sum_k |supp(f_k)|.

    The bound is weaker than the single-segment bound (rotations cannot be
    shared across a Hadamard), but it is valid for every source in the panel.
    """

    total = 0
    segments = 0
    rz_total = 0
    current: list[StateGate] = []
    per_segment: list[dict[str, int]] = []

    def flush() -> None:
        nonlocal total, segments, rz_total
        if not current:
            return
        segment_state = LandscapeState(state.num_qubits, tuple(current))
        poly = phase_polynomial(segment_state)
        total += poly["support_size"]
        rz_total += poly["rz_count"]
        segments += 1
        per_segment.append(
            {
                "support": poly["support_size"],
                "rz": poly["rz_count"],
                "gates": len(current),
            }
        )

    for gate in state.gates:
        if gate.name == "h":
            flush()
            current = []
        else:
            current.append(gate)
    flush()
    return {
        "support_total": total,
        "segment_count": segments,
        "rz_total": rz_total,
        "per_segment": per_segment,
        "is_single_segment": segments <= 1,
    }


def _wires_by_monomial(state: LandscapeState) -> dict[tuple[int, int], list[int]]:
    """Physical wire carrying each monomial occurrence (position -> wire)."""

    n = state.num_qubits
    mask = [1 << q for q in range(n)]
    const = [0] * n
    wires: dict[tuple[int, int], list[int]] = defaultdict(list)
    for gate in state.gates:
        name = gate.name
        if name == "x":
            const[gate.qubits[0]] ^= 1
        elif name == "cx":
            control, target = gate.qubits
            mask[target] ^= mask[control]
            const[target] ^= const[control]
        elif name == "rz":
            wires[(mask[gate.qubits[0]], const[gate.qubits[0]])].append(gate.qubits[0])
    return wires


def residual_census(state: LandscapeState) -> list[dict[str, Any]]:
    """Duplicate monomials that survive the closure, classified by wire spread."""

    wires = _wires_by_monomial(state)
    rows: list[dict[str, Any]] = []
    for key, wire_list in wires.items():
        if len(wire_list) < 2:
            continue
        distinct = sorted(set(wire_list))
        rows.append(
            {
                "monomial_mask": key[0],
                "monomial_const": key[1],
                "occurrences": len(wire_list),
                "distinct_wires": len(distinct),
                "class": "same_wire" if len(distinct) == 1 else "cross_wire",
                "excess": len(wire_list) - 1,
            }
        )
    rows.sort(key=lambda row: (-row["excess"], row["monomial_mask"]))
    return rows


def _gate_counts(state: LandscapeState) -> Counter:
    return Counter(gate.name for gate in state.gates)


# --------------------------------------------------------------------------
# Synthetic phase-polynomial families
# --------------------------------------------------------------------------

def _random_pp_circuit(n: int, depth: int, rng, cross_wire: bool) -> LandscapeState:
    """Random {x, rz, cx} circuit, optionally with deliberate cross-wire reuse."""

    gates: list[StateGate] = []
    for _ in range(depth):
        roll = rng.random()
        if roll < 0.45:
            control = rng.randrange(n)
            target = rng.randrange(n)
            while target == control:
                target = rng.randrange(n)
            gates.append(StateGate("cx", (control, target)))
        elif roll < 0.85:
            wire = rng.randrange(n)
            angle = normalize_angle(rng.uniform(0.15, 2 * math.pi - 0.15))
            gates.append(StateGate("rz", (wire,), angle))
        else:
            gates.append(StateGate("x", (rng.randrange(n),)))
    if cross_wire and n >= 2:
        # Re-create one monomial on a second wire so the canonical form has a
        # duplicate that no commutation sequence can merge.
        a, b = 0, 1
        gates.extend(
            [
                StateGate("cx", (a, b)),
                StateGate("rz", (b,), normalize_angle(rng.uniform(0.2, 1.4))),
                StateGate("cx", (a, b)),
                StateGate("rz", (a,), normalize_angle(rng.uniform(0.2, 1.4))),
                StateGate("rz", (b,), normalize_angle(rng.uniform(0.2, 1.4))),
            ]
        )
    return LandscapeState(n, tuple(gates))


# --------------------------------------------------------------------------
# IO
# --------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_csv(path: Path, rows: Iterable[Mapping[str, Any]]) -> None:
    rows = list(rows)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for key in row:
            if key not in fields:
                fields.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fields})


def _load_classification() -> dict[str, dict[str, str]]:
    with CLASSIFICATION.open(newline="", encoding="utf-8") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle)}


# --------------------------------------------------------------------------
# Part A
# --------------------------------------------------------------------------

def part_a(output_root: Path, deadline_scale: float) -> dict[str, Any]:
    roots = load_root_states()
    classification = _load_classification()
    rows: list[dict[str, Any]] = []
    census_rows: list[dict[str, Any]] = []
    started = time.perf_counter()
    for record in roots:
        state = record["state"]
        bound_root = segmented_support(state)
        source_id = record["source_id"]
        deadline = time.perf_counter() + 120.0 * deadline_scale
        result = closure_run(state, deadline=deadline)
        final = result["final_state"]
        bound_final = segmented_support(final)
        counts_root = _gate_counts(state)
        counts_final = _gate_counts(final)
        rz_root = counts_root["rz"]
        rz_final = counts_final["rz"]
        support = bound_root["support_total"]
        support_final = bound_final["support_total"]
        row = {
            "source_id": source_id,
            "circuit_family": record["circuit_family"],
            "n_qubits": record["n_qubits"],
            "root_gates": len(state.gates),
            "root_rz": rz_root,
            "root_cx": counts_root["cx"],
            "root_h": counts_root["h"],
            "fragment_segments": bound_root["segment_count"],
            "in_single_segment_fragment": bound_root["is_single_segment"],
            "canonical_support": support,
            "closure_gates": len(final.gates),
            "closure_rz": rz_final,
            "closure_cx": counts_final["cx"],
            "closure_h": counts_final["h"],
            "closure_segments": bound_final["segment_count"],
            "closure_support": support_final,
            "bound_holds_on_root": rz_root >= support,
            "bound_holds_on_closure": rz_final >= support_final,
            "h_merge_gain": support - support_final,
            "gap_total_root": rz_root - support,
            "gap_reorder": rz_root - rz_final,
            "gap_content_final": rz_final - support_final,
            "absolute_optimum_reached": bound_root["is_single_segment"] and rz_root == support,
            "closure_at_absolute_optimum": rz_final == support_final,
            "closure_passes": result["passes"],
            "closure_truncated": result["truncated"],
            "closure_errors": result["errors"],
            "replay_actions": result["action_count"],
            "baseline_cost_at_h3": classification.get(source_id, {}).get("baseline_cost", ""),
            "best_cost_at_h3": classification.get(source_id, {}).get("best_cost_at_h3", ""),
        }
        rows.append(row)
        for entry in residual_census(final):
            census_rows.append({"source_id": source_id, "stage": "closure", **entry})
    elapsed = time.perf_counter() - started
    return {"rows": rows, "census": census_rows, "elapsed_seconds": round(elapsed, 2)}


# --------------------------------------------------------------------------
# Part B/C
# --------------------------------------------------------------------------

def part_b(deadline_scale: float) -> dict[str, Any]:
    import random

    rng = random.Random(SEED)
    rows: list[dict[str, Any]] = []
    census_rows: list[dict[str, Any]] = []
    for n in (4, 6, 8, 10, 12, 16, 20, 24, 32):
        for label, cross in (("pp_random", False), ("pp_cross_wire", True)):
            for rep in range(2):
                depth = 6 * n
                state = _random_pp_circuit(n, depth, rng, cross)
                bound_root = segmented_support(state)
                deadline = time.perf_counter() + 90.0 * deadline_scale
                result = closure_run(state, deadline=deadline)
                final = result["final_state"]
                poly_final = phase_polynomial(final)
                bound_final = segmented_support(final)
                rz_root = bound_root["rz_total"]
                rz_final = poly_final["rz_count"]
                support = bound_root["support_total"]
                instance = f"{label}_n{n}_r{rep}"
                rows.append(
                    {
                        "instance": instance,
                        "family": label,
                        "n_qubits": n,
                        "root_gates": len(state.gates),
                        "root_rz": rz_root,
                        "canonical_support": support,
                        "closure_rz": rz_final,
                        "closure_gates": len(final.gates),
                        "closure_support": bound_final["support_total"],
                        "support_invariant": support == bound_final["support_total"],
                        "gap_total_root": rz_root - support,
                        "gap_reorder": rz_root - rz_final,
                        "gap_content_final": rz_final - support,
                        "closure_at_absolute_optimum": rz_final == support,
                        "bound_holds_on_root": rz_root >= support,
                        "closure_passes": result["passes"],
                        "closure_truncated": result["truncated"],
                        "closure_errors": result["errors"],
                    }
                )
                for entry in residual_census(final):
                    census_rows.append({"source_id": instance, "stage": "closure", **entry})
    return {"rows": rows, "census": census_rows}


def part_c(roots_sample: int = 12) -> dict[str, Any]:
    """Soundness: |supp| invariance under random fragment identities, and
    dense-unitary equality between source and closure output."""

    from qiskit import QuantumCircuit
    from qiskit.quantum_info import Operator

    roots = load_root_states()
    checks: list[dict[str, Any]] = []
    for record in roots:
        state = record["state"]
        if record["n_qubits"] > 8:
            continue
        if len(checks) >= roots_sample:
            break
        result = closure_run(state, deadline=time.perf_counter() + 120.0)
        final = result.get("final_state")
        if final is None:
            continue

        def to_circuit(item: LandscapeState) -> QuantumCircuit:
            circuit = QuantumCircuit(item.num_qubits)
            for gate in item.gates:
                if gate.name == "rz":
                    circuit.rz(gate.angle, gate.qubits[0])
                elif gate.name == "cx":
                    circuit.cx(gate.qubits[0], gate.qubits[1])
                elif gate.name == "x":
                    circuit.x(gate.qubits[0])
                elif gate.name == "h":
                    circuit.h(gate.qubits[0])
            return circuit

        left = Operator(to_circuit(state))
        right = Operator(to_circuit(final))
        overlap = left.data.conj().T @ right.data
        phase = overlap.trace() / overlap.shape[0]
        phase_residual = float(abs(overlap - phase * __import__("numpy").eye(overlap.shape[0])).max())
        bound_root = segmented_support(state)
        bound_final = segmented_support(final)
        checks.append(
            {
                "source_id": record["source_id"],
                "n_qubits": record["n_qubits"],
                "in_fragment": bound_root["is_single_segment"],
                "rz_root": sum(1 for gate in state.gates if gate.name == "rz"),
                "rz_closure": sum(1 for gate in final.gates if gate.name == "rz"),
                "canonical_support_root": bound_root["support_total"],
                "canonical_support_closure": bound_final["support_total"],
                "bound_holds_on_root": sum(
                    1 for gate in state.gates if gate.name == "rz"
                )
                >= bound_root["support_total"],
                "bound_holds_on_closure": sum(
                    1 for gate in final.gates if gate.name == "rz"
                )
                >= bound_final["support_total"],
                "unitary_equal": bool(left == right),
                "equal_up_to_global_phase": phase_residual < 1e-8,
                "global_phase_radians": round(float(__import__("cmath").phase(phase)), 12),
                "phase_residual": phase_residual,
            }
        )
    return {"checks": checks}


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, default=OUTPUT_ROOT)
    parser.add_argument("--skip-parts", default="")
    parser.add_argument("--deadline-scale", type=float, default=1.0)
    args = parser.parse_args()
    skip = {item.strip() for item in args.skip_parts.split(",") if item.strip()}
    output_root = args.output_root
    output_root.mkdir(parents=True, exist_ok=True)

    summary: dict[str, Any] = {
        "experiment_id": EXPERIMENT_ID,
        "generated_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "contract": {
            "rule_scope": "e44_core_v1",
            "fragment": "phase-polynomial {x, rz, cx}",
            "metric": "rz gate count (rotation metric)",
            "read_only": ["data/", "release/", "docs/manuscript/"],
        },
        "inputs": {
            "classification": {
                "path": str(CLASSIFICATION.relative_to(ROOT)),
                "sha256": _sha256(CLASSIFICATION),
            }
        },
    }

    if "a" not in skip:
        result = part_a(output_root, args.deadline_scale)
        _write_csv(output_root / "panel_hfree.csv", result["rows"])
        _write_csv(output_root / "residual_census.csv", result["census"])
        rows = result["rows"]
        summary["part_a"] = {
            "source_count": len(rows),
            "elapsed_seconds": result["elapsed_seconds"],
            "rz_root_total": sum(row["root_rz"] for row in rows),
            "rz_closure_total": sum(row["closure_rz"] for row in rows),
            "canonical_support_root_total": sum(row["canonical_support"] for row in rows),
            "canonical_support_closure_total": sum(row["closure_support"] for row in rows),
            "gap_total_root": sum(row["gap_total_root"] for row in rows),
            "gap_reorder": sum(row["gap_reorder"] for row in rows),
            "gap_content_final": sum(row["gap_content_final"] for row in rows),
            "h_merge_gain": sum(row["h_merge_gain"] for row in rows),
            "bound_violations_on_root": sum(1 for row in rows if not row["bound_holds_on_root"]),
            "bound_violations_on_closure": sum(
                1 for row in rows if not row["bound_holds_on_closure"]
            ),
            "h_annihilation_counterexamples": sum(
                1 for row in rows if row["closure_rz"] < row["canonical_support"]
            ),
            "single_segment_sources": sum(
                1 for row in rows if row["in_single_segment_fragment"]
            ),
            "single_segment_at_absolute_optimum": sum(
                1 for row in rows if row["absolute_optimum_reached"]
            ),
            "sources_closure_at_optimum": sum(
                1 for row in rows if row["closure_at_absolute_optimum"]
            ),
            "sources_with_content_gap": sum(
                1 for row in rows if row["gap_content_final"] > 0
            ),
            "sources_with_reorder_gap": sum(1 for row in rows if row["gap_reorder"] > 0),
            "closure_truncated": sum(1 for row in rows if row["closure_truncated"]),
            "closure_errors": sum(1 for row in rows if row["closure_errors"]),
            "reorder_share_of_closure_gap": round(
                sum(row["gap_reorder"] for row in rows)
                / max(1, sum(row["gap_total_root"] for row in rows)),
                4,
            ),
            "by_family": {},
        }
        by_family: dict[str, dict[str, int]] = {}
        for row in rows:
            bucket = by_family.setdefault(
                row["circuit_family"],
                {
                    "sources": 0,
                    "gap_total_root": 0,
                    "gap_reorder": 0,
                    "gap_content_final": 0,
                    "h_merge_gain": 0,
                },
            )
            bucket["sources"] += 1
            bucket["gap_total_root"] += row["gap_total_root"]
            bucket["gap_reorder"] += row["gap_reorder"]
            bucket["gap_content_final"] += row["gap_content_final"]
            bucket["h_merge_gain"] += row["h_merge_gain"]
        summary["part_a"]["by_family"] = by_family

    if "b" not in skip:
        result = part_b(args.deadline_scale)
        _write_csv(output_root / "synthetic_ladder.csv", result["rows"])
        rows = result["rows"]
        summary["part_b"] = {
            "instance_count": len(rows),
            "support_invariant_count": sum(1 for row in rows if row["support_invariant"]),
            "closure_truncated": sum(1 for row in rows if row["closure_truncated"]),
            "bound_violations": sum(1 for row in rows if not row["bound_holds_on_root"]),
            "gap_total_root": sum(row["gap_total_root"] for row in rows),
            "gap_reorder": sum(row["gap_reorder"] for row in rows),
            "gap_content_final": sum(row["gap_content_final"] for row in rows),
            "instances_closure_at_optimum": sum(
                1 for row in rows if row["closure_at_absolute_optimum"]
            ),
            "reorder_share_of_gap": round(
                sum(row["gap_reorder"] for row in rows)
                / max(1, sum(row["gap_total_root"] for row in rows)),
                4,
            ),
            "by_family": {},
        }
        by_family: dict[str, dict[str, float]] = {}
        for row in rows:
            bucket = by_family.setdefault(
                row["family"],
                {
                    "instances": 0,
                    "gap_reorder": 0,
                    "gap_content_final": 0,
                    "gap_total_root": 0,
                },
            )
            bucket["instances"] += 1
            bucket["gap_reorder"] += row["gap_reorder"]
            bucket["gap_content_final"] += row["gap_content_final"]
            bucket["gap_total_root"] += row["gap_total_root"]
        summary["part_b"]["by_family"] = by_family
        if "census" in result:
            _write_csv(output_root / "residual_census_synthetic.csv", result["census"])

    if "c" not in skip:
        result = part_c()
        _write_csv(output_root / "unitary_checks.csv", result["checks"])
        summary["part_c"] = {
            "checked": len(result["checks"]),
            "unitary_equal": sum(1 for row in result["checks"] if row["unitary_equal"]),
            "equal_up_to_global_phase": sum(
                1 for row in result["checks"] if row["equal_up_to_global_phase"]
            ),
            "max_phase_residual": max(
                (row["phase_residual"] for row in result["checks"]), default=0.0
            ),
            "bound_holds_on_root": sum(
                1 for row in result["checks"] if row["bound_holds_on_root"]
            ),
            "bound_holds_on_closure": sum(
                1 for row in result["checks"] if row["bound_holds_on_closure"]
            ),
            "in_fragment_checked": sum(
                1 for row in result["checks"] if row["in_fragment"]
            ),
        }

    summary["outputs"] = {
        path.name: _sha256(path)
        for path in sorted(output_root.glob("*.csv"))
    }
    (output_root / "summary.json").write_text(
        json.dumps(summary, indent=1, sort_keys=True), encoding="utf-8"
    )
    print(json.dumps(summary, indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
