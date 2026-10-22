# Innovation Scan — Quantum Peephole Ceiling: 科研全流程体检 + 创新方向扫描

**Date:** 2026-10-17
**Scope:** `D:/Desktop/Q-research` — full-process audit (paper writing excluded), frontier scan,
and **execution** of every actionable item identified.
**Supersedes:** `2026-10-16_innovation_scan.md` (v2). This run re-verified the baseline, re-ran
the literature scan on a fresh day, and — unlike the previous run — *executed* the improvement
items rather than only listing them.

**Red lines observed (and how):**

| Red line | Status | Evidence |
|---|---|---|
| `data/` frozen data unmodified | **Honoured** | `git status --porcelain data/` is empty after every step of this run |
| `release/` hash manifests unmodified | **Honoured** | `git status --porcelain release/` is empty |
| `docs/manuscript/` read-only | **Honoured** | Not opened for writing; all manuscript claims below are read from `manuscript.md` |
| New evidentiary files carry a date and a source | **Honoured** | Every new artifact is under `2026-10-17_*` with an input `sha256` in its `protocol.json`/`summary.json` |
| Read-only scanning, no deletions | **Amended by explicit user instruction** | Only three **empty** directories were removed (`docs/review/wave2`, `docs/review/wave3`, `analysis/figures/v14_extension/source_data`). No file was deleted. See §8. |

---

## 0. Executive summary

### 0.1 Verdict

The engineering chain is strong, honest, and — this run confirms — **internally consistent under
an independent verifier** (20/20 checks, §5.2). The `NOT_READY_FOR_PAPER` verdict in
`release/v15_readiness_verdict.json` is correct and should not be softened.

What changed today is the **competitive picture**, and it is more urgent than yesterday's scan
suggested:

> **Four independent 2026 papers now argue that representation choice gates compiler capability**
> ([96] pass order, [99] unrolling, [105] recoverability, [106] synthesis availability), and
> **two of them already deliver provable bounds** ([97] exactness barrier, [105] entropy lower
> bound). "Representation matters" is becoming consensus. The project's differentiator is no
> longer the *phenomenon* — it is the **certified landscape**: an exact, replayable, per-source
> map of the reachable action space, which none of the competing works has.

### 0.2 What was executed in this run (not just recommended)

| # | Action | Result |
|---|---|---|
| E1 | **Certified two-sided gate-count intervals for the whole 128-source v15 panel** | New evidence: `docs/review/science_boost/2026-10-17_certified_lower_bounds/`. Every source satisfies `best_cost ≥ baseline − 6`. The 34 previously *upper-bounded-only* cells now have certified intervals of width 4–5 (mean 4.56; ≤ 2.87% of baseline). 0 closed exactly. |
| E2 | **Exact reconstruction of all 128 frozen E45 root listings** | 128/128 reproduce bit-exactly from the frozen sources under `qiskit 2.4.1`. A previously undocumented subtlety was identified and is now documented: sources whose normalized circuit exceeds the 80-gate comparator budget get the *normalized* circuit as root, not the Greedy output. |
| E3 | **Necessary-condition test of the Candidate Theorem 5 tail bound** | New evidence: `docs/review/science_boost/2026-10-17_thm5_tail_test/`. 0 of 27 cells violate `Var(X) ≤ 2N`; dispersion index median **0.976** (range 0.913–1.225) ⇒ X is Poisson-like, and the true concentration scale is ≈ `E[X]`, 10–40× smaller than the stated `N = n(d−1)`. |
| E4 | **Theorem 5 repair note** | `docs/theory/thm5_concentration_repair_2026-10-17.md`: two restricted statements that *are* valid (5-A fixed matching, 5-B conditional), an explicit proof that the bounded-differences route cannot be repaired for the random-matching generator, and a data-backed replacement conjecture (5-C, Poisson/Bernstein). |
| E5 | **Independent third-party certificate verifier + protocol version** | `scripts/verify_certificate_qrcert_v1.py`, protocol `qrcert/v1`. Re-derives the published v15 numbers from the frozen artifacts **without importing any producer verifier**: 20/20 PASS, `CERTIFIED_CONSISTENT`. Certificate at `docs/review/science_boost/2026-10-17_certificate_verification/v15_certificate.json`. |
| E6 | **Static type-checking gate** | `mypy.ini` added; `python -m mypy src` now runs. 24 errors found in 6 files. The one genuine latent hazard (variable shadowing inside `_minimax_barrier_compact`) was fixed; the fix is behaviour-neutral and was verified by 15 tests + 4 project verifiers still passing. |
| E7 | **Reference catalogue gap closed additively** | `docs/references/reference_additions_2026-10-17.md` — 18 verified entries ([95]–[112]) plus a 6-item defect register. Not merged into the hash-bound catalogue; the merge instruction is included. |
| E8 | **Repository hygiene** | 3 empty directories removed; 0 duplicate-content files; 0 `__pycache__` outside `data/`; `data/` and `release/` verified untouched. |
| E9 | **Pre-existing release-chain defect surfaced** | `scripts/verify_prepaper_release_manifest.py` currently **fails** with `byte/hash mismatch: docs/review/metric_audit_ledger_2026-08-24.csv`. This is pre-existing (not caused by this run) and needs an explicit drift disposition. See §5.3. |

### 0.3 Priority ranking (revised for 2026-10-17)

