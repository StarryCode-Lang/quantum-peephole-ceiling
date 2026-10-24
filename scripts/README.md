# scripts/ index

89 scripts. The naming is intentionally verb-first: the prefix tells you what the script
*does*, not which experiment it belongs to. Read this file before adding a new one.

## Naming convention

| Prefix | Meaning | Count |
|---|---|---|
| `verify_*` | Independent checker for one frozen evidence package. Exits non-zero on mismatch. These are the reproducibility chain — do not delete. | 27 |
| `generate_*` | Builds a verdict, manifest, or disposition JSON from frozen receipts. | 12 |
| `audit_*` | Read-only audit that writes a CSV/JSON report and mutates nothing. | 11 |
| `e4x_*` / `e5x_*` | Experiment scripts introduced by the review rounds (E47–E63). | 19 |
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
| `round12_literature_scan.py` | Round 12 literature + ecosystem sweep | 20 structured arXiv queries + authenticated GitHub snapshot. Writes a dated package; network failures are logged, never papered over. |
| `build_round12_evidence_manifest.py` | Round 12 packaging | Adds a self-describing SHA-256 `MANIFEST.json` to each round-12 evidence package without touching the frozen release chain. |

## Analysis helpers introduced by review rounds

| Script | Purpose |
|---|---|
| `audit_panel_baseline_inflation.py` | Normalisation inflation per source (E48 → D1). |
| `census_rule_library.py` | Rule-library census: 1,474 rules, Δ histogram, reverse closure. |
| `derive_v15_certified_lower_bounds.py` | Two-sided intervals for the 34 witness-bounded cells. |
| `test_thm5_tail_necessary_condition.py` | E30-based test of the Thm 5 variance condition. |

## Rules

1. New scripts must not write under `data/` or `release/` — those trees are hash-bound.
2. Every script that produces evidence writes into a dated directory and records the
   SHA-256 of every input it read.
3. Do not rename or delete a script that appears in `release/prepaper_release_manifest.json`
   (35 of the 76 are bound); a rename is a release-drift event.
