# SOTA Benchmark Protocol: Fair Comparison of Quantum Circuit Optimizers

> **Document**: Unified protocol for comparing the Q-research framework against SOTA tools
> **Date**: 2026-07-17
> **Target**: Reproducible, fair, and publication-grade comparison

---

## 1. Unified Benchmark Suite

### 1.1 Circuit Families (15 families)

All comparisons use the project's standard 15-circuit-family extended suite (`generate_extended_suite` in `src/circuits/real_benchmarks.py`):

| # | Family | Type | Circuit ID Pattern | Description |
|---|--------|------|-------------------|-------------|
| 1 | QFT | Algorithmic | `qft_{n}` | Quantum Fourier Transform, no final swaps |
| 2 | GHZ | Algorithmic | `ghz_{n}` | GHZ state preparation, linear CNOT chain |
| 3 | CNOT | Algorithmic | `cnot_chain_{n}` | CNOT chain with adjacent cancellable pairs |
| 4 | Oracle (BV) | Algorithmic | `bv_{n}` | Bernstein-Vazirani oracle, secret string encoded |
| 5 | QAOA | Variational | `qaoa_line_{n}` | Line-graph QAOA, 2 reps, bound numeric angles |
| 6 | VQE | Variational | `vqe_twolocal_{n}` | TwoLocal VQE ansatz, Ry+Rz+CX, 2 reps |
| 7 | HardwareEfficient | Variational | `hardware_eff_{n}` | Alternating Ry/Rz + CX entanglers, 2 layers |
| 8 | Grover | Algorithmic | `grover_{n}` | Single Grover iteration, random marked state |
| 9 | Adder | Arithmetic | `adder_{n}` | Ripple-carry adder, random inputs |
| 10 | QuantumWalk | Algorithmic | `qwalk_{n}` | Discrete-time quantum walk on cycle, 3 steps |
| 11 | IQP | Algorithmic | `iqp_{n}` | IQP circuit, 3 diagonal layers |
| 12 | RandomClifford | Random | `clifford_{n}` | Random Clifford circuit, depth=10, {H,S,CX} |
| 13 | SurfaceCode | Error Correction | `surface_code_{n}` | Surface-code X-stabilizer syndrome extraction |
| 14 | UCCSD_inspired | Variational | `uccsd_{n}` | Parameterized ansatz inspired by UCCSD |
| 15 | HaarRandom | Random | `haar_{n}` | Haar-random unitary, exact synthesis (n <= 4) |

### 1.2 Qubit Counts

- **Standard set**: n in {4, 6, 8} — matches E20 controlled comparison
- **Extended set**: n in {3, 4, 5, 6, 7, 8, 9, 10} — for scaling analysis
- **Large-scale set**: n in {12, 15, 20} — for scalability (scalable families only)
- **Haar subset**: n in {2, 3, 4} — exponential synthesis cost

### 1.3 Random Trials

- **Standard**: 10 independent random trials per (family, n_qubits) cell
- **Smoke test**: 1 trial per cell for quick validation
- **Seed**: Base seed = 42; per-family seed offset applied (see `generate_extended_suite`)

### 1.4 QASM Export

All circuits are exported to OpenQASM 2.0 (`qiskit.qasm2.dumps`) to provide a tool-agnostic interchange format. This ensures every SOTA tool receives identical input circuits.

---

## 2. Unified Metrics

### 2.1 Primary Metrics

| Metric | Symbol | Definition | Measurement |
|--------|--------|-----------|-------------|
| T-gate count | `t_count` | Number of T and T-dagger gates in the circuit | `sum(1 for inst in circuit.data if inst.operation.name in {"t", "tdg"})` |
| S-gate count | `s_count` | Number of S and S-dagger gates | `sum(1 for inst in circuit.data if inst.operation.name in {"s", "sdg"})` |
| CNOT count | `cnot_count` | Number of CX/CNOT gates | `sum(1 for inst in circuit.data if inst.operation.name in ("cx", "cnot"))` |
| Two-qubit gate count | `two_q_count` | All 2-qubit gates (CX, CZ, etc.) | `sum(1 for inst in circuit.data if inst.operation.num_qubits == 2)` |
| Circuit depth | `depth` | Critical path length | `circuit.depth()` |
| Total gate count | `gate_count` | Total number of gate operations | `circuit.size()` |
| Wall-clock runtime | `runtime_s` | Elapsed time in seconds (includes conversion overhead) | `time.time()` delta |

