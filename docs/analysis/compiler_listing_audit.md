# Production Compiler Listing Audit

> **Date**: 2026-07-21 (wave 4)
> **Auditor**: CompilerAudit worker
> **Question under audit**: the manuscript's flagship premise — *"the listing model
> determines the reachable action space"* (listing model 决定可达作用空间). If production
> compilers already perform WCL-style (wire-consecutive listing) relisting — implicitly
> or explicitly — the claim must be scoped. This audit establishes, from installed
> package source and a controlled experiment, whether each production compiler (a)
> exploits listing reordering and (b) has a peephole action space that depends on the
> input listing.
> **Verdict (summary)**: None of Qiskit 2.4.1, pytket 2.18.0, or Cirq 1.6.1 performs
> explicit WCL-style relisting in its default pipeline, and none is sensitive to the
> flat listing of the input circuit — but for a structural reason that *qualifies* the
> manuscript claim: all three normalize the circuit into a non-listing intermediate
> representation (Qiskit `DAGCircuit`, pytket's internal DAG, Cirq *moments*) whose
> peephole windows are already wire-relative. They therefore already occupy the
> WCL-equivalent action space *by representation*, not by relisting. The listing-model
> limitation is specific to flat-list peephole designs (the prototype), which is
> confirmed empirically: the prototype is listing-sensitive, the production compilers
> are not (Sec. 5).

---

## 1. Scope, environment, and method

| Item | Value |
|------|-------|
| qiskit | 2.4.1 (`D:\Downloads\miniforge3\Lib\site-packages\qiskit`) |
| pytket / pytket-qiskit | 2.18.0 / 0.77.0 (`...\site-packages\pytket`) |
| cirq (-core) | 1.6.1 (`...\site-packages\cirq`) |
| Python | 3.12.12 (`/d/Downloads/miniforge3/python`) |
| Method | (1) read pass classes / docstrings / pipeline assembly in installed source; (2) run a controlled listing-sensitivity experiment (`experiments/listing_sensitivity_check.py`); (3) cross-check against the wave-1 pass-isolation data (`data/v5/qiskit_pass_isolation.csv`) |

**Terminology used below.** A *flat listing* is the linear instruction order of a
circuit file/QASM. *WCL* (wire-consecutive listing) reorders the listing so that gates
acting on the same wire become consecutive, enlarging the window a list-based peephole
can see. A compiler is *listing-sensitive* if two unitary-equivalent flat listings of
the same circuit can yield different optimized outputs. A peephole window is
*wire-relative* if adjacency is defined along the per-qubit dependency chains of the
circuit graph rather than by position in the flat listing.

## 2. Qiskit 2.4.1

### 2.1 Pipeline structure (evidence)

The optimization stage is assembled in
`qiskit/transpiler/preset_passmanagers/builtin_plugins.py::OptimizationPassManager`
(lines 484–603). The loops for the levels used in the benchmark:

- **L1** loop: `Optimize1qGatesDecomposition` → `InverseCancellation` →
  `ContractIdleWiresInControlFlow`, to a fixed point.
- **L2** pre-loop `ConsolidateBlocks` + `UnitarySynthesis`; loop:
  `RemoveIdentityEquivalent` → `Optimize1qGatesDecomposition` →
  `CommutativeCancellation` → `ContractIdleWiresInControlFlow`, to a fixed point.
- **L3** loop: `ConsolidateBlocks` → `UnitarySynthesis` → `RemoveIdentityEquivalent`
  → `Optimize1qGatesDecomposition` → `CommutativeCancellation` →
  `ContractIdleWiresInControlFlow`, to a minimum point.

No pass in any of these loops re-lists the circuit; all operate on the `DAGCircuit`.

### 2.2 Pass-by-pass findings

- **`Collect2qBlocks`** (`passes/optimization/collect_2q_blocks.py`, line 51:
  `block_list = dag.collect_2q_runs()`; docstring: blocks are nodes "in topological
  order such that all gates in a block act on the same qubits, are adjacent in the
  circuit"). Adjacency here is *DAG adjacency along the two wires*, not flat-listing
  adjacency: gates interleaved on other wires do not break a block. This is exactly
  the WCL window, obtained from the graph representation rather than from relisting.
- **`ConsolidateBlocks`** (`consolidate_blocks.py`, lines 58–75): "Replace each block
  of consecutive gates by a single Unitary node … to be resynthesized later" via KAK
  (`TwoQubitBasisDecomposer`). The peephole is the collected block; resynthesis is
  whole-block, so within-block order does not matter.
- **`CommutativeCancellation`** (`commutative_cancellation.py`, lines 28–35, 71–83):
  "Cancel the redundant (self-adjoint) gates through commutation relations", via the
  Rust-accelerated `cancel_commutations` with a `CommutationChecker`. This pass *does*
  exploit commutation to bring canceling gates together — a semantic reordering within
  commutation classes that goes beyond any static listing window — but it never
  materializes a reordered listing; it edits the DAG in place.
- **`Optimize1qGatesDecomposition`** (`optimize_1q_decomposition.py`, lines 61–70):
  "Optimize chains of single-qubit gates by combining them into a single gate" —
  chains are per-wire runs on the DAG (`dag.collect_1q_runs`), again wire-relative.
- **`Optimize1qGatesSimpleCommutation`** (`optimize_1q_commutation.py`, lines 47–59;
  not in the default L1–L3 loops): explicitly commutes 1q gates through 2q "barrier"
  gates with hard-coded rules — commutation-based movement, self-documented as
  non-exhaustive ("Does not exhaustively test all the different ways commuting gates
  can be assigned to either side of a barrier").
- **Permutation elision**: `ElidePermutations` is scheduled only in the *init* stage
  of L3 (builtin_plugins.py line 147), not in the optimization loop; it removes
  explicit permutation/SWAP structure, it does not relist.

### 2.3 Qiskit conclusion

- **Exploits listing reordering?** No explicit relisting pass exists anywhere in the
  L0–L3 pipelines. Commutation is exploited (CommutativeCancellation) as in-DAG
  movement, which subsumes what WCL relisting would expose to a list-based peephole.
- **Peephole action space listing-dependent?** No. The DAG is the meet of all legal
  flat listings; wire-relative windows (`collect_2q_runs`, `collect_1q_runs`) are
  invariant under listing permutations that preserve dependencies. Empirically
  confirmed (Sec. 5): 20 unitary-preserving relistings × 4 circuits → identical
  optimized gate counts on every variant.

## 3. pytket 2.18.0

### 3.1 Pipeline structure (evidence)

`FullPeepholeOptimise` (FPO, the benchmark configuration) is a monolithic
`StandardPass` in the compiled tket core — `FullPeepholeOptimise().to_dict()` returns
`{"pass_class": "StandardPass", "StandardPass": {"name": "FullPeepholeOptimise",
"allow_swaps": true, "target_2qb_gate": "CX"}}`; no Python-visible sub-pass sequence
exists. Its docstring:

> "Performs peephole optimisation including resynthesis of 2- and 3-qubit gate
> sequences, and converts to a circuit containing only the given 2-qubit gate (which
> may be CX or TK2) and TK1 gates." — `:param allow_swaps: whether to allow implicit
> wire swaps`

### 3.2 Pass-by-pass findings (docstring evidence from the installed package)

- **`KAKDecomposition`**: "any sequence of two or more two-qubit gates on the same
  set of qubits are replaced by a single TK2 gate … Using the `allow_swaps=True`
  (default) option, qubits will be swapped when convenient to further reduce the
  two-qubit gate count". The window is a *same-qubit-set sequence* on the circuit
  graph — wire-relative, not listing-relative. `allow_swaps` introduces **implicit
  wire swaps** (a tracked qubit permutation), which is a form of reordering *across*
  wires, more aggressive than WCL; see the correctness incident in
  `docs/results/sota_compiler_benchmark.md` Sec. 12.
- **`PeepholeOptimise2Q`** / **`ThreeQubitSquash`**: "Squash sequences of two-qubit
  operations" / "Squash three-qubit subcircuits … and apply Clifford simplification"
  — the same wire-set-relative window at 2q/3q granularity.
- **`CliffordSimp`**: rewrite rules "similar to Duncan & Fagan
  (https://arxiv.org/abs/1901.10114)" on Clifford gate sequences — region-based
  Clifford simplification, again defined on the graph.
- **`RemoveRedundancies`**: "Removes gate-inverse pairs, merges rotations, removes
  identity rotations, and removes redundant gates before measurement" — local
  cancellation on the DAG.

### 3.3 pytket conclusion

- **Exploits listing reordering?** No relisting step; the tket core works on its own
  DAG. It goes beyond WCL in one respect: implicit wire swaps permute the wire
  assignment itself (`allow_swaps=True`, default), which a pure relisting cannot
  express.
- **Peephole action space listing-dependent?** No. Empirically invariant under
  relisting (Sec. 5, run with `allow_swaps=False` so gate counts are comparable).

## 4. Cirq 1.6.1

### 4.1 Pipeline structure (evidence)

The benchmark pipeline calls `optimize_for_target_gateset(circuit,
gateset=cirq.CZTargetGateset())`
(`cirq/transformers/optimize_for_target_gateset.py`, lines 100–167), which runs, per
pass: `gateset.preprocess_transformers` → decompose-to-gateset →
`gateset.postprocess_transformers`. The chains
(`cirq/transformers/target_gatesets/compilation_target_gateset.py`, lines 158–189):

- preprocess: `expand_composite` → [`insertion_sort_transformer` *only if*
  `reorder_operations=True`] → `merge_k_qubit_unitaries(k=2)`;
- postprocess: `merge_single_qubit_moments_to_phxz` → `drop_negligible_operations`
  → `drop_empty_moments` (→ `stratified_circuit` only if
  `preserve_moment_structure=False`).

`CZTargetGateset()` defaults (`cz_gateset.py`, lines 46–61):
`preserve_moment_structure=True`, **`reorder_operations=False`** — the one explicit
relisting transformer is *off* in the benchmark configuration.

### 4.2 Transformer-by-transformer findings

- **`merge_k_qubit_unitaries`**: "Merges connected components of unitary operations,
  acting on <= k qubits." The window is a *connected component* of the moment graph —
  wire-relative, not listing-relative. Merged components are resynthesized via
  `two_qubit_matrix_to_cz_operations` (KAK-class analytical decomposition).
- **`eject_z`**: "Pushes Z gates towards the end of the circuit … they may absorb
  other Z gates, get absorbed into measurements, cross CZ gates, cross PhasedXPowGate
  (aka W) gates (by phasing them)". Commutation-based movement across the moment
  structure — beyond a static listing window, but not a relisting.
- **`insertion_sort_transformer`**: "Sorts the operations using their sorted
  `.qubits` property as comparison key. Operations are swapped only if they commute."
  — this **is** an explicit WCL-style relisting transformer (sorting by qubits makes
  gates wire-consecutive). It is gated behind `reorder_operations=True`, which is
  *not* the default and was not used in the benchmark. Its existence shows the Cirq
  authors consider WCL-style relisting an optional preprocessing choice, not a
  necessity — the moment representation already provides wire-relative windows.
- **Moment IR**: Cirq stores circuits as ordered *moments* (sets of simultaneous
  operations). Flat-listing permutations that preserve dependencies produce the same
  moment structure under the greedy (earliest) insertion used on QASM import, so the
  listing is normalized away at parse time.

### 4.3 Cirq conclusion

- **Exploits listing reordering?** Not by default. An explicit WCL-style relister
  exists (`insertion_sort_transformer`) but is disabled unless
  `reorder_operations=True`.
- **Peephole action space listing-dependent?** No. Moment-based windows are
  wire-relative; empirically invariant under relisting (Sec. 5).

## 5. Controlled experiment: listing sensitivity

Script: `experiments/listing_sensitivity_check.py` (this wave). For each of
`clifford_5`, `iqp_5`, `qaoa_line_5`, `vqe_twolocal_5` (suite `mode="full"`,
seed 42), 20 flat listings were generated by random adjacent swaps of instructions
on disjoint qubits (unitary-preserving by construction; verified per variant against
`Operator`, including the circuits' nonzero `global_phase`, which must be copied when
rebuilding — see the script). Each variant was compiled with Qiskit L3 (fair mode,
`seed_transpiler=42`), pytket `FullPeepholeOptimise(allow_swaps=False)`, and the Cirq
benchmark pipeline; the repo prototype (`GreedyGateCancellation`, Phase-1) serves as
the flat-list positive control. Output gate counts:

| circuit | base | Qiskit L3 | t\|ket> FPO (no swaps) | Cirq default | prototype (flat-list) |
|---------|-----:|-----------|------------------------|--------------|-----------------------|
| clifford_5 | 44 | 13 (×20 identical) | 12 (identical) | 14 (identical) | **34–44, 5 distinct values** |
| iqp_5 | 24 | 13 (identical) | 11 (identical) | 17 (identical) | **23–24, 2 distinct** |
| qaoa_line_5 | 39 | 39 (identical) | 37 (identical) | 51 (identical) | 39 (identical; nothing to cancel) |
| vqe_twolocal_5 | 38 | 23 (identical) | 23 (identical) | 38 (identical) | 38 (identical) |

**Result.** All three production compilers are flat-listing invariant on every tested
family; the flat-list prototype is listing-sensitive exactly where it has optimization
opportunities (RandomClifford: optimized counts range over 34–44 across relistings of
one and the same circuit). This is the direct experimental counterpart of the
source-level findings above.

## 6. Consequences for the manuscript claim

1. **The claim stands for listing-based peephole designs.** For an optimizer whose
   window is defined on the flat listing, the listing model demonstrably determines
   the reachable action space (prototype, Sec. 5: same circuit, same tool, 34 vs 44
   gates out depending only on the listing).
2. **The claim must be qualified for production compilers.** Qiskit, pytket, and Cirq
   do not relist, and are not listing-sensitive — because their intermediate
   representations (DAG / moments) already define peephole windows *per wire or per
   connected component*, i.e. they operate on the WCL-equivalent action space *by
   construction*. A flat-list peephole + WCL relisting is the representational poor
   cousin of what DAG-based compilers do natively. Recommended scoping (wording
   suggestion, integration worker to adapt): *"for listing-based peephole optimizers,
   the listing model determines the reachable action space; graph-based production
   compilers escape this dependence by defining windows on the circuit DAG/moment
   structure, which is equivalent to compiling against the wire-consecutive
   listing."*
3. **Production windows are still local.** DAG/moment normalization removes listing
   sensitivity, not locality: Qiskit's blocks are 2q runs, pytket's are 2q/3q
   sequences, Cirq's are ≤2q connected components. The wave-1 pass-isolation result
   (one `CommutativeCancellation` pass reproduces the prototype's reductions on
   CNOT/Oracle/RandomClifford) and the L2≡L3 fair-mode equivalence are consistent
   with this: the *class* of reachable transformations is local-peephole on both
   sides; the production advantage comes from beyond-peephole synergy
   (resynthesis/KAK, phase polynomials, Clifford regions), not from a larger listing
   window.
4. **Beyond-WCL reordering exists but is semantic, not textual.**
   `CommutativeCancellation` (Qiskit), `eject_z` (Cirq), and pytket's implicit wire
   swaps all move operations through commutation/permutation structure; none emits a
   reordered listing. Cirq's `insertion_sort_transformer` is the only explicit
   WCL-style relister found, and it is off by default.

## 7. Audit limitations

- pytket's FPO internals are compiled; the audit relies on its public docstring and
  `to_dict()` metadata, not on readable pass-chain source.
- The relisting experiment covers 4 families at n = 5 with 20 variants each
  (disjoint-wire swaps only). Swaps of *commuting same-wire* gates were not
  enumerated; DAG-based windows are expected to be invariant to those as well, but
  this was not tested.
- Qiskit synthesis passes (`UnitarySynthesis`, `HighLevelSynthesis`) can be
  stochastic in general; all Qiskit runs here used a fixed `seed_transpiler=42`, and
  invariance held at that seed.

## 8. Addendum: Wave-5 listing-sensitivity expansion (2026-07-21)

The relisting experiment (Sec. 6) has been expanded from 4 families x n=5 x 20
variants to **10 families x n={3,5,8} x 20-50 variants** (4,320 rows, data in
data/v8/listing_sensitivity/). Families covered: CNOT, GHZ, Grover,
HaarRandom, HardwareEfficient, IQP, Oracle, QAOA, QFT, RandomClifford. Five
families (UCCSD_inspired, VQE, Adder, QuantumWalk, SurfaceCode) were not
completed due to compute-time constraints at n=5/8; the 10 completed families
provide 81 production-compiler family-n-tool combos and 27 prototype combos.

### 8.1 Results

| Metric | Original (Sec. 6) | Wave-5 expansion |
|---|---|---|
| Families | 4 | 10 |
| N values | {5} | {3, 5, 8} |
| Variants per circuit | 20 | 50 (n=3,5) / 20 (n=8) |
| Total rows | ~320 | 4,320 |
| Production compiler sensitive combos | 0/16 | **0/81** |
| Prototype sensitive combos | 5/16 | **13/27** |

**Conclusion unchanged and strengthened.** All three production compilers
(Qiskit L3, pytket FPO allow_swaps=False, Cirq default) produce identical gate
counts across all relistings for every tested family and n-value (0/81
sensitive combos). The flat-list prototype is listing-sensitive on 13/27
combos, spanning CNOT, Grover, IQP, Oracle, and RandomClifford at n=3, 5, and 8.

### 8.2 Impact on manuscript claim

The manuscript's core claim ("listing model determines the reachable action
space of listing-type peephole optimizers") is **strengthened** by the expanded
coverage. The negative result (production compilers are flat-listing invariant)
now holds across 10 families and 3 qubit counts, eliminating the "small sample"
rebuttal. The positive control (prototype IS listing-sensitive) now demonstrates
sensitivity in 5 distinct families across 3 n-values, including the
worst-case RandomClifford family (6 distinct outputs at n=3, 6 at n=5, 3 at
n=8).

### 8.3 Remaining limitations

- 5 of 15 families (UCCSD_inspired, VQE, Adder, QuantumWalk, SurfaceCode) were
  not completed due to compute-time constraints (some families produce very
  large circuits at n=5/8 that are slow to compile with all 4 tools). The
  conclusion is not expected to change for these families (they use the same
  DAG/moment-based compilers), but this should be noted.
- Same-wire commuting-gate swaps were not enumerated (same as Sec. 7).
- n=8 used 20 variants (vs. 50 for n=3,5) due to compilation time.

---

## 9. Addendum: Wave-6 completion of the remaining 5 families (2026-07-21)

The 5 families left incomplete in wave 5 (UCCSD_inspired, VQE, Adder,
QuantumWalk, SurfaceCode) have now been run with the identical methodology
(unitary-preserving adjacent disjoint-gate relistings, rng = Random(1234),
n_swaps = 4 x size, 50 variants at nominal n={3,5}, 20 at n=8, same 4 tools).
Data merged into `data/v8/listing_sensitivity/listing_sensitivity_v8.csv`
(4,320 -> 6,652 rows; backups `*.bak-20260721_141836`).

### 9.1 Root cause of the wave-5 gap (corrected)

Wave 5 attributed the gap to compile-time at n=5/8. The full root cause is
twofold:

1. **Selection bug**: the wave-5 script filters suite circuits by
   `circuit.num_qubits in {3,5,8}`. Adder, QuantumWalk, and SurfaceCode use
   ancilla/coin qubits, so their actual qubit counts (4-10) never match the
   nominal sizes and these circuits were silently excluded regardless of
   budget. The wave-6 fill script
   (`experiments/listing_sensitivity_fill.py`) selects by circuit_id suffix
   (nominal n) instead, and records the ACTUAL qubit count in `n_qubits`.
2. **Genuine compute cost**: QuantumWalk is dominated by MCX decompositions;
   at nominal n=8 (9 qubits, 106 gates) one variant costs ~190 s across the
   4 tools (pytket 61.6 s, Cirq 30.1 s, prototype 98.4 s), and the exact
   `Operator()` unitary check at 9 qubits pushed a single variant past the
   250 s per-call budget.

### 9.2 Results (5 filled families, 60 new family-n-tool combos)

| Metric | Wave-5 (10 fam) | Wave-6 (15 fam) |
|---|---|---|
| Families covered | 10/15 | **15/15** |
| Total rows | 4,320 | 6,652 |
| Family-n-tool combos | 108 | 168 |
| Production compiler sensitive combos | 0/81 | **0/126** |
| Prototype sensitive combos | 13/27 | **15/42** |

Newly observed prototype sensitivity: UCCSD_inspired at n_qubits=5 (5 distinct
outputs, 44-48 gates) and n_qubits=8 (3 distinct, 78-80 gates). VQE, Adder,
QuantumWalk, and SurfaceCode show no prototype sensitivity (their circuits are
either too structured or already minimal for the greedy pass).

**Conclusion unchanged and now complete.** All three production compilers
produce identical gate counts across all relistings for **every** suite family
(0/126 sensitive combos, 15/15 families). The flat-list prototype remains
listing-sensitive (15/42 combos, now spanning 6 families including
UCCSD_inspired). The manuscript's core claim survives full-coverage testing.

### 9.3 Honest limitations of the wave-6 fill

- **qwalk_8 is partial**: 3/20 variants (indices 0-2) due to the ~190 s/variant
  cost; all 3 variants x 4 tools give identical gate counts (qiskit 4551,
  tket 7385, Cirq 11474, prototype 106). Recorded as a gap, not extrapolated.
- **qwalk_8 unitary check skipped** (`unitary_check=skip`, 12 rows): the exact
  `Operator()` equivalence check is computationally infeasible at 9 qubits
  within budget. The relisting transform is unitary-preserving by construction
  (adjacent disjoint-gate swaps) and was verified exactly (`pass`) for all
  other 14 circuits including qwalk_3 and qwalk_5 (2,320 rows).
- n_qubits for Adder/QuantumWalk/SurfaceCode is the actual count (4-10), so
  their summary rows appear at n_qubits in {4,5,6,7,8,9,10}, not {3,5,8}.
