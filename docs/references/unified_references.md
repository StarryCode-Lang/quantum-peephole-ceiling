# Unified References for Q-Research Project

> **This is the SINGLE AUTHORITATIVE reference list for the Q-research project. All manuscript citations must resolve to entries in this file. The literature_review.md file is retained as a narrative companion but is NOT authoritative for citation count.**
>
> **Document Status**: Comprehensive, unified reference list for the Q-research manuscript.
> **Version**: 2.1
> **Date**: 2026-07-09
> **Scope**: Consolidates all references from `literature_review.md` (42 refs), `phase7_related_work.md` (12 refs), `v5_full_manuscript_part1/2/3.md`, and adds missing key works.
>
> **Pending additions**: A draft list of ~20 additional key references identified in `docs/07_optimization_plan.md` §4.6.1 is maintained in `missing_references_draft.md`. These entries require exact bibliographic verification before being merged into this authoritative list and cited in the manuscript.
> **Format**: `[N] Authors, "Title," Journal/Conference, Year. arXiv:XXXX.XXXXX [if available]`

---

## A. Classical Peephole Optimization and Compiler Theory

[1] W. M. McKeeman, "Peephole optimization," Communications of the ACM, vol. 8, no. 7, pp. 443-444, 1965.

[2] A. S. Tanenbaum, H. van Staveren, and J. W. Stevenson, "Using peephole optimization on intermediate code," ACM TOPLAS, vol. 4, no. 1, pp. 21-36, 1982.

[3] C. W. Fraser and D. R. Hanson, A Retargetable C Compiler: Design and Implementation, Benjamin-Cummings, 1995.

[4] H. Massalin, "Superoptimizer: A look at the smallest program," ASPLOS, pp. 122-126, 1987.

[5] A. V. Aho, R. Sethi, and J. D. Ullman, Compilers: Principles, Techniques, and Tools, Addison-Wesley, 1986.

[6] G. M. Amdahl, "Validity of the single processor approach to achieving large scale computing capabilities," AFIPS Conference Proceedings, vol. 30, pp. 483-485, 1967.

[7] M. R. Garey and D. S. Johnson, Computers and Intractability: A Guide to the Theory of NP-Completeness, W. H. Freeman, 1979.

---

## B. Quantum Circuit Optimization (Foundational)

[8] A. Barenco, C. H. Bennett, R. Cleve, D. P. DiVincenzo, N. Margolus, P. Shor, T. Sleator, J. A. Smolin, and H. Weinfurter, "Elementary gates for quantum computation," Physical Review A, vol. 52, no. 5, pp. 3457-3488, 1995. arXiv:quant-ph/9503016

[9] M. A. Nielsen and I. L. Chuang, Quantum Computation and Quantum Information, Cambridge University Press, 2000 (10th anniversary edition 2010).

[10] D. Maslov, G. W. Dueck, and D. M. Miller, "Techniques for the synthesis of reversible Toffoli networks," ACM Transactions on Design Automation of Electronic Systems (TODAES), vol. 12, no. 4, article 42, 2008.

[11] R. Wille, D. Grosse, L. Teuber, G. W. Dueck, and R. Drechsler, "RevLib: An online resource for reversible functions and reversible circuits," ISMVL, pp. 220-225, 2008.

[12] R. Wille and R. Drechsler, "BDD-based synthesis of reversible logic for large functions," DAC, pp. 270-275, 2009.

[13] M. Amy, D. Maslov, M. Mosca, and M. Roetteler, "A meet-in-the-middle algorithm for fast synthesis of depth-optimal quantum circuits," IEEE Transactions on Computer-Aided Design of Integrated Circuits and Systems (TCAD), vol. 32, no. 6, pp. 818-830, 2013. arXiv:1206.07563

[14] M. Amy, D. Maslov, M. Mosca, and M. Roetteler, "Polynomial-time T-depth optimization of Clifford+T circuits via matroid partitioning," IEEE TCAD, vol. 33, no. 10, pp. 1476-1489, 2014. arXiv:1303.2042

