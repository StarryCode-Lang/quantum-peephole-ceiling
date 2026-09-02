# v13 novelty red-team comparison

Status: `PASS_WITH_BOUNDARIES` as of 2026-09-02. This is a method-level
red-team review of the proposed certified rewrite landscape. It is not a claim
that every quantum-compilation publication has been enumerated.

## Candidate contribution under review

For a fixed ordered unitary gate listing and a frozen, semantically safe rule
library, v13 proposes to enumerate the bounded rewrite landscape and return:

1. minimum escape depth within horizon `H`;
2. minimum barrier height among improving paths within `H`;
3. an `H`-local-optimum classification when exhaustive search proves no
   improving path in the declared state space; and
4. hash-pinned, step-by-step replay certificates for the three claims.

The intended object is representation-conditioned and rule-library bounded. It
is not global circuit optimality, a replacement for a semantic equivalence
checker, or an assertion about unseen gate sets.

## Hard red-team rule

If a prior work had all three of minimum escape depth, minimum barrier height,
and a replayable proof for a fixed listing under an explicit rewrite contract,
the contribution would be narrowed to representation-conditioned barrier
spectra and failure decomposition. No such substantive isomorphism was found
in the required comparison scope as of the search date. QALM is the closest
threat because it explicitly studies exploration depth and escaping local
minima; its `k` is a search-depth parameter, not a minimum-depth certificate,
and the paper does not define or replay a minimum barrier certificate.

## Comparison matrix

Legend: “Not found” means that the cited public source does not expose the
specified artifact; it does not mean the system could not be extended to emit
one. “Different object” is a hard boundary, not a claim of inferior software.

