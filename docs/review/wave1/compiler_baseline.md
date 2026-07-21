# Wave-1 Completion Report: Industrial Compiler Baseline (SOTA)

> **Worker**: Benchmark engineer — compiler baselines
> **Date**: 2026-07-20
> **Status**: COMPLETE. All deliverables produced from real runs or pre-existing
> canonical data; no fabricated numbers. No new long-running benchmarks were started
> after the wrap-up instruction.

---

## 1. What was done

### 1.1 Coverage audit (reuse-first; only true gaps filled)

Audited all existing SOTA coverage before running anything. Findings and actions:

| Tool / config | Pre-existing coverage | Gap action |
|---|---|---|
| Qiskit L3 ("default") | v6 canonical, 520 rows, n = 4–10, 10 trials | reused, no rerun |
| Qiskit L0/L1/L2 | absent from v6 (E12 legacy had ~1 trial/cell, old schema) | **ran on 2026-07-20**: 3 × 520 rows, n = 4–10, 10 trials; sequential rerun for clean timing after a parallel first pass (outputs verified bit-identical) |
| Cirq default | v6 canonical had 100/520 error rows and a silently skipped pipeline step (bugs, Sec. 1.3) | fixed 2 bugs and reran once: 520/520 ok |
| t\|ket> FPO | v6 canonical, 440 rows, full families n <= 5, partial n = 6–7 | reused, no rerun; n <= 6 limitation documented |
| Prototype (custom) | v6 smoke only (21 rows, 1 trial) | **not run** (out of scope; prototype workstream). Tables use E15 full-scale data (994 rows) filtered to n in {4,6,8} |

Machine-readable audit: `data/v6/sota_benchmark/derived/coverage_audit.csv`.

### 1.2 Environment record

`data/v6/sota_benchmark/metadata/hardware_environment.json`, measured with
`platform`/`psutil`/`/proc/cpuinfo`: i7-11370H @ 3.30 GHz, 4C/8T, 15.8 GiB RAM,
Windows 11 26200, Python 3.12.12, qiskit 2.4.1, pytket 2.18.0, pytket-qiskit 0.77.0,
cirq 1.6.1, numpy 1.26.4, scipy 1.13.1, pandas 2.2.2; protocol constants (seed 42
+ 1000/trial, 10 trials/cell, timeout 120 s / 60 s tket, fidelity exact n <= 8,
threshold 0.999).

### 1.3 Bugs found and fixed (provenance-critical)

1. `experiments/sota_benchmark.py::cirq_optimize` called
   `optimize_for_target_gateset(..., target_gateset=...)`; cirq 1.6.1 renamed the
   keyword (`gateset=`), the bare `except` swallowed the TypeError, and the
   CZTargetGateset step **never ran** in the 2026-07-18 canonical Cirq data. Fixed;
   Cirq rerun produced protocol-conformant data (CNOT 0→100%, RandomClifford
   47.4→63.1%, QuantumWalk −382.6→−4547.4%).
2. Cirq QASM export uses `sx`/`sxdg`, which `qiskit.qasm2`'s builtin qelib1 set lacks;
   100 rows failed re-import. Fixed by injecting the standard qelib1 gate definitions;
   zero import errors in the rerun.
3. Aggregation canonical selection parsed the run date into the (tool, config) key,
   mixing smoke/buggy/fixed Cirq runs into one aggregate. Fixed parser
   (`{tool}_{config}_{date}_{time}`, config may contain underscores).
4. Fidelity pass rate now computed over exact-fidelity rows only (n > 8 rows no longer
   counted as failures); success rate computed over all rows including errors.
5. All overwrite paths made atomic (tmp + `os.replace`) with timestamped backups.

### 1.4 Deliverables

