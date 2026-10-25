"""Build the FULL 128-cell re-certification package from full_cells.jsonl.

Review-grade tooling: writes only inside this package directory.  Consumes the
per-cell records produced by rerun_all_cells.py (frozen v14 budgets, fixed
engine) plus the optional determinism re-run (determinism_cells.jsonl), and
writes full_comparison.csv, full_results.json, determinism.json and
receipt.json.  Frozen ``data/`` and ``release/`` are read-only.

Validation: every one of the 78 screened cells must reproduce the pilot
(pilot_cells.jsonl) corrected statuses/best costs/escape depths exactly.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PKG = Path(__file__).resolve().parent

FROZEN_COMPACT_GRID = ROOT / "data" / "v14" / "e45_full_development" / "grid_results.csv"
FROZEN_IDASTAR_GRID = ROOT / "data" / "v14" / "e45_idastar_escape" / "grid_results.csv"

AGREE_TYPES = {"AGREE"}
NOT_A_CHANGE_TYPES = {"AGREE", "RESOURCE_BOUNDED_BOTH"}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fnum(value):
    return "" if value is None else value


def load_records(path: Path) -> list[dict]:
    return [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def classify(r: dict) -> tuple[str, str]:
    """Return (change_type, note).  Partition of the 128 cells.

   change_type vocabulary:
      FALSE_OPTIMUM_NOW_ESCAPE    frozen stated exact H-local optimum, corrected exact escape
      ESCAPE_COST_STATED_WRONG    both exact escapes, corrected best_cost < frozen stated best_cost
      ESCAPE_DEPTH_OVERSTATED     best cost unchanged, corrected exact escape depth < frozen stated
      COST_REVISED                stated exact best_cost revised in a case not covered above
      AGREE                       corrected exact quantities identical to frozen stated ones
      RESOURCE_BOUNDED_BOTH       frozen compact truncated and corrected compact truncated
      FROZEN_TRUNCATED_NOW_EXACT  frozen compact truncated, corrected compact complete (newly certified)
      FROZEN_EXACT_NOW_TRUNCATED  frozen compact complete, corrected compact truncated (flagged)
      UNEXPECTED_REGRESSION       corrected worse than frozen where frozen was exact (flagged)
    """

    fc = r["frozen_compact"]
    fi = r["frozen_idastar"]
    cc = r["corrected_compact"]
    ci = r["corrected_idastar"]
    cls = r["frozen_classification"]
    fv = cls["classification_status"]
    fc_cost = fc["best_cost"]
    cc_cost = cc["best_cost"]
    fc_complete = fc["resource_status"] == "COMPLETE"
    cc_complete = cc["resource_status"] == "COMPLETE"
    fi_depth = fi["escape_depth"]
    ci_depth = ci["escape_depth"]

    if fc_complete and cc_complete:
        if fv == "EXACT_H_LOCAL_OPTIMUM" and cc["status"] == "EXACT_ESCAPE":
            return "FALSE_OPTIMUM_NOW_ESCAPE", f"best_cost {fc_cost}->{cc_cost}; escape_depth {cc['escape_depth']}"
        if fv == "EXACT_H_LOCAL_OPTIMUM" and cc["status"] == "EXACT_H_LOCAL_OPTIMUM":
            if cc_cost == fc_cost:
                return "AGREE", ""
            note = f"best_cost {fc_cost}->{cc_cost}"
            return ("COST_REVISED", note) if cc_cost < fc_cost else ("UNEXPECTED_REGRESSION", note)
        if fv == "EXACT_ESCAPE" and cc["status"] == "EXACT_ESCAPE":
            if cc_cost < fc_cost:
                return "ESCAPE_COST_STATED_WRONG", (
                    f"best_cost {fc_cost}->{cc_cost}; escape_depth {fnum(fc['escape_depth'])}->{fnum(cc['escape_depth'])}"
                )
            if cc_cost > fc_cost:
                return "UNEXPECTED_REGRESSION", f"corrected best_cost {cc_cost} > frozen {fc_cost}"
            if (cc["escape_depth"] or 0) < (fc["escape_depth"] or 0):
                return "ESCAPE_DEPTH_OVERSTATED", f"escape_depth {fc['escape_depth']}->{cc['escape_depth']} (best_cost {fc_cost} unchanged)"
            if (cc["escape_depth"] or 0) > (fc["escape_depth"] or 0):
                return "UNEXPECTED_REGRESSION", f"corrected escape_depth {cc['escape_depth']} > frozen {fc['escape_depth']}"
            return "AGREE", ""
        if fv == "EXACT_ESCAPE" and cc["status"] == "EXACT_H_LOCAL_OPTIMUM":
            return "UNEXPECTED_REGRESSION", "corrected claims H-local where frozen found an exact escape"
        return "UNEXPECTED_REGRESSION", f"unhandled exact/exact pair {fv}/{cc['status']}"

    if fc_complete and not cc_complete:
        note = (
            f"frozen compact COMPLETE ({fc['states_seen']} states) but corrected truncated "
            f"({cc['resource_reason']}); corrected incumbent best_cost {cc_cost}; "
            f"corrected idastar {ci['status']}/d{fnum(ci_depth)}"
        )
        return "FROZEN_EXACT_NOW_TRUNCATED", note

    if not fc_complete and cc_complete:
        note = (
            f"frozen compact truncated ({fc['resource_reason']}); corrected complete: "
            f"{cc['status']} best_cost {cc_cost} depth {fnum(cc['escape_depth'])}"
        )
        return "FROZEN_TRUNCATED_NOW_EXACT", note

    # both compact arms truncated
    if (
        cls["certificate_tier"] == "COMPACT_COMPLETE_DERIVED"
        and fi["resource_status"] == "COMPLETE"
        and ci["resource_status"] != "COMPLETE"
    ):
        return "FROZEN_EXACT_NOW_TRUNCATED", (
            f"frozen stated exact H-local optimum by derivation (frozen idastar COMPLETE); "
            f"corrected compact truncated ({cc['resource_reason']}) and corrected idastar truncated "
            f"({ci['resource_reason']}): the exact H-local claim is NOT re-certifiable at the frozen budgets"
        )
    if fi["resource_status"] == "COMPLETE" and ci["resource_status"] == "COMPLETE" and fi_depth != ci_depth:
        if (ci_depth or 0) < (fi_depth or 0):
            return "ESCAPE_DEPTH_OVERSTATED", (
                f"stated escape depth (exact IDA*) {fi_depth}->{ci_depth}; compact incumbent best_cost {fc_cost}->{cc_cost}"
            )
        return "UNEXPECTED_REGRESSION", f"corrected idastar depth {ci_depth} > frozen {fi_depth}"
    note = ""
    if cc_cost != fc_cost:
        direction = "improved" if cc_cost < fc_cost else "REGRESSED"
        note = f"compact incumbent best_cost {fc_cost}->{cc_cost} ({direction}, non-exact both sides)"
    return "RESOURCE_BOUNDED_BOTH", note


def pick_subsample(values: list[int], count: int) -> list[int]:
    """Evenly spaced deterministic picks across a sorted index list."""

    if len(values) <= count:
        return list(values)
    return sorted({values[round(i * (len(values) - 1) / (count - 1))] for i in range(count)})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cells", type=Path, default=PKG / "full_cells.jsonl")
    parser.add_argument("--determinism", type=Path, default=PKG / "determinism_cells.jsonl")
    parser.add_argument("--print-determinism-ids", action="store_true")
    args = parser.parse_args()

    records = load_records(args.cells)
    if len(records) != 128:
        raise RuntimeError(f"expected 128 cells, got {len(records)}")
    records.sort(key=lambda r: r["panel_index"])
    engine_hashes = {json.dumps(r["engine_source_sha256"], sort_keys=True) for r in records}
    if len(engine_hashes) != 1:
        raise RuntimeError(
            "engine_source_drift_across_cells:" + ";".join(sorted(engine_hashes))
        )
    engine_source_hashes = json.loads(engine_hashes.pop())
    for r in records:
        r["change_type"], r["change_note"] = classify(r)
        r["changed"] = r["change_type"] not in NOT_A_CHANGE_TYPES

    # ---- frozen internal consistency: classification vs frozen certificates ----
    for r in records:
        cls, fc, fi = r["frozen_classification"], r["frozen_compact"], r["frozen_idastar"]
        tier = cls["certificate_tier"]
        if tier == "COMPACT_COMPLETE_ENUMERATED":
            if cls["best_cost"] != fc["best_cost"] or cls["escape_depth"] != fc["escape_depth"]:
                raise RuntimeError(f"classification_compact_disagreement:{r['source_id']}")
        elif tier == "COMPACT_COMPLETE_DERIVED":
            if cls["best_cost"] != r["baseline_cost"] or fc["status"] != "RESOURCE_BOUNDED_NO_WITNESS":
                raise RuntimeError(f"derived_tier_shape_unexpected:{r['source_id']}")
        if cls["classification_status"] == "EXACT_H_LOCAL_OPTIMUM" and fi["status"] != "EXACT_H_LOCAL_OPTIMUM":
            raise RuntimeError(f"classification_idastar_disagreement:{r['source_id']}")

    # ---- validation against the pilot screen (78 cells) ----
    pilot = load_records(PKG / "pilot_cells.jsonl")
    pilot_by_id = {p["source_id"]: p for p in pilot}
    pilot_mismatches = []
    for r in records:
        p = pilot_by_id.get(r["source_id"])
        if p is None:
            continue
        for side, keys in (("corrected_compact", ("status", "best_cost", "escape_depth")),
                           ("corrected_idastar", ("status", "escape_depth"))):
            for key in keys:
                if p[side][key] != r[side][key]:
                    pilot_mismatches.append(
                        f"{r['source_id']}:{side}:{key}:{p[side][key]!r}->{r[side][key]!r}"
                    )
    if pilot_mismatches:
        raise RuntimeError("pilot_reproduction_mismatch:" + ";".join(pilot_mismatches[:10]))

    # ---- full_comparison.csv ----
    csv_rows = []
    for r in records:
        fc, cc = r["frozen_compact"], r["corrected_compact"]
        fi, ci = r["frozen_idastar"], r["corrected_idastar"]
        cls = r["frozen_classification"]
        csv_rows.append({
            "source_id": r["source_id"],
            "panel_index": r["panel_index"],
            "source_kind": r["source_kind"],
            "circuit_family": r["circuit_family"],
            "n_qubits": r["n_qubits"],
            "root_state_sha256": r["root_state_sha256"],
            "root_kind": r["root_kind"],
            "baseline_cost": r["baseline_cost"],
            "config_id": r["config"]["config_id"],
            "horizon": r["config"]["horizon"],
            "state_budget": r["config"]["state_budget"],
            "rule_scope": r["rule_scope"],
            "frozen_verdict": cls["classification_status"],
            "frozen_certificate_tier": cls["certificate_tier"],
            "frozen_best_cost": cls["best_cost"],
            "frozen_escape_depth": fnum(None if cls["escape_depth"] is None else cls["escape_depth"]),
            "frozen_compact_status": fc["status"],
            "frozen_compact_resource_status": fc["resource_status"],
            "frozen_compact_states_seen": fc["states_seen"],
            "frozen_idastar_escape_depth": fnum(fi["escape_depth"]),
            "corrected_verdict": cc["status"],
            "corrected_best_cost": cc["best_cost"],
            "corrected_escape_depth": fnum(cc["escape_depth"]),
            "corrected_compact_resource_status": cc["resource_status"],
            "corrected_compact_states_seen": cc["states_seen"],
            "corrected_idastar_status": ci["status"],
            "corrected_idastar_escape_depth": fnum(ci["escape_depth"]),
            "corrected_idastar_states_seen": ci["states_seen"],
            "changed": r["changed"],
            "change_type": r["change_type"],
            "change_note": r["change_note"],
            "incumbent_delta": cc["best_cost"] - fc["best_cost"],
            "escape_depth_delta_idastar": (
                "" if ci["escape_depth"] is None or fi["escape_depth"] is None
                else ci["escape_depth"] - fi["escape_depth"]
            ),
            "compact_states_seen": cc["states_seen"],
            "idastar_states_seen": ci["states_seen"],
            "compact_seconds": round(r["compact_seconds"], 4),
            "idastar_seconds": round(r["idastar_seconds"], 4),
            "compact_replay": r["compact_replay"],
            "idastar_replay": r["idastar_replay"],
        })
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(csv_rows[0]), lineterminator="\n")
    writer.writeheader()
    writer.writerows(csv_rows)
    (PKG / "full_comparison.csv").write_text(buffer.getvalue(), encoding="utf-8", newline="\n")

    # ---- aggregates ----
    change_counts: dict[str, int] = {}
    for r in records:
        change_counts[r["change_type"]] = change_counts.get(r["change_type"], 0) + 1

    cc_exact_hlocal = [r for r in records if r["corrected_compact"]["status"] == "EXACT_H_LOCAL_OPTIMUM"]
    cc_exact_escape = [r for r in records if r["corrected_compact"]["status"] == "EXACT_ESCAPE"]
    cc_truncated = [r for r in records if r["corrected_compact"]["resource_status"] != "COMPLETE"]
    ci_exact_hlocal = [r for r in records if r["corrected_idastar"]["status"] == "EXACT_H_LOCAL_OPTIMUM"]
    ci_exact_escape = [r for r in records if r["corrected_idastar"]["status"] == "EXACT_ESCAPE"]
    ci_truncated = [r for r in records if r["corrected_idastar"]["resource_status"] != "COMPLETE"]
    cc_derived_hlocal = [
        r for r in records
        if r["corrected_compact"]["status"] == "RESOURCE_BOUNDED_NO_WITNESS"
        and r["corrected_idastar"]["status"] == "EXACT_H_LOCAL_OPTIMUM"
    ]

    exact_94 = [
        r for r in records
        if r["frozen_classification"]["certificate_tier"]
        in ("COMPACT_COMPLETE_ENUMERATED", "COMPACT_COMPLETE_DERIVED")
    ]
    changed_94 = [
        {
            "source_id": r["source_id"],
            "circuit_family": r["circuit_family"],
            "baseline_cost": r["baseline_cost"],
            "old_best_cost": r["frozen_compact"]["best_cost"],
            "new_best_cost": r["corrected_compact"]["best_cost"],
            "delta": r["corrected_compact"]["best_cost"] - r["frozen_compact"]["best_cost"],
            "change_type": r["change_type"],
        }
        for r in exact_94
        if r["corrected_compact"]["resource_status"] == "COMPLETE"
        and r["corrected_compact"]["best_cost"] != r["frozen_compact"]["best_cost"]
    ]
    not_recertified_94 = [
        {
            "source_id": r["source_id"],
            "frozen_best_cost": r["frozen_compact"]["best_cost"],
            "corrected_compact_status": r["corrected_compact"]["status"],
            "corrected_idastar_status": r["corrected_idastar"]["status"],
        }
        for r in exact_94
        if r["corrected_compact"]["resource_status"] != "COMPLETE"
    ]

    incumbents_improved = [
        {"source_id": r["source_id"], "frozen_incumbent": r["frozen_compact"]["best_cost"],
         "corrected_incumbent": r["corrected_compact"]["best_cost"]}
        for r in records
        if r["change_type"] == "RESOURCE_BOUNDED_BOTH"
        and r["corrected_compact"]["best_cost"] < r["frozen_compact"]["best_cost"]
    ]
    incumbents_regressed = [
        {"source_id": r["source_id"], "frozen_incumbent": r["frozen_compact"]["best_cost"],
         "corrected_incumbent": r["corrected_compact"]["best_cost"]}
        for r in records
        if r["change_type"] == "RESOURCE_BOUNDED_BOTH"
        and r["corrected_compact"]["best_cost"] > r["frozen_compact"]["best_cost"]
    ]
    unexpected = [
        {"source_id": r["source_id"], "change_type": r["change_type"], "note": r["change_note"]}
        for r in records
        if r["change_type"] in ("UNEXPECTED_REGRESSION", "FROZEN_EXACT_NOW_TRUNCATED")
    ]

    frozen_grid_c = {
        row["source_id"]: float(row["runtime_seconds"])
        for row in csv.DictReader(FROZEN_COMPACT_GRID.open(encoding="utf-8", newline=""))
        if row["arm"] == "certificate_guided_escape"
    }
    frozen_grid_i = {
        row["source_id"]: float(row["runtime_seconds"])
        for row in csv.DictReader(FROZEN_IDASTAR_GRID.open(encoding="utf-8", newline=""))
        if row["arm"] == "idastar_escape"
    }
    corrected_c_total = sum(r["compact_seconds"] for r in records)
    corrected_i_total = sum(r["idastar_seconds"] for r in records)

    results = {
        "review_grade": True,
        "outside_release_hash_chain": True,
        "date": "2026-10-25",
        "experiment_id": "FULL_ENGINE_SUCCESSOR_RECERT_2026_10_25",
        "scope": "all 128 fixed-panel roots, both engines, fixed iter_legal_actions, frozen v14 budgets/configs",
        "defect_fix_identity": {
            "module": "src/optimisation/certified_landscape.py",
            "function": "iter_legal_actions",
            "engine_source_hashes_producing_run": engine_source_hashes,
        },
        "inputs": {
            "rule_library": {
                "path": "data/v13/e43_quartz_rule_import/generation_a/rule_library.json",
                "sha256": sha256(ROOT / "data/v13/e43_quartz_rule_import/generation_a/rule_library.json"),
                "rule_scope": "e44_core_v1",
            },
            "frozen_compact_certificates": {
                "path": "data/v14/e45_full_development/certificates.jsonl",
                "sha256": sha256(ROOT / "data/v14/e45_full_development/certificates.jsonl"),
            },
            "frozen_idastar_certificates": {
                "path": "data/v14/e45_idastar_escape/certificates.jsonl",
                "sha256": sha256(ROOT / "data/v14/e45_idastar_escape/certificates.jsonl"),
            },
            "classification_complete": {
                "path": "data/v15/e45_landscape_integration/classification_complete.csv",
                "sha256": sha256(ROOT / "data/v15/e45_landscape_integration/classification_complete.csv"),
            },
            "frozen_config": {"config_id": "h3_b64_s200k", "horizon": 3, "beam_width": 64, "state_budget": 200000, "barrier_cap": 2},
            "cell_time_budget_seconds": 30.0,
        },
        "method": {
            "root_states": "rebuilt via experiments.e46_window_landscape.run.load_root_states (hash-checked against frozen compact certificates)",
            "engines": "search_landscape_horizons_compact + search_escape_idastar AFTER the iter_legal_actions fix",
            "witness_replay": "every non-empty corrected witness replayed via replay_actions",
            "pilot_validation": "all 78 screened cells reproduce pilot_cells.jsonl corrected statuses/best costs/escape depths exactly",
        },
        "wall_time": {
            "corrected_compact_seconds_total": round(corrected_c_total, 2),
            "corrected_idastar_seconds_total": round(corrected_i_total, 2),
            "corrected_total_seconds": round(corrected_c_total + corrected_i_total, 2),
            "frozen_compact_seconds_total_same_panel": round(sum(frozen_grid_c.values()), 2),
            "frozen_idastar_seconds_total_same_panel": round(sum(frozen_grid_i.values()), 2),
            "corrected_compact_cells_at_time_cap_30s": sum(1 for r in records if r["compact_seconds"] >= 29.0),
            "corrected_idastar_cells_at_time_cap_30s": sum(1 for r in records if r["idastar_seconds"] >= 29.0),
        },
        "change_type_counts": dict(sorted(change_counts.items())),
        "corrected_headline": {
            "cells": len(records),
            "exact_h_local_optima_compact_complete": len(cc_exact_hlocal),
            "exact_escapes_compact_complete_enumerated": len(cc_exact_escape),
            "exact_best_cost_by_derivation_compact_truncated_idastar_exact_h_local": len(cc_derived_hlocal),
            "compact_resource_truncated": len(cc_truncated),
            "compact_truncated_with_certified_witness": sum(
                1 for r in cc_truncated if r["corrected_compact"]["status"] == "WITNESS_CERTIFIED_SEARCH_INCOMPLETE"
            ),
            "compact_truncated_no_witness": sum(
                1 for r in cc_truncated if r["corrected_compact"]["status"] == "RESOURCE_BOUNDED_NO_WITNESS"
            ),
            "idastar_exact_h_local_optima": len(ci_exact_hlocal),
            "idastar_exact_escapes": len(ci_exact_escape),
            "idastar_resource_truncated": len(ci_truncated),
            "stated_best_cost_exact_after_fix": len(cc_exact_hlocal) + len(cc_exact_escape) + len(cc_derived_hlocal),
            "witness_replay_failures": sum(
                1 for r in records if r["compact_replay"] == "REPLAY_FAIL" or r["idastar_replay"] == "REPLAY_FAIL"
            ),
        },
        "frozen_headline_comparison": {
            "frozen_classification": {"EXACT_H_LOCAL_OPTIMUM": 65, "EXACT_ESCAPE": 63},
            "frozen_exact_best_cost_cells": len(exact_94),
            "frozen_exact_best_cost_values_changed": len(changed_94),
            "frozen_exact_best_cost_total_delta": sum(item["delta"] for item in changed_94),
            "frozen_exact_best_cost_changed_cells": changed_94,
            "frozen_exact_best_cost_no_longer_recertified_at_frozen_budget": not_recertified_94,
        },
        "resource_bounded_observations": {
            "incumbents_improved_under_truncation": incumbents_improved,
            "incumbents_regressed_under_truncation": incumbents_regressed,
            "unexpected_or_flagged_cells": unexpected,
        },
        "cells": csv_rows,
    }
    (PKG / "full_results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    # ---- determinism subsample ----
    changed_ids = sorted(r["source_id"] for r in records if r["changed"])
    agree_ids = sorted(r["source_id"] for r in records if r["change_type"] == "AGREE")
    bounded_ids = sorted(r["source_id"] for r in records if r["change_type"] == "RESOURCE_BOUNDED_BOTH")
    changed_idx = pick_subsample([records.index(next(r for r in records if r["source_id"] == s)) for s in changed_ids], 5)
    agree_pool = agree_ids or bounded_ids
    agree_idx = pick_subsample([records.index(next(r for r in records if r["source_id"] == s)) for s in agree_pool], 5)
    subsample = sorted(records[i]["source_id"] for i in changed_idx + agree_idx)
    if args.print_determinism_ids:
        print(",".join(subsample))
        return 0

    det_records = load_records(args.determinism) if args.determinism.exists() else []
    det_by_id = {d["source_id"]: d for d in det_records}
    det_cells = []
    for source_id in subsample:
        first = next(r for r in records if r["source_id"] == source_id)
        second = det_by_id.get(source_id)
        if second is None:
            det_cells.append({"source_id": source_id, "rerun": "MISSING"})
            continue

        def quantities(rec: dict) -> dict:
            return {
                "compact_status": rec["corrected_compact"]["status"],
                "compact_best_cost": rec["corrected_compact"]["best_cost"],
                "compact_escape_depth": rec["corrected_compact"]["escape_depth"],
                "idastar_status": rec["corrected_idastar"]["status"],
                "idastar_escape_depth": rec["corrected_idastar"]["escape_depth"],
            }

        q1, q2 = quantities(first), quantities(second)
        det_cells.append({
            "source_id": source_id,
            "change_type": first["change_type"],
            "first_run": q1,
            "second_run": q2,
            "byte_identical": q1 == q2,
        })
    determinism = {
        "experiment_id": "FULL_ENGINE_SUCCESSOR_RECERT_2026_10_25",
        "purpose": "re-run a deterministic 10-cell subsample (5 changed + 5 agreeing) and confirm byte-identical verdict/best_cost/escape_depth",
        "selection_rule": (
            "sort each group by source_id and take 5 evenly spaced picks "
            "(all if fewer than 5); agreeing pool falls back to RESOURCE_BOUNDED_BOTH if AGREE is empty"
        ),
        "subsample_size_requested": 10,
        "cells": det_cells,
        "all_byte_identical": all(c.get("byte_identical") is True for c in det_cells) and len(det_cells) == 10,
    }
    (PKG / "determinism.json").write_text(json.dumps(determinism, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    # ---- receipt.json (package-wide; pilot artifacts kept, new artifacts added) ----
    artifacts = [
        "README.md",
        "build_package.py",
        "comparison.csv",
        "pilot_cells.jsonl",
        "pilot_results.json",
        "rerun_all_cells.py",
        "full_cells.jsonl",
        "full_cells_first_pass.jsonl",
        "build_full_package.py",
        "full_comparison.csv",
        "full_results.json",
        "determinism.json",
        "determinism_cells.jsonl",
    ]
    receipt = {
        "status": "FULL_RECERT_COMPLETE" if len(det_cells) == 10 and determinism["all_byte_identical"] else "FULL_RECERT_COMPLETE_WITH_CAVEATS",
        "experiment_id": "FULL_ENGINE_SUCCESSOR_RECERT_2026_10_25",
        "date": "2026-10-25",
        "outside_release_hash_chain": True,
        "frozen_inputs_untouched": True,
        "cells": len(records),
        "change_type_counts": dict(sorted(change_counts.items())),
        "stated_best_cost_exact_after_fix": results["corrected_headline"]["stated_best_cost_exact_after_fix"],
        "frozen_exact_best_cost_values_changed": len(changed_94),
        "artifact_sha256": {name: sha256(PKG / name) for name in artifacts if (PKG / name).exists()},
        "engine_source_sha256": results["defect_fix_identity"]["engine_source_hashes_producing_run"],
        "input_sha256": {
            "rule_library": results["inputs"]["rule_library"]["sha256"],
            "frozen_compact_certificates": results["inputs"]["frozen_compact_certificates"]["sha256"],
            "frozen_idastar_certificates": results["inputs"]["frozen_idastar_certificates"]["sha256"],
            "classification_complete": results["inputs"]["classification_complete"]["sha256"],
        },
    }
    (PKG / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")

    print("full_comparison.csv rows:", len(csv_rows))
    print("change_type_counts:", json.dumps(dict(sorted(change_counts.items()))))
    print("corrected headline:", json.dumps({k: v for k, v in results["corrected_headline"].items() if k != "cells"}))
    print("determinism cells:", len(det_cells), "all_byte_identical:", determinism["all_byte_identical"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
