# Pre-paper novelty and comparator matrix (frozen audit packet)

Status: working research record, not manuscript prose.  Search date: 2026-08-10.

## Search and inclusion record

- Sources searched: SciSpace semantic paper search; Sider Scholar/OpenAlex and
  Google Scholar interfaces; local Scholar exports under
  `data/v6/ceiling_repair/scholar`; primary arXiv, publisher/conference, and
  artifact records.
- Inclusion: 2020--2026 methods that optimize or synthesize gate-model quantum
  circuits and materially overlap with representation, local rewriting,
  equivalence search, learned search, or compiler comparison.
- Exclusion: pulse/control optimization, circuit cutting for distributed
  execution, and papers without enough primary metadata to establish the
  claimed method.
- Evidence labels: **primary** means paper/publisher/artifact record checked;
  **index** means metadata/abstract checked in SciSpace or Scholar but the full
  experimental contract has not yet been independently reconstructed.

### 2026-08-10 search audit update

- A full-question SciSpace semantic query on representation, ordering,
  dependency graphs, e-graphs, and local rewrite visibility returned ten
  candidates and surfaced Q-PreSyn as the closest new priority challenge.
- Sider Scholar's broad Google-Scholar query returned no records and its first
  multi-field OpenAlex query was visibly low precision; neither result was used
  as absence evidence. A direct Sider arXiv-title query then resolved
  `arXiv:2601.19738`, which was independently checked against the official
  arXiv record.
- Sider Wisebase returned no usable file listing in this session. The local
  Scholar verification exports under `data/v6/ceiling_repair/scholar` therefore
  remain the local-data evidence source; the empty connector response is not
  interpreted as an empty user library.

## Feature-by-feature comparison

| Work | Internal representation / search | Objective and scope | Guarantee or correctness contract | Direct implication for this project | Evidence |
|---|---|---|---|---|---|
| Quartz (PLDI 2022, DOI 10.1145/3519939.3523433) | Enumerated small circuits, equivalence classes, generated rewrites | General gate-count superoptimization on bounded fragments | Equivalence checking and bounded enumeration; not whole-circuit global optimality | Already occupies automated bounded-rewrite discovery; the project cannot claim that local search-space limitation was previously unstudied | primary + Scholar |
| Quanto (QST 2024) | Automatically generated circuit identities, including parameterized gates | Broader identity discovery and rewriting | Identity/equivalence contract, bounded by identity search and application | Narrows novelty to measured sensitivity of a specified listing/rule system, not identity generation | local primary-verification record |
| Quarl (PACMPL 2024, DOI 10.1145/3649831) | Circuit graph neural representation plus decomposed location/transformation actions | Learned whole-circuit gate-count optimization | Empirical policy; semantic validity rests on allowed rewrites | Directly defeats any claim that graph representation or action-space design is absent from prior optimizer research | primary metadata + Scholar |
| AlphaTensor-Quantum (NMI 2025; arXiv:2402.14396) | Tensor decomposition over the phase-polynomial/T-count problem | Fault-tolerant T-count, especially arithmetic workloads | Domain reduction to tensor decomposition; empirical learned search | Strong representation-specific precedent, but a different objective and circuit domain | primary arXiv + SciSpace |
| Relaxed peephole optimization (CGO 2021) | Non-contiguous/relaxed local matching | Extend local cancellation reach | Semantics-preserving matched transformations; no general optimum | Precedes claims about enlarging fixed windows; comparison must be about the exact listing and rule contract | local primary-verification record |
| ZX + RL (Quantum 9, 1758, 2025; arXiv:2312.11597) | ZX graph plus GNN/PPO rewrite policy | Clifford+T / extracted circuit cost | Sound ZX rewrites; learned policy is not globally optimal | Prior work already links graph structure to learned rewrite selection | primary metadata + Scholar |
| VOQC (POPL 2021; arXiv:1912.02250) | Verified sequential rewrite passes | General logical circuit cleanup | Machine-checked semantic preservation in Coq | Establishes a correctness standard this Python prototype does not match formally | local primary-verification record |
| PCOAST (QCE 2023; arXiv:2305.10966) | Pauli-based graph spanning unitary and non-unitary nodes | Pauli/Clifford, preparation and measurement aware optimization | Measurement- or state-preservation contract depends on requested semantics | Important omitted comparator: flat gate-list sensitivity is not representative of Pauli-graph compilers | primary arXiv + SciSpace |
| GUOQ, *Optimizing Quantum Circuits, Fast and Slow* (arXiv:2411.04104) | Unified abstract transformations combining fast rewrites and slow resynthesis | General logical optimization | Transformation semantics; empirical comparison | Direct comparator for the fast-local versus slow-search boundary | primary arXiv + Scholar |
| Cut-and-meld, *Local Optimization of Quantum Circuits* (arXiv:2502.19526) | Partition, oracle-optimize segments, lazily meld boundaries | Oracle-parametric local optimality with scalable composition | Proves every segment locally optimal under stated assumptions; linear oracle-call bound under assumptions | Defeats a general “first local ceiling/optimality” claim; only a listing/model-conditional empirical boundary remains plausible | primary arXiv |
| Quasar (PLDI 2026, DOI 10.1145/3808254) | Complementary graph and sequence e-graphs with equality saturation | Multi-objective rewrite optimization | Lowest-cost circuit reachable within a bounded rewrite-step closure; soundness techniques | Most direct representation/search comparator; representation sensitivity and phase ordering are central, not absent | publisher/conference + artifact |
| Q-PreSyn, *Quantum Circuit Pre-Synthesis* (arXiv:2601.19738) | Equivalence-preserving local edits selected by reinforcement learning before Clifford+T synthesis | Reduce downstream T-count by changing the representation supplied to local synthesis | The pre-synthesis edits preserve equivalence; reported benefit is empirical and synthesis-pipeline specific | Closest recent priority challenge: it explicitly states that local synthesis depends strongly on circuit representation and learns edits to improve that representation. This project must differentiate itself by the frozen flat-listing diagnostic, family-level decomposition, and sealed out-of-family test, not by representation dependence alone | primary arXiv + Sider + SciSpace |
| SSR (TODAES 2026, DOI 10.1145/3828549; arXiv:2503.03227) | SWAP reordering, CNOT-block extraction, SAT rewriting | Post-mapping circuit-depth recovery | Depth optimality only for extracted bounded CNOT subcircuits | Different compilation stage; useful negative control against overgeneralizing logical gate-count results | primary record locally verified |

