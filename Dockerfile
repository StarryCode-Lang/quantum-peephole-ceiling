# Pinned base image: 26.5.3-1 is the current stable miniconda3 tag as of
# 2026-07-20 (Docker Hub `latest` aliases 26.5.3, last_updated 2026-07-08).
# Pinning avoids silent base-image drift that `latest` would introduce.
FROM continuumio/miniconda3:26.5.3-1

WORKDIR /app

# Dependency layer first: copy only the environment spec and create the
# conda env so this layer is cached unless dependencies change.
COPY environment.yml .
RUN conda env create -f environment.yml && conda clean -afy

# Code and data layer after dependencies.
COPY src/ ./src/
COPY experiments/ ./experiments/
COPY analysis/ ./analysis/
COPY scripts/ ./scripts/
COPY tests/ ./tests/
COPY data/ ./data/
COPY docs/ ./docs/
COPY release/ ./release/
COPY requirements.txt requirements-lock.txt README.md environment.yml ./

# Activate conda env by default
SHELL ["conda", "run", "-n", "q-research", "/bin/bash", "-c"]

# Default: verify canonical data integrity against release/release_manifest.json
CMD ["conda", "run", "-n", "q-research", "python", "scripts/reproduce_all.py", "--verify"]
