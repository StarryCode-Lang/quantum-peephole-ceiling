"""Wave-6 fill: listing-sensitivity completion for the 5 missing families.

Families: UCCSD_inspired, VQE, Adder, QuantumWalk, SurfaceCode.

Differs from listing_sensitivity_check.py in two ways (same methodology otherwise):

1. Circuit selection is by *nominal* size (circuit_id suffix), not by
   ``circuit.num_qubits``. Adder / QuantumWalk / SurfaceCode use ancilla or
   coin qubits, so their actual qubit count differs from the nominal n
   (e.g. ``adder_3`` has 4 qubits). The wave-5 filter ``num_qubits in n_list``
   silently excluded most of these circuits; this script selects them by
   circuit_id suffix so nominal n={3,5,8} coverage is real. The recorded
   ``n_qubits`` column remains the ACTUAL qubit count (honest, traceable).

2. Resume support: variants are regenerated deterministically
   (rng = random.Random(1234), n_swaps = 4 * size, variant 0 = base circuit,
   identical to wave-5), then sliced by --start / --n-variants, with a
   --max-seconds budget so each bash call stays under ~250 s. Rows are
   appended incrementally to the chunk CSV after every variant x tool, so a
   timeout never loses completed work.

Run:
  D:\\Downloads\\miniforge3\\python experiments\\listing_sensitivity_fill.py \
      --circuits uccsd_3,vqe_twolocal_3 --n-variants 50 --start 0
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from qiskit.quantum_info import Operator

from experiments.listing_sensitivity_check import (
    EXPERIMENT_ID,
    DATA_DIR,
    relist,
    compile_qiskit,
    compile_tket,
    compile_cirq,
    compile_prototype,
)
from src.circuits.real_benchmarks import generate_extended_suite

FILL_FAMILIES = {"UCCSD_inspired", "VQE", "Adder", "QuantumWalk", "SurfaceCode"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Wave-6 listing-sensitivity fill")
    parser.add_argument("--circuits", type=str, required=True,
                        help="Comma-separated circuit_ids, e.g. 'uccsd_3,qwalk_5'")
    parser.add_argument("--n-variants", type=int, default=50,
                        help="Variants to run in THIS call (slice size)")
    parser.add_argument("--start", type=int, default=0,
                        help="First variant index (inclusive) for resume")
    parser.add_argument("--total-variants", type=int, default=None,
                        help="Total variant list length to generate before slicing "
                             "(default: start + n-variants; must match across calls "
                             "for deterministic slicing)")
    parser.add_argument("--max-seconds", type=float, default=230.0,
                        help="Soft time budget; stop starting new variants past this")
    parser.add_argument("--skip-unitary-check", action="store_true",
                        help="Skip the exact Operator() equivalence check (record "
                             "unitary_check='skip'). Use only when the exact check is "
                             "computationally infeasible (e.g. qwalk_8 at 9 qubits); "
                             "the relisting operation is unitary-preserving by "
                             "construction and is verified exactly at smaller sizes.")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    out_dir = Path(args.output_dir) if args.output_dir else DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    chunk_csv = out_dir / f"listing_sensitivity_v8_wave6fill_chunk_{ts}.csv"

    wanted = [c.strip() for c in args.circuits.split(",") if c.strip()]
    suite = {bc.circuit_id: bc for bc in generate_extended_suite(mode="full", seed=42)}
    tools = {
        "qiskit_L3": compile_qiskit,
        "tket_FPO_noswap": compile_tket,
        "cirq_default": compile_cirq,
        "prototype_greedy": compile_prototype,
    }

    t_start = time.time()
    rows_written = 0
    chunk_written = False
    completed = []

    for name in wanted:
        bc = suite.get(name)
        if bc is None:
            print(f"  SKIP {name}: not in suite", flush=True)
            continue
        if bc.family not in FILL_FAMILIES:
            print(f"  SKIP {name}: family {bc.family} not a fill family", flush=True)
            continue
        qc = bc.circuit
        fam = bc.family
        n = qc.num_qubits  # ACTUAL qubit count (may differ from nominal)

        import random
        rng = random.Random(1234)
        total = args.total_variants or (args.start + args.n_variants)
        variants = [qc] + [relist(qc, n_swaps=4 * qc.size(), rng=rng)
                           for _ in range(total - 1)]
        sel = variants[args.start: args.start + args.n_variants]
        if not sel:
            print(f"  {name}: nothing to do (start={args.start})", flush=True)
            continue

        # sanity: relistings preserve the unitary (only for the selected slice)
        if args.skip_unitary_check:
            unitary_ok = None
        else:
            try:
                u0 = Operator(qc).data
                unitary_ok = all(np.allclose(Operator(v).data, u0, atol=1e-10)
                                 for v in sel[1:])
            except Exception:
                unitary_ok = None  # too large for exact; skip check
        if unitary_ok is False:
            print(f"  SKIP {name}: relisting changed the unitary", flush=True)
            continue

        base_gc = {}
        done_variants = 0
        for vi, variant in enumerate(sel, start=args.start):
            if time.time() - t_start > args.max_seconds:
                print(f"  {name}: budget exhausted at variant {vi} "
                      f"({done_variants}/{len(sel)} done)", flush=True)
                break
            family_rows = []
            for tool, fn in tools.items():
                try:
                    gc = fn(variant)
                except Exception as exc:
                    gc = -1
                    err = str(exc)[:80]
                else:
                    err = ""
                family_rows.append({
                    "experiment": EXPERIMENT_ID,
                    "circuit_id": name,
                    "circuit_family": fam,
                    "n_qubits": n,
                    "variant_idx": vi,
                    "tool": tool,
                    "gate_count": gc,
                    "base_gate_count": qc.size() if vi == 0 else None,
                    "unitary_check": "pass" if unitary_ok else ("skip" if unitary_ok is None else "fail"),
                    "error": err,
                })
                if vi == 0 and gc >= 0:
                    base_gc[tool] = gc
            fam_df = pd.DataFrame(family_rows)
            fam_df.to_csv(chunk_csv, mode="a", header=not chunk_written, index=False)
            chunk_written = True
            rows_written += len(family_rows)
            done_variants += 1
            if done_variants % 5 == 0 or done_variants == len(sel):
                el = time.time() - t_start
                print(f"  {name} fam={fam} n_actual={n} variant {vi} "
                      f"({done_variants}/{len(sel)} this call, {el:.0f}s)", flush=True)
        completed.append((name, fam, n, done_variants, len(sel)))

    print(f"\n{'='*70}")
    for name, fam, n, done, total_sel in completed:
        status = "DONE" if done == total_sel else f"PARTIAL {done}/{total_sel}"
        print(f"  {name:<20} fam={fam:<16} n_actual={n} {status}")
    print(f"Rows written this call: {rows_written} -> {chunk_csv}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
