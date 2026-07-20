# Manuscript Declarations

> **Version**: 6.0.0
> **Date**: 2026-07-11
> **Scope**: Declaration sections for the manuscript "Listing Model Sensitivity and Structural Ceilings in Quantum Circuit Optimization," targeting ACM Transactions on Quantum Computing (TQC) / Quantum journal. These sections are to be appended to the main manuscript upon finalization.

---

## Data Availability Statement

All experimental data supporting the findings of this study-including raw CSV outputs, experiment metadata, and release manifests-are available in the project repository under the `data/` directory, organized into versioned subdirectories (`v1`-`v7`) corresponding to successive experimental campaigns. Each dataset entry records its experiment identifier, row count, schema version, and file path.

To ensure reproducibility and integrity verification, SHA-256 checksums for every dataset are recorded in `release/release_manifest.json`. Researchers may verify data integrity by recomputing checksums against the manifest.

All datasets can be regenerated from scratch by executing:

```
python scripts/reproduce_all.py --all
```

This script orchestrates the full experimental pipeline (E01-E24) across all 15 circuit families and 6 optimizer types, reproducing the 63,535 canonical optimizer trials reported in the manuscript. A persistent archival copy of the data has been deposited on Zenodo:

> **Archival DOI (placeholder)**: `10.5281/zenodo.XXXXXXX` (to be assigned upon acceptance)

---

## Code Availability Statement

The complete source code for this study-including all optimizer implementations, experiment scripts, analysis tools, and documentation-is publicly available at the project repository:

> **Repository**: `https://github.com/Q-research-team/q-research`

The codebase is organized as follows:

- **`src/`**: Core optimizer implementations (Greedy, RLS, Simulated Annealing, Genetic Algorithm, `CommutationRewriter`, `HybridCommuteRewrite`, Phase-2b template matcher) and circuit family generators.
- **`experiments/`**: Experiment drivers for E01-E24, including configuration files and run scripts.
- **`analysis/`**: Statistical analysis, figure generation, and claim-evidence validation tools.
- **`scripts/`**: Reproducibility pipeline (`reproduce_all.py`) and utility scripts.
- **`tests/`**: Unit tests, including Phase-2b template matcher verification.

The project requires Python 3.12. All dependencies are pinned in `requirements.txt` (pip) and `environment.yml` (conda) to ensure deterministic environment reproduction. A Docker container is provided via the `Dockerfile` at the repository root for containerized execution.

**Release version**: v6.0.0

---

## Competing Interests

The authors declare no competing interests.

---

## Author Contributions

**Author A** conceived the study, designed the experiments, implemented the optimizers, and wrote the manuscript. **Author B** contributed to theoretical analysis and manuscript revision. All authors reviewed and approved the final manuscript.

> **Note**: Author names are placeholders to be finalized upon submission.

---

*Manuscript version 6.0.0*
*Date: 2026-07-11*
