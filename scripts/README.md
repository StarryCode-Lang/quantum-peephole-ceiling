# scripts/ index

119 scripts. The naming is intentionally verb-first: the prefix tells you what the script
*does*, not which experiment it belongs to. Read this file before adding a new one.

## Naming convention

| Prefix | Meaning | Count |
|---|---|---|
| `verify_*` | Independent checker for one frozen evidence package. Exits non-zero on mismatch. These are the reproducibility chain — do not delete. | 32 |
| `generate_*` | Builds a verdict, manifest, or disposition JSON from frozen receipts. | 15 |
| `audit_*` | Read-only audit that writes a CSV/JSON report and mutates nothing. | 12 |
| `e4x_*` / `e5x_*` / `e7x_*` / `e8x_*` | Experiment scripts introduced by the review rounds (E47–E83). | 34 |
| `build_*` | Packaging (restore capsules, readiness packages, evidence manifests). | 3 |
| `reproduce_*` / `regenerate_*` | Full-corpus replay entry points. | 2 |

## Entry points

| Task | Command |
|---|---|
| Full test suite | `python -m pytest tests/ -q` |
| Replay every canonical dataset | `python scripts/reproduce_all.py` |
| Verify a frozen package | `python scripts/verify_<package>.py` |
| v15 readiness | `python scripts/verify_v15_readiness_verdict.py` |
| Certificate verifier (standalone) | `python scripts/verify_certificate_qrcert_v1.py <cert>` |

## Review-round experiments (E47–E63)

Each writes a dated evidence package under `docs/review/science_boost/<date>_<topic>/`
and carries an `EXPERIMENT_ID` plus a contract block in its docstring.

