# Reference additions and catalogue-defect register — 2026-10-17

**Status:** additive companion to `docs/references/unified_references.md` (v2.2, 94 entries).
**Why a separate file:** `docs/references/unified_references.md` is a path-bound entry of
`release/prepaper_release_manifest.json`. Editing it in place would add a new hash-drift
entry to a frozen release manifest, which the project's own discipline forbids
(see `docs/review/v15_cleanup_2026-10-11.md` for the same decision applied to
`docs/theory/`). This file therefore carries the additions and the defect register
verbatim, so the owner can merge them in a single controlled drift-disposition commit.

**Verification:** every arXiv identifier below was retrieved from
`https://export.arxiv.org/api/query` on the date in the last column. Titles, dates and
author lists are quoted from the API response. No entry is included on the strength of a
secondary source.

---

## A. New entries, proposed numbering [95]–[107]

### A.1 Direct novelty pressure — representation as a first-class compiler variable

| # | Reference | Verified | Why it matters |
|---|---|---|---|
| **[95]** | To, Quetschlich, Elsharkawy, Schulz, Wille, Kranzlmüller, "Evaluating the Effect of the Order of Optimization Passes in Quantum Circuit Optimization," arXiv:2609.29406 (2026-09-24) | 2026-10-17 | The **pass-ordering** counterpart of this project's listing-ordering result; MQT group (authors of MQT Bench, already ref. [69]). The single most likely novelty objection. Cite in §1.1 and §7.2 and state the distinction explicitly. |
| **[105]** | Yang, Li, Deng, "Representation-Dependent Recoverability in Quantum Compilation," arXiv:2609.29210 (2026-09-24) | 2026-10-17 | **New since the 2026-10-16 scan.** Proves an entropy lower bound $\overline{A}_p+(2p-1)S\ge(1-\delta)m\log_2 K_\varepsilon-h_2(\delta)$ on what a downstream compiler can recover across a representation change, and measures a per-generator toll under a preregistered protocol. Same *conceptual* claim as this project ("representation determines downstream capability"), different object (information-theoretic recoverability of phase data, not the combinatorial action space of a local rewriter), and — importantly — **already in the "provable bound" style** that Direction P0-1 targets. |
| **[106]** | Ye, Liang, Khan, "When Equivalent Quantum Circuits Lose Synthesis Choices," arXiv:2610.06142 (2026-10-05) | 2026-10-17 | **New since the 2026-10-16 scan.** Introduces *synthesis availability*: representation changes (OpenQASM round trips) remove high-level operations, so requested synthesis has no effect in **360/360** conditions; the MQT pipeline gains 37.2% two-qubit gates on an 8-qubit Grover circuit after an OpenQASM 2 interchange. A third independent 2026 demonstration that representation choice gates optimizer capability. |
| **[99]** | Rovara, Haag, Koch, Izaac, Sivarajah, Wille, Borgna, "Why Are We Unrolling? The Importance of Structured Quantum Programs for Compilation," arXiv:2609.16171 (2026-09-14) | 2026-10-17 | Structured-vs-unrolled argument; the generalisation frame that a theorem covering both axes would subsume. |

**Consequence for positioning.** Three independent 2026 papers now argue that
representation choice determines what a compiler can do ([95], [99], [105], [106]).
The project's differentiator is no longer "representation matters" — that is becoming
consensus — but **the certified landscape**: an exact, replayable map of the reachable
action space per source. The abstract and introduction must lead with the certified
object, not with the phenomenon.

### A.2 Methodological templates for the certified-barrier upgrade

