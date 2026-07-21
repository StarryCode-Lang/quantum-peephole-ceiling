# Wave-1 Review — Universal Law Discovery

Worker: Theoretical Physicist (Theory). Date: 2026-07-20.
Scope: `docs/theory/*.md` (full read), manuscript reference list (verification
only), ceiling-prediction model (diagnosis + repair), cross-disciplinary and
Nature/Science-tier assessment. Main intellectual deliverable:
`docs/theory/universal_law_assessment.md` (new, this domain owns it).

No edits were made to `docs/manuscript/manuscript.md` or
`src/optimisation/ceiling_aware.py` (both off-limits to this worker). The one
overwritten file (`experiments/ceiling_model_repair.py`) was backed up with a
timestamp (`experiments/ceiling_model_repair.py.bak-20260720-230053`) and
replaced atomically (write `.tmp` → `mv`). All result files were written
atomically.

## 1. Files created or changed

| File | Action | Content |
|---|---|---|
| `docs/theory/universal_law_assessment.md` | Created | Universality verdict per theorem; most surprising result + cross-disciplinary connections; citation audit; Nature/Science gap analysis |
| `docs/review/wave1/universal_law.md` | Created | This report |
| `experiments/ceiling_model_repair.py` | Rewritten (backup `.bak-20260720-230053`) | Diagnosis + mechanism-feature rebuild + LOFO retest + reframed evaluations |
| `data/v6/ceiling_repair/diagnosis.json` | Created | Root-cause diagnosis of the HGC failure |
| `data/v6/ceiling_repair/repair_summary.json` | Created | Repair metrics, baselines, reframed results |
| `data/v6/ceiling_repair/repair_lofo_results.csv` | Created | Per-fold LOFO metrics (8 configs × 15 folds) |
| `data/v6/ceiling_repair/mechanism_features.csv` | Created | Leak-free mechanism features for 570 E21 circuits (sha256-verified regeneration) |
| `data/v6/ceiling_repair/scholar/` | Created | Citation-verification scripts (`verify_refs*.py`) and raw results (`ref_verification*.csv`, `results/`) |

Prior-attempt artifacts `data/v6/ceiling_repair/lofo_cv_results.csv` /
`lofo_cv_summary.json` (20 families, 835 rows, dated 2026-07-17, source
pipeline no longer in repo) were left untouched as a historical record.

## 2. Theory documents read (complete)

`framework.md` (D1–D10, complexity taxonomy, honest scope statements);
`formal_results.md` (1,313 lines: Thm 1a/1b, 2, 2c/2d, Lemma 3/4, Thm 5–9,
Prop 1 corrected, Obs 1, C1/C2, Appendix A INSERTION proofs, Appendix B BV
Phase-2b bound); `nontrivial_upgrades.md`; `phase2_lower_bound_strengthening.md`
(Directions A–D); `QMA_hardness_draft.md` (Thm 1 proven; Thm 2/4 conditional;
Thm 3 sketch only). Verdicts per theorem are in the assessment document §1:
no physics-grade universal law exists in the corpus; the strongest exportable
principles are the Thm 2c/2d conservation law (move-set-bounded) and the
representation-determinism principle (§1.2 of the assessment).

## 3. Ceiling-model repair — results (completed, honestly reported)

**Diagnosis** (`diagnosis.json`, re-verified this session): the held-out
generalization failure was driven by (i) target degeneracy — 11 of 15 families
have zero variance in `gate_reduction`, so per-fold Pearson is structurally
NaN; (ii) family identity carrying $\eta^2 = 0.939$ of target variance, so
LOFO removes the signal; (iii) feature–mechanism mismatch (generic features are
correlates of family identity, not of reducibility). Not label noise, not
primarily data volume, not model architecture.

**Repair**: deterministic regeneration of all 570 E21 naive-pipeline circuits
(sha256-verified, 60/60 spot check + full pass), mechanism features extracted
via `analysis/structural_ceiling.py` (no optimizer run, no leakage).