## Current defensible innovation boundary

Fact: prior work already covers graph representations, sequence
representations, equality saturation, bounded equivalence classes,
representation-specific tensor reductions, learned action spaces, learned
representation-changing pre-synthesis edits, and formal local-optimality
guarantees.

Current supported candidate contribution: a reproducible empirical
diagnostic of how **one explicitly specified flat listing**, window policy, and
local rewrite class change measured reduction across generator families, plus
an out-of-family predictive test of that diagnostic. The sealed eight-generator
test passed its preregistered directional gate (MCC 0.731; nested 95% CI lower
bound 0.425), establishing transfer under that fixed label/feature contract.

Not established: priority/uniqueness of that diagnostic relative to the full
Quasar, Q-PreSyn, cut-and-meld, PCOAST, Quartz, and Quarl feature sets;
superiority to those optimizers on a shared metric/input contract; or a general
theorem. The held-out result establishes predictive validity for the frozen
experiment, not novelty or universal validity.

## Claim constraints carried into analysis

1. Do not use “first representation-aware optimizer”, “first structural
   ceiling”, “largest study”, or “universal Phase-1 ceiling”.
2. Treat row count as repeated observations, not independent study scale.
3. Separate descriptive in-sample mechanisms from sealed held-out prediction.
4. Compare external tools only when input QASM, semantics, basis/cost metric,
   timeout, failures, and provenance are aligned; otherwise report an artifact
   integration result, not a performance ranking.

## Primary records

- Quartz: https://doi.org/10.1145/3519939.3523433
- Quarl: https://doi.org/10.1145/3649831
- Quasar paper/program: https://doi.org/10.1145/3808254
- Quasar artifact: https://zenodo.org/records/19571754
- GUOQ: https://arxiv.org/abs/2411.04104
- Cut-and-meld: https://arxiv.org/abs/2502.19526
- PCOAST: https://arxiv.org/abs/2305.10966
- ZX + RL: https://arxiv.org/abs/2312.11597
- AlphaTensor-Quantum: https://arxiv.org/abs/2402.14396
- Q-PreSyn: https://arxiv.org/abs/2601.19738