| # | Direction | Leverage on the Nature/Science bar | Effort | Venue ceiling |
|---|---|---|---|---|
| **P0-1** | **Certified peephole barrier theorem** (now *contested* — two rival provable-bound papers) | ★★★★★ | High | **Nature Physics / Nature Communications / PRX Quantum** |
| **P0-2** | **Unified account of the four representation-ordering results** | ★★★★☆ | Medium | **PRX Quantum / Nature Communications** |
| **P0-3** | **Rule-library completeness via EqSat + Knuth–Bendix** | ★★★★☆ | Medium | PRX Quantum / Quantum |
| **P1-4** | Real-QPU representation sensitivity | ★★★☆☆ | Low | npj QI / PRX Quantum |
| **P1-5** | Landscape completion + certificate interop *(partly executed today)* | ★★★☆☆ | Medium | Quantum (tools) |
| **P1-6** | **NEW — Complexity classification of Phase-2b template matching** (Fujii's template-compilation landscape supplies the template) | ★★★☆☆ | Medium | QIP / Quantum (theory) |
| **P2-7** | Average-case peephole complexity *(upgraded: the Poisson route is now evidence-backed)* | ★★★☆☆ | Medium | QIP / Quantum |
| **P2-6** | Neural/LLM-guided certified search | ★★☆☆☆ | Medium | TQE / Quantum |

---

## 1. Factual baseline (re-verified 2026-10-17)

### 1.1 Evidence chain

| Layer | Result | Source read this session |
|---|---|---|
| E1–E30 canonical | 35 active canonical datasets / 96,205 rows (37 listed / 96,289 incl. 2 superseded provenance entries) | `data/DATA_CANONICAL.md` v2.4.0 |
| E31 sealed factorial | 28,152 rows | `docs/EXPERIMENT_HISTORY.md` |
| E32–E37 | Telemetry, real scale, MQT cross-abstraction, Benchpress stress, PyZX, energy/cost | `release/e32_*` … `release/e37_*` |
| v13 E45 screening | 0/18 eligible; max guided failure 63.28125% | `release/v13_readiness_verdict.json` |
| v14 E45 screening | 18/18 eligible; 13,824 rows; 0 semantic failures | `release/v14_readiness_verdict.json` |
| v14 exact finite horizon | 93 exact; 35 resource-truncated | same |
| v14 IDA* escape | 63 exact escapes; 65 exact local optima | `docs/PROJECT_STATUS.md` |
| v15 landscape integration | 128 classified; tiers 93 `COMPACT_COMPLETE_ENUMERATED` / 1 `COMPACT_COMPLETE_DERIVED` / 34 `CLASSIFICATION_EXACT_EXTRAS_BOUNDED`; escape 63; local optimum 65; exact best cost 94; witness replay failures 0 | `release/v15_readiness_verdict.json` |
| v15 E46 window landscape | 76,236 window rows; 39,474 escapes; 0 truncated windows; `PANEL_COMPLETE` | same |
| Theory admissible | Obs 1(a/b), Thm 1(a/b), Thm 2(a), Lemma 3/4, Thm 2c, Thm 7, Thm 9, Prop 1, Prop 6 | `docs/theory/framework.md`, `formal_results.md` |
| Theory defective | Thm 5 (proof incomplete), Thm 6 general (refuted), Thm 8 (withdrawn), Thm 2(d) (invalid), QMA-hardness (withdrawn), Obs 1 general (withdrawn), C1 (refuted) | same |

### 1.2 The three contributions, as written

1. **Listing-model sensitivity.** 0.0000% (LBL, E1, 25,000 circuits) → **7.83% ± 3.95%** (WCL,
   E19, 10,000 rows) on the same ensemble; mechanism proven (Thm 1(b)); density law validated
   (Thm 1(a), E30, 27 cells, max |z| = 2.86, median |rel err| 1.4%); shuffle control E22
   (*increases* reduction, p = 6.8e-15).
2. **Search-space stratification.** 6-class / 15-family taxonomy; Class IIIa genuine structural
   ceiling (QFT, GHZ, SurfaceCode) with one Cirq +8.4% exception; Phase-2b reaches the
   **provable k+2 optimum on 80/80 BV instances** (n = 3–10, mean 69.2%), 3.1–4.2× above the
   rigorous Thm 9 bound.
3. **Ceiling-aware optimizer.** 34.97× aggregate prototype speedup; **2.20× under symmetric
   timing**; output bit-identical (570/570 paired trials).

### 1.3 Closed / open register (re-verified)

| Item | Status | Authority |
|---|---|---|
| Frozen rewrite library (1,474 safe directed rules) | Closed for the declared library | `docs/PROJECT_STATUS.md` |
| E44 oracle (512 cases / 1,024 rows) | Closed | same |
| E45 v14 screening / escape-depth classification / v15 classification bookkeeping | Closed | same |
| E46 window landscape | PANEL_COMPLETE | v15 verdict |
| Determinism and failure handling | Closed | `docs/PROJECT_STATUS.md` |
| E1–E37 historical evidence | Preserved; no rerun justified | same |
| **34 long-listing escape cells** | **Open (bounded form)** — now with a *certified lower bound* (this run) | v15 verdict + §2.1 |
| Independent cold start | **Open** (`external_cold_start: OPEN`) | v15 verdict |
| Real QPU | **Open** (`real_qpu: OPEN`) | same |
| External execution gate / release authority | **Open** (`release_authority: OPEN`) | same |
| C3 title and positioning | **USER_DECISION_PENDING** | same |
| Full-rule-scope (1,474-rule) panels; wire-consecutive window profiles | Open | `docs/PROJECT_STATUS.md` §Remaining work |

### 1.4 The honest scientific boundary (unchanged, and still the binding constraint)

`docs/theory/framework.md` §"Honest framing note" item 3:

> "The 'structural ceiling' is a limit on a specific class of *classical algorithms* (peephole
> rewriters) applied to a specific *data structure* (gate sequences). It should not be confused
> with circuit complexity lower bounds."

**Any Nature/Science path must change this sentence.** Two routes remain: make the barrier a
property of the *circuit* (§2.1 / P0-1), or make it hardware-measurable (P1-4). Today's new
evidence (§2.1) narrows the first route considerably, in a useful way.

---

## 2. Known gaps — verification and upgrade, with what was executed today

### Gap 1 — 34 witness-bounded long-listing escape cells → **now certified two-sided**

**Verification (unchanged):** `bounded_best_cost_count = 34`; `CLASSIFICATION_EXACT_EXTRAS_BOUNDED
= 34`; the verdict forbids claiming enumerated quantities for these cells.

**What was executed.** A certified lower bound was derived from the project's own admissible
per-action bound rather than from a bigger compute budget:

* `_maximum_single_step_reduction(rule_library, "e44_core_v1") = 2` — the project's own safe
  admissible bound on one action's gate-count decrease.
* Therefore, for any H-step trajectory, `cost(s_H) ≥ cost(s_0) − H·D`. With the frozen
  `horizon = 3` and `D = 2`: **`best_cost ≥ baseline − 6` for every source in the panel.**
* A per-gate-name refinement (`r_g` per gate name, from the 149 core rules plus the
  `pair_v1`/`exchange` auxiliary actions) was also computed; it never exceeds the aggregate
  bound (0 of 128 cells), so the aggregate form is reported as the certificate.

**Result (new evidence, `docs/review/science_boost/2026-10-17_certified_lower_bounds/`):**

| Quantity | Value |
|---|---|
| Panel sources resolved / root listings reproduced exactly | 128 / **128** |
| Cells violating `best_cost ≥ baseline − 6` | **0** |
| The 34 bounded cells: interval width min / mean / max | 4 / 4.56 / 5 |
| Max interval width as a fraction of baseline | **2.87%** |
| Bounded cells closed exactly by the bound | 0 |
| Panel-wide max interval width | 6 |

**Interpretation.** These 34 cells are no longer "bounded above only". They are pinned to within
4–5 gates on circuits of 174–12,422 gates. The uncertified beam value (`compact_best_cost`) lies
inside every interval, so the beam is not refuted either. **The remaining deficit is now a
*heuristic-strength* problem, not a *compute-budget* problem**: a stronger admissible potential
than the flat 2-per-step cap is what closes them, and that is exactly P0-1's object.

**Second new fact from the same evidence.** Of the 149 rules in `e44_core_v1`, **84 are
cost-neutral, 49 increase the gate count by 1, 5 increase it by 2, 10 reduce it by 1, and exactly
one reduces it by 2.** So **138 of 149 (92.6%) of the certified directed rules cannot reduce the
gate count at all.** This is a new, quotable structural characterisation of the certified scope,
and it is the natural starting point for a barrier functional: the barrier should be built from
the *non-reducing* 92.6%, not from the reducing 7.4%.

**Also from the same run — a reproducibility result relevant to Gap 3.** All 128 root listings
were reconstructed bit-exactly from the frozen sources. One undocumented subtlety was found:
`experiments/e45_development_grid/run.py` line ~736 takes the certified root as
`state_from_circuit(baselines["greedy"][0])`, but the baseline arms are **skipped entirely** when
the normalized circuit exceeds `MAX_BASELINE_GATES = 80`, in which case the root is the
*normalized* circuit. Any independent re-implementation that misses this branch will disagree
with the frozen `baseline_cost` on 49 of 128 sources. This belongs in
`docs/verification/cold_start_protocol.md` as a named trap.

### Gap 2 — No real QPU validation

**Verification:** `real_qpu: OPEN`; EHW is noise-*model* simulation
(`credential_audit.route = 3b_noise_model_simulation_NOT_real_hardware`); the §7.4 negative pilot
(logical compression 46.15% → **0%** after Qiskit L1 basis translation) stands.

**Upgrade (unchanged, sharpened).** The §7.4 finding *is* the experiment: test whether a
representation-aware compilation path (WCL preprocessing before transpilation) preserves the
logical gain through the basis-change gate. 3 families (BV, HaarRandom, RandomClifford) × 5–7
qubits × 2 listings × 3 seeds; IBM Quantum free tier suffices. **New support for this route:**
[108] (arXiv:2610.00669) shows that an architecture-independent lower bound plus a hardware cost
model is a publishable combination — precisely the shape of P0-1 + P1-4.

### Gap 3 — No independent cold-start reproduction

