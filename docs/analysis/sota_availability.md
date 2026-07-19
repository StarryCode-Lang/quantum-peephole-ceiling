# SOTA Tool Availability Assessment

> **Date**: 2026-07-17
> **Context**: Q-research project SOTA comparison design
> **Environment**: Windows, 16 GB RAM, no GPU, Python 3.x

---

## 1. Summary Availability Matrix

| Tool | Open Source | Language | pip Install | Windows Support | GPU Required | RAM Footprint | Feasibility (Win/16 GB/no GPU) | Priority |
|------|:-----------:|----------|:------------:|:----------------:|:------------:|:-------------:|:------------------------------:|:--------:|
| **t\|ket> (pytket)** | Yes | Python/C++ | Yes (`pytket`, `pytket-qiskit`) | Yes | No | <2 GB | **Already installed** (v2.18.0) | P0 (baseline) |
| **Qiskit transpile** | Yes | Python/C++ | Yes (`qiskit`) | Yes | No | <2 GB | **Already installed** (v2.4.1) | P0 (baseline) |
| **Cirq** | Yes | Python | Yes (`cirq`) | Yes | No | <2 GB | **Already installed** (v1.6.1) | P0 (baseline) |
| **VOQC (pyvoqc)** | Yes (MIT) | OCaml/Python | Partial (`install.sh`) | Unverified | No | <1 GB | **Medium** — requires OCaml toolchain | P1 |
| **Micro-Benchmark Suite** | Yes | Python | Yes (`pip install -r requirements.txt`) | Yes | No | <1 GB | **High** — pure Python, Qiskit/t\|ket>/Cirq/Braket | P1 |
| **Quartz** | Yes (Apache 2.0) | C++/Python | No (CMake build) | Yes (MSVC) | No | 4-8 GB (ECC gen) | **Medium** — heavy C++ build, ECC generation ~hours | P2 |
| **Quarl** | Yes (Apache 2.0) | C++/Python | No (fork of Quartz) | Yes (MSVC) | **Yes (training)** | 8-16 GB (RL) | **Low** — RL training needs GPU; inference possible but build is heavy | P3 |
| **AlphaTensor-Quantum** | Partial | Python/JAX | Unverified | Unverified | Yes (TPU/GPU) | >16 GB | **Not feasible** — requires TPU/GPU, large memory | P3 (skip) |

---

## 2. Detailed Assessment per Tool

### 2.1 t|ket> (pytket) — ALREADY INTEGRATED

- **Repository**: https://github.com/CQCL/tket
- **pip package**: `pytket` (v2.18.0 installed), `pytket-qiskit` (v0.77.0 installed)
- **Key pass**: `FullPeepholeOptimise` — applies Clifford simplification, gate cancellation, commutation-based reordering, single-qubit rotation merging, template matching, and phase polynomial synthesis
- **Integration status**: Fully integrated in E20 (`experiments/e20_multi_compiler_full/run.py`). Conversion pipeline: Qiskit -> `qiskit_to_tk` -> `DecomposeBoxes` -> `FullPeepholeOptimise` -> `tk_to_qiskit`.
- **Limitation**: t|ket> optimizer timeouts on circuits >6 qubits in E20 (1,070 rows, n <= 6 for t|ket>). For the SOTA benchmark, we constrain t|ket> to n <= 8 with per-circuit timeout.
- **Verdict**: **Primary SOTA baseline.** No additional installation required.

### 2.2 Qiskit transpile — ALREADY INTEGRATED

- **Repository**: https://github.com/Qiskit/qiskit
- **pip package**: `qiskit` (v2.4.1 installed)
- **Key passes**: 4 optimization levels (0-3); `TemplateOptimization`, `CommutativeCancellation`, `ConsolidateBlocks`, `UnitarySynthesis`
- **Integration status**: Fully integrated in E12 (`experiments/e12_compiler_baseline/run.py`) with both coupling-map and no-coupling-map (fair comparison) modes.
- **Verdict**: **Primary SOTA baseline.** No additional installation required.

### 2.3 Cirq — ALREADY INTEGRATED

- **Repository**: https://github.com/quantumlib/Cirq
- **pip package**: `cirq` (v1.6.1 installed)
- **Key passes**: `optimize_for_target_gateset(CZTargetGateset)`, `eject_z`, `merge_single_qubit_gates_to_phased_x_and_z`
- **Integration status**: Fully integrated in E20. Conversion via OpenQASM2 round-trip (Qiskit -> QASM2 -> Cirq -> QASM2 -> Qiskit).
- **Limitation**: Cirq evaluated on n <= 8 in E20 due to conversion complexity for large circuits.
- **Verdict**: **Supplementary SOTA baseline.** No additional installation required.

### 2.4 VOQC (pyvoqc)

- **Repository**: https://github.com/inQWIRE/pyvoqc (Python wrapper); https://github.com/inQWIRE/SQIR (Coq formalization); https://github.com/inQWIRE/mlvoqc (OCaml library)
- **License**: MIT
- **Language**: OCaml (extracted from Coq proofs), Python wrapper
- **Installation**:
  1. Install OCaml and opam: `opam init` + `eval $(opam env)`
  2. Pin the VOQC library: `opam pin voqc https://github.com/inQWIRE/mlvoqc.git#mapping`
  3. Run `./install.sh` (builds OCaml lib with dune, installs Python package via pip)