### 2.2 Derived Metrics

| Metric | Formula |
|--------|--------|
| Gate reduction (%) | `100 * (1 - optimized_gate_count / baseline_gate_count)` |
| T-count reduction (%) | `100 * (1 - optimized_t_count / baseline_t_count)` |
| CNOT reduction (%) | `100 * (1 - optimized_cnot_count / baseline_cnot_count)` |
| Depth reduction (%) | `100 * (1 - optimized_depth / baseline_depth)` |
| Average gate fidelity | `F_avg = (|Tr(U1^dagger . U2)|^2 + d) / (d^2 + d)` where `d = 2^n` |

### 2.3 Fidelity Protocol

- Exact unitary comparison for n <= 8 (Hilbert space dimension <= 256)
- For n > 8: mark fidelity as "unavailable" (too expensive to compute)
- Fidelity threshold for "success": F_avg >= 0.999
- Record `fidelity_source`: "exact" | "unavailable" | "error"

---

## 3. Unified Environment

### 3.1 Hardware

- **OS**: Windows (native, no WSL)
- **RAM**: 16 GB
- **GPU**: None
- **CPU**: Multi-core x86-64

### 3.2 Software Stack

| Package | Version | Role |
|---------|---------|------|
| Python | 3.x | Runtime |
| qiskit | 2.4.1 | Circuit construction + transpile baseline |
| pytket | 2.18.0 | t|ket> FullPeepholeOptimise |
| pytket-qiskit | 0.77.0 | Qiskit <-> t|ket> conversion |
| cirq | 1.6.1 | Cirq optimization |
| scipy | 1.13.1 | Statistical tests |
| numpy | 1.26.4 | Numerical computation |
| pandas | 2.2.2 | Data handling / CSV output |

### 3.3 Runtime Measurement Protocol

- **Warm-up**: Run each tool once on a dummy circuit before timing (cache/JIT effects)
- **Timing**: Measure wall-clock time per circuit, including conversion overhead
- **Timeout**: 120 seconds per circuit per tool; record "timeout" status
- **Repetition**: 10 trials with different random seeds; report median + IQR
- **Process isolation**: Each tool run in a fresh Python subprocess to prevent cross-contamination of global state

---

## 4. Fairness Constraints

### 4.1 Default Configuration

Each tool is run with its **default configuration** as documented in its official documentation:
- **Qiskit**: `transpile(circuit, optimization_level=3, seed_transpiler=42)` (level 3 = maximum optimization)
- **t|ket>**: `DecomposeBoxes().apply()` then `FullPeepholeOptimise().apply()` (default parameters)
- **Cirq**: `drop_empty_moments` + `optimize_for_target_gateset(CZTargetGateset)` + `eject_z` + `merge_single_qubit_gates_to_phased_x_and_z` + `drop_empty_moments`
- **VOQC** (if available): Default pass sequence from `pyvoqc.optimize()`
- **Quartz** (if available): Default ECC set for the matching gate set, default cost function (gate count)

### 4.2 Tuned Configuration

Each tool is also run with a **tuned configuration** that maximizes its performance:
- **Qiskit**: Level 3 + custom coupling map (heavy-hex, dynamic sizing) + `basis_gates=["cx","id","rz","sx","x"]`
- **t|ket>**: `FullPeepholeOptimise` with `target_2qb_gate=CZ` + `contextual_simplification` + `PeepholeOptimise` (2 passes)
- **Cirq**: Additional `CZTargetGateset` with `max_num_single_qubit_gates_to_merge=5`
- **Custom prototype**: Phase-1 (Greedy) + Phase-2a (CommutationRewriter) + Phase-2b (template matcher, fixture-scale)

### 4.3 Fairness Modes

Following the E12 design, all production compiler comparisons run in **two modes**:

1. **Hardware-realistic mode** (with coupling map): Qiskit solves routing + optimization. This is harder than the custom optimizer (optimization only). Report separately.
2. **Fair mode** (no coupling map): Qiskit solves optimization only (no routing). This matches the scope of the custom peephole optimizer. **This is the primary comparison mode.**

For t|ket> and Cirq, the coupling-map constraint is not applicable in the same way (t|ket> routing is optional; Cirq does not impose connectivity by default). The fair mode is the default for these tools.

### 4.4 Input Circuit Standardization

- All circuits originate from `generate_extended_suite(mode="full", seed=42)`
- Circuits are exported to OpenQASM 2.0 before passing to each tool
- Each tool receives the **identical QASM string** for the same (family, n, seed) tuple
- Parameter binding: All parameterized circuits are bound with `materialize_circuit(qc, parameter_seed=42)` before export

### 4.5 Gate Set Normalization

- **Input gate set**: {H, T, Tdg, S, Sdg, Rx, Ry, Rz, X, Y, Z, CNOT, CZ, CCX (Toffoli)}
- **Post-processing**: Each tool's output is normalized to a common gate set for fair metric comparison:
  - Decompose CCX/Toffoli into {H, T, Tdg, CNOT} (standard 7-gate decomposition)
  - Do NOT re-optimize after normalization (report metrics on the tool's raw output, then normalized)
- **Reporting**: Report both raw-tool-output metrics and normalized metrics

---

## 5. Statistical Protocol

### 5.1 Tests

| Test | Use Case | Implementation |
|------|----------|----------------|
| Mann-Whitney U | Compare two independent groups (e.g., custom vs t|ket>) across circuits | `scipy.stats.mannwhitneyu(group_a, group_b, alternative="two-sided")` |
| Wilcoxon signed-rank | Compare paired measurements (same circuit, two tools) | `scipy.stats.wilcoxon(group_a, group_b)` |
| Holm-Bonferroni correction | Correct for multiple comparisons across 15 families | Apply Holm step-down procedure to p-values from 15 family-level tests |
| Cliff's delta | Effect size (non-parametric) | Custom implementation (negligible/small/medium/large thresholds) |

### 5.2 Significance Threshold

- Per-comparison alpha = 0.05
- After Holm-Bonferroni correction for 15 families: effective alpha = 0.05/15 = 0.00333 (most stringent)
- Report both raw p-values and Holm-corrected significance flags

### 5.3 Sample Size

- 15 families x 3 qubit sizes x 10 trials = 450 data points per tool (minimum)
- With 4-6 tools: 1,800-2,700 total data points
- Statistical power: For Mann-Whitney U with n=450 per group, minimum detectable effect size (Cliff's delta) ~0.15 at alpha=0.00333, power=0.80

---

## 6. Output Format

### 6.1 CSV Schema (per-tool, per-run)

```
tool,circuit_family,circuit_id,n_qubits,trial,seed,
t_count,s_count,cnot_count,two_q_count,depth,gate_count,
optimized_t_count,optimized_s_count,optimized_cnot_count,optimized_two_q_count,
optimized_depth,optimized_gate_count,
gate_reduction_pct,t_count_reduction_pct,cnot_reduction_pct,depth_reduction_pct,
fidelity,fidelity_source,runtime_seconds,compiler_status,tool_config,
timestamp_utc
```

### 6.2 Aggregated CSV Schema (per-family, per-tool)

```
tool,circuit_family,n_qubits,n_trials,
mean_gate_reduction,median_gate_reduction,iqr_gate_reduction,
mean_t_count_reduction,mean_cnot_reduction,mean_depth_reduction,
mean_runtime_seconds,fidelity_pass_rate,
mann_whitney_p_vs_custom,wilcoxon_p_vs_custom,cliffs_delta_vs_custom,
holm_significant
```

### 6.3 File Naming

```
data/v6/sota_benchmark/
  raw/
    {tool}_{config}_{run_id}.csv        # e.g., tket_default_20260717_120000.csv
  aggregated/
    sota_comparison_aggregated.csv       # all tools, all families
  metadata/
    {tool}_{config}_metadata.json        # provenance per run
```

---

## 7. Tool-Specific Adaptation Notes

### 7.1 t|ket> Adaptation

- **Conversion**: Qiskit -> `qiskit_to_tk()` -> `DecomposeBoxes().apply()` -> `FullPeepholeOptimise().apply()` -> `tk_to_qiskit()`
- **Timeout**: 60s per circuit (E20 showed timeouts at n > 6); record "timeout" status
- **Metric extraction**: After conversion back to Qiskit, count gates using the unified metric functions

### 7.2 Qiskit Adaptation

- **Fair mode**: `transpile(circuit, optimization_level=3, seed_transpiler=42)` (no coupling map, no basis gates)
- **Hardware mode**: `transpile(circuit, optimization_level=3, seed_transpiler=42, coupling_map=..., basis_gates=...)`
- **Both modes run and saved separately**

### 7.3 Cirq Adaptation

- **Conversion**: Qiskit -> OpenQASM2 -> Cirq -> optimize -> Cirq QASM -> Qiskit
- **Optimization pipeline**: As defined in E20 (`_cirq_optimize`)

### 7.4 VOQC Adaptation (if available)

- **Conversion**: Qiskit -> OpenQASM2 -> `pyvoqc.VOQC().optimize(circuit_qasm)` -> QASM output -> Qiskit
- **Gate set**: VOQC works on {H, X, T, Tdg, CNOT, Rz}; may require gate set translation
- **Fallback**: If VOQC installation fails, mark as "unavailable" and proceed with remaining tools

### 7.5 Quartz Adaptation (if build succeeds)

- **Input**: OpenQASM 2.0 file
- **ECC set**: Use pre-generated ECC set for Nam gate set (closest to our gate set)
- **Cost function**: Gate count (default)
- **Qubit limit**: n <= 4 for ECC-based search (memory constraint)
- **Fallback**: If build fails, use textual comparison with published results

### 7.6 Custom Prototype Optimizers

- **Phase-1 (Greedy)**: `GreedyGateCancellation().optimize(circuit, target=circuit)`
- **Phase-2a (Hybrid)**: `HybridCommuteRewrite().optimize(circuit, target=circuit)`
- **Ceiling-aware**: `CeilingAwareOptimizer().optimize(circuit, target=circuit)` (E21, exploratory)

---

## 8. Reproducibility Checklist

- [x] Fixed random seed (42) for all circuit generation
- [x] Fixed random seed (42) for all compiler-internal randomness (seed_transpiler=42)
- [x] All input circuits exported to QASM for verification
- [x] All tool versions recorded in metadata.json
- [x] Script SHA-256 hashes recorded for provenance
- [x] Environment (Python version, package versions) recorded
- [x] Per-circuit timeout enforced (120s)
- [x] Both default and tuned configurations run
- [x] Both fair (no coupling) and hardware (with coupling) modes run for Qiskit
- [x] 10 random trials per (family, n_qubits) cell
- [x] Statistical tests with Holm-Bonferroni correction applied
- [x] CSV output with full schema for downstream analysis

---

## 9. Execution Order

1. Generate benchmark suite: `generate_extended_suite(mode="full", seed=42)`
2. Export all circuits to QASM files in `data/v6/sota_benchmark/qasm/`
3. Run t|ket> (Tier 1): `python experiments/sota_tk_comparison.py --mode full`
4. Run Qiskit fair mode (Tier 1): `python experiments/e12_compiler_baseline/run.py --mode full --no-coupling-map`
5. Run Cirq (Tier 1): via `sota_benchmark.py --tool cirq`
6. Install and run VOQC (Tier 2): `python experiments/sota_benchmark.py --tool voqc`
7. Install and run Micro-Benchmark Suite (Tier 2): cross-validation
8. Attempt Quartz build (Tier 3): if successful, run on n <= 4 subset
9. Aggregate all results: `python experiments/sota_benchmark.py --aggregate`
10. Run predictive advantage analysis: `python experiments/predictive_advantage.py`
11. Generate tables and figures: `python analysis/generate_figures.py --sota`

---

*Protocol version 1.0.0 | 2026-07-17*
