# Universal-Law Assessment — Representation Sensitivity, Structural Ceilings, and Predictive Advantage

Worker: Theoretical Physicist (Theory) — Universal Law Discovery domain.
Date: 2026-07-20.
Scope: `docs/theory/` (framework.md, formal_results.md, nontrivial_upgrades.md,
phase2_lower_bound_strengthening.md, QMA_hardness_draft.md),
`docs/manuscript/manuscript.md` (read-only), `docs/references/`,
`data/v6/ceiling_repair/`.

This document answers four questions posed to the Theory domain:

1. Do any of the project's formal results rise to the level of a *universal law*
   (physics sense: representation-, family-, and algorithm-independent
   regularities with non-trivial content)?
2. What is the single most surprising result, and what are its
   cross-disciplinary connections?
3. Do the manuscript's citations and novelty claims survive independent
   verification?
4. How far is the work, quantitatively and honestly, from Nature/Science tier?

All quoted numbers were re-derived from canonical artifacts (manuscript tables,
`data/v6/ceiling_repair/repair_summary.json`, E12/E15/E20 comparison tables)
on 2026-07-20; nothing is cited from memory.

---

## 1. Universality verdict, theorem by theorem

Verdict classes:

- **U-triv** — universal within stated scope but elementary (counting- or
  definition-level).
- **RC** — representation-conditional: true, but the *content* changes with
  the data-structure representation.
- **FS** — family-specific.
- **FAU** — falsified as a universal statement (survives only in weakened form).
- **ML-cand** — candidate meta-law: non-trivial, wide scope, survives scrutiny
  inside an explicitly stated boundary.

| Result | Statement (compressed) | Verdict | Reason |
|---|---|---|---|
| Thm 1(a) | $\mathbb{E}[\lvert\mathcal{A}_{\text{adj}}\rvert] \le n(d-1)\left[(1-\rho)^2/g_1^2 + \rho^2/(g_2(n-1))\right]$ under WCL | U-triv | Birthday-paradox-grade first-moment counting over a finite gate alphabet. Correct and useful as a design rule of thumb; not a law. |
| Thm 1(b) | Under LBL, $n \ge 2 \Rightarrow \mathcal{S}_1(C) = \emptyset$ for every $C$ | RC | True for every circuit — but it is a theorem *about a data structure*, not about circuits. Its entire content is "listing adjacency $\ne$ wire adjacency". Universal across circuits; vacuous across representations. |
| Thm 2(a) | $R_1(C) = 0$ iff $\mathcal{S}_1(C) = \emptyset$ (plus rotation-merge clause) | U-triv | Near-definitional for the Phase-1 move set. |
| Thm 2(c) | Insertion-debt invariant: $k$ INSERTIONs $\Rightarrow$ net gate change $\ge 0$ | ML-cand | A genuine conservation law for local rewriting; see §1.1. |
| Thm 2(d) | INSERTION+SWAP+COMMUTATION cannot exceed the pre-existing accessible inverse-pair structure $\mathcal{S}_{1+2}(C)\setminus\mathcal{S}_1(C)$ | ML-cand | Strongest result in the corpus; wire-order invariant; see §1.1. |
| Cor 2.1 | All four Phase-1 optimizers share the ceiling $R_1^*(C)$ | FAU (as "universal desert") | True per circuit for the tested move sets, but any universal "~0% everywhere" reading is falsified twice: the CNOT family has $R_1^* = 100\%$, and WCL relisting moves the same random ensemble from 0.0000% to 7.83%. Survives only as "algorithm-independence conditional on (move set, listing)". |
| Thm 5–8 | Complexity classification; context-dependent Phase-2 advantage constructions | FS → RC | Constructive per-family results; the context-dependence is itself the anti-universal message. |
| Thm 9 | BV Phase-2b upper bound $n/(4.5n+4)$ | FS | Single-family bound; honest and non-trivial, not exportable. |
| Prop 1 (corrected), Obs 1 | LBL generator ⇒ zero variance is structural | RC | Same content class as Thm 1(b). |
| C1/C2 (conjectures) | Listing/window-conditional ceiling tightness | RC | Already scoped as conditional. |

