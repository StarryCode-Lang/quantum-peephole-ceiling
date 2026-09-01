# v12 novelty red-team comparison

Status: `PASS_WITH_BOUNDARIES` as of 2026-09-01. This is a method-level
comparison, not a claim that every quantum-compilation publication has been
enumerated. The literature window searched for newly relevant work was
2025-09-01 through 2026-09-01; older named systems were included because the
protocol explicitly requires them.

## Candidate contribution under review

The proposed contribution is a deterministic certificate for a *fixed,
unitary gate listing*: construct a stated dependence DAG, enumerate supported
inverse/mergeable endpoint pairs, distinguish pairwise exposability from joint
exposability after quotient contraction, and return a constructive lower bound
(`LB`), a matching upper bound (`UB`), and explicit zero/exact statuses. A
Certificate-Guided Listing (CGL) materializes a legal topological order that
attains its reported `LB`. The object being certified is not general circuit
optimality and not equivalence of an already-produced rewrite.

The repository's current baseline has separate mechanisms for commutation
rewriting, template matching, and a sliding-window action-space proxy:

| Local baseline | Evidence | What it does | What it does not certify |
|---|---|---|---|
| Phase-2a commutation rewriter | `src/optimisation/phase2/commutation_rewriter.py:29-128` | Searches a bounded window, bubbles one inverse pair through sufficient commutation rules, and removes it. | No dependence-poset certificate, joint multi-pair matching bound, or CGL listing. |
| Phase-2b template matcher | `src/optimisation/phase2/template_matcher.py:126-252` | Applies a fixed template library, diagonal/rotation merges, and optional bounded gathering. | No universal candidate-pair exposure certificate; template and gathering behavior remain rule-library-specific. |
| Ceiling-aware proxy | `src/optimisation/ceiling_aware.py:39-96` | Counts adjacent or bounded-window candidates to skip phases. | A count is not a legality proof, a joint-exposure bound, or a constructive lower bound. |
| Equivalence layer | `src/equivalence.py:117-257` | Separates exact structural, exact Clifford, numerical, sampled, heuristic, and unavailable evidence. | Verifies semantic equivalence of circuits; it does not predict listing exposure. |

## External comparison

Legend: “No” means no such artifact was identified in the cited public
description, not that the system could not be extended to produce one.

| Work | Representation | Safety / equivalence contract | Joint pair exposure? | LB / UB / zero certificate? | Certificate-to-listing? | Forward external validation? | Red-team disposition |
|---|---|---|---|---|---|---|---|
| Qiskit `DAGDependency` and exact pattern matching [1,2] | Dependency DAG whose edges encode non-commutation; pattern matcher finds maximal pattern matches considering pairwise commutation. | Exact pattern matching and compiler rewrite semantics. | No exposed matching/quotient-DAG certificate for a selected set of independent cancelable pairs. | No v12-style LB/UB/zero object. | Produces matches/rewrites, not a listing selected from an exposure certificate. | Qiskit implementation and numerical scaling evaluation. | Closest representation precedent, but not substantively isomorphic: v12 certifies a bounded opportunity frontier before choosing a rewrite. |
| Quartz [3,4] | Circuit graph plus equivalent-circuit-class (ECC) rewrite space. | Automatically generates and verifies transformations; cost-based backtracking applies verified rules. | Search explores rewrite sequences, not a pairwise-exposable graph with quotient joint-feasibility. | Rule/circuit equivalence is verified; no matching LB/UB/zero exposure certificate identified. | Returns optimized circuits, not CGL materialization from an exposure certificate. | Benchmarks across multiple gate sets. | Strong safety/search precedent; different certified object and output. |
| QUESO [5,6] | Algebraic symbolic rewrite rules with polynomial-identity filtering and beam search. | High-probability correctness via probabilistic identity testing. | No explicit dependence-poset joint pair-exposure theorem. | No deterministic LB/UB/zero exposure certificate. | Applies synthesized rules; no certificate-derived legal listing. | Benchmark suite against Qiskit/TKET. | Different objective, probabilistic contract, and abstraction. |
| Quasar [7,8] | Two complementary e-graphs for graph and sequence representations; equality saturation. | Sound rewrite/e-graph machinery and step-limited best-cost extraction. | Jointly explores equivalent forms, but does not expose the v12 candidate matching/quotient-DAG certificate. | Step-limited optimum is not the v12 matching UB for a fixed candidate set; no v12 zero certificate identified. | Extracts a low-cost circuit, not a listing proven to attain an exposure LB. | Standard benchmark evaluation and artifact. | Closest search-space threat; not a substantive identity because the certified quantity and construction differ. |
| Local Optimization / cut-and-meld [9] | Cuts a circuit into segments and melds optimized subcircuits. | Proves local optimality under an oracle-optimizer model. | Segment interfaces are not pair-exposure matching with quotient-cycle checks. | Local-optimality guarantee, not v12 LB/UB/zero exposure certificate. | Melding produces a circuit, not a certificate-guided topological listing. | Implemented comparison with state-of-the-art optimizers. | Different locality notion and oracle model. |
| Q-PreSyn [10] | Representation-sensitive local-edit trajectories before synthesis. | Local edits preserve equivalence; RL chooses edit sequences to reduce T-count after synthesis. | No deterministic joint pair-exposure certificate. | No LB/UB/zero exposure certificate. | RL materializes edits, not a proof-backed listing from a pair certificate. | Evaluated up to 25 qubits over synthesis methods. | Important representation-sensitivity prior; not a certificate or fixed pair model. |
| QuTuner [11] | Static circuit features plus optimization-aware pass embeddings. | Learns/ranks pass sequences for compiler objectives. | No explicit commutation-poset candidate graph. | No formal exposure LB/UB/zero certificate. | Ranks pass sequences, not a certificate-derived listing. | Qiskit and PyTKET benchmark evaluation. | Orthogonal learning-based pass tuning; v12 deliberately has no ML dependency. |
| SSR [12] | Genetic commutation/sweeping followed by SAT-generated CNOT rewrites. | Functionally equivalent, SAT-supported subcircuit rewrites. | Reorders and rewrites subcircuits, but no v12 joint-exposure certificate. | No LB/UB/zero exposure certificate identified. | Optimizer output is not certificate-to-listing materialization. | QCT benchmark evaluation. | Relevant commutation/rewrite scheduling threat; different target and proof object. |
| HOPPS [13] | CNOT/Rz phase-polynomial blocks with SAT-based blockwise synthesis. | SAT-based count/depth optimality for bounded blocks. | Blockwise synthesis is not fixed-pair exposure under two dependence models. | Block optimum is not a v12 matching bound or zero certificate. | Emits synthesized blocks, not a CGL topological order. | OLSQ/QAOA evaluations. | Recent in-window block-optimization precedent; no substantive identity. |
| Quantum Circuit Equivalence Checking: Unitary to Hybrid [14] | Semantic lifting from unitary to hybrid circuits via deferred measurement, separation, and projection. | Equivalence checking for transformations, including hybrid circuits. | Does not predict whether pairs can be made adjacent in a legal listing. | No exposure LB/UB/zero certificate. | Verifies a given transformation rather than constructing CGL. | Qiskit/compiler and hybrid-circuit examples. | Relevant verification precedent; answers a different question. |
| RL with deterministic Commutation-and-Reduction [15] | RL state/action space with deterministic local commutation/cancellation after each action. | Elementary reductions are deterministic; overall policy is learned. | No matching/quotient-DAG joint certificate. | No deterministic exposure LB/UB/zero certificate. | Learns actions rather than materializing a certificate-selected listing. | Multiple gate sets and cross-scale tests. | Latest in-window commutation-learning threat; still not the proposed certificate. |

