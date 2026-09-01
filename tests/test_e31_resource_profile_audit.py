import json

from analysis.e31_resource_profile_audit import DEFAULT_OUTPUT_DIR


def test_generated_resource_profile_is_complete_and_bounded():
    audit = json.loads(
        (DEFAULT_OUTPUT_DIR / "resource_profile_audit.json").read_text(
            encoding="utf-8"
        )
    )
    assert audit["status"] == "PASS_BOUNDED_E31_RESOURCE_PROFILE"
    assert audit["main_panel"]["families"] == 15
    assert audit["main_panel"]["qubit_range"] == [4, 10]
    assert audit["main_panel"]["all_semantically_valid"] is True
    assert audit["memory_scaling"]["n_scale_points"] == 7
    assert audit["worker_sensitivity"]["worker_counts"] == [1, 2, 4]
    assert audit["worker_sensitivity"]["deterministic_output_hashes_across_conditions"] is True
    assert audit["cache_sensitivity"]["repetitions_same_process"] == 5
    assert audit["cache_sensitivity"]["output_hash_stable"] is True
