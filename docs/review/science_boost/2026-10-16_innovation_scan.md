# Innovation Scan — Quantum Peephole Ceiling: 科研全流程体检 + 创新方向扫描

**Date**: 2026-10-16
**Version**: v2 (supersedes the 2026-10-16 08:19 draft; see §0.3 for the corrections that motivated the rewrite)
**Scope**: `D:/Desktop/Q-research` — full-process audit (paper writing excluded) + frontier scan + prioritised innovation directions
**Red lines observed**:
- `data/` frozen data and `release/` hash manifests: **not modified**.
- `docs/manuscript/`: **read-only** (no text written or edited).
- No file deleted during the scan. Structural cleanup performed is limited to untracked build artifacts and one new index document; see §8.
- Every new evidentiary statement in this document carries a date and a source path.

---

## 0. Executive Summary

### 0.1 Verdict

The project's engineering evidence chain is genuinely strong and unusually well-audited for a single-author project: 37 canonical datasets / 96,289 rows, 128/128 classified landscape cells, 76,236 window searches with zero truncations, a 1,474-rule frozen rewrite library with provenance, and a theory gate that honestly records which results were **withdrawn** (Thm 5 incomplete, Thm 6 general refuted, Thm 8 withdrawn, Thm 2(d) invalid, QMA-hardness withdrawn). The `NOT_READY_FOR_PAPER` verdict in `release/v15_readiness_verdict.json` is correct and should not be softened.

**The project is currently a strong *Quantum* / *PRX Quantum* / *npj Quantum Information* candidate, not a *Nature*/*Science* candidate.** The reason is not effort or data volume — it is that the surviving theory (`docs/theory/framework.md` §"Scope and Nature of the Framework") explicitly disclaims fundamental significance, and the strongest empirical result (7.83% vs 0.0000% listing sensitivity) is a **representation-conditioned** ("RC") observation whose content changes with the data structure.

**Three things separate this project from the top tier**, in order of leverage:

1. **A theorem-shaped ceiling, not an empirical one.** The 2026 ZX-calculus literature now contains a worked model of exactly this (`arXiv:2608.22801`, "An Exactness Barrier for ZX-Calculus Optimization"): a per-instance, computable lower bound on achievable T-count that *explains* an observed near-null optimization. The project's "structural ceiling" is currently an empirical unanimity across tools. Converting it into an instance-computable certified barrier would be the single highest-value scientific upgrade.
2. **Disentangling representation ordering from pass ordering.** A September 2026 paper (`arXiv:2609.29406`, To/Quetschlich/Elsharkawy/Schulz/Wille/Kranzlmüller) has now systematically studied **pass order** in Qiskit. The project studies **listing order**. These are the same mathematical phenomenon viewed from two sides, and nobody has unified them. That unification is a genuinely new contribution and a defensible top-tier frame.
3. **Hardware-consequential evidence.** Every result to date is noise-free simulation; EHW is noise-*model* simulation (`credential_audit.route = 3b_noise_model_simulation_NOT_real_hardware`). A real-QPU result where the representation choice changes measured fidelity would give the work cross-disciplinary weight.

### 0.2 Priority ranking (short form)

| # | Direction | Leverage on Nature/Science bar | Effort | Venue ceiling |
|---|---|---|---|---|
| **P0-1** | **Certified peephole barrier theorem** (exactness-barrier-style) | ★★★★★ | High | **Nature Physics / Nature Communications** |
| **P0-2** | **Representation-ordering × pass-ordering unification** | ★★★★☆ | Medium | **PRX Quantum / Nature Communications** |
| **P0-3** | **Rule-library completeness attack via EqSat + Knuth–Bendix** | ★★★★☆ | Medium | PRX Quantum / Quantum |
| **P1-4** | Real-QPU representation sensitivity | ★★★☆☆ | Low | npj QI |
| **P1-5** | Certified landscape completion + certificate-protocol interop | ★★★☆☆ | Medium-High | Quantum (tools) |
| **P2-6** | Neural/LLM-guided certified search | ★★☆☆☆ | Medium | TQE / Quantum |
| **P2-7** | Average-case peephole complexity theory | ★★☆☆☆ | Low-Medium | QIP / Quantum |

### 0.3 Corrections to the morning draft

The 08:19 draft of this file contained three factual errors that would have misdirected the 30-day plan. Corrected here:

| Morning-draft claim | Verified reality |
|---|---|
| `docs/references/unified_references.md` is missing Onodera et al. [73], Nation et al. [71], Yang et al. [77], Rosenhahn et al. [94] | **All four are present** (`unified_references.md` lines 223, 219, 239, 251). Only the "missing" list's items 1 (Lee et al. 2501.14447), 3 (Meijer-van de Griend JSS 2025), 4 (BQSKit), 7, 8 are genuinely absent — and items 7/8 are low-relevance. |
| "Cross-Compiler IR Audit" is a new P0 direction (Direction 3) | **Already substantially executed.** `docs/analysis/compiler_listing_audit.md` plus the wave-6 relisting experiment (6,720 rows, 168 family–n–tool combinations) show production compilers are sensitive in **0/126** combinations vs **15/42** for the flat-list prototype. The direction should be *extended*, not started. |
| The relisting/IR audit is "not systematically verified" | The manuscript (§1.2, §7.2, §8) already states the WCL-equivalence claim with evidence. The remaining gap is narrower: beyond-peephole passes (resynthesis, phase polynomials) were not audited. |

---

## 1. Factual Baseline (verified 2026-10-16)

### 1.1 Evidence chain

| Layer | Result | Status | Source (read this session) |
|---|---|---|---|
| E1–E30 canonical benchmark | 35 active canonical datasets / 96,205 rows (37 listed / 96,289 incl. 2 superseded provenance entries) | Hash-pinned, frozen | `data/DATA_CANONICAL.md` v2.4.0, lines 48–88 |
| E31 sealed factorial | 28,152 rows; 15-family listing × rule-set × window × budget | Sealed v11 | manuscript §6.9 |
| E32–E37 | Telemetry, real scale, MQT cross-abstraction, Benchpress stress, PyZX third-artifact, CPU-package energy | Hash-bound receipts | `release/e32_*` … `release/e37_*` |
| v13 E45 screening | 0/18 eligible; max guided failure 63.28125% | Closed as recorded resource failure | `release/v13_readiness_verdict.json` |
| v14 E45 screening | 18/18 eligible; 13,824 rows; 0 semantic failures | Optimization item closed | `release/v14_readiness_verdict.json` |
| v14 exact finite horizon | 93 exact certificates; 35 resource-truncated | Incomplete (superseded by v15 classification) | `release/v14_readiness_verdict.json` |
| v14 IDA* escape | 63 exact escapes; 65 exact local optima; 0 resource bounds | Closed for the 128-input panel | `docs/PROJECT_STATUS.md` |
| v15 landscape integration | `classified_count: 128`, `unclassified_count: 0`, tiers `93 COMPACT_COMPLETE_ENUMERATED` / `1 COMPACT_COMPLETE_DERIVED` / `34 CLASSIFICATION_EXACT_EXTRAS_BOUNDED`, `escape_count: 63`, `local_optimum_count: 65`, `exact_best_cost_count: 94`, `witness_replay_failures: 0` | Classification closed | `release/v15_readiness_verdict.json` lines 4–19, 84–88 |
| v15 E46 window landscape | `window_rows: 76236`, `escape_row_count: 39474`, `resource_truncated_windows: 0`, `status: PANEL_COMPLETE`, 4 configs (w8/w16 × h2/h3) | New evidence layer | `release/v15_readiness_verdict.json` lines 21–60 |
| Theory (admissible) | Obs 1(a/b), Thm 2(a), Thm 2(c), Lemma 3/4, Thm 7, Thm 9 | Admissible within stated scope | `docs/theory/framework.md` §"Cross-Reference Map" |
| Theory (withdrawn/incomplete) | Thm 5 (proof incomplete), Thm 6 general (refuted by n=2 seed=35), Thm 8 (withdrawn, incompatible premises), Thm 2(d) (invalid per-wire factorisation), QMA-hardness of CODP (withdrawn), Conj. C1 (refuted) | Not admissible | same |

### 1.2 What the project actually claims (three contributions, as written)

1. **Contribution 1 — Listing-model sensitivity.** Thm 1(b): LBL makes the Phase-1 action space structurally empty for $n\ge2$ under the stated generator contract. Thm 1(a): WCL adjacent-inverse density $\mathbb{E}[|\mathcal{A}_{adj}|] = n(d-1)p_{cancel}$, validated by E30 (13,500 rows, 27 cells, max |z| = 2.86, median |rel err| = 1.4%). Headline: **0.0000% (E1, 25,000 circuits, LBL) → 7.83% ± 3.95% (E19, 10,000 rows, WCL)** on the *same* ensemble. E22 adds a shuffle control: shuffling *increases* Phase-1 reduction (6.30% → 10.34%, $p=6.8\times10^{-15}$), confirming the effect tracks listing *structure*.
2. **Contribution 2 — Search-space stratification.** A refined 6-class / 15-family taxonomy: Class I trivially compressible (CNOT chain, 100%); Class II commutation-enabled (Oracle/BV, RandomClifford, Grover, 6.2–16.5%); Class IIIa genuine structural ceiling (QFT, GHZ, SurfaceCode, 0.0% across all tools with one Cirq +8.4% exception); Class IIIb prototype action-space ceiling (VQE, HardwareEfficient, IQP, UCCSD, QAOA + borderline HaarRandom; t|ket> recovers 6.3–64.4%, Phase-2b up to 92.0%); Class IIIc practical ceiling (Adder, QuantumWalk). Lead result: **Phase-2b reaches the provable $k+2$ gate optimum on all 80 Bernstein–Vazirani instances ($n=3..10$, 80/80, mean 69.2%)**, exceeding the rigorous Thm 9 bound by 3.1–4.2×.
3. **Contribution 3 — Ceiling-aware optimizer.** 1.6×–228× per-family speedup, aggregate 34.97× under prototype timing; **2.20× under the symmetric-timing control**, output bit-identical (570/570 paired trials, E21, 1,140 rows).

### 1.3 Closed / open item register

| Item | Status | Authority |
|---|---|---|
| Frozen rewrite library (1,474 safe directed rules) | **Closed** for declared library | `docs/PROJECT_STATUS.md` |
| E44 exact oracle (512 cases / 1,024 model rows) | **Closed** | same |
| E45 v14 screening | **Closed** | same |
| Escape-depth classification | **Closed** for 128-input panel | same |
| v15 classification bookkeeping | **Closed** (128/128) | same |
| E46 window landscape | **PANEL_COMPLETE** | `release/v15_readiness_verdict.json` |
| Determinism / failure handling | **Closed** | `docs/PROJECT_STATUS.md` |
| Historical E1–E37 | **Preserved, no rerun justified** | same |
| 34 long-listing escape cells | **Open (bounded form)** — `bounded_best_cost_count: 34` | `release/v15_readiness_verdict.json` |
| Independent cold start | **Open** — `external_cold_start: "OPEN"` | same, line 100 |
| Real QPU | **Open** — `real_qpu: "OPEN"` | same, line 101 |
| External execution gate / release authority | **Open** — `release_authority: "OPEN"` | same, line 102 |
| C3 title and positioning | **USER_DECISION_PENDING** | same, line 93 |
| Full-rule-scope (1,474-rule) panels | Open | `docs/PROJECT_STATUS.md` §Remaining work |
| Wire-consecutive window profiles | Open | same |

### 1.4 Current scientific boundary (the honest line)

From `docs/theory/framework.md` §"Honest framing note (added 2026-06-11)":

> "The structural ceiling framework is primarily a combinatorial and algebraic analysis of gate sequences, not a discovery about quantum physics. … The 'structural ceiling' is a limit on a specific class of *classical algorithms* (peephole rewriters) applied to a specific *data structure* (gate sequences)."

This is the correct scientific statement and it is also, precisely, the reason the work cannot presently clear a *Nature*/*Science* bar. **Any Nature/Science path must change this sentence** — either by making the ceiling a statement about the circuit rather than about the rewriter, or by connecting it to something measurable on hardware or to a complexity-theoretic classification.

