"""Integrity tests for the outcome-blind heldout-v2 sealing stage."""

import json

import numpy as np
import pandas as pd

from experiments.heldout_v2_seal import GENERATORS, _fixed_model_predictions, verify_seal


def test_heldout_v2_declares_eight_unique_mechanisms():
    protocol = json.loads(open("experiments/heldout_v2_protocol.json", encoding="utf-8").read())
    assert len(GENERATORS) == 8
    assert set(protocol["families"]) == set(GENERATORS)
    mechanisms = [entry["mechanism_id"] for entry in protocol["families"].values()]
    assert len(mechanisms) == len(set(mechanisms)) == 8


def test_fixed_model_replay_matches_direct_logistic_formula():
    model = json.loads(open(
        "data/v10/prepaper/heldout/sealed_predictions/model.json", encoding="utf-8"
    ).read())
    row = {feature: value for feature, value in zip(model["features"], model["scaler_mean"])}
    frame = pd.DataFrame([row])
    probability, prediction = _fixed_model_predictions(frame, model)
    expected = 1.0 / (1.0 + np.exp(-float(model["intercept"][0])))
    assert probability[0] == expected
    assert prediction[0] == int(expected >= model["threshold"])


def test_protocol_forbids_refit_and_requires_unique_hashes():
    protocol = json.loads(open("experiments/heldout_v2_protocol.json", encoding="utf-8").read())
    assert protocol["fixed_model"]["refit_allowed"] is False
    assert protocol["fixed_model"]["feature_change_allowed"] is False
    assert protocol["required_global_unique_input_hashes"] is True
    assert protocol["required_zero_hash_overlap_with_training_and_v1"] is True


def test_materialized_input_packet_hashes_verify_at_current_stage():
    # ``verify_seal`` is deliberately pre-outcome-only and must refuse after
    # the formal results directory exists.  The execution-stage verifier keeps
    # all immutable hash/cardinality checks without pretending the experiment
    # is still outcome blind.
    from experiments.heldout_v2_execute import _verify_immutable_packet

    seal, protocol = _verify_immutable_packet()
    assert seal["status"] == "SEALED_BEFORE_HELDOUT_V2_OPTIMIZATION"
    assert seal["n_families"] == 8
    assert seal["n_rows"] == protocol["expected_rows_per_tool"] == 192
    assert seal["n_unique_inputs"] == protocol["required_unique_input_hashes"] == 192
