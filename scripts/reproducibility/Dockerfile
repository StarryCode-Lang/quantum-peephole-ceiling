# Q-Research Reproducibility Environment
FROM python:3.11-slim

LABEL maintainer="Q-research Team"
LABEL description="Reproducible environment for quantum circuit optimization phase transition study"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project code
COPY src/ ./src/
COPY experiments/ ./experiments/
COPY scripts/ ./scripts/
COPY paper/ ./paper/
COPY theory/ ./theory/
COPY literature/ ./literature/

# Create data directories
RUN mkdir -p data/raw data/processed figures logs

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Default command
CMD ["python", "experiments/run_all_experiments_v3.py"]