### 1.1 The meta-law candidate: conservation of contraction opportunities (Thm 2c/2d)

The 2c/2d pair is the only result with the *shape* of a physical law: an
invariant (the insertion debt $\Delta$; the wire-order of pre-existing gates)
constraining all trajectories of a stochastic dynamics (RLS/SA/GA move
sequences), with a falsifiable consequence (net reduction bounded by
pre-existing accessible structure), confirmed empirically — INSERTION creates
new $\mathcal{S}_1$ elements in 1000/1000 probe trials yet yields zero net
reduction in 5000/5000 trials (formal_results.md, Appendix A).

Two honest boundaries:

1. **Scope of the move set.** The invariant holds for {REMOVAL, SWAP,
   COMMUTATION, INSERTION}. Production compilers escape it precisely by
   violating its premises: template matching and phase-polynomial resynthesis
   create contractions that are *not* latent as wire-level inverse pairs
   (E12/E15/E20: Qiskit O3 39.3% on VQE, 35.5% on HardwareEfficient, 61.2% on
   IQP where the prototype move set yields 0.0–0.5%). It is therefore a law of
   *local involution-pair rewriting*, not of quantum circuit optimization as a
   whole.
2. **Risk of trivialization.** In term-rewriting terms this is a
   Lyapunov/potential argument; the mathematics is elementary. Its value is
   empirical surprisingness (§2), not depth.

Recommendation: state it as the project's central meta-law — *identity
insertion cannot create contraction opportunities beyond pre-existing
accessible structure* — with the move-set boundary printed inside the
statement.

### 1.2 What a true universal law would look like here, and why we do not have one

A physics-grade law in this domain must be representation-independent. The
project's own results prove Phase-1 ceilings *cannot* be
representation-independent (Thm 1(b) + E19). The natural candidate — a
listing-invariant ceiling theory over wire-level structure — is only partially
built: Phase-2a (commutation closure) is listing-invariant, but Phase-2b
(window-limited) reintroduces a parameter, and no theorem currently bounds
reduction over the space of *all valid listings* (the manuscript itself flags
this as open, §3.5). Until a listing-invariant invariant exists, the strongest
honest formulation is the **representation-determinism principle**:

> *The reachable action space of a local optimizer is a property of the
> (object, representation) pair, not of the object alone.*

This is universal and non-trivial as a design principle, but it is already
known in spirit in classical compiler construction (IR design, canonicalization
passes) and in representation learning. It should be claimed as a
*formalization and quantification in the quantum setting*, not as a discovery
ex nihilo.

---

## 2. The most surprising result, and its cross-disciplinary connections

### 2.1 Primary: the E19 listing flip

Same circuits, same optimizer, same seeds; only the data-structure ordering of
gates changes (LBL → WCL, an $O(m \log m)$ relabeling that preserves the
unitary exactly). Mean gate reduction moves from **exactly 0.0000%** (E1:
25,000 trials, zero variance, max 0.00%) to **7.83%** (std 3.95%, max 33.33%,
fidelity 1.0; E19: 5,000 circuits × 2 listings = 10,000 rows).

Why this is the most surprising result in the corpus:

- A null result replicated across 25,000 trials and five experiment series
  (E1–E5) was naturally read as landscape hardness — an "optimization desert".
  It was, in fact, 100% a representation artifact: provable in four lines
  (Thm 1(b)) once seen, invisible before.
- It inverts the usual direction of explanation: not "the object is hard" but
  "the view of the object is incomplete". The desert is in the map, not the
  territory.
- It is algorithm-independent: four optimizers (Greedy, RLS, SA, GA), 45,500
  trials, all agree on the ceiling under a fixed listing. Representation choice
  dominates algorithm choice — a reversal of the field's default research
  question.

### 2.2 Supporting surprises

- **INSERTION sterility.** An optimizer can manufacture unlimited *apparent*
  search space with zero expected progress: INSERTION creates action-space
  elements in 100% of probe trials (1000/1000) and produces zero net reduction
  in 100% of outcome trials (5000/5000). Thm 2(c) makes this a theorem.
