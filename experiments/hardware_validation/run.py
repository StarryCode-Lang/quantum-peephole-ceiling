"""E-HW: Hardware validation of peephole optimization under device noise models.

Route 3b (noise-model simulation, NOT real hardware):
No IBM Quantum credentials were found on this machine (checked env
``QISKIT_IBM_TOKEN`` and ``~/.qiskit/qiskitrc``), and a full-repository audit
found no historical real-hardware runs.  This script therefore executes the
validation on ``qiskit_ibm_runtime.fake_provider`` backends (FakeManilaV2,
FakeNairobiV2), which ship calibration snapshots of real IBM devices, via
``qiskit_aer.AerSimulator.from_backend``.

For each of three representative circuits (GHZ, Oracle/Bernstein-Vazirani,
random UNIVERSAL; n <= 5) and three project optimizers (greedy Phase-1,
commutation Phase-2, hybrid Phase-1+2) we:

1. run the structural optimizer (noiseless, exact unitary-equivalence check),
2. transpile original and optimized circuits onto the fake backend at BOTH
   ``optimization_level=0`` (layout/routing/basis translation only) and
   ``optimization_level=1`` (default light optimization), with a fixed
   ``seed_transpiler``,
3. compute the exact ideal output distribution of the *transpiled* circuit
   (statevector on the full backend width),
4. sample the transpiled circuit on (a) a noiseless Aer simulator and
   (b) the fake-backend noisy Aer simulator, with fixed seeds,
5. record Hellinger fidelity, total-variation distance, and dominant-mode
   mass (probability of ideal-dominant bitstrings) so that the noise
   resilience gained by gate reduction can be quantified.

Why two transpile levels: at ``optimization_level=1`` the transpiler's own
1q-gate cancellation passes can absorb reductions achieved by the project
optimizers (observed for the Oracle/BV instance, where the transpiled
original and optimized circuits are literally identical).  Level 0 preserves
the pre-optimization structure and therefore exposes the raw noise benefit
of gate reduction; level 1 quantifies how much of that benefit the backend
compiler recovers on its own.

Random-instance selection (transparent, deterministic): the random UNIVERSAL
instance is chosen by an in-script scan over depth in {16, 24, 32} and seed
in {42, 7, 123, 2024}; the first configuration with hybrid reduction >= 5%
and at least one removed two-qubit gate is used (random UNIVERSAL circuits
are near their structural ceiling, so most instances show ~0% reduction).
The scan is executed live on every run and recorded in the metadata.

All numbers in the emitted CSVs come from actual simulation on this machine.
Nothing here is a real-hardware result.  A ready-to-run real-hardware
counterpart lives in ``real_hardware_protocol.py`` (requires an IBM Quantum
token; not executed in this wave).

Outputs (atomically written):
    data/v8/hardware_validation/ehw_runs_<mode>_<ts>.csv
    data/v8/hardware_validation/ehw_summary_<mode>_<ts>.csv
    data/v8/hardware_validation/ehw_metadata_<mode>_<ts>.json
"""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))

from qiskit import QuantumCircuit, transpile  # noqa: E402
from qiskit.quantum_info import Statevector  # noqa: E402
from qiskit_aer import AerSimulator  # noqa: E402
from qiskit_ibm_runtime.fake_provider import FakeManilaV2, FakeNairobiV2  # noqa: E402

from src.circuits.generator_v2 import CircuitFamily, generate_circuit  # noqa: E402
from src.circuits.real_benchmarks import (  # noqa: E402
    circuit_sha256,
    make_bernstein_vazirani,
    make_ghz,
)
from src.optimisation.phase1.greedy import GreedyGateCancellation  # noqa: E402
from src.optimisation.phase2.commutation_rewriter import (  # noqa: E402
    CommutationRewriter,
    HybridCommuteRewrite,
)
from src.provenance import run_metadata  # noqa: E402

SCHEMA_VERSION = "1.0.0"
EXPERIMENT_ID = "EHW"
VERSION = "1.1.0"

OUTPUT_DIR = PROJECT_ROOT / "data" / "v8" / "hardware_validation"

SEED = 42
SEED_TRANSPILER = 12345
TRANSPILE_LEVELS = (0, 1)
RANDOM_SCAN_DEPTHS = (16, 24, 32)
RANDOM_SCAN_SEEDS = (42, 7, 123, 2024)
RANDOM_MIN_HYBRID_REDUCTION = 0.05


# ---------------------------------------------------------------------------
# Circuit suite
# ---------------------------------------------------------------------------

def _two_qubit_count(qc: QuantumCircuit) -> int:
    return sum(1 for inst in qc.data if inst.operation.num_qubits == 2)


