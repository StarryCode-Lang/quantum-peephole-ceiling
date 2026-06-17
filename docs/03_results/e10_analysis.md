# E10: Phase 1 vs Phase 2 Optimization Comparison

## Executive Summary

### RANDOM Circuits

| Optimizer | Mean Reduction | Fidelity | N |
|-----------|---------------|----------|---|
| greedy_phase1 | 0.0000 | 1.000000 | 100 |
| commutation_phase2 | 0.0326 | 1.000000 | 100 |
| hybrid_phase1_2 | 0.0326 | 1.000000 | 100 |

**Cliff's delta (Greedy vs Hybrid)**: -0.840 [-1.000, -0.680]

### STRUCTURED Circuits

| Optimizer | Mean Reduction | Fidelity | N |
|-----------|---------------|----------|---|
| greedy_phase1 | 0.0000 | 1.000000 | 100 |
| commutation_phase2 | 0.0000 | 1.000000 | 100 |
| hybrid_phase1_2 | 0.0000 | 1.000000 | 100 |

**Cliff's delta (Greedy vs Hybrid)**: +0.000 [-0.160, 0.160]

> **Note**: The Real Circuits data below (QFT/GHZ/CNOT, N=9) is **historical / superseded** by E11 full results (see end of document).

### REAL Circuits (Historical — superseded by E11)

| Optimizer | Mean Reduction | Fidelity | N |
|-----------|---------------|----------|---|
| greedy_phase1 | 0.3333 | 1.000000 | 9 |
| commutation_phase2 | 0.0000 | 1.000000 | 9 |
| hybrid_phase1_2 | 0.3333 | 1.000000 | 9 |

**Cliff's delta (Greedy vs Hybrid)**: +0.000 [-0.548, 0.548]

## Key Findings

1. **Random circuits**: Phase 2 (commutation) provides ~3.3% additional reduction over Phase 1 (Greedy).
2. **Structured circuits**: No significant difference — all optimizers achieve ~0% reduction.
3. **Real circuits (historical)**: Greedy already achieves 33.3% reduction; Phase 2 does not provide additional benefit. *Superseded by E11 — see below.*

## Interpretation

The Phase 2 advantage is **context-dependent**:
- On random circuits, commutation rewriting can bring non-adjacent inverse gates together.
- On structured circuits (brickwork), the specific gate patterns may not have commutation opportunities.
- On real circuits (QFT/GHZ/CNOT), Greedy already finds all adjacent cancellations.

This suggests that **Phase 2 value depends on circuit structure** — not all circuits benefit.

---

## E11 Full Results (v4 — supersedes Real Circuits above)

E11 tested 37 real-circuit instances across 7 families (QFT, GHZ, CNOT chain, Oracle/Bernstein–Vazirani, QAOA, VQE Two-Local, Hardware Efficient) with $n=3\text{--}8$ qubits using v4 optimizers.

### E11 Summary Table

| Circuit Family | Phase 1 (Greedy) | Phase 2 (Hybrid) | Notes |
|---------------|------------------|------------------|-------|
| QFT | 0% | 0% | Already optimal |
| GHZ | 0% | 0% | Already optimal |
| CNOT chain | 100% | 100% | Greedy cancels all adjacent pairs; Phase 2 adds nothing |
| Oracle (BV) | 0% | ~20% (16–50%) | Commutation exposes redundant H/X gates |
| QAOA | 0% | 0% | No commutation opportunities found |
| VQE (Two-Local) | 0% | 0% | No commutation opportunities found |
| Hardware Efficient | 0% | 0% | No commutation opportunities found |

### E11 Interpretation

- **Already-optimal circuits** (QFT, GHZ, QAOA, VQE, Hardware Efficient) show 0% reduction across all optimizers, confirming they are structurally minimal under the tested gate sets.
- **Oracle (BV)** is the only real-circuit family where Phase 2 provides significant benefit (~20% mean, up to 50% for larger $n$). The benefit comes from commuting Hadamard and X gates that encode the oracle string.
- **CNOT chain** achieves 100% reduction via Phase 1 alone; Phase 2 adds no value because all inverse pairs are already adjacent.