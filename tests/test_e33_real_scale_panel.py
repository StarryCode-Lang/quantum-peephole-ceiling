from experiments.e33_real_scale_panel import run_id


def test_run_id_is_deterministic_and_listing_sensitive() -> None:
    assert run_id("a" * 64, "LBL") == run_id("a" * 64, "LBL")
    assert run_id("a" * 64, "LBL") != run_id("a" * 64, "WCL")
