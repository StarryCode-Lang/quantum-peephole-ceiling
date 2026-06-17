"""Circuit generation package for quantum peephole optimization research."""

from .generator_v2 import (
    CircuitFamily,
    StructureType,
    CircuitConfig,
    CircuitMetrics,
    BaseCircuitGenerator,
    create_generator,
    generate_circuit,
    generate_circuit_batch,
    MetricsCalculator,
)
from .real_benchmarks import (
    BenchmarkCircuit,
    circuit_sha256,
    gate_counts,
    average_gate_fidelity,
    materialize_circuit,
    generate_extended_suite,
    generate_real_circuit_suite,
)

__all__ = [
    # generator_v2
    "CircuitFamily",
    "StructureType",
    "CircuitConfig",
    "CircuitMetrics",
    "BaseCircuitGenerator",
    "create_generator",
    "generate_circuit",
    "generate_circuit_batch",
    "MetricsCalculator",
    # real_benchmarks
    "BenchmarkCircuit",
    "circuit_sha256",
    "gate_counts",
    "average_gate_fidelity",
    "materialize_circuit",
    "generate_extended_suite",
    "generate_real_circuit_suite",
]
