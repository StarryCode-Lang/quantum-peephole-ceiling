"""Release-level integrity checks for the active canonical evidence set."""

import hashlib
import json
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]


def test_manifest_and_listing_dataset_are_synchronized():
    manifest = json.loads((ROOT / "release" / "release_manifest.json").read_text(encoding="utf-8"))
    entry = next(item for item in manifest["datasets"] if item["experiment_id"] == "E_listing_sensitivity_v8")
    path = ROOT / entry["file"]

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = len(pd.read_csv(path))
    metadata = json.loads((path.parent / "metadata.json").read_text(encoding="utf-8"))

    assert len(manifest["datasets"]) == 36
    assert sum(item["rows"] or 0 for item in manifest["datasets"]) == 82789
    assert digest == entry["sha256"]
    assert rows == entry["rows"] == metadata["n_rows"] == 6720
