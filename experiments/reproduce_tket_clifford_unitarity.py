"""Minimal reproduction: pytket 2.18.0 FullPeepholeOptimise unitarity violation on random Clifford circuits.

Context (wave-1 audit, docs/review/wave1/compiler_baseline.md Sec. 1.4 and
docs/results/sota_compiler_benchmark.md Sec. 8): 14 of 30 t|ket> RandomClifford
trials in the canonical run (data/v6/sota_benchmark/raw/tket_default_20260718_173443.csv)
fail exact fidelity with F_avg in {1/3, 5/17, 3/11} = (d/4 + 1)/(d + 1) for
d = 2^n, i.e. |Tr(U_in^dagger U_out)| = d/2 exactly. The optimized unitary
differs from the target on half the computational basis.

This script reproduces the failure directly with pytket calls (no benchmark
harness), for the recorded failing cells:
  - n = 3, trial 2 (seed 2042): F_avg = 1/3
  - n = 4, trial 4 (seed 4042): F_avg = 5/17  (~0.2941)
  - n = 5, trial 4 (seed 4042): F_avg = 3/11  (~0.2727), 40 -> 10 gates

Circuit generation is identical to the benchmark suite:
``make_random_clifford(n, depth=10, seed=trial_seed + 800 + n)`` with
``trial_seed = 42 + 1000 * trial``.

Run:  /d/Downloads/miniforge3/python experiments/reproduce_tket_clifford_unitarity.py
Expected exit code: 0 with REPRODUCED lines (the bug is real); the script does
not raise on reproduction because the bug itself is the object of study.
"""

from __future__ import annotations

import sys

import numpy as np
import pytket
from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
from pytket.passes import DecomposeBoxes, FullPeepholeOptimise
from qiskit.quantum_info import Operator

# Repo root on sys.path so `src.circuits.real_benchmarks` imports cleanly.
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.circuits.real_benchmarks import make_random_clifford  # noqa: E402

BASE_SEED = 42
TRIAL_STRIDE = 1000

# (n_qubits, trial) cells recorded as fidelity failures in the canonical CSV.
FAILING_CELLS = [(3, 2), (4, 4), (5, 4)]
# (n_qubits, trial) cells recorded as fidelity-passing (controls).
PASSING_CELLS = [(3, 0), (4, 0), (5, 0)]


def average_gate_fidelity(u_in: np.ndarray, u_out: np.ndarray) -> tuple[float, float]:
    """Return (F_avg, |Tr(U_in^d U_out)|). F_avg = (|Tr|^2 / d + 1) / (d + 1)."""
    d = u_in.shape[0]
    tr = abs(np.trace(u_in.conj().T @ u_out))
    f_avg = (tr**2 / d + 1.0) / (d + 1.0)
    return f_avg, tr


def run_cell(n_qubits: int, trial: int) -> dict:
    trial_seed = BASE_SEED + trial * TRIAL_STRIDE
    qc = make_random_clifford(n_qubits, depth=10, seed=trial_seed + 800 + n_qubits)

    tk_circ = qiskit_to_tk(qc)
    DecomposeBoxes().apply(tk_circ)
    FullPeepholeOptimise().apply(tk_circ)
    qc_out = tk_to_qiskit(tk_circ)

    # Exact unitary comparison (benchmark protocol: exact fidelity for n <= 8).
    u_in = Operator(qc).data
    u_out = Operator(qc_out).data
    f_avg, tr = average_gate_fidelity(u_in, u_out)
    d = u_in.shape[0]
    return {
        "n": n_qubits,
        "trial": trial,
        "seed": trial_seed,
        "gates_in": qc.size(),
        "gates_out": qc_out.size(),
        "f_avg": f_avg,
        "tr": tr,
        "d": d,
        "f_expected_if_tr_eq_d_half": (d / 4.0 + 1.0) / (d + 1.0),
    }


def main() -> int:
    print(f"pytket version: {pytket.__version__}")
    print("Reproducing t|ket> FullPeepholeOptimise unitarity failures "
          "(RandomClifford family, benchmark suite seeds)\n")
    header = f"{'n':>2} {'trial':>5} {'gates':>10} {'F_avg':>10} {'|Tr|':>8} {'d/2':>6} {'verdict':>18}"
    print(header)
    print("-" * len(header))
    reproduced = 0
    for n, trial in FAILING_CELLS + PASSING_CELLS:
        r = run_cell(n, trial)
        broken = r["f_avg"] < 0.999
        matches_half_trace = abs(r["tr"] - r["d"] / 2.0) < 1e-6
        if broken and matches_half_trace:
            verdict = "REPRODUCED"
            reproduced += 1
        elif broken:
            verdict = "BROKEN (other)"
        else:
            verdict = "ok (control)"
        print(f"{r['n']:>2} {r['trial']:>5} "
              f"{r['gates_in']:>4}->{r['gates_out']:<4} "
              f"{r['f_avg']:>10.6f} {r['tr']:>8.4f} {r['d'] // 2:>6} {verdict:>18}")
    print()
    print(f"Reproduced {reproduced}/{len(FAILING_CELLS)} recorded failures with "
          f"|Tr(U_in^d U_out)| = d/2 exactly (F_avg = (d/4 + 1)/(d + 1)).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
