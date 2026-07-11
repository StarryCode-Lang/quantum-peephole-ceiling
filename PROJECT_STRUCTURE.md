# Project Structure

```
Q-research/
├── src/                                      # Source code for circuit generation and optimization
│   ├── circuits/                             # Circuit generation modules (v2.1)
│   └── optimisation/
│       ├── phase1/                            # Phase 1: Adjacent-search optimizers (Greedy, RLS, SA, GA)
│       └── phase2/                            # Phase 2: Commutation-based optimizers
├── experiments/                              # Experiment scripts organized by experiment ID
│   ├── e01_phase_transition/                 # E1: Phase transition test (25,000 trials)
│   ├── e02_entanglement_density/             # E2: Entanglement density sweep (2,100 trials)
│   ├── e03_scaling/                          # E3: Scaling analysis (12,000 trials)
│   ├── e04_algorithm_comparison/             # E4: Algorithm comparison (400 trials)
│   ├── e05_landscape/                        # E5: Landscape characterization (6,000 trials)
│   ├── e10_phase1_vs_phase2/                 # E10: Phase 1 vs Phase 2 comparison (1,905 trials)
│   ├── e11_real_circuit_benchmark/           # E11: Real-circuit optimizer benchmark (426 trials)
│   ├── e12_compiler_baseline/                # E12: Qiskit compiler baseline (568 trials)
│   ├── e13_structural_ceiling/               # E13: Structural ceiling analysis (56 trials)
│   ├── e14_extended_benchmark/               # E14: Extended benchmark (2,130 trials)
│   ├── e15_multi_compiler/                   # E15: Custom peephole vs Qiskit (994 trials)
│   ├── e16_window_scaling/                   # E16: Phase-2 window size saturation (696 trials)
│   ├── e17_connectivity/                     # E17: Topology constraint analysis (755 trials)
│   ├── e18_clifford_t/                       # E18: Clifford+T decomposition (270 trials)
│   ├── e19_wcl_listing/                      # E19: WCL vs LBL listing comparison (10,000 trials)
│   ├── e20_multi_compiler_full/              # E20: Qiskit/Cirq/t|ket> comparison (1,070 trials)
│   ├── e21_ceiling_aware/                    # E21: Ceiling-aware optimizer (1,140 trials)
│   ├── e23_ag_canonical/                     # E23: AG canonical form validation (160 trials)
│   ├── e24_theorem7/                         # E24: Theorem 7 hardness validation (75 trials)
│   └── e25_industry_benchmarks/              # E25: Industry proxy circuit benchmarks (66 trials)
├── data/                                     # Versioned experimental data
│   ├── v2_fixed/                             # E1-E5 re-run with fixed Greedy v3.0.0
│   ├── v4/                                   # Real-circuit, compiler baseline, ceiling outputs (E11-E13)
│   ├── v5/                                   # Extended benchmark suite (E10 expanded, E14-E18)
│   ├── v6/                                   # Preliminary/planned artifacts (E19-E21, E25)
│   └── v7/                                   # Theorem validation data (E23, E24)
├── analysis/                                 # Analysis scripts and outputs
│   ├── figures/                              # Generated analysis figures (17 vector PDF figures)
│   ├── phase1_statistics/                    # Statistical methods toolkit for Phase 1
│   └── phase2_threshold_sensitivity/         # Threshold sensitivity analysis for Phase 2
├── docs/                                     # Documentation
│   ├── theory/                               # Theoretical framework (definitions, theorems, complexity)
│   ├── manuscript/                           # Manuscript draft and appendices
│   ├── supplementary/                        # Supplementary materials for manuscript
│   ├── archive/                              # Historical documentation (audit reports, checklists)
│   └── deliverables/                         # Phase completion reports
├── scripts/                                  # One-command reproduction and release scripts
├── tests/                                    # Core and statistical unit tests
└── release/                                  # Machine-readable release manifest
```
