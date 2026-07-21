# Wave-4 Completion Report: Compiler Listing Audit + t|ket> Incident Disposition

> **Worker**: CompilerAudit (编译器审计)
> **Date**: 2026-07-21
> **Status**: COMPLETE. All claims trace to installed package source or to real runs
> executed in this session (`/d/Downloads/miniforge3/python`). No manuscript files
> touched.

---

## 1. What was done

### 1.1 Production compiler listing audit (task 1)

Audited whether Qiskit 2.4.1 / pytket 2.18.0 / Cirq 1.6.1 exploit listing reordering
and whether their peephole action spaces depend on the input flat listing, using
installed source as evidence plus a controlled experiment.

**Source-level findings** (all citations with file/line in the audit doc):

- **Qiskit 2.4.1**: no relisting pass exists in any L0–L3 pipeline
  (`preset_passmanagers/builtin_plugins.py::OptimizationPassManager`, lines 484–603).
  Peephole windows are wire-relative by construction: `Collect2qBlocks` uses
  `dag.collect_2q_runs()` (DAG adjacency along the two wires, unaffected by
  interleaving on other wires); `ConsolidateBlocks` resynthesizes whole blocks (KAK);
  `CommutativeCancellation` moves gates through commutation *inside the DAG*;
  `Optimize1qGatesDecomposition` works on per-wire 1q runs. The DAG is the meet of
  all legal listings ⇒ flat-listing invariant.
- **pytket 2.18.0**: `FullPeepholeOptimise` is a monolithic compiled `StandardPass`
  (`to_dict()` evidence); constituent passes (`KAKDecomposition`, `CliffordSimp`,
  `PeepholeOptimise2Q`, `ThreeQubitSquash`, `RemoveRedundancies`) all define windows
  on same-qubit-set sequences / regions of the internal DAG, per installed
  docstrings. Beyond WCL in one respect: `allow_swaps=True` (default) introduces
  implicit wire swaps (a tracked qubit permutation).