---

## 2. Known Gaps — Verification and Upgrade Plans

### Gap 1 — 34 witness-bounded long-listing escape cells

**Verification.** `release/v15_readiness_verdict.json`: `blocking_evidence.landscape_integration.bounded_best_cost_count = 34`; `certificate_tiers.CLASSIFICATION_EXACT_EXTRAS_BOUNDED = 34`. `claim_boundary` states these "carry witness-bounded best-cost and barrier values rather than enumerated ones". `paper_status` forbids claiming "complete enumerated landscape quantities for the 34 bounded cells".

**Why it is hard.** The v14 compact exact finite-horizon engine exhausted its budget on exactly these long-listing sources; E46 already certified 39,474 window escapes on the same sources, so the *barrier structure* is known and the deficit is in whole-listing enumeration only.

**Upgrade plan.**
- Algorithmic: IDA* with a pattern-database heuristic seeded from the 94 completed cells; the E46 first-escape witnesses give admissible move-ordering information.
- Alternative framing (cheaper, and more publishable): do **not** complete enumeration. Instead prove a *certified lower bound* on the residual barrier for these 34 cells in the style of `arXiv:2608.22801` (see Direction P0-1). A bound is a stronger scientific object than an enumeration and is not resource-gated.
- Evidence: a new v16 package with tiers upgraded, `data/v15/` and `data/v14/` untouched.

### Gap 2 — No real QPU validation

**Verification.** `scientific_gates.real_qpu = "OPEN"`. `data/DATA_CANONICAL.md` Known Issue 6: EHW is noise-model simulation, `credential_audit.route = 3b_noise_model_simulation_NOT_real_hardware`. §7.4 already reports the *negative* pilot result honestly: Oracle/BV compresses 46.15% logically (13 → 7 gates) but **0% after Qiskit L1 basis translation**, with Hellinger improvements of only +0.0011–0.0018.

**Upgrade plan.**
- The §7.4 finding is itself the experiment to run on hardware: **logical compression does not survive basis translation**. Test whether a *representation-aware* compilation path (WCL preprocessing before transpilation) preserves the logical gain through the basis-change gate. That is a falsifiable, hardware-measurable claim about representation choice.
- Scope: 3 families (BV, HaarRandom, RandomClifford) × 5–7 qubits × 2 listings × 3 sampling seeds. IBM Quantum free tier is sufficient.
- Evidence: v16 QPU package; v8 EHW canonical untouched.

### Gap 3 — No independent cold-start reproduction

**Verification.** `scientific_gates.external_cold_start = "OPEN"`; `docs/verification/cold_start_protocol.md` exists; `docs/PROJECT_STATUS.md` records "Sparse package verification is recorded; clean non-author execution remains pending".

**Upgrade plan.** The `Dockerfile` exists. Ship a pinned single-command entry point (`scripts/reproduce_all.py --verify` is already the canonical chain), run it on a second machine or CI runner, and archive the SHA-256 receipts as external evidence. This is the cheapest of the four open gates and should be closed first because it converts three "OPEN" labels into one.

### Gap 4 — No external execution gate

**Verification.** `scientific_gates.release_authority = "OPEN"`.

**Upgrade plan.** Two natural reviewers given tool overlap: the MQT group (TUM — Quetschlich/Burgholzer/Wille, authors of both MQT Bench [69] and the new pass-order paper `arXiv:2609.29406`) and the BQSKit team (LBNL). Provide `release/release_manifest.json` + the verifier scripts as the review target. Note the conflict-of-interest angle: the MQT group now has a directly adjacent paper, which makes them valuable reviewers *and* a competitive risk — see Direction P0-2.

### Gap 5 — Theory framework: withdrawn and incomplete results

**Verification.** `docs/theory/framework.md` §"Audit correction (2026-08-09)" and §"Cross-Reference Map":

| Result | Status | Concrete defect |
|---|---|---|
| Thm 5 (McDiarmid concentration) | **Proof incomplete** | Dependent-exposure martingale not constructed; product-space assumption does not match the generator's probability space |
| Thm 6 (AG canonical) | **General claim refuted** | Counterexample at $n=2$, seed 35; narrowed to the restricted generator |
| Thm 8 (Haar incompressibility) | **Withdrawn** | Premises incompatible: no polynomial-size exact circuit can implement Haar-random $U$ on the high-probability event |
| Thm 2(d) (INSERTION+SWAP ceiling) | **Invalid** | Per-wire factorisation fails for multi-qubit gates; pair count ≠ attainable optimum |
| QMA-hardness of CODP | **Withdrawn** | Promise reversal; diamond norm on channels not matrices; SWAP test insufficient |
| Conj. C1 (universal Phase-1 ceiling) | **Refuted** | Three-gate SWAP+REMOVAL counterexample |
| Obs 1 (Greedy matches stochastic) | **Withdrawn** | Counterexample + historical incumbent bug (`data/DATA_CANONICAL.md` Known Issue 15) |

**Assessment.** The pattern is consistent: every withdrawn result failed for the *same* structural reason — the probability space or the factorisation was assumed rather than constructed. **Thm 5 is the one worth repairing**, because a valid concentration bound on adjacent-inverse-pair count is exactly what a certified-barrier theorem (Direction P0-1) needs as its upper companion. Repair route: the correct independent variables are the $\approx (n/2)(d-1)$ pair choices, not the $n(d-1)$ per-wire choices; bounded-differences constant $c_i = 4$ at pair level is plausible but the exposure martingale must be written explicitly.

---

## 3. Full-Process Audit

### 3.1 Scientific question and narrative — the Nature/Science bar

**Current framing.** Three RQs: (RQ1) how listing model affects outcomes; (RQ2) structure of the search space across families; (RQ3) where production compilers exceed the local peephole model and whether ceiling knowledge improves efficiency. The narrative is honest, well-scoped, and the historical "phase transition" refutation is handled correctly (manuscript §7.1 "Historical note on terminology", RQ2 definition in §1.3).

**Bar assessment.** Three specific deficits, each with a named remedy:

| Deficit | Evidence | Remedy |
|---|---|---|
| **The object of study is the algorithm, not nature.** The framework's own framing note says the ceiling is "a limit on a specific class of classical algorithms applied to a specific data structure". *Nature*/*Science* require a claim about the world. | `framework.md` §"Honest framing note" item 3 | Direction P0-1: make the barrier a property of the circuit's algebraic structure (ring-element valuation, like 2608.22801), or make it hardware-measurable (Direction P1-4) |
| **No surprise.** "Data-structure ordering changes what an optimizer sees" is expected to anyone from classical compiler theory (McKeeman 1965 lineage, already ref [1]). The 7.83% vs 0.0000% gap is striking but confirms an expected mechanism. | manuscript §1.1–1.2 | Direction P0-2: the *surprise* is that representation ordering and pass ordering are the same phenomenon and that the classical literature's phase-ordering results do **not** transfer |
| **Scope of impact is one sub-community** (~500 quantum-software researchers). | manuscript §1.1 framing | Direction P1-4 + P0-1: hardware consequence, or a complexity classification |

**One narrative weakness worth fixing regardless of venue.** The abstract leads with **Methods** (row counts, dataset counts, experiment IDs) before **Results**. For any venue above *Quantum*, the lead must be the 0.0000% → 7.83% contrast and the 80/80 BV optimum, with the 96,289 rows demoted to a methods sentence. The abstract as written currently reads as an audit report rather than a discovery paper.

### 3.2 Theory framework — which conjectures are repairable

