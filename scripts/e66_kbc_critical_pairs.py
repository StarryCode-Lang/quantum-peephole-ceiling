"""KBC critical-pair census for the certified rule library (P3.5, round-12 P0-3).

Round-12 innovation scan, P0-3 / 30-day items 6–7: answer "why not
Knuth–Bendix-complete the rule library?" with a concrete census.  For the
pinned ``e44_core_v1`` scope this script:

1. enumerates overlapping critical pairs — ordered rule pairs (r1, r2) whose
   r1-target tail equals the r2-source head as a canonical gate sequence
   (same names, same relative wiring, same angles), so the shared segment of
   the composition cancels;
2. derives each candidate rule  L = src(r1) + src(r2)[m:]  →
   R = tgt(r1) + tgt(r2)[m:]  and tests semantic validity EXACTLY by dense
   unitary equality on the union wires (library rules in this scope are
   parameter-free);
3. keeps strictly gate-reducing candidates, and for each records whether its
   LHS contains a contiguous canonical subsequence matching some existing
   rule's source (a weak derivability signal — full derivability is rewrite
   reachability and is NOT claimed; confluence is undecidable in general,
   arXiv:2608.18859).

Output: dated review-grade package with per-candidate semantic status.

Usage:
    python scripts/e66_kbc_critical_pairs.py [--out-dir <dir>] [--max-wires 5]
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.optimisation.certified_landscape import filter_rule_scope  # noqa: E402

RULE_LIBRARY = ROOT / "data" / "v13" / "e43_quartz_rule_import" / "generation_a" / "rule_library.json"
RULE_SCOPE = "e44_core_v1"
EXPERIMENT_ID = "E66_KBC_CRITICAL_PAIRS_V1"


def canonical_seq(ops: list[dict]) -> tuple:
    """Canonical form of an operation sequence: names+params in order, wires
    renamed by first appearance."""
    renaming: dict[int, int] = {}
    out = []
    for op in ops:
        rel = []
        for q in op["qubits"]:
            if q not in renaming:
                renaming[q] = len(renaming)
            rel.append(renaming[q])
        params = tuple(
            p if isinstance(p, str) else round(float(p), 12)
            for p in op.get("params", [])
        )
        out.append((op["name"], tuple(sorted(rel)), params))
    return tuple(out)


def wire_touch(ops: list[dict]) -> set[int]:
    return {q for op in ops for q in op["qubits"]}


def build(ops: list[dict], wire_map: dict[int, int], n_wires: int) -> QuantumCircuit:
    qc = QuantumCircuit(n_wires)
    for op in ops:
        qs = [wire_map[q] for q in op["qubits"]]
        params = [float(p) for p in op.get("params", [])]
        name = op["name"]
        if name == "cx":
            qc.cx(qs[0], qs[1])
        elif name == "rz":
            qc.rz(params[0], qs[0])
        elif name in ("x", "h", "z", "s", "sdg", "t", "tdg"):
            getattr(qc, name)(qs[0])
        elif name == "swap":
            qc.swap(qs[0], qs[1])
        elif name == "cz":
            qc.cz(qs[0], qs[1])
        elif name == "rx":
            qc.rx(params[0], qs[0])
        elif name == "ry":
            qc.ry(params[0], qs[0])
        else:
            raise ValueError(f"unsupported_gate:{name}")
    return qc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs/review/science_boost/2026-10-25_kbc_critical_pairs")
    parser.add_argument("--max-wires", type=int, default=5)
    args = parser.parse_args()

    lib = json.loads(RULE_LIBRARY.read_text(encoding="utf-8"))
    # the 14 pair_v1 entries are structural declarations without LHS/RHS
    # sequences; the engine synthesizes them inline, so the census covers the
    # quartz_v1 entries only (same split the engine's loader makes)
    rules = [r for r in lib["rules"] if "source" in r]
    rules = filter_rule_scope(rules, RULE_SCOPE)
    def parameter_free(rule: dict) -> bool:
        for side in ("source", "target"):
            for op in rule[side]["operations"]:
                for param in op.get("params", []):
                    if isinstance(param, str):
                        return False
        return int(rule.get("parameter_rank", 0)) == 0

    dense = [
        r for r in rules
        if r["source"]["num_qubits"] <= args.max_wires
        and r["target"]["num_qubits"] <= args.max_wires
        and parameter_free(r)
    ]
    print(f"scope {RULE_SCOPE}: {len(rules)} rules, dense-checkable (<= {args.max_wires} q): {len(dense)}")

    canon_src = {r["rule_id"]: canonical_seq(r["source"]["operations"]) for r in dense}

    candidates: list[dict] = []
    pair_count = 0
    for r1, r2 in itertools.product(dense, repeat=2):
        t1 = r1["target"]["operations"]
        l2 = r2["source"]["operations"]
        max_overlap = min(len(t1), len(l2))
        for m in range(1, max_overlap + 1):
            if canonical_seq(t1[-m:]) != canonical_seq(l2[:m]):
                continue
            pair_count += 1
            joined_l = list(r1["source"]["operations"]) + list(l2[m:])
            joined_r = list(r1["target"]["operations"]) + list(r2["target"]["operations"][m:])
            delta = len(joined_l) - len(joined_r)
            if delta >= 0:
                continue
            wires_l = wire_touch(joined_l)
            wires_r = wire_touch(joined_r)
            if wires_l != wires_r:
                candidates.append({"r1": r1["rule_id"], "r2": r2["rule_id"], "overlap": m,
                                   "status": "WIRE_MISMATCH", "lhs_wires": len(wires_l), "rhs_wires": len(wires_r)})
                continue
            n_wires = len(wires_l)
            if n_wires > args.max_wires:
                continue
            ordered = sorted(wires_l)
            wm = {q: i for i, q in enumerate(ordered)}
            try:
                qc_l = build(joined_l, wm, n_wires)
                qc_r = build(joined_r, wm, n_wires)
                equal = bool(Operator(qc_l).equiv(Operator(qc_r)))
            except Exception as exc:
                candidates.append({"r1": r1["rule_id"], "r2": r2["rule_id"], "overlap": m,
                                   "status": "BUILD_ERROR", "error": str(exc)})
                continue
            # weak derivability signal: any existing rule's source sequence
            # appearing as a contiguous subsequence of the candidate LHS
            seq = canonical_seq(joined_l)
            derivable_signal = any(
                len(canon_src[rid]) >= 2 and any(
                    seq[i:i + len(canon_src[rid])] == canon_src[rid]
                    for i in range(len(seq) - len(canon_src[rid]) + 1)
                )
                for rid in canon_src
            )
            candidates.append(
                {
                    "r1": r1["rule_id"],
                    "r2": r2["rule_id"],
                    "overlap": m,
                    "status": "CHECKED",
                    "lhs_gates": len(joined_l),
                    "rhs_gates": len(joined_r),
                    "gate_delta": int(delta),
                    "semantically_valid": equal,
                    "lhs_matches_existing_source_subsequence": derivable_signal,
                }
            )

    checked = [c for c in candidates if c.get("status") == "CHECKED"]
    valid_reducing = [c for c in checked if c["semantically_valid"]]
    novel = [c for c in valid_reducing if not c["lhs_matches_existing_source_subsequence"]]
    report = {
        "experiment_id": EXPERIMENT_ID,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "rule_library_sha256": hashlib.sha256(RULE_LIBRARY.read_bytes()).hexdigest(),
        "rule_scope": RULE_SCOPE,
        "scope_rule_count": len(rules),
        "dense_rule_count": len(dense),
        "critical_pair_count": pair_count,
        "candidate_count": len(candidates),
        "checked_count": len(checked),
        "valid_reducing_count": len(valid_reducing),
        "valid_reducing_without_subsequence_signal": len(novel),
        "candidates": candidates,
    }
    args.out_dir.mkdir(parents=True, exist_ok=True)
    (args.out_dir / "kbc_critical_pairs.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "experiment_id": EXPERIMENT_ID,
        "critical_pairs": pair_count,
        "checked": len(checked),
        "valid_reducing": len(valid_reducing),
        "novel_signal": len(novel),
        "status": "COMPLETE",
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