def select_random_circuit() -> Tuple[QuantumCircuit, dict]:
    """Deterministically select a reducible random UNIVERSAL instance.

    Scans (depth, seed) grid in fixed order and returns the first circuit
    whose hybrid-optimizer reduction is >= RANDOM_MIN_HYBRID_REDUCTION with
    at least one two-qubit gate removed.  Falls back to the best-scoring
    configuration if none qualifies.  The full scan table is returned for
    the metadata record.
    """
    scan_rows = []
    best = None
    for depth in RANDOM_SCAN_DEPTHS:
        for seed in RANDOM_SCAN_SEEDS:
            qc = generate_circuit(
                n_qubits=4, depth=depth, seed=seed, family=CircuitFamily.UNIVERSAL
            )
            hybrid = HybridCommuteRewrite(success_reduction=0.01).optimize(qc, target=qc)
            removed_2q = _two_qubit_count(qc) - _two_qubit_count(hybrid.optimized_circuit)
            scan_rows.append(
                {
                    "depth": depth,
                    "seed": seed,
                    "size": int(qc.size()),
                    "hybrid_reduction": round(float(hybrid.reduction), 6),
                    "hybrid_removed_2q": int(removed_2q),
                    "hybrid_fidelity": float(hybrid.fidelity),
                }
            )
            qualifies = (
                hybrid.reduction >= RANDOM_MIN_HYBRID_REDUCTION and removed_2q >= 1
            )
            if best is None or hybrid.reduction > best[1].reduction:
                best = (qc, hybrid, depth, seed, removed_2q)
            if qualifies:
                chosen = {
                    "depth": depth,
                    "seed": seed,
                    "selection_rule": (
                        f"first config with hybrid_reduction >= "
                        f"{RANDOM_MIN_HYBRID_REDUCTION} and >=1 removed 2q gate"
                    ),
                    "scan": scan_rows,
                }
                return qc, chosen
    qc, hybrid, depth, seed, removed_2q = best
    chosen = {
        "depth": depth,
        "seed": seed,
        "selection_rule": "fallback: max hybrid_reduction config (no config qualified)",
        "scan": scan_rows,
    }
    return qc, chosen


def build_circuits(seed: int = SEED) -> Tuple[List[Tuple[str, str, QuantumCircuit]], dict]:
    """Return ([(circuit_id, family, circuit)], random_selection_record)."""
    random_qc, selection = select_random_circuit()
    circuits = [
        ("ghz_n4", "GHZ", make_ghz(4)),
        ("oracle_bv_n4", "Oracle/BV", make_bernstein_vazirani(4, seed=seed)),
        (
            f"random_uni_n4_d{selection['depth']}_s{selection['seed']}",
            "Random/UNIVERSAL",
            random_qc,
        ),
    ]
    return circuits, selection


def build_optimizers() -> Dict[str, object]:
    """Optimizers identical to the E11 real-circuit benchmark configuration."""
    return {
        "greedy_phase1": GreedyGateCancellation(success_reduction=0.01),
        "commutation_phase2": CommutationRewriter(success_reduction=0.01),
        "hybrid_phase1_2": HybridCommuteRewrite(success_reduction=0.01),
    }


# ---------------------------------------------------------------------------
# Distribution helpers
# ---------------------------------------------------------------------------

def exact_probabilities(circuit_no_meas: QuantumCircuit) -> np.ndarray:
    """Exact output probabilities of a circuit (full width) from |0...0>."""
    sv = Statevector.from_instruction(circuit_no_meas)
    return np.asarray(sv.probabilities(), dtype=float)


def counts_to_prob(counts: Dict[str, int], width: int, shots: int) -> np.ndarray:
    """Map a Qiskit counts dict to a probability vector of length 2**width."""
    probs = np.zeros(2**width, dtype=float)
    for bitstring, count in counts.items():
        probs[int(bitstring.replace(" ", ""), 2)] += count / shots
    return probs


def hellinger_fidelity(p: np.ndarray, q: np.ndarray) -> float:
    """Classical (Hellinger) fidelity between two distributions."""
    return float(np.sum(np.sqrt(np.clip(p, 0, None) * np.clip(q, 0, None))) ** 2)


def total_variation_distance(p: np.ndarray, q: np.ndarray) -> float:
    return float(0.5 * np.sum(np.abs(p - q)))


def dominant_mode_mass(p_sampled: np.ndarray, p_exact: np.ndarray) -> float:
    """Sampled probability mass on bitstrings that dominate the ideal output.

    The dominant set is {b : p_exact(b) >= 0.5 * max(p_exact)}.  For GHZ this
    is the two all-equal components; for BV it is the secret bitstring; for
    random circuits it is the set of ideal-high-probability outcomes.
    """
    threshold = 0.5 * float(np.max(p_exact))
    mask = p_exact >= threshold
    return float(np.sum(p_sampled[mask]))


