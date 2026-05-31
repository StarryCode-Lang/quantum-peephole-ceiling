# Literature Map: Phase Transition Structures and Optimisability in Quantum Circuit Search Spaces

## Overview

**Total Papers Found**: 148+
- Quantum Circuit Optimization: 41 papers
- Phase Transitions in Computational Problems: 35 papers
- Quantum Circuit Structure & Landscape Theory: 38 papers
- Research Gaps & Surveys: 30+ papers

**Time Span**: 1994-2025
**Key Databases**: arXiv, IEEE, APS, Nature, Science, ACM, Springer

---

## Literature Landscape

### 1. Quantum Circuit Optimization (41 papers)

**Core Topics**:
- Gate synthesis algorithms (MITM, QFAST, Z4)
- Circuit simplification (ZX-calculus, template matching)
- Optimization methods (greedy, SA, GA, RL)
- Complexity bounds (NP-hardness, #P-hardness)
- Tools (Qiskit, BQSKit, MQT)

**Key Findings**:
- T-count optimization is NP-hard (van de Wetering 2023)
- ZX-calculus extraction is #P-hard (de Beaudrap 2022)
- RL approaches emerging (AlphaTensor 2025)
- BQSKit dominant academic tool

**Research Gap**: No connection to phase transition theory

### 2. Phase Transitions in Computational Problems (35 papers)

**Core Topics**:
- Phase transition theory (order parameters, critical exponents)
- SAT phase transitions (k-SAT threshold, 1RSB)
- Graph coloring phase transitions
- Optimization landscape phase transitions

**Key Findings**:
- SAT phase transition at clause-to-variable ratio ~4.27 (3-SAT)
- Replica cavity method solves random 3-SAT
- Universality classes exist across different problems
- Local optima networks characterize phase transitions

**Research Gap**: Not applied to quantum circuits

### 3. Quantum Circuit Structure & Landscape Theory (38 papers)

**Core Topics**:
- Barren plateaus (gradient vanishing)
- Entanglement phase transitions
- Circuit representations (DAG, ZX, tensor networks)
- Circuit complexity measures
- Local minima and optimization landscapes

**Key Findings**:
- Barren plateaus are fundamental challenge (McClean 2018)
- Measurement-induced entanglement phase transitions exist
- Nielsen complexity connects to topological phases
- Natural gradient helps escape local minima

**Research Gap**: No framework connecting structure to optimizability

### 4. Research Gaps & Surveys (30+ papers)

**Identified Gaps**:
1. No phase transition framework for circuit optimizability
2. No predictive models for optimization hardness
3. No circuit structure → optimizability connection
4. No search space landscape topology mapping

**Survey Sources**:
- MDPI Quantum (2025)
- IEEE Quantum Architecture Search (2024)
- arXiv VQA Reviews (2024)
- APS Measurement-Induced Phase Transitions (2023-2024)

---

## Research Positioning

### What Exists:
1. Rich physics of phase transitions in quantum circuits (entanglement, complexity)
2. Rich optimization literature for quantum circuits (synthesis, compilation)
3. Rich phase transition theory from statistical physics (SAT, graph problems)

### What's Missing:
1. **Connection**: Phase transition theory → Quantum circuit optimization
2. **Framework**: Circuit structure → Optimizability via phase transitions
3. **Predictors**: Structural features → Optimization hardness
4. **Mapping**: Search space topology → Phase boundaries

### Novelty of This Research:
- First to apply phase transition theory to quantum circuit optimization
- First to develop predictive models for circuit optimizability
- First to map search space topology with phase boundaries
- First to connect circuit structure to optimization difficulty via statistical physics

---

## Key Papers by Relevance

### Most Relevant (Must Cite):
1. van de Wetering (2023) - NP-hardness of circuit optimization
2. McClean (2018) - Barren plateaus
3. Kirkpatrick & Selman (1994) - SAT phase transition
4. Monasson et al. (1999) - Phase transitions and complexity
5. Zdeborová & Krzakala (2007) - Graph coloring phase transitions
6. Mézard et al. (2002) - Cavity method for SAT
7. Nielsen (2006) - Geometric approach to circuit complexity
8. Cerezo et al. (2022) - Barren plateau analysis
9. Haug & Bharti (2022) - Entanglement complexity transitions
10. Hartmann & Weigt (2005) - Phase transitions textbook

### Foundational Theory:
- Statistical physics of phase transitions
- Replica cavity method
- Universality classes and critical exponents
- Fitness landscape theory

### Quantum Circuit Specific:
- Gate synthesis algorithms
- ZX-calculus
- Qiskit/BQSKit transpilers
- VQA training challenges

---

## Literature Organization

```
literature/
├── 01_quantum_circuit_optimization.md  (41 papers)
├── 02_phase_transitions.md             (35 papers)
├── 03_circuit_structure_landscape.md   (38 papers)
├── 04_research_gaps.md                 (30+ papers)
└── 05_literature_map.md                (this file)
```

---

## Next Steps

1. **Deep Dive**: Read top 20 most relevant papers in detail
2. **Theory Development**: Build mathematical framework connecting phases to circuits
3. **Gap Filling**: Design experiments to address identified gaps
4. **Positioning**: Clearly articulate novelty and contributions

---

## Statistics

- **Total Papers**: 148+
- **Time Span**: 31 years (1994-2025)
- **Sources**: 10+ journals/conferences
- **Languages**: English (100%)
- **Open Access**: ~60%
- **Key Authors**: 50+ researchers