**LOFO results** (`repair_summary.json`, pooled over all rows; verified against
the JSON this session):

| Config | Pooled MAE | Pooled Pearson r | Pooled Spearman ρ | NaN-r folds |
|---|---:|---:|---:|---:|
| baseline predict-0 | 0.0963 | — | — | — |
| baseline global-train-mean | 0.1685 | −0.969 | −0.716 | — |
| generic + two-stage RF | 0.1182 | −0.060 | 0.317 | 13 |
| generic + single-stage RF | 0.1164 | −0.054 | 0.223 | 11 |
| **mechanism + single-stage RF** | **0.0695** | **0.722** | **0.847** | 11 |
| mechanism + two-stage RF | 0.0927 | 0.184 | 0.184 | 13 |
| combined + single-stage RF | 0.0750 | 0.613 | 0.797 | 11 |
| combined + two-stage RF | 0.0994 | −0.051 | −0.025 | 13 |

Original failure reproduced (generic features, r ≈ −0.06). Repair beats the
predict-0 baseline (0.0695 < 0.0963). Two-stage gating hurts; generic features
dilute mechanism features. Feature importance (full-fit RF, recomputed this
session): `structural_upper_bound` 0.759, `phase1_action_density` 0.188, all
others ≤ 0.041.

**Ceiling-proxy tightness** (structural upper bound vs actual reduction,
pooled): r = 0.988, ρ = 0.928, MAE = 0.009 — the project's predictive-advantage
thesis holds under a leak-free rebuild.

**Still failing (recorded, not hidden):**

- CNOT family held out: fold MAE 0.745 (predicts ~0.25, actual 1.0) — the model
  cannot extrapolate the 100%-reduction regime from other families.
- Family-mean regression: n = 15 families, r = 0.059 (ρ = 0.508) — underpowered;
  no cross-family *level* prediction.
- 11/15 folds remain structurally NaN-Pearson (zero-variance targets) —
  irreducible without non-degenerate families.
- Classification reframing: balanced-acc 0.769, MCC 0.598, but F1 = 0.075
  (zero-positive folds dominate).
- Within-family magnitude works where variance exists: Grover r = 0.868,
  Oracle r = 0.920, RandomClifford r = 0.775.

**Verification command**: `/d/Downloads/miniforge3/python experiments/ceiling_model_repair.py`
(~1 min with cached `mechanism_features.csv`; full circuit regeneration adds
several minutes). Run earlier today: completed green; numbers above read back
from `repair_summary.json` this session and matched.

## 4. Literature verification — results (completed)

Method and full tables in the assessment §3; raw evidence in
`data/v6/ceiling_repair/scholar/`. Four scholar passes plus arXiv API, direct
arXiv abstract fetches, and web search (final two checks this session).

Headline findings (must fix before submission):

- **[22] fabricated**: "de Beaudrap, Glendinning, Zhang, Faster resynthesis
  with the ZX-calculus, QPL 2022, arXiv:2206.10843" — no such paper (arXiv
  title search 0 hits; no quantum author Glendinning); the arXiv ID belongs to
  an unrelated ML paper (verified by fetching arxiv.org/abs/2206.10843 this
  session). Likely-intended real work: de Beaudrap, Kissinger, van de Wetering,
  "Circuit Extraction for ZX-diagrams can be #P-hard", ICALP 2022,
  arXiv:2202.09194 (verified this session) — whose content contradicts the
  manuscript's gloss.
- **[81] fabricated**: "Patel, Shapira, Markov, Quantum circuit optimization:
  A survey, ACM CSUR 55(9):178, arXiv:2210.12035" — the arXiv ID is a
  computer-vision paper (verified by fetching arxiv.org/abs/2210.12035 this
  session); no such survey exists (3 scholar passes + 2 web searches).
- **[70] QASMBench**: real paper, wrong authors/arXiv ID (real: Li, Stein,
  Krishnamoorthy, Ang; ACM TQC 2022; arXiv:2005.13018).
- **[16] Kliuchnikov**: real; volume/page/title wrong (real: PRL 110, 190502,
  2013; arXiv ID correct).
