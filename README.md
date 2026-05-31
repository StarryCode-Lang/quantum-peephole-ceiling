# Q-Research: No Phase Transition in Quantum Circuit Optimization

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Qiskit 2.4+](https://img.shields.io/badge/Qiskit-2.4.1-purple.svg)](https://qiskit.org/)

**A systematic 25,560-trial experimental study refuting the phase transition hypothesis for quantum circuit optimization, with key findings on greedy dominance, entanglement sweet spots, and industrial baseline comparison.**

## Key Findings

1. **No phase transition.** Optimization success decays **smoothly and exponentially** $P(d) = P_0 e^{-d/d_0}$ with $d_0 = 19.0 \pm 4.0$, rejecting the phase transition hypothesis at high confidence ($\Delta \mathrm{AIC} > 10$, $R^2 = 0.86$). Finite-size scaling confirms no systematic $d_0$ scaling with qubit count ($R^2 = 0.085$, $p = 0.52$).

2. **Greedy beats stochastic by 3 orders of magnitude.** Deterministic greedy cancellation dominates Simulated Annealing, Genetic Algorithms, and Random Local Search in both quality and speed ($p < 10^{-17}$, Wilcoxon). Greedy: 20% success, 3.5 ms. SA/GA: 0% success, 1.4–1.9 s.

3. **Entanglement sweet spot.** Circuits at intermediate entanglement density ($\rho \in [0.3, 0.5]$) are maximally optimizable (peak 29.4%). Both under- and over-entangled circuits are harder to optimize.

4. **Power-law gate redundancy.** Achievable gate reduction scales as $\Delta G \propto n^{0.281}$ (95% CI: $[0.254, 0.308]$), meaning larger circuits have proportionally more redundant gates.

5. **Industrial baseline.** Qiskit transpiler (L2) achieves **55% gate reduction with 100% success** vs. our prototype greedy's 12.0%/6.1%, validating that deterministic peephole optimization is the correct paradigm.

## Project Structure

```
Q-research/
├── README.md                     # This file
├── src/
│   ├── circuits/generator_v2.py  # Circuit generation (v2.x)
│   ├── optimisation/
│   │   ├── optimizers_v2.py      # Greedy, SA, GA, RLS optimizers
│   │   └── create_optimizer.py   # Optimizer factory
│   └── analysis/
│       ├── analysis_v2.py        # Statistical analysis pipeline
│       └── statistical_rigor.py  # AIC/BIC, power analysis, multiple testing
├── experiments/
│   ├── run_all_experiments_v3.py # E1–E5 experiment suite
│   └── run_e6.py                 # Qiskit transpiler baseline (E6)
├── scripts/
│   ├── generate_publication_figures.py  # Publication-quality figures
│   ├── verify_all.py                    # End-to-end verification
│   ├── reproducibility/                 # Conda/Docker environment
│   └── snapshot_environment.py          # Reproducibility snapshot
├── docs/
│   ├── manuscript_v4.md          # Target: Nature Communications / PRX
│   └── comprehensive_analysis_report_v2.md
├── data/
│   ├── raw/                      # Raw CSV outputs (E1–E6)
│   └── processed/                # Analyzed statistics (JSON)
├── figures/
│   └── final/                    # Publication-ready figures
└── archive/                      # Superseded code (manuscripts v1–v3, v2 code)
```

## Quick Start

### Installation

```bash
# Using conda (recommended)
conda env create -f scripts/reproducibility/environment.yml
conda activate q-research

# Using pip
pip install -r scripts/reproducibility/requirements.txt
```

### Run Experiments

```bash
# All five core experiments (E1–E5)
python experiments/run_all_experiments_v3.py

# Qiskit transpiler baseline (E6)
python experiments/run_e6.py

# End-to-end verification
python scripts/verify_all.py
```

### Individual Experiment API

```python
from experiments.run_all_experiments_v3 import (
    Experiment1, Experiment2, Experiment3,
    Experiment4, Experiment5, ExperimentConfig
)
config = ExperimentConfig()
df = Experiment1(config).run()
```

## Experiments Summary

| Exp | Topic | Parameters | Trials | Purpose |
|-----|-------|-----------|--------|---------|
| E1 | Depth Sweep | $n=5$, $d \in [1,50]$ | 5,000 | Test phase transition hypothesis |
| E2 | Entanglement Density | $n=6$, $d=20$, $\rho \in [0,1]$ | 1,260 | Find optimal entanglement regime |
| E3 | Finite-Size Scaling | $n \in [3,10]$, $d \in [1,30]$ | 12,000 | Extract scaling exponents |
| E4 | Algorithm Comparison | $n=5$, $d=15$, 4 optimizers | 400 | Benchmark optimization strategies |
| E5 | Landscape Characterization | $n=5$, $d \in [3,20]$ | 6,000 | Map optimization topography |
| E6 | Industrial Baseline | $n=5$, $d \in [5,30]$, Qiskit L0–L3 | 900 | Contextualize vs. Qiskit transpiler |

**Total: 25,560 independent trials**

## Core Results

### Exponential Decay (E1)
$P_{\text{success}}(d) = P_0 e^{-d/d_0}$ with $d_0 = 19.0 \pm 4.0$, $R^2 = 0.86$  
Sigmoid model: fails to converge reliably ($\Delta \mathrm{AIC} > 10$)

### Algorithm Ranking (E4, d=15)
| Algorithm | Success Rate | Runtime | $p$ vs. greedy |
|:---|---:|---:|:---:|
| **Greedy** | **20%** | **3.5 ms** | — |
| Random Local Search | 0% | 7.3 ms | $p < 0.001$ |
| Simulated Annealing | 0% | 1.41 s | $p < 10^{-17}$ |
| Genetic Algorithm | 0% | 1.86 s | $p < 10^{-17}$ |

### Qiskit Baseline (E6, d ∈ [5,30])
| Optimizer | Mean Reduction | Success Rate | Fidelity |
|:---|---:|---:|---:|
| Greedy (ours) | 12.0% | 6.1% | 0.153 |
| Qiskit L2 | **55.0%** | **100%** | **1.000** |

## Manuscript

The manuscript `docs/manuscript_v4.md` is formatted for submission to *Nature Communications* or *Physical Review X*, including:
- Complete abstract, introduction, results, theory, discussion, and methods sections
- Quantitative theory-experiment comparison table (Table 4)
- Industrial baseline comparison (Section 2.7)
- 26 references across physics, computer science, and quantum information

## Reproducibility

- Pinned Python environment via `conda env create` / `requirements.txt`
- Docker container: `scripts/reproducibility/Dockerfile`
- Environment snapshot JSON with SHA-256 source hashes
- Fixed random seeds recorded in raw data
- All raw data (CSV) and processed statistics (JSON) committed

## Citation

```bibtex
@article{qresearch2026,
  title={No Phase Transition: Exponential Decay, Greedy Dominance, and 
         Entanglement Sweet Spots in Quantum Circuit Optimization},
  author={Q-research Team},
  journal={Nature Communications / Physical Review X},
  year={2026}
}
```

## License

MIT License — see LICENSE file for details.