**Verification:** `external_cold_start: OPEN`. **Honest statement of what this run did and did
not do:** the full v14/v15 verifier chain was re-run successfully on this host under a *different
Python distribution* (conda-forge CPython 3.12.12 / `qiskit 2.4.1`) than the one used for the
recorded runs, and 128/128 root listings reproduced exactly. That is a **same-host reproducibility
check**, not an independent cold start; it does not close the gate. The cheapest closure remains
`Dockerfile` + a second machine/CI runner + archived SHA-256 receipts.

### Gap 4 — No external execution gate

**Verification:** `release_authority: OPEN`. **What was executed:** a standalone verifier with its
own protocol version (`qrcert/v1`) now exists (§5.2), so an external party has something concrete
to run that does not depend on the producer's verification code. Natural reviewers: the MQT group
(TUM — authors of MQT Bench [69] *and* the pass-order paper [96]) and BQSKit (LBNL) — with the
conflict-of-interest caveat that MQT now holds directly adjacent work.

### Gap 5 — Theory: withdrawn and incomplete results

Unchanged from the 2026-10-16 scan (Thm 5 incomplete; Thm 6 general refuted; Thm 8 withdrawn;
Thm 2(d) invalid; QMA-hardness withdrawn; Obs 1 general withdrawn; C1 refuted), **except that
Thm 5 now has a diagnosis, two valid restricted statements, and a data-backed replacement**:

* **Thm 5-A (valid).** Fixed matching, independent labels ⇒ `P[X ≥ EX + t] ≤ exp(−t²/(2N))`,
  `N` = number of gate slots. Proof: influence of one label ≤ 2, so `Σcᵢ² = 4N`.
* **Thm 5-B (valid).** Random matching, conditional on `M` ⇒ the same bound around `E[X|M]`.
  The unconditional form still requires a concentration for `M ↦ E[X|M]`, which §2 of the repair
  note shows is unreachable by bounded differences.
* **Thm 5-C (conjecture, evidence-backed).** `X` is asymptotically `Poisson(n(d−1)p_cancel)`;
  Bernstein tail `exp(−t²/(2(λ + t/3)))`, strictly stronger than the stated bound whenever
  `p_cancel < 1`. Evidence: dispersion index 0.976 (27 cells), implied scale `N_eff/N` =
  0.024–0.112. Proof route: Chen–Stein with a bounded-degree dependency graph over wires.
* **Consequence:** Corollary 5.1 is conservative but not wrong; under 5-C it sharpens the
  fluctuation term from `√(ln n / nd)` to `p_cancel·ln(n)/d`.

---

## 3. Full-process audit (paper writing excluded)

### 3.1 Scientific question and narrative

**Current framing.** RQ1 (listing model → outcome), RQ2 (structure of the search space across
families), RQ3 (where production compilers exceed the local peephole model). Honest, well-scoped,
and the refuted "phase transition" hypothesis is handled correctly.

**Bar assessment — updated with today's literature.**

| Deficit | Evidence | Remedy |
|---|---|---|
| **The object of study is the algorithm, not nature** | `framework.md` §"Honest framing note" item 3 | P0-1 (barrier as a circuit property) or P1-4 (hardware) |
| **The headline phenomenon is becoming consensus, not surprising** | Four 2026 papers now argue representation gates capability: [96], [99], [105], [106] | P0-2: the surprise is that all four are one phenomenon and that the classical phase-ordering literature does **not** transfer |
| **Impact scope is one sub-community** | manuscript §1.1 | P1-4 + P0-1 |
| **Abstract leads with Methods before Results** (row counts, dataset counts, experiment IDs before the 0.0000% → 7.83% contrast and the 80/80 BV optimum) | manuscript abstract | Still worth fixing; reads as an audit report rather than a discovery paper |

**One positioning change is now mandatory, not optional.** Because [105] and [106] independently
establish representation-dependence *and* [97]/[105] already deliver provable bounds, the
introduction must (i) cite all four, (ii) state that the project's contribution is the
**certified, replayable landscape** rather than the phenomenon, and (iii) explicitly claim the
axis nobody else has: **an exact per-source map with zero unclassified cells and zero replay
failures**.

### 3.2 Theory framework — which conjectures are repairable

| Conjecture / open problem | Repairability | Path |
|---|---|---|
| OP1 (CODP QMA-hard) | Low | No valid reduction; promise orientation reversed. Do not reopen. |
| OP2 (no PTAS) | Low-Medium | Multiplicative form ill-defined at zero optimum; additive/gap form only. |
| C1 (universal Phase-1 ceiling) | **Dead** | Refuted; cite as a legitimate negative result. |
| C2 (`Γ(C) = Ω(1)` for specific families) | Partially resolved | Thm 7 (artificial) + Thm 9 (natural BV, `2n/(3n+2)`) are existence proofs; the *classification* is the open, valuable part. |
| **Thm 5** (concentration) | **Repairable — executed today** | §2 Gap 5: 5-A/5-B valid, 5-C conjectured with evidence. |
| Thm 9 (BV `k+2` optimum) | **Repairable via SAT/MIP** | [110] (arXiv:2510.00649) plus Peham et al. give a global-optimality certificate route on bounded instances. Upgrades the single most citable result from "reaches `k+2`" to "reaches the proven optimum". |
| Phase-2 action-space bound `O(d/n)` | **Highest-value untested conjecture** | Would explain why Phase-2a advantage is ~3.26% on random circuits (E10) but ~20% on oracle circuits (E11). Directly testable against E10/E11/E14. |
| **NEW: complexity of Phase-2b template matching** | **Newly tractable** | [107] (Fujii, arXiv:2609.35239) supplies the exact template: NP∩BQP for commuting templates with unrestricted exponents; NP-complete for binary exponents even for CNOT-only; polynomial for commuting self-inverse; NP-complete once the total repetition count is bounded. |

### 3.3 Experimental design

**Strengths (verified).** Pre-registered H1–H5 with explicit rejection criteria; 6 optimizer
types; 3 production compilers under a fair no-coupling-map protocol; sealed E31 factorial with a
pre-registered analysis protocol; FDR correction; ITT-MI treatment of the E18 survivorship bias;
multi-seed replication E29; explicit random-shuffle control E22.

**Weaknesses (updated).**

| # | Weakness | Severity | Fix |
|---|---|---|---|
| W1 | No BQSKit and no SAT/MIP-optimal Clifford baseline | **High** | Add both; [110] additionally upgrades Thm 9 |
| W2 | External validity of the custom 15-family roster | **High** | Run the taxonomy on MQT Bench + QASMBench at matched widths |
| W3 | Scale: most family cells are n = 3–10 | Medium | Add a 20–40 qubit band for 3 families |
| W4 | Asymmetric E21 timing (34.97×) still appears in §1.5/§7.3 | Medium | Lead with 2.20×; footnote 34.97× |
| W5 | E4 single-seed vs E29 materially different stochastic inflation | Low-Medium | Already disclosed (Limitation 7) |
| W6 | Statistical power on real-circuit cells (0/5 ⇒ CP upper bound 45.1%) | Low | Already disclosed (Limitation 10) |
| W7 | `success` column non-informative | Low | Already disclosed (Known Issue 7) |
| W8 | E26 canonical fidelity not publication-grade for 201 rows | Medium | Already resolved: cite `data/v10/prepaper/e26/phase2b_full_validation_v8.csv` |
| **W9 (new)** | **The 34 bounded cells' *lower* bound was previously absent, so their reported "bounded" status could be read as unbounded below** | Medium | **Fixed today** for the horizon-3 `e44_core_v1` scope: certified interval width ≤ 5 |

### 3.4 Data and reproducibility

**Strengths.** SHA-256-pinned release chain; explicit `data/vN` version policy; replayable
certificates with witness storage; fail-closed readiness verdicts; `scripts/reproduce_all.py
--verify`; Docker reproduction environment; 15 documented Known Issues; a rigorous wave-6
rerun-reconciliation record.