- **Manuscript fragment**: `docs/manuscript/sections/sota_table_fragment.md` —
  auto-generated, 5 tables: S1 main comparison (family × Prototype/Qiskit L3/Cirq/
  t|ket>), S2 Qiskit L0–L3 progression, S3 wall-clock runtime, S4 correctness/reliability,
  S5 QuantumWalk blowup detail. Regenerate with `experiments/generate_sota_tables.py`.
- **Results document**: `docs/results/sota_compiler_benchmark.md` — coverage audit,
  environment, bug provenance, leading finding, QuantumWalk mechanism, L0–L3 findings,
  runtime, reliability, integrated pass-isolation analysis, limitations, reproduction.
- **Leading finding** (as assigned): production compilers exceed the prototype on 7 of
  15 ceiling families — written with the audit's quantified caveats: on 5 of the 7
  (IQP +64.4, VQE +42.2, HardwareEfficient +36.5, UCCSD +23.3, QAOA +6.3) production
  wins by 6–64 pp; on Adder and QuantumWalk every production compiler also fails
  (QuantumWalk is strictly worse under all three: Qiskit −1904.7%, Cirq −4547.4%,
  t|ket> −1261.9%). Across all 15 families, best-production-minus-prototype ≥ 5 pp on
  8–9 families. The prototype never increases gate count on any family; every
  production compiler blows up on ≥ 2.
- **QuantumWalk −256.5% explanation**: n = 4, 46 → 164 gates; CNOT 6 → 75 (12.5×);
  caused by HighLevelSynthesis/box decomposition of multi-controlled walk operators
  before any peephole pass, with no adjacent inverse pairs afterwards; exact
  transformation (F = 1.0), escalation to −4193.4% at n = 9.
- **New audit discoveries beyond the assigned findings**:
  - t|ket> RandomClifford correctness failure: 14/30 trials produce F ≈ 0.27–0.33
    (|Tr(U1†U2)| = d/2 exactly), bimodal, seed-dependent, confined to RandomClifford.
    Nominal +71.6% partially invalid; fidelity-passing mean +73.5% (n = 16).
    Reproduced directly (clifford_5 trial 4: F = 0.2727, 40 → 10 gates).
  - Qiskit L2 ≡ L3 in fair mode: bit-identical outputs on 100% of 520 matched rows;
    L1 ≠ L2 on 30.8% (CommutativeCancellation only from L2); L0 still decomposes
    multi-controlled gates (Grover/QuantumWalk blowup), so L0 is not a neutral baseline.
- **Full wall-clock runtime table**: fragment Table S3 + results doc Sec. 7
  (Qiskit 6–13 ms/circuit by level; Cirq mean 1.96 s, median 0.10 s, QuantumWalk-dominated;
  t|ket> mean 0.75 s; prototype 1.65 s at n in {4,6,8}, 74.9 s full-range, max 14,915 s).

## 2. Files changed / created

Modified (all in owned scope):
- `experiments/sota_benchmark.py` — v1.1.0: cirq `gateset=` fix, sx/sxdg QASM injection,
  explicit Qiskit `level0..level3` configs, `--families` / `--target-qubits` CLI filters,
  atomic writes + backups, canonical (tool, config) parsing fix, fidelity/success metric
  fixes, per-(tool, config) aggregation with median runtime.
- `experiments/aggregate_sota_results.py` — now a thin wrapper delegating to
  `sota_benchmark.aggregate_results()` (removes the dual-schema write conflict on
  `aggregated/sota_comparison_aggregated.csv`).
- `experiments/generate_sota_tables.py` — rewritten; emits the manuscript fragment from
  canonical raw CSVs (nothing hard-coded), atomic write with backup, UCCSD naming
  unification, t|ket> correctness caveat auto-computed.

