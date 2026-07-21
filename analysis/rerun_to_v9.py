"""Rerun an experiment's run.py with output redirected to data/v9/<eXX>/.

Does NOT modify files under experiments/. Instead it reads the run.py source,
rewrites only the `output_dir = PROJECT_ROOT / "data" / "vX" / "eYY"` line to
point at data/v9/<eYY>, and execs the patched source with __file__ set to the
real script path (so PROJECT_ROOT and source hashes resolve correctly).

--fidelity-samples N: monkey-patch BaseOptimizer._estimate_fidelity to use N
samples instead of DEFAULT_FIDELITY_SAMPLES (1000). This ONLY affects the
sampled-fidelity path for circuits with n > MAX_EXACT_FIDELITY_QUBITS (12).
Exact fidelity (n <= 12) and all gate-count / reduction metrics are untouched.
Rationale: the 1000-sample Haar-product estimator on 15-20 qubit circuits
(hundreds of statevector evolutions of 2^20 amplitudes per optimize call) is
what made the wave-5 E13 rerun time out; the sampled fidelity values for n>12
are non-deterministic across sampler versions anyway (review H4 changed both
the scheme and the sample count since the canonical run).

Usage:
  /d/Downloads/miniforge3/python analysis/rerun_to_v9.py e13 --mode smoke
  /d/Downloads/miniforge3/python analysis/rerun_to_v9.py e13 --fidelity-samples 8
"""
from __future__ import annotations

import argparse
import re
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# Defaults mirror each experiment's canonical metadata.json exactly.
RUN_PY = {
    "e12": ("experiments/e12_compiler_baseline/run.py", "v4",
            {"mode": "full", "seed": 42, "max_qubits_fidelity": 10,
             "no_coupling_map": True}),
    "e15": ("experiments/e15_multi_compiler/run.py", "v5",
            {"mode": "full", "seed": 42, "max_qubits_fidelity": 10,
             "skip_cirq": True, "skip_tket": True}),
    "e18": ("experiments/e18_clifford_t/run.py", "v5",
            {"mode": "full", "seed": 42, "max_qubits_fidelity": 10}),
    "e20": ("experiments/e20_multi_compiler_full/run.py", "v6",
            {"mode": "full", "seed": 42, "max_qubits_fidelity": 10,
             "skip_custom": True, "per_circuit_timeout": 60.0}),
    "e13": ("experiments/e13_structural_ceiling/run.py", "v4",
            {"mode": "full", "seed": 42, "window": 10}),
    "e14": ("experiments/e14_extended_benchmark/run.py", "v5",
            {"mode": "full", "seed": 42, "max_qubits_fidelity": 10,
             "window_sizes": [2, 5, 10, 20, 50]}),
    "e16": ("experiments/e16_window_scaling/run.py", "v5",
            {"mode": "full", "seed": 42, "max_qubits_fidelity": 10,
             "window_sizes": [2, 5, 10, 20, 50]}),
    "e17": ("experiments/e17_connectivity/run.py", "v5",
            {"mode": "full", "seed": 42, "max_qubits_fidelity": 10,
             "topologies": ["linear", "grid", "heavy_hex"]}),
}


def load_patched_module(exp: str):
    rel, canon_ver, _ = RUN_PY[exp]
    script = PROJECT_ROOT / rel
    src = script.read_text(encoding="utf-8")
    # Rewrite the canonical output dir to the v9 rerun dir.
    pattern = rf'output_dir = PROJECT_ROOT / "data" / "{canon_ver}" / "{exp}"'
    replacement = f'output_dir = PROJECT_ROOT / "data" / "v9" / "{exp}"'
    new_src, n = re.subn(re.escape(pattern), replacement, src)
    if n < 1:
        raise RuntimeError(f"output_dir rewrite failed for {exp} (matches={n})")
    glb = {"__file__": str(script), "__name__": f"rerun_{exp}"}
    exec(compile(new_src, str(script), "exec"), glb)
    return glb


def patch_fidelity_samples(n_samples: int) -> None:
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.optimisation.base import BaseOptimizer

    orig = BaseOptimizer._estimate_fidelity

    def patched(self, circuit, target, n_samples_override=None):
        return orig(self, circuit, target, n_samples=n_samples)

    BaseOptimizer._estimate_fidelity = patched
    print(f"[rerun_to_v9] fidelity sampler capped at {n_samples} samples "
          f"(affects only n>12 sampled-fidelity path)", flush=True)


