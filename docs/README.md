# Documentation Map

This directory separates current project guidance from dated research history.
Use the current-facing documents below for the active implementation and
evidence boundaries. Dated review files, manuscript text, and `archive/`
directories remain historical records and are not silently rewritten.

## Current entry points

| Purpose | Document |
|---|---|
| Project overview and release boundaries | [`../README.md`](../README.md) |
| Reproduction and verification commands | [`reproducibility.md`](reproducibility.md) |
| Dataset schemas and provenance | [`data_dictionary.md`](data_dictionary.md) |
| Experiment design and protocol history | [`results/experimental_design.md`](results/experimental_design.md) |
| Current aggregate results and claim limits | [`results/analysis_summary.md`](results/analysis_summary.md) |
| Theoretical framework | [`theory/framework.md`](theory/framework.md) |
| v12 rewrite-exposure theory draft | [`theory/v12_rewrite_exposure_theory.md`](theory/v12_rewrite_exposure_theory.md) |
| v12 execution state and boundaries | [`review/v12_execution_state.json`](review/v12_execution_state.json) |
| v12 requirement-to-evidence ledger | [`../data/v12/v12_requirement_to_evidence_ledger.json`](../data/v12/v12_requirement_to_evidence_ledger.json) |
| v12 readiness disposition | [`../release/prepaper_v12_readiness_verdict.json`](../release/prepaper_v12_readiness_verdict.json) |

## Evidence conventions

- Historical canonical totals are controlled by `data/DATA_CANONICAL.md` and
  `release/release_manifest.json`.
- v12 is a separately bounded evidence package. It does not silently replace
  E1--E37 data or become manuscript evidence merely because its verifier passes.
- `PASS`, `EXTERNAL_BOUNDARY`, `NOT_ESTIMABLE_EXTERNAL_BOUNDARY`, and
  `NOT_READY_FOR_PAPER` are distinct dispositions and must be preserved.
- The active manuscript is intentionally unchanged while the v12 E40 efficacy
  estimand is not estimable.

## Historical material

`docs/review/wave*/`, `docs/**/archive/`, dated review notes, and the active
manuscript's historical sections are retained for provenance. Their dates and
claims should not be rewritten to make them appear to be current v12 results.