| Script | Experiment | Question |
|---|---|---|
| `e47_horizon4_probe.py` | E47 (2026-10-19) | Do h=3 local optima break at h=4..8? |
| `e47_verify_escapes.py` | E47 support | Replay + independent walk + unitary check for each escape. |
| `e48_external_falsifier.py` | E48 (2026-10-20) | Do external optimizers break the ceilings? (qiskit / tket / pyzx) |
| `postprocess_e48.py` | E48 support | Panel-level aggregation of E48 rows. |
| `e49_source_relative_rebaseline.py` | E49 (2026-10-21) | Dual-denominator reporting (baseline vs source). |
| `e50_horizon_scaling.py` | E50 (2026-10-21) | Does the first improving horizon grow with n? (BV ladder) |
| `e51_literature_harvest.py` | E51 (2026-10-21/22) | arXiv harvest + zero-coverage report. `--output-dir` overrides the date. |
| `e51b_github_ecosystem.py` | E51b | Ecosystem probe (rate-limited without `GITHUB_TOKEN`). |
| `e52_escape_mechanism_census.py` | E52 (2026-10-22) | What carries the certified escapes? Root kind, reducing rule, neutral-step effect. |
| `e53_bqskit_tzap_falsifier.py` | E53 (2026-10-22) | BQSKit as the fifth external optimizer; GHZ / SurfaceCode / QFT / genuine escapes. |
| `e54_d2_uniform_rebaseline.py` | E54 (2026-10-22) | Uniform greedy re-baseline (D2) + full h=3 panel rerun. |
| `e55_commutation_gap_probe.py` | E55 (2026-10-22) | Six-engine probe of diagonal-through-control commutation. |
| `e56_closure_criterion.py` | E56 (2026-10-23) | Exposability criterion (Theorem 1) + certified closure; `--self-check` compares the local predicate with `_commutes`. |
| `e57_closure_vs_tket.py` | E57 (2026-10-23) | Closure vs tket 2.18.0 `RemoveRedundancies` on the same roots. |
| `e58_cross_engine_closure.py` | E58 (2026-10-24) | Two-qubit cost split of the closure gain + closure applied on top of qiskit L3 / tket FPO / BQSKit, with residual-pair diagnosis. |
| `e59_qcec_oracle.py` | E59 (2026-10-24) | Third-party equivalence oracle (MQT QCEC 3.11.0) over the closure panel. Carries the `sysconfig` DLL shim that makes QCEC importable on Windows. |
| `e60_closure_selection_order.py` | E60 (2026-10-24) | Closure under three pair-selection keys (distance / finish / random) — tests Theorem 2's per-pass optimality on the real panel. |
| `e61_opt_level_monotonicity.py` | E61 (2026-10-24) | Qiskit L0–L3 in the frozen basis: is `optimization_level` monotone? Found L3 worse than L2 on 6/101 sources. |
| `e62_rotation_gap.py` | E62 (2026-10-25) | Phase-polynomial rotation bound `R >= |supp(f)|`, the reorder/content gap decomposition, and the Hadamard-annihilation counterexamples. Parts A/B/C via `--skip-parts`. |
| `e63_qiskit_261_recheck.py` | E63 (2026-10-25) | Does E61's L3 defect survive qiskit 2.6.1? Three stages so two interpreters can share one panel: `dump` (2.4.1) → `sweep` (2.6.1) → `compare`. |
| `e64_escape_geometry_atlas.py` | E64 (2026-10-25) | Frozen-window escape-rate atlas, window→whole-listing separation test, branching law, gain/barrier distributions, and the bounded-cell exactification tracker. |
| `e65_bounded_exactification.py` | E65 (2026-10-25) | Raised-contract (s1M/t300) re-run of BOTH engines on the 34 witness-bounded cells + the derived cell `e39:b2f83603…`, with free-RAM gating, resume-safe JSONL. |
| `e66_kbc_critical_pairs.py` | E66 (2026-10-25) | Knuth–Bendix critical-pair census over `e44_core_v1`: overlap unification, exact dense semantic checks, gate-reducing candidates and derivability signals. |
| `e67_full_scope_pilot.py` | E67 (2026-10-25) | `rule_scope="full"` (1,474 rules) pilot on the 32 E44 fixture cells at the frozen budgets. |
| `generate_v16_landscape_integration.py` | v16 re-pin (2026-10-25) | v15 integration derivation against the corrected-engine v16 panels; adds the resource-bounded tier for `e39:b2f83603…`. |
| `generate_fragment_bench.py` | P5 (2026-10-25) | Fragment-native benchmark generator: 6 families × ≥8 instances × n=4..64 with analytic phase-polynomial support size s. |
| `e70_fragment_rotation_gap.py` | E70 (2026-10-26) | Rotation-gap decomposition on the fragment-native benchmark (240 instances, n=4..64); per-family scaling of g_reorder/g_total. |
| `e71_external_circuits.py` | E71 (2026-10-26) | External validity set: MQT Bench subset normalized to the frozen basis + certified closure (mqt-bench 2.3.0, 14/14 OK). |
| `build_e65_package.py` | E65 packaging | Builds summary/receipt for the bounded-exactification campaign from its resume-safe cells.jsonl. |
| `generate_v16_readiness_verdict.py` / `verify_v16_readiness_verdict.py` | v16 re-pin (2026-10-25) | v16 readiness verdict derivation and its fail-closed verifier. |
| `verify_bv_lower_bound.py` | P6 (2026-10-25) | Exact-arithmetic verification of the BV k+2 document: true unitary identity, Heisenberg images, achievability via the real Phase-2b pipeline, exhaustive Case-B check (n ≤ 3). |
| `verify_perp_reliability.py` | P6 (2026-10-25) | Matrix proof of the nine ⊥ exchange rules + negative controls (exact sympy, engine families imported). |
| `e68_literature_scan.py` | E68 (2026-10-26) | arXiv Atom + GitHub REST + Crossref/DataCite sweep. Writes a dated package with per-file SHA-256; no synthesis, no LLM. |
| `e69_window_inference.py` | E69 (2026-10-26) | Design-based inference for the frozen v16 window landscape: denominator reconciliation, cluster bootstrap, ICC/design effect, paired-by-source contrasts, and the root-kind stratification. Closes WL-4 and surfaces D3. |
| `e72_span_law.py` | E72 (2026-10-27) | Search-free span criterion vs the frozen E46 window panel: 76,236 rows, 0 false positives, exact first-escape depth on 38,006/38,008; strata split shows recall 97.0% (raw roots) vs 32.8% (greedy fixed points). |
| `e73_library_completeness.py` | E73 (2026-10-27) | Rule-library completeness on the 2-qubit Clifford fragment (4,681 listings / 460 unitary classes, absolute optimum by enumeration): 30.25% of reducible listings cannot reach the optimum; 114 are rewrite-isolated (zero legal actions). |
| `e78_width_threshold.py` | E78 (2026-10-29) | Completeness-threshold experiment: widths 2 and 3, listings m = 5 and 6, plus a primitive-identity census. Result: `L* = m`, not a constant. Also repairs E75's alphabet closure (name-based -> instance-based). |
| `e80_rule_length_demand.py` | E80 (2026-10-29) | (A) the genuine 24-element one-qubit Clifford group on `{h,s,x,z}`: `L* = 5`, library price 82.87%. (B) action-type census of E72's 1,564 content-class FN rows: 954 are a **criterion implementation gap** (parametric rotation pairs), 610 genuinely need depth >= 2. |
| `e81_ladder_m7.py` | E81 (2026-10-29) | The m=7 ladder point with a **two-pass streaming fragment** (E75's Fragment materialises every listing and died with MemoryError at 8^7). Reproduces E78's m=6 exactly before running m=7. |
| `e79_literature_scan.py` | E79 (2026-10-29) | Round-19 arXiv + GitHub sweep (18 fielded queries, 185 records, 108 from 2026). |
| `e82_diameter_bound.py` | E82 (2026-10-30) | **Exact Cayley distance oracle** on the projective Clifford tableau, plus a locally-rigid word census. Proves `L*(m) <= min(m, D+1)` empirically and refutes the unbounded-ladder reading of E78/E81: `W2` has `D = 7` and `L*(8) = 8`; `Q1` has `D = 4` and `L* = 5`. Reproduces E78's m=6 gap-1 count (4,664) and E81's m=7 count (7,056) bit-exactly, and matches a qiskit `Clifford` BFS bit-exactly. Also censuses the shipped library: max rule source length **5**, so it is 3 levels short of the `W2` threshold. |
| `e84_panel_gate_diameter.py` | E84 (2026-10-31) | Exact Cayley distance oracle on the panel gate set, with **Z4 phases** so no `i` factor is dropped. The project's own basis `{h,x,rz,cx}` has 2-qubit Clifford order **11,520** and diameter **9** (threshold 10); round 20's `D = 7` was measured on a 1,152-element index-10 subgroup. Also censuses CX directions in the frozen panel (18,234 forward / 6,348 reversed) and constructs locally rigid witnesses of length `D+1`. 19 self-checks; qiskit agrees bit-exactly on all 7 fragments. |
| `e85_literature_scan.py` | E85 (2026-10-31) | Round-21 arXiv sweep (20 fielded queries, 246 records, 123 from 2026) with **authenticated** GitHub REST (9/11 repos OK; `psg-mit/quanto` and `quartz-tools/quartz` are 404). Coverage is measured against every arXiv id under `docs/`, not just the catalogue. |
| `e86_threshold_scaling.py` | E86 (2026-10-31) | The counting bound `L_min(n) = min{L : sum_{k<=L} g(n)^k >= |C_n|}` with `g(n) = n^2+3n`: the completeness threshold is `Omega(n^2/log n)`, and the shipped 5-gate budget already fails at `n = 3`. Validates `|C_n|` against 24 / 11,520 / 92,897,280. |
| `e87_panel_price_recheck.py` | E87 (2026-11-02) | Re-measures the completeness-price curve on the **panel** generator set (11,520) instead of the 1,152-element subgroup every published point used. Part A reproduces E78 bit-exactly (the numbers were right, the scope label was wrong); Part B gives L=4 = 6.40% and shipped = 56.07%; Part D (m=6) gives the first non-zero length floor, `P_len(6,5) = 4.03%`. Coverage-class counts 876 / 3,775 / 7,621 equal E84's Cayley ball sizes at radii 5 / 5 / 6. 13 self-checks. |
| `e88_consistent_diameter.py` | E88 (2026-11-02) | Three-qubit diameter via bidirectional ball growth: `D_3 in [11, 12]` (lower bound pinned exactly by `ball_5(e) ∩ ball_6(g) != ∅` and `ball_5(e) ∩ ball_5(g) = ∅`), ball growth 1/22/274/2,565/19,680/127,925/711,213. Also the generator-variant table behind `PD-3`: adding `sdg` leaves the 2-qubit group order and `D` unchanged but moves the distance distribution (d=5: 2,465 -> 2,926; d=8: 706 -> 328), and drops the 1-qubit `D` from 4 to 3. 12 self-checks. |
| `e89_literature_scan.py` | E89 (2026-11-02) | Round-22 arXiv sweep (18 fielded queries, 229 records, 174 from 2025+). Reports **two** coverage keys, `records_cited_loose` and `records_cited_strict`; the loose count matches a substring anywhere under `docs/`, the strict one requires the id to appear outside earlier scans' own dumps. Found `2607.22248` (states `Theta(n^2/log n)` is known) and `1305.0810` (PMH 2013 peephole with optimal <=4-input Clifford circuits), both previously uncited. |
| `e90_rule_utilisation.py` | E90 (2026-11-04) | Census of which rules the frozen E46 window panel actually uses: 38,118 unique windows, 19,303 with a reducing action and **every one of them source length 2**; only 37 of the 149 `e44_core_v1` rules ever fire, 2 of them as reducing; 699 of 20,002 escapes have **no** reducing action at the root (reorder-first), and all 19,303 content-first windows sit on the RAW stratum while the 1,228 greedy-fixed-point windows have none. Also records that the declared scope's maximal source length is **4**, not the catalogue's 5 (defect D10). 5 self-checks. |
| `e91_rigidity_floor.py` | E91 (2026-11-04) | Exact counting law for the locally irreducible class, no search and no sampling: `V(m,L)` = words of length `m` whose every window of length `<= L` is geodesic, by DP on the last `L-1` generators; `m = D+1, L = D` by the two-window identity. Panel group: 20,568 of 10^10 at `(10, 9)` (2.057e-6); `rho(m,5)` peaks at m=7 (6.03%) then decays geometrically with lambda ~ 0.58. Reproduces E87's two fragment denominators (80,986 / 988,046) from the `G` sequence alone. 11 self-checks. |
| `e92_literature_scan.py` | E92 (2026-11-04) | Round-23 arXiv sweep (20 fielded queries, 243 records, 92 from 2026) reusing E85's client. Found `2608.27592` (plateau-constrained selection: equal-cost orders give routed depths 228.6 / 233.8 / 256.7) — the strongest external corroboration of the neutral-move mechanism and the closest priority competitor. |
| `e93_fragment_bench_dedup.py` | E93 (2026-11-04) | Defect D11: the fragment bench's 240 "instances" are **170 distinct circuits** -- `gen_trotter_zz` and `gen_arithmetic_phase` never consume their seed, so 80 rows are 10 circuits replicated 8x. `trotter_zz` has a reorder share of exactly 0 but 22.1% of the gap weight, so the duplication inflated it 8x: pooled `g_reorder/g_total` is **0.880**, not the published 0.710. Family-level conclusions are unaffected. 6 self-checks. |
| `e83_literature_scan.py` | E83 (2026-10-30) | Round-20 sweep: 22 fielded arXiv queries (343 records, 183 from 2026, latest 2026-10-27) + 11 ecosystem repos. Coverage check excludes earlier scans' own dumps. GitHub REST returned 403 this round (unauthenticated quota). |
| `e74_literature_scan.py` | E74 (2026-10-27) | Round-17 arXiv + GitHub sweep with **fielded** `abs:"..." AND abs:"..."` queries (221 records). Use this form, not `e68`'s `all:` wrapper -- the wrapper degenerates into a bag-of-words AND and drowns the relevant hits. |
| `round12_literature_scan.py` | Round 12 literature + ecosystem sweep | 20 structured arXiv queries + authenticated GitHub snapshot. Writes a dated package; network failures are logged, never papered over. |
| `build_round12_evidence_manifest.py` | Round 12 packaging | Adds a self-describing SHA-256 `MANIFEST.json` to each round-12 evidence package without touching the frozen release chain. |

## Analysis helpers introduced by review rounds

| Script | Purpose |
|---|---|
| `audit_frozen_bytes.py` | **Use this instead of `git status` to prove frozen data is untouched.** Hashes every `(path, sha256)` pair a manifest declares and classifies MATCH / CRLF_DRIFT / REAL_DRIFT / MISSING / KNOWN_DRIFT_ACCEPTED. Round 19 found a 6,721-byte CRLF drift that `git status` reported as clean. Pass `--dispositions docs/review/release_drift_register.json` for the preprint chain: a digest matching the register is accepted, a digest that moves again fails closed. |
| `audit_panel_baseline_inflation.py` | Normalisation inflation per source (E48 → D1). |
| `census_rule_library.py` | Rule-library census: 1,474 rules, Δ histogram, reverse closure. |
| `derive_v15_certified_lower_bounds.py` | Two-sided intervals for the 34 witness-bounded cells. |
| `test_thm5_tail_necessary_condition.py` | E30-based test of the Thm 5 variance condition. |

## Rules

1. New scripts must not write under `data/` or `release/` — those trees are hash-bound.
2. Every script that produces evidence writes into a dated directory and records the
   SHA-256 of every input it read.
3. Do not rename or delete a script that appears in `release/prepaper_release_manifest.json`
   (35 of the 80 are bound); a rename is a release-drift event.