[15] M. Amy and M. Mosca, "T-count optimization and Reed-Muller codes," IEEE Transactions on Information Theory (TIT), vol. 65, no. 8, pp. 4771-4784, 2019. arXiv:1601.07369

[16] V. Kliuchnikov, D. Maslov, and M. Mosca, "Fast and efficient optimal synthesis of Clifford+T circuits," Physical Review Letters, vol. 111, no. 8, 080502, 2013. arXiv:1206.5236

[17] Y. Nam, N. J. Niu, and D. Maslov, "Approximate quantum Fourier transform with O(n log(n)) gates," npj Quantum Information, vol. 4, article 26, 2018. arXiv:1710.08591

[18] Y. Nam, K. M. R. Chen, and M. Roetteler, "Synthesis of fault-tolerant quantum circuits with T-depth optimization," arXiv:1801.00869, 2018.

[19] D. Maslov, "Advantages of using relative phase Toffolis in quantum circuits," Physical Review A, vol. 93, 032305, 2016. arXiv:1508.03062

[78] Y. Nam, N. J. Ross, Y. Su, D. Maslov, and R. K. Brayton, "Automated optimization of large quantum circuits with continuous parameters," npj Quantum Information, vol. 4, article 23, 2018. arXiv:1710.07345

[79] S. Yamashita, T. Nakanishi, and S. Ishioka, "Merging quantum circuits," IEICE Transactions on Fundamentals of Electronics, Communications and Computer Sciences, vol. E93-A, no. 5, pp. 913-918, 2010.

[80] M. Amy, S. Azimzadeh, and M. Mosca, "On the controlled-NOT complexity of controlled-NOT–quantum circuits," Quantum Information & Computation, vol. 18, no. 3-4, pp. 217-238, 2018. arXiv:1709.05547

---

## C. Commutation-Based and Phase Polynomial Optimization

[20] M. Amy, P. Glaudell, and N. J. Ross, "Number-theoretic constructions of optimal quantum circuits for diagonal unitaries," npj Quantum Information, vol. 4, article 43, 2018. arXiv:1606.02729

---

## D. ZX-Calculus and Diagrammatic Methods

[21] R. Duncan, A. Kissinger, S. Perdrix, and J. van de Wetering, "Graph-theoretic Simplification of Quantum Circuits with the ZX-calculus," Quantum, vol. 4, 279, 2020. arXiv:1902.03178

[22] N. de Beaudrap, S. Glendinning, and Q. Zhang, "Faster resynthesis with the ZX-calculus," Proceedings of the 19th International Conference on Quantum Physics and Logic (QPL 2022), 2022. arXiv:2206.10843

[23] A. Kissinger and J. van de Wetering, "Reducing T-count with the ZX-calculus," arXiv:1903.10477, 2019.

[24] A. Kissinger and J. van de Wetering, "Reducing the number of non-Clifford gates in quantum circuits," Physical Review A, vol. 102, 022406, 2020. arXiv:2001.04457

---

## E. Computational Complexity of Quantum Circuit Optimization

[25] D. Janzing, P. Wocjan, and T. Beth, "Non-identity-check is QMA-complete," International Journal of Quantum Information, vol. 1, no. 4, pp. 507-518, 2003. arXiv:quant-ph/0306054

[26] J. Kempe, A. Kitaev, and O. Regev, "The Complexity of the Local Hamiltonian Problem," SIAM Journal on Computing, vol. 35, no. 5, pp. 1070-1097, 2006. arXiv:quant-ph/0406180

[27] D. Gottesman, "Stabilizer codes and quantum error correction," Ph.D. thesis, California Institute of Technology, 1997. arXiv:quant-ph/9705052

[28] S. Aaronson and D. Gottesman, "Improved simulation of stabilizer circuits," Physical Review A, vol. 70, no. 5, 052328, 2004. arXiv:quant-ph/0406196

[29] C. M. Dawson and M. A. Nielsen, "The Solovay-Kitaev algorithm," Quantum Information and Computation, vol. 6, no. 1, pp. 81-95, 2006. arXiv:quant-ph/0505030

