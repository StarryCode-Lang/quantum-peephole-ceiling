#!/usr/bin/env python3
"""
One-Command Reproduction Script for Q-Research Project
======================================================
Runs all experiments, generates figures, and verifies data integrity.

Usage:
    python scripts/reproduce_all.py [--experiments E1 E2 ...] [--figures] [--tests] [--verify]

Options:
    --experiments: Space-separated list of experiments to run (default: none unless --all).
        Experiments that expose a ``--mode`` flag are pinned to ``smoke`` here;
        run the scripts directly with ``--mode full`` for full-scale reruns.
    --figures: Generate publication-quality figures
    --tests: Run the unit test suite via ``pytest tests/ -q`` (mirrors CI)
    --verify: Verify data integrity — every canonical CSV listed in
        release/release_manifest.json must exist with a matching SHA-256
        checksum and row count, followed by per-experiment structural checks
        (metadata, required columns, source-hash drift warnings)
"""

import sys
import os
import subprocess
import argparse
import time
import json
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))

# Experiment registry
# Entries with a ``--mode`` CLI flag are pinned explicitly to ``smoke`` so that
# ``--all`` stays a fast reproduction check and never silently escalates to a
# multi-hour full run if an experiment's default changes. Full-scale reruns
# remain available by invoking each experiment script directly (see
# release/release_manifest.json ``full_experiment_entrypoints``).
EXPERIMENTS = {
    "E1": {
        "script": "experiments/e01_phase_transition/run.py",
        "description": "Phase transition test (n=5, depth=1-50, 25,000 trials)",
        "estimated_time": "~30 minutes",
        "output": "data/v2_fixed/e01/"
    },
    "E2": {
        "script": "experiments/e02_entanglement_density/run.py",
        "description": "Entanglement density sweep (n=5, 2,100 trials)",
        "estimated_time": "~5 minutes",
        "output": "data/v2_fixed/e02/"
    },
    "E3": {
        "script": "experiments/e03_scaling/run.py",
        "description": "Scaling analysis (n=3-10, 12,000 trials)",
        "estimated_time": "~15 minutes",
        "output": "data/v2_fixed/e03/"
    },
    "E4": {
        "script": "experiments/e04_algorithm_comparison/run.py",
        "description": "Algorithm comparison (n=5, 400 trials, paired)",
        "estimated_time": "~2 hours (SA/GA are slow)",
        "output": "data/v2_fixed/e04/"
    },
    "E5": {
        "script": "experiments/e05_landscape/run.py",
        "description": "Landscape characterization (n=5, 6,000 trials)",
        "estimated_time": "~10 minutes",
        "output": "data/v2_fixed/e05/"
    },
    "E10": {
        "script": "experiments/e10_phase1_vs_phase2/run_expanded.py",
        "description": "Phase 1 vs Phase 2 (expanded, 1,905 rows)",
        "estimated_time": "~5 minutes",
        "output": "data/v5/e10/"
    },
    "E10p2b": {
        "script": "experiments/e10_phase1_vs_phase2/run_phase2b.py",
        "description": "Phase-2b template matching validation (Thm 7/9, review F1)",
        "estimated_time": "~2 minutes",
        "output": "data/v6/e10_phase2b/"
    },
    "E11": {
        "script": "experiments/e11_real_circuit_benchmark/run.py",
        "args": ["--mode", "smoke"],
        "description": "Real-circuit optimizer benchmark (pinned smoke mode)",
        "estimated_time": "~1 minute smoke / longer full",
        "output": "data/v4/e11/"
    },
    "E12": {
        "script": "experiments/e12_compiler_baseline/run.py",
        "args": ["--mode", "smoke"],
        "description": "Qiskit compiler baseline (pinned smoke mode, supports --no-coupling-map)",
        "estimated_time": "~1 minute smoke / longer full",
        "output": "data/v4/e12/"
    },
    "E13": {
        "script": "experiments/e13_structural_ceiling/run.py",
        "args": ["--mode", "smoke"],
        "description": "Structural ceiling/action-space analysis (pinned smoke mode)",
        "estimated_time": "~1 minute smoke / longer full",
        "output": "data/v4/e13/"
    },
    "E14": {
        "script": "experiments/e14_extended_benchmark/run.py",
        "args": ["--mode", "smoke"],
        "description": "Extended benchmark suite (v5, 15 families, pinned smoke mode)",
        "estimated_time": "~2 minutes smoke / ~30 minutes full",
        "output": "data/v5/e14/"
    },
    "E15": {
        "script": "experiments/e15_multi_compiler/run.py",
        "args": ["--mode", "smoke"],
        "description": "Multi-compiler baseline (Qiskit+Cirq+t|ket>, pinned smoke mode)",
        "estimated_time": "~2 minutes smoke / ~20 minutes full",
        "output": "data/v5/e15/"
    },
    "E16": {
        "script": "experiments/e16_window_scaling/run.py",
        "args": ["--mode", "smoke"],
        "description": "Window-size scaling study (pinned smoke mode)",
        "estimated_time": "~2 minutes smoke / ~20 minutes full",
        "output": "data/v5/e16/"
    },
    "E17": {
        "script": "experiments/e17_connectivity/run.py",
        "args": ["--mode", "smoke"],
        "description": "Hardware connectivity constraints (pinned smoke mode)",
        "estimated_time": "~2 minutes smoke / ~20 minutes full",
        "output": "data/v5/e17/"
    },
    "E18": {
        "script": "experiments/e18_clifford_t/run.py",
        "args": ["--mode", "smoke"],
        "description": "Clifford+T gate-set experiment (pinned smoke mode)",
        "estimated_time": "~1 minute smoke / ~15 minutes full",
        "output": "data/v5/e18/"
    },
    "E19": {
        "script": "experiments/e19_wcl_listing/run.py",
        "args": ["--mode", "smoke"],
        "description": "WCL vs LBL listing model comparison (review fix M10, pinned smoke mode)",
        "estimated_time": "~1 minute smoke / ~5 minutes full",
        "output": "data/v6/e19/"
    },
    "E20": {
        "script": "experiments/e20_multi_compiler_full/run.py",
        "args": ["--mode", "smoke"],
        "description": "Multi-compiler full comparison (Qiskit/Cirq/t|ket>, pinned smoke mode)",
        "estimated_time": "~1 minute smoke / ~5 minutes full",
        "output": "data/v6/e20/"
    },
    "E21": {
        "script": "experiments/e21_ceiling_aware/run.py",
        "args": ["--mode", "smoke"],
        "description": "Ceiling-aware optimizer (pinned smoke mode, review fix M10)",
        "estimated_time": "~1 minute smoke / ~10 minutes full",
        "output": "data/v6/e21/"
    },
    "E22": {
        "script": "experiments/gate_shuffle_ablation.py",
        "args": ["--mode", "smoke"],
        "description": "Gate-shuffle ablation (v7, pinned smoke mode)",
        "estimated_time": "~2 minutes smoke / longer full",
        "output": "data/v7/e22/"
    },
    "E23": {
        "script": "experiments/e23_ag_canonical/run.py",
        "description": "AG canonical form validation (Thm 6)",
        "estimated_time": "~1 minute",
        "output": "data/v7/e23/"
    },
    "E24": {
        "script": "experiments/e24_theorem7/run.py",
        "description": "Theorem 7 hardness family validation",
        "estimated_time": "~1 minute",
        "output": "data/v7/e24/"
    },
    "E25": {
        "script": "experiments/e25_industry_benchmarks/run.py",
        "description": "Industry benchmark proxy circuits",
        "estimated_time": "~1 minute",
        "output": "data/v6/e25/"
    },
    "E26": {
        "script": "experiments/phase2b_full_validation.py",
        "args": ["--mode", "smoke"],
        "description": "Theorem-9 BV theory-bounds validation (v7, pinned smoke mode)",
        "estimated_time": "~2 minutes smoke / longer full",
        "output": "data/v7/e26/"
    },
    "E29": {
        "script": "experiments/multi_seed_e04.py",
        "args": ["--mode", "smoke"],
        "description": "Multi-seed E04 robustness study (v7, pinned smoke mode)",
        "estimated_time": "~2 minutes smoke / ~1 hour full",
        "output": "data/v7/e29/"
    },
}


