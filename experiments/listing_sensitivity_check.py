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

Run:  /d/Downloads/miniforge3/python experiments/listing_sensitivity_check.py
"""

from __future__ import annotations

import random
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.quantum_info import Operator

from src.circuits.real_benchmarks import generate_extended_suite

N_VARIANTS = 20
FAMILIES = ["RandomClifford", "IQP", "QAOA", "VQE"]
N_QUBITS = 5
SEED = 42


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
    suite = {
        bc.circuit_id: bc
        for bc in generate_extended_suite(mode="full", seed=SEED)
        if bc.family in FAMILIES and bc.circuit.num_qubits == N_QUBITS
    }
    tools = {
        "qiskit_L3": compile_qiskit,
        "tket_FPO_noswap": compile_tket,
        "cirq_default": compile_cirq,
        "prototype_greedy": compile_prototype,
    }
    print(f"Listing-sensitivity check: {N_VARIANTS} unitary-preserving relistings "
          f"per circuit (adjacent disjoint-gate swaps), n = {N_QUBITS}\n")
    print(f"{'circuit':<14}{'tool':<20}{'base':>5}{'min':>5}{'max':>5}"
          f"{'distinct':>9}  counts")
    print("-" * 100)
    any_sensitive = False
    for name in sorted(suite):
        qc = suite[name].circuit
        rng = random.Random(1234)
        variants = [qc] + [relist(qc, n_swaps=4 * qc.size(), rng=rng)
                           for _ in range(N_VARIANTS - 1)]
        # sanity: relistings preserve the unitary
        u0 = Operator(qc).data
        assert all(np.allclose(Operator(v).data, u0, atol=1e-10) for v in variants[1:]), \
            f"relisting changed the unitary for {name}"
        for tool, fn in tools.items():
            try:
                counts = [fn(v) for v in variants]
            except Exception as exc:  # report, don't hide
                print(f"{name:<14}{tool:<20}  ERROR: {exc}")
                continue
            spread = len(set(counts))
            if spread > 1:
                any_sensitive = True
            print(f"{name:<14}{tool:<20}{qc.size():>5}{min(counts):>5}{max(counts):>5}"
                  f"{spread:>9}  {counts[:10]}{'...' if len(counts) > 10 else ''}")
    print()
    print("VERDICT:", "some tool IS listing-sensitive" if any_sensitive
          else "all tested tools are flat-listing invariant on this suite")
    return 0


if __name__ == "__main__":
    sys.exit(main())