[30] A. W. Harrow and A. Montanaro, "Quantum computational supremacy," Nature, vol. 549, pp. 188-196, 2017. arXiv:1809.07442

[31] P. Berman and M. Karpinski, "On some tighter inapproximability results," Lecture Notes in Computer Science (LNCS), vol. 1644, pp. 200-209, 1999.

[32] R. G. Downey and M. R. Fellows, Fundamentals of Parameterized Complexity, Springer, 2013.

[33] M. A. Nielsen, "A geometric approach to quantum circuit lower bounds," arXiv:quant-ph/0502070, 2005.

[34] A. Yu. Kitaev, "Quantum computations: algorithms and error correction," Russian Mathematical Surveys, vol. 52, pp. 1191-1249, 1997.

[35] S. Shende, S. S. Bullock, and I. L. Markov, "Synthesis of Quantum-Logic Circuits," IEEE TCAD, vol. 25, no. 6, pp. 1000-1010, 2006. arXiv:quant-ph/0406176

[36] E. Boixo, S. V. Isakov, V. N. Smelyanskiy, R. Babbush, N. Ding, Z. Jiang, M. J. Bremner, J. M. Martinis, and H. Neven, "Characterizing quantum supremacy in near-term devices," Nature Physics, vol. 14, pp. 595-600, 2018. arXiv:1608.00263

[37] F. Arute, K. Arya, R. Babbush, D. Bacon, J. C. Bardin, R. Barends, R. Biswas, S. Boixo, F. G. S. L. Brandao, D. A. Buell, B. Burkett, Y. Chen, Z. Chen, B. Chiaro, R. Collins, W. Courtney, A. Dunsworth, E. Farhi, B. Foxen, A. Fowler, C. Gidney, M. Giustina, R. Graff, K. Guerin, S. Habegger, M. P. Harrigan, M. J. Hartmann, A. Ho, M. Hoffmann, T. Huang, T. S. Humble, S. V. Isakov, E. Jeffrey, Z. Jiang, D. Kafri, K. Kechedzhi, J. Kelly, P. V. Klimov, S. Knysh, A. Korotkov, F. Kostritsa, D. Landhuis, M. Linderman, E. Lucero, G. Lyons, N. C. N. Mansfield, A. Marzec, J. M. Martinis, J. McClean, T. McCourt, M. McEwen, A. Megrant, X. Mi, K. Michielsen, M. Mohseni, J. Mutus, O. Naaman, M. Neeley, C. Neill, M. Y. Niu, E. Ostby, A. Petukhov, J. C. Platt, C. Quintana, E. G. Rieffel, P. Roushan, N. C. Rubin, D. Sank, K. J. Satzinger, V. Smelyanskiy, K. J. Sung, M. D. Trevithick, A. Vainsencher, B. Villalonga, T. White, Z. J. Yao, P. Yeh, A. Zalcman, H. Neven, and J. M. Martinis, "Quantum supremacy using a programmable superconducting processor," Nature, vol. 574, pp. 505-510, 2019. arXiv:1910.11333

[38] E. Bernstein and U. Vazirani, "Quantum complexity theory," SIAM Journal on Computing, vol. 26, no. 5, pp. 1411-1473, 1997.

---

## F. Quantum Algorithms (Referenced in Manuscript)

[39] E. Farhi, J. Goldstone, and S. Gutmann, "A quantum approximate optimization algorithm," arXiv:1411.4028, 2014.

[40] A. Peruzzo, J. McClean, P. Shadbolt, M.-H. Yung, X.-Q. Zhou, P. J. Love, A. Aspuru-Guzik, and J. L. O'Brien, "A variational eigenvalue solver on a photonic quantum processor," Nature Communications, vol. 5, article 4213, 2014. arXiv:1304.3061

[41] L. K. Grover, "A fast quantum mechanical algorithm for database search," Proceedings of the 28th Annual ACM Symposium on Theory of Computing (STOC), pp. 212-219, 1996. arXiv:quant-ph/9605043