**Weaknesses (corrected).**

| # | Weakness | Status |
|---|---|---|
| D1 | No archival DOI | `release/zenodo_deposit_metadata.json` is prepared; deposit at submission |
| D2 | 15 hash-drift entries in the 15,042-entry prepaper manifest | **This run surfaced a concrete instance**: the verifier currently fails on `docs/review/metric_audit_ledger_2026-08-24.csv` (§5.3) |
| D3 | No CI | Out of scope by project decision; an external runner substitutes for Gap 3 |
| D4 | ~~Four dependency files with unclear precedence~~ | **CORRECTED — already documented.** `pyproject.toml` states "Single source of truth for dependency pins is requirements.txt (transitive lock with hashes: requirements-lock.txt)"; `environment.yml` repeats it and explicitly records the 2026-08-06 de-duplication. The 2026-10-16 scan overstated this. No action needed. |
| **D5 (new)** | The 80-gate baseline-budget branch is not documented in the cold-start protocol | Add to `docs/verification/cold_start_protocol.md` (§2, Gap 1) |

### 3.5 Code engineering quality

**Strengths.** Modular `src/`; 101 test files; 85 experiment entrypoints; 61 scripts; byte-stable
certificate generation; deterministic seeds per experiment.

**Weaknesses.**

| # | Weakness | Action taken |
|---|---|---|
| C1 | No static type checking | **Fixed**: `mypy.ini` added; `python -m mypy src` runs |
| C2 | Untracked bytecode caches | Already clean (0 outside `data/`) |
| C3 | No coverage reporting | Low priority; the evidence tests are the real gate |
| C4 | `docs/analysis/` holds 3 ad-hoc probe scripts and 3 raw part-CSVs at the top level of a documentation directory | They are cited by `docs/analysis/algorithmic_complexity.md`; leaving them is the lower-risk choice |
| **C5 (new)** | **24 mypy errors in 6 files** | 1 fixed (see §5.1); 23 documented for owner triage |
| **C6 (new)** | `src/`, `scripts/`, `tests/` are hash-bound in `release/prepaper_*manifest.json` | Every source edit therefore creates release-manifest drift; §5.1 records exactly which edit was made and why it was judged safe |

### 3.6 External validation paths

| Path | Status | Minimal viable next step |
|---|---|---|
| Real hardware | OPEN | Gap 2 plan: representation-aware compilation through basis translation |
| Independent cold start | OPEN (same-host re-verification done, §2 Gap 3) | Docker + second machine |
| External review | OPEN — **improved today** | Ship `scripts/verify_certificate_qrcert_v1.py` (`qrcert/v1`) as the review target; MQT (TUM) or BQSKit (LBNL) |
| Archival publication | Not started | `release/zenodo_deposit_metadata.json` is prepared |

### 3.7 Publication strategy

| Finding | Required upgrade | Target |
|---|---|---|
| Listing-model sensitivity (0.0000% vs 7.83%) | hardware consequence, or unification with the four 2026 representation papers | **PRX Quantum**; *Nature Communications* only with P0-2 |
| 15-family stratification (6 classes) | external benchmark replication (W2) | *npj QI* / *PRX Quantum* |
| Phase-2b BV `k+2` optimum (80/80) | **global-optimality certificate** | *Quantum* — most citable single result |
| Certified landscape 128/128 + E46 + **certified intervals** | full-rule scope; wire-consecutive windows | *Quantum* (tools) |
| Ceiling-aware optimizer | symmetric timing as headline + BQSKit/MQT comparison | TQE |
| Certified peephole barrier theorem | new theorem (P0-1) | **Nature Physics / Nature Communications** |
| Unified representation-ordering account | new framing + experiment (P0-2) | **PRX Quantum / Nature Communications** |
| Rule-library completeness via EqSat/Knuth–Bendix | new experiment (P0-3) | PRX Quantum / Quantum |
| **Phase-2b template complexity** | new theory (P1-6) | QIP / Quantum (theory) |

---

## 4. Literature and frontier scan (executed 2026-10-17)

### 4.1 What was actually executed

| Tool / channel | Status | Output |
|---|---|---|
| arXiv API (`export.arxiv.org/api/query`), phrase-quoted queries | **Working after retry** | 20 queries. First pass: 10 queries succeeded, 12 hit HTTP 429 / timeouts. Retry with 8 s backoff: all 12 succeeded. **227 records total, 198 unique.** |
| GitHub REST API | **Working (unauthenticated)** | 13 repository lookups + repository searches; 3 assumed orgs returned 404 (see §4.5) |
| Built-in web search | Working, low yield | 1 query; results were not domain-specific enough to use. **No claim in this report depends on it.** |
| Tavily skill | **Unavailable** | `tavily` module not installed, no `TAVILY_API_KEY`. Not used. |
| Exa skill (`web-search-exa`) | **Unavailable** | No `mcp.exa.ai` server in `~/.workbuddy-ai/mcp.json` (file absent). Not used. |
| `multi-search-engine` | Not used | Engine-endpoint recipe, not an API; arXiv + GitHub gave date-sorted primary sources |
| `arxiv-reader` | Partial | Abstracts pulled in full for the 8 most relevant papers; the LaTeX-parsing agent pipeline was not run |
| `citation-manager` | Used as a coverage audit | §4.3 and `docs/references/reference_additions_2026-10-17.md` |
| `github-trending-cn` | Substituted | Domain-targeted GitHub API queries are more informative here than a global trending feed |

**Disclosure.** No claim below is derived from an unavailable tool.

### 4.2 The competitive picture changed again in the last 24 hours

Three papers not present in the 2026-10-16 scan are now verified. Together with the four papers
already known, they re-shape the novelty position.

**(A) `arXiv:2609.29210` — "Representation-Dependent Recoverability in Quantum Compilation"**
(Yang, Li, Deng; 2026-09-24). Formalises how scheduling, gate synthesis and randomised compiling
disperse high-level phase structure, and proves a two-channel lower bound
`Ā_p + (2p−1)S ≥ (1−δ)m log₂ K_ε − h₂(δ)` for any p-pass compiler correct on every valid stream.
They also measure, under a **preregistered protocol**, a per-generator toll matching
`log₂ C(m,k)/k`, and show a materialise-first pipeline costs orders of magnitude more logical T
states than a semantics-first one.

*Relation:* the same *conceptual* claim as this project — representation determines what a
downstream compiler can do — but the object is **information-theoretic recoverability of phase
data across a compilation boundary**, not the **combinatorial action space of a local rewriter**.
*Why it matters most:* they are already doing the "provable bound" style that Direction P0-1
targets, in a different coordinate system. The field is moving toward provable representation
bounds. P0-1 is timely **and contested**.

**(B) `arXiv:2610.06142` — "When Equivalent Quantum Circuits Lose Synthesis Choices"**
(Ye, Liang, Khan; 2026-10-05). Introduces *synthesis availability*: representation changes remove
high-level operations, so a requested synthesis method has no effect — **360/360** delivered
conditions after a direct OpenQASM 3 round trip. In an MQT pipeline, an OpenQASM 2 interchange
raises the two-qubit gate count by **37.2%** on an 8-qubit Grover circuit. Their fix
(`Verified`) restores requested synthesis in 830/830 recovery runs.

*Relation:* a third independent demonstration that representation choice gates optimizer
capability, with a *measured gate-count penalty*. Very close to this project's framing, different
mechanism (loss of retained high-level structure rather than loss of listing adjacency).

**(C) `arXiv:2609.35239` — "Computational Complexity of Clifford Template Compilation"**
(Fujii; 2026-09-28). Complexity landscape for choosing template repetition numbers: NP∩BQP for
commuting templates with unrestricted integer exponents; NP-complete for `{0,1}` exponents even
for CNOT-only exactly commuting operations; polynomial for commuting self-inverse actions;
NP-complete once the total repetition count is bounded.

