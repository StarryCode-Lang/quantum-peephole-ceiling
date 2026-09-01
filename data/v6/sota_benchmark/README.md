# SOTA Benchmark — Qiskit / Cirq / t|ket> / Custom Default Optimizers

**Canonical dataset**: `aggregated/sota_comparison_aggregated.csv` (105 rows) —
per-(tool, config, family) aggregate of all raw runs (7 tool configurations ×
15 families: Qiskit default/level0/level1/level2, Cirq default, t|ket> default,
custom default); the dataset used for manuscript SOTA comparisons.

**Coverage limitation (audited 2026-08-09):** the custom baseline is only a
21-row smoke run (1-3 successful circuits per family), whereas the other full
runs contain 440-520 rows.  Descriptive per-tool means therefore have unequal
width/trial coverage and must not be treated as a balanced head-to-head
benchmark.  Inferential columns in the regenerated aggregate use only exact
one-to-one circuit matches; most families have zero matches, and the only
available paired cells have $n=3$.  A full custom rerun on the shared 520-row
design is required before making SOTA superiority claims.

## Layout

| Path | Role |
|------|------|
| `raw/` | Primary per-tool run CSVs (`{tool}_default_{run_id}.csv`, `qiskit_level{0,1,2}_{run_id}.csv`). Inputs to the aggregate; not canonical themselves. Analysis inputs: `qiskit_default_20260718` (520 rows, optimization level 3), `qiskit_level0/1/2_20260720` (520 rows each, L0–L2 progression), `cirq_default_20260720` (520 rows, corrected pipeline), `tket_default_20260718` (440 rows). The 20260717 files are smoke runs; `cirq_default_20260718` is stale (pre-fix Cirq pipeline — see manuscript Appendix E.1). |
| `metadata/` | Per-run metadata sidecars (`{tool}_default_metadata.json`) with full provenance for each raw run. |
| `aggregated/sota_comparison_aggregated.csv` | **Canonical** aggregate (tool × config × family means) |
| `derived/sota_comparison_aggregated_audit20260809.csv` | Corrected matched-pair inferential audit. This is non-canonical and does not replace the SHA-pinned descriptive aggregate. |
| `derived/` | Predictive-advantage analysis of the aggregate: `predictive_advantage_predictions.csv`, `predictive_advantage_results.csv`, `predictive_advantage_summary.json` (from `experiments/predictive_advantage.py`). These are explicitly in-sample/resubstitution diagnostics, not held-out predictive validation. |

Protocol: `experiments/SOTA_BENCHMARK_PROTOCOL.md`. Generators:
`experiments/sota_benchmark.py` (raw), `experiments/aggregate_sota_results.py`
(aggregate), `experiments/predictive_advantage.py` (derived).