- **Windows feasibility**: OCaml toolchain (opam) is available on Windows via WSL or native OCaml installer. The `install.sh` script is Unix-style but can be adapted. Native Windows OCaml has improved significantly; `opam` on Windows is supported via `ocaml-platform` or `diskuv-ocaml`.
- **GPU**: Not required. VOQC is a verified, rule-based optimizer.
- **RAM**: <1 GB typical.
- **Key optimizations**: Matsumoto-Amy T-parity, single-qubit gate merging, Hadamard synthesis, Rz/Rx synthesis, Clifford+T normal form
- **Limitation**: Not a simple `pip install pyvoqc` — requires building OCaml. Not tested on this Windows environment. The `#mapping` branch is required.
- **Verdict**: **Medium feasibility.** Worth attempting installation via WSL or diskuv-ocaml. If installation fails, document the failure and use t|ket> as the peephole SOTA proxy. VOQC's optimizations are partially subsumed by t|ket>'s `FullPeepholeOptimise`.

### 2.5 Quartz

- **Repository**: https://github.com/quantum-compiler/quartz
- **License**: Apache 2.0
- **Paper**: Xu et al., "Quartz: Superoptimization of Quantum Circuits," PLDI 2022 (not OSDI as sometimes cited)
- **Language**: C++ (core), Python (bindings/verifier), OpenQASM (circuit files)
- **Installation** (Windows):
  1. Visual Studio Community 2019+ (MSVC build tools)
  2. CMake 3.16+
  3. Conda: `conda env create --name quartz --file env.yml`
  4. `conda install openmp`
  5. `mkdir build && cd build && cmake ..`
  6. Open `Quartz.sln` in Visual Studio, Build Solution (F7)
  7. Optional Python: `cd ../python && python setup.py build_ext --inplace install`
- **GPU**: Not required for optimization (only for some RL extensions).
- **RAM concern**: ECC (Equivalent Circuit Class) set generation is the bottleneck. Generating ECC sets for a new gate set can take hours and requires significant memory. Pre-generated ECC sets for common gate sets (e.g., Nam, IBM, Rigetti, SK) are available in the repository.
- **Windows feasibility**: Build system supports MSVC/CMake on Windows. The main challenge is the C++ build complexity and ECC generation time. With 16 GB RAM, ECC generation for small qubit counts (n <= 4) is feasible.
- **Key capability**: Automatically generates circuit identities via ECC, then applies cost-based backtracking search. Achieves significant T-gate reduction on arithmetic circuits.
- **Limitation**: Heavy C++ build; ECC generation for new gate sets is time-consuming. Input format is OpenQASM 2.0. Pre-generated ECC sets may not cover the project's gate set exactly.
- **Verdict**: **Medium feasibility.** If the C++ build succeeds, Quartz can run on pre-generated ECC sets for n <= 4-6 qubits. This would be the strongest non-pip SOTA comparison. If build fails, use the manuscript's textual analysis of Quartz results as a fallback.

### 2.6 Quarl

- **Repository**: https://github.com/quantum-compiler/Quarl (fork of Quartz)
- **License**: Apache 2.0
- **Paper**: Li et al., "Quarl: A Learning-Based Quantum Circuit Optimizer," 2024
- **Language**: C++ (Quartz core), Python (RL training), OpenQASM (circuits)
- **Installation**: Same as Quartz (fork of Quartz) plus RL training dependencies (PyTorch, etc.)
- **GPU**: **Required for RL training.** The RL model (graph neural network) needs GPU for training. Pre-trained models could potentially run inference on CPU, but no pre-trained model checkpoints are published.
- **RAM**: 8-16 GB for RL training.
- **Windows feasibility**: Low. Same C++ build challenges as Quartz, plus GPU requirement for training. The RL training pipeline has not been tested on Windows.
- **Key capability**: Deep RL with GNN for circuit optimization, learns rotation merging strategies. Outperforms Quartz on some benchmarks.
- **Limitation**: No pre-trained model published; RL training requires GPU. The environment (16 GB RAM, no GPU) makes training infeasible. Even inference would require a pre-trained model.
- **Verdict**: **Low feasibility.** Cannot train without GPU. If pre-trained models become available, CPU inference is possible but currently no checkpoints are published. Recommend **textual comparison** citing Quarl's reported results on overlapping circuit families rather than direct execution.

### 2.7 AlphaTensor-Quantum