| # | Reference | Verified | Why it matters |
|---|---|---|---|
| **[97]** | Kam, Mahasinghe, De Silva, Cadet, Wang, "An Exactness Barrier for ZX-Calculus Optimization of Synthesized Clifford+T Circuits," arXiv:2608.22801 (2026-08-24) | 2026-10-17 | **The template.** A per-instance computable lower bound that *explains* a near-null optimization. This is what the project's empirical "structural ceiling" must become. |
| **[100]** | Bruzzone, Cazzola, "A Multi-Dimensional, Per-Pass Empirical Study of the LLVM Optimization Pipeline," arXiv:2606.31238 (2026-06-30) | 2026-10-16 | Classical methodological twin: 113 cumulative prefixes, non-monotonicity 6.6–9.7%, back-loadedness 84.8%, and a search-free additive bound (46.35%). Supplies the measurement design for the representation × pass-order factorial. |
| **[101]** | Schifferer, Ullrich, Hack, "Augmenting Rewrite Rule Sets via Knuth-Bendix Completion," arXiv:2610.01246 (2026-10-01) | 2026-10-16 | Automatic rule generation — the direct attack on "the trichotomy is a library artefact". |
| **[103]** | Hong, Soi, Zhang, Aiken, "Rewrite System Showdown: Stochastic Search vs. EqSat," arXiv:2605.19005 (2026-05-18) | 2026-10-16 | Honest negative-control baseline for the EqSat route. |
| **[98]** | Laabs, "AlchemQ: Proof-Carrying Quantum Circuit Optimization with Per-Result Equivalence Certificates," arXiv:2609.19160 (2026-08-24) | 2026-10-17 | Certificate-protocol precedent: versioned certificates + standalone Apache-2.0 verifier + a real IBM Heron r2 pilot. |
| **[104]** | "Testing and Verification of Quantum Compilers through Assurance Contracts and Evidence," arXiv:2610.00255 (2026-09-24) | 2026-10-16 | Ready-made framing reference for the evidence-chain methodology. |
| **[107]** | Fujii, "Computational Complexity of Clifford Template Compilation: Are Quantum Computers Useful for Compiling Quantum Circuits?," arXiv:2609.35239 (2026-09-28) | 2026-10-17 | **New since the 2026-10-16 scan.** Complexity landscape for *template compilation*: NP∩BQP for commuting templates with unrestricted exponents; NP-complete for binary exponents even for CNOT-only exactly commuting operations; polynomial for commuting self-inverse actions, but NP-complete once the total repetition count is bounded. This is the missing complexity backdrop for this project's Phase-2b template matching, and a candidate route to classifying it. |

### A.3 Comparator and explanation candidates

| # | Reference | Verified | Why it matters |
|---|---|---|---|
| **[102]** | "Leveraging Phase Polynomials for Quantum Circuit Optimization" (PhasePoly), arXiv:2506.20624 (2025-06-25) | 2026-10-17 | Up to 50.00% gate reduction (34.70% avg) via a cross-block parity representation — a representation change that beats this project's local rewriting on exactly the families it classifies as IIIb. Must be engaged, not ignored. |
| **[96]** | Lee, Jeong, Kim, "Quantum Circuit Optimization by Graph Coloring," *Quantum* (2026), arXiv:2501.14447 | 2026-10-16 | Reduces depth minimisation of commuting operations to vertex colouring on a non-parallelisability graph — that graph is this project's commutation graph. Published in *Quantum*, a target venue. |
| **[108]** | Escofet, Almudéver, Abadal, Alarcón, "Quantum Circuit Pruning: From NISQ Architectures to Fault-Tolerant Operations," arXiv:2610.00669 (2026-09-30) | 2026-10-17 | **New since the 2026-10-16 scan.** Architecture-independent lower bound on fidelity cost vs. hardware routing model; up to 48.6% gate reduction with fidelity improvements. Evidence that "lower bound + hardware consequence" is a publishable combination — the exact shape of Direction P0-1 + P1-4. |
| **[109]** | "Discovering state-of-the-art quantum circuits with large language models," arXiv:2610.22367 (2026-10-15) | 2026-10-17 | Newest LLM-for-circuits result; relevant to Direction P2-6. |
| **[110]** | "Provably Optimal Quantum Circuits with Mixed-Integer Programming," arXiv:2510.00649 (2025-10-01) | 2026-10-17 | A second route (besides SAT) to global-optimality certificates for the BV family — directly relevant to upgrading Theorem 9. |

### A.4 Tool references (no arXiv identifier)

| # | Tool | Verified | Note |
|---|---|---|---|
| **[111]** | BQSKit (Berkeley Quantum Synthesis Toolkit, LBNL), `BQSKit/bqskit` | GitHub API 2026-10-17: 188★, last push 2026-08-11, not archived | Major SOTA compiler, absent from every comparison in this project. Add to the SOTA panel. |
| **[112]** | `qqq-wisc/tzap` | GitHub API 2026-10-17: 48★, last push 2026-10-16, not archived | "A very fast and scalable quantum circuit optimizer" — brand new, direct SOTA comparator and novelty risk. Pin the commit before benchmarking. |

---

## B. Defect register for `unified_references.md` (report only, not edited)