# ---------------------------------------------------------------------------
# Core experiment
# ---------------------------------------------------------------------------

def circuit_structural_metrics(qc: QuantumCircuit) -> Dict[str, int]:
    return {
        "gates": int(qc.size()),
        "depth": int(qc.depth() or 0),
        "two_qubit_gates": int(_two_qubit_count(qc)),
    }


def sample_distribution(
    simulator: AerSimulator,
    circuit_meas: QuantumCircuit,
    width: int,
    shots: int,
    seed_simulator: int,
) -> np.ndarray:
    job = simulator.run(circuit_meas, shots=shots, seed_simulator=seed_simulator)
    counts = job.result().get_counts()
    return counts_to_prob(counts, width, shots)


def run(mode: str, shots: int, seed_reps: int) -> Tuple[pd.DataFrame, pd.DataFrame, dict]:
    run_id = f"ehw_{mode}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    script_path = Path(__file__).resolve()
    metadata = run_metadata(PROJECT_ROOT, script_path, VERSION, run_id)

    circuits, random_selection = build_circuits()
    optimizers = build_optimizers()
    backends = {
        "FakeManilaV2": FakeManilaV2(),
        "FakeNairobiV2": FakeNairobiV2(),
    }
    sampling_seeds = [101 + 101 * k for k in range(seed_reps)]

    ideal_sim = AerSimulator(seed_simulator=sampling_seeds[0])

    # ------------------------------------------------------------------
    # Stage 1: structural optimization (noiseless)
    # ------------------------------------------------------------------
    versions: List[dict] = []
    for circuit_id, family, qc in circuits:
        versions.append(
            {
                "circuit_id": circuit_id,
                "family": family,
                "version": "original",
                "optimizer": "none",
                "circuit": qc,
                "logical": circuit_structural_metrics(qc),
                "unitary_fidelity_exact": 1.0,
                "optimizer_success": True,
                "optimizer_runtime_seconds": 0.0,
            }
        )
        for opt_name, optimizer in optimizers.items():
            start = time.time()
            result = optimizer.optimize(qc, target=qc)
            runtime = time.time() - start
            versions.append(
                {
                    "circuit_id": circuit_id,
                    "family": family,
                    "version": opt_name,
                    "optimizer": opt_name,
                    "circuit": result.optimized_circuit,
                    "logical": circuit_structural_metrics(result.optimized_circuit),
                    "unitary_fidelity_exact": float(result.fidelity),
                    "optimizer_success": bool(result.success),
                    "optimizer_runtime_seconds": runtime,
                }
            )

    # ------------------------------------------------------------------
    # Stage 2: transpile + exact ideal distribution + noisy sampling
    # ------------------------------------------------------------------
    rows: List[dict] = []
    transpiled_originals: Dict[Tuple[str, str, int], Dict[str, int]] = {}

    for backend_name, backend in backends.items():
        noisy_sim = AerSimulator.from_backend(backend)

        for level in TRANSPILE_LEVELS:
            for entry in versions:
                qc = entry["circuit"]
                tqc = transpile(
                    qc,
                    backend=backend,
                    optimization_level=level,
                    seed_transpiler=SEED_TRANSPILER,
                )
                physical = circuit_structural_metrics(tqc)
                width = int(tqc.num_qubits)
                p_exact = exact_probabilities(tqc)

                tqc_meas = tqc.copy()
                tqc_meas.measure_all()

                key = (entry["circuit_id"], backend_name, level)
                if entry["version"] == "original":
                    transpiled_originals[key] = physical
                orig_physical = transpiled_originals.get(key, physical)

                base = {
                    "schema_version": SCHEMA_VERSION,
                    "experiment_id": EXPERIMENT_ID,
                    "run_id": run_id,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "circuit_id": entry["circuit_id"],
                    "circuit_family": entry["family"],
                    "n_qubits_logical": int(qc.num_qubits),
                    "version": entry["version"],
                    "optimizer": entry["optimizer"],
                    "output_sha256": circuit_sha256(qc),
                    "logical_gates": entry["logical"]["gates"],
                    "logical_depth": entry["logical"]["depth"],
                    "logical_2q_gates": entry["logical"]["two_qubit_gates"],
                    "unitary_fidelity_exact": entry["unitary_fidelity_exact"],
                    "optimizer_success": entry["optimizer_success"],
                    "optimizer_runtime_seconds": round(entry["optimizer_runtime_seconds"], 6),
                    "backend_name": backend_name,
                    "backend_width": int(backend.num_qubits),
                    "transpile_optimization_level": level,
                    "seed_transpiler": SEED_TRANSPILER,
                    "transpiled_gates": physical["gates"],
                    "transpiled_depth": physical["depth"],
                    "transpiled_2q_gates": physical["two_qubit_gates"],
                    "transpiled_orig_gates": orig_physical["gates"],
                    "transpiled_orig_2q_gates": orig_physical["two_qubit_gates"],
                    "shots": shots,
                }

                for sampler_kind, simulator in (
                    ("aer_ideal", ideal_sim),
                    ("aer_noisy_fakebackend", noisy_sim),
                ):
                    for seed_simulator in sampling_seeds:
                        p_sampled = sample_distribution(
                            simulator, tqc_meas, width, shots, seed_simulator
                        )
                        row = dict(base)
                        row.update(
                            {
                                "sampler": sampler_kind,
                                "seed_simulator": seed_simulator,
                                "hellinger_fidelity": hellinger_fidelity(p_sampled, p_exact),
                                "tvd": total_variation_distance(p_sampled, p_exact),
                                "dominant_mode_mass": dominant_mode_mass(p_sampled, p_exact),
                            }
                        )
                        rows.append(row)

    runs_df = pd.DataFrame(rows)

    # ------------------------------------------------------------------
    # Stage 3: reductions + per-group aggregate + fidelity gains
    # ------------------------------------------------------------------
    runs_df["logical_reduction"] = 0.0
    runs_df["transpiled_2q_reduction"] = 0.0
    group_key = ["circuit_id", "backend_name", "transpile_optimization_level"]
    for (cid, bname, level), grp in runs_df.groupby(group_key):
        orig = grp[grp["version"] == "original"].iloc[0]
        mask = (
            (runs_df["circuit_id"] == cid)
            & (runs_df["backend_name"] == bname)
            & (runs_df["transpile_optimization_level"] == level)
        )
        if orig["logical_gates"] > 0:
            runs_df.loc[mask, "logical_reduction"] = (
                1.0 - runs_df.loc[mask, "logical_gates"] / orig["logical_gates"]
            )
        if orig["transpiled_2q_gates"] > 0:
            runs_df.loc[mask, "transpiled_2q_reduction"] = (
                1.0
                - runs_df.loc[mask, "transpiled_2q_gates"] / orig["transpiled_2q_gates"]
            )

    agg_rows = []
    group_cols = [
        "circuit_id",
        "circuit_family",
        "version",
        "optimizer",
        "backend_name",
        "transpile_optimization_level",
    ]
    for keys, grp in runs_df.groupby(group_cols):
        rec = dict(zip(group_cols, keys))
        noisy = grp[grp["sampler"] == "aer_noisy_fakebackend"]
        ideal = grp[grp["sampler"] == "aer_ideal"]
        first = grp.iloc[0]
        rec.update(
            {
                "logical_gates": int(first["logical_gates"]),
                "logical_reduction": float(first["logical_reduction"]),
                "transpiled_gates": int(first["transpiled_gates"]),
                "transpiled_2q_gates": int(first["transpiled_2q_gates"]),
                "transpiled_2q_reduction": float(first["transpiled_2q_reduction"]),
                "unitary_fidelity_exact": float(first["unitary_fidelity_exact"]),
                "noisy_hellinger_mean": float(noisy["hellinger_fidelity"].mean()),
                "noisy_hellinger_std": float(noisy["hellinger_fidelity"].std(ddof=0)),
                "noisy_tvd_mean": float(noisy["tvd"].mean()),
                "noisy_dominant_mass_mean": float(noisy["dominant_mode_mass"].mean()),
                "noisy_dominant_mass_std": float(noisy["dominant_mode_mass"].std(ddof=0)),
                "ideal_hellinger_mean": float(ideal["hellinger_fidelity"].mean()),
                "ideal_dominant_mass_mean": float(ideal["dominant_mode_mass"].mean()),
                "shots": int(first["shots"]),
                "n_seeds": int(grp["seed_simulator"].nunique()),
            }
        )
        agg_rows.append(rec)
    summary_df = pd.DataFrame(agg_rows)

    # fidelity gains vs original version of the same circuit/backend/level
    summary_df["noisy_hellinger_gain_vs_original"] = 0.0
    summary_df["noisy_dominant_mass_gain_vs_original"] = 0.0
    gain_key = ["circuit_id", "backend_name", "transpile_optimization_level"]
    for (cid, bname, level), grp in summary_df.groupby(gain_key):
        orig = grp[grp["version"] == "original"].iloc[0]
        mask = (
            (summary_df["circuit_id"] == cid)
            & (summary_df["backend_name"] == bname)
            & (summary_df["transpile_optimization_level"] == level)
        )
        summary_df.loc[mask, "noisy_hellinger_gain_vs_original"] = (
            summary_df.loc[mask, "noisy_hellinger_mean"] - orig["noisy_hellinger_mean"]
        )
        summary_df.loc[mask, "noisy_dominant_mass_gain_vs_original"] = (
            summary_df.loc[mask, "noisy_dominant_mass_mean"]
            - orig["noisy_dominant_mass_mean"]
        )

    # ------------------------------------------------------------------
    # Metadata
    # ------------------------------------------------------------------
    credential_audit = {
        "env_QISKIT_IBM_TOKEN_present": bool(os.environ.get("QISKIT_IBM_TOKEN")),
        "qiskitrc_present": (Path.home() / ".qiskit" / "qiskitrc").exists(),
        "route": "3b_noise_model_simulation_NOT_real_hardware",
    }
    metadata.update(
        {
            "mode": mode,
            "shots": shots,
            "seed_reps": seed_reps,
            "sampling_seeds": sampling_seeds,
            "seed_transpiler": SEED_TRANSPILER,
            "transpile_levels": list(TRANSPILE_LEVELS),
            "circuits": [
                {
                    "circuit_id": cid,
                    "family": fam,
                    "n_qubits": int(qc.num_qubits),
                    "sha256": circuit_sha256(qc),
                }
                for cid, fam, qc in circuits
            ],
            "random_circuit_selection": random_selection,
            "backends": {
                name: {
                    "num_qubits": int(b.num_qubits),
                    "source": "qiskit_ibm_runtime.fake_provider (calibration snapshot)",
                }
                for name, b in backends.items()
            },
            "package_versions": {
                pkg: importlib_metadata.version(pkg)
                for pkg in ("qiskit", "qiskit-aer", "qiskit-ibm-runtime", "numpy", "pandas")
            },
            "credential_audit": credential_audit,
        }
    )
    return runs_df, summary_df, metadata


