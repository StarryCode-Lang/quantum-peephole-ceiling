# Multi-stage Dockerfile for Q-research reproducibility.
# Builds a minimal Python 3.12 environment with all project dependencies
# pinned in requirements-lock.txt.

FROM python:3.12-slim AS base

WORKDIR /app

# Install build dependencies for compiled packages (numpy, scipy, pytket, etc.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    g++ \
    cmake \
    libopenblas-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency lock file and install exact pinned versions.
COPY requirements-lock.txt .
RUN pip install --no-cache-dir -r requirements-lock.txt

# Copy project source.
COPY . .

# Run a smoke test to verify the installation.
RUN python tests/test_core.py TestBaseOptimizer TestCommutation TestPhase2bTemplateMatcher

# Default entrypoint: run the full test suite.
CMD ["python", "tests/test_core.py"]
