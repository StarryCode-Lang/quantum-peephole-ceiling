#!/usr/bin/env python3
"""Environment provenance snapshot for reproducibility."""
import sys, os, json, hashlib, platform, subprocess
from pathlib import Path
from datetime import datetime

def compute_file_hash(filepath: str) -> str:
    """SHA256 hash of a file."""
    sha256 = hashlib.sha256()
    with open(filepath, 'rb') as f:
        sha256.update(f.read())
    return sha256.hexdigest()

def get_package_versions():
    """Get versions of key packages."""
    packages = ['qiskit', 'numpy', 'scipy', 'pandas', 'matplotlib']
    versions = {}
    for pkg in packages:
        try:
            mod = __import__(pkg)
            versions[pkg] = getattr(mod, '__version__', 'unknown')
        except ImportError:
            versions[pkg] = 'not installed'
    return versions

def get_git_info():
    """Get current git commit hash if in a repo."""
    try:
        result = subprocess.run(['git', 'rev-parse', 'HEAD'], 
                              capture_output=True, text=True, timeout=5)
        return result.stdout.strip() if result.returncode == 0 else None
    except:
        return None

def snapshot_environment(project_root: str = 'D:/Desktop/Q-research'):
    root = Path(project_root)
    files_to_hash = [
        'src/circuits/generator_v2.py',
        'src/optimisation/optimizers_v2.py', 
        'src/analysis/analysis_v2.py',
        'experiments/run_all_experiments_v3.py',
    ]
    
    snapshot = {
        'timestamp': datetime.now().isoformat(),
        'python_version': sys.version,
        'packages': get_package_versions(),
        'git_commit': get_git_info(),
        'source_hashes': {f: compute_file_hash(root / f) for f in files_to_hash if (root / f).exists()},
        'system': {
            'platform': platform.platform(),
            'processor': platform.processor(),
            'cpu_count': os.cpu_count(),
        },
    }
    
    output_path = root / 'data' / 'processed' / 'environment_snapshot.json'
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(snapshot, f, indent=2)
    print(f"Environment snapshot saved to {output_path}")
    return snapshot

if __name__ == '__main__':
    snapshot_environment()
