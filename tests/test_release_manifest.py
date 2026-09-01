"""Release-level integrity checks for the active canonical evidence set."""

import hashlib
import json
from pathlib import Path

import pandas as pd

from scripts.generate_release_manifest import dataset_entries
from scripts.verify_prepaper_release_manifest import _verify_external_lineage


ROOT = Path(__file__).resolve().parents[1]


def test_manifest_and_listing_dataset_are_synchronized():
    manifest = json.loads((ROOT / "release" / "release_manifest.json").read_text(encoding="utf-8"))
    entry = next(item for item in manifest["datasets"] if item["experiment_id"] == "E_listing_sensitivity_v8")
    path = ROOT / entry["file"]

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    rows = len(pd.read_csv(path))
    metadata = json.loads((path.parent / "metadata.json").read_text(encoding="utf-8"))

    assert len(manifest["datasets"]) == 37
    assert sum(item["rows"] or 0 for item in manifest["datasets"]) == 96289
    active = [item for item in manifest["datasets"] if not item.get("superseded", False)]
    assert len(active) == 35
    assert sum(item["rows"] or 0 for item in active) == 96205
    assert digest == entry["sha256"]
    assert rows == entry["rows"] == metadata["n_rows"] == 6720


def test_historical_manifest_generator_excludes_prepaper_packet():
    entries = dataset_entries(ROOT / "data")
    assert entries
    assert all("/prepaper/" not in str(entry["file"]) for entry in entries)


def test_external_fidelity_lineage_is_cross_verified():
    # Source, raw/revalidated data, input manifests, segment ledgers and driver
    # hashes are all checked for both independently executed artifacts.
    assert _verify_external_lineage() == 15
