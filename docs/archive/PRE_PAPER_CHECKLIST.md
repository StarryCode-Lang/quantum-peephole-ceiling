# Pre-Paper-Writing Final Checklist

**Project**: Q-research — Boundary Characterization of Quantum Circuit Peephole Optimization  
**Date**: 2026-06-14  
**Status**: READY FOR PAPER WRITING

---

## Verification Summary

| Check | Status | Detail |
|-------|--------|--------|
| All unit tests pass | ✅ | 239 tests, all passing |
| All figures regenerated | ✅ | 17 generated PDF figures from canonical data |
| Release manifest updated | ⚠️ | SHA256 computed, but manifest remains dirty until commit/regeneration and includes legacy entries |
| Data canonical file aligned | ⚠️ | DATA_CANONICAL.md is authoritative; release manifest includes canonical plus legacy/provenance entries |
| README.md updated | ✅ | v5.0.0, 53,300 canonical optimizer trials, core/statistical tests documented |
| PROJECT_SUMMARY.md updated | ✅ | Consistent with README |
| manuscript_structure.md updated | ✅ | v5 structure, 53,300 canonical optimizer trials, target Quantum |
| E12 degeneracy resolved | ✅ | New 568-row data shows distinct L0/L1/L2/L3 |
| v6 directory documented | ✅ | README/data/v6 documents E19 (full canonical run, 10,000 rows), E20 (metadata-only), E21 (smoke-only) |
| provenance.py updated | ✅ | Includes ceiling_aware.py, wire_traversal.py |
| FDR correction complete | ✅ | 11/15 hypotheses significant after BH-FDR |
| Target journal unified | ✅ | All documents reference Quantum (quantum-journal.org) |

---

## Experiment Data Summary (Canonical)

| Experiment | Rows | Key Result |
|-----------|------|------------|
| E1 Phase Transition | 25,000 | ~0% reduction across all depths |
| E2 Entanglement Density | 2,100 | No correlation with entanglement |
| E3 Scaling | 12,000 | ~0% reduction for n=3-10 |
| E4 Algorithm Comparison | 400 | All optimizers ~0% |
| E5 Landscape | 6,000 | Flat landscape, rare deep minima |
| E10 Phase 1 vs Phase 2 | 1,905 | Expanded Phase 1/Phase 2 comparison; supersedes 819-row intermediate run |
| E11 Real-Circuit Benchmark | 426 | 15 families × 3 optimizers |
| E12 Compiler Baseline | 568 | Qiskit L0/L1/L2/L3 all distinct |
| E13 Structural Ceiling | 56 | Ceiling proxy estimates |
| E14 Extended Benchmark | 2,130 | 15 families, extended metrics |
| E15 Compiler Comparison | 994 | Custom vs Qiskit (Qiskit-only) |
| E16 Window Scaling | 696 | Saturation at ws=10-20 |
| E17 Connectivity | 755 | Linear/grid/heavy-hex |
| E18 Clifford+T | 270 | T-count reduction |
| E19 WCL Listing | 10,000 | WCL vs LBL comparison; WCL 7.83% vs LBL 0.0000% |
| **Total E1-E18** | **53,300** | canonical optimizer rows |
| **Total incl. E19 + held-out/isolation** | **63,525** | canonical analysis artifacts |

---

## Figures Generated (17 total)

| Figure | File | Content |
|--------|------|---------|
| Fig 1 | fig01_phase_transition.pdf | E1 depth sweep |
| Fig 2 | fig02_scaling.pdf | E3 qubit scaling |
| Fig 3 | fig03_algorithm_comparison.pdf | E4 optimizer comparison |
| Fig 4 | fig04_phase1_vs_phase2.pdf | E10 Phase 1 vs Phase 2 |
| Fig 5 | fig05_threshold_sensitivity.pdf | Threshold sensitivity |
| Fig 6 | fig06_fidelity_distribution.pdf | Fidelity distributions |
| Fig 7 | fig07_landscape.pdf | E5 landscape |
| Fig 8 | fig08_fdr_correction.pdf | BH-FDR results |
| Fig 8b | fig08b_real_circuit_optimizer_comparison.pdf | E11 real circuits |
| Fig 9 | fig09_compiler_baseline_comparison.pdf | E12 Qiskit baseline |
| Fig 10 | fig10_structural_ceiling_gap.pdf | E13 ceiling gap |
| Fig 11 | fig11_extended_benchmark_heatmap.pdf | E14 heatmap |
| Fig 12 | fig12_multi_compiler_comparison.pdf | E15 compiler comparison |
| Fig 13 | fig13_window_scaling_curves.pdf | E16 window scaling |
| Fig 14 | fig14_connectivity_ceiling.pdf | E17 connectivity |
| Fig 15 | fig15_qiskit_pass_waterfall.pdf | Qiskit pass waterfall |
| Fig 16 | fig16_qiskit_pass_family_heatmap.pdf | Qiskit pass family heatmap |
| Fig 17 | fig17_qiskit_pass_interaction.pdf | Qiskit pass interaction |

---

## Known Limitations (for paper)

1. **L3/L8 (HIGH)**: Multi-compiler comparison is Qiskit-only; Cirq and t|ket> not yet benchmarked
2. **L5 (MEDIUM)**: ~60% circuit family decomposition failures in Clifford+T (E18)
3. **Theorem 2**: INSERTION cascade gap resolved for bounded circuits (Theorem 2b/2c/2d); unbounded version remains open
4. **Theorem 8**: Applies to Haar-random unitaries, not experimental random gate sequences
5. **Qubit scale**: Limited to n=3-20
6. **No noise modeling**: All experiments are noiseless

---

## Paper Writing Entry Points

- **Manuscript**: `docs/06_manuscript/v6_manuscript.md` (authoritative v6 manuscript, complete)
- **Theory framework**: `docs/01_theory/framework.md` (v5.4.0, 12 definitions, 10 theorems)
- **Literature review**: `docs/02_literature/literature_review.md` (42 narrative refs; see `unified_references.md` for authoritative list of 81 refs)
- **Experimental design**: `docs/03_results/experimental_design.md` (formal specification)
- **Claim-evidence map**: `docs/06_manuscript/v6_claim_evidence_map.md`
- **Scope/limitations**: `docs/06_manuscript/v6_scope_limitations_risks.md`
- **Unified references**: `docs/02_literature/unified_references.md`
- **Supplementary materials**: `docs/05_supplementary/supplementary_materials.md`

---

## Recommended Next Steps

1. Use the `academic-paper-writing` skill to draft the full manuscript from `manuscript_structure.md`
2. Target: Quantum (quantum-journal.org), 10-12 pages main + supplementary
3. Use `paper-polishing-translation` skill for language polishing
4. Use `latex-paper-writing` skill for LaTeX formatting