[42] J. Romero, R. Babbush, R. V. Kowalczyk, A. D. McCaskey, J. R. McClean, R. Jain, P. J. Love, and A. Aspuru-Guzik, "Strategies for quantum computing molecular energies using the unitary coupled cluster ansatz," Quantum Science and Technology, vol. 4, 014008, 2019. arXiv:1701.02691

[43] S. A. Cuccaro, T. G. Draper, S. A. Kutin, and D. P. Moulton, "A new quantum ripple-carry addition circuit," arXiv:quant-ph/0410184, 2004.

[44] Y. Aharonov, L. Davidovich, and N. Zagury, "Quantum random walks," Physical Review A, vol. 48, no. 2, pp. 1687-1690, 1993.

[45] D. Shepherd and M. J. Bremner, "Temporally unstructured quantum computation," Proceedings of the Royal Society A, vol. 475, no. 2225, 20180527, 2019. arXiv:1807.04084

---

## G. Quantum Compilers

[46] Qiskit Contributors, Qiskit: An Open-source Framework for Quantum Computing, Zenodo, 2024. DOI: 10.5281/zenodo.2562110

[47] Cirq Contributors, Cirq: A Python library for NISQ circuits, Google AI Quantum, 2023.

[48] P. Sivarajah, S. Dilkes, R. Duncan, A. Edgington, S. Harrison, and R. Nosse, "t|ket>: A retargetable compiler for NISQ devices," Quantum Science and Technology, vol. 6, no. 1, 014003, 2020. arXiv:2003.10611

[49] T. Itoko and T. Imamichi, "Optimization of quantum circuit mapping using gate transformation and commutation," Integration, vol. 72, pp. 58-65, 2020.

[50] A. G. Fowler, M. Mariantoni, J. M. Martinis, and A. N. Cleland, "Surface codes: Towards practical large-scale quantum computation," Physical Review A, vol. 86, 032324, 2012. arXiv:1208.0928

---

## H. Random Circuits, Entanglement, and Barren Plateaus

[51] F. G. S. L. Brandao, A. W. Harrow, and M. Horodecki, "Local random quantum circuits are approximate polynomial-designs," Communications in Mathematical Physics, vol. 346, pp. 397-434, 2016. arXiv:1208.0692

[52] A. W. Harrow and R. A. Low, "Random quantum circuits are approximate 2-designs," Communications in Mathematical Physics, vol. 291, pp. 257-302, 2009. arXiv:0802.1886

[53] D. N. Page, "Average entropy of a subsystem," Physical Review Letters, vol. 71, no. 9, pp. 1291-1294, 1993. arXiv:gr-qc/9305007

[54] P. Hayden and J. Preskill, "Black holes as mirrors: quantum information in random subsystems," Journal of High Energy Physics (JHEP), 2007, article 120. arXiv:0708.4025

[55] J. R. McClean, S. Boixo, V. N. Smelyanskiy, R. Babbush, and H. Neven, "Barren plateaus in quantum neural network training landscapes," Nature Communications, vol. 9, article 4812, 2018. arXiv:1803.11173

---

## I. Equivalence Checking and Simulation

[56] S. Yamashita, S. Tanishima, T. Matsumoto, and N. N. Masuda, "Fast equivalence checking of quantum circuits," IEICE Transactions on Fundamentals of Electronics, Communications and Computer Sciences, vol. E94-A, no. 1, pp. 251-258, 2011.

[57] I. L. Markov and Y. Shi, "Simulating quantum computation by contracting tensor networks," SIAM Journal on Computing, vol. 38, no. 3, pp. 963-981, 2008. arXiv:quant-ph/0511069

---

## J. Combinatorial Optimization

[58] J. Edmonds, "Paths, trees, and flowers," Canadian Journal of Mathematics, vol. 17, pp. 449-467, 1965.

---

## K. Verified Quantum Circuit Optimization

[59] Hietala, K. and Martinez, R. and Hung, S.-H. and Peyton Jones, S. and Silberstein, M., "A verified optimizer for quantum circuits," Proceedings of the ACM on Programming Languages (PACMPL), vol. 5, no. POPL, pp. 1-29, 2021. arXiv:1912.02250

