"""Regression checks for the selected-configuration full exact package."""

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
FULL = ROOT / "data" / "v14" / "e45_full_development"


def test_exact_full_development_package_verifies_and_exposes_boundary():
    completed = subprocess.run(
        [sys.executable, "scripts/verify_e45_exact_development.py", "--output-root", str(FULL)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    result = json.loads(completed.stdout.strip().splitlines()[-1])
    assert result["status"] == "PASS"
    assert result["source_count"] == 128
    screening_selection = json.loads(
        (ROOT / "data/v14/e45_development_grid/selection.json").read_text(encoding="utf-8")
    )
    full_selection = json.loads((FULL / "selection.json").read_text(encoding="utf-8"))
    fields = ("config_id", "horizon", "beam_width", "state_budget", "barrier_cap")
    assert all(
        full_selection["selected_config"][key] == screening_selection["selected_config"][key]
        for key in fields
    )
    certificate_count = 0
    exact_count = 0
    truncated_count = 0
    with (FULL / "certificates.jsonl").open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            certificate = json.loads(line)["certificate"]
            certificate_count += 1
            exact_count += certificate["exactness_status"] == "EXACT_FINITE_HORIZON"
            truncated_count += certificate["resource_status"] == "TRUNCATED"
    assert certificate_count == 128
    assert exact_count + truncated_count == certificate_count
    assert exact_count > 0
