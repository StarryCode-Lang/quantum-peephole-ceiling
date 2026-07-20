## Industrial Baseline Comparison: Custom Peephole vs Production Compilers

Table 13: Per-family comparison of custom prototype optimizers against Qiskit and t|ket> production compilers. Reduction is gate-count reduction (positive = fewer gates, negative = inflation from basis translation).

| Family | Prototype (Hybrid) | Qiskit O3 | t|ket> FullPeephole | Cirq | Ceiling Class |
|--------|-------------------|-----------|---------------------|------|---------------|
| CNOT | 66.7% | 75.0% | 1.0% | 0.0% | Not ceiling |
| Oracle (BV) | 10.0% | 30.1% | 36.6% | 0.4% | Not ceiling |
| RandomClifford | 10.8% | 55.0% | 72.8% | 44.6% | Not ceiling |
| Adder | 0.0% | 0.0% | -5.4% | 0.0% | Genuine ceiling |
| **QFT** | **0.0%** | **0.0%** | **0.0%** | N/A | **Genuine ceiling** |
| **GHZ** | **0.0%** | **0.0%** | **0.0%** | -18.1% | **Genuine ceiling** |
| **SurfaceCode** | **0.0%** | **0.0%** | **0.0%** | -25.4% | **Genuine ceiling** |
| VQE | 0.0% | 39.3% | 39.6% | 0.0% | Prototype-limited |
| HardwareEfficient | 0.0% | 35.5% | 35.8% | 0.0% | Prototype-limited |
| IQP | 0.3% | 60.0% | 63.4% | 12.7% | Prototype-limited |
| UCCSD | 0.3% | 23.3% | 22.5% | 10.8% | Prototype-limited |
| QAOA | 0.0% | 0.0% | 5.4% | -12.7% | Prototype-limited (weak) |
| Grover | 4.1% | -881.8% | -437.5% | -167.4% | Unclear |
| QuantumWalk | 0.0% | -2526% | -1083% | N/A | Unclear |
| HaarRandom | 0.0% | 6.5% | 6.5% | -33.5% | Not ceiling |

### Key Findings

**1. Genuine structural ceilings (3 families):** QFT, GHZ, and SurfaceCode show 0% reduction across ALL compilers, including production peephole optimizers. These circuits are genuinely gate-count-optimal under standard decomposition.

**2. Prototype-limited ceilings (5 families):** VQE, HardwareEfficient, IQP, UCCSD, and QAOA show 0% with the prototype but 5-63% with t|ket>'s FullPeepholeOptimise. The previous aggregate-mean table (showing Qiskit at -175% to -247%) was misleading because it mixed basis-translation inflation (QuantumWalk, Grover) with genuine optimization (VQE 35%, IQP 60%). The per-family view reveals that production peephole optimizers CAN optimize these families.

**3. t|ket>'s FullPeepholeOptimise is a peephole optimizer.** Despite the prototype's narrow definition (adjacent inverse cancellation + bounded commutation), t|ket>'s pass - explicitly named "FullPeepholeOptimise" - achieves 23-63% reduction on VQE/IQP/UCCSD using single-qubit rotation merging, template matching, and phase polynomial synthesis. These are standard peephole techniques. The "ceiling" on these families is the prototype's ceiling, not a structural limit of peephole optimization.

**4. The difference is engineering sophistication, not algorithmic paradigm.** The prototype implements a subset of peephole techniques. Production compilers implement a superset. When the superset achieves positive reduction where the subset achieves 0%, the ceiling is optimizer-specific, not structural.

### Corrected Comparison Note

The previous version of this table reported aggregate means (Greedy +7.8%, Qiskit L0 -247.9%, etc.), which was misleading. The aggregate mean is dominated by basis-translation inflation on QuantumWalk (-2526%) and Grover (-882%). The per-family table above is the correct comparison.
