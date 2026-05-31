#!/usr/bin/env python3
"""
Setup reproducibility environment for Q-research project.

This script:
1. Verifies Python version
2. Checks/installs dependencies
3. Creates necessary directories
4. Generates a reproducibility manifest
"""

import sys
import os
import json
import platform
import subprocess
from pathlib import Path
from datetime import datetime


def check_python_version():
    """Check Python version >= 3.11."""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 11):
        print(f"ERROR: Python {version.major}.{version.minor} detected. Python 3.11+ required.")
        return False
    print(f"OK: Python {version.major}.{version.minor}.{version.micro}")
    return True


def install_dependencies():
    """Install dependencies from requirements.txt."""
    req_file = Path(__file__).parent / "requirements.txt"
    if not req_file.exists():
        print("WARNING: requirements.txt not found")
        return False
    
    print("Installing dependencies...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-r", str(req_file)],
        capture_output=True,
        text=True
    )
    if result.returncode == 0:
        print("OK: Dependencies installed")
        return True
    else:
        print(f"ERROR: Failed to install dependencies:\n{result.stderr}")
        return False


def create_directories():
    """Create necessary directories."""
    base = Path("D:/Desktop/Q-research")
    dirs = [
        "data/raw",
        "data/processed",
        "figures/final",
        "logs",
        "docs/reports",
        "docs/review",
    ]
    for d in dirs:
        (base / d).mkdir(parents=True, exist_ok=True)
    print("OK: Directories created")


def generate_manifest():
    """Generate reproducibility manifest."""
    manifest = {
        "project": "Q-research",
        "version": "2.1.0",
        "date": datetime.now().isoformat(),
        "environment": {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "platform": platform.platform(),
            "processor": platform.processor(),
        },
        "dependencies": {},
        "directories": {
            "data_raw": "data/raw",
            "data_processed": "data/processed",
            "figures": "figures/final",
            "logs": "logs",
        },
        "experiments": [
            "exp1_phase_transition",
            "exp2_entanglement_density",
            "exp3_scaling",
            "exp4_algorithm_comparison",
            "exp5_landscape",
        ],
    }
    
    # Get installed package versions
    try:
        import numpy, pandas, scipy, qiskit, matplotlib, seaborn
        manifest["dependencies"] = {
            "numpy": numpy.__version__,
            "pandas": pandas.__version__,
            "scipy": scipy.__version__,
            "qiskit": qiskit.__version__,
            "matplotlib": matplotlib.__version__,
            "seaborn": seaborn.__version__,
        }
    except ImportError as e:
        print(f"WARNING: Could not get package versions: {e}")
    
    manifest_path = Path("D:/Desktop/Q-research") / "REPRODUCIBILITY_MANIFEST.json"
    manifest_path.write_text(json.dumps(manifest, indent=2))
    print(f"OK: Manifest saved to {manifest_path}")


def main():
    """Main setup function."""
    print("=" * 60)
    print("Q-Research Reproducibility Setup")
    print("=" * 60)
    
    success = True
    success &= check_python_version()
    success &= install_dependencies()
    create_directories()
    generate_manifest()
    
    print("=" * 60)
    if success:
        print("Setup complete! Run experiments with:")
        print("  python experiments/run_all_experiments_v3.py")
    else:
        print("Setup completed with warnings. Please review output above.")
    print("=" * 60)


if __name__ == "__main__":
    main()