- **The compiler gap is again representational.** On identical circuits, Qiskit
  O3 reaches 76.1% (RandomClifford) / 61.2% (IQP) / 39.3% (VQE) where the
  listing-based prototype reaches 16.5% / 0.5% / 0.0% (E12/E15/E20 tables).
  Production compilers operate on DAG/moment representations — once more the
  representation, not a smarter search.
- **Ceiling-proxy tightness.** A purely structural quantity (computed from the
  circuit, no optimizer run, no leakage) predicts the actually achieved
  reduction at pooled Pearson $r = 0.988$, Spearman $\rho = 0.928$,
  MAE = 0.009 (`data/v6/ceiling_repair/repair_summary.json`,
  `ceiling_proxy_tightness`). The project's "predictive advantage" thesis
  survives a leak-free rebuild (§3 of the wave-1 report).

### 2.3 Cross-disciplinary connections (for the Discussion section)

1. **Machine learning — representation determines the learnable function
   class.** The listing flip is an exact analog of feature engineering / kernel
   choice: the same data, re-encoded, moves a problem from unlearnable to
   learnable. It also mirrors the adversarial-robustness lesson that a model's
   failure can be entirely an encoding failure. The ceiling-proxy result (§2.2)
   is the compiler-side counterpart of predicting generalization from
   data/structure rather than from the learner.
2. **Classical compilers — phase ordering and IR design.** The phase-ordering
   problem (pass order changes outcomes) and instruction scheduling's
   dependence on program linearization are the classical counterparts; WCL
   preprocessing is a *canonicalization* pass, and "canonicalize before
   peephole" is standard practice in classical toolchains (automatic
   peephole-rule inference since the late 1980s assumes normalized forms). Our
   contribution is the quantum-circuit instance plus a proof of *why* it
   matters.
3. **Statistical physics.** Three contacts: (i) measure concentration on
   finite-alphabet involution sequences explains Thm 1(a)'s exponential rarity
   of adjacent inverse pairs at large alphabet — an entropic desert,
   mechanistically distinct from barren plateaus (which are dimensional, not
   representational; worth one paragraph of contrast in the manuscript);
   (ii) commutation blocks behave like percolation clusters — Phase-2 reduction
   appears when commuting structure spans the window (Oracle/RandomClifford vs
   QFT/GHZ/SurfaceCode); (iii) the context-dependent-advantage constructions
   (Thm 7 family) are formally frustration phenomena — global constraints
   (separator gates) block local relaxation moves.
4. **Term rewriting / algebra.** Thm 2(c)/2(d) are invariant (Lyapunov)
   arguments over a string-rewriting system. Two open questions inherit
   standard rewriting vocabulary: confluence of the Phase-1+2 relation modulo
   commutation (Church–Rosser), and the listing-invariant ceiling of §1.2 as a
   normal-form-invariance question.

---

## 3. Literature verification and novelty

### 3.1 Method

Independent verification of the manuscript's reference list: scholar plugin
(four passes; scripts and raw CSV/JSON evidence under
`data/v6/ceiling_repair/scholar/`), the arXiv API, direct arXiv abstract-page
fetches, and web search (all on 2026-07-20). Criteria: (a) the work exists;
(b) author list, title, venue, year, and identifiers match as cited.

### 3.2 Audit result

**Fabricated or unverifiable-as-cited (must fix before any submission):**

