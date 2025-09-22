#!/bin/bash
set -e

echo "Starting AI Service..."

# Note: SincNet models are not currently used in production

# Start the service with uvicorn directly for debugging
exec uvicorn app.main:app \
    --host 0.0.0.0 \
    --port ${PORT:-8080} \
    --workers ${WORKERS:-1} \
    --log-level ${LOG_LEVEL:-info}