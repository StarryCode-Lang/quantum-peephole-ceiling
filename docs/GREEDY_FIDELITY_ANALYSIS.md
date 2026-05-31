# Greedy Optimizer Fidelity Bug Analysis

**Date:** 2026-05-30  
**Experiment:** E6 — Qiskit Transpiler Baseline Comparison  
**Issue:** Greedy optimizer reports mean fidelity = 0.153 (should be ≈1.0)

---

## 1. Summary of Findings

The Greedy optimizer (`GreedyGateCancellation` in `src/optimisation/optimizers_v2.py`) contains a **critical correctness bug** in its `_are_inverse()` method that causes it to cancel gates acting on **different qubits**, thereby destroying the unitary equivalence of the optimized circuit. This results in a mean fidelity of 0.153 (vs. 1.0 for all Qiskit transpiler levels).

The bug also causes the optimizer to **always report fidelity = 1.0 internally** because it bypasses the fidelity check when called without a `target` argument.

---

## 2. Root Cause Analysis

### 2.1 Primary Bug: `_are_inverse()` Does Not Check Qubit Assignments

**Location:** `src/optimisation/optimizers_v2.py`, lines 485–511

The `GreedyGateCancellation._are_inverse()` method checks if two adjacent gate instructions are inverses of each other. For self-inverse gates (H, X, Y, Z, CX, CZ, SWAP), it compares only the **gate names**:

```python
def _are_inverse(self, inst1, inst2) -> bool:
    gate1 = inst1.operation.name
    gate2 = inst2.operation.name
    
    # Self-inverse gates — ONLY checks gate name, NOT qubits!
    if gate1 == gate2 and gate1 in ('h', 'x', 'y', 'z', 'cx', 'cz', 'swap'):
        return True
    # ...
```

**The method does NOT verify that both gates act on the same qubits.** Two H gates on different qubits (H(0) and H(1)) are incorrectly treated as self-canceling.

**Verified empirically:**

```python
qc = QuantumCircuit(2)
qc.h(0)  # H on qubit 0
qc.h(1)  # H on qubit 1
opt = GreedyGateCancellation()
opt._are_inverse(qc.data[0], qc.data[1])  # Returns True — WRONG!
```

Result: `True` — the method claims H(0) and H(1) are inverses, even though they act on different qubits and do NOT cancel.

### 2.2 Consequence: Random Gate Cancellation

When the `optimize()` method scans the linear instruction list:

```python
for iteration in range(self.max_iterations):
    i = 0
    while i < len(optimized.data) - 1:
        if self._are_inverse(optimized.data[i], optimized.data[i + 1]):
            optimized.data.pop(i)
            optimized.data.pop(i)  # Cancels BOTH gates
            improved = True
```

Any two adjacent instructions in the list that share the same gate name (among the self-inverse set) get cancelled, **regardless of which qubits they act on**. In multi-qubit circuits, this happens frequently because gates on different qubits are often adjacent in the linear instruction list.

**Example failure mode:**
```
Instruction list: [H(0), H(1), CX(0,1), H(0), CX(0,1), ...]
                    ↑____↑
                  Cancelled! But H(0) ≠ H(1)⁻¹ — they're on different qubits!
```

This produces a circuit that is **not unitary-equivalent** to the original, explaining the 0.153 mean fidelity.

### 2.3 Secondary Bug: Internal Fidelity Always Returns 1.0

**Location:** `src/optimisation/optimizers_v2.py`, line 470

```python
fidelity = 1.0 if target is None else self.calculate_fidelity(optimized, target)
```

In `run_e6.py`, the optimizer is called as:
```python
result = optimizer.optimize(circuit)  # No target argument → target=None
```

When `target=None`, fidelity is **hardcoded to 1.0**. The optimizer never verifies its own output. The E6 script independently computes fidelity using `Statevector.from_instruction()` (line 105), which correctly detects the unitary mismatch.

---

## 3. Comparison with `BaseOptimizer._is_self_inverse_pair()`

The base class (`BaseOptimizer`, line 231) has a **correct** implementation:

```python
def _is_self_inverse_pair(self, circuit, inst1, inst2) -> bool:
    name1 = inst1.operation.name
    name2 = inst2.operation.name
    qubits1 = self._get_qubit_indices(circuit, inst1)
    qubits2 = self._get_qubit_indices(circuit, inst2)
    
    # Must act on the same qubits
    if qubits1 != qubits2:
        return False
    # ...
```

This method correctly checks qubit indices. The `GreedyGateCancellation` class overrides this with its own `_are_inverse()` but **omits the qubit check**.

---

## 4. Why Qiskit Transpiler Levels Succeed

Qiskit's transpiler (L1–L3) uses industrial-grade optimization passes that:
1. Track qubit dependencies correctly
2. Use DAG-based circuit representations (not linear instruction lists)
3. Verify unitary equivalence after optimization

Results:
| Optimizer | Mean Reduction | Success Rate | Mean Fidelity |
|-----------|---------------|-------------|---------------|
| Qiskit L0 | 0.000 | 0.0% | 1.000 |
| Qiskit L1 | 0.425 | 98.9% | 1.000 |
| Qiskit L2 | 0.550 | 100.0% | 1.000 |
| Qiskit L3 | 0.550 | 100.0% | 1.000 |
| Greedy | 0.120 | 6.1% | **0.153** |

---

## 5. Fix Required

The `_are_inverse()` method in `GreedyGateCancellation` must check qubit indices before declaring two gates as inverses:

```python
def _are_inverse(self, inst1, inst2) -> bool:
    try:
        gate1 = inst1.operation.name
        gate2 = inst2.operation.name
        
        # FIX: Extract qubit indices and verify they match
        qubits1 = [q._index for q in inst1.qubits]
        qubits2 = [q._index for q in inst2.qubits]
        if qubits1 != qubits2:
            return False
        
        # Self-inverse gates (now correctly constrained to same qubits)
        if gate1 == gate2 and gate1 in ('h', 'x', 'y', 'z', 'cx', 'cz', 'swap'):
            return True
        # ... rest unchanged
```

Additionally, the `optimize()` method should verify fidelity against the original circuit rather than hardcoding 1.0 when `target=None`.

---

## 6. Impact Assessment

- **All previous experiments (E1–E5) using the Greedy optimizer are affected** by this bug.
- Reported fidelities in those experiments were 1.0 (hardcoded) rather than measured.
- The actual circuit equivalence was never verified — gate cancellations may have been incorrect.
- The 6.1% success rate in E6 is likely inflated: some circuits may achieve ≥20% reduction by chance (incorrect cancellations that happen to reduce gate count), even though the resulting circuit is functionally wrong.

---

## 7. Files Involved

| File | Line(s) | Issue |
|------|---------|-------|
| `src/optimisation/optimizers_v2.py` | 485–511 | `_are_inverse()` missing qubit check |
| `src/optimisation/optimizers_v2.py` | 470 | Fidelity hardcoded to 1.0 when `target=None` |
| `src/optimisation/optimizers_v2.py` | 513–544 | `_merge_rotations()` — also uses `q._index` directly, may need review |
| `experiments/run_e6.py` | 105 | Correctly catches bug via independent state fidelity check |

---

## 8. Conclusion

The Greedy optimizer's low fidelity (0.153) is caused by a **missing qubit-identity check** in the `_are_inverse()` method. This is a correctness bug, not a limitation of the greedy algorithm itself. Once fixed, the optimizer should achieve near-1.0 fidelity (matching Qiskit L0's behavior of "no incorrect cancellations").

The fix is a single guard clause (~3 lines) but requires re-running all experiments (E1–E6) to obtain correct fidelity measurements.