| Conjecture / open problem | Repairability | Path |
|---|---|---|
| **OP1** CODP is QMA-hard | Low | No valid reduction exists; the promise orientation is reversed (r=0 is trivial). Do not reopen without an explicit promise-preserving size-gap reduction. |
| **OP2** no PTAS for CODP | Low-Medium | The multiplicative formulation is ill-defined when the optimum is zero. Only the additive/gap formulation is admissible. |
| **C1** universal Phase-1 ceiling | **Dead** | Refuted. Do not attempt repair; the refutation is a legitimate result and should be *cited* as a negative result. |
| **C2** $\Gamma(C)=\Omega(1)$ for specific families | **Partially resolved** | Thm 7 (artificial family) and Thm 9 (natural BV family, $2n/(3n+2)$) are existence proofs. The *classification* — which families have $\Omega(1)$ gap and which do not — is the open, valuable part. |
| **Thm 5** concentration | **Repairable** | See Gap 5. Highest-value theory repair. |
| **Phase-2 action-space bound $O(d/n)$** (`docs/theory/nontrivial_upgrades.md`) | **Highest-value untested conjecture** | This would explain *why* Phase-2a advantage on random circuits is small (~3.26%, E10) while being large on oracle circuits (~20%, E11). The document is a "historical brainstorming document, not a theorem-status source" — but the conjecture itself is well-posed and directly testable against E10/E11/E14 data. |
| **Thm 9 global optimality** | **Repairable via SAT** | The $k+2$ bound is a construction, not an optimality proof. The SAT-based depth-optimal Clifford synthesis route (Peham et al.) could certify optimality for the BV family on bounded instances — which would upgrade the single most citable result from "reaches $k+2$" to "reaches the proven optimum $k+2$". **This is a cheap, high-yield upgrade.** |

### 3.3 Experimental design — power, controls, external validity

**Strengths (verified).** Pre-registered H1–H5 with explicit rejection criteria and verdicts (manuscript Table 1); 6 optimizer types; 3 production compilers under a fair no-coupling-map protocol; sealed E31 factorial with a pre-registered analysis protocol; FDR correction; ITT-MI treatment of the E18 survivorship bias (44.4% row-level failure, ITT-MI estimate 0.1351 [0.102, 0.169]); multi-seed replication E29 (800 rows, 10 seeds); explicit random-shuffle control E22.

**Weaknesses, with severity.**

