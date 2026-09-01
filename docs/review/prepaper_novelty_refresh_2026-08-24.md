# Pre-paper novelty refresh (2026-08-24)

Status: live primary-record collision audit performed before manuscript writing.
This is not a claim of systematic-review completeness and is not manuscript prose.

## Search scope and method

The refresh searched 2025--2026 work on quantum-circuit representation,
local rewriting, equality saturation, parameterized equivalence, learned
compilation, multi-objective optimization, and scalable fidelity evaluation.
Searches were executed on 2026-08-24. Inclusion decisions use official arXiv,
publisher, or DOI records; secondary result lists were used only to locate a
primary record and never as absence evidence.

Targeted queries included:

- `quantum circuit optimization representation local rewriting 2026`
- `quantum circuit compiler equality saturation e-graph 2026`
- `parameterized quantum circuit equivalence verification 2025 2026`
- `quantum circuit local optimization synthesis 2026`
- `quantum circuit optimizer compiler rewrite synthesis reinforcement learning`

The current arXiv records for Q-PreSyn (`2601.19738`), cut-and-meld
(`2502.19526`), and GUOQ (`2411.04104`) were also re-opened to check version
history and current claims.

## Newly relevant primary records

| Work | Verified primary record | What it adds | Consequence for Q-research |
|---|---|---|---|
| Abdulla et al., *Parameterized Verification of Quantum Circuits* | arXiv:2511.19897, submitted 2025-11-25 | Fully automatic relational verification for parameterized programs that generate an infinite circuit family; synchronized weighted tree automata and decision procedures for inclusion/equivalence | The project's finite numeric parameter bindings are further from the current verification frontier than the older symbolic-PQC comparison alone showed. Any parameterized or family-wide correctness claim remains barred. |
| Szyniszewski et al., *Automated quantum circuit optimization with randomized replacements* | arXiv:2601.15934, submitted 2026-01-22 | Greedy local ZX rewriting with approximate transformations and stochastic mixtures of circuits under a strict error budget | Establishes a distinct mixed-channel/approximate paradigm. The project's exact-unitary contract is a defensible bounded choice, not a universal definition of valid optimization; results cannot be generalized to approximate channels. |
| Ghlib, Bouhadouza, and Hnaien, *Scalable multi-objective genetic algorithm for quantum circuit optimization* | *Scientific Reports* 16, 17977 (2026), DOI 10.1038/s41598-026-47674-5 | NSGA-II optimization of fidelity, depth, and gate cost using block and overlapping-window fidelity surrogates, reported up to 32 qubits | Removes novelty from generic “multi-objective Pareto optimization” and from using local windows as a scalability device. E31 remains distinguishable only by its exact small-circuit validity contract and preregistered listing x rule-set x window x budget causal diagnostic. |
| Rosenhahn, Osborne, and Hirche, *Optimization Driven Quantum Circuit Reduction* | *New Journal of Physics* 27, 104509 (2025), DOI 10.1088/1367-2630/ae0e40; arXiv:2502.14715 | Localized term replacement with stochastic search, database retrieval, and machine-learning decision support; official abstract reports Qiskit comparisons and the paper includes BQSKit comparisons | New close comparator for local replacement and search-policy claims. A shared-input, shared-basis, equal-budget reproduction would be needed before any performance comparison; no local run is claimed here. |

## Version and collision recheck

- Q-PreSyn remains arXiv v1 (2026-01-27). Its abstract continues to state that
  local synthesis performance strongly depends on circuit representation and
  reports equivalence-preserving learned local edits with up to 20% T-count
  reduction. Representation dependence itself is not novel.
- Cut-and-meld remains arXiv v1 (2025-02-26). Its local-optimality theorem and
  oracle-parametric cut-and-meld algorithm continue to bar general “first local
  ceiling” or “first guaranteed local optimum” wording.
- GUOQ remains arXiv v1 and identifies rewriting plus resynthesis as a unified
  transformation framework. The local BQSKit-backed GUOQ packet in this project
  remains a pilot, not a formal shared-grid performance result.

## Updated defensible boundary

The strongest currently defensible contribution is not representation awareness,
windowing, local rewriting, Pareto optimization, or local optimality in isolation.
It is a reproducible, preregistered diagnostic of how one specified flat listing,
one shared rule engine, window size, and fixed compute budget interact on a frozen
391-input benchmark, with exact semantic checks and family-aware reporting.

That contribution remains conditional on the E31 formal completion gate. It does
not establish:

- priority over Q-PreSyn, Quasar, cut-and-meld, GUOQ, or optimization-driven local
  replacement;
- superiority to the new multi-objective evolutionary method;
- validity for approximate mixed channels, symbolic parameter families, large
  circuits, unseen circuit families, or real hardware;
- a universal representation or algorithm-independent ceiling.

## Primary records

- https://arxiv.org/abs/2511.19897
- https://arxiv.org/abs/2601.15934
- https://doi.org/10.1038/s41598-026-47674-5
- https://doi.org/10.1088/1367-2630/ae0e40
- https://arxiv.org/abs/2502.14715
- https://arxiv.org/abs/2601.19738
- https://arxiv.org/abs/2502.19526
- https://arxiv.org/abs/2411.04104
