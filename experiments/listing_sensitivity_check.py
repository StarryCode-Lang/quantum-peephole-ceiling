"""Listing-sensitivity check for production compilers (compiler listing audit).

Question: does the *flat listing* of a circuit (the linear order of instructions)
determine the reachable peephole action space of production compilers, the way
it does for a flat-list peephole prototype ("listing model determines the
reachable action space")?

Method: for a set of suite circuits, generate random *unitary-preserving*
relistings by repeatedly swapping adjacent instructions that act on disjoint
qubits (always a symmetry of the unitary). Each relisting is a different flat
listing of the same circuit. Then compile every variant with

  - Qiskit 2.4.1 transpile(optimization_level=3, fair mode, fixed seed)
  - pytket 2.18.0 FullPeepholeOptimise(allow_swaps=False)   [swap elision off,
    so gate counts are comparable and the implicit-permutation hazard documented
    in experiments/reproduce_tket_clifford_unitarity.py cannot confound]
  - Cirq 1.6.1 benchmark pipeline (drop_empty/negligible -> CZTargetGateset ->
    eject_z -> merge_single_qubit -> drop_empty)

and record the optimized gate count per variant. If a compiler's output gate
count is invariant across all relistings, its peephole window is defined by the
DAG / moment representation, not by the flat listing; variance would indicate
listing sensitivity.

Positive control: the repo's flat-list prototype (Phase-1 GreedyGateCancellation)
is included to demonstrate what listing sensitivity looks like.

Wave-5 expansion (2026-07-21): extended from 4 families x n=5 x 20 variants to
all 15 suite families x n={3,5,8} x 50 variants, with CSV + metadata output to
data/v8/listing_sensitivity/.

Run:  D:\\Downloads\\miniforge3\\python experiments\\listing_sensitivity_check.py
      D:\\Downloads\\miniforge3\\python experiments\\listing_sensitivity_check.py --smoke
"""

from __future__ import annotations

import argparse
import json
import platform
import random
import subprocess
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator

from src.circuits.real_benchmarks import generate_extended_suite

# Wave-5 expanded constants
N_VARIANTS = 50
N_QUBITS_LIST = [3, 5, 8]
SEED = 42
EXPERIMENT_ID = "E_listing_sensitivity_v8"
VERSION = "2.0.0"
DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "v8" / "listing_sensitivity"


def relist(circuit: QuantumCircuit, n_swaps: int, rng: random.Random) -> QuantumCircuit:
    """Return a unitary-preserving relisting via adjacent disjoint-gate swaps."""
    data = list(circuit.data)

    def qindex(inst) -> set[int]:
        return {circuit.find_bit(q).index for q in inst.qubits}

    for _ in range(n_swaps):
        i = rng.randrange(len(data) - 1)
        if qindex(data[i]).isdisjoint(qindex(data[i + 1])):
            data[i], data[i + 1] = data[i + 1], data[i]
    out = QuantumCircuit(circuit.num_qubits)
    out.global_phase = circuit.global_phase
    for inst in data:
        qidx = [circuit.find_bit(q).index for q in inst.qubits]
        cidx = [circuit.find_bit(c).index for c in inst.clbits]
        out.append(inst.operation, qidx, cidx)
    return out


def compile_qiskit(qc: QuantumCircuit) -> int:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        out = transpile(qc, optimization_level=3, seed_transpiler=SEED)
    return out.size()


def compile_tket(qc: QuantumCircuit) -> int:
    from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
    from pytket.passes import DecomposeBoxes, FullPeepholeOptimise

    tk = qiskit_to_tk(qc)
    DecomposeBoxes().apply(tk)
    FullPeepholeOptimise(allow_swaps=False).apply(tk)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return tk_to_qiskit(tk).size()


def compile_cirq(qc: QuantumCircuit) -> int:
    import cirq
    from cirq.contrib.qasm_import import circuit_from_qasm
    from cirq.transformers import (
        drop_empty_moments,
        drop_negligible_operations,
        eject_z,
        merge_single_qubit_gates_to_phased_x_and_z,
        optimize_for_target_gateset,
    )
    from qiskit.qasm2 import dumps as qasm2_dumps

    cc = circuit_from_qasm(qasm2_dumps(qc))
    cc = drop_empty_moments(cc)
    cc = drop_negligible_operations(cc)
    cc = optimize_for_target_gateset(cc, gateset=cirq.CZTargetGateset())
    cc = eject_z(cc)
    cc = merge_single_qubit_gates_to_phased_x_and_z(cc)
    cc = drop_empty_moments(cc)
    return sum(1 for _ in cc.all_operations())


def compile_prototype(qc: QuantumCircuit) -> int:
    from src.optimisation.phase1.greedy import GreedyGateCancellation

    opt = GreedyGateCancellation(success_reduction=0.01)
    return opt.optimize(qc, target=qc).optimized_circuit.size()