Created:
- `data/v6/sota_benchmark/raw/qiskit_level0_20260720_153511.csv` (520 rows, canonical L0)
- `data/v6/sota_benchmark/raw/qiskit_level1_20260720_153805.csv` (520 rows, canonical L1)
- `data/v6/sota_benchmark/raw/qiskit_level2_20260720_154059.csv` (520 rows, canonical L2)
- `data/v6/sota_benchmark/raw/cirq_default_20260720_151000.csv` (520 rows, canonical fixed Cirq)
- `data/v6/sota_benchmark/raw/qiskit_level{0,1,2}_20260720_1508{37,03,54}.csv` (first-pass
  parallel-load runs; non-canonical, kept for provenance)
- `data/v6/sota_benchmark/metadata/hardware_environment.json`
- `data/v6/sota_benchmark/metadata/qiskit_level{0,1,2}_metadata.json` (level1 restored
  after smoke-run overwrite; `.bak-…` kept)
- `data/v6/sota_benchmark/metadata/cirq_default_metadata.json` (updated to fixed run)
- `data/v6/sota_benchmark/derived/coverage_audit.csv`
- `data/v6/sota_benchmark/logs/*.log`
- `data/v6/sota_benchmark/aggregated/sota_comparison_aggregated.csv` (regenerated,
  105 rows, protocol schema; `.bak-…` backups of the previous 60-row file kept)
- `docs/manuscript/sections/sota_table_fragment.md`
- `docs/results/sota_compiler_benchmark.md`
- `docs/review/wave1/compiler_baseline.md` (this file)

Not touched (per scope): `docs/manuscript/manuscript.md`, release manifest,
`docs/manuscript/sections/sota_comparison_tables.md` (superseded by the new fragment —
flagged for the integration worker).

## 3. Verification performed

- Small-sample validation (final state of all modified scripts):
  `python experiments/sota_benchmark.py --tool qiskit --config level1 --mode smoke
  --n-trials 1 --families QFT --target-qubits 3` → 1 row, ok, F = 1.0 (sample CSV
  removed afterwards). Interpreter: `/d/Downloads/miniforge3/python`.
- Aggregation: `python experiments/aggregate_sota_results.py` → 105-row protocol-schema
  CSV; canonical selection prints one file per (tool, config).
- Fragment: `python experiments/generate_sota_tables.py` → fragment regenerated;
  spot-checked S1–S5 against raw CSVs (e.g. QuantumWalk n = 4: 46 → 164, −256.5%).
- Determinism: parallel vs sequential L0–L2 runs → 100% identical optimized gate counts
  (520/520 rows per level).
- Fix efficacy: Cirq QFT/QuantumWalk smoke rows went from import-error to ok
  (F = 1.0) after the sx/sxdg injection.

## 4. Remaining gaps / handoffs

1. **Cirq numbers changed materially** after the pipeline fix (protocol-conformant).
   The older fragment `sections/sota_comparison_tables.md` and any manuscript text
   citing the 2026-07-18 Cirq values (e.g. RandomClifford +47.4, GHZ −18.1) are stale;
   integration worker should reconcile against Table S1 of the new fragment.
2. **Prototype full-scale v6 run** still missing (smoke only); prototype column in
   Table S1 comes from E15 (labeled). Owner: prototype-optimizer workstream.
3. **t|ket> RandomClifford correctness issue** needs a decision: report with caveat
   (current fragment approach), exclude the family, or escalate as an upstream pytket
   bug report. Not a data error on our side — reproduced via direct pytket calls.
4. **t|ket> n > 6 / Cirq n > 8 fidelity** coverage gaps are documented, not filled
   (compute/timeout constraints per protocol).
5. **Statistical tests** in the aggregated CSV are underpowered for the prototype
   column (E15 3–8 trials/cell vs 10 for production); flagged in results doc Sec. 10.
6. `data/v5/qiskit_pass_isolation.csv` covers only 5 families × 2 Qiskit passes; a
   wider pass-isolation sweep (e.g. TemplateMatching) would strengthen Sec. 9 but was
   out of this wave's scope.
7. VOQC / Quartz remain unavailable (Windows native, no build); comparison stays
   literature-based as per protocol §7.4–7.5.
