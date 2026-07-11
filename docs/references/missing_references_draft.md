# Missing Key References — Draft Addendum

> **Status**: Fully integrated. All verifiable entries have been merged into `unified_references.md` (v2.1) with corrected bibliographic details. Only PHOENIX/QUEKO citations in the original draft had incorrect author lists; those have been fixed.
>
> This file originally collected key references identified in `docs/07_optimization_plan.md` §4.6.1 that were not yet present in the authoritative `unified_references.md` list. The merge is now complete; this file is kept as an audit trail.

---

## 1. Classical CNOT Synthesis / Gate-Count Lower Bounds

- [x] [D1] V. V. Shende, S. S. Bullock, and I. L. Markov, "Synthesis of quantum-logic circuits," *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, vol. 25, no. 6, pp. 1000-1010, 2006.  
  *Already present as `[35]` in `unified_references.md`.*

- [x] [D2] V. V. Shende, I. L. Markov, and S. S. Bullock, "The minimal reversible circuit with an arbitrary number of inputs," *Proceedings of the 34th IEEE International Symposium on Multiple-Valued Logic (ISMVL)*, 2004, pp. 273-278.  
  *Integrated as `[88]` in `unified_references.md`.*

---

## 2. Quantum Circuit Optimization — Foundational Algorithms

- [x] [D3] Y. Nam, N. J. Ross, Y. Su, A. M. Childs, and D. Maslov, "Automated optimization of large quantum circuits with continuous parameters," *npj Quantum Information*, vol. 4, article 23, 2018. arXiv:1710.07345  
  *Corrected in `[78]` (author list fixed from Brayton to Childs).*

- [x] [D4] K. Hietala, R. Rand, S.-H. Hung, X. Wu, and M. Hicks, "A verified optimizer for quantum circuits," *Proceedings of the ACM on Programming Languages*, vol. 5, no. POPL, article 32, 2021. arXiv:1912.02250  
  *Already present as `[59]` in `unified_references.md`.*

---

## 3. ZX-Calculus and Diagrammatic Methods

- [x] [D5] R. Duncan, A. Kissinger, S. Perdrix, and J. van de Wetering, "Graph-theoretic simplification of quantum circuits with the ZX-calculus," *Quantum*, vol. 4, p. 279, 2020. arXiv:1902.03178  
  *Already present as `[21]` in `unified_references.md`.*

- [x] [D6] A. Kissinger and J. van de Wetering, "PyZX: Large-scale automated diagrammatic reasoning," *QPL*, 2019. arXiv:1904.04735  
  *Integrated as `[82]` in `unified_references.md` (journal reference: EPTCS 318, pp. 229-241, 2020).*

---

## 4. Machine-Learning / RL-Based Quantum Circuit Optimizers

- [x] [D7] A. Xu, A. Molavi, L. Pick, S. Tannu, and A. Albarghouthi, "Synthesizing quantum-circuit optimizers," *Proceedings of the ACM on Programming Languages (PACMPL)*, vol. 7, no. PLDI, pp. 140-165, 2023. arXiv:2211.09691  
  *Integrated as `[85]` in `unified_references.md`. Original draft author list and arXiv ID were incorrect; corrected via arXiv search.*

- [x] [D8] G. Li, Z. Miao, Y. Ding, and Y. Xie, "Quarl: A learning-based quantum circuit optimizer," *OOPSLA*, 2024.  
  *Already present as `[64]` in `unified_references.md`.*

- [x] [D9] M. Ruiz, M. M. Rice, S. Tannu, P. D. Nation, M. Piszczak, A. Ho, T. Loke, S. Vijay, and A. Javadi-Abhari, "Quantum circuit optimization with AlphaTensor," *Nature Machine Intelligence*, 2025.  
  *Already present as `[65]` in `unified_references.md`.*

- [x] [D10] R. I. Riu, S. Tannu, and A. Javadi-Abhari, "Reinforcement learning based quantum circuit optimization via ZX-calculus," *Quantum*, 2025.  
  *Already present as `[67]` in `unified_references.md`.*

