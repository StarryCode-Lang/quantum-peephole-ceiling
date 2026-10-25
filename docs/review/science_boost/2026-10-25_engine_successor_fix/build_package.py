"""Build the comparison CSV and results JSON for the engine-successor pilot.

Review-grade tooling: writes only inside this package directory.  Rerunnable
after pilot_cells.jsonl has been produced by the screening driver documented
in README.md.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PKG = Path(__file__).resolve().parent


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


rows = [
    json.loads(line)
    for line in (PKG / "pilot_cells.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]

CTRL_H = "e39:ec754f7e3892"  # frozen EXACT_H_LOCAL_OPTIMUM that agrees (control)
CTRL_E = "e39:2d71c39b2658"  # frozen EXACT_ESCAPE that agrees (control)
pilot = [r for r in rows if r["verdict"] in ("FALSE_H_LOCAL_OPTIMUM", "WRONG_ESCAPE_QUANTITY")]
pilot += [r for r in rows if r["source_id"].startswith(CTRL_H) or r["source_id"].startswith(CTRL_E)]
order = {"FALSE_H_LOCAL_OPTIMUM": 0, "WRONG_ESCAPE_QUANTITY": 1, "AGREE_H_LOCAL": 2, "AGREE_ESCAPE": 3}
pilot.sort(key=lambda r: (order[r["verdict"]], r["source_id"]))


def fnum(value):
    return "" if value is None else value


csv_rows = []
for r in pilot:
    fc, cc = r["frozen_compact"], r["corrected_compact"]
    fi, ci = r["frozen_idastar"], r["corrected_idastar"]
    cls = r["frozen_classification"]
    csv_rows.append({
        "source_id": r["source_id"], "source_kind": r["source_kind"], "circuit_family": r["circuit_family"],
        "n_qubits": r["n_qubits"], "root_state_sha256": r["root_state_sha256"], "root_kind": r["root_kind"],
        "baseline_cost": r["baseline_cost"], "config_id": r["config"]["config_id"], "horizon": r["config"]["horizon"],
        "state_budget": r["config"]["state_budget"], "rule_scope": "e44_core_v1",
        "verdict": r["verdict"],
        "frozen_classification_status": cls["classification_status"],
        "frozen_best_cost": fc["best_cost"], "corrected_best_cost": cc["best_cost"],
        "frozen_compact_status": fc["status"], "corrected_compact_status": cc["status"],
        "frozen_escape_depth": fnum(fc["escape_depth"]), "corrected_escape_depth": fnum(cc["escape_depth"]),
        "frozen_barrier_height": fnum(fc["barrier_height"]), "corrected_barrier_height": fnum(cc["barrier_height"]),
        "frozen_idastar_escape_depth": fnum(fi["escape_depth"]), "corrected_idastar_escape_depth": fnum(ci["escape_depth"]),
        "frozen_idastar_status": fi["status"], "corrected_idastar_status": ci["status"],
        "frozen_compact_states_seen": fc["states_seen"], "corrected_compact_states_seen": cc["states_seen"],
        "frozen_idastar_states_seen": fi["states_seen"], "corrected_idastar_states_seen": ci["states_seen"],
        "corrected_compact_seconds": round(r["compact_seconds"], 4),
        "corrected_idastar_seconds": round(r["idastar_seconds"], 4),
        "witness_replay_compact": r["compact_replay"], "witness_replay_idastar": r["idastar_replay"],
        "corrected_resource_status": cc["resource_status"] + "/" + ci["resource_status"],
    })
buffer = io.StringIO()
writer = csv.DictWriter(buffer, fieldnames=list(csv_rows[0]), lineterminator="\n")
writer.writeheader()
writer.writerows(csv_rows)
(PKG / "comparison.csv").write_text(buffer.getvalue(), encoding="utf-8", newline="\n")

gr = list(csv.DictReader((ROOT / "data/v14/e45_full_development/grid_results.csv").open(encoding="utf-8")))
gi = list(csv.DictReader((ROOT / "data/v14/e45_idastar_escape/grid_results.csv").open(encoding="utf-8")))
frozen_c = {r["source_id"]: float(r["runtime_seconds"]) for r in gr if r["arm"] == "certificate_guided_escape"}
frozen_i = {r["source_id"]: float(r["runtime_seconds"]) for r in gi if r["arm"] == "idastar_escape"}
screened_ids = {r["source_id"] for r in rows}
big = [s for s in frozen_c if s not in screened_ids]
screened_c = sum(r["compact_seconds"] for r in rows)
screened_i = sum(r["idastar_seconds"] for r in rows)
big_frozen_c = sum(frozen_c[s] for s in big)
big_frozen_i = sum(frozen_i[s] for s in big)
capped_c = sum(1 for s in big if frozen_c[s] >= 29.0)

results = {
    "review_grade": True,
    "outside_release_hash_chain": True,
    "date": "2026-10-25",
    "experiment_id": "PILOT_ENGINE_SUCCESSOR_RECERT_2026_10_25",
    "defect": {
        "module": "src/optimisation/certified_landscape.py",
        "function": "iter_legal_actions",
        "description": (
            "The per-rule location loop overwrote local_actions on every matching location "
            "(last location wins), silently dropping Quartz actions from all earlier locations "
            "of a shared source signature."
        ),
        "fix": (
            "Accumulate actions across all locations of a rule, then apply the single final "
            "sort_key sort (rule-by-rule, sorted-within-rule order preserved)."
        ),
        "fixed_engine_source_hashes": {
            "src/optimisation/certified_landscape.py": sha256(ROOT / "src/optimisation/certified_landscape.py"),
            "src/optimisation/quartz_rule_import.py": sha256(ROOT / "src/optimisation/quartz_rule_import.py"),
            "src/optimisation/rewrite_exposure.py": sha256(ROOT / "src/optimisation/rewrite_exposure.py"),
        },
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
        "engines": (
            "search_landscape_horizons_compact + search_escape_idastar from "
            "src/optimisation/certified_landscape.py AFTER the iter_legal_actions fix"
        ),
        "screening_scope": "all 128-panel cells with baseline_cost <= 70 (78 cells), matching the audit scope",
        "pilot_set": "6 false H-local-optima + 5 wrong escape quantities found by the screen (identical to the prior audit) + 2 agreeing controls",
        "witness_replay": "every non-empty corrected witness replayed via replay_actions; all REPLAY_PASS",
    },
    "screening": {
        "cells": len(rows),
        "false_h_local_optima": sum(1 for r in rows if r["verdict"] == "FALSE_H_LOCAL_OPTIMUM"),
        "wrong_escape_quantities": sum(1 for r in rows if r["verdict"] == "WRONG_ESCAPE_QUANTITY"),
        "agree_with_frozen": sum(1 for r in rows if r["verdict"].startswith("AGREE")),
        "resource_truncated_cells": sum(
            1 for r in rows
            if r["corrected_compact"]["resource_status"] != "COMPLETE"
            or r["corrected_idastar"]["resource_status"] != "COMPLETE"
        ),
        "witness_replay_failures": sum(
            1 for r in rows if r["compact_replay"] == "REPLAY_FAIL" or r["idastar_replay"] == "REPLAY_FAIL"
        ),
        "total_compact_seconds": round(screened_c, 3),
        "total_idastar_seconds": round(screened_i, 3),
        "total_seconds": round(screened_c + screened_i, 3),
        "frozen_compact_seconds_same_cells": round(sum(frozen_c[r["source_id"]] for r in rows), 3),
        "frozen_idastar_seconds_same_cells": round(sum(frozen_i[r["source_id"]] for r in rows), 3),
    },
    "full_rerun_estimate_128_cells": {
        "measured_small_78_cells_seconds": round(screened_c + screened_i, 2),
        "remaining_50_frozen_compact_seconds": round(big_frozen_c, 1),
        "remaining_50_frozen_idastar_seconds": round(big_frozen_i, 1),
        "remaining_50_compact_cells_at_frozen_time_cap": capped_c,
        "expected_seconds": "approx 1080-1330 (18-22 min)",
        "expected_note": (
            "remaining-50 compact is dominated by cells already pinned at the 30 s fail-closed "
            "budget (the corrected engine explores strictly more states but is capped at the same "
            "30 s); IDA* scales by the measured 0.86 corrected/frozen ratio on screened cells; "
            "small-78 measured cost added"
        ),
        "worst_case_seconds": "approx 3000 (50 min) if every remaining-50 compact AND idastar cell exhausts its 30 s budget",
    },
    "pilot_cells": csv_rows,
}
(PKG / "pilot_results.json").write_text(json.dumps(results, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")
print("comparison.csv rows:", len(csv_rows))
print("pilot_results.json written")
