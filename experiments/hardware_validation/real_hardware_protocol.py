"""E-HW real-hardware protocol (READY TO RUN once an IBM Quantum token exists).

STATUS: NOT executed in this wave — no IBM Quantum credentials were found on
this machine (env ``QISKIT_IBM_TOKEN`` absent, ``~/.qiskit/qiskitrc`` absent).
Everything below is written to run unchanged as soon as a token is provided.

Setup (one-time, either of):
    1. Environment variable:
           export QISKIT_IBM_TOKEN="<your-token>"          # Git Bash
           setx QISKIT_IBM_TOKEN "<your-token>"            # Windows persistent
       optionally also QISKIT_IBM_INSTANCE="<hub/group/project>" (CRN).
    2. Saved account:
           /d/Downloads/miniforge3/python -c "from qiskit_ibm_runtime import QiskitRuntimeService; QiskitRuntimeService.save_account(channel='ibm_quantum', token='<your-token>', set_as_default=True)"

Execution:
    PY=/d/Downloads/miniforge3/python
    $PY experiments/hardware_validation/real_hardware_protocol.py --shots 8192 --seed-reps 3
    # dry-run (prints the full plan, submits nothing):
    $PY experiments/hardware_validation/real_hardware_protocol.py --dry-run

Design (mirrors run.py so real results are directly comparable to the
fake-backend noise-model results in data/v8/hardware_validation/):
  * Circuits: GHZ n=4, Oracle/Bernstein-Vazirani n=4 (+ancilla = 5 qubits),
    random UNIVERSAL n=4 depth=24 seed=7 (same deterministic selection).
  * Versions: original + {greedy_phase1, commutation_phase2, hybrid_phase1_2}.
  * Transpile: locally with seed_transpiler=12345 at optimization_level 0
    and 1 (ISA circuits submitted; the backend performs no further rewriting).
  * Sampler: qiskit_ibm_runtime SamplerV2, shots=8192 per PUB, seed_reps
    independent jobs (real hardware exposes no seed_simulator; repetitions
    give sampling variability instead).
  * Metrics: Hellinger fidelity / TVD / dominant-mode mass against the exact
    ideal distribution of each transpiled circuit (statevector, computed
    locally before submission).

Cost estimate (IBM Quantum Open Plan, 10 min QPU time/month free):
  * PUBs per level-job: 3 circuits x 4 versions = 12 ISA circuits.
  * Two level-jobs x 3 seed-reps = 6 jobs total, 24 PUB executions per rep
    (72 PUB executions overall), each <= 8192 shots on <= 7 active qubits.
  * Expected QPU time per PUB: ~2-10 s (small circuits, 8192 shots).
    Total expected QPU time: ~3-8 minutes — fits the free monthly quota.
  * Queue time: highly variable (minutes to hours on shared open systems);
    recorded per job from job.metrics() when available.

Success criteria (evaluated against the emitted CSV):
  1. For every circuit with logical reduction > 0, the real-device noisy
     Hellinger fidelity of the optimized versions is >= that of the original
     within 2 standard errors (per backend, per level).
  2. GHZ dominant-mode mass (P(0000)+P(1111)) >= 0.5 on the real device
     (entanglement-witness threshold for genuine 4-qubit GHZ entanglement).
  3. BV success probability on the real device within +-0.15 of the
     fake-backend prediction at the same transpile level (model-drift bound).
  4. The random instance's dominant-mode-mass gain of hybrid_phase1_2 over
     original is positive on the real device (sign consistency with the
     noise-model prediction of +0.0044..+0.0054).

Outputs (atomically written, same schema family as run.py):
    data/v8/hardware_validation/ehw_real_runs_<ts>.csv
    data/v8/hardware_validation/ehw_real_metadata_<ts>.json
"""

from __future__ import annotations

import argparse
import importlib.metadata as importlib_metadata
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from qiskit import transpile  # noqa: E402

