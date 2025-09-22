# Senior MHealth AI Analysis Service
# Optimized for AI/ML workloads with GPU support option

FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies for AI/ML libraries
RUN apt-get update && apt-get install -y \
    gcc g++ \
    build-essential \
    libsndfile1-dev \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --user --no-cache-dir -r requirements.txt

# Runtime stage
FROM python:3.11-slim

# Create non-root user
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser app/ ./app/

# Copy SincNet model files to expected location
COPY --chown=appuser:appuser backend/libraries/voice_analysis/analysis/sincnet/models/ ./models/sincnet/

# Create additional models directory if needed
RUN mkdir -p ./models/

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/appuser/.local/bin:$PATH \
    PORT=8081 \
    SERVICE_NAME=ai-service

USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8081/health || exit 1

EXPOSE 8081

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8081", \
     "--workers", "2", \
     "--log-level", "info"]