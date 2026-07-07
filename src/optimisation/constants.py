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
#
# NOTE (review H4): Previous documentation referenced n_samples=1000
# giving ~3% uncertainty, while the actual constant was 100 giving
# ~10% uncertainty.  The constant has been raised to 1000 so that the
# ~1/sqrt(n_samples) standard error (~3% at 1000 samples) matches the
# documented guarantee.  If runtime becomes a concern for very large
# circuits, callers may override ``n_samples`` explicitly, but the
# default now reflects the published precision claim.
DEFAULT_FIDELITY_SAMPLES: int = 1000