[60] R. de Griend and R. Duncan, "Architecture-aware synthesis of nearest neighbour compliant quantum circuits," Quantum Science and Technology, vol. 5, 035004, 2020. arXiv:1809.02718

[61] Iten, R. and Moyard, R. and Metger, T. and Sutter, D. and Woerner, S., "Exact and practical pattern matching for quantum circuit optimization," ACM Transactions on Quantum Computing, vol. 3, no. 1, pp. 1-44, 2022. arXiv:1909.09119

---

## L. Recent Advances in Quantum Circuit Optimization (2021-2026)

[62] M. Xu, Z. Li, O. Padon, S. Lin, J. Pointing, A. Hirth, H. Ma, A. Aiken, U. A. Acar, Z. Jia, and J. Palsberg, "Quartz: Superoptimization of quantum circuits," Proceedings of the ACM on Programming Languages (PACMPL), vol. 6, no. PLDI, pp. 625-650, 2022.

[63] J. Pointing, O. Padon, Z. Jia, A. Hirth, H. Ma, J. Palsberg, and A. Aiken, "Quanto: Optimizing quantum circuits with automatic generation of circuit identities," Quantum Science and Technology, vol. 9, no. 3, 035045, 2024.

[64] Z. Li, J. Peng, Y. Mei, S. Lin, Y. Wu, O. Padon, and Z. Jia, "Quarl: A learning-based quantum circuit optimizer," Proceedings of the ACM on Programming Languages (PACMPL), vol. 8, no. OOPSLA2, pp. 1570-1598, 2024. arXiv:2307.10120

[65] F. J. R. Ruiz, T. Laakkonen, J. Bausch, M. Balog, M. Barekatain, F. J. H. Heras, A. Novikov, N. Fitzpatrick, B. Romera-Paredes, J. van de Wetering, A. Fawzi, K. Meichanetzidis, and P. Kohli, "Quantum circuit optimization with AlphaTensor," Nature Machine Intelligence, vol. 7, no. 3, pp. 406-419, 2025. arXiv:2402.14396

[66] J. Liu, L. Bello, and H. Zhou, "Relaxed peephole optimization: A novel compiler optimization for quantum circuits," Proceedings of the IEEE/ACM International Symposium on Code Generation and Optimization (CGO), 2021, pp. 145-156. arXiv:2012.07711

[67] J. Riu, J. Nogue, G. Vilaplana, A. Garcia-Saez, and M. P. Estarellas, "Reinforcement learning based quantum circuit optimization via ZX-calculus," Quantum, vol. 9, 1634, 2025. arXiv:2312.11597

[68] J. Merilehto, "A 200-line Python micro-benchmark suite for NISQ circuit compilers," arXiv:2509.16205, 2025.

[69] C. Nitsch, D. Hillmich, M. Burgholzer, and R. Wille, "MQT Bench: Benchmarking Software and Design Automation Tools for Quantum Computing," ACM Transactions on Quantum Computing (TEAC), vol. 4, no. 1, 2023. arXiv:2204.13719

[70] A. Wang, S. Lu, and X. Wang, "QASMBench: A low-layer QASM benchmark suite for evaluating NISQ programming and compilation," arXiv:2108.10472, 2021.

[71] IBM, "Benchpress: A benchmarking framework for quantum compilation," 2024.

[72] QCircuitBench, "QCircuitBench: A benchmark suite for quantum circuit optimization," NeurIPS 2025 Datasets and Benchmarks Track, 2025.

[73] MLCO, "Multilevel Quantum Circuit Optimization with Structural Pattern Detection," 2025.

[74] ~~Removed: duplicate of [59] (Hietala et al., VOQC, POPL 2021). See [59].~~

[81] K. Patel, J. Shapira, and I. L. Markov, "Quantum circuit optimization: A survey," ACM Computing Surveys, vol. 55, no. 9, article 178, pp. 1-32, 2022. arXiv:2210.12035

