#!/bin/bash

# Senior MHealth API Service - Fixed Deployment Script
# Builds from root to access serviceAccountKey.json

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting API Service deployment with root serviceAccountKey.json${NC}"

# Go to root directory
cd ../..

# Configuration
PROJECT_ID="senior-mhealth-472007"
REGION="asia-northeast3"
SERVICE_NAME="senior-mhealth-api"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
TAG="fixed4"

echo -e "${YELLOW}📋 Using configuration:${NC}"
echo "  Project: ${PROJECT_ID}"
echo "  Region: ${REGION}"
echo "  Service: ${SERVICE_NAME}"
echo "  Tag: ${TAG}"

# Check if serviceAccountKey.json exists in root
if [ ! -f "serviceAccountKey.json" ]; then
    echo -e "${RED}❌ serviceAccountKey.json not found in root directory${NC}"
    exit 1
fi

echo -e "${GREEN}✅ Found serviceAccountKey.json in root directory${NC}"

# Create a modified Dockerfile that works from root context
cat > Dockerfile.api-fixed << 'EOF'
# Senior MHealth API Service - Fixed Multi-Stage Build
FROM python:3.11-slim as builder

WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY backend/api-service/requirements-prod.txt requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

# Stage 2: Runtime
FROM python:3.11-slim

# Create non-root user for security
RUN useradd -m -u 1000 appuser && \
    mkdir -p /app && \
    chown -R appuser:appuser /app

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy Python packages from builder
COPY --from=builder --chown=appuser:appuser /root/.local /home/appuser/.local

# Copy application code
COPY --chown=appuser:appuser backend/api-service/app/ ./app/
COPY --chown=appuser:appuser backend/api-service/pytest.ini ./

# Copy service account key from root folder
COPY --chown=appuser:appuser serviceAccountKey.json /app/serviceAccountKey.json

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/home/appuser/.local/bin:$PATH \
    PORT=8080 \
    ENVIRONMENT=production

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Expose port
EXPOSE 8080

# Run with optimized settings
CMD ["python", "-m", "uvicorn", "app.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8080", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--access-log", \
     "--log-level", "info"]
EOF

echo -e "${YELLOW}🔨 Building Docker image from root context...${NC}"
docker build -t ${IMAGE_NAME}:${TAG} -f Dockerfile.api-fixed .

echo -e "${YELLOW}📤 Pushing image to Container Registry...${NC}"
docker push ${IMAGE_NAME}:${TAG}

echo -e "${YELLOW}🚀 Deploying to Cloud Run with min-instances=1...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:${TAG} \
    --region ${REGION} \
    --platform managed \
    --allow-unauthenticated \
    --port 8080 \
    --memory 1Gi \
    --cpu 1 \
    --min-instances 1 \
    --max-instances 10 \
    --timeout 60 \
    --service-account cloud-run-sa@${PROJECT_ID}.iam.gserviceaccount.com

# Get service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --format='value(status.url)')

echo -e "${GREEN}🎉 Deployment successful!${NC}"
echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"

# Clean up temporary Dockerfile
rm -f Dockerfile.api-fixed

# Test the deployment
echo -e "${YELLOW}🧪 Testing deployment...${NC}"
curl -f ${SERVICE_URL}/health && echo -e "\n${GREEN}✅ Health check passed${NC}" || echo -e "\n${RED}❌ Health check failed${NC}"