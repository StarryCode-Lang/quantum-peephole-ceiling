"""Derive two-sided certified gate-count intervals for the v15 fixed panel.

Purpose
-------
The v15 readiness verdict records 34 ``CLASSIFICATION_EXACT_EXTRAS_BOUNDED``
cells: their best cost is bounded *above* by a certified witness path, but no
lower bound is published.  This script adds a rigorous, per-instance lower
bound that is independent of the search budget, so each of those 34 cells
becomes a two-sided certified interval instead of a one-sided witness bound.

Method (certified, not heuristic)
--------------------------------
Let ``cost(s) = len(s.gates)`` (the engine's own cost, see
``src/optimisation/certified_landscape.py``).  Every legal action in rule scope
``e44_core_v1`` is one of

  * a Quartz rule application (source pattern -> target pattern),
  * a ``pair_v1`` adjacent cancellation / rotation merge,
  * an ``exchange.*`` commutation (cost-neutral).

For a gate name ``g`` define

    r_g = max over legal actions a of max(0, n_g(pre(a)) - n_g(post(a)))

the largest per-action decrease of the count of gates named ``g``.  Then for
any H-step trajectory s_0 -> ... -> s_H,

    n_g(s_H) >= n_g(s_0) - H * r_g          (each step decreases by at most r_g)

and therefore

    cost(s_H) >= sum_g max(0, n_g(s_0) - H * r_g)  =: LB_class(H)

which is a valid lower bound on the minimum cost reachable within H actions.
The coarser aggregate bound

    LB_total(H) = cost(s_0) - H * D,   D = max over actions of (removed gates)

is also computed; the reported bound is the maximum of the two.

Provenance
----------
Inputs are read-only:
  * ``data/v13/e43_quartz_rule_import/generation_a/rule_library.json``
  * ``data/v14/e45_full_development/qasm/*.qasm`` (128 normalized listings)
  * ``data/v15/e45_landscape_integration/classification_complete.csv``
  * ``release/v15_readiness_verdict.json``

No frozen file is modified.  Output goes to a dated directory outside
``data/`` and ``release/``.

Usage
-----
    python scripts/derive_v15_certified_lower_bounds.py [--output-root DIR]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RULE_LIBRARY = ROOT / "data/v13/e43_quartz_rule_import/generation_a/rule_library.json"
QASM_DIR = ROOT / "data/v14/e45_full_development/qasm"
NORMALIZATION_MANIFEST = ROOT / "data/v14/e45_full_development/normalization_manifest.csv"
CLASSIFICATION = ROOT / "data/v15/e45_landscape_integration/classification_complete.csv"
VERDICT = ROOT / "release/v15_readiness_verdict.json"
DEFAULT_OUT = ROOT / "docs/review/science_boost/2026-10-17_certified_lower_bounds"

HORIZON = 3  # frozen E45 full-development configuration (h3_b64_s200k)
SELF_INVERSE = frozenset({"h", "x", "y", "z", "cx", "cz", "swap"})
ROTATIONS = frozenset({"rx", "ry", "rz"})

# Matches both bare gates ("h q[0];") and parameterized gates ("rz(0.5) q[0];").
QASM_GATE_RE = re.compile(r"^\s*([a-z][a-z0-9_]*)\s*(?:\([^)]*\))?\s+.*;\s*$")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def core_rules() -> list[dict]:
    library = json.loads(RULE_LIBRARY.read_text(encoding="utf-8"))
    rules = [rule for rule in library["rules"] if rule.get("rule_family") == "quartz_v1"]
    core = [
        rule
        for rule in rules
        if int(rule["source"]["num_qubits"]) <= 2
        and len(rule["source"]["operations"]) <= 4
        and len(rule["target"]["operations"]) <= 6
    ]
    return core


def per_gate_action_ceiling(rules: list[dict], gate_names: set[str]) -> dict[str, int]:
    """Maximum per-action decrease for each gate name, over all legal actions."""

    ceiling: dict[str, int] = {name: 0 for name in gate_names}

    # Quartz rules: count operations by name on both sides.
    for rule in rules:
        source = Counter(op["name"] for op in rule["source"]["operations"])
        target = Counter(op["name"] for op in rule["target"]["operations"])
        for name in set(source) | set(target):
            drop = max(0, source.get(name, 0) - target.get(name, 0))
            if drop:
                ceiling[name] = max(ceiling.get(name, 0), drop)

    # pair_v1 self-inverse cancellation removes two gates of the same name.
    for name in SELF_INVERSE:
        ceiling[name] = max(ceiling.get(name, 0), 2)
    # pair_v1 t/tdg and s/sdg cancellation removes one gate of each name.
    for left, right in (("t", "tdg"), ("s", "sdg")):
        ceiling[left] = max(ceiling.get(left, 0), 1)
        ceiling[right] = max(ceiling.get(right, 0), 1)
    # pair_v1 rotation_zero removes two rotations; rotation_merge removes one.
    for name in ROTATIONS:
        ceiling[name] = max(ceiling.get(name, 0), 2)
    return ceiling


def aggregate_action_ceiling(rules: list[dict]) -> int:
    """Coarse ceiling on the total gate-count drop of a single action."""

    worst = 2  # pair_v1 self-inverse / rotation_zero remove two gates
    for rule in rules:
        drop = len(rule["source"]["operations"]) - len(rule["target"]["operations"])
        worst = max(worst, drop)
    for name in ROTATIONS:
        worst = max(worst, 1)
    return max(0, int(worst))


def parse_qasm_counts(path: Path) -> tuple[int, Counter]:
    """Return (num_qubits, Counter of gate names) for a normalized listing."""

    num_qubits = 0
    counts: Counter = Counter()
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("//") or not stripped:
            continue
        if stripped.startswith("qreg"):
            match = re.search(r"qreg\s+\w+\[(\d+)\]", stripped)
            if match:
                num_qubits = int(match.group(1))
            continue
        if stripped.startswith(("OPENQASM", "include", "creg", "barrier")):
            continue
        match = QASM_GATE_RE.match(stripped)
        if match:
            counts[match.group(1)] += 1
    return num_qubits, counts


def reconstruct_root_states(manifest: Path) -> dict[str, tuple[int, Counter]]:
    """Rebuild the frozen E45 root listings exactly as the v14 run did.

    The certified landscape does not search the normalized circuit: it searches
    ``state_from_circuit(Greedy(normalize(source)))`` (see
    ``experiments/e45_development_grid/run.py`` line 736).  Reproducing that
    pipeline is the only way to obtain per-gate-name counts for the true root
    state, so the per-class lower bound applies to the object the frozen
    certificates actually describe.
    """

    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from qiskit import QuantumCircuit  # noqa: PLC0415

    from experiments.e45_development_grid.run import (  # noqa: PLC0415
        MAX_BASELINE_GATES,
        circuit_from_row,
        load_e39_rows,
        load_e44_rows,
        normalize_circuit,
        state_from_circuit,
    )
    from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: PLC0415

    rows = {row["source_id"]: row for row in load_e39_rows()}
    rows.update({row["source_id"]: row for row in load_e44_rows()})

    wanted = [line for line in manifest.read_text(encoding="utf-8").splitlines()[1:] if line.strip()]
    results: dict[str, tuple[int, Counter]] = {}
    for index, line in enumerate(wanted, start=1):
        source_id = line.split(",", 1)[0]
        row = rows.get(source_id)
        if row is None:
            continue
        try:
            raw = circuit_from_row(row)
            normalized, _ = normalize_circuit(raw)
            if normalized is None:
                continue
            # The frozen v14 run skips every baseline arm when the normalized
            # circuit exceeds the 80-gate comparator budget, in which case the
            # certified root is the normalized circuit itself.
            if normalized.size() > MAX_BASELINE_GATES:
                root_circuit = normalized
            else:
                greedy = GreedyGateCancellation(
                    max_iterations=50, fidelity_threshold=1.0, success_reduction=0.0)
                root_circuit = greedy.optimize(normalized).optimized_circuit
            state = state_from_circuit(root_circuit)
        except Exception:  # noqa: BLE001 - reconstruction failure is recorded, not raised
            continue
        results[source_id] = (state.num_qubits, Counter(gate.name for gate in state.gates))
        if index % 16 == 0:
            print(f"  reconstructed {index}/{len(wanted)}", file=sys.stderr, flush=True)
    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--no-reconstruct-roots", action="store_true",
                        help="skip the exact root-state rebuild and use the coarse bound only")
    args = parser.parse_args()
    out_root = args.output_root
    out_root.mkdir(parents=True, exist_ok=True)

    rules = core_rules()
    rows = list(csv.DictReader(CLASSIFICATION.open(encoding="utf-8")))

    qasm_by_prefix: dict[str, Path] = {}
    for path in sorted(QASM_DIR.glob("*.qasm")):
        qasm_by_prefix[path.stem.rsplit("_", 1)[-1]] = path

    root_states: dict[str, tuple[int, Counter]] = {}
    if not args.no_reconstruct_roots:
        print("rebuilding frozen E45 root listings ...", file=sys.stderr, flush=True)
        root_states = reconstruct_root_states(NORMALIZATION_MANIFEST)

    verdict = json.loads(VERDICT.read_text(encoding="utf-8"))
    blocked = verdict["blocking_evidence"]["landscape_integration"]

    out_rows: list[dict] = []
    unresolved: list[str] = []
    mismatches: list[str] = []

    for row in rows:
        source_id = row["source_id"]
        baseline = int(row["baseline_cost"])
        reconstructed = root_states.get(source_id)
        counts: Counter
        num_qubits = int(row["n_qubits"])
        if reconstructed is not None and sum(reconstructed[1].values()) == baseline:
            num_qubits, counts = reconstructed
            verified = True
        else:
            digest = row["input_circuit_sha256"]
            path = qasm_by_prefix.get(digest[:12])
            if path is None:
                unresolved.append(source_id)
                continue
            num_qubits, counts = parse_qasm_counts(path)
            verified = False
            mismatches.append(source_id)

        gate_names = set(counts) | SELF_INVERSE | ROTATIONS | {"t", "tdg", "s", "sdg"}
        ceiling = per_gate_action_ceiling(rules, gate_names)
        aggregate = aggregate_action_ceiling(rules)

        observed_total = sum(counts.values())
        lb_class = sum(max(0, counts.get(name, 0) - HORIZON * ceiling.get(name, 0))
                       for name in counts)
        lb_total = max(0, baseline - HORIZON * aggregate)
        lb = max(lb_class, lb_total) if verified else lb_total

        upper = row["best_cost"] or ""
        upper_exactness = row["best_cost_exactness"] or ""
        upper_int = int(upper) if upper else None

        out_rows.append({
            "source_id": source_id,
            "circuit_id": row["circuit_id"],
            "circuit_family": row["circuit_family"],
            "n_qubits": num_qubits,
            "horizon": HORIZON,
            "rule_scope": row["rule_scope"],
            "certificate_tier": row["certificate_tier"],
            "classification_status": row["classification_status"],
            "baseline_cost": baseline,
            "root_gate_total": observed_total,
            "root_reconstruction_verified": verified,
            "gate_name_counts": json.dumps(dict(sorted(counts.items())), separators=(",", ":")),
            "lb_per_gate_class": lb_class if verified else "",
            "lb_aggregate": lb_total,
            "certified_lower_bound": lb,
            "best_cost_upper": "" if upper_int is None else upper_int,
            "best_cost_exactness": upper_exactness,
            "interval_width": "" if upper_int is None else upper_int - lb,
            "lower_bound_is_tight": bool(upper_int is not None and upper_int == lb),
        })

    out_rows.sort(key=lambda item: (item["certificate_tier"], item["source_id"]))

    csv_path = out_root / "certified_lower_bounds.csv"
    fieldnames = list(out_rows[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(out_rows)

    bounded = [r for r in out_rows if r["certificate_tier"] == "CLASSIFICATION_EXACT_EXTRAS_BOUNDED"]
    closed = [r for r in bounded if r["lower_bound_is_tight"]]
    widths = [r["interval_width"] for r in bounded if r["interval_width"] != ""]
    all_widths = [r["interval_width"] for r in out_rows if r["interval_width"] != ""]
    verified_rows = [r for r in out_rows if r["root_reconstruction_verified"]]

    summary = {
        "as_of": datetime.now().astimezone().strftime("%Y-%m-%d"),
        "panel_source_count": len(rows),
        "sources_resolved": len(out_rows),
        "sources_unresolved": unresolved,
        "root_states_reconstructed": len(root_states),
        "root_reconstruction_verified": len(verified_rows),
        "root_reconstruction_failed": mismatches,
        "horizon": HORIZON,
        "rule_scope": "e44_core_v1",
        "core_rule_count": len(rules),
        "aggregate_action_ceiling": aggregate_action_ceiling(rules),
        "per_gate_action_ceiling": per_gate_action_ceiling(
            rules, set(SELF_INVERSE) | set(ROTATIONS) | {"t", "tdg", "s", "sdg"}),
        "bounded_cells": len(bounded),
        "bounded_cells_closed_by_bound": len(closed),
        "bounded_interval_width_max": max(widths) if widths else None,
        "bounded_interval_width_mean": round(sum(widths) / len(widths), 4) if widths else None,
        "bounded_interval_width_as_fraction_of_baseline_max": (
            round(max((r["interval_width"] / r["baseline_cost"]) for r in bounded
                      if r["interval_width"] != "" and r["baseline_cost"]), 6)
            if bounded else None
        ),
        "panel_interval_width_max": max(all_widths) if all_widths else None,
        "verdict_reference": {
            "path": "release/v15_readiness_verdict.json",
            "sha256": sha256_file(VERDICT),
            "bounded_best_cost_count": blocked["bounded_best_cost_count"],
            "classified_count": blocked["classified_count"],
        },
        "inputs": {
            "rule_library": {"path": RULE_LIBRARY.relative_to(ROOT).as_posix(),
                             "sha256": sha256_file(RULE_LIBRARY)},
            "classification": {"path": CLASSIFICATION.relative_to(ROOT).as_posix(),
                               "sha256": sha256_file(CLASSIFICATION)},
            "normalization_manifest": {"path": NORMALIZATION_MANIFEST.relative_to(ROOT).as_posix(),
                                       "sha256": sha256_file(NORMALIZATION_MANIFEST)},
            "qasm_dir": QASM_DIR.relative_to(ROOT).as_posix(),
            "qasm_file_count": len(qasm_by_prefix),
        },
        "claim_boundary": (
            "The lower bound is certified for the e44_core_v1 action set within the declared "
            "horizon; it is not a bound for unrestricted rewriting, and it does not by itself "
            "upgrade any certificate tier in the frozen v15 package."
        ),
    }
    (out_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    protocol = {
        "protocol_id": "V15_CERTIFIED_LOWER_BOUND_V1",
        "date": summary["as_of"],
        "derivation": "per-gate-class bounded-decrease argument + aggregate action ceiling",
        "horizon": HORIZON,
        "rule_scope": "e44_core_v1",
        "predicate": (
            "for every legal action a in e44_core_v1, "
            "n_g(post(a)) >= n_g(pre(a)) - r_g ; hence cost(s_H) >= sum_g max(0, n_g(s_0) - H*r_g)"
        ),
        "inputs_read_only": summary["inputs"],
        "frozen_paths_untouched": ["data/", "release/", "docs/manuscript/"],
        "output": {
            "csv": csv_path.relative_to(ROOT).as_posix(),
            "summary": (out_root / "summary.json").relative_to(ROOT).as_posix(),
        },
        "provenance": {
            "script": Path(__file__).relative_to(ROOT).as_posix(),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
    }
    (out_root / "protocol.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps({k: v for k, v in summary.items() if k != "inputs"}, indent=2, sort_keys=True))
    return 0 if not unresolved and not mismatches else 1


if __name__ == "__main__":
    sys.exit(main())