## Core-difference audit

The five claims survive the red-team comparison only with the following
boundaries:

1. “Representation robust” means robust across the two explicitly declared
   dependence models (`wire_order_v1` and
   `conservative_commutation_v1`), not representation-independent across all
   compiler IRs.
2. “Certificate” means a certificate about supported pair exposure under a
   finite rule library. It is not a global circuit-optimality proof, a proof
   of compiler optimality, or a semantic equivalence checker replacement.
3. `UB` is safe only for the candidate graph and dependence/rule contract that
   produced it. Candidate caps, budget exhaustion, unsupported gates, and
   dynamic/nonunitary circuits must be fail-closed or explicitly downgraded.
4. External validation is prospective only when the generator/family was not
   used to develop the method. Existing E31 data are read-only and cannot
   serve as confirmation of E40.
5. H-sandwich and other three-gate templates remain secondary Phase-2b arms;
   they are excluded from the core pair-exposure theorem.

## References

[1] Qiskit, “DAGDependency,” current API documentation:
<https://qiskit.qotlabs.org/docs/api/qiskit/qiskit.dagcircuit.DAGDependency>

[2] Iten et al., “Exact and practical pattern matching for quantum circuit
optimization,” arXiv:1909.05270:
<https://arxiv.org/abs/1909.05270>

[3] Xu et al., “Quartz: Superoptimization of Quantum Circuits,” arXiv:2204.09033:
<https://arxiv.org/abs/2204.09033>

[4] Quartz project and artifact documentation:
<https://github.com/quantum-compiler/quartz>

[5] Xu et al., “Synthesizing Quantum-Circuit Optimizers,” arXiv:2211.09691:
<https://arxiv.org/abs/2211.09691>

[6] QUESO project documentation:
<https://github.com/qqq-wisc/queso>

[7] Yang et al., “Equality Saturation for Quantum Circuit Optimization,”
Proc. ACM Program. Lang. 10 (2026): <https://doi.org/10.1145/3808254>

[8] Quasar artifact, Zenodo record 19055645:
<https://zenodo.org/records/19055645>

[9] Arora et al., “Local Optimization of Quantum Circuits,” arXiv:2502.19526:
<https://arxiv.org/abs/2502.19526>

[10] Bosco et al., “Quantum Circuit Pre-Synthesis: Learning Local Edits to
Reduce T-count,” arXiv:2601.19738: <https://arxiv.org/abs/2601.19738>

[11] Zhong et al., “QuTuner: Feature- and Learning-Guided Optimization Pass
Tuning for Quantum Compilers,” arXiv:2607.04586:
<https://arxiv.org/abs/2607.04586>

[12] Huang et al., “SSR: A Swapping-Sweeping-and-Rewriting Optimizer for
Quantum Circuit Transformation,” arXiv:2503.03227:
<https://arxiv.org/abs/2503.03227>

[13] Li et al., “HOPPS: Hardware-Aware Optimal Phase Polynomial Synthesis with
Blockwise Optimization for Quantum Circuits,” arXiv:2511.18770:
<https://arxiv.org/abs/2511.18770>

[14] Ricciardi et al., “Quantum Circuit Equivalence Checking: A Tractable
Bridge From Unitary to Hybrid Circuits,” arXiv:2511.22523:
<https://arxiv.org/abs/2511.22523>

[15] Tao et al., “Quantum circuit optimization using deep reinforcement
learning: Applications across multiple gate sets,” arXiv:2608.19103:
<https://arxiv.org/abs/2608.19103>