- **[67] Riu**: real; article number 1634 → 1758.
- **[69] MQT Bench**: real; first author "C. Nitsch" → N. Quetschlich.
- **[20] Amy/Glaudell/Ross**: author–topic real; venue/year combination
  unverified.
- **Missing citations**: VOQC (Hietala et al., POPL 2021 — in
  `unified_references.md` but absent from the manuscript list), Equality
  Saturation for Quantum Circuit Optimization (verified exists), SSR
  (Swapping-Sweeping-and-Rewriting, verified exists).

Novelty searches (N1–N10) found no direct precedent for the listing-model
taxonomy, the quantified listing flip, or structural ceiling proxies at
r ≈ 0.99 — with the explicit caveat that absence in these passes is not proof.

## 5. Most surprising result + cross-disciplinary connections

Flagship: E19 listing flip (0.0000% over 25,000 LBL trials → 7.83% over the
same ensemble in WCL, 10,000 rows, fidelity 1.0) — a replicated null result
that was entirely a representation artifact. Supporting: INSERTION sterility
(1000/1000 creates action space, 5000/5000 zero net gain), 45,500-trial
algorithm-independence, and the compiler gap being representational (Qiskit O3
vs prototype per-family table). Connections developed in the assessment §2.3:
ML representation learning, classical phase-ordering/canonicalization,
statistical physics (measure concentration, percolation-like commutation
blocks, frustration), term-rewriting invariants/confluence.

## 6. Nature/Science honest assessment

Delivered quantitatively in the assessment §4. Summary: current package fits
Quantum / ACM TQC / PRX Quantum after citation fixes; Nature-tier requires
hardware validation, ≥ 50-family scale with predictive (not descriptive)
validation, completion of Thm 3 or a listing-invariant ceiling theory, full
15/15 mechanism attribution, and the WCL-audit caveat. Months of work, not
weeks.

## 7. Unresolved gaps (handoff list)

1. Manuscript reference fixes ([16], [22], [67], [69], [70], [81], possibly
   [20], [61]) and three additions (VOQC, equality saturation, SSR) — owner:
   manuscript/integration worker. Evidence ready in §3.2–3.3 of the assessment.
2. `docs/references/literature_review.md` lines 100–107 summarize the
   fabricated [22]; the paragraph must be rewritten or deleted.
3. CNOT held-out underestimation (fold MAE 0.745) — needs either
   regime-indicator features or explicit exclusion with a stated boundary.
4. Family-mean prediction underpowered (n = 15) — needs more families before
   any cross-family level claim.
5. The 20-family/835-row prior LOFO artifacts have no reproducible source in
   the repo; flagged as historical only.
6. Listing-invariant ceiling theory (assessment §1.2) and QMA Thm 3 roundtrip
   lemma remain open theory campaigns.
7. WCL-audit of production compilers (manuscript §7.5) still open; the
   flagship practical claim is hostage to it.

## 8. Verification commands used this session

- Read-back of all quoted repair numbers:
  `python3 -c` JSON/CSV queries against `data/v6/ceiling_repair/repair_summary.json`,
  `repair_lofo_results.csv`, `lofo_cv_summary.json` (prior attempt).
- Feature-importance recompute (matches notes): full-fit RF on
  `mechanism_features.csv` + naive rows of `data/v6/e21/ceiling_aware_comparison.csv`
  → `structural_upper_bound` 0.759, `phase1_action_density` 0.188.
- ref [22]/[81] final verdicts: `FetchURL https://arxiv.org/abs/2206.10843`,
  `https://arxiv.org/abs/2210.12035`, `https://arxiv.org/abs/2202.09194`;
  arXiv API author/title queries (`au:"Glendinning"`, `all:"Faster resynthesis"`
  → 0 hits); web searches for the ACM CSUR survey (0 hits).
- E19/E1/E12/E20 numbers re-read from `docs/manuscript/manuscript.md` tables
  and `data/v4/e12/` source CSV.