| Defect | Location | Detail |
|---|---|---|
| §P contradicts §L | line 353 vs line 237 | §P lists `[76] Hietala et al. (2022) Quartz superoptimizer (PLDI)`; §L's `[76]` is Xu et al., Quartz (correct). |
| §P contradicts §L | line 354 vs line 239 | §P lists `[77] Ravi et al. (2022) QUASAR compiler`; §L's `[77]` is Yang et al., equality saturation for quantum circuit optimization. |
| §P header vs §L | line 355 vs line 69 | §P claims `[20] Amy, Glaudell, Ross (2018)` was "missing from the original 42-reference list"; §L already contains it. The same over-claim applies to [5] and [6]. |
| Non-contiguous numbering | §L | `[74]` and `[81]` are removed placeholders, so §A–§M is not contiguous while §P counts them. |
| Stale repository URLs | `docs/analysis/archive/sota_availability.md` line 28; `docs/results/tket_bug_report_final.md` lines 4, 169 | `https://github.com/CQCL/tket` → the repository is now `https://github.com/Quantinuum/tket` (verified live 2026-10-17: 318★, last push 2026-10-08). Both files are path-bound in `release/prepaper_v12_capsule_inner_manifest.json`, so they were **not** edited; the correction is recorded here. |
| Unresolved tool homes | manuscript tool citations | `softwareQinc/quartz`, `gwwatkin/quanto` and `epiqc/voqc` all return 404. The PLDI'22 Quartz *artifact* repository resolves at `quantum-compiler/quartz-artifact` (9★, last push 2024-03-02); the live Quartz, Quanto and VOQC homes were **not** resolved within this run's GitHub API budget (rate limit). Resolve before citing URLs; do not guess. |

---

## C. Merge instruction for the owner

1. Apply §A as `[95]`–`[112]` in `unified_references.md` (or renumber to keep §L contiguous).
2. Fix the four §B consistency defects in the same commit.
3. Record the resulting hash change as one explicit drift-disposition entry, following the
   existing pattern in `release/prepaper_external_blockers.csv` /
   `docs/review/prepaper_final_audit_2026-08-10.md`.
4. Do **not** fold this file into `unified_references.md` without step 3; a silent merge
   is exactly the failure mode the release manifest exists to catch.

---

## D. Additions 2026-10-23 (E56/E57 round)

Retrieved from `https://export.arxiv.org/api/query` on 2026-10-23. Proposed numbering
continues §A: **[113]–[116]**. Still additive only — `unified_references.md` remains
unmodified.

| # | Reference | Verified | Why it matters |
|---|---|---|---|
| **[113]** | "Fast Template Matching for Quantum Circuits Using Hypergraph," arXiv:2610.29095 (2026-10-21) | 2026-10-23 | Newest representation paper. Replaces the DAG template-matching representation with a *hypergraph* that collapses commutativity classes, and reports lower matching complexity. This is the closest published work to the E56 criterion's object (commutativity classes as a data structure), and it must be compared explicitly in the related-work section or the criterion will read as a re-derivation. |
| **[114]** | "Complexity Thresholds for the Constrained Colored Token Swapping Problem," arXiv:2601.09681 (2026-01-14) | 2026-10-23 | Proves PSPACE-completeness for constrained coloured token swapping. This is the **hardness source** for Direction P1-2: listing-reachability under a commutation constraint is a constrained token-swapping problem, so the order class is polynomial exactly where the constraint graph is a path. |
| **[115]** | "Settling Weighted Token Swapping up to Algorithmic Barriers," arXiv:2507.22450 (2025-07-30) | 2026-10-23 | Weighted token swapping with algorithmic lower bounds. Supplies the language for "distance to a reachable configuration" that $D_{\min}$ instantiates in the unweighted case. |
| **[116]** | "OpenQudit: Extensible and Accelerated Numerical Quantum Compilation via a JIT-Compiled DSL," arXiv:2511.16585 (2025-11-20) | 2026-10-23 | Current numerical-synthesis baseline missing from the SOTA panel (S1–S5). Needed before any "no tested compiler reduces them" claim is restated. |

### D.1 Repository-path corrections found on 2026-10-23

| Item | Correction | How verified |
|---|---|---|
| MQT QCEC | `mqt/qcec` returns 404. Live home is `munich-quantum-toolkit/qcec` (120★, last push 2026-10-22). | GitHub REST, authenticated. |
| Quanto | No public GitHub repository resolves under that name; the 2026-10-17 note that `gwwatkin/quanto` 404s is confirmed, and no replacement was found. Cite the paper, not a URL. | GitHub REST search. |
| tket | `CQCL/tket` redirects (HTTP 301) to `Quantinuum/tket`; already recorded in §B, still unfixed in the two path-bound files. | GitHub REST redirect resolution. |