from run import (  # noqa: E402  (reuses the validated fake-route pipeline)
    OUTPUT_DIR,
    SEED_TRANSPILER,
    TRANSPILE_LEVELS,
    atomic_write_csv,
    atomic_write_json,
    backup_if_exists,
    build_circuits,
    build_optimizers,
    circuit_structural_metrics,
    counts_to_prob,
    dominant_mode_mass,
    exact_probabilities,
    hellinger_fidelity,
    total_variation_distance,
)
from src.circuits.real_benchmarks import circuit_sha256  # noqa: E402

EXPERIMENT_ID = "EHW-REAL"
VERSION = "1.0.0"


def discover_service():
    """Return an authenticated QiskitRuntimeService or raise SystemExit(2)."""
    try:
        from qiskit_ibm_runtime import QiskitRuntimeService
    except ImportError:  # pragma: no cover
        print("[EHW-REAL] qiskit-ibm-runtime is not installed.")
        raise SystemExit(2)

    token = os.environ.get("QISKIT_IBM_TOKEN")
    instance = os.environ.get("QISKIT_IBM_INSTANCE")
    if token:
        kwargs = {"channel": "ibm_quantum", "token": token}
        if instance:
            kwargs["instance"] = instance
        return QiskitRuntimeService(**kwargs)
    try:
        return QiskitRuntimeService()  # falls back to saved default account
    except Exception as exc:  # pragma: no cover
        print("[EHW-REAL] No IBM Quantum credentials found.")
        print("  - env QISKIT_IBM_TOKEN: absent")
        print(f"  - saved account error: {exc}")
        print("See the module docstring for one-time setup instructions.")
        raise SystemExit(2)


def job_queue_seconds(job) -> Optional[float]:
    """Best-effort queue/wait time extraction from runtime job metrics."""
    try:
        metrics = job.metrics()
        timestamps = metrics.get("timestamps", {})
        created = timestamps.get("created")
        running = timestamps.get("running")
        if created and running:
            fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
            t0 = datetime.strptime(created, fmt)
            t1 = datetime.strptime(running, fmt)
            return (t1 - t0).total_seconds()
    except Exception:
        return None
    return None


