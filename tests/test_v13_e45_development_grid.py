from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_e45_configuration_grid_is_exactly_18():
    protocol_path = ROOT / "data" / "v13" / "e45_development_grid" / "protocol.json"
    assert protocol_path.exists()
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    configs = protocol["configuration_grid"]
    assert len(configs) == 18
    assert {(row["horizon"], row["beam_width"], row["state_budget"]) for row in configs} == {
        (h, b, s) for h in (2, 3, 4) for b in (16, 64) for s in (10_000, 50_000, 200_000)
    }


def test_e45_results_have_only_declared_arms():
    path = ROOT / "data" / "v13" / "e45_development_grid" / "grid_results.csv"
    assert path.exists()
    arms = {"greedy", "wcl_greedy", "v12_cgl_greedy", "phase2b_greedy", "unguided_beam", "certificate_guided_escape"}
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    assert rows
    assert {row["arm"] for row in rows} == arms


def test_e45_does_not_label_resource_bound_as_exact_local():
    path = ROOT / "data" / "v13" / "e45_development_grid" / "grid_results.csv"
    assert path.exists()
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row["status"] == "RESOURCE_BOUNDED_NO_WITNESS":
                assert row["certificate_status"] not in {"EXACT_H_LOCAL_OPTIMUM", "EXACT_ESCAPE"}