def main() -> int:
    parser = argparse.ArgumentParser(description="Listing-sensitivity check (wave-5 expanded)")
    parser.add_argument("--smoke", action="store_true",
                        help="Quick mode: 5 variants, n=3 only")
    parser.add_argument("--n-variants", type=int, default=None,
                        help="Override variant count")
    parser.add_argument("--sizes", type=str, default=None,
                        help="Comma-separated n values, e.g. '3,5,8'")
    parser.add_argument("--output-dir", type=str, default=None)
    args = parser.parse_args()

    n_variants = args.n_variants or (5 if args.smoke else N_VARIANTS)
    if args.sizes:
        n_list = [int(x) for x in args.sizes.split(",")]
    elif args.smoke:
        n_list = [3]
    else:
        n_list = N_QUBITS_LIST
    out_dir = Path(args.output_dir) if args.output_dir else DATA_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    suite = {
        bc.circuit_id: bc
        for bc in generate_extended_suite(mode="full", seed=SEED)
        if bc.circuit.num_qubits in n_list
    }
    tools = {
        "qiskit_L3": compile_qiskit,
        "tket_FPO_noswap": compile_tket,
        "cirq_default": compile_cirq,
        "prototype_greedy": compile_prototype,
    }
    print(f"Listing-sensitivity check (wave-5): {n_variants} unitary-preserving "
          f"relistings per circuit, n={n_list}")
    print(f"Circuits: {len(suite)} across {len(set(bc.family for bc in suite.values()))} families\n")

    all_rows = []
    t_start = time.time()
    any_sensitive = False
    chunk_csv = out_dir / f"listing_sensitivity_v8_chunk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    chunk_written = False

    for name in sorted(suite):
        bc = suite[name]
        qc = bc.circuit
        fam = bc.family
        n = qc.num_qubits
        rng = random.Random(1234)
        variants = [qc] + [relist(qc, n_swaps=4 * qc.size(), rng=rng)
                           for _ in range(n_variants - 1)]
        # sanity: relistings preserve the unitary
        try:
            u0 = Operator(qc).data
            unitary_ok = all(np.allclose(Operator(v).data, u0, atol=1e-10)
                             for v in variants[1:])
        except Exception:
            unitary_ok = None  # too large for exact; skip check
        if unitary_ok is False:
            print(f"  SKIP {name}: relisting changed the unitary", flush=True)
            continue

        family_rows = []
        for vi, variant in enumerate(variants):
            for tool, fn in tools.items():
                try:
                    gc = fn(variant)
                except Exception as exc:
                    gc = -1
                    err = str(exc)[:80]
                else:
                    err = ""
                row = {
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
                }
                family_rows.append(row)
                all_rows.append(row)
                if vi == 0 and gc >= 0:
                    base_gc = gc
                if vi > 0 and gc >= 0 and gc != base_gc:
                    any_sensitive = True

        # Incremental write: append this family's rows to chunk CSV
        fam_df = pd.DataFrame(family_rows)
        fam_df.to_csv(chunk_csv, mode='a', header=not chunk_written, index=False)
        chunk_written = True

        elapsed = time.time() - t_start
        print(f"  {name:<24} n={n} fam={fam:<18} ({len(all_rows)//len(tools)} "
              f"variants done, {elapsed:.0f}s)", flush=True)

    df = pd.DataFrame(all_rows)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    csv_path = out_dir / f"listing_sensitivity_v8_{ts}.csv"

    # Atomic write
    tmp = out_dir / (csv_path.name + ".tmp")
    df.to_csv(tmp, index=False)
    tmp.replace(csv_path)

    # Canonical symlink/copy
    canonical = out_dir / "listing_sensitivity_v8.csv"
    if canonical.exists():
        bak = out_dir / f"listing_sensitivity_v8.csv.bak-{ts}"
        canonical.replace(bak)
    df.to_csv(canonical, index=False)

    # Summary per family x tool
    summary_rows = []
    for (fam, n, tool), grp in df[df.gate_count >= 0].groupby(["circuit_family", "n_qubits", "tool"]):
        counts = grp.gate_count.values
        summary_rows.append({
            "circuit_family": fam,
            "n_qubits": n,
            "tool": tool,
            "n_variants": len(counts),
            "min_gates": int(counts.min()),
            "max_gates": int(counts.max()),
            "distinct_outputs": int(len(set(counts))),
            "std_gates": float(counts.std()) if len(counts) > 1 else 0.0,
            "listing_sensitive": bool(len(set(counts)) > 1),
        })
    summary_df = pd.DataFrame(summary_rows)
    summary_path = out_dir / "family_summary_v8.csv"
    tmp2 = out_dir / (summary_path.name + ".tmp")
    summary_df.to_csv(tmp2, index=False)
    tmp2.replace(summary_path)

    # Metadata
    import qiskit
    try:
        git_commit = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=Path(__file__).resolve().parent.parent,
            text=True).strip()
    except Exception:
        git_commit = "unknown"
    metadata = {
        "experiment_id": EXPERIMENT_ID,
        "version": VERSION,
        "description": (
            "Listing-sensitivity check: unitary-preserving relistings compiled "
            "by production compilers (Qiskit L3, pytket FPO no-swap, Cirq) and "
            "flat-list prototype. Wave-5 expansion: all 15 families x n={3,5,8} "
            f"x {n_variants} variants."),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "n_rows": int(len(df)),
        "n_variants": n_variants,
        "n_qubits_list": n_list,
        "families": sorted(df.circuit_family.unique().tolist()),
        "tools": sorted(df.tool.unique().tolist()),
        "seed": SEED,
        "python_version": platform.python_version(),
        "qiskit_version": qiskit.__version__,
        "git_commit": git_commit,
        "canonical_data_file": canonical.name,
        "summary_file": summary_path.name,
        "chunk_file": csv_path.name,
    }
    meta_path = out_dir / "metadata.json"
    if meta_path.exists():
        bak2 = out_dir / f"metadata.json.bak-{ts}"
        meta_path.replace(bak2)
    tmp3 = out_dir / "metadata.json.tmp"
    with open(tmp3, "w") as f:
        json.dump(metadata, f, indent=2)
    tmp3.replace(meta_path)

    print(f"\n{'='*70}")
    print(f"VERDICT: {'some tool IS listing-sensitive' if any_sensitive else 'all tested tools are flat-listing invariant'}")
    print(f"Rows: {len(df)} -> {canonical}")
    print(f"Summary: {summary_path}")
    print(f"Metadata: {meta_path}")
    print(f"Sensitive combos: {len(summary_df[summary_df.listing_sensitive])}/{len(summary_df)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