| Ref | Cited as | Finding | Key evidence |
|---|---|---|---|
| [22] | N. de Beaudrap, S. Glendinning, Q. Zhang, "Faster resynthesis with the ZX-calculus," QPL 2022, arXiv:2206.10843 | **Fabricated.** Title search on arXiv: 0 hits; no quantum author "Glendinning" exists; arXiv:2206.10843 is an unrelated ML paper (debiased classifiers; Kim et al.). The real de Beaudrap 2022 ZX paper is "Circuit Extraction for ZX-diagrams can be #P-hard" (de Beaudrap, Kissinger, van de Wetering, ICALP 2022, arXiv:2202.09194) — whose content (extraction *hardness*) contradicts the manuscript's "faster resynthesis" gloss. The supporting paragraph in `docs/references/literature_review.md` (lines 100–107) is likewise unreliable. | arXiv API author/title queries; arxiv.org/abs/2206.10843; arxiv.org/abs/2202.09194 |
| [70] | A. Wang, S. Lu, X. Wang, "QASMBench," arXiv:2108.10472 | **Authors and arXiv ID do not match the real work.** QASMBench is Ang Li, Samuel Stein, Sriram Krishnamoorthy, James Ang, ACM TQC 2022, arXiv:2005.13018, DOI 10.1145/3550488. | scholar pass; arXiv |
| [81] | K. Patel, J. Shapira, I. L. Markov, "Quantum circuit optimization: A survey," ACM Comput. Surv. 55(9):178, 2022, arXiv:2210.12035 | **Fabricated.** arXiv:2210.12035 is a computer-vision paper (BlanketGen, ENBENG 2023). No such ACM CSUR survey exists (three scholar passes; two web searches). Closest real surveys: Saeedi & Markov, ACM CSUR 45(2), 2013 (reversible circuits); Karuppasamy 2025 (MDPI, "A Comprehensive Review of Quantum Circuit Optimization"). Patel and Markov are real researchers (QIC 2008) — the survey as cited is not. | arxiv.org/abs/2210.12035; web search ×2 |

**Real work, wrong bibliographic details:**

| Ref | Issue |
|---|---|
| [16] Kliuchnikov et al. | Real paper: "Fast and efficient exact synthesis of single qubit unitaries generated by Clifford and T gates," PRL **110**, 190502 (2013); arXiv:1206.5236 as cited is correct. Manuscript cites PRL **111**, 080502 and (in `literature_review.md`) a different title. Fix volume/page/title. |
| [67] Riu et al. | Real: Quantum **9**, **1758** (2025); arXiv:2312.11597 as cited is correct. Manuscript cites article **1634** — wrong. |
| [69] MQT Bench | Real first author is **N. Quetschlich** (with L. Burgholzer, R. Wille); arXiv:2204.13719 as cited is correct. Manuscript cites "C. Nitsch" — wrong author. |
| [20] Amy/Glaudell/Ross | Author–topic real (phase-polynomial synthesis series), but the "npj Quantum Information 4:43 (2018)" venue/title combination is unverified; the verified series member is Quantum 4, 252 (2020). Recheck against the intended paper. |
| [61] Iten et al. | Real (ACM TQC 3(1), 2022; arXiv:1909.09119 correct). Normative page range seen in the wild is 1–41; manuscript cites 1–44. Low priority. |

**Verified true (30+ spot-checked):** [1], [2], [4], [8], [9], [13], [25],
[27], [28], [29], [30], [33], [35], [38], [40], [41], [42], [43], [45], [48],
[51], [61], [62], [63], [65], [66], [67]\*, [68], [69]\*, [78], [82]
(\* = real with detail errors as above). Standard works ([10] Maslov Toffoli,
[21] Duncan ZX Quantum 4:279, [32] Downey–Fellows, [39] Farhi QAOA,
[46]/[47] Qiskit/Cirq, [50] Fowler, [56] Yamashita IEICE, [64] Quarl) assessed
as real from corroborating citations. Full evidence:
`data/v6/ceiling_repair/scholar/`.

### 3.3 Missing citations (manuscript must add)

1. **VOQC** — Hietala, Rand, Hung, Wu, Hicks, "A verified optimizer for quantum
   circuits," POPL 2021. Present in `docs/references/unified_references.md`
   (as [59]) but **absent from the manuscript's reference list** (numbering
   jumps [56] → [61]). This is the closest prior optimizer-formalization work;
   its absence is a reviewer-red-flag gap.
2. **Equality Saturation for Quantum Circuit Optimization** (Yang, Raun, Tao,
   Gu; verified to exist via scholar) — e-graphs are exactly a
   representation-normalization technology; must be discussed alongside WCL
   canonicalization.
3. **SSR: Swapping-Sweeping-and-Rewriting** (Huang et al., 2025; verified via
   scholar) — recent peephole-class optimizer; needed for the SOTA comparison.

