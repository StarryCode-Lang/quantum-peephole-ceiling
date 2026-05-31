# Q-research Reproducibility Package

## Quick Start

### Option 1: Using pip
```bash
pip install -r requirements.txt
python experiments/run_all_experiments_v3.py
```

### Option 2: Using conda
```bash
conda env create -f environment.yml
conda activate q-research
python experiments/run_all_experiments_v3.py
```

### Option 3: Using Docker
```bash
docker build -t q-research .
docker run -v $(pwd)/data:/app/data q-research
```

## Project Structure
```
Q-research/
├── src/                          # Source code
│   ├── circuits/                 # Circuit generation
│   │   ├── generator_v2.py       # Production generator
│   │   └── generator.py          # Original generator
│   ├── optimisation/             # Optimization algorithms
│   │   ├── optimizers_v2.py      # Production optimizers
│   │   └── optimizers.py         # Original optimizers
│   └── analysis/                 # Analysis tools
│       ├── analysis_v2.py        # Production analysis
│       └── analysis_tools.py     # Original analysis
├── experiments/                  # Experiment scripts
│   ├── run_all_experiments_v3.py # Production runner
│   ├── run_all_experiments_v2.py # Previous version
│   └── core.py                   # Core utilities
├── data/                         # Data directory
│   ├── raw/                      # Raw experimental data
│   └── processed/                # Processed analysis results
├── figures/                      # Generated figures
│   └── final/                    # Publication-ready figures
├── paper/                        # Paper materials
│   ├── manuscript_v3.md          # Latest manuscript
│   └── references.bib            # Bibliography
├── requirements.txt              # Python dependencies
├── environment.yml               # Conda environment
├── Dockerfile                    # Docker configuration
└── README.md                     # This file
```

## Reproducibility Checklist

### Data
- [ ] Raw data archived
- [ ] Processing scripts provided
- [ ] Checksums computed
- [ ] Data dictionary provided

### Code
- [ ] Version controlled (Git)
- [ ] Requirements specified
- [ ] Random seeds documented
- [ ] Docker container available

### Analysis
- [ ] Statistical tests documented
- [ ] Assumptions checked
- [ ] Sensitivity analysis performed
- [ ] Missing data handled

### Environment
- [ ] Python version specified
- [ ] Library versions fixed
- [ ] Hardware documented
- [ ] OS documented

## Hardware Requirements

- **CPU**: Multi-core processor (8+ cores recommended)
- **RAM**: 16 GB minimum, 32 GB recommended
- **Storage**: 10 GB for data and figures
- **OS**: Linux, macOS, or Windows with WSL

## Estimated Runtime

- Experiment 1: ~2 hours
- Experiment 2: ~4 hours
- Experiment 3: ~8 hours
- Experiment 4: ~1 hour
- Experiment 5: ~3 hours
- **Total**: ~18 hours

## Contact

For questions or issues, please contact: [email]

## License

This project is licensed under the MIT License.