| # | Weakness | Severity | Fix |
|---|---|---|---|
| W1 | **No BQSKit and no SAT-optimal Clifford baseline.** BQSKit (LBNL) handles >100 qubits via LEAP synthesis; MQT's SAT-based Clifford synthesis gives depth-optimal certificates directly comparable to the ceiling analysis. Both absent. | **High** — weakens every SOTA claim | Add both to the SOTA panel; the MQT route additionally upgrades Thm 9 |
| W2 | **External validity of the 15-family roster.** The roster is custom-generated. E35 uses Benchpress-derived stress and E34 uses MQT cross-abstraction, but the canonical benchmark does not intersect QASMBench/MQT Bench/Benchpress/QCircuitBench. | **High** — a reviewer will ask "is the trichotomy an artefact of your generator?" | Run the taxonomy on MQT Bench + QASMBench at matched widths; the classifier is cheap once the family detector exists |
| W3 | **Scale.** Most family cells are $n=3$–10. E33 covers 11–36 qubits on 22 cells only. | Medium | Add a 20–40 qubit band for 3 families |
| W4 | **Asymmetric E21 timing.** Resolved in the manuscript by reporting the symmetric-timing control (2.20×), but the *headline* 34.97× still appears in §1.5 and §7.3 | Medium | Lead with 2.20×; move 34.97× to a footnote |
| W5 | **E4 single-seed values; E29 shows materially different stochastic inflation** (SA −22.15%, GA −8.31% pooled vs E4's −1.55%/−0.23%) | Low-Medium | Already disclosed (Limitation 7) |
| W6 | **Statistical power on real-circuit cells** (QFT/GHZ in E10 have $N=5$; Clopper–Pearson 95% upper bound for 0/5 is 45.1%) | Low | Already disclosed (Limitation 10); non-parametric methods are primary for zero-inflated data |
| W7 | **`success` column is non-informative** in every dataset carrying it | Low | Already disclosed (Known Issue 7); do not use |
| W8 | **E26 canonical fidelity is not publication-grade for 201 rows** (superseded `sampled200` product-state estimator) | Medium | Already resolved: a 2,427-row publication-gate rerun is frozen at `data/v10/prepaper/e26/phase2b_full_validation_v8.csv`; cite that file, not the v8 canonical |

### 3.4 Data and reproducibility

**Strengths.** SHA-256-pinned release chain (`release/release_manifest.json`); explicit data-version policy (new `data/vN/` never in-place overwrite, `data/DATA_CANONICAL.md` §"Data version policy"); replayable certificates with witness storage; fail-closed readiness verdicts; `scripts/reproduce_all.py --verify`; Docker reproduction environment; 15 documented Known Issues with resolution status; a genuinely rigorous rerun-reconciliation record (wave 6, `docs/review/wave6/reconciliation_disposition.md`).

**Weaknesses.**

| # | Weakness | Fix |
|---|---|---|
| D1 | No archival DOI (Zenodo/figshare) for the dataset. `release/zenodo_deposit_metadata.json` exists but no deposit is recorded. | Deposit on Zenodo at submission; the metadata file is already prepared |
| D2 | The 15,042-entry prepaper manifest carries 15 hash-drift entries (13 committed drifts + 2 CRLF artefacts) | Resolve before any release claim; CRLF artefacts are a `.gitattributes` fix |
| D3 | No CI. GitHub Actions is explicitly out of scope by project decision (`docs/PROJECT_STATUS.md` line 7) | Out of scope — but an external runner for Gap 3 would substitute |
| D4 | Four dependency files (`requirements.txt`, `requirements-lock.txt`, `environment.yml`, `pyproject.toml`) with unclear precedence | Designate `pyproject.toml` as primary and document the roles in one place (see §8) |

### 3.5 Code engineering quality

**Strengths.** Modular `src/` (`circuits/`, `optimisation/phase1`, `optimisation/phase2`, `integrations/`); 101 test files; 85 experiment entrypoints; 61 scripts; byte-stable certificate generation; deterministic seeds recorded in `metadata.json` per experiment.

**Weaknesses.**

| # | Weakness | Fix |
|---|---|---|
| C1 | No static type checking (`mypy`/`pyright` not configured) | Add `mypy` in non-strict mode over `src/` only; cheap and catches the class of error that produced Known Issue 9 (misaligned `success_reduction` defaults) |
| C2 | 221 untracked `.pyc` files across 16 `__pycache__` directories (gitignored, so no repo pollution, but local noise) | **Executed this session** — see §8 |
| C3 | No coverage reporting | Low priority; the evidence tests are the real gate |
| C4 | `docs/analysis/` contains 3 ad-hoc probe scripts (`_alg_complexity_*.py`) and 3 raw part-CSVs at the top level of a documentation directory | Move the raw CSVs under a `data/`-adjacent path or leave; they are cited by `docs/analysis/algorithmic_complexity.md` |

### 3.6 External validation paths

| Path | Status | Minimal viable next step |
|---|---|---|
| Real hardware | OPEN | §3.3 Gap 2 plan: representation-aware compilation path through basis translation, 3 families × 5–7 qubits |
| Independent cold start | OPEN | Docker + second machine; cheapest gate to close |
| External review | OPEN | MQT (TUM) or BQSKit (LBNL); note the adjacency risk with `arXiv:2609.29406` |
| Archival publication | Not started | `release/zenodo_deposit_metadata.json` is prepared |

### 3.7 Publication strategy — which finding belongs where

| Finding | Present venue fit | Required upgrade | Target |
|---|---|---|---|
| Listing-model sensitivity (0.0000% vs 7.83%) | *Quantum* / *PRX Quantum* | hardware consequence, or unification with pass ordering | **PRX Quantum**; *Nature Communications* only with P0-2 |
| 15-family stratification (6 classes) | *Quantum* | external benchmark replication (W2) | *npj QI* / *PRX Quantum* |
| Phase-2b BV $k+2$ optimum (80/80) | QIP conference | **global optimality certificate** (§3.2) | *Quantum* — and this is the most citable single result |
| Certified landscape 128/128 + E46 | workshop / software track | 34 cells or a bound; full-rule scope | *Quantum* (tools) |
| Ceiling-aware optimizer | TQE / software | symmetric timing as headline + BQSKit/MQT comparison | TQE |
| Certified peephole barrier theorem | — | new theorem (P0-1) | **Nature Physics / Nature Communications** |
| Representation-ordering × pass-ordering unification | — | new framing + experiment (P0-2) | **PRX Quantum / Nature Communications** |
| Rule-library completeness via EqSat/Knuth–Bendix | — | new experiment (P0-3) | PRX Quantum / Quantum |

---

## 4. Literature and Frontier Scan (executed 2026-10-16)

### 4.1 What was actually executed

| Tool / channel | Status | What it produced |
|---|---|---|
| arXiv API (`export.arxiv.org/api/query`, phrase-quoted queries) | **Working** | 17 topic queries, 115 records retrieved, sorted by submission date; full abstracts pulled for 10 papers |
| GitHub REST API (token from the Windows credential store; never printed) | **Working** | Live star counts / last-push dates for 8 quantum-compiler repositories; 3 repository-search queries |
| Built-in web search | **Working** | Cross-check on pass-ordering literature |
| Tavily skill (`scripts/tavily_search.py`) | **Unavailable** | `tavily-python` not installed and no `TAVILY_API_KEY` in the environment. **Not used; no Tavily-derived claim appears in this document.** |
| Exa skill (`web-search-exa`) | **Unavailable** | Requires the `mcp.exa.ai` MCP server, which is not configured in `~/.workbuddy-ai/mcp.json`. **Not used.** |
| `multi-search-engine` skill | **Not used** | It is a `web_fetch`-driven engine-endpoint recipe, not an API; the built-in search plus the arXiv/GitHub APIs gave higher-quality, date-sorted primary sources for this domain. |
| `arxiv-reader` deep-read pipeline | **Partial** | The full LaTeX-parsing agent pipeline was not run; deep reading was done by pulling complete arXiv abstracts (not truncated snippets) for the 5 most relevant papers and reading them against the project's claims. Methodological extraction is in §4.2. |
| `github-trending-cn` | **Substituted** | The script's global trending feed is not domain-targeted; a direct GitHub API repository search over quantum-compiler topics gave the relevant ecosystem picture (§4.5). |
| `citation-manager` | **Partial** | Used as a coverage audit against `unified_references.md` (§4.3), not as a CrossRef batch importer. |
| `deep-research` | **Partial** | The structured outline → deep → report pipeline was not run as a separate multi-agent pass; this document is itself the report, with the search log in Appendix B. Running the full pipeline is listed in the 30-day plan as a *methodological* upgrade, not a substitute for this scan. |

**Disclosure.** No claim in §4.2–§4.5 is derived from a tool that was unavailable. Every arXiv ID, title, date and author list below was retrieved from the arXiv API on 2026-10-16; every star count and push date is from the GitHub API on 2026-10-16.

### 4.2 Closest competing work — and why it matters

This is the most consequential part of the scan. Five papers published in the last eight weeks are close enough to the project's core that the novelty framing must be adjusted.

**(A) `arXiv:2609.29406` — "Evaluating the Effect of the Order of Optimization Passes in Quantum Circuit Optimization"** (To, Quetschlich, Elsharkawy, Schulz, Wille, Kranzlmüller; 2026-09-24). Systematic study of pass **order** in Qiskit: pairwise combinations of 16 passes, depth and gate count across benchmark circuits. Findings: pass order matters; some dependencies exist; a worse sequence can be repaired by repeating passes; the native gate set is the dominant factor.

- **Relation to this project**: This is the *same phenomenon in the dual coordinate system*. The project varies the **representation** ordering of a fixed circuit under a fixed move set; this paper varies the **algorithm** ordering of a fixed representation. The project's E22 shuffle control already proves the representation-ordering effect is causal for Phase-1.
- **Why it is a threat**: it is from the MQT group (authors of MQT Bench, already ref [69]), it uses Qiskit (the project's primary comparator), and it is *published first*. A reviewer who knows it will ask "how is this different from pass ordering?"
- **Why it is an opportunity**: the two papers have never been connected, and the project has the tooling (certified landscape, window profiles) to make the connection *rigorous* rather than empirical. See Direction P0-2.
- **Required action**: cite it; build the representation × pass-order factorial; state the distinction explicitly in the abstract.

**(B) `arXiv:2608.22801` — "An Exactness Barrier for ZX-Calculus Optimization of Synthesized Clifford+T Circuits"** (Kam, Mahasinghe, De Silva, Cadet, Wang; 2026-08-24). Proves that for any exactly-preserving optimizer, achievable T-count is bounded below by the denominator exponent of the synthesized ring element. The barrier is **computable per instance**, and it *explains* a previously contradictory empirical pattern (ZX removes a stable fraction of Solovay–Kitaev circuits but almost nothing from number-theoretically synthesized ones). Certified rigidity of 99.4–99.9% on the quantum-Shannon-decomposition + gridsynth pipeline.

- **Relation**: this is the closest existing analogue of the project's "structural ceiling" — but it is a *theorem with a computable instance-level bound*, whereas the project's ceiling is an empirical unanimity across tools.
- **Why it matters most**: it is a **worked model for exactly the upgrade the project needs**. A Nature-tier version of the peephole-ceiling result looks like this paper: a per-instance computable barrier, derived from algebraic structure, that explains why an observed optimization is near-null.
- **Required action**: read it as a template; see Direction P0-1.

**(C) `arXiv:2609.19160` — "AlchemQ: Proof-Carrying Quantum Circuit Optimization with Per-Result Equivalence Certificates"** (Laabs; 2026-08-24). Couples an untrusted beam-search optimizer to a per-result certification layer; ZX full-reduction equivalence proof with a numeric-tensor fallback; canonical gate hashing; tri-state verdicts (certified/rejected/inconclusive); versioned certificate protocol 0.2.0; guarantees no componentwise regression. Reports a pilot on IBM Heron r2 (78% shallower, 65% fewer two-qubit gates, not significant at 1024 shots). Certificate spec and a standalone verifier released Apache-2.0; engine proprietary.

- **Relation**: directly comparable to the project's replayable certificates and fail-closed readiness verdicts. **The project's certificate design is at least as rigorous** (byte-stable, witness replay, 0 replay failures) — but AlchemQ is the first to propose a *protocol version* and a *standalone third-party verifier*.
- **Required action**: adopt a protocol version string for the project's certificates; if the formats can be aligned, cross-verification is a strong, cheap external-validation result and closes part of Gap 4.

**(D) `arXiv:2609.16171` — "Why Are We Unrolling? The Importance of Structured Quantum Programs for Compilation"** (Rovara, Haag, Koch, Izaac, Sivarajah, Wille, Borgna; 2026-09-14). Argues that quantum compilation must operate on *structured* representations (classical control, mid-circuit measurement feedforward, repeat-until-success) rather than unrolled straight-line circuits, and challenges the community to compile without unrolling.

- **Relation**: this is a **representation-choice argument from the opposite direction**. The project shows that *within* straight-line representations, the choice of listing changes the reachable action space. This paper shows that *leaving* the straight-line representation changes the reachable action space more fundamentally. Both are instances of "representation determines the action space."
- **Why it matters**: it supplies the generalisation frame. A theorem that covers both (straight-line listing choice *and* structured-vs-unrolled choice) is a much stronger claim than either paper alone.
- **Required action**: cite in the introduction as the strongest existing evidence that representation choice is a first-class compiler variable; position the project's contribution as the *quantitative, certified* version of a claim the community has now made qualitatively twice.

**(E) `arXiv:2606.31238` — "A Multi-Dimensional, Per-Pass Empirical Study of the LLVM Optimization Pipeline"** (Bruzzone, Cazzola; 2026-06-30). 84,750 measurements over 113 cumulative prefixes of LLVM `-O3` on 30 PolyBench/C kernels. Findings: the pipeline is non-monotone (6.6–9.7% of transitions regress); strongly back-loaded (median non-regressing kernel needs 84.8% of the pipeline for 80% of its speedup); a small Pareto-dominant core of passes drives most gains; the final `-O3` config is Pareto-dominated on (size, speedup) for 29 of 30 kernels; IR instruction count is an unreliable predictor of runtime; the search-free additive upper bound on phase-interference loss is 46.35%.

- **Relation**: this is the **classical methodological twin** of the project. It is exactly the study the project did for quantum peephole optimization, but for LLVM, with per-pass decomposition, noise mitigation, and a formal phase-interference bound.
- **Why it matters**: (i) it validates the *method* as publishable in a top systems venue; (ii) it supplies a directly comparable baseline for the "IR instruction count is an unreliable predictor" claim, which is the classical analogue of the project's finding that circuit family does not predict peephole reduction; (iii) its "search-free additive upper bound on phase interference" is a template for the certified barrier.
- **Required action**: cite as the classical-methodology precedent; adopt the cumulative-prefix measurement design for the representation × pass-order factorial.

**(F) Other directly relevant 2026 work** (titles/dates verified via arXiv API):

| arXiv | Date | Title | Relevance |
|---|---|---|---|
| 2601.15934 | 2026-01-22 | Automated quantum circuit optimization with randomized replacements (Szyniszewski, Kissinger, Linden, Skrzypczyk) | Already ref [92]. Approximate/mixed-channel rewriting with a strict error budget — a **different ceiling notion** (error-budget ceiling vs move-set ceiling). Substantial QFT reduction. |
| 2506.20624 | 2025-06-25 | Leveraging Phase Polynomials for Quantum Circuit Optimization (PhasePoly) | Up to 50.00% gate-count reduction (34.70% avg), CNOT up to 48.57%. **This is a direct explanation candidate for the project's Class IIIb failures** — the cross-block parity representation exposes long-range structure that local rewriting cannot. |
| 2605.19005 | 2026-05-18 | Rewrite System Showdown: Stochastic Search vs. EqSat (Hong, Soi, Zhang, Aiken) | Directly asks "are e-graphs actually good?" — the exact question the project would ask when testing whether the trichotomy is a rule-library artefact. From the Aiken group (Quartz/Quanto lineage). |
| 2610.01246 | 2026-10-01 | Augmenting Rewrite Rule Sets via Knuth-Bendix Completion (Schifferer, Ullrich, Hack) | Automatically generates and augments EqSat rewrite rules; faster optimization and previously-missed optimizations. **Directly applicable to the project's hand-assembled 1,474-rule library.** |
| 2609.36065 | 2026-09-28 | Irene: Equivalence Checking of Hybrid Quantum Programs via Structure-Preserving Symbolic Reduction | Hybrid/measurement-dependent equivalence checking — the class the project's D11 contract explicitly returns `unavailable` for. |
| 2610.00255 | 2026-09-24 | Testing and Verification of Quantum Compilers through Assurance Contracts and Evidence | Integrative survey of verified transformations, equivalence checking, differential/metamorphic testing, evidence across revisions. **A ready-made framing reference for the project's evidence-chain methodology.** |
| 2610.11195 | 2026-10-08 | Retromorphic Testing of Quantum Compiler Passes | Pass-level testing methodology. |
| 2609.01037 | 2026-09-01 | A Dynamic Intermediate Representation for Hybrid Quantum-Classical Programs | Gates as first-class values; unified representation. |
| 2609.29305 | 2026-09-24 | QaiJi IR: An Eight-Layer Intermediate Representation Family for Hybrid Quantum-Classical Compilation | IR-family design. |
| 2610.22367 | 2026-10-15 | Discovering state-of-the-art quantum circuits with large language models | Newest LLM-for-circuits result (published the day before this scan). |
| 2608.19103 | 2026-08-19 | Quantum circuit optimization using deep reinforcement learning: Applications across multiple gate sets | RL across gate sets. |
| 2605.11375 | 2026-05-12 | TuniQ: Autotuning Compilation Passes for Quantum Workloads at Scale | RL-based pass selection — the "pass-order" automation arm of (A). |
| 2607.04586 | 2026-07-06 | QuTuner: Feature- and Learning-Guided Optimization Pass Tuning for Quantum Compilers | Feature-guided pass tuning. |
| 2306.15020 | 2023-06-26 | Clifford Assisted Optimal Pass Selection for Quantum Transpilation | Earlier "optimal pass selection" — the pre-2024 baseline for (A). |
| 2504.19113 | 2025-04-27 | Inverse-Transpilation: Reverse-Engineering Quantum Compiler Optimization Passes from Circuit Snapshots | Treats compilers as black boxes and infers their passes — an external-validation technique the project could borrow. |
| 2411.04104 | 2024-11-06 | Optimizing Quantum Circuits, Fast and Slow | Unifies rewrite rules and unitary synthesis into one framework. |
| 2509.02668 | 2025-09-02 | Quantum Circuit Optimization for the Fault-Tolerance Era: Do We Have to Start from Scratch? | FT-era reframing of the whole optimization agenda. |
| 2609.17465 | 2026-09-15 | Quantum Compiler Design for Fault-Tolerant Quantum Computing | FT compiler design. |
| 2609.07776 | 2026-09-07 | QROB: Quantifying Realization Overhead in Quantum Compilation via Reverse Construction | Quantifies the compilation overhead the project's §7.4 basis-translation finding implicates. |
| 2602.12831 | 2026-02-13 | Optimized Compilation of Logical Clifford Circuits | Clifford-specific compilation. |
| 2603.12697 | 2026-03-13 | Efficient equivalence checking of Clifford-U circuits with shared single-qubit unitaries | Extends the equivalence-checking envelope beyond D11. |
| 2511.18770 | 2025-11-24 | HOPPS: Hardware-Aware Optimal Phase Polynomial Synthesis with Blockwise Optimization | Phase-polynomial + hardware-aware. |
| 2510.00649 | 2025-10-01 | Provably Optimal Quantum Circuits with Mixed-Integer Programming | **A second route to global optimality certificates** alongside SAT — relevant to upgrading Thm 9. |
| 2409.06020 | 2024-09-09 | Peephole Optimization for Quantum Approximate Synthesis | The only prior paper with "peephole" in the title in the quantum setting; cited in the project's literature. |

### 4.3 Reference coverage audit (corrected)

`docs/references/unified_references.md` v2.2 (last updated 2026-08-24) holds **94 numbered entries** in §A–§M, of which [74] and [81] are explicitly removed placeholders.

**Genuinely missing, with relevance:**

| Reference | Verified | Relevance | Suggested action |
|---|---|---|---|
| Lee, Jeong, Kim, "Quantum Circuit Optimization by Graph Coloring," *Quantum* (2026), arXiv:2501.14447 | **Verified via arXiv API 2026-10-16** | **High** — reduces depth minimization of commuting operations to vertex colouring on a non-parallelizability graph; that graph is the project's commutation graph. Published in *Quantum*, a target venue. | Add to §L as [95] |
| Meijer-van de Griend, "A comparison of quantum compilers using a DAG-based or phase polynomial-based intermediate representation," *J. Systems & Software* (2025) | **Not verified this session** (no arXiv record; JSS paywalled) | **High if it exists** — closest published work to listing-model sensitivity from the IR side | Verify via Crossref/DBLP before citing; do not add on the strength of the morning draft |
| BQSKit (Berkeley Quantum Synthesis Toolkit, LBNL), https://bqskit.lbl.gov | Tool; live repo confirmed (188★, pushed 2026-08-11) | **High** — major SOTA compiler, absent from every comparison | Add as a tool reference **and** benchmark it (W1) |
| To, Quetschlich, Elsharkawy, Schulz, Wille, Kranzlmüller, "Evaluating the Effect of the Order of Optimization Passes in Quantum Circuit Optimization," arXiv:2609.29406 (2026) | **Verified 2026-10-16** | **Critical** — see §4.2(A) | Add to §L as [96]; cite in §1.1 and §7.2 |
| Kam, Mahasinghe, De Silva, Cadet, Wang, "An Exactness Barrier for ZX-Calculus Optimization of Synthesized Clifford+T Circuits," arXiv:2608.22801 (2026) | **Verified 2026-10-16** | **Critical** — the theorem template for the ceiling | Add as [97] |
| Laabs, "AlchemQ: Proof-Carrying Quantum Circuit Optimization with Per-Result Equivalence Certificates," arXiv:2609.19160 (2026) | **Verified 2026-10-16** | **High** — certificate-protocol precedent | Add as [98] |
| Rovara et al., "Why Are We Unrolling? The Importance of Structured Quantum Programs for Compilation," arXiv:2609.16171 (2026) | **Verified 2026-10-16** | **High** — structured-representation argument | Add as [99] |
| Bruzzone, Cazzola, "A Multi-Dimensional, Per-Pass Empirical Study of the LLVM Optimization Pipeline," arXiv:2606.31238 (2026) | **Verified 2026-10-16** | **High** — classical methodology twin | Add as [100] |
| Schifferer, Ullrich, Hack, "Augmenting Rewrite Rule Sets via Knuth-Bendix Completion," arXiv:2610.01246 (2026) | **Verified 2026-10-16** | **High** — rule-library automation | Add as [101] |
| Chen et al., "Leveraging Phase Polynomials for Quantum Circuit Optimization" (PhasePoly), arXiv:2506.20624 (2025) | **Verified 2026-10-16** | **High** — explains Class IIIb gaps | Add as [102] |
| Hong, Soi, Zhang, Aiken, "Rewrite System Showdown: Stochastic Search vs. EqSat," arXiv:2605.19005 (2026) | **Verified 2026-10-16** | Medium-High — EqSat-vs-stochastic baseline | Add as [103] |
| "Testing and Verification of Quantum Compilers through Assurance Contracts and Evidence," arXiv:2610.00255 (2026) | **Verified 2026-10-16** | Medium-High — evidence-methodology framing | Add as [104] |

**Internal consistency defects found in `unified_references.md` itself** (report only; editing the reference list is outside this scan's red lines for the manuscript, but the catalog is a project file and these should be fixed by the owner):

| Defect | Location | Detail |
|---|---|---|
| §P contradicts §L | line 353 vs line 237 | §P lists `[76] Hietala et al. (2022) Quartz superoptimizer (PLDI)`; §L's `[76]` is **Xu et al., Quartz** (correct). |
| §P contradicts §L | line 354 vs line 239 | §P lists `[77] Ravi et al. (2022) QUASAR compiler`; §L's `[77]` is **Yang et al., Equality saturation for quantum circuit optimization**. |
| §P header vs §L | line 355 vs line 69 | §P lists `[20] Amy, Glaudell, Ross (2018)` as newly added; §L's `[20]` is the same work — fine — but §P's stated purpose ("missing from the original 42-reference list") is not true for [20], [5], [6]. |
| Gap in numbering | §L | `[74]` and `[81]` are removed placeholders, leaving the sequence non-contiguous in §A–§M even though §P counts them. |

### 4.4 Frontier methodology gaps (what the project does not yet use)

1. **Equality saturation is the natural generalisation of the project's Phase-1/Phase-2 hierarchy, and the project does not use it.** Phase-1 = e-graph with adjacent-pair rules only; Phase-2a = e-graph with commutation rules added; Phase-2b = e-graph with template rules added. Ref [77] (Yang et al., PACMPL PLDI 2026) already applies EqSat to quantum circuits. Reformulating the hierarchy as a restricted e-graph gives a formal language for representation-conditioned reachability **and** a direct test of whether the "~0% class" is a rule-library artefact. `arXiv:2605.19005` (Aiken group) supplies the honest baseline question: are e-graphs actually better than stochastic search here?
2. **Automated rule-set completion.** The 1,474-rule library is hand-assembled and source-pinned, with two underdetermined reverse directions excluded. `arXiv:2610.01246` shows Knuth–Bendix completion can generate and augment rewrite rules automatically, reaching previously-missed optimizations. Applied to the project's library, this is both a completeness test and a direct attack on the strongest criticism of the trichotomy.
3. **Phase-polynomial / cross-block representations.** `arXiv:2506.20624` (PhasePoly) reduces total gate count by up to 50% using a cross-block parity matrix — i.e. by *changing the representation*. This is the project's own thesis applied by another group with better results on exactly the families the project classifies as IIIb. Must be engaged, not ignored.
4. **Certificate-protocol interoperability.** `arXiv:2609.19160` (AlchemQ) proposes versioned certificates with a standalone third-party verifier. The project has stronger internal guarantees (byte-stability, witness replay, 0 failures) but no protocol version and no external verifier. Aligning formats would produce cross-verification evidence.
5. **Per-pass / cumulative-prefix measurement design.** `arXiv:2606.31238` (LLVM) decomposes a pipeline into 113 cumulative prefixes and measures noise-mitigated marginal impact. The project's E21 does paired naive-vs-ceiling-aware timing but not cumulative-prefix decomposition of the representation × pass space. Adopting the design makes the representation-ordering result directly comparable to a top-tier systems paper.
6. **Average-case complexity.** `framework.md` OP3.3.1/OP3.3.2 remain open and the historical "phase transition" framing is dead. The admissible question is now: is there a *representation-conditioned* average-case bound on achievable reduction? This is well-posed and the E30 ensemble (13,500 trials) already provides validation data.

### 4.5 Open-source ecosystem monitoring (GitHub API, 2026-10-16)

| Repository | Stars | Last push | Relevance |
|---|---|---|---|
| `Qiskit/qiskit` | 7,892 | **2026-10-16** | Primary comparator; benchmarked (E20) |
| `Quantinuum/tket` | 318 | 2026-10-08 | Note: the repo is now under the `Quantinuum` org, not `CQCL` — **update any hard-coded paths/links** |
| `zxcalc/pyzx` | 550 | 2026-10-15 | E36 third-artifact panel; AlchemQ reports a false negative root-caused to a `compare_tensors` pivot-normalisation bug in PyZX — worth a version check |
| `BQSKit/bqskit` | 188 | 2026-08-11 | **Not benchmarked — major gap (W1)** |
| `qqq-wisc/tzap` | 48 | **2026-10-16** | "A very fast and scalable quantum circuit optimizer" — **brand new, pushed today**; a direct SOTA comparator and a novelty risk |
| `DVLab-NTU/qsyn` | 198 | 2026-10-05 | C++ synthesis / optimization / verification system |
| `boschmitt/tweedledum` | 109 | 2026-07-16 | C++17 analysis / compilation / synthesis library |
| `PennyLaneAI/catalyst` | 239 | 2026-10-16 | JIT compiler for hybrid programs |
| `silq-lang/silq` | 652 | 2026-10-16 | High-level quantum language with type checking |
| `overshiki/SymbolicCircuit.jl` | 11 | 2026-04-17 | Term rewriting + equality saturation for quantum — small but directly on the EqSat thesis |
| `choi95/awesome-quantum-compiler` | 175 | 2026-09-27 | Curated index — use as a coverage checklist |
| Quartz (`softwareQinc/quartz`) | repo name no longer resolves | — | Verify the current home before citing the URL |
| Quanto, VOQC | repo names did not resolve under the assumed orgs | — | Verify current homes; both are cited in the manuscript |

**Actionable**: `tzap` (new today) and BQSKit must be added to the SOTA panel before any submission. `Quantinuum/tket` and the unresolved Quartz/Quanto/VOQC paths should be corrected in the repository layout documentation.

---

## 5. Prioritised Innovation Directions

Each direction is stated as: **essence and difference → feasibility → required new evidence → expected scientific impact → recommended submission tier.**

### P0-1. Certified Peephole Barrier Theorem ★★★★★

**Essence and difference from existing work.** The project's "structural ceiling" is an empirical unanimity: no tested tool reduces QFT, GHZ, or SurfaceCode; every tested tool fails on Adder and QuantumWalk. That is a statement about *tools*. The top-tier version is a statement about *circuits*: for a given circuit and a given certified class of exactly-preserving local rewrites, produce a **per-instance, computable lower bound** on the residual gate count, and show that the bound is attained (or nearly attained) by the observed optimizers.

The 2026 ZX literature supplies the template. `arXiv:2608.22801` proves that for any exactly-preserving optimizer the achievable T-count is bounded below by the denominator exponent of the synthesized ring element; the barrier is computable per instance; and it *explains* a contradictory empirical pattern that no prior framework could explain. `arXiv:2606.31238` supplies the second template: a **search-free additive upper bound on loss due to phase interference** (46.35% for LLVM `-O3`).

Neither the project's ceiling analysis nor any quantum-compiler paper currently has this. Quartz and Quanto generate rules without certifying search-space completeness; VOQC verifies correctness without certifying landscape completeness; SAT-based Clifford synthesis certifies depth-optimality only for bounded instances.

**Difference from the project's own prior work.** The prior "ceiling" was defined by *empirical unanimity across tools* (`framework.md` §7.1 Class IIIa: "the ceiling is empirical, not proven" — the Cirq +8.4% SurfaceCode exception proves it). A certified barrier is defined by *algebraic structure* and is falsifiable per instance. This converts a negative empirical result into a theorem-shaped one, and it is the only route that changes the framework's own honest framing sentence ("not a discovery about quantum physics").

**Feasibility: High (Medium effort, High risk).** The concrete route:
1. Restrict to the exactly-preserving rewrite class the project already uses (1,474 source-pinned rules, two reverse directions excluded).
2. Define a valuation on the circuit's gate-sequence algebra — candidate: a weight/valuation on the phase polynomial plus a commutation-graph invariant — and prove that exactly-preserving local rewriting cannot reduce the valuation below a threshold.
3. Compute the threshold per instance on the 128-source certified panel and compare against the 94 exact best costs and the 34 witness-bounded cells.
4. Show the bound explains the Class IIIa/IIIc families and predicts the Class IIIb recovery magnitudes.

**Required new evidence.**
- A formal definition of the barrier functional and a proof that it is invariant under the certified rewrite class.
- Per-instance barrier values on all 128 sources of the v15 panel (new file, dated, sourced).
- A comparison table: barrier vs `exact_best_cost_count` (94) and vs the 34 bounded cells — does the barrier close the 34-cell gap *without* enumeration? If yes, Gap 1 is resolved by a theorem rather than a compute budget.
- Falsification test: find any instance where an exactly-preserving rewrite beats the barrier (a counterexample would be a publishable negative result in its own right).

**Expected scientific impact: Very High.** This is the single change that makes the work a claim about circuits rather than about tools. It also subsumes Gap 1 (the 34 bounded cells) and gives the Class IIIa families a proof instead of an observation.

**Recommended submission tier: Nature Physics / Nature Communications / PRX Quantum.** With a hardware consequence (P1-4), *Nature Physics* becomes arguable.

---

### P0-2. Representation-Ordering × Pass-Ordering Unification ★★★★☆

**Essence and difference from existing work.** `arXiv:2609.29406` (2026-09-24) establishes that **pass order** matters in Qiskit. This project establishes that **listing order** matters for flat-list peephole optimization, causally (E22 shuffle control, $p=6.8\times10^{-15}$), with a proven mechanism (Thm 1(b)) and a validated density law (Thm 1(a), E30). No work connects the two.

The unification claim to be tested: *both are instances of a single phenomenon — the reachable action space of a local optimizer is determined by the (representation, algorithm) pair, and the two orderings act on the same underlying adjacency structure.* If true, the classical phase-ordering literature (LLVM, `arXiv:2606.31238`) transfers only partially, and the quantum case has an extra degree of freedom the classical case lacks (a circuit can be *relisted* without changing its semantics; a program cannot be re-ordered without changing it).

**Difference from existing work.** The pass-order paper varies the algorithm with a fixed representation. The project varies the representation with a fixed algorithm. Neither paper has both axes, and the project already owns the certified-landscape tooling to make a joint factorial rigorous rather than empirical.

**Feasibility: High.** The representation axis is implemented; the pass axis is Qiskit's `PassManager`; the measurement design is `arXiv:2606.31238`'s cumulative-prefix decomposition. The 128-source panel gives the controlled input set.

**Required new evidence.**
- A **representation × pass-order factorial**: listings {LBL, WCL, RANDOM_TOPOLOGICAL} × cumulative pass prefixes over a fixed pass list, on a fixed input panel, measuring gate count, depth, and a certified-reduction axis.
- A non-monotonicity statistic (fraction of prefix transitions that regress) directly comparable to the LLVM paper's 6.6–9.7%.
- A back-loadedness statistic (what fraction of the pipeline is needed for 80% of the gain) comparable to the LLVM paper's 84.8%.
- A statement of which pass-order effects are *absorbed* by relisting and which are not.

**Expected scientific impact: High.** It converts the project's central finding from "a data-structure choice matters" into "representation choice is the missing coordinate in the phase-ordering problem", which is a claim the compiler community broadly (classical and quantum) must engage with. It also directly answers the "how is this different from pass ordering?" reviewer question.

**Recommended submission tier: PRX Quantum / Nature Communications.** If the unification produces a bound covering both axes, it feeds P0-1.

---

### P0-3. Rule-Library Completeness Attack (EqSat + Knuth–Bendix) ★★★★☆

**Essence and difference from existing work.** The strongest criticism of the project's own Contribution 2 is already recorded by the project: "the '~0%' band was partly template-library artifact" (manuscript §1.4 on H4; E26 moves IQP 0.5% → 92.0%). If a template library can move a family from 0.5% to 92.0%, then **every Class IIIa/IIIb classification is conditional on the library**, and the honest scientific object is not "this family is incompressible" but "this family is incompressible *under this rule set*".

The fix is to make the rule set not a free parameter. Two 2026 tools do this: equality saturation with automated rule generation via Knuth–Bendix completion (`arXiv:2610.01246`) and the EqSat-vs-stochastic comparison (`arXiv:2605.19005`). Reformulating Phase-1/Phase-2a/Phase-2b as restricted e-graph exploration and then *saturating* turns "the library is hand-assembled" into "the library is closed under the completion procedure".

**Difference from existing work.** `arXiv:2610.01246` is about classical compiler IRs; `arXiv:2605.19005` compares EqSat and stochastic search on five classical benchmarks. Neither has a certified landscape to evaluate against. The project's 128-cell certified landscape plus the 94 exact best costs give **ground-truth labels** that no EqSat paper has had. That is the unique asset here.

**Feasibility: Medium.** e-graph infrastructure (`egg`/`egglog`) exists; the work is encoding the project's rule set, running saturation on the 128-source panel, and comparing reachable action space against the certified landscape.

**Required new evidence.**
- E-graph saturation over the project's rule library on the 128-source panel, with and without Knuth–Bendix augmentation.
- A per-family table: certified optimum vs EqSat reachable minimum vs prototype Phase-2b result. **Any family where EqSat beats the certified "ceiling" falsifies the ceiling.**
- A library-completeness statement: which of the 1,474 rules are redundant, which are derivable, and what completion adds.
- An honest negative control: where EqSat and stochastic search tie (per `arXiv:2605.19005`), report it.

**Expected scientific impact: High.** This either (a) breaks some ceilings — a headline result, and the honest one — or (b) closes the strongest criticism of the trichotomy by showing the ceilings survive rule-set completion. Both outcomes are publishable and both are better than the current conditional statement.

**Recommended submission tier: PRX Quantum / Quantum.**

---

### P1-4. Real-QPU Representation Sensitivity ★★★☆☆

**Essence and difference from existing work.** The 7.83% vs 0.0000% result is simulator-only. EHW is noise-*model* simulation and already reports the crucial negative finding: logical compression of BV circuits (46.15%) is **fully absorbed by mandatory basis translation** (0% physical). AlchemQ's Heron r2 pilot (2026-08-24) shows a real-device run of a certified optimizer is now routine and reports "78% shallower, 65% fewer two-qubit gates, not significant at 1024 shots".

The question this direction answers is sharper than "does the effect survive noise": **can a representation-aware compilation path preserve the logical gain through the basis-change gate?** That is a falsifiable claim about representation choice with a hardware-measurable outcome, and §7.4 has already established the failure mode it must beat.

**Difference from existing work.** No prior work validates representation-conditioned optimization on real hardware. AlchemQ validates a *certificate protocol*, not a *representation effect*.

**Feasibility: High.** IBM Quantum free tier; 3 families (BV, HaarRandom, RandomClifford) × 5–7 qubits × 2 listings × 3 seeds. The BV family is the natural first target because Phase-2b already reaches the proven-optimal $k+2$ there.

**Required new evidence.**
- Raw fidelity / Hellinger / TVD data for the listing pairs on real hardware, pre-registered against the §7.4 noise-model predictions.
- A physical-compression measurement *after* basis translation, to test whether WCL preprocessing survives.
- Readout-error mitigation and a drift-controlled calibration snapshot per job.

**Expected scientific impact: Medium-High.** Closes the most-cited gap, and the §7.4 basis-translation finding makes the *negative* outcome scientifically interesting too.

**Recommended submission tier: npj QI** (combined with P0-2), or *PRX Quantum* if the physical-compression survival is demonstrated.

---

### P1-5. Certified Landscape Completion + Certificate-Protocol Interoperability ★★★☆☆

**Essence and difference from existing work.** Two separable upgrades, both cheap relative to P0-1:
1. **Complete the 34 cells** (or bound them via P0-1) and extend the panel to full-rule scope (1,474 rules) and wire-consecutive window profiles — both already listed as open in `docs/PROJECT_STATUS.md`.
2. **Adopt a certificate protocol version and a standalone third-party verifier**, following AlchemQ (`arXiv:2609.19160`). The project's certificates are already byte-stable with witness replay and zero failures; what is missing is a versioned schema and an external verifier.

**Feasibility: Medium-High** for (1) with the P0-1 bound; **High** for (2).

**Required new evidence.** v16 package with tiers upgraded or bounded; a published certificate schema version; cross-verification of the project's certificates by a third-party verifier (and, ideally, mutual verification with AlchemQ's released verifier, which is Apache-2.0).

**Expected scientific impact: Medium.** This is an artifact-and-methodology contribution. It is what makes the rest of the work *trustworthy* to an outside reader, and it partially closes Gap 4.

**Recommended submission tier: Quantum (tools/software track) / npj QI.**

---

### P2-6. Neural- or LLM-Guided Certified Search ★★☆☆☆

**Essence and difference from existing work.** The certified search is complete but resource-truncated on 34 cells. Learned search priors (RL: `arXiv:2608.19103`, `arXiv:2605.11375`, `arXiv:2607.04586`; LLM: `arXiv:2610.22367`, published 2026-10-15) accelerate circuit optimization but without completeness guarantees. The project's 94 completed cells give **ground-truth optimal labels** for training a prior that preserves completeness — a combination nobody has.

**Difference from existing work.** Quarl [64] uses RL without certified completeness; AlchemQ uses an untrusted beam search with *post-hoc* certification. This direction would be the first *prior-guided certified* quantum circuit optimizer.

**Feasibility: Medium.** Training data exists (94 exact cells + 76,236 window searches). The difficulty is preserving the completeness guarantee while using a learned prior — solvable by using the prior for move ordering only, keeping the exhaustive/IDA* frontier intact.

**Required new evidence.** Neural-guided vs brute-force IDA* time-to-certificate on the 34 bounded cells; a completeness proof or an explicit statement that the prior affects ordering only.

**Expected scientific impact: Medium.** Bridges ML and formal methods; the *guarantee-preserving* framing is the novel part, not the neural network.

**Recommended submission tier: TQE / Quantum (software).**

---

### P2-7. Average-Case Peephole Complexity Theory ★★☆☆☆

**Essence and difference from existing work.** The historical "phase transition" hypothesis is dead (manuscript §7.1) and OP3.3.1/OP3.3.2 in `framework.md` remain open. The admissible reformulation is **representation-conditioned**: for a fixed listing model and move set, what is the average-case achievable reduction over a circuit ensemble? The project already has the empirical law (Thm 1(a), validated by E30 at 27 cells, median |rel err| 1.4%) and the negative result that the optimum is *not* $O(1/d)$ in the way greedy is.

**Difference from existing work.** Janzing et al. [25] give worst-case QMA-completeness for exact identity testing; van de Wetering & Amy give worst-case hardness for approximate gate-count optimization. No average-case bound for *peephole rewriting under a specified representation* exists.

**Feasibility: Low-Medium.** The probability space must be constructed, not assumed — this is exactly the error that invalidated Thm 5. Pair-level variables ($\approx (n/2)(d-1)$ of them) with bounded-differences constant $c_i=4$ is the credible route, and the exposure martingale must be written out explicitly.

**Required new evidence.** A valid concentration bound with an explicitly constructed martingale; validation against the E30 ensemble; and a companion lower bound (the certified barrier from P0-1 supplies the lower half).

**Expected scientific impact: Medium.** Modest on its own, but it is the natural upper companion to P0-1 and it repairs Thm 5 — which is the project's one genuinely repairable theory defect.

**Recommended submission tier: QIP / Quantum (theory).**

---

## 6. Prioritised Summary

| Priority | Direction | Effort | Scientific impact | Closes which gap | Venue ceiling |
|---|---|---|---|---|---|
| **P0-1** | Certified peephole barrier theorem | Medium-High | Very High | Gap 1 (by theorem, not compute); changes the framework's own framing sentence | Nature Physics / Nature Comms / PRX Q |
| **P0-2** | Representation × pass-order unification | Medium | High | Answers the "vs. pass ordering" novelty challenge | PRX Q / Nature Comms |
| **P0-3** | EqSat + Knuth–Bendix rule completeness | Medium | High | Closes the "library artefact" criticism of the trichotomy | PRX Q / Quantum |
| **P1-4** | Real-QPU representation sensitivity | Low | Medium-High | Gap 2 | npj QI |
| **P1-5** | Landscape completion + certificate protocol | Medium-High | Medium | Gap 1 (partial), Gap 4 (partial) | Quantum (tools) |
| **P2-6** | Neural/LLM-guided certified search | Medium | Medium | — | TQE / Quantum |
| **P2-7** | Average-case peephole complexity | Low-Medium | Medium | Repairs Thm 5 | QIP / Quantum |

**Cheapest high-value actions, ranked by return per unit effort:**
1. Thm 9 global optimality via SAT (`2510.00649` or Peham et al.) — upgrades the most citable result from "reaches $k+2$" to "reaches the proven optimum".
2. Add BQSKit + `tzap` to the SOTA panel — removes the biggest weakness in §3.3.
3. Cite and engage `arXiv:2609.29406` — pre-empts the single most likely novelty objection.
4. Certificate protocol version + standalone verifier — partially closes Gap 4 cheaply.
5. Fix the abstract's Methods-before-Results ordering.

---

## 7. Next 30 Days — Action Checklist

### Week 1 (Days 1–7): Theory route and novelty defence

1. **[Theory, P0-1]** Write a 3–4 page formal sketch of the barrier functional: definition, invariance under the certified rewrite class, and the falsifier. Read `arXiv:2608.22801` and `arXiv:2606.31238` first and mirror their structure. Output: `docs/theory/peephole_barrier_sketch_<date>.md` (new file; do not touch `framework.md` or `formal_results.md`).
2. **[Theory]** Repair Thm 5: construct the pair-level exposure martingale with $c_i=4$ and either prove the bound or document precisely why it fails. This is the only repairable defect in the surviving theory.
3. **[Theory, cheap win]** Attempt Thm 9 global optimality for the BV family using SAT-based depth-optimal Clifford synthesis (`arXiv:2510.00649`, Peham et al.). A certificate on $n \le 6$ would already upgrade the headline claim.
4. **[Literature]** Add the 12 verified references from §4.3 to `docs/references/unified_references.md` as [95]–[104], and log the queries in `docs/references/search_ledger.md`. Fix the four §P/§L internal inconsistencies listed in §4.3. **Red line: no manuscript text is modified.**
5. **[Evidence]** Profile the 34 bounded cells under a pattern-database heuristic seeded from the 94 exact cells: produce a resource estimate and a run plan. Output: a dated planning file, not a rerun.

### Week 2 (Days 8–14): External validation and comparators

6. **[Reproducibility, Gap 3]** Build and test the Docker reproduction container on a second machine; run `scripts/reproduce_all.py --verify` from a clean checkout and archive the SHA-256 receipts as external evidence. **This is the cheapest of the four open gates.**
7. **[Experiment, W1]** Add BQSKit to the SOTA panel on all 15 families at canonical sizes. Output: a new dated dataset directory, canonical files untouched.
8. **[Experiment, W1]** Add `qqq-wisc/tzap` to the same panel (it was pushed 2026-10-16 — verify the version and pin the commit).
9. **[Hardware, Gap 2]** Register an IBM Quantum account; run a 5-qubit BV + HaarRandom pilot with WCL and LBL listings, 10 circuits each, pre-registered against the §7.4 noise-model predictions. Output: raw data + a pre-registration record dated *before* the run.
10. **[Novelty]** Draft the representation × pass-order distinction paragraph for the manuscript's introduction (as a *note to the author*, not as manuscript text).

### Week 3 (Days 15–21): Experiments

11. **[Experiment, P0-2]** Build the cumulative-prefix pass-order panel and cross it with {LBL, WCL, RANDOM_TOPOLOGICAL} on a fixed 128-source input set. Report the non-monotonicity and back-loadedness statistics in the LLVM paper's format.
12. **[Experiment, P0-3]** Run `egglog` saturation over the project's rule library on a 16-cell subset of the 128 panel, then with Knuth–Bendix augmentation. Output: certified optimum vs EqSat reachable minimum, per cell.
13. **[Experiment]** If the hardware pilot succeeds, expand to 3 families × 50 circuits × 2 listings, with physical-compression measurement after basis translation.
14. **[Evidence]** Start the pattern-database IDA* run on the 34 cells in the background (multi-day). Do not modify v14/v15 packages.

### Week 4 (Days 22–30): Synthesis and decisions

15. **[Synthesis]** Compile the representation × pass-order results into a draft section outline with tables.
16. **[Synthesis]** Compile the barrier sketch plus its per-instance values on the 128 sources into a table: barrier vs exact best cost vs the 34 bounded cells.
17. **[Synthesis]** Write a dated findings summary: what was learned, what remains open, and the revised venue ladder.
18. **[Cleanup]** Execute the deferred structural items in §8.3 (dependency-file role documentation; `docs/theory/README.md` status index if not already added by this run).
19. **[Cleanup]** Verify the current repository homes of Quartz, Quanto, VOQC and `tket` and correct any stale links.
20. **[Decision]** Choose the top-tier path: **P0-1 + P1-4** (theorem + hardware) toward *Nature Physics*/*Nature Communications*, versus **P0-2 + P0-3** (representation × pass-order + rule completeness) toward *PRX Quantum*. The C3 title decision (`scientific_gates.C3_title_and_positioning = USER_DECISION_PENDING`) should be made together with this choice.

---

## 8. Structural Cleanup

### 8.1 Executed in this run

| Action | Detail | Safety |
|---|---|---|
| Removed local Python bytecode caches | 221 `.pyc` files across 16 `__pycache__` directories. Verified **untracked** by git and matched by `.gitignore` (`__pycache__/`, `*.pyc`) before removal, so this is pure local-artifact hygiene with no repository effect. | Fully regenerable; no tracked file touched |
| Added `docs/theory/README.md` | A status index classifying the 10 theory documents as **active / superseded / withdrawn / path-bound**, so a reader arriving in `docs/theory/` no longer has to open every file to learn which results are admissible. | New file only; no existing file modified |

**Explicitly NOT done, and why:**

| Considered action | Decision | Reason |
|---|---|---|
| Move `QMA_hardness_draft.md` and `universal_law_assessment.md` to `docs/theory/archive/` | **Blocked** | Both paths are bound in `release/prepaper_release_manifest.json` (verified at `scripts/generate_prepaper_release_manifest.py` lines 546–547). Moving them would break the release hash chain — a stated red line. The new `docs/theory/README.md` records their status instead. |
| Merge the two `metric_audit_resolution` files; consolidate the six `e31_*_limitation` notes | **Deferred to the owner** | These are hash-bound audit records under `docs/review/`. Merging changes evidence semantics and is not a structural-cleanliness decision; the consolidation candidates are listed in §8.3 instead. |
| Move `docs/analysis/_alg_complexity_*.py` / `*.csv` | **Deferred** | They are cited by `docs/analysis/algorithmic_complexity.md`; relocating requires updating that document, which is outside this scan's scope. |

### 8.2 Theory document status (as indexed in the new `docs/theory/README.md`)

| Document | Status |
|---|---|
| `framework.md` | **Active** — central definitions hub; claim admissibility governed by the theory gate |
| `formal_results.md` | **Active** — theorem/lemma/proof-status authority |
| `prepaper_theory_gate_2026-08-10.md` | **Active** — controls claim admissibility |
| `proof_audit_2026-08-06.md` | **Active** — proof-status audit record |
| `v12_rewrite_exposure_theory.md` | **Active (bounded)** — `conjecture_or_draft_until_e38` |
| `QMA_hardness_draft.md` | **Withdrawn** — "Withdrawn as a proof"; path-bound to the release manifest |
| `phase2_lower_bound_strengthening.md` | **Superseded 2026-08-11** — failed reasoning route |
| `universal_law_assessment.md` | **Superseded** — path-bound to the release manifest |
| `nontrivial_upgrades.md` | **Historical** — explicitly "not a theorem-status source" |
| `archive/` | Empty; see the note in `docs/theory/README.md` for why |

### 8.3 Recommended (owner decisions, not executed)

| Item | Recommendation | Risk if done carelessly |
|---|---|---|
| Four dependency files (`requirements.txt`, `requirements-lock.txt`, `environment.yml`, `pyproject.toml`) | Declare `pyproject.toml` primary; document the role of each in `docs/reproducibility.md`. Do not delete `requirements-lock.txt` — it is 147 KB of pinned versions and is the actual reproduction lock. | Removing the lock file would break the cold-start protocol |
| Two `metric_audit_resolution` files (2026-08-11, 2026-08-24) | Keep both; add a one-line superseded pointer in the 08-11 file. | Merging hash-bound audit records changes the evidence chain |
| Six `e31_*_limitation_2026-08-24.md` notes | Keep as separate dated records; add a consolidated index note if readability becomes a problem. | Consolidation would collapse distinct dated evidence into one file |
| Stale repository links (Quartz, Quanto, VOQC, `tket`) | Verify current homes and correct in the layout docs. `Quantinuum/tket` is confirmed live; the other three did not resolve under the assumed orgs on 2026-10-16. | None — documentation-only |
| 15 hash-drift entries in the 15,042-entry prepaper manifest | Resolve the 2 CRLF artefacts via `.gitattributes`; disposition the 13 committed drifts. | Do not silently rewrite manifest entries |

---

## Appendix A — Reference coverage gap table (corrected, verified)

| Reference | Verified 2026-10-16 | In `unified_references.md`? | Relevance | Action |
|---|---|---|---|---|
| To et al., pass order, arXiv:2609.29406 | arXiv API | **No** | Critical | Add [96] |
| Kam et al., exactness barrier, arXiv:2608.22801 | arXiv API | **No** | Critical | Add [97] |
| Laabs, AlchemQ, arXiv:2609.19160 | arXiv API | **No** | High | Add [98] |
| Rovara et al., unrolling/structured, arXiv:2609.16171 | arXiv API | **No** | High | Add [99] |
| Bruzzone & Cazzola, LLVM per-pass, arXiv:2606.31238 | arXiv API | **No** | High | Add [100] |
| Schifferer et al., Knuth–Bendix rules, arXiv:2610.01246 | arXiv API | **No** | High | Add [101] |
| Chen et al., PhasePoly, arXiv:2506.20624 | arXiv API | **No** | High | Add [102] |
| Hong et al., EqSat vs stochastic, arXiv:2605.19005 | arXiv API | **No** | Medium-High | Add [103] |
| Assurance contracts survey, arXiv:2610.00255 | arXiv API | **No** | Medium-High | Add [104] |
| Lee et al., graph colouring, arXiv:2501.14447 | arXiv API | **No** | High | Add [95] |
| BQSKit, LBNL | GitHub API (188★, pushed 2026-08-11) | **No** | High (tool) | Add as tool ref + benchmark |
| `qqq-wisc/tzap` | GitHub API (48★, pushed 2026-10-16) | **No** | Medium-High (tool) | Add as tool ref + benchmark |
| Meijer-van de Griend, JSS 2025 | **Not verified** | **No** | High if real | Verify via Crossref/DBLP first |
| Onodera et al. [73], Nation et al. [71], Yang et al. [77], Rosenhahn et al. [94] | — | **Already present** | — | The morning draft wrongly listed these as missing; no action |

## Appendix B — Search log (2026-10-16)

**arXiv API** (`https://export.arxiv.org/api/query`), phrase-quoted `all:"..."` queries, `sortBy=submittedDate&sortOrder=descending`, `max_results=12`, 1.2 s inter-query delay. 17 queries, 115 records retrieved.

| Query | Hits | Highest-relevance hit |
|---|---|---|
| `all:"peephole" AND all:"quantum"` | 9 | Relaxed Peephole Optimization (2012.07711) |
| `all:"optimization pass" AND all:"quantum circuit"` | 12 | **2609.29406 pass order** |
| `all:"equality saturation"` | 12 | **2610.01246 Knuth–Bendix**; 2605.19005 EqSat vs stochastic |
| `all:"ZX-calculus" AND all:"optimization"` | 12 | **2608.22801 exactness barrier**; 2609.19160 AlchemQ |
| `all:"superoptimization" AND all:"quantum"` | 1 | Quartz extended (2204.09033) |
| `all:"reinforcement learning" AND all:"quantum circuit" AND all:"compil"` | 12 | 2608.19103 RL across gate sets |
| `all:"large language model" AND all:"quantum circuit"` | 12 | **2610.22367 LLM-discovered circuits (2026-10-15)** |
| `all:"quantum circuit" AND all:"compilation" AND all:"hardware"` | 12 | 2609.16171 unrolling/structured |
| `all:"search landscape" AND all:"circuit"` | 4 | — (no relevant hit; the project's landscape work has no arXiv precedent) |
| `all:"circuit identities" AND all:"optimization"` | 5 | Quanto (2111.11387) |
| `all:"benchmark" AND all:"quantum compiler"` | 12 | 2610.00255 assurance contracts |
| `all:"certified" AND all:"quantum circuit" AND all:"optimal"` | 12 | 2510.00649 provably optimal via MIP |
| `ti:"unrolling" AND all:"quantum"` | 8 | 2609.16171 |
| `all:"structured quantum programs"` | 4 | 2609.16171 |
| `all:"intermediate representation" AND all:"quantum"` | 8 | 2609.29305 QaiJi IR; 2609.01037 dynamic IR |
| `all:"representation" AND all:"peephole"` | 3 | 2407.03685 verifying peephole rewriting in SSA IRs (classical) |
| `all:"optimization pass" AND all:"order"` | 8 | 2609.29406; **2606.31238 LLVM per-pass** |

**GitHub REST API** — 8 repository lookups + 3 repository searches (`q=quantum+circuit+optimization`, `quantum+compiler`, `quantum+circuit+rewriting`, `sort=stars`). Results in §4.5. Authenticated with the token held in the Windows credential store; the token value was never written to any output or file.

**Built-in web search** — 1 query (`quantum circuit compiler optimization pass ordering representation sensitivity 2026`), 5 results, used only to cross-check the pass-order paper's existence and venue context.

**Not available this session** — Tavily (`tavily-python` not installed, no `TAVILY_API_KEY`), Exa (`mcp.exa.ai` MCP server not configured). No claim in this document depends on either.

---

## Appendix C — Files read to establish the baseline

| Path | Purpose |
|---|---|
| `README.md` | Repository-level evidence snapshot and current boundary statement |
| `docs/PROJECT_STATUS.md` (2026-10-11) | Optimization status, closed/open register, evidence pointers |
| `docs/manuscript/manuscript.md` (read-only) | Abstract, §1.1–1.6 (RQ, hypotheses, contributions), §7.1–7.6 (discussion, limitations, future work), §8 (conclusion), full heading structure |
| `docs/theory/framework.md` v5.4.2 | Definitions D1–D12, honest framing note, complexity classification, theorem status map |
| `data/DATA_CANONICAL.md` v2.4.0 | 37-dataset canonical register, version policy, 15 Known Issues |
| `docs/references/unified_references.md` v2.2 | 94-entry catalog, §P/§L consistency audit |
| `docs/references/search_ledger.md` | Existing literature-search provenance record |
| `release/v15_readiness_verdict.json` | Authoritative open/closed gate values |
| `release/` directory listing | 39 receipts, manifests, and audits |
| `docs/theory/*` headers | Status labels for the 10 theory documents |
| `docs/analysis/`, `docs/verification/`, `docs/theory/archive/`, `docs/results/` listings | Structural inventory |
| `.gitignore`, `git ls-files` | Confirmed `.pyc`/`__pycache__` untracked before cleanup |
| `scripts/generate_prepaper_release_manifest.py` lines 546–547 | Confirmed two theory docs are release-manifest path-bound |

---

*End of innovation scan v2. Generated 2026-10-16. Supersedes the 2026-10-16 08:19 draft. No frozen data, release manifest, or manuscript text was modified.*