# ---------------------------------------------------------------------------
# Atomic output
# ---------------------------------------------------------------------------

def atomic_write_csv(df: pd.DataFrame, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    df.to_csv(tmp, index=False)
    os.replace(tmp, path)


def atomic_write_json(payload: dict, path: Path) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, default=str)
    os.replace(tmp, path)


def backup_if_exists(path: Path) -> Optional[Path]:
    if path.exists():
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup = path.with_name(f"{path.stem}.bak-{stamp}{path.suffix}")
        path.rename(backup)
        return backup
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=["smoke", "full"], default="smoke")
    parser.add_argument("--shots", type=int, default=None,
                        help="Override shots (default: 2048 smoke / 8192 full)")
    parser.add_argument("--seed-reps", type=int, default=None,
                        help="Override sampling seed repetitions (default: 1 smoke / 3 full)")
    args = parser.parse_args()

    shots = args.shots if args.shots is not None else (2048 if args.mode == "smoke" else 8192)
    seed_reps = args.seed_reps if args.seed_reps is not None else (1 if args.mode == "smoke" else 3)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    runs_df, summary_df, metadata = run(args.mode, shots, seed_reps)

    runs_path = OUTPUT_DIR / f"ehw_runs_{args.mode}_{stamp}.csv"
    summary_path = OUTPUT_DIR / f"ehw_summary_{args.mode}_{stamp}.csv"
    metadata_path = OUTPUT_DIR / f"ehw_metadata_{args.mode}_{stamp}.json"

    for path in (runs_path, summary_path, metadata_path):
        backup_if_exists(path)
    atomic_write_csv(runs_df, runs_path)
    atomic_write_csv(summary_df, summary_path)
    atomic_write_json(metadata, metadata_path)

    print(f"[EHW] mode={args.mode} shots={shots} seed_reps={seed_reps}")
    print(f"[EHW] runs rows={len(runs_df)} -> {runs_path}")
    print(f"[EHW] summary rows={len(summary_df)} -> {summary_path}")
    print(f"[EHW] metadata -> {metadata_path}")

    cols = [
        "circuit_id", "version", "backend_name", "transpile_optimization_level",
        "logical_reduction", "transpiled_2q_reduction", "noisy_hellinger_mean",
        "noisy_hellinger_gain_vs_original", "noisy_dominant_mass_gain_vs_original",
    ]
    with pd.option_context("display.width", 220, "display.max_rows", 100):
        print(summary_df[cols].round(4).to_string(index=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
