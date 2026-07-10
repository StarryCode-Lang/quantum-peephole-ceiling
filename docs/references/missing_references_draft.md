# Missing Key References — Draft Addendum

> **Status**: Draft. Exact bibliographic details (especially arXiv IDs and page numbers) should be verified before integration into `unified_references.md`.
>
> This file collects the key references identified in `docs/07_optimization_plan.md` §4.6.1 that are not yet present in the authoritative `unified_references.md` list. Once verified, these entries should be merged into `unified_references.md` with consecutive numbering and the in-text citations in the manuscript updated accordingly.

---

## 1. Classical CNOT Synthesis / Gate-Count Lower Bounds

[D1] V. V. Shende, S. S. Bullock, and I. L. Markov, "Synthesis of quantum-logic circuits," *IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems*, vol. 25, no. 6, pp. 1000-1010, 2006.

[D2] V. V. Shende, I. L. Markov, and S. S. Bullock, "The minimal reversible circuit with an arbitrary number of inputs," *ISMVL*, 2004.

---

## 2. Quantum Circuit Optimization — Foundational Algorithms

[D3] Y. Nam, N. J. Ross, Y. Su, A. M. Childs, and D. Maslov, "Automated optimization of large quantum circuits with continuous parameters," *npj Quantum Information*, vol. 4, article 23, 2018. arXiv:1710.07345

[D4] K. Hietala, R. Rand, S.-H. Hung, X. Wu, and M. Hicks, "A verified optimizer for quantum circuits," *Proceedings of the ACM on Programming Languages*, vol. 5, no. POPL, article 32, 2021. (Journal version: *ACM TOPLAS*, 2023 — exact details to be verified.)

---

## 3. ZX-Calculus and Diagrammatic Methods

[D5] R. Duncan, A. Kissinger, S. Perdrix, and J. van de Wetering, "Graph-theoretic simplification of quantum circuits with the ZX-calculus," *Quantum*, vol. 4, p. 279, 2020. arXiv:1902.03178

[D6] A. Kissinger and J. van de Wetering, "PyZX: Large-scale automated diagrammatic reasoning," *QPL*, 2019. arXiv:1904.04735

---

## 4. Machine-Learning / RL-Based Quantum Circuit Optimizers

[D7] Q. Xu, M. Li, M. Ying, and Z. Sui, "Synthesizing quantum-circuit optimizers," *PLDI*, pp. 855-869, 2023. arXiv:2211.11896

[D8] G. Li, Z. Miao, Y. Ding, and Y. Xie, "Quarl: A learning-based quantum circuit optimizer," *OOPSLA*, 2024.

[D9] M. Ruiz, M. M. Rice, S. Tannu, P. D. Nation, M. Piszczak, A. Ho, T. Loke, S. Vijay, and A. Javadi-Abhari, "Quantum circuit optimization with AlphaTensor," *Nature Machine Intelligence*, 2025.

[D10] R. I. Riu, S. Tannu, and A. Javadi-Abhari, "Reinforcement learning based quantum circuit optimization via ZX-calculus," *Quantum*, 2025.

---

## 5. Industry Benchmark Suites

[D11] P. D. Nation, A. A. Saki, S. Brandhofer, L. Bello, S. Garion, M. Treinish, and A. Javadi-Abhari, "Benchmarking the performance of quantum computing software," *Nature Computational Science*, 2025. arXiv:2409.08844

[D12] N. Quetschlich, L. Burgholzer, and R. Wille, "MQT Bench: Benchmarking software and design automation tools for quantum computing," *Quantum*, vol. 7, p. 1142, 2023. arXiv:2204.13719

[D13] B. Tan and J. Cong, "Optimal layout synthesis for quantum computing," *ICCAD*, 2020. (QUEKO benchmark suite.)

---

## 6. Advanced Compiler / Phase-Polynomial Methods

[D14] J. Liu, A. Gonzales, B. Huang, Z. H. Saleem, and P. Hovland, "QuCLEAR: Clifford extraction and absorption for quantum circuit optimization," arXiv:2408.13316, 2024.

[D15] T. Onodera, Y. Sato, T. Itoko, and N. Yamamoto, "Multilevel circuit optimization in quantum compilers: A case study," arXiv:2505.09320, 2025.

[D16] P.-A. Plante, S. G. N. Jones, and A. Broadbent, "PHOENIX: Pauli-based high-level quantum circuit optimization," *DAC*, 2025. (Exact citation to be verified.)

---

## 7. Circuit Unoptimization / Hardness Perspective

[D17] A. B. Grilo, A. A. M. de Oliveira, and S. P. Perdrix, "Quantum circuit unoptimization," *Physical Review Research*, vol. 7, no. 2, 023139, 2025.

[D18] M. A. Nielsen and I. L. Chuang, *Quantum Computation and Quantum Information*, 10th anniversary ed., Cambridge University Press, 2010.

---

## 8. Random Unitary Designs / Theoretical Barriers

[D19] F. G. S. L. Brandão, A. W. Harrow, and M. Horodecki, "Local random quantum circuits are approximate polynomial-designs," *Communications in Mathematical Physics*, vol. 346, no. 2, pp. 397-434, 2016. arXiv:1208.0692

[D20] S. Aaronson and D. Gottesman, "Improved simulation of stabilizer circuits," *Physical Review A*, vol. 70, no. 5, 052328, 2004.

---

## Integration checklist

- [ ] Verify each title, author list, venue, year, and DOI/arXiv ID.
- [ ] Renumber entries to be consecutive with `unified_references.md`.
- [ ] Add in-text citations in `docs/manuscript/manuscript.md` and `docs/theory/*.md`.
- [ ] Generate `.bib` file for LaTeX compilation.