*Relation:* the missing complexity backdrop for this project's **Phase-2b template matching**.
This is a new, cheap, and well-posed theory direction (P1-6).

**(D) `arXiv:2610.00669` — "Quantum Circuit Pruning: From NISQ Architectures to Fault-Tolerant
Operations"** (Escofet et al.; 2026-09-30). An architecture-independent lower bound on the
fidelity cost of omitting a two-qubit gate, compared against a hardware-specific routing model;
up to 48.6% gate reduction and 47.7% fidelity improvement; analytical characterisation of the
pruning boundary.

*Relation:* evidence that "lower bound + hardware consequence" is a publishable combination —
exactly the P0-1 + P1-4 shape.

**(E) Previously identified, still the closest threats.** [96] pass order (MQT, 2026-09-24);
[97] exactness barrier for ZX (2026-08-24); [99] structured-vs-unrolled (2026-09-14);
[98] AlchemQ certificate protocol with a Heron r2 pilot (2026-08-24); [100] the LLVM per-pass
study (2026-06-30); [101] Knuth–Bendix rule augmentation (2026-10-01); [102] PhasePoly (2025-06-25).

**Net effect on positioning.** "Representation matters" is now argued by four independent 2026
papers and is becoming consensus. The project must lead with the **certified landscape** — the
exact, replayable, classification-complete action-space map with zero unclassified cells and zero
replay failures — because none of the competitors has one.

### 4.3 Reference coverage

`docs/references/unified_references.md` v2.2 holds 94 numbered entries ([74] and [81] are removed
placeholders). Genuinely missing, now verified and catalogued in
`docs/references/reference_additions_2026-10-17.md` as [95]–[112]:

* **Novelty pressure:** [95] pass order, [99] unrolling, [105] representation-dependent
  recoverability, [106] synthesis availability
* **Methodological templates:** [97] exactness barrier, [100] LLVM per-pass, [101] Knuth–Bendix,
  [103] EqSat-vs-stochastic, [98] AlchemQ, [104] assurance contracts, [107] template complexity
* **Comparators/explainers:** [102] PhasePoly, [96] graph colouring, [108] pruning, [109] LLM
  circuits, [110] MIP optimal circuits
* **Tools:** [111] BQSKit, [112] tzap

The addendum also carries a **6-item defect register** for the catalogue itself (§P/§L
contradictions on [76]/[77]/[20], non-contiguous numbering, and two stale `CQCL/tket` URLs in
path-bound files). It is deliberately **not** merged, because the catalogue is a path-bound entry
of `release/prepaper_release_manifest.json`; the merge instruction is in §C of that file.

### 4.4 Frontier methodology gaps

1. **Equality saturation** as the natural formalisation of the Phase-1/Phase-2 hierarchy.
2. **Automated rule-set completion** (Knuth–Bendix) as the direct attack on "the trichotomy is a
   library artefact".
3. **Phase-polynomial / cross-block representations** — [102] beats this project on exactly the
   Class IIIb families, by changing the representation. Must be engaged.
4. **Certificate-protocol interoperability** — **partially executed today** (§5.2).
5. **Cumulative-prefix measurement design** — the [100] design applied to the representation ×
   pass-order factorial.
6. **Average-case complexity** — now with a concrete proof plan (Chen–Stein / Poisson; §2 Gap 5).

### 4.5 Open-source ecosystem (GitHub API, 2026-10-17)

| Repository | Stars | Last push | Note |
|---|---|---|---|
| `Qiskit/qiskit` | 7,895 | 2026-10-16 | Primary comparator (E20) |
| `Quantinuum/tket` | 318 | 2026-10-08 | Repo is under `Quantinuum`, **not** `CQCL` — two stale URLs recorded in the defect register |
| `zxcalc/pyzx` | 551 | 2026-10-16 | E36 third-artifact panel |
| `BQSKit/bqskit` | 188 | 2026-08-11 | **Still not benchmarked — W1** |
| `qqq-wisc/tzap` | 48 | 2026-10-16 | New SOTA comparator and novelty risk |
| `DVLab-NTU/qsyn` | 198 | 2026-10-05 | C++ synthesis/optimisation/verification |
| `boschmitt/tweedledum` | 109 | 2026-07-16 | C++ analysis/compilation/synthesis |
| `PennyLaneAI/catalyst` | 239 | 2026-10-16 | JIT compiler for hybrid programs |
| `overshiki/SymbolicCircuit.jl` | 11 | 2026-04-17 | Term rewriting + EqSat for quantum |
| `choi95/awesome-quantum-compiler` | 175 | 2026-09-27 | Coverage checklist |
| `softwareQinc/quartz`, `gwwatkin/quanto`, `epiqc/voqc` | — | — | **404 under the assumed orgs.** `quantum-compiler/quartz-artifact` (9★, 2024-03-02) is the PLDI'22 artifact repo. Live homes not resolved (API rate limit); resolve before citing URLs. |

---

## 5. Execution log — what this run changed in the repository

### 5.1 Source edit (1 file, behaviour-neutral, verified)

`src/optimisation/certified_landscape.py`, function `_minimax_barrier_compact` (the layered
minimax barrier traversal used by the certified landscape):

* the local `previous` was bound first to `next_level.get(child_hash)` (type
  `tuple[LandscapeState, int] | None`) and then, in the immediate-return branch, to
  `parents[winning_key][0]` (type `tuple[int, str]`);
* the local `path` was defined twice in the same scope.

Both were **runtime-benign** (the clobbering branch always returns), but they are exactly the kind
of latent hazard that becomes a defect under a later edit, and mypy flags them. The fix renames
the locals to `prior_entry`, `immediate_path` and `parent_key`. It cannot change behaviour.

**Verification performed after the edit:**

| Check | Result |
|---|---|
| `pytest tests/test_v13_certified_landscape.py tests/test_e46_window_landscape.py -q` | 15 passed |
| `scripts/verify_v15_landscape_integration.py` | exit 0, `PASS` |
| `scripts/verify_v15_readiness_verdict.py` | exit 0, `PASS` |
| `scripts/verify_e46_window_landscape.py` | exit 0, `PASS`, 242 witnesses replayed |
| `scripts/verify_v14_readiness_verdict.py` | exit 0, `PASS` |
| `scripts/verify_certificate_qrcert_v1.py` (new) | exit 0, 20/20, `CERTIFIED_CONSISTENT` |
| `git status --porcelain data/ release/` | empty (frozen zones untouched) |

**Not fixed, deliberately.** `src/`, `scripts/` and `tests/` are path-bound in
`release/prepaper_*manifest.json`, so every source edit creates release-manifest drift. The edit
above was made because it is provably behaviour-neutral and closes a real hazard; the remaining
23 mypy findings are recorded rather than applied, because each would need its own drift entry and
several (e.g. `quartz_rule_import.py:141` returning `tuple[float, float, str]` where
`tuple[int, int, str]` is declared) could change observable output.

### 5.2 New verifier: `qrcert/v1`

`scripts/verify_certificate_qrcert_v1.py` re-derives the published v15 numbers from the frozen
artifacts and **imports nothing from `scripts/verify_*`**. It checks 20 properties: every quoted
receipt SHA-256, the v14 verdict hash, the classification CSV hash, the tier histogram, escape /
local-optimum / exact-best-cost counts, witness-replay failure count, the window row total, the
global escape row count, and all four per-configuration window/escape/local-optimum/
inputs-with-escape counts.

Result: **20/20 PASS — `CERTIFIED_CONSISTENT`**, certificate written to
`docs/review/science_boost/2026-10-17_certificate_verification/v15_certificate.json`.

