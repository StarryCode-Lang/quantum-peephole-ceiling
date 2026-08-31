from experiments.e37_energy_cost_telemetry import ORDER, cny_cost


def test_cost_conversion_and_frozen_order() -> None:
    assert cny_cost(3_600_000.0, 0.6) == 0.6
    assert ORDER.count("idle_then_workload") == 3
    assert ORDER.count("workload_then_idle") == 2