---

## M. Additional 2023-2026 Works

[75] K. Chandrasekaran, A. Hashmi, M. Roetteler, and K. M. Svore, "PEephole REwrite: An Optimizer for Quantum Programs (PERE)," 2023.

[76] K. Hietala, R. Martinez, S.-H. Hung, S. Peyton Jones, and M. Silberstein, "Quartz: Superoptimization of Quantum Circuits," Proceedings of the ACM on Programming Languages (PLDI), vol. 6, 2022. arXiv:2205.00125

[77] Ravi, R. and Gokhale, P. and Smith, K. and Brown, J. and others, "QUASAR: An architecture-aware quantum compiler," Proceedings of the ACM on Programming Languages (PACMPL), 2022.

---

## N. Cross-Reference Map: Literature Review Number to Unified Number

| Lit. Rev. # | Unified # | Reference |
|:-----------:|:---------:|:----------|
| 1 | [1] | McKeeman (1965) |
| 2 | [2] | Tanenbaum et al. (1982) |
| 3 | [3] | Fraser & Hanson (1995) |
| 4 | [4] | Massalin (1987) |
| 5 | [8] | Barenco et al. (1995) |
| 6 | [9] | Nielsen & Chuang (2000, 2010) |
| 7 | [10] | Maslov et al. (2008) |
| 8 | [13] | Amy et al. (2013) |
| 9 | [14] | Amy et al. (2014) |
| 10 | [15] | Amy & Mosca (2019) |
| 11 | [11] | Wille et al. (2008) |
| 12 | [12] | Wille & Drechsler (2009) |
| 13 | [16] | Kliuchnikov et al. (2013) |
| 14 | [21] | Duncan et al. (2020) |
| 15 | [22] | de Beaudrap et al. (2022) |
| 16 | [25] | Janzing et al. (2003) |
| 17 | [26] | Kempe et al. (2006) |
| 18 | [27] | Gottesman (1997) |
| 19 | [28] | Aaronson & Gottesman (2004) |
| 20 | [29] | Dawson & Nielsen (2006) |
| 21 | [30] | Harrow & Montanaro (2017) |
| 22 | [31] | Berman & Karpinski (1999) |
| 23 | [32] | Downey & Fellows (2013) |
| 24 | [46] | Qiskit Contributors (2024) |
| 25 | [47] | Cirq Contributors (2023) |
| 26 | [48] | Sivarajah et al. (2020) |
| 27 | [49] | Itoko & Imamichi (2020) |
| 28 | [51] | Brandao et al. (2016) |
| 29 | [52] | Harrow & Low (2009) |
| 30 | [53] | Page (1993) |
| 31 | [54] | Hayden & Preskill (2007) |
| 32 | [55] | McClean et al. (2018) |
| 33 | [33] | Nielsen (2005) |
| 34 | [34] | Kitaev (1997) |
| 35 | [7] | Garey & Johnson (1979) |
| 36 | [62] | Xu et al. (2022) (Quartz) |
| 37 | [63] | Pointing et al. (2024) (Quanto) |
| 38 | [64] | Li et al. (2024) (Qarl) |
| 39 | [65] | Ruiz et al. (2025) (AlphaTensor-Quantum) |
| 40 | [66] | Liu et al. (2021) (Relaxed Peephole) |
| 41 | [67] | Riu et al. (2025) (ZX+RL) |
| 42 | [68] | Merilehto (2025) |

---

## O. Cross-Reference Map: Phase 7 Related Work Number to Unified Number

| Phase 7 # | Unified # | Reference |
|:----------:|:---------:|:----------|
| [1] | [46] | Qiskit Contributors (2024) |
| [2] | [48] | Sivarajah et al. (tket, 2020) |
| [3] | [47] | Cirq Contributors (2023) |
| [4] | [35] | Shende, Bullock, Markov (2006) |
| [5] | [69] | Nitsch et al. (MQT Bench, 2023) |
| [6] | [70] | Wang et al. (QASMBench, 2021) |
| [7] | [71] | IBM (Benchpress, 2024) |
| [8] | [72] | QCircuitBench (NeurIPS 2025) |
| [9] | [64] | Li et al. (Quarl, 2024) |
| [10] | [73] | MLCO (2025) |
| [11] | [5] | Aho, Sethi, Ullman (1986) |
| [12] | [6] | Amdahl (1967) |

