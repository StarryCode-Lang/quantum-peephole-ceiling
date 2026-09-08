"""Regression checks for the v14 IDA* escape-depth package."""

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SMOKE = ROOT / "data" / "v14" / "e45_idastar_escape_smoke"


def test_idastar_escape_smoke_package_verifies():
    completed = subprocess.run(
        [sys.executable, "scripts/verify_v14_idastar_escape.py", "--output-root", str(SMOKE)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert json.loads(completed.stdout.strip().splitlines()[-1])["status"] == "PASS"
