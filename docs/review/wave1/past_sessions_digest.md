# Past Sessions Digest — Multi-Agent Optimization History (Archive Worker)

**Purpose**: Digest of 14 exported session logs (~25 MB, 532,916 lines total) recording the
multi-agent optimization waves that brought Q-research to its current state. Produced for the
publication-readiness wave-1 review. Source copies live in `_agent_work/past_sessions/`
(originals on `D:\Desktop\` were never modified).

**Method**: Non-linear digestion — keyword distribution mapping (`ceiling`, `Phase-2b`, `E18`,
`manifest`, `TODO`, `缺口`, `失败`, `过时`), user-turn agenda extraction, final-summary reads, and
targeted deep reads at grep anchors. All quantitative claims below were cross-checked against the
current repo state (git log, `release/release_manifest.json`, `data/`, `docs/manuscript/manuscript.md`,
`docs/results/analysis_summary.md`). Coverage caveat: tool-call dumps and code blocks inside the
logs were skimmed, not read linearly; narrative conclusions were verified at anchor points.
Concurrency note: repo-state checks ran 2026-07-20 ~23:00–23:15 CST while other wave-1 workers were
actively editing the tree (manifest, CI, E18 derived-file moves, `data/v8/`); open items O1–O13 are
stated as of that verification window and may already be under repair by their assigned owners.

---

## 1. Session inventory and chronology

| Alias | File (in `_agent_work/past_sessions/`) | Tool / dates | Size | Role in the arc |
|---|---|---|---|---|
| S1 | `session-ses_0bbe.md` | opencode, 07-09 → 07-11 | 295 KB | "按优化计划全面完善项目至最终版" — executes P0/P1 backlog (T13/T15/T17/T19) |
| S2 | `session-ses_0af4.md` | opencode, 07-11 → 07-14 | 299 KB | Literature-search retry; GitHub release prep (repo naming, push, CONTRIBUTORS, cleanup, README de-targeting) |
| S3 | `session-ses_0ae7.md` | opencode, 07-11 → 07-19/20 | 444 KB | Skill/rtk config; research-lifecycle skill; commits & pushes `9d47a75` |
| S4 | `session-ses_0803.md` | opencode, 07-20 21:47 → 22:00+ | 638 KB | Caveman config; embeds K1 content; final GitHub sync; pushes `d6f90a0` |
| K1 | `kimi-export-session_-20260720-135635.md` | Kimi, exported 07-20 21:56 CST | 509 KB | scientific-agent-skills install; GitHub API rate-limit fix; opencode-memory import; "全面分析" (5 parallel explore agents) + "全量优化，不要撰写论文" |
| K2 | `kimi-export-session_-20260720-135720.md` | Kimi, exported 07-20 21:57 CST | 346 KB | Project understanding + formal top-journal gap analysis |
| Q1 | `Execute_academic_research_skills_2026-07-20_22-04.md` | qoder, 07-20 | 237 KB | Meta-task: generates the 11-dimension evaluation prompt (`evaluation_prompt.md`) later used by Q2–Q8 |
| Q2 | `采用多agent执行优化_2026-07-20_22-04.md` | qoder, 07-20 | 1.4 MB | The 6-path parallel optimization whose content became commit `9d47a75`; session ends on Qoder quota FORBIDDEN errors |
| Q3 | `清理项目准备论文_2026-07-20_22-05.md` | qoder, 07-20 | 361 KB | Reproducibility pinning (requirements `==`, py3.12, CI matrix+coverage); 2 sub-agents user-interrupted |
| Q4 | `{_requestId_e229c896...}__2026-07-20_22-05.md` | qoder, 07-20 | 9.9 MB | Largest log: "max parallel agents, check every file, postdoc-level 40–50-page paper" → round-7 audit, 28 problems fixed, 8.5→9/10 |
| Q5 | `Academic_paper_research_tasks_2026-07-20_22-05.md` | qoder, 07-20 | 4.8 MB | Thorough review + Phase A/B/C honesty fixes to v6 manuscript |
| Q6 | `使用最多的agent并行agent..._2026-07-20_22-05.md` | qoder, 07-20 | 5.5 MB | Per-file deep inspection; embeds the round 1→7 review history (5.5/10 → 9/10); export ends mid-work |
| Q7 | `严格审查项目研究_2026-07-20_22-05.md` | qoder, 07-20 | 3.4 MB | Adversarial "Nature reviewer" audit; E21 full run was executing during this session; ends with 6-file cleanup |
| Q8 | `检查论文项目是否达标_2026-07-20_22-05.md` | qoder, 07-20 | 4.7 MB | 10-dimension verdict (6 pass / 4 fail) incl. the pivotal listing-artifact diagnosis; ends with 101-item cleanup (`docs/CLEANUP_REPORT.md`) |

Git history corroboration (54 commits, all historical commits referenced in the logs still exist):
`2472c2f` → `2ce8678` → `01ccb5e` → `012da95` → `8f41dbc` → `9d47a75` → `83e9eb4` → `d6f90a0` (HEAD).
Older anchors: `17569bd` (initial complete-project commit), `b48d4d6`, `adbc2a0`, `cf518a7`,
`b67df34`/`ca2824e` (round-7 audit + manifest regen), `511809e`/`6d60f8d` (P1 backlog, 24 datasets).

---

## 2. What each wave did — key decisions

### 2.1 Early build-out waves (S1, S2; 07-09 → 07-14)

**S1 — P0/P1 backlog completion** (commits `511809e`, `6d60f8d`; manifest: dirty=False, **24 datasets**):
- **T17 references**: `docs/references/unified_references.md` → v2.1, **88 citations**; MQT Bench,
  Benchpress, QuCLEAR, QUEKO, QUESO, circuit unoptimization, PHOENIX, PyZX verified/corrected;
  `.bib` export deferred to writing stage.
- **T19 test split**: monolithic `tests/test_core.py` split into 6 focused modules
  (circuit_generation / optimizers / commutation / integration / wire_traversal / ceiling_aware);
  237 passed, 2 deselected (slow 10-qubit GA).
- **T13 statistical power**: E10 random condition N=200 (Cohen's d=1.23, power OK); E12 N=142
  (MWU power=0.886 OK); **E11 was underpowered** (N=142, power=0.766 < 0.80) → independent
  replicas added for Grover/IQP/Oracle/UCCSD → `e11_merged_powered.csv` N=173, power=0.859.
- **T15 industry benchmarks**: no network access (proxy refused) → **decision: honest fallback** —
  `experiments/e25_industry_benchmarks/run.py` scaffold with Qiskit circuit-library proxies,
  limitation documented; real MQT Bench/QUEKO/Benchpress integration left open.
- Verdict: P0 + P1 complete; P2 (T21–T26, submission/promotion stage) deferred until after writing.

**S2 — release prep**: repo named `quantum-peephole-ceiling`
(`github.com/StarryCode-Lang/quantum-peephole-ceiling`); AI agents could not be shown as GitHub
contributors (avatars don't render) → CONTRIBUTORS.md approach tried, later removed in root cleanup
(`2ce8678`); "Target Journal" line removed from README (`8f41dbc`) — decision: do not advertise
target venue in the public repo.

### 2.2 Review-rounds history (embedded in Q6/Q4; June → 07-20)

The sessions document **seven formal review rounds**, score progression **5.5/10 → 9/10**:
- Round 3 (pre-06-17): 8/10; 95/97 problems fixed; 2 manual items left (post-commit manifest regen;
  PNG→PDF/SVG figure upgrade).
- **Round 4 (2026-06-17) — scope convergence**: round-3 "all solved" verdict was *revised*; the risk
  was narrative overreach, not code. Main results converged to E1–E18 canonical trials (53,300 rows;
  53,525 with held-out + pass-isolation artifacts). **E19/E20/E21 demoted** to planned / metadata-only /
  smoke-only. Listing-model "discovery" temporarily downgraded to hypothesis.
- Round 7 (Q4; commits `b67df34`, `ca2824e`): 28 problems found by 4-way parallel scan, all fixed —
  10 manuscript edits (table renumbering Methods T1-3 → Results T4-11; data re-checked vs
  DATA_CANONICAL; refs [43][44] Fraser & Hanson, Tanenbaum added; orphans [13][14][15] cited;
  E19/E20 annotation fixes; "D8 Track A5" made self-contained; Nielsen & Chuang unified), 4 code fixes
  (unused import in `commutation_rewriter.py`; Dockerfile CMD = CI; E19 `metadata.json` created;
  `.dockerignore`), cleanup of 44 files / −18,518 lines (13 `__pycache__`, 9 old review logs, 7 orphan
  scripts, 2 v4 docs, 3 merged v5 parts, 5 duplicate CSVs; D1–D7 → `_superseded/`). 219 tests pass;
  manifest regenerated dirty=false (16 datasets). **Score 8.5 → 9/10; authoritative manuscript declared
  `docs/06_manuscript/v6_manuscript.md`.**

### 2.3 Diagnostic wave (K2, Q7, Q8; 07-20) — the three verdicts that set the agenda

**K2 (top-journal gap analysis)** — gap table vs. PRX Quantum/Quantum:
- HIGH: theory depth (core theorems elementary); SOTA comparison unfavorable (custom optimizers ~0%
  vs t|ket> FullPeepholeOptimise 5–63%); ceiling-aware holdout failure (MAE=0.2775, Pearson=NaN);
  Phase-2b validated only at fixture scale; E18 44.4% survival bias.
- MED: WCL validated only on random Universal circuits; no random gate-shuffle control; E04 single
  seed; negative results need stronger counter-intuitiveness; abstract/narrative density; 1761-line
  draft; author placeholders.
- Recommended realistic target: **QCE / ACM TQC**; 6-step remediation path (theory depth → key
  experiments → practical value → E18 data quality → refocus narrative on listing sensitivity →
  head-to-head SOTA benchmark).

**Q7 (adversarial audit)** — "solid science (8/10), needs major revision", three critical gaps:
1. **Phase-2a/2b theory–experiment断层**: all lower bounds (Thm 7 ≥16.7%, Thm 9 n/(4.5n+4)) proved for
   Phase-2b (template matching), but experiments ran only Phase-2a (commutation). Biggest logical gap.
2. **Listing-model dependency buried in Discussion** — recommended making representation sensitivity
   the paper's core contribution (directly seeded the v7 restructure).
3. **Multi-compiler claim with Qiskit-only data** (Cirq/t|ket> never executed).
   Plus statistics flags: E10 per-family N=9 (power=0.170), E16 power=0.126, E18 survivorship bias;
   and code-level findings (percentile-vs-BCa bootstrap; `core.py` Cohen's d SE missing the
   `d²/(2df)` term; max-|Cliff's-δ| cherry-picking; BH mislabeled as BY; `load_latest_csv`
   filename-sort fragility; in-place fidelity<0.99 filtering; bootstrap convergence re-run on every
   error bar = ~925k wasted resamples).

**Q8 (10-dimension verdict, 6/10 pass)** — four shortcomings: (1) length 10–12 pp plan vs 40–50 pp
target → reposition as journal long-form; (2) thin theory (honest self-assessment: only 2–3 of 8
theorems substantive; **Thm 2 INSERTION-cascade gap**; Thm 7 artificial circuits; Thm 8 inapplicable
regime); (3) multi-compiler incomplete; (4) **listing-model artifact risk** — Thm 1(b) proves the
Phase-1 action space is structurally empty *under LBL*, so E1–E5's all-zero results could be a
generator-listing artifact rather than "random circuits are incompressible" — the single most
dangerous reviewer attack surface. Q8's follow-up turn ("彻底优化…解决所有问题") is the direct
trigger of the Q2/`9d47a75` optimization wave.

### 2.4 The `9d47a75` wave (Q2 executed, S3 committed/pushed; 07-19/20)

Commit `9d47a75` "feat: multi-agent optimization addressing 6 review gaps" (80 files, +26,977 lines)
— full text preserved in S3; this is the project's single largest quality jump:
- **Path 1 theory**: `docs/theory/QMA_hardness_draft.md` (bounded case); Phase-2 lower bound
  strengthened 1/4.5 → **1/3** via amortization (Thm B1); WCL→LBL gap theorem D1 with full proof;
  upgrade roadmap for Thm 1a/2c/6/7/9.
- **Path 2 experiments**: **Phase-2b full 15-family validation** (624 rows; BV bound PASS n=4,6,8,
  **FAIL n=10**); **WCL full-family expansion** (960 rows; 7/15 families significant WCL>LBL,
  p<1e-6); **gate-shuffle ablation** (2,240 rows; Phase-1 listing-sensitive p=4e-15, Phase-2a robust);
  **multi-seed E04** (800 rows; no seed effect, ANOVA p>0.24).
- **Path 3 ceiling model**: LOFO CV diagnosis — MAE 0.098 vs always-0 baseline 0.092
  (indistinguishable) → **decision: downgrade from exploratory to negative result**; rule-driven
  `CeilingAwareOptimizer` (valid) formally separated from the failed correlation-prediction model.
- **Path 4 E18 data quality**: ITT mean=0.135 [0.102–0.169] vs survivor-only 0.180; failure mode
  systematic (gate-set incompatibility), **MCAR rejected p=1.6e-12**; fidelity verification
  150 pass / 78 decompose_error / 42 unverifiable_width; sensitivity bracket [0.135, 0.187].
  New artifacts: `e18_bias_report.txt`, `e18_corrected.csv`, `e18_itt_report.csv`,
  `e18_littles_mcar.json`, `e18_imputation_draws.csv`, `e18_fidelity_verified.csv`.
- **Path 5 manuscript**: `manuscript_v7.md` 792 lines (from 1761); **"phase transition" renamed to
  "search space stratification"**; contributions consolidated 5+ → 3 around columnar-representation
  example sensitivity.
- **Path 6 SOTA**: 4-tool benchmark (t|ket>/Qiskit/Cirq/custom, 1,480 rows) — custom optimizer
  **never** blows up gates (0/15 families) while production tools blow up on 2–6 families
  (QuantumWalk −1262% to −1905%) → motivates ceiling-aware compilation.
- Tooling: `experiments/comprehensive_analysis.py`, `aggregate_sota_results.py`,
  `generate_sota_tables.py`; SOTA tables freed of TBDs.

### 2.5 Reproducibility + overhaul waves (Q3, K1, S4 → `83e9eb4`, `d6f90a0`)

- Q3 pinned all 12 packages with `==` across `requirements.txt` / `environment.yml` /
  `requirements-lock.txt` (qiskit 2.4.1, numpy 1.26.4, scipy 1.13.1, matplotlib 3.9.0, pandas 2.2.2,
  tqdm 4.66.4, seaborn 0.13.2, scikit-learn 1.8.0, cirq-core 1.6.1, pytket 2.18.0, pytket-qiskit
  0.77.0, pytest 8.2.2); CI test matrix 3.10→3.10+3.12; `flake8 --exit-zero` removed; coverage added;
  `docs/reproducibility.md` lock-file section rewritten. Two sibling agents ("Fix data integrity
  layer", "Archive manuscript update theory") were **manually interrupted by the user** — their scope
  was later completed inside `83e9eb4`.
- `83e9eb4` (07-20 21:58): publication-readiness overhaul — metadata.json schema unified across 28
  files; `data/v5/e18/README.md` (canonical vs derived + survivorship caveat); v7 datasets tracked
  (`e10_phase2b_full`, `e19_extended`, `e22`, `e26`, `e29`); **v6 archived to
  `docs/manuscript/archive/manuscript_v6_archived.md`, v7 promoted to `docs/manuscript/manuscript.md`
  as sole active draft**; theory–experiment scorecard MATCH 12 / PARTIAL 3 / MISMATCH 1 / UNTESTED 0
  (Thm 6 closed by E23 160 rows; Thm 7 closed by E24 75 rows, Phase-2a 79.8% ≫ 1/6 bound);
  `scripts/reproduce_all.py --verify` PASS.
- S4: `d6f90a0` adds `kimi-export-*.md` to `.gitignore` (current HEAD).

---

## 3. Cross-session TODO / gap list (deduplicated, status vs. current repo HEAD `d6f90a0`)

### 3.1 CLOSED by `9d47a75`/`83e9eb4` — do not re-open
1. ~~Phase-2b no canonical validation~~ → `data/v7/e10_phase2b_full/` (625 rows) + E24 closes Thm 7.
2. ~~Multi-compiler Qiskit-only~~ → E20 full (`multi_compiler_full.csv`, 1,070 rows; Cirq n≤8,
   t|ket> n≤6 timeout caveats disclosed).
3. ~~Ceiling-aware model unexamined~~ → LOFO diagnosis done; downgraded to negative result; HGC
   framing throughout v7.
4. ~~E18 survivorship bias unquantified~~ → ITT/bracket/MCAR/fidelity-verification artifacts in
   `data/v5/e18/`.
5. ~~E04 single seed~~ → E29 multi-seed (800 rows, no effect).
6. ~~No gate-shuffle ablation~~ → E22 (2,240 rows).
7. ~~WCL random-only~~ → `e19_extended` full-family (961 rows).
8. ~~Thm 6 UNTESTED / Thm 7 PARTIAL~~ → E23/E24 → MATCH.
9. ~~PNG figures~~ → vector PDFs exist (`analysis/figures/fig*.pdf`; commit `776ce43`).
10. ~~BH-mislabeled-as-BY, Cohen's-d SE term, `load_latest_csv`~~ → fixed (`core.py:229-235` now
    includes `d²/(2df)`; `multiple_comparison.py:94` implements true BY; commit `adbc2a0`).
11. ~~E19/E20 empty dirs~~ → both populated (`e19_wcl_listing_full_*.csv`, `multi_compiler_full.csv`).
12. ~~"phase transition" misnomer~~ → renamed "search space stratification"; historical note only
    (v7 §7.1).
13. ~~Dependency drift (`>=` ranges, numpy 2.x)~~ → `==` pinning everywhere.

### 3.2 STILL OPEN (verified against repo on 2026-07-20)
| # | Gap | Evidence | Suggested owner |
|---|---|---|---|
| O1 | **Release manifest records `dirty: true` and commit `9d47a75`** — it was regenerated mid-`83e9eb4` (created 21:51:22, commit 21:58:46) and never re-regenerated after `83e9eb4`/`d6f90a0`. Breaks the project's own long-standing pattern of ending each wave with a `dirty=false` regen commit (`8ab4a8c`, `fb9bcaf`, `f947ead`, `ca2824e`). | `release/release_manifest.json` git block | manifest worker (already assigned elsewhere — flagged only) |
| O2 | **CI `lint` and `verify-data-integrity` jobs still hardcode Python 3.10** (lines 59, 76) although the test matrix is 3.10+3.12 and all specs say 3.12. First flagged in Q3, explicitly deferred then. | `.github/workflows/ci.yml` | reproducibility worker |
| O3 | **E25 industry benchmarks are proxies, not real suites** — MQT Bench/QUEKO/Benchpress never ran (offline). CSV is literally `e25_industry_proxies_*.csv`. Manuscript must keep the "scaffold/proxy" framing or the suites must actually be run with network access. | `data/v6/e25/`, S1 §T15 | experiments |
| O4 | **Phase-2b BV bound FAILS at n=10** (passes n=4,6,8) — either a theory refinement (bound is asymptotic?) or an explicit limitation; not resolved in any session. | `9d47a75` message path 2 | theory |
| O5 | **Thm 2 INSERTION-cascade gap remains formally open** — noted in Q8 diagnosis and still marked open in `docs/results/analysis_summary.md` (Thm 2b row: "remains formally open"). | `analysis_summary.md` | theory |
| O6 | **QMA-hardness proof is a bounded-case draft only** (`docs/theory/QMA_hardness_draft.md`); full proof + the Thm 1a/2c/6/7/9 "nontrivial upgrade roadmap" are unexecuted. | `9d47a75` path 1 | theory |
| O7 | **Manuscript length 792 lines vs. self-declared target 1200–1400** (v7 status note), and author placeholders unfilled. The 40–50-page ambition from Q8 remains aspirational. | `docs/manuscript/manuscript.md` header | manuscript integration worker |
| O8 | **`docs/results/analysis_summary.md` internal inconsistency**: scorecard says Thm 6 MATCH (closed by E23) but the detailed discussion still carries the pre-E23 "[ACTION REQUIRED] This theorem has not been experimentally validated" note. | grep of the file | docs consistency |
| O9 | **Figure filenames lag the rename**: `analysis/figures/fig01_phase_transition.pdf` etc. still use "phase_transition" while the manuscript uses "search space stratification". | `analysis/figures/` listing | figures worker |
| O10 | **E18 residual unverifiability**: 78 rows decompose_error + 42 rows unverifiable_width remain unverifiable; ITT bracket [0.135, 0.187] is wide. Inherent to data, but must stay visible in Limitations. | `9d47a75` path 4 | manuscript |
| O11 | **WCL advantage significant on only 7/15 families** (p<1e-6) — the other 8 families show no significant WCL>LBL difference; narrative must not overgeneralize "WCL rescues reduction". | `9d47a75` path 2 | manuscript |
| O12 | Minor count drift: `analysis_summary.md` cites E3 = 11,962 trials; manifest's canonical E03 file has 12,000 rows (likely post-filter vs raw — worth one-line reconciliation). | cross-check | data worker |
| O13 | P2 backlog T21–T26 (submission-stage: cover letter, `.bib` export, author info, venue formatting) untouched by design. | S1 | post-writing |

---

## 4. Outdated or contradicted conclusions in the logs (do not quote them against current state)

1. **"Authoritative manuscript is `docs/06_manuscript/v6_manuscript.md`"** (Q4 round-7 verdict,
   multiple sessions) → superseded: v6 archived; sole active draft is `docs/manuscript/manuscript.md`
   (v7, 792 lines); `docs/06_manuscript/` no longer exists.
2. **Round-4 scope convergence ("E19 planned / E20 metadata-only / E21 smoke-only; main results =
   E1–E18 only, 53,300 rows")** → outdated: E19 full (10,000 rows), E20 full (1,070), E21 full
   (1,140) all landed later; current canonical span is 15 families / 67,000+ rows / 27 datasets
   (45 manifest entries).
3. **"Listing-model discovery downgraded to hypothesis"** (round 4) → reversed twice: after WCL/E19
   evidence landed, representation sensitivity was re-elevated to the **core** contribution of v7
   ("columnar representation example sensitivity").
4. **Manifest dataset counts "16" (Q4) and "24" (S1)** → historical snapshots; current manifest
   covers 45 entries (27 canonical datasets + derived/auxiliary).
5. **Test counts 219 / 220 / 237** (various sessions) → current suite is 12 files / **271 test
   functions** (growth from new modules: gate_predicates, hardness_families, ag_canonical, etc.).
6. **"Phase transition" framing and E1 figure naming** → terminology retired project-wide
   ("search space stratification"); old term survives only in v7 §7.1 historical note, dataset
   filenames (`e01_phase_transition_*`), and figure filenames (see O9).
7. **"Thm 6 UNTESTED / Thm 7 PARTIAL"** (v6-era notes) → both MATCH now (E23/E24).
8. **"Statistical code issues" from Q7's adversarial audit (Cohen's d SE, BH/BY label,
   `load_latest_csv`)** → fixed (`adbc2a0` + later); Q7's remaining valid points are the
   *performance* waste of per-call bootstrap convergence checks and the max-|Cliff's-δ|
   selection-bias caveat (not re-verified this wave).
9. **K2's "realistic target: QCE/ACM TQC, not PRX Quantum"** → pre-`9d47a75` judgment made before
   the 6-gap remediation; the current wave treats venue as reopened (PRA/Quantum floor per current
   briefing). Historical context only, not a binding verdict.
10. **Session-referenced commit `cf518a74`/scorecard states at each round** — all still exist in git
    (54-commit history intact, no rewrites), but working-tree claims like "working tree clean at
    9d47a75" are time-stamped snapshots, not current state.

---

## 5. Scientific-conclusion evolution (manuscript-narrative raw material)

### 5.1 Ceiling-aware optimization: from Contribution 5 to honest negative result
1. Rule-based `CeilingAwareOptimizer` built (skip provably-futile passes); E21 created 07-11.
2. An **empirical correlation model** was also fit to predict family-level reduction ceilings.
3. Held-out evaluation **failed**: MAE=0.2775, Pearson=NaN — root cause identified as a
   **zero-variance prediction column**: all five held-out families had exactly 0% observed
   reduction, collapsing covariance. (Q2/S3 deep-reads of v6 §5.5.)
4. 9d47a75 path 3 ran **leave-one-family-out CV**: MAE 0.098 vs always-predict-0 baseline 0.092 —
   statistically indistinguishable → formal downgrade: the *predictive* claim is a **negative
   result**; the *rule-based skipper* remains valid (E21 full mode, 1,140 rows: identical reduction,
   **1.6×–228× speedup, mean 35×**).
5. Manuscript now carries the "**held-out generalization caveat (HGC)**" terminology and frames the
   optimizer as exploratory/observational. Correctness side-note: `CommutationRewriter` v3.1.0 fix —
   the bubble-sort must verify commutation with **both** gate[i] and gate[j] (exhaustive unitary
   tests added, incl. the S–CNOT–Sdg counterexample family).

### 5.2 Phase-2b: theory–experiment gap → full validation → one bound failure
1. v6 era (status note 07-13): Phase-2a = implemented commutation-only optimizer used in canonical
   experiments; Phase-2b = `Phase2bTemplateMatcher`, fixture-scale only (E10 Phase-2b, 1,017 rows) —
   explicitly flagged "no full canonical Phase-2b benchmark".
2. Q7 adversarial audit made this the #1 logical gap: Thm 7 (≥16.7%) and Thm 9 (n/(4.5n+4)) bounds
   are Phase-2b results, but all evidence was Phase-2a.
3. 9d47a75 closed it: full 15-family Phase-2b validation (624 rows; +625-row v7 canonical file).
   **BV bound: PASS n=4,6,8 — FAIL n=10** (O4). Theory simultaneously strengthened: Phase-2 lower
   bound 1/4.5 → 1/3 amortized (Thm B1); Thm 7 generalized to natural BV circuits
   (`thm7_natural_bv.md`, E26).
4. E24 (75 rows) then closed Thm 7 as MATCH: Phase-2a alone achieves 79.8% ≫ the 1/6 bound on the
   theorem's family. Scorecard now MATCH 12 / PARTIAL 3 / MISMATCH 1 / UNTESTED 0.
5. Terminology discipline: "ceiling" claims are always LWM-conditional (listing/window/model),
   never absolute.

### 5.3 E18 (Clifford+T) deviation handling
1. Raw problem: 270 rows → **44.4% row-level / 64.8% circuit-level failure**; naive analysis
   filtered failures → survivorship bias; early manuscript text said "approximately 60%".
2. v6 honesty pass (Q5): exact rates substituted; Oracle Phase-2 description rewritten from actual
   data (Phase 1 ≈31%, **Phase 2 = 0%**); E6–E9 re-labeled "planned but not executed".
3. 9d47a75 path 4 produced the rigorous treatment: ITT mean 0.135 [0.102–0.169] vs survivor 0.180;
   failure mechanism shown **systematic** (gate-set incompatibility), Little's MCAR test rejected
   (p=1.6e-12); fidelity verification triage 150 pass / 78 decompose_error / 42 unverifiable_width;
   final **sensitivity bracket [0.135, 0.187]** reported with canonical-vs-derived README.
4. Narrative use: E18 is now the showcase of the project's statistical-honesty methodology
   (ITT + imputation draws + bracketing), not a hidden flaw.

### 5.4 Listing-model / columnar narrative arc (the current core contribution)
1. v2 era (June): E1 dataset literally named `phase_transition`; zero-reduction framed as phase
   transition / structural ceiling of random circuits.
2. Q8 diagnosis: Thm 1(b) proves LBL makes the Phase-1 action space structurally empty for n≥2 →
   the zeros may be a **listing artifact**. Response: `WireTraversalPreprocessor` + WCL listing.
3. E19 (10,000 rows): under WCL the same circuits yield **7.83%** mean reduction — artifact
   confirmed, desert is a property of the (circuit, listing) pair.
4. E22 gate-shuffle ablation: Phase-1 is listing-sensitive (p=4e-15), Phase-2a robust.
   `e19_extended`: 7/15 families significant WCL>LBL.
5. Thm 1a vs 1b resolution documented in `analysis_summary.md`: the scorecard's single MISMATCH is
   a *model–experiment mismatch* (Thm 1a assumes WCL; generator uses LBL), fully explained by 1b.
6. v7 (07-17 restructure, finalized in 9d47a75): "columnar representation example sensitivity" +
   "search space stratification"; trichotomy 100% (CNOT chains) / 14–16% commutation (oracle,
   Clifford) / ~0% on 10 of 15 families (3 genuine ceilings confirmed by all production compilers,
   7 prototype-limited). "Phase transition" survives only as a §7.1 historical note + a Binder-
   cumulant zero-variance cautionary note (v6 §6.3.8: the cumulant is uninformative on zero-variance
   reduction data; the phase-transition hypothesis was formally rejected).

### 5.5 Release-manifest rebuild history
- Pattern: every audit wave ends with "Regenerate release manifest with clean git state
  (dirty=false, commit X)" — visible at `8ab4a8c`, `fb9bcaf`, `f947ead`, `ca2824e`, `4e9ba91`,
  `bc781eb`, `92173db`, `6d60f8d`, `012da95`.
- Dataset coverage evolution: 16 (round-7) → 24 (S1 P1) → 27 canonical (pre-overhaul) → **45
  entries** (`83e9eb4`, includes derived/auxiliary) with unified metadata schema (seed,
  python_version, qiskit_version, timestamp, git_commit) across 28 metadata files.
- Current deviation from the pattern: HEAD manifest is the mid-`83e9eb4` snapshot
  (`git.commit=9d47a75`, `dirty=true`) — see O1.

---

## 6. One-paragraph arc (for the integration worker)

The logs describe a project that audited itself seven times (5.5/10 → 9/10), survived an adversarial
"Nature reviewer" pass, and pivoted its core claim twice under evidence pressure: from "phase
transition in random-circuit optimizability" (v2), to a defensively scoped "structural-ceiling
benchmark with listing caveats" (v5/v6, round-4 convergence), to "columnar representation example
sensitivity" as the central discovery (v7) — the pivot forced by the Thm 1(b) listing-artifact
diagnosis and confirmed by E19/E22. Along the way it converted its two weakest claims into stated
negative results (ceiling-prediction model → HGC exploratory; Phase-2b bound → full validation with
an n=10 counter-case), hardened E18 into an ITT/bracketed analysis, and industrialized
reproducibility (pinned deps, 45-entry manifest, schema-unified metadata, PDF figures, 271 tests).
Residual work is concentrated in theory depth (QMA draft, Thm 2 INSERTION gap, BV n=10), real
industry benchmarks (E25 proxies), manuscript length/venue framing, and small consistency items
(O1–O13).

---

*Digest prepared by the Archive worker from `_agent_work/past_sessions/` copies. Originals at
`D:\Desktop\*.md` untouched. No repository files were modified except this digest and the
`_agent_work/past_sessions/` copies.*