- **Repository**: Code not publicly released (as of assessment date)
- **Paper**: Ruiz et al., "Quantum circuit optimization with AlphaTensor," Nature Machine Intelligence, 2025
- **Language**: Python/JAX (inferred from DeepMind AlphaTensor lineage)
- **GPU**: **Required.** AlphaTensor uses deep RL with TPU/GPU for tensor decomposition. The original AlphaTensor required TPU v4.
- **RAM**: >16 GB for training. Large tensor decomposition problems require significant memory.
- **Windows feasibility**: Not feasible. No public code, requires GPU/TPU, and the underlying AlphaTensor framework is resource-intensive.
- **Key capability**: T-count optimization via tensor decomposition over F_2. Achieves 37-47% T-gate reduction on arithmetic circuits (adders, multipliers).
- **Limitation**: Not open source. Not pip installable. Requires GPU/TPU. The results are specific to T-count (not gate count or depth), making direct metric comparison difficult.
- **Verdict**: **Not feasible.** Skip direct execution. Recommend **textual comparison** citing AlphaTensor-Quantum's reported T-count reductions on arithmetic circuits (Adder family overlaps with our benchmark). Note metric difference: ATQ optimizes T-count; our framework measures gate count, CNOT count, and depth.

### 2.8 Micro-Benchmark Suite (Merilehto 2025)

- **Repository**: https://github.com/juhanimerilehto/microbench
- **License**: Unspecified (publicly available on GitHub)
- **Language**: Python 100%
- **Installation**: `pip install -r microbench/requirements.txt` or `conda env create -f microbench/environment.yml`
- **Dependencies**: `qiskit >= 0.46`, `qiskit_braket_provider`, optional `pytket` and `cirq`
- **GPU**: Not required.
- **RAM**: <1 GB.
- **Windows feasibility**: **High.** Pure Python, pip installable, same compiler stack already installed.
- **Key capability**: Benchmarks 6 self-generated circuits (Ripple-Carry Adder, QFT, Grover, Hardware-Efficient Ansatz, Random Clifford, Modular Multiplication) at 3-8 qubits across Qiskit, t|ket>, Cirq, and Amazon Braket. Measures depth, 2Q gate count, wall-clock time, peak RSS.
- **Limitation**: Only 6 circuits vs our 15 families. Uses its own circuit generators (not our standard suite). For fair comparison, we should run our 15-family suite through microbench's measurement harness AND run microbench's 6 circuits through our analysis framework.
- **Verdict**: **High feasibility.** Directly pip installable. Overlapping circuit families (QFT, Grover, Adder, Random Clifford, Hardware-Efficient) enable cross-validation. Recommend **integration** of microbench as a secondary benchmark and cross-validation tool.

---

## 3. Recommended Comparison Tool Set

Based on the availability assessment, the recommended SOTA comparison tool set is:

### Tier 1: Direct Execution (P0 — already available)
1. **t|ket> FullPeepholeOptimise** — primary peephole SOTA (already in E20)
2. **Qiskit transpile (levels 0-3)** — primary production compiler (already in E12)
3. **Cirq** — supplementary production compiler (already in E20)

### Tier 2: Direct Execution (P1 — installable with effort)
4. **Micro-Benchmark Suite** — cross-validation with 6 overlapping families; pure Python, pip installable
5. **VOQC (pyvoqc)** — verified optimizer; requires OCaml toolchain; if installation succeeds, adds a formally verified SOTA perspective

### Tier 3: Textual Comparison (P2-P3 — not directly executable)
6. **Quartz** — attempt C++ build; if successful, run on pre-generated ECC sets for n <= 4. If build fails, cite Quartz's reported T-gate reductions on Nam/IBM benchmarks
7. **Quarl** — cite published results; no GPU for RL training. Note RL approach as contrast to our structural approach
8. **AlphaTensor-Quantum** — cite published T-count results on arithmetic circuits; note metric difference (T-count vs gate count)

---

## 4. Fallback Strategy

For tools that cannot be directly executed (Quarl, AlphaTensor-Quantum, potentially Quartz/VOQC):

1. **Textual comparison table**: Reproduce published results from each tool's paper on overlapping circuit families, clearly citing the source.
2. **Metric normalization**: Convert reported metrics to our unified metric set (T-count, CNOT count, depth, total gate count, runtime) where the paper provides sufficient detail.
3. **Fairness caveat**: Explicitly note that cross-paper comparisons may use different circuit instances, gate sets, and qubit counts. Mark these as "literature-cited, not directly reproduced."
4. **Predictive advantage framing**: For tools we cannot run, our framework's structural predictions (ceiling classification, Phase-2 advantage prediction) can be validated against their published results, demonstrating the "predictive advantage" strategy without requiring direct execution.

---

## 5. Environment Constraints Summary

| Constraint | Impact |
|-----------|--------|
| Windows (no WSL guaranteed) | Quartz/Quarl C++ build needs MSVC; VOQC needs OCaml/opam |
| 16 GB RAM | ECC generation for Quartz limited to n <= 4; Quarl RL training infeasible |
| No GPU | Quarl RL training infeasible; AlphaTensor-Quantum infeasible |
| Python-first | t|ket>, Qiskit, Cirq, Micro-Benchmark all pip-installable; VOQC partially |
| Existing stack | Qiskit 2.4.1, pytket 2.18.0, Cirq 1.6.1, scipy 1.13.1 already installed |

---

*This assessment was conducted on 2026-07-17. Tool availability may change as new versions are released.*
