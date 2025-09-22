# Simplified AI Service - Optimized Multi-stage Docker Image
# Stage 1: Build dependencies
FROM python:3.11-slim as builder

WORKDIR /app

# Copy only requirements first for better caching
COPY requirements.txt .

# Install dependencies with no cache and no compile
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

WORKDIR /app

# Create non-root user for security
RUN useradd -m -u 1001 appuser && chown -R appuser:appuser /app

# Copy dependencies from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy only necessary application files
COPY --chown=appuser:appuser app/ ./app/

# Switch to non-root user
USER appuser

# Add user's local bin to PATH
ENV PATH=/home/appuser/.local/bin:$PATH
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD python -c "import httpx; httpx.get('http://localhost:8080/health')" || exit 1

# Run with optimized settings
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1", "--loop", "uvloop", "--no-access-log"]