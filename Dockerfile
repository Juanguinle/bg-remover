FROM ubuntu:22.04

# Set metadata
LABEL maintainer="your.email@example.com" \
      version="1.0.0" \
      description="BG Remover - Professional Background Removal Application"

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Security hardening
RUN apt-get update && apt-get upgrade -y && \
    # Install security updates
    apt-get install -y --no-install-recommends \
    unattended-upgrades \
    && unattended-upgrade -d \
    # Install Python and dependencies
    && apt-get install -y --no-install-recommends \
    python3.11 \
    python3.11-dev \
    python3.11-venv \
    python3-pip \
    # System dependencies
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    libgomp1 \
    libgthread-2.0-0 \
    libgtk-3-0 \
    libavcodec58 \
    libavformat58 \
    libswscale5 \
    # Security tools
    ca-certificates \
    curl \
    # Clean up
    && apt-get autoremove -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Create non-root user with specific UID/GID
RUN groupadd -r -g 1001 appuser && \
    useradd -r -u 1001 -g appuser -d /home/appuser -s /bin/bash appuser && \
    mkdir -p /home/appuser && \
    chown -R appuser:appuser /home/appuser

# Set working directory
WORKDIR /app

# Copy requirements and install Python packages
COPY requirements.txt .

# Install Python dependencies
RUN python3.11 -m pip install --upgrade pip setuptools wheel && \
    python3.11 -m pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Install the application
RUN python3.11 -m pip install --no-cache-dir -e .

# Create necessary directories
RUN mkdir -p /app/input /app/output /app/processed /app/logs && \
    chown -R appuser:appuser /app

# Security: Remove package managers and unnecessary tools
RUN apt-get remove -y \
    python3-pip \
    curl \
    && apt-get autoremove -y \
    && apt-get clean

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD python3.11 -m bg_remover.cli.main info > /dev/null 2>&1 || exit 1

# Volumes
VOLUME ["/app/input", "/app/output", "/app/processed", "/app/logs"]

# Default command
CMD ["python3.11", "-m", "bg_remover.cli.main", "monitor", "--input", "/app/input"]