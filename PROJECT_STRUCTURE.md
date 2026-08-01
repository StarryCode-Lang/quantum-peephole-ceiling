# Project Structure

## Source Of Truth

- `src/`: reusable circuit generators, optimizers, predicates, configuration, and provenance helpers.
- `experiments/`: experiment drivers. Each driver records parameters and writes versioned outputs under `data/`.
- `analysis/`: statistical analysis and figure-generation code. `analysis/figures/` contains derived publication artifacts.
- `tests/`: unit, integration, optimizer-correctness, data-schema, and statistical tests.
- `data/DATA_CANONICAL.md`: canonical dataset policy and active file list.
- `release/release_manifest.json`: SHA-256 and row-count release gate for canonical datasets.
- `docs/manuscript/`: active manuscript and claim-evidence map.
- `docs/theory/`: definitions, proofs, conjectures, and scope notes.
- `docs/supplementary/`: supplementary methods, tables, and provenance context.
- `docs/review/`: audit reports and historical wave decisions; historical files are not active evidence unless referenced by the current claim map.
- `docs/verification/`: reproducibility and calibration artifacts.
- `scripts/`: repository-level verification, manifest, and calibration entrypoints.

## Data Roles

- Canonical evidence: files listed in `release/release_manifest.json`.
- Derived evidence: regenerated summaries under experiment `derived/` directories or `analysis/figures/`.
- Rerun evidence: `data/v9/`; current-code reconciliation outputs are non-canonical and must not replace frozen release data without an explicit version decision.
- Disposable local state: Python caches, timestamped backups, agent sessions, and logs. These are ignored and removed during final cleanup.

## Required Gates

```text
python -m pytest tests/ -q
python -m compileall -q src experiments scripts analysis
python scripts/reproduce_all.py --verify
python scripts/characterize_fidelity_fallback.py --n-values 3 5 8 --samples 1000
```

Use `conda run -n q-research python ...` when the environment is not activated.