def patch_bypass_fidelity() -> None:
    """E13-only: fidelity is not part of the E13 output schema at all, so skip
    the expensive exact/sampled fidelity computation entirely. Zero effect on
    any recorded column."""
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.optimisation.base import BaseOptimizer

    BaseOptimizer.calculate_fidelity = lambda self, circuit, target: 1.0
    print("[rerun_to_v9] fidelity BYPASSED (E13 schema has no fidelity column)",
          flush=True)


def patch_fast_fidelity(n_samples: int = 32, max_exact: int = 10) -> None:
    """Runtime-only fidelity acceleration for E14/E16/E17 reruns.

    Applied patches (none of them touch reduction / gate-count / structural
    columns; only the fidelity column is affected):
      1. identical circuits -> 1.0 (exact semantics)
      2. both-Clifford and tableau-equal -> 1.0 (exact semantics)
      3. memoization on (sha256(optimized), sha256(target)) - the experiment
         loops recompute fidelity for identical (circuit, optimizer-output)
         pairs across window sizes
      4. exact Operator fidelity capped at n <= max_exact (default 10, down
         from 12): n=11/12 rows fall to the sampled estimator. At n=12 the
         exact path costs ~70 s per call (4096x4096 Operator composition)
         which is what blew the time budget
      5. sampled estimator (n > max_exact) uses n_samples (default 32)
         instead of 1000. For functionality-preserving optimizers every
         sample yields overlap exactly 1.0, so values match the exact
         result; genuinely degraded circuits get a noisier estimate
         (documented in the wave6 report).
    """
    sys.path.insert(0, str(PROJECT_ROOT))
    from src.optimisation import base as base_mod
    from src.optimisation.base import BaseOptimizer
    from src.circuits.real_benchmarks import circuit_sha256

    base_mod.MAX_EXACT_FIDELITY_QUBITS = max_exact

    orig_est = BaseOptimizer._estimate_fidelity

    def patched_est(self, circuit, target, n_samples_override=None):
        return orig_est(self, circuit, target, n_samples=n_samples)

    BaseOptimizer._estimate_fidelity = patched_est

    orig_calc = BaseOptimizer.calculate_fidelity
    cache: dict = {}
    clifford_gates = {'h', 'x', 'y', 'z', 's', 'sdg', 'cx', 'cnot', 'cz', 'swap', 'id'}

    def fast_calc(self, circuit, target):
        if circuit == target:
            return 1.0
        try:
            from qiskit.quantum_info import Clifford
            if all(i.operation.name in clifford_gates for i in circuit.data) and \
               all(i.operation.name in clifford_gates for i in target.data):
                if Clifford(circuit) == Clifford(target):
                    return 1.0
        except Exception:
            pass
        key = (circuit_sha256(circuit), circuit_sha256(target))
        if key not in cache:
            cache[key] = orig_calc(self, circuit, target)
        return cache[key]

    BaseOptimizer.calculate_fidelity = fast_calc
    print(f"[rerun_to_v9] fast fidelity: exact<=n{max_exact}, samples={n_samples}, "
          f"equality+Clifford shortcuts, memoized", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("experiment", choices=sorted(RUN_PY))
    parser.add_argument("--mode", default=None)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--fidelity-samples", type=int, default=None)
    parser.add_argument("--bypass-fidelity", action="store_true")
    parser.add_argument("--fast-fidelity", action="store_true")
    parser.add_argument("--extra", nargs="*", default=[],
                        help="extra k=v kwargs passed to run()")
    args = parser.parse_args()

    if args.bypass_fidelity:
        patch_bypass_fidelity()
    elif args.fast_fidelity:
        patch_fast_fidelity(n_samples=args.fidelity_samples or 32)
    elif args.fidelity_samples:
        patch_fidelity_samples(args.fidelity_samples)

    _, _, defaults = RUN_PY[args.experiment]
    kwargs = dict(defaults)
    if args.mode:
        kwargs["mode"] = args.mode
    if args.seed is not None:
        kwargs["seed"] = args.seed
    for kv in args.extra:
        k, v = kv.split("=", 1)
        kwargs[k] = int(v) if v.isdigit() else v

    glb = load_patched_module(args.experiment)
    run_fn = glb["run"]
    t0 = time.time()
    print(f"[rerun_to_v9] {args.experiment} kwargs={kwargs}", flush=True)
    run_fn(**kwargs)
    print(f"[rerun_to_v9] {args.experiment} done in {time.time()-t0:.1f}s", flush=True)


if __name__ == "__main__":
    main()