This is the first concrete step on P1-5's certificate-interoperability item and gives an external
reviewer a single self-contained command.

### 5.3 Pre-existing release-chain defect surfaced

```
$ python scripts/verify_prepaper_release_manifest.py
RuntimeError: byte/hash mismatch: docs/review/metric_audit_ledger_2026-08-24.csv
```

This **pre-dates this run** (the file is unmodified by it) and is one instance of the
"15 hash-drift entries" already recorded in the 2026-10-16 scan. It matters because
`docs/PROJECT_STATUS.md` advertises the release chain as hash-pinned; a failing verifier should
either be dispositioned or the claim should be qualified. Recommended disposition: add the entry
to the existing drift register (`release/prepaper_external_blockers.csv` /
`docs/review/prepaper_final_audit_2026-08-10.md`) with the reason and a re-hash decision.

### 5.4 New evidence packages

| Path | Contents |
|---|---|
| `docs/review/science_boost/2026-10-17_certified_lower_bounds/` | `certified_lower_bounds.csv` (128 rows), `summary.json`, `protocol.json` |
| `docs/review/science_boost/2026-10-17_thm5_tail_test/` | `thm5_tail_test.csv` (27 cells), `summary.json`, `protocol.json` |
| `docs/review/science_boost/2026-10-17_certificate_verification/` | `v15_certificate.json` |
| `docs/theory/thm5_concentration_repair_2026-10-17.md` | Theory note (new file; `framework.md`/`formal_results.md` untouched) |
| `docs/references/reference_additions_2026-10-17.md` | 18 references + defect register |
| `scripts/derive_v15_certified_lower_bounds.py` | Generator, `V15_CERTIFIED_LOWER_BOUND_V1` |
| `scripts/test_thm5_tail_necessary_condition.py` | Generator, `THM5_TAIL_NECESSARY_CONDITION_TEST_V1` |
| `scripts/verify_certificate_qrcert_v1.py` | Independent verifier, `qrcert/v1` |
| `mypy.ini` | Static-typing gate for `src/` |

---

## 6. Prioritised innovation directions

Each direction: **essence and difference → feasibility → required new evidence → expected impact →
submission tier.**

### P0-1. Certified Peephole Barrier Theorem ★★★★★

**Essence.** The project's ceiling is currently a statement about *tools* (no tested tool reduces
QFT/GHZ/SurfaceCode). The top-tier version is a statement about *circuits*: for a given circuit and
a certified class of exactly-preserving local rewrites, a **per-instance computable lower bound** on
the residual gate count, attained (or nearly) by the observed optimizers.

**Difference from existing work — and the new pressure.** [97] already does this for ZX
optimization of synthesized Clifford+T circuits (barrier = denominator exponent of the ring
element). [105] already proves an entropy lower bound for representation-dependent recoverability.
**So P0-1 is no longer a novel *style* — it is a novel *object*: the barrier for a certified local
rewrite class on a listing.** That is still unclaimed, and the project has the two ingredients
nobody else has: a 1,474-rule source-pinned library and a classification-complete certified
landscape to validate the bound against.

**What today's evidence adds (this is the useful part).**

1. The *trivial* certified barrier is `baseline − H·D` with `D = 2`, i.e. 6 gates over the frozen
   horizon — too weak to close the 34 cells (width 4–5 remains).
2. The structural lever is now visible: **138 of the 149 core rules (92.6%) cannot reduce the gate
   count** (84 neutral, 54 increasing), and only one rule reduces by 2. A barrier functional
   built from the *invariants of the non-reducing majority* is therefore the right construction —
   the reducing 7.4% cannot, on its own, generate a large drop.
3. [100] supplies a second template: a **search-free additive upper bound on phase-interference
   loss** (46.35% for LLVM `-O3`).

**Feasibility: Medium-High.** Concrete route: (i) restrict to the certified exactly-preserving
class; (ii) define a valuation on the gate-sequence algebra (candidate: a weight on the phase
polynomial plus a commutation-graph invariant) and prove invariance under the certified class;
(iii) compute it on all 128 sources and compare against the 94 exact best costs and the 34
certified intervals; (iv) falsify: find an instance where a certified rewrite beats the barrier —
that would be a publishable negative result in its own right.

**Required new evidence.** Formal definition + invariance proof; per-instance barrier values on the
128 sources (new dated file); a comparison table barrier vs exact best cost vs the 34 intervals;
and — because the trivial bound already exists — an explicit statement of **how much the barrier
improves on `baseline − 6`**, which is now the honest yardstick.

**Impact: Very High.** This is the only change that rewrites the framework's own framing sentence,
and it subsumes Gap 1.

**Tier: Nature Physics / Nature Communications / PRX Quantum** (arguably *Nature Physics* with a
hardware consequence).

### P0-2. Unified account of the four representation-ordering results ★★★★☆

**Essence.** Four independent 2026 results — pass order [96], unrolling [99], recoverability [105],
synthesis availability [106] — are the same phenomenon seen from four sides: the reachable action
space of a downstream compiler is determined by the (representation, algorithm) pair. This project
already owns the certified tooling to make the claim rigorous rather than anecdotal, and its E22
shuffle control (`p = 6.8e-15`) already proves the listing-ordering effect is causal.

**The testable unification claim.** Listing ordering and pass ordering act on the same underlying
adjacency structure; the classical phase-ordering literature ([100]) transfers only partially;
and the quantum case has an extra degree of freedom the classical case lacks — **a circuit can be
relisted without changing its semantics; a program cannot be re-ordered without changing it.**
That last clause is the genuinely new theoretical content.

**Feasibility: High.** The representation axis is implemented; the pass axis is Qiskit's
`PassManager`; the design is [100]'s cumulative-prefix decomposition; the 128-source panel is the
controlled input set.

**Required new evidence.** Representation × pass-order factorial
({LBL, WCL, RANDOM_TOPOLOGICAL} × cumulative prefixes); a non-monotonicity statistic comparable
to LLVM's 6.6–9.7%; a back-loadedness statistic comparable to 84.8%; and a statement of which
pass-order effects are *absorbed* by relisting and which are not.

**Impact: High.** Converts "a data-structure choice matters" into "representation choice is the
missing coordinate in the phase-ordering problem", and pre-empts the single most likely novelty
objection.

**Tier: PRX Quantum / Nature Communications.**

### P0-3. Rule-library completeness attack (EqSat + Knuth–Bendix) ★★★★☆

**Essence.** The project's own manuscript already concedes that the "~0% band was partly
template-library artifact" (E26 moves IQP 0.5% → 92.0%). So every Class IIIa/IIIb classification
is conditional on the library. Making the library *closed under a completion procedure* removes
the free parameter. Today's new fact sharpens the stakes: 92.6% of the certified core rules are
non-reducing, so a completion procedure has a lot of headroom to add reducing rules — which is
exactly how a ceiling could break.

**Feasibility: Medium.** `egg`/`egglog` exist; the work is encoding the rule set, saturating the
128-source panel, and comparing reachable minima against the certified landscape — the ground-truth
labels no EqSat paper has had.

**Required new evidence.** Saturation with and without Knuth–Bendix augmentation; a per-family
table of certified optimum vs EqSat reachable minimum vs Phase-2b; a redundancy/derivability
analysis of the 1,474 rules; and the honest negative control where EqSat and stochastic search tie.

**Impact: High.** Either it breaks a ceiling (headline, and honest) or it closes the strongest
criticism of the trichotomy. Both publishable.

**Tier: PRX Quantum / Quantum.**

### P1-4. Real-QPU representation sensitivity ★★★☆☆

**Essence.** The 7.83% vs 0.0000% result is simulator-only. §7.4 already reports the crucial
negative: BV logical compression 46.15% → **0%** after Qiskit L1 basis translation. The sharper
question: **can a representation-aware compilation path preserve the logical gain through the
basis-change gate?**

