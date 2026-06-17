"""Module-level constants for the optimisation package."""

# Default numerical precision threshold used throughout the package for
# floating-point comparisons (e.g., checking if two rotation angles cancel).
DEFAULT_PRECISION: float = 1e-10

# Maximum number of qubits for exact Operator-based fidelity calculation.
# Beyond this, constructing the full (2^n x 2^n) unitary matrix becomes
# prohibitively expensive in memory.
MAX_EXACT_FIDELITY_QUBITS: int = 12

# Default number of gate samples used when estimating fidelity for
# circuits with more than MAX_EXACT_FIDELITY_QUBITS qubits.
DEFAULT_FIDELITY_SAMPLES: int = 100
