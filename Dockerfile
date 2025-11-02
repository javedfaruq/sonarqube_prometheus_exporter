FROM python:3.11-slim

LABEL maintainer="your-email@company.com"
LABEL description="SonarQube Prometheus Exporter for Enterprise 2025"

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash exporter && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY exporter/ ./exporter/

# Change ownership to non-root user
RUN chown -R exporter:exporter /app

# Switch to non-root user
USER exporter

# Expose metrics port
EXPOSE 8198

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8198/metrics || exit 1

# Run exporter
CMD ["python", "-m", "exporter.main"]