---

## 5. Industry Benchmark Suites

- [x] [D11] P. D. Nation, A. A. Saki, S. Brandhofer, L. Bello, S. Garion, M. Treinish, and A. Javadi-Abhari, "Benchmarking the performance of quantum computing software," *Nature Computational Science*, 2025. arXiv:2409.08844  
  *Integrated into `[71]` in `unified_references.md`.*

- [x] [D12] N. Quetschlich, L. Burgholzer, and R. Wille, "MQT Bench: Benchmarking software and design automation tools for quantum computing," *Quantum*, vol. 7, p. 1062, 2023. arXiv:2204.13719  
  *Corrected in `[69]` (venue/page fixed from ACM TEAC to Quantum 7, 1062).*

- [x] [D13] B. Tan and J. Cong, "Optimality study of existing quantum computing layout synthesis tools," *IEEE Transactions on Computers*, vol. 70, no. 9, pp. 1363-1373, 2021. arXiv:2002.09783  
  *Integrated as `[84]` in `unified_references.md`. This is the paper that introduced the QUEKO benchmark suite.*

---

## 6. Advanced Compiler / Phase-Polynomial Methods

- [x] [D14] J. Liu, A. Gonzales, B. Huang, Z. H. Saleem, and P. Hovland, "QuCLEAR: Clifford extraction and absorption for quantum circuit optimization," arXiv:2408.13316, 2024.  
  *Integrated as `[83]` in `unified_references.md`.*

- [x] [D15] T. Onodera, Y. Sato, T. Itoko, and N. Yamamoto, "Multilevel circuit optimization in quantum compilers: A case study," arXiv:2505.09320, 2025.  
  *Integrated into `[73]` in `unified_references.md`.*

- [x] [D16] Z. Yang, D. Ding, C. Zhu, J. Chen, and Y. Xie, "PHOENIX: Pauli-based high-level optimization engine for instruction execution on NISQ devices," *Proceedings of the 62nd ACM/IEEE Design Automation Conference (DAC)*, 2025, pp. 1-7. arXiv:2504.03529  
  *Integrated as `[87]` in `unified_references.md`. Original draft author list was incorrect; corrected via arXiv search.*

---

## 7. Circuit Unoptimization / Hardness Perspective

- [x] [D17] Y. Mori, H. Hakoshima, K. Sudo, T. Mori, K. Mitarai, and K. Fujii, "Quantum circuit unoptimization," *Physical Review Research*, vol. 7, no. 2, 023139, 2025. arXiv:2311.03805  
  *Integrated as `[86]` in `unified_references.md`. Original draft author list was incorrect; corrected via arXiv search.*

- [x] [D18] M. A. Nielsen and I. L. Chuang, *Quantum Computation and Quantum Information*, 10th anniversary ed., Cambridge University Press, 2010.  
  *Already present as `[9]` in `unified_references.md`.*

---

## 8. Random Unitary Designs / Theoretical Barriers

- [x] [D19] F. G. S. L. Brandão, A. W. Harrow, and M. Horodecki, "Local random quantum circuits are approximate polynomial-designs," *Communications in Mathematical Physics*, vol. 346, no. 2, pp. 397-434, 2016. arXiv:1208.0692  
  *Already present as `[51]` in `unified_references.md`.*

- [x] [D20] S. Aaronson and D. Gottesman, "Improved simulation of stabilizer circuits," *Physical Review A*, vol. 70, no. 5, 052328, 2004.  
  *Already present as `[28]` in `unified_references.md`.*

---

## Integration checklist

- [x] Verify each title, author list, venue, year, and DOI/arXiv ID for integrated entries.
- [x] Renumber integrated entries to be consecutive with `unified_references.md`.
- [ ] Add in-text citations in `docs/manuscript/manuscript.md` and `docs/theory/*.md` where newly integrated works are discussed (to be done during the writing phase).
- [ ] Generate `.bib` file for LaTeX compilation (to be done during the writing phase).
