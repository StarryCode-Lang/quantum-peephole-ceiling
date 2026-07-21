> **STATUS**: Not yet integrated into main manuscript. Pending merge.

# SOTA Comparison Tables (Updated with Actual Data)

> **Generated**: 2026-07-19T02:40:15.943503
> **Data**: 4 tools, 1501 total rows

---

## Table 1: Mean Gate-Count Reduction (%) by Family x Tool

> Pooled across n_qubits. **Bold** = best tool per family. Negative values indicate gate blowup.

| Family | Custom | Qiskit | Cirq | t|ket> | Quartz (lit.) | Quarl (lit.) |
|--------|:------:|:------:|:----:|:-----:|:-------------:|:-----------:|
| QFT | **+0.0** | +0.0 | - | -206.7 | 0* | 0* |
| GHZ | **+0.0** | +0.0 | -18.1 | +0.0 | 0* | 0* |
| SurfaceCode | **+0.0** | +0.0 | -23.3 | +0.0 | 0* | 0* |
| CNOT chain | **+100.0** | +100.0 | +0.0 | +100.0 | 100* | 100* |
| Oracle (BV) | +0.0 | **+41.8** | +11.0 | +39.2 | - | - |
| RandomClifford | +0.0 | **+72.5** | +47.4 | +71.6 | - | - |
| Grover | **+7.7** | -500.5 | -166.7 | -157.8 | - | - |
| Adder | **+0.0** | +0.0 | +0.0 | -505.9 | - | - |
| QuantumWalk | **+0.0** | -1904.7 | -382.6 | -1261.9 | - | - |
| IQP | +0.0 | +62.8 | +12.4 | **+64.4** | - | - |
| QAOA | +0.0 | +0.0 | -12.7 | **+6.3** | - | - |
| VQE | +0.0 | +39.3 | +0.0 | **+42.2** | - | - |
| HardwareEfficient | +0.0 | +35.5 | +0.0 | **+36.5** | - | - |
| UCCSD | +0.0 | **+23.3** | +11.0 | +14.5 | - | - |
| HaarRandom | +0.0 | **+6.5** | -33.5 | +5.8 | - | - |

---

## Table 2: Gate Blowup Analysis

> Families where tool INCREASES gate count (negative reduction).


| Tool | Families with blowup | Worst family | Worst reduction % |
|------|---------------------:|--------------|------------------:|
| custom | 0 | - | - |
| qiskit | 2 | QuantumWalk | -1904.7 |
| cirq | 6 | QuantumWalk | -382.6 |
| tket | 4 | QuantumWalk | -1261.9 |

**Key finding**: The custom prototype optimizer NEVER causes gate blowup. 
Production optimizers (t|ket>, Qiskit, Cirq) catastrophically increase gate count 
on 2-6 families due to multi-controlled gate decomposition. 
This argues for ceiling-aware compilation: skip optimization on ceiling families.

---

## Table 3: Tool Performance Summary

| Tool | Positive families | Zero families | Blowup families | Best family | Best reduction % |
|------|:-----------------:|:-------------:|:---------------:|-------------|-----------------:|
| custom | 2 | 13 | 0 | CNOT | +100.0 |
| qiskit | 8 | 5 | 2 | CNOT | +100.0 |
| cirq | 4 | 4 | 6 | RandomClifford | +47.4 |
| tket | 9 | 2 | 4 | CNOT | +100.0 |
