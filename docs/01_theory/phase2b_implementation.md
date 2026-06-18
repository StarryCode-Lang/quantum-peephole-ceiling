# Phase 2b Template Matcher Implementation

## Implemented scope

`Phase2bTemplateMatcher` implements a deterministic, local Clifford template pass:

\[
H(c)\;\mathrm{CNOT}(c,t)\;H(c) \rightarrow H(t)\;\mathrm{CNOT}(t,c)\;H(t).
\]

The pass also performs safe adjacent Hadamard-pair cleanup:

\[
H(q)\;H(q) \rightarrow I.
\]

Both transformations are unitary-preserving and act only on explicit adjacent instruction windows in the circuit list. The implementation is intentionally conservative: it does not reorder unrelated gates, infer non-adjacent matches, or introduce identities.

## Test coverage

The focused unittest suite covers:

- the basic three-gate template shape and qubit reversal;
- unitary preservation against Qiskit's exact `Operator` for small circuits;
- adjacent `H-H` cleanup exposed by the template rewrite;
- BV-like template pipelines for `n = 2, 3, 5`, where each data qubit contributes one matched template and one adjacent `H-H` cancellation.

For the implemented BV-like fixture, the input size is `5n` and the optimized size is `n + 2`, because the local template exposes both in-block and cross-block adjacent `H-H` pairs on the shared ancilla. This preserves the exact unitary.

## Remaining gap

This is not a complete Phase-2 optimizer. It does not yet implement:

- non-adjacent template matching through commutation-aware movement;
- multi-template search or cost-guided template selection;
- insertion-based cascades;
- full Clifford tableau/canonical-form synthesis;
- topology-aware template variants;
- measurement/classical-bit-preserving circuit rewrites.

The current module should therefore be interpreted as a minimal Phase-2b template-matching prototype rather than a complete compiler pass.
