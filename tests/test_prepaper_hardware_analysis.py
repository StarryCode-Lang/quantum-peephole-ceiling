import pandas as pd
import pytest

from analysis.prepaper_hardware_validation import paired_analysis


def _row(version, seed, fidelity, output_hash):
    return {
        "circuit_id": "c1",
        "circuit_family": "fixture",
        "backend_name": "snapshot",
        "transpile_optimization_level": 0,
        "sampler": "aer_noisy_fakebackend",
        "seed_simulator": seed,
        "version": version,
        "output_sha256": output_hash,
        "logical_reduction": 0.0 if version == "original" else 0.25,
        "transpiled_2q_reduction": 0.0 if version == "original" else 0.5,
        "hellinger_fidelity": fidelity,
        "tvd": 1.0 - fidelity,
        "transpiled_2q_depth": 4 if version == "original" else 2,
        "scheduled_duration_seconds": 10.0 if version == "original" else 8.0,
        "calibration_success_probability": 0.8 if version == "original" else 0.9,
        "unitary_equivalence_method": "numerical_unitary",
        "unitary_equivalence_status": "verified_equivalent",
        "unitary_equivalence_is_verified": True,
    }


def test_paired_analysis_treats_seed_as_repeat_not_new_design_cell():
    frame = pd.DataFrame([
        _row("original", 1, 0.8, "in"),
        _row("original", 2, 0.82, "in"),
        _row("optimizer", 1, 0.9, "out"),
        _row("optimizer", 2, 0.92, "out"),
    ])

    cells, report = paired_analysis(frame)

    assert len(cells) == 1
    assert cells.iloc[0]["n_seed_repeats"] == 2
    assert cells.iloc[0]["hellinger_gain_mean"] == pytest.approx(0.1)
    assert report["n_eligible_design_cells"] == 1


def test_paired_analysis_fails_when_original_pair_is_missing():
    frame = pd.DataFrame([_row("optimizer", 1, 0.9, "out")])

    with pytest.raises(ValueError, match="no paired original"):
        paired_analysis(frame)


def test_paired_analysis_rejects_unverified_reduced_output():
    original = _row("original", 1, 0.8, "in")
    optimized = _row("optimizer", 1, 0.9, "out")
    optimized["unitary_equivalence_is_verified"] = False

    with pytest.raises(ValueError, match="lacks verified equivalence"):
        paired_analysis(pd.DataFrame([original, optimized]))