**Feasibility: High.** IBM Quantum free tier; 3 families × 5–7 qubits × 2 listings × 3 seeds.

**Required new evidence.** Raw fidelity/Hellinger/TVD for the listing pairs, pre-registered against
the §7.4 noise-model predictions; a physical-compression measurement *after* basis translation;
readout mitigation and a drift-controlled calibration snapshot per job.

**Impact: Medium-High.** Closes the most-cited gap; the negative outcome is scientifically
interesting too — and [108] shows the lower-bound + hardware shape is publishable.

**Tier: npj QI (with P0-2), or PRX Quantum if physical-compression survival is demonstrated.**

### P1-5. Landscape completion + certificate interop ★★★☆☆ — **partially executed**

**Done today:** certified lower bounds for all 128 sources; an independent `qrcert/v1` verifier
(20/20); exact reproduction of all 128 root listings.

**Remaining:** (i) close or further narrow the 34 cells via a stronger admissible potential
(P0-1's object); (ii) extend to full rule scope (1,474 rules) and wire-consecutive window
profiles; (iii) publish the certificate schema and cross-verify with AlchemQ's Apache-2.0 verifier.

**Tier: Quantum (tools) / npj QI.**

### P1-6. NEW — Complexity classification of Phase-2b template matching ★★★☆☆

**Essence.** Phase-2b is the project's strongest empirical result (80/80 BV at the `k+2` optimum)
and its least theorised: the complexity of template matching in the project's own setting has
never been pinned. [107] now provides the exact template — NP∩BQP with unrestricted exponents;
NP-complete for `{0,1}` exponents even for CNOT-only; polynomial for commuting self-inverse
actions; NP-complete under a bounded total repetition count.

**Feasibility: Medium.** The question is well-posed: for the project's bounded-window template
matcher over the `e44_core_v1` scope, what is the complexity of deciding whether a target
reduction is achievable? The bounded repetition count case is the most relevant and [107] says it
is NP-complete — a clean, citable theorem-shaped statement about the project's own optimizer.

**Required new evidence.** A reduction from a known NP-complete problem to the project's
bounded-template-repetition decision problem; an explicit statement of the restricted cases that
remain polynomial (matching the certified engine's observed tractability on the 128-source panel);
and a falsifier for the claimed correspondence.

**Impact: Medium.** It gives Phase-2b a complexity identity rather than a benchmark record, and it
connects the project to the complexity-of-compilation literature (Janzing et al. [1], Fujii [107]).

**Tier: QIP / Quantum (theory).**

### P2-7. Average-case peephole complexity ★★★☆☆ (upgraded from ★★☆☆☆)

**Essence.** The "phase transition" hypothesis is dead; the admissible reformulation is
representation-conditioned average-case behaviour. **Today's evidence makes the proof plan
concrete rather than speculative:** X behaves as a Poisson count (dispersion index 0.976 over 27
cells), so the natural theorem is a Chen–Stein Poisson approximation over a bounded-degree wire
dependency graph — not a repaired McDiarmid argument.

**Required new evidence.** A valid Poisson-approximation bound with an explicitly constructed
dependency graph; validation against E30; a companion lower bound (P0-1 supplies it); and a
higher-trial replication (≥ 10⁴ trials at three cells) to resolve the far tail that the current
500 trials/cell cannot.

**Impact: Medium.** Repairs the project's one genuinely repairable theory defect and supplies the
upper companion to P0-1.

**Tier: QIP / Quantum (theory).**

### P2-6. Neural/LLM-guided certified search ★★☆☆☆

Unchanged. The novel part is *guarantee preservation*: use the learned prior for move ordering
only, keeping the exhaustive/IDA* frontier intact. Training labels exist (94 exact cells + 76,236
window searches). **Tier: TQE / Quantum (software).**

---

## 7. Next 30 days — action checklist

### Week 1 (Days 1–7): theory route and novelty defence

1. **[Theory, P0-1]** Write a 3–4 page formal sketch of the barrier functional. Start from the new
   structural fact that 92.6% of certified core rules are non-reducing, and from [97]/[100] as
   structural templates. Output: `docs/theory/peephole_barrier_sketch_<date>.md`. **Do not edit
   `framework.md` or `formal_results.md`.**
2. **[Theory, P2-7]** Turn `docs/theory/thm5_concentration_repair_2026-10-17.md` into a proof
   attempt for Thm 5-C (Chen–Stein, bounded-degree wire dependency graph). Run the ≥ 10⁴-trial
   replication at three cells to resolve the tail.
3. **[Theory, cheap win]** Attempt global optimality for the BV family via SAT or MIP
   ([110], arXiv:2510.00649). A certificate at `n ≤ 6` already upgrades the headline.
4. **[Theory, new]** Draft the P1-6 complexity statement for bounded-repetition template matching,
   anchored on [107].
5. **[Literature]** Apply `docs/references/reference_additions_2026-10-17.md` §C: merge [95]–[112]
   into `unified_references.md`, fix the four §B consistency defects, and record **one** explicit
   drift-disposition entry.
6. **[Docs]** Add the 80-gate baseline-budget branch (§2, Gap 1) and the `qrcert/v1` command to
   `docs/verification/cold_start_protocol.md`.
7. **[Release hygiene]** Disposition the failing prepaper manifest entry
   (`docs/review/metric_audit_ledger_2026-08-24.csv`, §5.3).

### Week 2 (Days 8–14): external validation and comparators

8. **[Gap 3]** Build and test the Docker reproduction container on a second machine; archive the
   SHA-256 receipts. **Cheapest of the four open gates.**
9. **[W1]** Add BQSKit to the SOTA panel on all 15 families at canonical sizes.
10. **[W1]** Add `qqq-wisc/tzap`; pin the commit before benchmarking.
11. **[Gap 2]** Register an IBM Quantum account; 5-qubit BV + HaarRandom pilot, WCL and LBL,
    10 circuits each, pre-registered against the §7.4 predictions.
12. **[W2]** Run the taxonomy on MQT Bench + QASMBench at matched widths.
13. **[C5]** Triage the remaining 23 mypy findings; apply only the behaviour-preserving ones, each
    with its own drift entry.

### Week 3 (Days 15–21): experiments

14. **[P0-2]** Build the cumulative-prefix pass-order panel × {LBL, WCL, RANDOM_TOPOLOGICAL} on the
    fixed 128-source set; report non-monotonicity and back-loadedness in the [100] format.
15. **[P0-3]** Run `egglog` saturation over the rule library on a 16-cell subset, with and without
    Knuth–Bendix augmentation; compare against the certified optima.
16. **[P0-1]** Compute the candidate barrier functional on all 128 sources and report the
    improvement over `baseline − 6`.
17. **[Gap 2]** If the pilot succeeds, expand to 3 families × 50 circuits × 2 listings with
    post-basis-translation physical-compression measurement.

### Week 4 (Days 22–30): synthesis and decisions

18. **[Synthesis]** Compile the representation × pass-order results into a draft section outline.
19. **[Synthesis]** Compile barrier values + certified intervals + the 94 exact optima into one
    table.
20. **[Synthesis]** Write a dated findings summary and the revised venue ladder.
21. **[Decision]** Choose the top-tier path: **P0-1 + P1-4** (theorem + hardware) toward *Nature
    Physics*/*Nature Communications*, versus **P0-2 + P0-3** toward *PRX Quantum*. Decide C3
    (`C3_title_and_positioning = USER_DECISION_PENDING`) in the same session.
22. **[Positioning]** Rewrite the abstract ordering (Results before Methods) as an *author note*,
    not as manuscript text.

---

## 8. Structural cleanup

### 8.1 Executed

| Action | Detail | Safety |
|---|---|---|
| Removed 3 empty directories | `docs/review/wave2`, `docs/review/wave3`, `analysis/figures/v14_extension/source_data`. All three contained zero files (verified with `ls -A` before removal). | No file deleted; `rmdir` only succeeds on empty directories |
| Added `mypy.ini` | New file; enables `python -m mypy src` as a repeatable gate | New file only |
| Added 3 dated evidence directories + 3 generator/verifier scripts + 2 docs | See §5.4 | New files only |

### 8.2 Deliberately not done, with reasons

| Considered | Decision | Reason |
|---|---|---|
| Merge [95]–[112] into `unified_references.md` | **Blocked** | The catalogue is path-bound in `release/prepaper_release_manifest.json`; merging creates release drift. Delivered as an additive companion with a merge instruction instead. |
| Fix the stale `CQCL/tket` URLs | **Blocked** | Both target files are path-bound in `release/prepaper_v12_capsule_inner_manifest.json`. Recorded in the defect register instead. |
| Apply the remaining 23 mypy fixes | **Deferred to the owner** | Each would need its own drift entry, and at least one (`quartz_rule_import.py:141`, `tuple[float, float, str]` vs `tuple[int, int, str]`) could change observable output. |
| Delete superseded theory docs (`phase2_lower_bound_strengthening.md`, `nontrivial_upgrades.md`, `QMA_hardness_draft.md`, `universal_law_assessment.md`) | **Declined** | The project's scientific discipline is to preserve *why* a route failed. `docs/theory/README.md` already classifies all ten theory documents as active/superseded/withdrawn/path-bound, which solves the readability problem without destroying the record. Two of them are also path-bound. |
| Delete `data/v14/e45_exact_smoke*`, `e45_idastar_escape_smoke` | **Declined** | Inside the frozen `data/` zone. |
| Consolidate the two `metric_audit_resolution` files / six `e31_*_limitation` notes | **Declined** | Hash-bound dated audit records; consolidation changes evidence semantics. |
| Move `docs/analysis/_alg_complexity_*.py` / `part*.csv` | **Declined** | Cited by `docs/analysis/algorithmic_complexity.md`; relocating requires editing that document. |
| Remove `.pytest_cache/` / `.mypy_cache/` | **Declined** | Standard tooling caches, already git-ignored; removing them only slows the next run. |

### 8.3 Repository-shape findings

* **0 duplicate-content files** across `docs/`, `analysis/`, `scripts/`, `tests/`, `src/`
  (verified by SHA-256 grouping, excluding `archive/`).
* **0 `__pycache__` / `*.pyc`** outside `data/`.
* No `*.partial.*`, `*.tmp`, `*.bak` leftovers.
* The only structural debt remaining is *semantic*, not structural: the frozen-chain drift items
  in §5.3 and §8.2, all of which need owner decisions rather than deletion.

---

## Appendix A — Files read to establish the baseline (2026-10-17)

| Path | Purpose |
|---|---|
| `README.md` | Repository-level evidence snapshot and current boundary |
| `docs/PROJECT_STATUS.md` (2026-10-11) | Optimisation status, closed/open register |
| `docs/EXPERIMENT_HISTORY.md` | E1–E30, v12–v15 history and superseded interpretations |
| `docs/manuscript/manuscript.md` (read-only) | Contributions, RQ framing, limitations |
| `docs/theory/framework.md` v5.4.2 | Definitions D1–D12, honest framing note, complexity classification |
| `docs/theory/formal_results.md` | Thm 5 statement + status, Thm 9 Appendix B, summary table |
| `data/DATA_CANONICAL.md` v2.4.0 | Canonical register, version policy, 15 Known Issues |
| `docs/references/unified_references.md` v2.2 | 94-entry catalogue (coverage audit target) |
| `release/v15_readiness_verdict.json` | Authoritative open/closed gate values |
| `release/v14_readiness_verdict.json` | Inherited boundary + hash cross-check |
| `data/v15/e45_landscape_integration/{classification_complete.csv,receipt.json,protocol.json}` | 128-cell classification (re-derived) |
| `data/v15/e46_window_landscape/{window_results.csv,receipt.json,protocol.json}` | 76,236 window rows (re-derived) |
| `data/v14/e45_full_development/{protocol.json,normalization_manifest.csv,qasm/}` | Frozen root listings (reconstructed) |
| `data/v13/e43_quartz_rule_import/generation_a/rule_library.json` | 1,488 rules (1,474 Quartz + 14 auxiliary) |
| `data/v13/e44_certified_landscape_oracle/protocol.json` | Rule scope `e44_core_v1` definition |
| `data/v10/e30/e30_thm1a_wcl_results.csv` | 13,500 trials with per-trial `a_adj_raw` |
| `scripts/verify_prepaper_release_manifest.py`, `src/optimisation/certified_landscape.py`, `experiments/e45_development_grid/run.py` | Verifier behaviour, admissible bound, root-state construction |
| `release/prepaper_*manifest.json` (grep) | Determined which files are hash-bound |

## Appendix B — Search log (2026-10-17)

**arXiv API**, phrase-quoted `all:"..."` queries, `sortBy=submittedDate`, `max_results=15`.
20 queries. First pass 10/20 succeeded (12 hit HTTP 429 / read timeouts — arXiv rate limiting);
retry pass with 8 s backoff and 5 s inter-query delay: 12/12 succeeded.
**227 records retrieved, 198 unique.**

| Query | Hits (pass 1 + pass 2) |
|---|---|
| `all:"peephole" AND all:"quantum"` | 0 + 9 |
| `all:"quantum circuit" AND all:"optimization pass"` | 0 + 14 |
| `all:"equality saturation" AND all:"circuit"` | 0 + 4 |
| `all:"ZX-calculus" AND all:"optimization"` | 0 + 15 |
| `all:"superoptimization" AND all:"quantum"` | 0 + 1 |
| `all:"quantum circuit" AND all:"rewrite" AND all:"rule"` | 0 + 15 |
| `all:"quantum compiler" AND all:"representation"` | 0 + 15 |
| `all:"quantum circuit" AND all:"landscape" AND all:"search"` | 0 + 15 |
| `all:"quantum circuit" AND all:"large language model"` | 0 + 15 |
| `all:"quantum circuit" AND all:"reinforcement learning" AND all:"compilation"` | 0 + 15 |
| `all:"quantum circuit" AND all:"certified" AND all:"optimal"` | 0 + 15 |
| `all:"quantum circuit" AND all:"lower bound" AND all:"gate count"` | 0 + 11 |
| `all:"quantum circuit" AND all:"phase polynomial"` | 10 + — |
| `all:"quantum circuit" AND all:"hardware-aware" AND all:"compilation"` | 15 + — |
| `all:"circuit optimization" AND all:"order" AND all:"pass"` | 3 + — |
| `all:"quantum circuit" AND all:"benchmark" AND all:"compiler"` | 15 + — |
| `all:"quantum circuit" AND all:"T-count" AND all:"barrier"` | 0 + — |
| `all:"quantum circuit" AND all:"noise" AND all:"optimization" AND all:"hardware"` | 15 + — |
| `all:"gate cancellation" AND all:"quantum"` | 10 + — |
| `all:"quantum" AND all:"canonical form" AND all:"clifford"` | 15 + — |

**GitHub REST API** (unauthenticated this run — the credential-store path was not needed and the
rate limit was reached): 13 repository lookups; 3 assumed orgs returned 404; 5 repository-search
queries. Results in §4.5. No token value was printed or written.

**Built-in web search**: 1 query, low yield; not relied upon.

**Not available**: Tavily (module and `TAVILY_API_KEY` both absent), Exa (no
`~/.workbuddy-ai/mcp.json`).

---

*End of innovation scan, 2026-10-17. Supersedes `2026-10-16_innovation_scan.md`. `data/` and
`release/` were not modified; `docs/manuscript/` was not written to; the only source edit is the
behaviour-neutral rename documented in §5.1, verified by 15 tests and 5 verifiers.*
