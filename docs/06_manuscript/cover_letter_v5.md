# Cover Letter — *Quantum* Submission

> **Target**: Editors, *Quantum* (quantum-journal.org)  
> **Version**: 5.0  
> **Date**: 2026-06-15  
> **Manuscript Title**: "Structural Ceilings and Context-Dependent Optimization in Quantum Circuit Peephole Rewriting"

---

Dear Editors,

We are pleased to submit our manuscript entitled **"Structural Ceilings and Context-Dependent Optimization in Quantum Circuit Peephole Rewriting"** for consideration for publication in *Quantum*.

Quantum circuit compilers universally employ peephole optimization, yet no systematic study has characterized when these local rewriting passes succeed or fail across diverse circuit families and circuit representations. We present the largest empirical benchmark of peephole optimization to date — 53,300 canonical optimizer trials across 15 primary circuit families and 6 optimizer types, with a completed Qiskit production-compiler baseline — revealing sharply divergent optimization profiles and representation-dependent limits of local rewriting.

Our manuscript makes six contributions:

1. **Large-scale empirical benchmark** establishing the first quantitative map of peephole optimization outcomes across 15+ structurally diverse circuit families.
2. **Listing-model dependency analysis** — a formal and preliminary empirical analysis showing that listing order can hide or expose Phase-1 opportunities, with full WCL benchmarking identified as planned follow-up.
3. **Ceiling-aware optimizer smoke study** that uses a structural ceiling proxy to skip futile optimization passes, showing preliminary 1.9x–27x speedup without reduction loss in smoke-mode data.
4. **Compiler mechanism analysis** with a completed Qiskit baseline and planned Cirq/t|ket> extensions, identifying the boundary between local peephole rewriting and production compiler mechanisms.
5. **Circuit-family and listing-model optimization prescriptions** providing the first actionable guide for compiler developers.
6. **Supporting theoretical framework** with formal bounds including a bounded INSERTION-cascade result and a corrected Bernstein–Vazirani Phase-2b advantage theorem.

We believe this work is well suited to *Quantum* for several reasons. The journal's commitment to open-access publication and reproducibility aligns directly with our emphasis on transparent, verifiable research at scale. Our reproducibility artifacts include:

- **Comprehensive test suite** of 149 unit tests and 57 statistical tests covering all optimization algorithms
- **Docker image** and **CI/CD pipeline** ensuring one-command environment reproduction
- **53,300 canonical optimizer trials** with SHA-256 verified data provenance, plus held-out/pass-isolation artifacts
- **Complete reproduction pipeline** (`reproduce_all.py`) enabling end-to-end replication of all reported results
- **All raw data, analysis scripts, and supplementary materials** publicly available

The manuscript is self-contained at 25–28 pages of main text with 15–22 pages of supplementary materials, and we believe it will be of broad interest to the *Quantum* readership, spanning quantum software engineering, compiler development, and circuit optimization.

We confirm that this manuscript has not been published elsewhere and is not under consideration at another journal. All authors have approved the manuscript and agree with its submission to *Quantum*.

**Suggested Reviewers**:

1. **Dr. Dmitri Maslov**  
   Chief Software Architect, IBM Quantum  
   Expertise: Quantum circuit optimization, template matching, quantum compilation  
   dmitri.maslov@ibm.com

2. **Prof. Alexandru Paler**  
   Department of Computer Science, Technical University of Munich  
   Expertise: Quantum circuit synthesis, quantum error correction, compiler optimization  
   alexandru.paler@tum.de

3. **Dr. Seyon Sivarajah**  
   Senior Research Scientist, Quantinuum (formerly Cambridge Quantum)  
   Expertise: Quantum compiler design, t|ket> development, peephole optimization  
   seyon.sivarajah@quantinuum.com

We thank the editors for their consideration and look forward to the review process.

Sincerely,

[Author Names]  
[Corresponding Author]  
[Corresponding Author Affiliation and Contact]

---

*Document version: 5.0*  
*Last updated: 2026-06-15*  
*Author: Q-Research Manuscript Team*