### 3.4 Novelty verdict (absence ≠ proof)

Targeted searches (N1–N10: "structural ceiling" in quantum optimization;
listing/gate-ordering sensitivity of peephole optimizers; structural features
predicting compilability) surfaced **no direct precedent** for: (i) a formal
listing-model taxonomy with an empty-action-space theorem; (ii) quantified
listing sensitivity (the 0.0000% → 7.83% flip); (iii) ceiling proxies
predicting achieved reduction at $r \approx 0.99$. Classical analogs exist
(peephole-rule inference since the 1980s; the phase-ordering literature), so
frame as "first formalization in quantum compilation", not "first discovery of
representation sensitivity". Absence of evidence in these search passes is not
proof of absence; a citation-graph pass by the integration worker is
recommended before submission.

---

## 4. Distance to Nature/Science — honest quantitative assessment

Current contribution class: quantum software engineering / compiler theory;
`framework.md` already concedes the work is not a physics discovery. Concrete
gaps, as of 2026-07-20:

| Gate | Current state | N/S-tier requirement |
|---|---|---|
| Hardware validation | None; all results classical, exact fidelity at $\le 12$ qubits | Compilation-time or fidelity benefit demonstrated on hardware (IBM/IonQ class) at algorithm-relevant scale |
| Statistical universality | 15 families, tens of circuits per family per condition; family-mean LOFO $n = 15$ ($r = 0.059$ — underpowered) | $\ge 50$ families × hundreds of circuits; pre-registered-style predictive validation (theorem first, experiment second — the manuscript's own methodological note, §3.5, concedes the reverse chronology) |
| Theory depth | Elementary combinatorics; QMA completeness conditional on circuit lower bounds (an open, possibly Millennium-class obstacle); Thm 3 sketch only | Either unconditional hardness (complete the Feynman–Kitaev roundtrip lemma) or a listing-invariant ceiling theory (§1.2) |
| Mechanism attribution | Pass-level attribution on 5/15 families (E12 isolation) | All 15 families, plus an audit of whether production compilers already perform WCL-like reordering (manuscript §7.5 open question — if they do, the flagship practical claim weakens) |
| Predictive model (repaired, this domain) | MAE 0.0172, pooled $r = 0.977$, $\rho = 0.853$, $R^2 = 0.954$ (LOFO; mechanism-gate + RF hybrid, gate selected post hoc — see the wave-4 addendum below), beats predict-0 baseline 0.0963; ceiling proxy $r = 0.988$; CNOT held-out failure closed (fold MAE 0.000); family-mean regression ($n = 15$, $r = 0.059$) remains a failure | External validation on unseen families/tools without family-identity leakage |

Realistic venue ladder: the current package — after the §3.2 citation fixes and
an honest WCL-audit caveat — fits Quantum / ACM TQC / PRX Quantum. Nature-tier
requires the hardware, scale, and predictive-validation rows above: two
experiment series plus one theory campaign — months, not weeks.

---

## 5. Pointers to artifacts produced by this domain

- Ceiling-model repair: `experiments/ceiling_model_repair.py` (rewritten;
  previous version backed up as `.bak-20260720-230053`), outputs in
  `data/v6/ceiling_repair/` (`diagnosis.json`, `repair_summary.json`,
  `repair_lofo_results.csv`, `mechanism_features.csv`).
  Reproduction: `/d/Downloads/miniforge3/python experiments/ceiling_model_repair.py`
  (~1 min with cached features).
- Citation-audit raw evidence: `data/v6/ceiling_repair/scholar/`.
- Wave-1 completion report: `docs/review/wave1/universal_law.md`.

---

## Addendum (2026-07-21, wave 4): CNOT saturation-regime intervention

**Context.** The §4 predictive-model row and manuscript §6.6 report the
repaired mechanism-informed model (mechanism features + single-stage
RandomForest, LOFO): pooled MAE 0.0695, pooled r = 0.722, ρ = 0.847 — with
the held-out CNOT fold as the dominant residual (fold MAE 0.7453, systematic
underestimation of the one fully saturated family). Wave 4 attempted to close
that residual. All numbers below are produced by
`experiments/ceiling_model_repair.py --regime` (seed 42, LOFO protocol
identical to Part 3); raw outputs:
`data/v6/ceiling_repair/regime_intervention_summary.json` and
`regime_intervention_results.csv`. The V0 reproduction matches the published
Table 18 row exactly, including bootstrap CIs.

**Diagnosis (computed, not assumed).** With CNOT held out, the training
target's 99th percentile is 0.4156 and exactly **one** saturated (y ≥ 0.99)
training row exists (Oracle, n = 4). A RandomForest regressor predicts
leaf-target averages and therefore cannot extrapolate to y = 1.0 for a family
whose feature signature is absent from training. The signature itself is
unambiguous: CNOT chains have Phase-1 action density exactly 0.5 (every gate
participates in an adjacent cancellable inverse pair) versus a maximum of
0.0345 across all 530 non-CNOT circuits — a >14× margin.

**Interventions tested (per-fold rows in regime_intervention_results.csv):**

| Variant | Pooled MAE [CI95] | Pooled r [CI95] | ρ | R² | CNOT fold MAE |
|---|---|---|---|---|---|
| V0 baseline = published best (mech + single-stage RF) | 0.0695 [0.0539, 0.0865] | 0.722 [0.666, 0.794] | 0.847 | 0.393 | 0.7453 |
| V1 + saturation indicator features | 0.0674 [0.0524, 0.0836] | 0.761 [0.705, 0.830] | 0.853 | 0.440 | 0.7125 |
| V2 learned two-stage (saturation classifier → regressor) | 0.0693 [0.0538, 0.0864] | 0.736 [0.690, 0.794] | 0.848 | 0.394 | 0.7453 |
| V3 rule gate: structural bound ≥ 0.99 → predict bound | 0.0176 [0.0130, 0.0225] | 0.974 [0.957, 0.987] | 0.853 | 0.948 | 0.0000 |
| **V4 rule gate: 2·Phase-1 density ≥ 1 → predict min(1, 2·d)** | **0.0172 [0.0129, 0.0218]** | **0.977 [0.963, 0.987]** | **0.853** | **0.954** | **0.0000** |
| V5 Ridge linear (extrapolating) | 0.0492 [0.0395, 0.0596] | 0.954 [0.912, 0.984] | 0.682 | 0.759 | 0.4495 |

**Outcome — success on the pre-registered criterion** (CNOT fold MAE < 0.1
with no pooled degradation). V4, a mechanism-derived saturation gate (each
adjacent cancellable inverse pair removes 2 gates, so density d ≥ 0.5 implies
full Phase-1 reduction), eliminates the CNOT residual exactly (0.7453 →
0.0000) and leaves every other fold numerically identical to the baseline —
the gate fires only on CNOT rows. V3 is nearly as good but has one false
positive (a RandomClifford n = 4 row with bound 1.0 but realized reduction
0.345), so V4 is the recommended config. **Negative results, recorded
honestly:** indicator features (V1) barely help and a learned two-stage
classifier (V2) fails completely on this fold — with a single saturated
training example the classifier never fires on the CNOT signature —
confirming the residual was an *extrapolation* failure of tree regressors,
not a missing-feature failure. Caveat for the record: the V4 gate is derived
from the Phase-1 mechanism, not fitted to data, but its *selection* was
informed by the observed failure — this is a post-hoc model revision
validated on a single dataset; claims should be phrased accordingly.

**Impact on manuscript §6.6 (decision deferred to the next wave — this
addendum does not modify the manuscript).** If V4 is adopted, the following
published numbers change:

| Location | Quantity | Published (V0) | Wave-4 candidate (V4) |
|---|---|---|---|
| §6.6 Table 18, best row | Pooled MAE | 0.0695 [0.0539, 0.0865] | 0.0172 [0.0129, 0.0218] |
| §6.6 Table 18, best row | Pooled Pearson r | 0.722 [0.666, 0.794] | 0.977 [0.963, 0.987] |
| §6.6 Table 18, best row | Pooled Spearman ρ | 0.847 | 0.853 |
| §6.6 Table 18, best row | Pooled R² | 0.393 | 0.954 |
| §6.6 prose; §7.6 item 6 | CNOT fold MAE | 0.745 (listed as a failure mode) | 0.000 (failure mode closed by the saturation gate) |
| Abstract, §1.3, §6.1.1/§7, conclusion | "MAE 0.0695 vs 0.0963 baseline; pooled r = 0.722" | as stated | MAE 0.0172; pooled r = 0.977 |
| — | predict-0 baseline MAE | 0.0963 | unchanged |

Adopting V4 also changes the *character* of the model: it becomes a hybrid
deterministic-mechanism gate + RF regressor, which the manuscript should
describe explicitly, and the §7.6 "CNOT fold MAE 0.745" limitation would need
rewording (residual closed by a mechanism rule; the learned-component limits
— family-mean regression r = 0.059, 11/15 undefined-Pearson folds,
classifier F1 = 0.075 — are unaffected by this intervention and still stand).

---

## Addendum 2026-07-21 (wave 6): PART 5 — five E27 families join the LOFO evaluation (n = 15 → 20 families)

**Scope.** Wave 5 generated five new circuit families (QPE,
TrotterHamiltonian, QuantumVolume, WState, RepetitionCode;
`data/v8/e27_new_families/`) to lift the family-mean regression from n = 15
to n = 20. `experiments/ceiling_model_repair.py --part5` now evaluates the
wave-4 V4 hybrid model (mechanism saturation gate + RF) under LOFO on all 20
families. Because E27 ran its three optimizers independently and never ran
the E21 naive pipeline that defines the target, PART 5 regenerates every
unique E27 circuit deterministically and re-runs the exact E21 naive
pipeline (Phase1 → Phase2(window=10) → Phase1) to obtain identically defined
`gate_reduction` labels. Regeneration was verified on all 225 circuit specs
(size match + exact Phase-1-reduction reproduction against the CSV), and 103
duplicate circuits (WState/QPE parameter invariance, RepetitionCode
param_n = 3 ≡ 4) were dropped, leaving 122 unique circuits; combined
dataset: 692 rows / 20 families. The V4 model on the original 15 families
was reproduced exactly (MAE 0.017240047, r 0.976939886 — matches
`regime_intervention_summary.json` to all printed digits) before any 20-family
number was trusted.

**Headline results (all LOFO, seed 42, mechanism features).**

| Quantity | 15 families (wave-4 V4) | 20 families (PART 5 V4) |
|---|---|---|
| Pooled MAE [CI95] | 0.0172 [0.0129, 0.0218] | 0.0188 [0.0144, 0.0236] |
| Pooled Pearson r [CI95] | 0.977 [0.963, 0.987] | 0.967 [0.948, 0.979] |
| Pooled Spearman ρ | 0.853 | 0.654 |
| Pooled R² | 0.954 | 0.934 |
| CNOT fold MAE | 0.000 | 0.000 (unchanged) |
| Worst fold MAE | 0.146 (RandomClifford) | 0.303 (RepetitionCode) |
| Undefined-Pearson folds | 11/15 | 14/20 (QPE, QuantumVolume, WState add zero-variance folds) |
| Family-mean regression r (RF, Part-3b(a) protocol) | 0.059 (n = 15) | 0.780 (n = 20) |
| Family-mean regression MAE | 0.114 | 0.085 |
| Family-mean r with V4 gate applied to family means | — | 0.887 |

The Spearman drop is a ties artefact: the three incompressible new families
contribute ~65 exact-zero actuals with near-zero predictions, which a rank
statistic cannot order; Pearson and R² remain essentially at wave-4 levels.

**Family-mean regression: material improvement, honestly qualified.** Under
the identical leave-one-family-out RF protocol, r rises 0.059 → 0.780
(ρ = 0.510, MAE 0.114 → 0.085) at n = 20. The gain is real but driven by the
added low-end variance: QPE, QuantumVolume and WState are exactly
incompressible and are predicted near zero. The two hard points remain hard
— with pure RF, CNOT (actual 1.0) is predicted 0.30 and RepetitionCode
(actual 0.486) is predicted 0.04. Applying the deterministic V4 gate to
family-mean features fixes CNOT exactly (r → 0.887) but leaves
RepetitionCode untouched. **The n = 15 statistical-power limitation is
mitigated, not eliminated: per-family extrapolation to unseen high-reduction
mechanisms is still the binding failure.**

**New failure mode exposed (reported, not smoothed over).** The
RepetitionCode fold fails: MAE 0.303 under both V0 and V4 (the V4 gate never
fires), with a *negative* within-fold Pearson (−0.826). Attribution, all
computed: (i) RepetitionCode reduction (0.466–0.496) comes entirely from
adjacent H–H / CX inverse-pair cancellation — Phase-1-only reduction equals
the full naive-pipeline reduction on all 12 rows; (ii) its Phase-1 action
density (0.233–0.248) sits between the ordinary families (≤ 0.0345) and CNOT
(0.5), so the V4 saturation rule (2d ≥ 1) correctly does not fire, but no
training family occupies this density regime, and tree regressors cannot
interpolate leaf averages to y ≈ 0.49 (predicted ≈ 0.18); (iii) the static
structural upper bound tracks the realized reduction *exactly* on all 12
rows (per-row equality to 1e-12) — an oracle-bound predictor would score
MAE 0 on this fold, so the failure is in the learned mapping, not in the
mechanism features. This is the same extrapolation limitation diagnosed for
CNOT in wave 4, now shown to cover the entire mid-density regime, not only
saturation.

**Gate behaviour on new families.** The V4 rule fires on no new-family row
(zero false positives; density maxima: RepetitionCode 0.248,
TrotterHamiltonian 0.020, others 0.000). QPE, QuantumVolume and WState folds
are essentially perfect (MAE ≤ 7e-6); TrotterHamiltonian is well predicted
(MAE 0.0059, within-fold r = 0.835). Side observation: under pure RF (V0),
adding RepetitionCode to the training pool halves the CNOT fold error
(0.745 → 0.409), confirming that mechanism-similar families are what tree
models need to interpolate.

**Impact on manuscript §6.6 / §7.6 (decision deferred — this addendum does
not modify the manuscript).** If the 20-family evaluation is adopted as the
canonical number set:

| Location | Quantity | Published / wave-4 (15 fam) | Wave-6 candidate (20 fam) |
|---|---|---|---|
| §6.6 Table 18, best row (V4 hybrid) | Pooled MAE | 0.0172 [0.0129, 0.0218] | 0.0188 [0.0144, 0.0236] |
| §6.6 Table 18, best row | Pooled Pearson r | 0.977 [0.963, 0.987] | 0.967 [0.948, 0.979] |
| §6.6 Table 18, best row | Pooled Spearman ρ | 0.853 | 0.654 (ties from incompressible families) |
| §6.6 Table 18, best row | Pooled R² | 0.954 | 0.934 |
| §6.6 prose; §7.6 item 6 | CNOT fold MAE | 0.000 (closed by gate) | 0.000 (still closed) |
| §7.6 limitations | Family-mean regression | r = 0.059, n = 15, "insufficient power" | r = 0.780 (RF) / 0.887 (gated), n = 20; limitation softens to per-family extrapolation failure |
| §7.6 limitations (NEW) | RepetitionCode fold | — | MAE 0.303, within-fold r = −0.826: mid-density Phase-1 regime is a new, documented extrapolation failure of the learned component |
| §7.6 limitations | Undefined-Pearson folds | 11/15 | 14/20 |
| §6.6/§7.6 | Dataset scope | 15 families / 570 rows | 20 families / 692 rows (122 unique E27 circuits, hash-deduplicated) |

Canonical sources: `data/v6/ceiling_repair/part5_summary.json`,
`part5_lofo_results.csv`, `part5_e27_features.csv`; report
`docs/review/wave6/e27_part5.md`. Reproduce with
`/d/Downloads/miniforge3/python experiments/ceiling_model_repair.py --part5`.