def run_command(cmd, description, cwd=None):
    """Run a command and report status."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(str(part) for part in cmd)}")
    print(f"{'='*60}")
    
    start = time.time()
    try:
        result = subprocess.run(
            cmd,
            shell=False,
            cwd=cwd or PROJECT_ROOT,
            capture_output=False,
            text=True,
            check=True
        )
        elapsed = time.time() - start
        print(f"\n✅ SUCCESS: {description} ({elapsed:.1f}s)")
        return True
    except subprocess.CalledProcessError as e:
        elapsed = time.time() - start
        print(f"\n❌ FAILED: {description} ({elapsed:.1f}s)")
        print(f"Error: {e}")
        return False


def run_tests():
    """Run the unit test suite through pytest, mirroring CI.

    Previously this invoked ``tests/test_core.py`` directly, but that file no
    longer exists in the repository, so ``--tests`` failed immediately. Running
    ``pytest tests/`` matches the CI workflow exactly.
    """
    cmd = [sys.executable, "-m", "pytest", "tests/", "-q"]
    return run_command(cmd, "Unit Tests (pytest tests/ -q)")


def run_experiment(exp_id):
    """Run a single experiment."""
    if exp_id not in EXPERIMENTS:
        print(f"❌ Unknown experiment: {exp_id}")
        print(f"Available: {', '.join(EXPERIMENTS.keys())}")
        return False

    exp = EXPERIMENTS[exp_id]
    script_path = PROJECT_ROOT / exp["script"]

    if not script_path.exists():
        print(f"❌ Script not found: {script_path}")
        return False

    cmd = [sys.executable, exp["script"], *exp.get("args", [])]
    return run_command(cmd, f"Experiment {exp_id}: {exp['description']}")


def generate_figures():
    """Generate publication-quality figures."""
    script_path = PROJECT_ROOT / "analysis" / "generate_figures.py"
    if not script_path.exists():
        print(f"❌ Figure generation script not found: {script_path}")
        return False
    
    cmd = [sys.executable, "analysis/generate_figures.py"]
    return run_command(cmd, "Figure Generation")


def verify_release_manifest():
    """Verify every canonical dataset against release/release_manifest.json.

    Each manifest dataset entry pins the file path, expected row count, and
    SHA-256 checksum. A missing file, unreadable CSV, row-count mismatch, or
    checksum mismatch fails verification. This is the authoritative integrity
    gate for the released canonical data.
    """
    import hashlib
    import pandas as pd

    print(f"\n{'='*60}")
    print("Verifying Canonical Datasets vs Release Manifest")
    print(f"{'='*60}")

    manifest_path = PROJECT_ROOT / "release" / "release_manifest.json"
    if not manifest_path.exists():
        print(f"❌ Release manifest not found: {manifest_path}")
        return False

    def sha256_of(path):
        h = hashlib.sha256()
        with open(path, "rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        return h.hexdigest()

    try:
        with open(manifest_path) as f:
            manifest = json.load(f)
    except Exception as e:
        print(f"❌ Release manifest is not valid JSON: {e}")
        return False

    datasets = manifest.get("datasets", [])
    if not datasets:
        print("❌ Release manifest contains no dataset entries")
        return False

    all_ok = True
    for ds in datasets:
        rel = ds.get("file")
        expected_sha = ds.get("sha256")
        expected_rows = ds.get("rows")
        label = f"{ds.get('experiment_id', '?'):>16} | {rel}"
        path = PROJECT_ROOT / rel if rel else None

        if path is None or not path.exists():
            print(f"❌ {label}: file missing")
            all_ok = False
            continue

        actual_sha = sha256_of(path)
        if actual_sha != expected_sha:
            print(f"❌ {label}: SHA-256 mismatch")
            print(f"   Expected: {expected_sha}")
            print(f"   Actual:   {actual_sha}")
            all_ok = False
            continue

        try:
            n_rows = len(pd.read_csv(path))
        except Exception as e:
            print(f"❌ {label}: unreadable CSV ({e})")
            all_ok = False
            continue

        if expected_rows is not None and n_rows != expected_rows:
            print(f"❌ {label}: row-count mismatch (expected {expected_rows}, got {n_rows})")
            all_ok = False
            continue

        print(f"✅ {label} | SHA-256 OK | Rows: {n_rows}")

    if all_ok:
        print(f"\n✅ All {len(datasets)} manifest dataset checksums verified")
    else:
        print(f"\n❌ Manifest dataset verification failed")

    return all_ok


def verify_data():
    """Verify data integrity.

    Two phases, both must pass:
    1. Authoritative check: every canonical CSV in release/release_manifest.json
       must exist with matching SHA-256 checksum and row count.
    2. Structural check: per-experiment metadata.json, required CSV columns,
       and (warning-only) source-hash drift since data generation.
    """
    manifest_ok = verify_release_manifest()

    print(f"\n{'='*60}")
    print("Verifying Per-Experiment Outputs (structural checks)")
    print(f"{'='*60}")

    all_ok = True
    for exp_id, exp in EXPERIMENTS.items():
        output_dir = PROJECT_ROOT / exp["output"]
        metadata_file = output_dir / "metadata.json"
        
        if not metadata_file.exists():
            print(f"❌ {exp_id}: metadata.json not found")
            all_ok = False
            continue
        
        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
            
            # Check for CSV files; prefer the canonical file declared by metadata.
            canonical = metadata.get("canonical_data_file")
            if canonical:
                csv_files = [output_dir / canonical]
            else:
                csv_files = list(output_dir.glob("*.csv"))
            if not csv_files or not all(path.exists() for path in csv_files):
                print(f"❌ {exp_id}: No CSV files found")
                all_ok = False
                continue
            
            # Basic CSV validation
            import pandas as pd
            for csv_file in csv_files:
                df = pd.read_csv(csv_file)
                if exp_id == "E13":
                    required_cols = ['experiment_id', 'n_qubits', 'depth', 'structural_upper_bound_reduction', 'observed_best_reduction']
                elif exp_id == "E15":
                    required_cols = ['n_qubits', 'reduction', 'fidelity']
                elif exp_id == "E16":
                    required_cols = ['n_qubits', 'reduction', 'fidelity']
                elif exp_id == "E17":
                    required_cols = ['n_qubits', 'reduction', 'fidelity']
                elif exp_id == "E18":
                    required_cols = ['n_qubits', 'reduction', 'fidelity']
                elif exp_id == "E19":
                    # WCL vs LBL listing model — schema v2 with listing_model column
                    required_cols = ['n_qubits', 'reduction']
                elif exp_id == "E20":
                    # Multi-compiler comparison — uses gate_reduction not reduction
                    required_cols = ['n_qubits', 'gate_reduction', 'fidelity']
                elif exp_id == "E21":
                    # Ceiling-aware optimizer summary — may have different schema
                    required_cols = []  # accept any columns
                elif exp_id == "E22":
                    # Gate-shuffle ablation — per-trial results schema
                    required_cols = ['n_qubits', 'reduction', 'fidelity']
                elif exp_id == "E23":
                    required_cols = ['n_qubits', 'reduction', 'fidelity']
                elif exp_id == "E24":
                    if 'summary' in csv_file.name.lower():
                        required_cols = ['n_qubits', 'optimizer', 'mean_reduction']
                    else:
                        required_cols = ['n_qubits', 'reduction', 'fidelity']
                elif exp_id == "E10p2b":
                    # Phase-2b validation — has optimizer + reduction columns
                    required_cols = ['optimizer', 'reduction']
                elif exp_id == "E26":
                    # Theorem-9 theory-bounds table — non-standard schema
                    required_cols = []  # accept any columns
                else:
                    required_cols = ['n_qubits', 'depth', 'reduction', 'fidelity']
                    if 'experiment' not in df.columns and 'experiment_id' not in df.columns:
                        required_cols.append('experiment')
                missing = [c for c in required_cols if c not in df.columns]
                if missing:
                    print(f"❌ {exp_id}: {csv_file.name} missing columns: {missing}")
                    all_ok = False
                else:
                    row_id_col = 'trial' if 'trial' in df.columns else 'sample' if 'sample' in df.columns else None
                    row_id_note = f" | Row id: {row_id_col}" if row_id_col else ""
                    if 'fidelity' in df.columns:
                        quality_note = f" | Mean fidelity: {df['fidelity'].dropna().mean():.6f}"
                    elif 'structural_upper_bound_reduction' in df.columns:
                        quality_note = f" | Mean ceiling: {df['structural_upper_bound_reduction'].mean():.6f}"
                    else:
                        quality_note = ""
                    print(f"✅ {exp_id}: {csv_file.name} | Records: {len(df)}{quality_note}{row_id_note}")
            
            # SHA256 source hash verification
            source_hashes = metadata.get("source_hashes", {})
            if source_hashes:
                from src.provenance import file_sha256
                stale_count = 0
                for rel_path, expected_hash in source_hashes.items():
                    abs_path = PROJECT_ROOT / rel_path
                    if abs_path.exists():
                        actual_hash = file_sha256(abs_path)
                        if actual_hash != expected_hash:
                            print(f"⚠️  {exp_id}: Source file modified since run: {rel_path}")
                            print(f"   Expected: {expected_hash[:16]}...")
                            print(f"   Actual:   {actual_hash[:16]}...")
                            stale_count += 1
                if stale_count > 0:
                    print(f"⚠️  {exp_id}: {stale_count} source file(s) modified since data generation")
                else:
                    print(f"✅ {exp_id}: All source hashes verified")
            else:
                print(f"ℹ️  {exp_id}: No source hashes in metadata (pre-provenance format)")
        
        except Exception as e:
            print(f"❌ {exp_id}: Verification error: {e}")
            all_ok = False
    
    if all_ok:
        print(f"\n✅ All per-experiment structural checks passed")
    else:
        print(f"\n❌ Some per-experiment structural checks failed")

    combined = manifest_ok and all_ok
    if combined:
        print(f"\n✅ All data integrity checks passed (manifest + structural)")
    else:
        print(f"\n❌ Data integrity verification failed")

    return combined


def main():
    parser = argparse.ArgumentParser(
        description="One-command reproduction for Q-Research project"
    )
    parser.add_argument(
        "--experiments",
        nargs="+",
        choices=list(EXPERIMENTS.keys()) + ["ALL"],
        default=None,
        help="Experiments to run (default: none unless --all)"
    )
    parser.add_argument(
        "--figures",
        action="store_true",
        help="Generate figures"
    )
    parser.add_argument(
        "--tests",
        action="store_true",
        help="Run unit tests"
    )
    parser.add_argument(
        "--verify",
        action="store_true",
        help="Verify data integrity"
    )
    parser.add_argument(
        "--smoke",
        action="store_true",
        help="Run tests and data verification only"
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Run everything (tests, all experiments, figures, verify)"
    )
    
    args = parser.parse_args()
    
    if args.all:
        args.tests = True
        args.experiments = ["ALL"]
        args.figures = True
        args.verify = True

    if args.smoke:
        args.tests = True
        args.verify = True
        if args.experiments is None:
            args.experiments = []
    
    # If no flags specified, show help
    if not any([args.tests, args.experiments, args.figures, args.verify, args.smoke]):
        parser.print_help()
        return
    
    # --verify alone should NOT trigger experiments
    if args.verify and args.experiments is None and not args.all:
        args.experiments = []
    
    print(f"{'='*60}")
    print("Q-Research Project: Full Reproduction Pipeline")
    print(f"{'='*60}")
    print(f"Project root: {PROJECT_ROOT}")
    print(f"Python: {sys.executable}")
    print(f"Start time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run tests
    if args.tests:
        results["tests"] = run_tests()
    
    # Run experiments
    if args.experiments:
        exp_list = list(EXPERIMENTS.keys()) if "ALL" in args.experiments else args.experiments
        for exp_id in exp_list:
            results[exp_id] = run_experiment(exp_id)
    
    # Generate figures
    if args.figures:
        results["figures"] = generate_figures()
    
    # Verify data
    if args.verify:
        results["verify"] = verify_data()
    
    # Summary
    print(f"\n{'='*60}")
    print("REPRODUCTION SUMMARY")
    print(f"{'='*60}")
    for task, success in results.items():
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"  {status}: {task}")
    
    all_passed = all(results.values())
    if all_passed:
        print(f"\n🎉 ALL TASKS PASSED — Reproduction successful!")
    else:
        print(f"\n⚠️  SOME TASKS FAILED — Check logs above")
    
    print(f"End time: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    if not all_passed:
        sys.exit(1)


if __name__ == "__main__":
    main()
