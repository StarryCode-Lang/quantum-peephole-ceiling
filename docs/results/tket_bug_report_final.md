# Bug Report: `tk_to_qiskit` silently drops implicit qubit permutations — returned circuit is unitarily inequivalent (warning-only)

> **Status**: Draft final (wave-5). Not yet submitted. Owner to review and post to
> [CQCL/tket](https://github.com/CQCL/tket) or
> [CQCL/pytket-qiskit](https://github.com/CQCL/pytket-qiskit).
>
> **Reproduction verified**: 2026-07-21, pytket 2.18.0, pytket-qiskit 0.77.0,
> qiskit 2.4.1, Python 3.12, Windows 11. Script:
> `experiments/reproduce_tket_clifford_unitarity.py` (3/3 recorded failures
> reproduced, 3/3 controls pass).

---

## Title

`tk_to_qiskit` silently drops implicit qubit permutations: returned circuit is unitarily inequivalent to the input (warning-only)

## Environment

| Package | Version |
|---|---|
| pytket | 2.18.0 |
| pytket-qiskit | 0.77.0 |
| qiskit | 2.4.1 |
| Python | 3.12 |
| OS | Windows 11 (platform-independent expected) |

## Summary

When a pytket circuit carries an implicit qubit permutation (produced e.g. by
`FullPeepholeOptimise` with its default `allow_swaps=True`),
`pytket.extensions.qiskit.tk_to_qiskit` returns a qiskit `QuantumCircuit` that
implements **U·P** (P = the implicit permutation) rather than **U**. The only
signal is a `UserWarning`, which is invisible in non-interactive pipelines
(unless explicitly captured). For a single transposition the mismatch is large:
`|Tr(U†U_out)| = d/2`, i.e. average gate fidelity
`F_avg = (d/4 + 1)/(d + 1) ≈ 0.27–0.33` for `d = 8–32`.

This is a **default-safety** issue: pytket documents implicit swaps and offers
both `Circuit.replace_implicit_wire_swaps()` and the `replace_implicit_swaps`
conversion flag, but the entirely default path
`qiskit_to_tk → FullPeepholeOptimise() → tk_to_qiskit` returns a silently
wrong circuit.

## Minimal reproducer

```python
import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator
from pytket.extensions.qiskit import qiskit_to_tk, tk_to_qiskit
from pytket.passes import FullPeepholeOptimise

rng = np.random.RandomState(4847)
qc = QuantumCircuit(5)
for _ in range(10):
    for q in range(5):
        g = rng.choice(["h", "s", "id"])
        if g == "h": qc.h(q)
        elif g == "s": qc.s(q)
    if rng.random() < 0.5:
        c = rng.randint(0, 4); qc.cx(c, c + 1)

tk = qiskit_to_tk(qc)
FullPeepholeOptimise().apply(tk)          # default allow_swaps=True
print(tk.implicit_qubit_permutation())    # e.g. {q[2]: q[3], q[3]: q[2], ...}
out = tk_to_qiskit(tk)                    # only a UserWarning
U, Uo = Operator(qc).data, Operator(out).data
tr = abs(np.trace(U.conj().T @ Uo))       # 16.0 == d/2  (expected 32.0)
print(f"|Tr| = {tr:.1f}, expected {2**5:.1f}, d/2 = {2**4:.1f}")

# Fix 1: materialize implicit swaps before conversion
tk2 = qiskit_to_tk(qc)
FullPeepholeOptimise().apply(tk2)
tk2.replace_implicit_wire_swaps()
out2 = tk_to_qiskit(tk2)
assert np.allclose(Operator(qc).data, Operator(out2).data, atol=1e-8)  # passes

# Fix 2: disable allow_swaps in the optimiser
tk3 = qiskit_to_tk(qc)
FullPeepholeOptimise(allow_swaps=False).apply(tk3)
out3 = tk_to_qiskit(tk3)
assert np.allclose(Operator(qc).data, Operator(out3).data, atol=1e-8)  # passes
```

## Expected behavior

`tk_to_qiskit` should default to `replace_implicit_swaps=True` (or raise when a
nontrivial implicit permutation is present). A warning-only path that returns a
unitarily inequivalent circuit is a correctness trap: every downstream consumer
that trusts the converted circuit (fidelity checks, simulators, hardware
submission) silently computes the wrong unitary.

## Actual behavior

Warning only; returned circuit differs from the input by a trailing qubit
permutation; measured average gate fidelity as low as **0.27** on n = 3–5
random Clifford circuits (3/3 seed-dependent failures reproduced in our
controlled sweep; 14/30 in the original 30-trial benchmark sweep).

### Reproduction sweep (2026-07-21)

```
pytket version: 2.18.0
Reproducing t|ket> FullPeepholeOptimise unitarity failures (RandomClifford family)

 n trial      gates      F_avg     |Tr|    d/2            verdict
-----------------------------------------------------------------
 3     2   30->10     0.333333   4.0000      4         REPRODUCED
 4     4   30->6      0.294118   8.0000     16         REPRODUCED
 5     4   40->10     0.272727  16.0000     16         REPRODUCED
 3     0   25->5      1.000000   8.0000      4       ok (control)
 4     0   28->11     1.000000  16.0000      8       ok (control)
 5     0   44->12     1.000000  32.0000     16       ok (control)

Reproduced 3/3 recorded failures with |Tr(U_in^d U_out)| = d/2 exactly
(F_avg = (d/4 + 1)/(d + 1)).
```

The theoretical fidelity for a single transposition is
`F_avg = (d/4 + 1)/(d + 1)`, which matches the observed values exactly:

| n | d = 2^n | d/2 | F_avg predicted | F_avg observed |
|---|---|---|---|---|
| 3 | 8 | 4 | (2+1)/9 = 0.3333 | 0.333333 |
| 4 | 16 | 8 | (4+1)/17 = 0.2941 | 0.294118 |
| 5 | 32 | 16 | (8+1)/33 = 0.2727 | 0.272727 |

## Root cause analysis

`FullPeepholeOptimise(allow_swaps=True)` (the default) may rewrite the circuit
so that logical qubit `q[i]` is physically realized on wire `q[σ(i)]`. This
implicit permutation `σ` is stored in the pytket `Circuit` object and accessible
via `c.implicit_qubit_permutation()`.

When `tk_to_qiskit` converts such a circuit, it maps pytket wires to qiskit
qubits positionally **without materializing** `σ`. The returned qiskit circuit
therefore implements `U · P_σ` (the unitary followed by the permutation) rather
than `U`. The conversion emits a `UserWarning` but does not raise.

For a single transposition `σ = (i, j)`, exactly `d/2` of the `d` basis states
are fixed by `σ`, so `|Tr(P_σ)| = d/2` and
`|Tr(U† · U · P_σ)| = |Tr(P_σ)| = d/2`, giving
`F_avg = (d/2 + 1) / (d + 1) = (d/4 + 1/2) / ((d+1)/2) ` — equivalently
`(d/4 + 1)/(d+1)` in the standard formula, matching the observed values.

## Fix / workaround

Two verified workarounds (both restore `F = 1.0`):

1. **`Circuit.replace_implicit_wire_swaps()`** — materializes the permutation as
   explicit SWAP gates before conversion. Verified 3/3 `F = 1.0`. May add 2–5
   gates.

2. **`FullPeepholeOptimise(allow_swaps=False)`** — prevents the optimiser from
   introducing implicit permutations. Verified 5/5 `F = 1.0` in the original
   sweep. May sacrifice 2–5 gates of optimization.

### Suggested upstream fix

Make `tk_to_qiskit` default to `replace_implicit_swaps=True`, or at minimum
raise `RuntimeError` (not `UserWarning`) when a nontrivial implicit permutation
is present. The current warning-only default is a silent correctness trap for
any pipeline that chains `qiskit_to_tk → FullPeepholeOptimise() → tk_to_qiskit`
without explicitly handling implicit permutations.

## Related upstream issues

A search of [CQCL/tket](https://github.com/CQCL/tket/issues?q=implicit+permutation+tk_to_qiskit)
(2026-07-21) found three closed issues about optimization passes and circuit
equivalence, none of which is an exact duplicate:

- **#1747** — "Optimisation Pass Failing to Preserve Circuit Equivalence"
  (closed Jan 2025) — general equivalence-preservation concern, not specific to
  `tk_to_qiskit` implicit permutations.
- **#1020** — "CliffordSimp produces circuit inequivalent to input"
  (closed Sep 2023) — different pass (`CliffordSimp`), not the
  `tk_to_qiskit` conversion default.
- **#1573** — serialization-related, not relevant.

No open or closed issue was found that specifically reports the
`tk_to_qiskit` default dropping implicit permutations. If this has been
reported elsewhere (e.g. in `CQCL/pytket-qiskit`), this report can serve as a
reproduction confirmation with additional root-cause detail.

## Impact on this project (Q-research)

In our SOTA compiler benchmark, 14/30 `RandomClifford` trials at n = 3–5
produced `F_avg < 0.34` via the default `qiskit_to_tk → FullPeepholeOptimise() →
tk_to_qiskit` path. All benchmark results in the manuscript use
`allow_swaps=False` (documented in `experiments/listing_sensitivity_check.py`
and `docs/results/sota_compiler_benchmark.md` §12), so **no published result is
affected**. The hazard is documented as a known limitation and dispositioned in
`docs/results/sota_compiler_benchmark.md` §12.2–12.4.
