## Reclassification of "Ceiling" Families

Based on production compiler results (Qiskit O3, t|ket> FullPeepholeOptimise), the 10 families previously classified as "structural ceiling" are reclassified into three groups:

| Family | Prototype (Hybrid) | Qiskit O3 | t|ket> FullPeephole | Classification |
|--------|-------------------|-----------|---------------------|----------------|
| QFT | 0.0% | 0.0% | 0.0% | **Genuine Ceiling** |
| GHZ | 0.0% | 0.0% | 0.0% | **Genuine Ceiling** |
| SurfaceCode | 0.0% | 0.0% | 0.0% | **Genuine Ceiling** |
| VQE | 0.0% | 39.3% | 39.6% | **Prototype-Limited** |
| HardwareEfficient | 0.0% | 35.5% | 35.8% | **Prototype-Limited** |
| IQP | 0.3% | 60.0% | 63.4% | **Prototype-Limited** |
| UCCSD | 0.3% | 23.3% | 22.5% | **Prototype-Limited** |
| QAOA | 0.0% | 0.0% | 5.4% | **Prototype-Limited (weak)** |
| Grover | 4.1% | -881.8% | -437.5% | **Unclear** (n-dependent) |
| QuantumWalk | 0.0% | -2526% | -1083% | **Unclear** (inflation) |

### Genuine Ceiling (3 families)
QFT, GHZ, SurfaceCode: all compilers (custom prototype, Qiskit O0-O3, t|ket> FullPeepholeOptimise) agree at 0% reduction. These circuits are genuinely gate-count-optimal under standard decomposition. The ceiling is structural.

### Prototype-Limited (5 families)
VQE, HardwareEfficient, IQP, UCCSD, QAOA: the prototype achieves ~0% but production peephole optimizers achieve 5-63% reduction. The ceiling is an artifact of the prototype's limited move set (adjacent inverse cancellation + bounded commutation window), not a structural property. t|ket>'s FullPeepholeOptimise - explicitly named as a peephole optimizer - achieves 23-63% on these families using single-qubit rotation merging, template matching, and phase polynomial synthesis, all of which are standard peephole techniques.

### Unclear (2 families)
Grover: Qiskit achieves 44-55% at n=6 but massive inflation at n=4,8 due to basis translation overhead. QuantumWalk: all compilers produce massive inflation (basis translation of multi-controlled gates). Neither has been tested in a no-basis-translation mode, so the ceiling status is inconclusive.

### Implications

The "10/15 families at structural ceiling" claim is revised to:
- **3/15 genuine structural ceiling** (QFT, GHZ, SurfaceCode)
- **5/15 prototype action-space ceiling** (VQE, HardwareEfficient, IQP, UCCSD, QAOA)
- **2/15 unclear** (Grover, QuantumWalk)
- **5/15 not at ceiling** (CNOT, Oracle, RandomClifford, Adder, HaarRandom)

The term "structural ceiling" should be reserved for the 3 genuine cases. For the 5 prototype-limited cases, the correct term is "prototype action-space ceiling."