### D.2 Status of the §B defect register

Unchanged. The owner merge described in §C has still not been performed, and the
2026-10-23 round again declined to touch `unified_references.md` for the same reason:
it is path-bound in three release manifests, so an editorial merge would create a
sixteenth drift entry before the re-pin decision is made.

---

## §E Round 11 additions (2026-10-24)

Retrieved from `https://export.arxiv.org/api/query` on 2026-10-24 (294 records from the
28-query base sweep plus 121 from 14 round-specific queries; see
`docs/review/science_boost/2026-10-24_literature_scan/`). Numbering continues §D:
**[117]–[119]**. Additive only — `unified_references.md` remains unmodified for the same
drift reason as §D.2.

| # | Reference | Verified | Why it matters |
|---|---|---|---|
| **[117]** | "Quantum Term Rewrite Systems: Applications to Complexity Analysis," arXiv:2607.20170 (2026-07-22) | 2026-10-24 | **The single most important new citation.** It gives a general framework for *termination certificates* and *reduction-length bounds* on quantum rewrite systems. The project's closure fixpoint is an instance of that framework, and Thm 3/4 of `docs/theory/closure_termination_and_optimality_2026-10-24.md` should be presented as a concrete instance rather than as a new theory. Omitting it invites "this is a special case of known TRS termination analysis". |
| **[118]** | "E-Graphs as a Persistent Compiler Abstraction," arXiv:2602.16707 (2026-02-18) | 2026-10-24 | Tamagoyaki: e-graph state kept through the whole compilation flow. Relevant to the "closure vs equality saturation" positioning: e-graphs *discover* equivalences, the closure *decides* a fixpoint. Needed if the paper argues that saturation and closure answer different questions. |
| **[119]** | "Equality saturation theory exploration à la carte," arXiv:2609.14527 (2026-09-13) | 2026-10-24 | Enumo, a DSL for programmable rule inference. Context for the rule-library-completeness argument (the project's `e44_core_v1` is a hand-curated 149-rule subset); a reviewer will ask why the library was not inferred. |

### E.1 Nothing in this round displaces an earlier must-cite

`2610.29095` [113], `2601.09681` [114], `2507.22450` [115], `2511.16585` [116] remain
unmerged and remain required reading. The four "zero coverage" ids flagged in earlier
rounds (`2609.20873`, `2610.02029`, `2609.04160`, `2610.01024`) are still absent from the
catalogue; that defect register is unchanged.

### E.2 Ecosystem snapshot corrections (2026-10-24, GitHub REST, authenticated)

| Item | Correction |
|---|---|
| Quartz | `quartz-tools/quartz` returns 404. Live home is **`quantum-compiler/quartz`** (93★, last push 2026-10-06); the artifact repo is `quantum-compiler/quartz-artifact` (9★). |
| Qiskit | `Qiskit/qiskit` 7,922★, last push **2026-10-23** — the most active of the set. Evidence remains pinned at 2.4.1. |
| tket | `Quantinuum/tket` 318★, last push 2026-10-08. |
| pyzx | `zxcalc/pyzx` 553★, last push 2026-10-22. |
| BQSKit | `BQSKit/bqskit` 188★, last push 2026-10-17. |
| tzap | `qqq-wisc/tzap` 48★, last push 2026-10-16. |
| MQT QCEC | `munich-quantum-toolkit/qcec` 120★, last push 2026-10-23. **Now usable on this machine** — see `docs/review/science_boost/2026-10-24_qcec_oracle/`. |

---

## §F Round 12 additions (2026-10-25)

Sweep: 20 structured arXiv queries → **274 unique records** (≥2023, latest 2026-10-21),
authenticated GitHub REST over 10 repositories, 2 web searches. Package:
`docs/review/science_boost/2026-10-25_literature_scan/`.
Channels unavailable this round and disclosed: Tavily (no key), Exa (no MCP server),
multi-search-engine (no key), arxiv-reader (no LLM key), citation-manager (no Crossref
dependency), github-trending (replaced by authenticated REST).

| # | Reference | Verified | Why it matters |
|---|---|---|---|
| **[120]** | "Exact $T$-counts of CCZ layers from an isotropy bound," arXiv:2610.01024 (2026-10-01) | 2026-10-25 | **The most dangerous citation of this round.** It gives a per-instance lower bound on the $T$-count of every third-level diagonal gate, computable by Gaussian elimination, and proves the CCZ-layer count exactly. The project's Lemma 1 (`R >= |supp(f)|`) is the same *kind* of statement in a simpler setting and is a literature fact, not a new theorem. Must be cited, and the novelty claim must be restricted to the gap decomposition and the Hadamard-annihilation wall. |
| **[121]** | "On the completeness of transformation rules in reversible logic synthesis," arXiv:2607.19059 (2026-07-21) | 2026-10-25 | Proves that practically adopted transformation rule sets are already complete for reversible circuits (no ancillae, no garbage). Directly attacks the framing "the hand-curated rule library is the bottleneck". Any claim about rule-library incompleteness must be stated relative to this result. |
| **[122]** | "Augmenting Rewrite Rule Sets via Knuth-Bendix Completion," arXiv:2610.01246 (2026-10-01) | 2026-10-25 | Rule sets for equality saturation can be completed automatically. Raises the obvious reviewer question "why not run KBC instead of curating 1,474 rules?" — and points at the cheapest way to answer it (run it and measure). |
| **[123]** | "Undecidability of Confluence for Binary Length-Reducing Cycle Rewriting," arXiv:2608.18859 (2026-08-19) | 2026-10-25 | Confluence of finite length-reducing cycle rewriting over a fixed two-letter alphabet is $\Pi^0_1$-complete. **No general confluence theorem can be claimed.** Round 11's plan to prove confluence via Newman's lemma must be downgraded to a per-panel empirical statement plus cost invariance. |
| **[124]** | "Associativity and Commutativity in Equality Saturation," arXiv:2610.01198 (2026-10-01) | 2026-10-25 | Native AC matching in relational e-matching. The commutation closure is an AC-style canonicalisation; this is the closest methodological relative and must be compared explicitly. |
| **[125]** | "Depth-Optimal Quantum Compilation," arXiv:2609.34659 (2026-09-28) | 2026-10-25 | First constant-depth single-qubit synthesis with a **matching** $\Omega(\log\log(1/\varepsilon))$ lower bound. Sets the current bar for what "optimal" means in a top-tier compilation paper: construction plus matching bound. |
| **[126]** | "CNOT-Distance is NP-complete under all-to-all connectivity," arXiv:2608.03825 (2026-08-04) | 2026-10-25 | Supplies the hardness anchor for the content class (cross-wire monomial merging is a CNOT-routing problem). |
| **[127]** | "Parallelizable Exact Synthesis of Quantum Circuits via Semi-Tensor Product," arXiv:2607.24195 (2026-07-27) | 2026-10-25 | Candidate external-validity comparator for exact synthesis; not yet benchmarked here. |
| **[128]** | "Normal-Form Characterization of Adaptivity and Entanglement in Pauli-Based Computation," arXiv:2610.30315 (2026-10-21) | 2026-10-25 | Normal-form characterisation of a computation model. Related-work anchor for the "what a normal form buys you" argument. |

### F.1 Non-arXiv competitive signal (verify before citing)

2026-10-16: Anthropic reported that Claude designed quantum circuits beating published
results on 8 task classes (up to ~17x gate reduction), with an automatic evaluation loop,
simulation and formal verification, **not** validated on hardware. Relevance: the
"LLM + independent verifier" loop is now a competing paradigm, and the project's
certificate/verifier layer is the judgement layer of that paradigm. No primary technical
report was retrieved this round, so it is recorded as competitive context only, not as a
citation.

### F.2 Ecosystem snapshot corrections (2026-10-25)

| Item | Correction |
|---|---|
| Qiskit | **2.6.1 released 2026-10-22** (2.6.0 was 2026-10-16). E63 re-ran the E61 panel on 2.6.1: the L3 non-monotonicity is **gone** (0/101, 0 residual `rz` pairs). Evidence remains pinned at 2.4.1. |
| Quartz | `quantum-compiler/quartz`, v0.3.2, last release 2025-12-10, last push 2026-10-06. |
| pyzx | `zxcalc/pyzx` v0.10.7 (2026-10-01). |
| tket | `Quantinuum/tket` v2.18.5 (2026-10-08). |
| BQSKit | 1.2.1 (2025-08-30), last push 2026-10-17. |
| tzap | v0.8.0 (2026-10-11). |
| MQT QCEC | v3.11.0 (2026-10-09), last push 2026-10-24. |
| Quanto / VOQC | Both queried paths return 404; correct repository paths still unidentified. |
