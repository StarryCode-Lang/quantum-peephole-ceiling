FROM continuumio/miniconda3:latest

WORKDIR /app

# Copy environment file and create conda env
COPY environment.yml .
RUN conda env create -f environment.yml && conda clean -afy

# Copy source code
COPY src/ ./src/
COPY experiments/ ./experiments/
COPY analysis/ ./analysis/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY data/ ./data/
COPY docs/ ./docs/
COPY requirements.txt README.md environment.yml ./

# Activate conda env by default
SHELL ["conda", "run", "-n", "q-research", "/bin/bash", "-c"]

# Run tests by default
CMD ["conda", "run", "-n", "q-research", "python", "scripts/reproduce_all.py", "--verify"]
