# =============================================================================
# Q-Research Reproducibility Dockerfile
# Quantum Circuit Peephole Optimization Project
# =============================================================================
# Build:  docker build -t q-research:latest .
# Run:    docker run --rm -it q-research:latest
# Shell:  docker run --rm -it q-research:latest /bin/bash
# Tests:  docker run --rm q-research:latest python tests/test_core.py
# Verify: canonical CSV verification requires mounting/copying data/ into the image
# =============================================================================

FROM continuumio/miniconda3:24.5.0-0

LABEL maintainer="Q-Research Project"
LABEL description="Quantum Circuit Peephole Optimization - Reproducible Research Environment"
LABEL org.opencontainers.image.source="https://github.com/q-research/q-research"

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    MPLBACKEND=Agg \
    CONDA_ENV_NAME=q-research

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create working directory
WORKDIR /app

# Copy environment specification first (for layer caching)
COPY environment.yml requirements.txt ./

# Create conda environment from environment.yml
RUN conda env create -f environment.yml && \
    conda clean -afy && \
    pip cache purge

# Activate the conda environment
SHELL ["conda", "run", "-n", "q-research", "/bin/bash", "-c"]

# Copy project files
COPY src/ src/
COPY tests/ tests/
COPY experiments/ experiments/
COPY analysis/ analysis/
COPY scripts/ scripts/
COPY release/ release/
# Only copy data documentation; canonical CSV verification requires mounting/copying data/
COPY data/DATA_CANONICAL.md data/
COPY docs/ docs/
COPY README.md LICENSE PROJECT_SUMMARY.md ./

# Verify installation
RUN python -c "import qiskit; import numpy; import pandas; import scipy; \
    print(f'Qiskit: {qiskit.__version__}'); \
    print(f'NumPy: {numpy.__version__}'); \
    print(f'Pandas: {pandas.__version__}'); \
    print(f'SciPy: {scipy.__version__}')"

# Default command: run test suite
CMD ["conda", "run", "-n", "q-research", "python", "tests/test_core.py"]