- **Cirq 1.6.1**: moment-based IR normalizes the listing at parse time.
  `optimize_for_target_gateset` chains
  (`target_gatesets/compilation_target_gateset.py`, lines 158–189) merge ≤2q
  *connected components* (wire-relative) and resynthesize analytically; `eject_z`
  performs commutation-based movement. Notably, Cirq ships an explicit WCL-style
  relister — `insertion_sort_transformer` ("Sorts the operations using their sorted
  `.qubits` property … swapped only if they commute") — but it is **off by default**
  (`CZTargetGateset(reorder_operations=False)`), and unused in the benchmark.

**Empirical confirmation** (`experiments/listing_sensitivity_check.py`, new): 20
unitary-preserving relistings (adjacent disjoint-wire swaps, verified per variant)
× 4 suite circuits at n = 5 → Qiskit L3, t|ket> FPO, and Cirq produced **identical
optimized gate counts on every variant**, while the flat-list prototype
(`GreedyGateCancellation`) produced 5 distinct outputs (34–44 gates) on
`clifford_5` and 2 on `iqp_5`. Production compilers are flat-listing invariant; the
prototype is listing-sensitive exactly where it has opportunities.

**Consequence for the flagship claim**: "listing model determines the reachable
action space" holds for listing-based peephole designs; production compilers already
occupy the WCL-equivalent action space *representationally* (DAG/moment windows),
so the manuscript statement should be scoped to listing-based peephole optimizers.
Suggested scoping wording is in the audit doc Sec. 6 (integration worker to adapt;
manuscript itself not touched per scope).

### 1.2 t|ket> RandomClifford unitarity incident: root cause + disposition (task 2)

- **Reproduced** the wave-1 failure with direct pytket calls:
  `experiments/reproduce_tket_clifford_unitarity.py` → 3/3 recorded failing cells
  REPRODUCED (F_avg = 1/3, 5/17, 3/11 for n = 3/4/5; |Tr| = d/2 exactly); 3/3
  controls pass at F = 1.0.
- **Root cause identified** (beyond wave-1 knowledge): `FullPeepholeOptimise`'s
  default `allow_swaps=True` leaves an implicit qubit permutation (a single
  transposition on every examined failing cell); `tk_to_qiskit` (pytket-qiskit
  0.77.0) does not materialize it — UserWarning only — so the converted circuit
  implements U_in·P. A single transposition has d/2 fixed points ⇒ |Tr| = d/2, the
  exact observed fingerprint. Verified two independent fixes:
  `replace_implicit_wire_swaps()` before conversion → F = 1.0 (3/3 cells);
  `allow_swaps=False` → F = 1.0 (5/5 cells) at +2–5 gates per circuit.
- **Disposition** (appended as Sec. 12 of `docs/results/sota_compiler_benchmark.md`):
  keep canonical data + prominent disclosure. Rationale: faithful record of a
  production-tool default-semantics trap (reporting value); gate counts are real
  tket outputs (mildly optimistic by the elided permutation, 2–5 gates); bounded
  numerical consequence (+73.5% fidelity-passing vs +71.6% nominal); no Sec. 4–6
  finding depends on it. Future t|ket> runs should materialize implicit swaps or
  disable `allow_swaps`.
- **Quantinuum bug report draft** included in Sec. 12.5 (targets pytket-qiskit's
  warning-only default in `tk_to_qiskit`; the embedded minimal reproducer was
  executed verbatim and produces exactly the claimed behavior: permutation
  {q[2]↔q[3]}, Tr = 16 = d/2, post-fix assert passes).

## 2. Files changed / created (owned scope only)

Created:
- `docs/analysis/compiler_listing_audit.md` — the audit (versions, source
  locations, docstring/line citations, experiment, manuscript-claim scoping).
- `experiments/reproduce_tket_clifford_unitarity.py` — minimal incident reproducer.
- `experiments/listing_sensitivity_check.py` — listing-sensitivity experiment.
- `docs/review/wave4/compiler_audit.md` — this report.

Modified (owned, append-only, atomic write with backup):
- `docs/results/sota_compiler_benchmark.md` — appended Sec. 12
  (incident root cause, reproduction, disposition, bug-report draft).
  Backup: `docs/results/sota_compiler_benchmark.md.bak-20260721-084827`.

Not touched (per scope): `docs/manuscript/manuscript.md`, all data files, all
benchmark CSVs, all other docs.

## 3. Verification performed

- `python experiments/reproduce_tket_clifford_unitarity.py` → 3/3 REPRODUCED,
  3/3 controls ok (output embedded in results doc Sec. 12.3).
- `python experiments/listing_sensitivity_check.py` → full table in audit doc
  Sec. 5; relistings verified unitary-preserving per variant (including the
  `global_phase` subtlety: qaoa/vqe suite circuits carry nonzero global phase,
  which must be copied when rebuilding circuits — handled and documented).
- Root-cause checks: implicit permutation extracted per failing cell;
  `replace_implicit_wire_swaps()` → F = 1.0 (3/3); `allow_swaps=False` → F = 1.0
  (5/5) with gate-count deltas recorded.
- Bug-report reproducer executed verbatim → output matches the draft exactly.
- Version/line citations spot-checked against installed source files (qiskit
  2.4.1, pytket 2.18.0, cirq 1.6.1 under `D:\Downloads\miniforge3\Lib\site-packages`).

## 4. Remaining gaps / handoffs

1. **Manuscript scoping**: the "listing model determines reachable action space"
   statement needs the qualification in audit doc Sec. 6 (production compilers are
   listing-invariant by representation, not by relisting). Owner: manuscript/
   integration worker — the audit provides suggested wording but did not edit the
   manuscript.
2. **pytket FPO internals** are compiled; pass-chain evidence is docstring-level.
   If line-level evidence is ever required, tket's open-source C++ repo is the
   place, not the installed wheel.
3. **Relisting experiment coverage**: 4 families, n = 5, 20 variants, disjoint-wire
   swaps only. A wider sweep (more families, commuting same-wire swaps, n = 6–8) is
   cheap and would strengthen Sec. 5 if reviewers push.
4. **Bug report not submitted**: Sec. 12.5 is a draft; submission to Quantinuum's
   pytket-qiskit tracker is an owner decision (external action).
5. **Benchmark harness hardening** (future runs only): add
   `replace_implicit_wire_swaps()` before `tk_to_qiskit` in
   `experiments/sota_benchmark.py::tket_optimize`, or set `allow_swaps=False`;
   left un-applied to preserve canonical-data provenance (decision recorded in
   Sec. 12.4).