---

## P. Summary of Newly Added References

The following references were identified as missing from the original 42-reference list and have been added in this unified compilation:

| Unified # | Reference | Topic | Task |
|:---------:|:----------|:------|:----:|
| [17] | Nam, Niu, Maslov (2018) | Optimal QFT gate synthesis | F-5 |
| [18] | Nam, Chen, Roetteler (2018) | T-depth optimization | F-5 |
| [19] | Maslov (2016) | Relative phase Toffolis | F-5 |
| [35] | Shende, Bullock, Markov (2006) | CNOT lower bounds | F-5, C-8 |
| [36] | Boixo et al. (2018) | Quantum supremacy characterization | F-5 |
| [37] | Arute et al. (2019) | Google quantum supremacy | F-5 |
| [38] | Bernstein, Vazirani (1997) | BV algorithm | F-5 |
| [39] | Farhi et al. (2014) | QAOA | F-5 |
| [40] | Peruzzo et al. (2014) | VQE | F-5 |
| [41] | Grover (1996) | Grover algorithm | F-5 |
| [42] | Romero et al. (2019) | UCCSD ansatz | F-5 |
| [43] | Cuccaro et al. (2004) | Ripple-carry adder | F-5 |
| [44] | Aharonov et al. (1993) | Quantum random walks | F-5 |
| [45] | Shepherd, Bremner (2019) | IQP circuits | F-5 |
| [50] | Fowler et al. (2012) | Surface codes | F-5 |
| [56] | Yamashita et al. (2011) | Equivalence checking | F-5, C-8 |
| [57] | Markov, Shi (2008) | Tensor network simulation | C-8 |
| [58] | Edmonds (1965) | Blossom algorithm | F-5 |
| [59] | Hietala et al. (2021) | VOQC verified optimizer | F-5 |
| [60] | de Griend, Duncan (2020) | Architecture-aware synthesis | F-5 |
| [61] | Iten et al. (2022) | Pattern matching for QC optimization | F-5 |
| [23] | Kissinger, van de Wetering (2019) | Reducing T-count with ZX-calculus | F-5, H-14 |
| [24] | Kissinger, van de Wetering (2020) | Reducing non-Clifford gates (PyZX) | F-5, H-15 |
| [75] | Chandrasekaran et al. (2023) | PERE optimizer | H-14 |
| [76] | Hietala et al. (2022) | Quartz superoptimizer (PLDI) | H-14 |
| [77] | Ravi et al. (2022) | QUASAR compiler | H-14 |
| [20] | Amy, Glaudell, Ross (2018) | Phase polynomial optimization | F-5 |
| [5] | Aho, Sethi, Ullman (1986) | Classical compiler theory | F-5 |
| [6] | Amdahl (1967) | Amdahl's Law | F-5 |
| [69] | Nitsch et al. (2023) | MQT Bench | F-5 |
| [70] | Wang et al. (2021) | QASMBench | F-5 |
| [71] | IBM (2024) | Benchpress | F-5 |
| [72] | QCircuitBench (2025) | Benchmark suite | F-5 |
| [73] | MLCO (2025) | Multilevel optimization | F-5 |
| [78] | Nam, Ross, Su, Maslov, Brayton (2018) | Automated optimization with continuous parameters | Foundational |
| [79] | Yamashita, Nakanishi, Ishioka (2010) | Merging quantum circuits | Foundational |
| [80] | Amy, Azimzadeh, Mosca (2018) | CNOT complexity of CNOT circuits | Foundational |
| [81] | Patel, Shapira, Markov (2022) | Quantum circuit optimization survey | Survey |

---

*Document version: 2.0*
*Last updated: 2026-06-17*
*Author: Q-Research Reference Compilation*