def run_real(shots: int, seed_reps: int, backend_name: Optional[str], dry_run: bool) -> int:
    from qiskit_ibm_runtime import SamplerV2 as Sampler  # deferred: needs creds

    service = discover_service()
    if backend_name:
        backend = service.backend(backend_name)
    else:
        backend = service.least_busy(operational=True, simulator=False, min_num_qubits=5)
    print(f"[EHW-REAL] backend={backend.name} num_qubits={backend.num_qubits}")

    circuits, random_selection = build_circuits()
    optimizers = build_optimizers()

    # Stage 1: structural optimization (local, noiseless)
    versions: List[dict] = []
    for circuit_id, family, qc in circuits:
        versions.append({"circuit_id": circuit_id, "family": family,
                         "version": "original", "circuit": qc,
                         "unitary_fidelity_exact": 1.0})
        for opt_name, optimizer in optimizers.items():
            result = optimizer.optimize(qc, target=qc)
            versions.append({"circuit_id": circuit_id, "family": family,
                             "version": opt_name, "circuit": result.optimized_circuit,
                             "unitary_fidelity_exact": float(result.fidelity)})

    # Stage 2: local transpile + exact ideal reference
    isa_by_level: Dict[int, List[dict]] = {level: [] for level in TRANSPILE_LEVELS}
    for level in TRANSPILE_LEVELS:
        for entry in versions:
            tqc = transpile(entry["circuit"], backend=backend,
                            optimization_level=level, seed_transpiler=SEED_TRANSPILER)
            tqc_meas = tqc.copy()
            tqc_meas.measure_all()
            isa_by_level[level].append({
                **entry,
                "transpiled": tqc,
                "transpiled_meas": tqc_meas,
                "p_exact": exact_probabilities(tqc),
                "width": int(tqc.num_qubits),
            })

    if dry_run:
        n_pubs = sum(len(v) for v in isa_by_level.values())
        print(f"[EHW-REAL] DRY RUN: {len(versions)} versions x {len(TRANSPILE_LEVELS)} levels "
              f"= {n_pubs} PUBs per job, {seed_reps} rep jobs per level, shots={shots}.")
        print("[EHW-REAL] Nothing submitted.")
        return 0

    # Stage 3: submit one job per (level, rep); record queue + usage
    rows: List[dict] = []
    job_records: List[dict] = []
    sampler = Sampler(mode=backend)
    for level in TRANSPILE_LEVELS:
        pubs = [entry["transpiled_meas"] for entry in isa_by_level[level]]
        for rep in range(seed_reps):
            submitted_at = datetime.now(timezone.utc)
            job = sampler.run(pubs, shots=shots)
            job_id = job.job_id()
            print(f"[EHW-REAL] level={level} rep={rep} job_id={job_id} ... waiting")
            result = job.result()
            queue_s = job_queue_seconds(job)
            usage_s = None
            try:
                usage_s = float(job.usage())
            except Exception:
                pass
            job_records.append({
                "job_id": job_id, "level": level, "rep": rep,
                "submitted_at_utc": submitted_at.isoformat(),
                "queue_seconds": queue_s, "usage_seconds": usage_s,
                "shots": shots, "n_pubs": len(pubs),
            })
            for entry, pub_result in zip(isa_by_level[level], result):
                counts = None
                data = pub_result.data
                for reg_name in ("meas", "c", "measure"):
                    if hasattr(data, reg_name):
                        counts = getattr(data, reg_name).get_counts()
                        break
                if counts is None:  # fall back to the first register
                    counts = next(iter(data.values())).get_counts()
                p_sampled = counts_to_prob(counts, entry["width"], shots)
                physical = circuit_structural_metrics(entry["transpiled"])
                logical = circuit_structural_metrics(entry["circuit"])
                rows.append({
                    "experiment_id": EXPERIMENT_ID,
                    "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                    "job_id": job_id,
                    "rep": rep,
                    "circuit_id": entry["circuit_id"],
                    "circuit_family": entry["family"],
                    "version": entry["version"],
                    "backend_name": backend.name,
                    "transpile_optimization_level": level,
                    "logical_gates": logical["gates"],
                    "logical_2q_gates": logical["two_qubit_gates"],
                    "transpiled_gates": physical["gates"],
                    "transpiled_2q_gates": physical["two_qubit_gates"],
                    "unitary_fidelity_exact": entry["unitary_fidelity_exact"],
                    "shots": shots,
                    "hellinger_fidelity": hellinger_fidelity(p_sampled, entry["p_exact"]),
                    "tvd": total_variation_distance(p_sampled, entry["p_exact"]),
                    "dominant_mode_mass": dominant_mode_mass(p_sampled, entry["p_exact"]),
                    "output_sha256": circuit_sha256(entry["circuit"]),
                })

    runs_df = pd.DataFrame(rows)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    runs_path = OUTPUT_DIR / f"ehw_real_runs_{stamp}.csv"
    meta_path = OUTPUT_DIR / f"ehw_real_metadata_{stamp}.json"
    for path in (runs_path, meta_path):
        backup_if_exists(path)
    atomic_write_csv(runs_df, runs_path)
    atomic_write_json({
        "experiment_id": EXPERIMENT_ID,
        "version": VERSION,
        "backend": backend.name,
        "shots": shots,
        "seed_reps": seed_reps,
        "seed_transpiler": SEED_TRANSPILER,
        "transpile_levels": list(TRANSPILE_LEVELS),
        "random_circuit_selection": random_selection,
        "jobs": job_records,
        "package_versions": {
            pkg: importlib_metadata.version(pkg)
            for pkg in ("qiskit", "qiskit-aer", "qiskit-ibm-runtime")
        },
    }, meta_path)
    print(f"[EHW-REAL] rows={len(runs_df)} -> {runs_path}")
    print(f"[EHW-REAL] metadata -> {meta_path}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--shots", type=int, default=8192)
    parser.add_argument("--seed-reps", type=int, default=3)
    parser.add_argument("--backend", type=str, default=None,
                        help="Backend name (default: least-busy real device, >=5 qubits)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the execution plan without submitting jobs")
    args = parser.parse_args()
    return run_real(args.shots, args.seed_reps, args.backend, args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