| Work | Representation / search object | Semantic or optimality contract in source | Minimum escape depth | Minimum barrier height | Replayable step proof for fixed listing | Threat level and disposition | Primary support position |
|---|---|---|---|---|---|---|---|
| **QALM** | Circuit-space search with rule-based exploitation; `k` controls exploration steps and is progressively increased. | Equivalence-preserving Quartz transformations plus a rule-based optimizer; empirical/local-minimum escape objective. | **No**: `k` is supplied/advanced exploration depth, not the minimum depth to any improving basin. | **No**: local-minimum escape is discussed, but no barrier-height definition or certificate is given. | **No**: algorithm returns an optimized circuit, not a hash-pinned path certificate. | **High**. Closest threat; preserves the boundary by distinguishing a controllable search depth from a certified minimum landscape quantity. | [arXiv HTML](https://arxiv.org/html/2606.16221), Abstract and §§3.1–3.2 (lines 51–55, 112–132), §5.6 (lines 372–380). |
| **Quasar** | Two complementary e-graphs for graph and sequence representations; equality saturation with a step limit and cost extraction. | Sound rewrite/e-graph machinery and step-limited optimal-cost extraction. | **No**: step limit bounds saturation/search; it is not a minimum escape depth from a given listing. | **No**: no barrier-height object identified. | **No**: extracts a circuit, not a per-step certificate for a fixed listing. | **High** for search-space overlap, but different certified object. | [QuICS publication page](https://www.quics.umd.edu/publications/equality-saturation-quantum-circuit-optimization), abstract; [artifact](https://zenodo.org/records/19055645). |
| **Quartz** | Equivalent-circuit classes (ECCs) generated over bounded gate/qubit sizes; cost-based backtracking search over transformations. | Symbolic transformations are automatically verified; ECC completeness and transformation correctness are formalized. | **No**: bounded transformation completeness is not a listing-specific escape-distance certificate. | **No**: no barrier-height spectrum identified. | **No** for the landscape: transformation equivalence is verified, but no replayable minimum-depth/barrier path object is returned. | **High** for frozen rule import and proof safety; different output and state-space question. | [arXiv](https://arxiv.org/abs/2204.09033), Abstract; §§3.2 and 6–7; [official repository](https://github.com/quantum-compiler/quartz). |
| **GUOQ / QUESO** | Randomized optimization combining rewrite transformations with unitary resynthesis; QUESO exposes beam/search configurations. | Functionally equivalent transformations and synthesized rules; stochastic/cost-based optimization. | **No**: no minimum escape-depth certificate. | **No**. | **No**: optimizer output and rule artifacts are not a replayable landscape proof. | **Medium**. Important baseline for the same Nam-style optimization setting, but not isomorphic. | [GUOQ/QUESO repository](https://github.com/qqq-wisc/guoq), §§GUOQ and QUESO (lines 176–180, 211–238, 261–281); [GUOQ paper](https://arxiv.org/abs/2411.04104). |
| **Local Optimization / cut-and-meld** | Cuts a circuit into segments, optimizes subcircuits with an oracle, then lazily melds across cuts. | Explicit segment local-optimality notion and a proof that cut-and-meld attains it under the oracle model. | **No**: segment optimality is not minimum rewrite distance from a fixed ordered listing. | **No**. | **Different object**: proof concerns segment optimality, not a step certificate over a rule graph. | **High** for the local-optimum claim; non-isomorphic locality and oracle contract. | [arXiv](https://arxiv.org/abs/2502.19526), Abstract and lines 18–20. |
| **Q-PreSyn** | Representation-sensitive trajectories of local equivalence-preserving edits selected by reinforcement learning before synthesis. | Local edits preserve equivalence; learning policy is evaluated for post-synthesis `T`-count. | **No**: learned edit sequence is not an exhaustive minimum-depth result. | **No**. | **No**: no deterministic replay certificate for the minimum landscape quantities. | **Medium**. Direct representation-sensitivity precedent, but different objective and proof status. | [arXiv](https://arxiv.org/abs/2601.19738), Abstract (line 5). |
| **QuTuner** | Static circuit features plus optimization-aware pass embeddings; retrieval/ranking/refinement over compiler pass sequences. | Offline learned ranking and Bayesian-optimization refinement; empirical compiler tuning. | **No**. | **No**. | **No**: pass sequence ranking is not a rule-application proof. | **Low–medium**. Representation/response awareness is relevant, but no rewrite landscape certificate. | [arXiv HTML](https://arxiv.org/html/2607.04586), Abstract/§2 and §§3.2.4–3.2.5 (lines 67, 90–105, 165–178). |
| **SSR** | Generalized commutation, genetic rearrangement, CNOT subcircuit sweeping, and SAT rewriting for routed circuits. | SAT-generated depth-optimal rewrites for extracted CNOT blocks; functional equivalence of transformations. | **No**. | **No**. | **No**: block-level SAT optimality is not a replayable bounded path from the input listing. | **Medium**. Relevant commutation/rewrite scheduling threat; target is QCT depth, not fixed-listing barrier structure. | [arXiv](https://arxiv.org/abs/2503.03227), Abstract (lines 0–3). |
| **HOPPS** | Phase-polynomial `{CNOT, Rz}` block synthesis under hardware topology; SAT and iterative blockwise optimization. | CNOT-count/depth optimality, including doubly optimal block solutions. | **No**: optimum of a synthesized block is not minimum escape depth in a rewrite neighborhood. | **No**. | **Different object**: SAT provides an optimal synthesis witness, not three landscape witnesses for an input listing. | **High** for bounded optimality, but restricted representation and objective. | [arXiv HTML](https://arxiv.org/html/2511.18770), §§III–IV (lines 88–102, 171–180, 223–290). |
| **MILP exact synthesis / QuantumCircuitOpt** | Mixed-integer formulation of target-unitary synthesis with gate-selection and parallel-scheduling variables. | Exact synthesis can certify depth-optimal solutions for small-to-medium circuits; scalable rolling-horizon heuristic beyond exact scope. | **No**: target synthesis optimum is not a minimum rewrite escape depth from the given listing. | **No**. | **Different object**: solver certificate supports target synthesis constraints, not a stepwise rewrite replay certificate. | **High** for exact optimality precedent; does not subsume the proposed fixed-listing landscape. | [arXiv HTML](https://arxiv.org/html/2510.00649), Abstract and §§II–V (lines 48–56, 110–119). |
| **Qiskit DAGDependency / exact pattern matching** | Operation-dependency DAG with non-commutation edges; maximal pattern matching considering pairwise commutation. | Exact/maximal pattern matching for fixed pattern size; compiler integration. | **No**: finds matches, not minimum path distance to an improving state. | **No**. | **No**: no joint landscape or barrier replay certificate. | **High representation precedent**, but a matching primitive rather than the proposed certificate. | [IBM Quantum documentation](https://qiskit.qotlabs.org/docs/api/qiskit/qiskit.dagcircuit.DAGDependency), lines 8–10, 22–26; [Iten et al.](https://arxiv.org/abs/1909.05270), Abstract. |
| **VOQC** | SQIR low-level circuit language with verified optimizer transformations. | Coq-proved semantic correctness of optimizer functions. | **No**. | **No**. | **Different object**: proof of transformation correctness, not proof of exhaustive landscape claims. | **Medium**. Strong semantic-proof precedent; does not define the v13 quantities. | [arXiv](https://arxiv.org/abs/1912.02250), Abstract. |

## Search log

| Search date | Database/source class | Fixed keyword or comparator query | Result used |
|---|---|---|---|
| 2026-09-02 | arXiv HTML/abstract search | `quantum circuit rewrite landscape barrier certificate` | QALM; quantum-circuit barrier certificates for verification; cut-and-meld. |
| 2026-09-02 | arXiv HTML/abstract search | `minimum escape depth circuit rewriting` | QALM exploration-depth threat; no source exposing the required minimum certificate. |
| 2026-09-02 | arXiv HTML/abstract search | `local minima quantum circuit optimizer` | QALM; local optimization; no three-part landscape certificate. |
| 2026-09-02 | arXiv HTML/abstract search | `bounded rewrite reachability certificate` | VOQC and exact synthesis results; no fixed-listing three-part object. |
| 2026-09-02 | arXiv HTML/abstract search | `proof-carrying quantum circuit optimization` | VOQC semantic proofs; no landscape replay certificate. |
| 2026-09-02 | arXiv HTML/abstract search | `representation-conditioned rewrite landscape` | Q-PreSyn and QALM as adjacent representation/search work; no isomorphic certificate. |
| 2026-09-02 | IBM Quantum documentation | `DAGDependency`, exact pattern matching | Dependency/non-commutation graph precedent; no barrier certificate. |
| 2026-09-02 | ACM/QuICS/DOI landing pages and official artifacts | Quasar, Quartz, cut-and-meld, MILP exact synthesis, HOPPS | Search-space, semantic, local-optimality, exact-synthesis and block-optimality precedents; none isomorphic to all three v13 quantities. |
| 2026-09-02 | Official GitHub repositories | GUOQ/QUESO and Quartz | Confirmed implementation contracts and output objects; no v13 landscape certificate. |

## Decision

`NOVELTY_STATUS = PASS_WITH_BOUNDARIES`.

Proceed to S2 only with these non-negotiable boundaries:

- the method is a certificate over a frozen finite rule library and declared
  dependence/listing representation;
- `minimum` means exhaustive minimum within the stated horizon and state
  contract, never global circuit optimality;
- a bounded or resource-truncated run may provide a witness and conservative
  bounds, but cannot claim no escape;
- QALM, Quasar, Quartz, GUOQ, HOPPS, MILP exact synthesis and cut-and-meld
  remain explicit related-work threats in all later claims;
- if S2/S3 reveals that Quartz import or the proposed certificate collapses to
  an existing object, the novelty status must be downgraded or stopped.
