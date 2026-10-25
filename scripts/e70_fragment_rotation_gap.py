"""E68: rotation-gap decomposition on the fragment-native benchmark (P5).

The round-12 P0-1 fix for WL-3 replaces the degenerate synthetic ladder
(whose rz-only cells sat trivially on the absolute bound) with the
fragment-native benchmark (`scripts/generate_fragment_bench.py`: 6 families
x >= 8 instances x n = 4..64, analytic support size s by construction).
This script runs the certified commutation closure on every benchmark
instance and reports the E62 gap decomposition

    gap_total   = R(root)  - s        (distance to the fragment optimum)
    gap_reorder = R(root)  - R(closure)
    gap_content = R(closure) - s

plus the scaling of g_reorder / g_total versus n, which is the
"law-or-refutation" deliverable of the round-12 30-day list item 5.

The closure is the same certified engine as E62 Part A
(`scripts/e56_closure_criterion.closure_run`); the analytic s from the
benchmark index must equal the measured support size on the root — a
mismatch is a generator bug and aborts.

Usage:
    python scripts/e70_fragment_rotation_gap.py [--bench-dir <dir>] [--deadline 60]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from qiskit import qasm2  # noqa: E402

from experiments.e45_development_grid.run import state_from_circuit  # noqa: E402
from scripts.e62_rotation_gap import segmented_support  # noqa: E402
from scripts.e56_closure_criterion import closure_run  # noqa: E402

BENCH = ROOT / "docs" / "review" / "science_boost" / "2026-11_fragment_bench"
EXPERIMENT_ID = "E70_FRAGMENT_ROTATION_GAP_V1"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bench-dir", type=Path, default=BENCH)
    parser.add_argument("--deadline", type=float, default=60.0)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "docs/review/science_boost/2026-10-26_fragment_rotation_gap")
    args = parser.parse_args()
    args.bench_dir = args.bench_dir.resolve()

    index_path = args.bench_dir / "bench_index.csv"
    if not index_path.is_file():
        raise SystemExit(f"E70_BENCH_MISSING:{index_path}")
    with index_path.open(encoding="utf-8", newline="") as handle:
        index = list(csv.DictReader(handle))
    print(f"benchmark instances: {len(index)}", flush=True)

    rows: list[dict] = []
    started = time.perf_counter()
    for number, entry in enumerate(index, start=1):
        family = entry["family"]
        n = int(entry["n_qubits"])
        k = int(entry["instance"])
        qasm_path = args.bench_dir / "instances" / family / f"{family}_n{n}_k{k}.qasm"
        analytic_s = int(entry["analytic_s"])
        circuit = qasm2.loads(qasm_path.read_text(encoding="utf-8"))
        state = state_from_circuit(circuit)

        bound_root = segmented_support(state)
        if bound_root["support_total"] != analytic_s:
            raise SystemExit(
                f"E70_SUPPORT_MISMATCH:{family}:n{n}:k{k}:"
                f"measured={bound_root['support_total']}:analytic={analytic_s}"
            )
        deadline = time.perf_counter() + args.deadline
        result = closure_run(state, deadline=deadline)
        final = result["final_state"]
        bound_final = segmented_support(final)

        rz_root = sum(1 for g in state.gates if g.name == "rz")
        rz_final = sum(1 for g in final.gates if g.name == "rz")
        support = bound_root["support_total"]
        support_final = bound_final["support_total"]
        gap_total = rz_root - support
        gap_reorder = rz_root - rz_final
        gap_content = rz_final - support_final
        rows.append(
            {
                "experiment_id": EXPERIMENT_ID,
                "family": family,
                "n_qubits": n,
                "instance": k,
                "seed": entry["seed"],
                "analytic_s": analytic_s,
                "root_gates": len(state.gates),
                "root_rz": rz_root,
                "root_cx": sum(1 for g in state.gates if g.name == "cx"),
                "closure_gates": len(final.gates),
                "closure_rz": rz_final,
                "gap_total_root": gap_total,
                "gap_reorder": gap_reorder,
                "gap_content_final": gap_content,
                "g_reorder_over_g_total": round(gap_reorder / gap_total, 6) if gap_total > 0 else "",
                "closure_at_absolute_optimum": rz_final == support_final,
                "closure_passes": result["passes"],
                "closure_truncated": result["truncated"],
                "closure_errors": result["errors"],
                "wall_seconds": round(time.perf_counter() - deadline + args.deadline, 3),
            }
        )
        if number % 20 == 0 or number == len(index):
            print(f"[{number}/{len(index)}] last={family} n={n} s={support} rz={rz_root}->{rz_final}", flush=True)

    # scaling aggregation: mean g_reorder/g_total per (family, n)
    scaling = defaultdict(list)
    for row in rows:
        if row["g_reorder_over_g_total"] != "":
            scaling[(row["family"], row["n_qubits"])].append(row["g_reorder_over_g_total"])
    scaling_rows = [
        {
            "family": family,
            "n_qubits": n,
            "instances": len(values),
            "mean_g_reorder_over_g_total": round(sum(values) / len(values), 6),
        }
        for (family, n), values in sorted(scaling.items())
    ]

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out_csv = args.out_dir / "fragment_gap_rows.csv"
    with out_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    scaling_csv = args.out_dir / "scaling_by_family_n.csv"
    with scaling_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(scaling_rows[0].keys()), lineterminator="\n")
        writer.writeheader()
        writer.writerows(scaling_rows)

    total_gap = sum(r["gap_total_root"] for r in rows)
    total_reorder = sum(r["gap_reorder"] for r in rows)
    at_optimum = sum(1 for r in rows if r["closure_at_absolute_optimum"])
    receipt = {
        "experiment_id": EXPERIMENT_ID,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "bench_dir": str(args.bench_dir.relative_to(ROOT)),
        "bench_index_sha256": sha256(index_path),
        "instance_count": len(rows),
        "support_mismatches": 0,
        "closure_truncated_count": sum(1 for r in rows if r["closure_truncated"]),
        "closure_error_count": sum(1 for r in rows if r["closure_errors"]),
        "aggregate_g_reorder_over_g_total": round(total_reorder / total_gap, 6) if total_gap else "",
        "instances_closure_at_absolute_optimum": at_optimum,
        "total_wall_seconds": round(time.perf_counter() - started, 1),
        "fragment_gap_rows_sha256": sha256(out_csv),
        "scaling_csv_sha256": sha256(scaling_csv),
    }
    (args.out_dir / "receipt.json").write_text(
        json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n"
    )
    print(json.dumps({k: receipt[k] for k in (
        "experiment_id", "instance_count", "aggregate_g_reorder_over_g_total",
        "instances_closure_at_absolute_optimum", "closure_truncated_count",
    )}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
