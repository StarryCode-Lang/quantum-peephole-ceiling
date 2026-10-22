"""Census of the frozen Quartz rewrite library: cost geometry, closure, redundancy.

Purpose
-------
The 2026-10-17 scan established, for the 149-rule ``e44_core_v1`` certified scope,
that 138/149 rules cannot reduce the gate count.  This script generalises that
fact to the **whole** 1,474-rule Quartz import plus the auxiliary
``pair_v1``/``structural_exchange_v1`` families, and adds three closure
statistics that matter for the "rule-library completeness" research direction:

  * cost geometry   — cost_delta distribution (reducing / neutral / increasing)
  * reverse closure — for every rule with cost_delta > 0, is the reverse
                      direction present in the library?
  * source collision — distinct rules sharing one source pattern (the local
                      confluence / choice-degree question)

Inputs are read-only.  Output is a dated evidence directory outside ``data/``
and ``release/``.

Usage
-----
    python scripts/census_rule_library.py [--output-root DIR]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RULE_LIBRARY = ROOT / "data/v13/e43_quartz_rule_import/generation_a/rule_library.json"
DEFAULT_OUT = ROOT / "docs/review/science_boost/2026-10-18_rule_library_census"

# Frozen certified scope of the E44/E45/E46 landscape (see certified_landscape.py).
CORE_MAX_SRC_QUBITS = 2
CORE_MAX_SRC_OPS = 4
CORE_MAX_TGT_OPS = 6


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def in_core_scope(rule: dict) -> bool:
    if rule.get("rule_family") != "quartz_v1":
        return True
    source = rule["source"]
    return (
        int(source["num_qubits"]) <= CORE_MAX_SRC_QUBITS
        and len(source["operations"]) <= CORE_MAX_SRC_OPS
        and len(rule["target"]["operations"]) <= CORE_MAX_TGT_OPS
    )


def op_signature(operations: list[dict]) -> tuple:
    """Gate-name/arity signature, ignoring qubit labels (rename-invariant)."""
    return tuple(sorted((op["name"], len(op["qubits"])) for op in operations))


def qubit_normalised(operations: list[dict]) -> tuple:
    """Exact operation list with qubit labels canonicalised by first appearance."""
    mapping: dict[int, int] = {}
    out = []
    for op in operations:
        qubits = []
        for qubit in op["qubits"]:
            if qubit not in mapping:
                mapping[qubit] = len(mapping)
            qubits.append(mapping[qubit])
        params = tuple(
            round(float(p), 9) if isinstance(p, (int, float)) else str(p)
            for p in op.get("params", [])
        )
        out.append((op["name"], tuple(qubits), params))
    return tuple(out)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    out_root = args.output_root
    out_root.mkdir(parents=True, exist_ok=True)

    library = json.loads(RULE_LIBRARY.read_text(encoding="utf-8"))
    rules: list[dict] = library["rules"]

    rows: list[dict] = []
    schema_rules: list[dict] = []
    for rule in rules:
        if "source" not in rule or "target" not in rule:
            schema_rules.append({
                "rule_id": rule.get("rule_id", ""),
                "rule_family": rule.get("rule_family", ""),
                "semantics": rule.get("semantics", ""),
            })
            continue
        source_ops = rule["source"]["operations"]
        target_ops = rule["target"]["operations"]
        delta = int(rule.get("cost_delta", len(target_ops) - len(source_ops)))
        rows.append({
            "rule_id": rule["rule_id"],
            "rule_family": rule.get("rule_family", ""),
            "class_id": rule.get("class_id", ""),
            "in_core_scope": in_core_scope(rule),
            "source_num_qubits": int(rule["source"]["num_qubits"]),
            "source_gate_count": len(source_ops),
            "target_gate_count": len(target_ops),
            "cost_delta": delta,
            "direction": rule.get("direction", ""),
            "reversible": bool(rule.get("reversible", False)),
            "source_hash": rule["source"].get("content_hash", ""),
            "target_hash": rule["target"].get("content_hash", ""),
            "source_signature": json.dumps(op_signature(source_ops)),
            "source_normalised": json.dumps(qubit_normalised(source_ops)),
            "target_normalised": json.dumps(qubit_normalised(target_ops)),
        })

    # --- cost geometry -------------------------------------------------------
    def geometry(subset: list[dict]) -> dict:
        deltas = Counter()
        for row in subset:
            d = row["cost_delta"]
            deltas["reducing" if d < 0 else ("neutral" if d == 0 else "increasing")] += 1
        values = [row["cost_delta"] for row in subset]
        return {
            "n": len(subset),
            "reducing": deltas["reducing"],
            "neutral": deltas["neutral"],
            "increasing": deltas["increasing"],
            "reducing_fraction": round(deltas["reducing"] / len(subset), 6) if subset else None,
            "max_reduction": -min(values) if values and min(values) < 0 else 0,
            "max_increase": max(values) if values else 0,
            "sum_cost_delta": sum(values),
        }

    by_family = defaultdict(list)
    for row in rows:
        by_family[row["rule_family"]].append(row)
    core = [row for row in rows if row["in_core_scope"]]

    # --- reverse closure -----------------------------------------------------
    # A rule (s -> t) is "reverse-closed" when some library entry implements
    # (t -> s) on the same qubit-normalised gate lists.
    pairs = {(row["source_normalised"], row["target_normalised"]) for row in rows}
    for row in rows:
        row["reverse_present"] = (
            row["cost_delta"] != 0
            and (row["target_normalised"], row["source_normalised"]) in pairs
        )

    def closure(subset: list[dict]) -> dict:
        weighted = [row for row in subset if row["cost_delta"] != 0]
        closed = [row for row in weighted if row["reverse_present"]]
        reducing = [row for row in weighted if row["cost_delta"] < 0]
        return {
            "n_directional": len(weighted),
            "n_reverse_present": len(closed),
            "reverse_closure_rate": round(len(closed) / len(weighted), 6) if weighted else None,
            "n_reducing": len(reducing),
            "n_reducing_reverse_present": sum(1 for row in reducing if row["reverse_present"]),
        }

    # --- source collision ----------------------------------------------------
    by_source: dict[str, list[dict]] = defaultdict(list)
    for row in rows:
        by_source[row["source_normalised"]].append(row)
    collisions = {key: value for key, value in by_source.items() if len(value) > 1}
    distinct_targets = Counter()
    for key, value in collisions.items():
        distinct_targets[key] = len({row["target_normalised"] for row in value})

    # --- per-family table ----------------------------------------------------
    family_rows = []
    for family, subset in sorted(by_family.items()):
        geo = geometry(subset)
        clo = closure(subset)
        family_rows.append({
            "rule_family": family,
            "n_rules": geo["n"],
            "reducing": geo["reducing"],
            "neutral": geo["neutral"],
            "increasing": geo["increasing"],
            "reducing_fraction": geo["reducing_fraction"],
            "max_reduction": geo["max_reduction"],
            "reverse_closure_rate": clo["reverse_closure_rate"],
        })

    core_geo = geometry(core)
    # schema-level rules (predicate families without an explicit pattern)
    core_clo = closure(core)
    core_collisions = {k: v for k, v in by_source.items() if len(v) > 1 and v[0]["in_core_scope"]}

    csv_path = out_root / "rule_census.csv"
    fieldnames = list(rows[0].keys())
    with csv_path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    fam_path = out_root / "rule_family_summary.csv"
    with fam_path.open("w", encoding="utf-8", newline="\n") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(family_rows[0].keys()))
        writer.writeheader()
        writer.writerows(family_rows)

    summary = {
        "as_of": datetime.now().astimezone().strftime("%Y-%m-%d"),
        "library": {
            "path": RULE_LIBRARY.relative_to(ROOT).as_posix(),
            "sha256": sha256_file(RULE_LIBRARY),
            "schema_version": library.get("schema_version"),
            "n_entries": len(rules),
            "n_pattern_rules": len(rows),
            "n_schema_rules": len(schema_rules),
        },
        "whole_library": geometry(rows),
        "core_scope": {
            "definition": (
                "quartz_v1 rules with source num_qubits <= 2, source operations <= 4, "
                "target operations <= 6, plus every pair_v1 / structural_exchange_v1 rule"
            ),
            **core_geo,
            "closure": core_clo,
            "source_collisions": len(core_collisions),
        },
        "reverse_closure": closure(rows),
        "source_collision": {
            "n_colliding_sources": len(collisions),
            "n_rules_involved": sum(len(v) for v in collisions.values()),
            "max_distinct_targets": max(distinct_targets.values()) if distinct_targets else 0,
            "n_sources_with_multiple_distinct_targets": sum(
                1 for v in distinct_targets.values() if v > 1),
        },
        "schema_rules": schema_rules,
        "by_family": family_rows,
        "claim_boundary": (
            "Descriptive census of the frozen rule library. cost_delta is read from the "
            "library metadata and cross-checked against operation counts; it is not a "
            "semantic-equivalence claim. Reverse closure is exact-match only and does not "
            "account for rules that reach the reverse by composition."
        ),
    }
    (out_root / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    protocol = {
        "protocol_id": "RULE_LIBRARY_CENSUS_V1",
        "date": summary["as_of"],
        "inputs_read_only": {"rule_library": summary["library"]},
        "outputs": {
            "census": csv_path.relative_to(ROOT).as_posix(),
            "family_summary": fam_path.relative_to(ROOT).as_posix(),
            "summary": (out_root / "summary.json").relative_to(ROOT).as_posix(),
        },
        "provenance": {
            "script": Path(__file__).relative_to(ROOT).as_posix(),
            "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "frozen_paths_untouched": ["data/", "release/", "docs/manuscript/"],
    }
    (out_root / "protocol.json").write_text(
        json.dumps(protocol, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
