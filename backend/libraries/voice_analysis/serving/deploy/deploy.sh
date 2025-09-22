#!/bin/bash

# Cloud Run Deployment Script
# Usage: ./deploy.sh [dev|staging|prod] [cpu|gpu]

set -e

# Configuration
PROJECT_ID=${PROJECT_ID:-"senior-mhealth-2025"}
REGION=${REGION:-"asia-northeast3"}
SERVICE_NAME="voice-analysis-service"
IMAGE_REGISTRY="${REGION}-docker.pkg.dev"
REPOSITORY="ml-models"

# Parse arguments
ENVIRONMENT=${1:-dev}
COMPUTE_TYPE=${2:-cpu}

# Set environment-specific configurations
case $ENVIRONMENT in
    dev)
        MIN_INSTANCES=0
        MAX_INSTANCES=2
        MEMORY="2Gi"
        CPU_CORES=1
        CONCURRENCY=10
        ;;
    staging)
        MIN_INSTANCES=0
        MAX_INSTANCES=5
        MEMORY="4Gi"
        CPU_CORES=2
        CONCURRENCY=20
        ;;
    prod)
        MIN_INSTANCES=1
        MAX_INSTANCES=10
        MEMORY="8Gi"
        CPU_CORES=4
        CONCURRENCY=50
        ;;
    *)
        echo "Invalid environment: $ENVIRONMENT"
        echo "Usage: $0 [dev|staging|prod] [cpu|gpu]"
        exit 1
        ;;
esac

# Select Dockerfile based on compute type
if [ "$COMPUTE_TYPE" = "gpu" ]; then
    DOCKERFILE="Dockerfile.gpu"
    ACCELERATOR="--gpu=1"
    ACCELERATOR_TYPE="--gpu-type=nvidia-l4"
    SERVICE_NAME="${SERVICE_NAME}-gpu"
else
    DOCKERFILE="Dockerfile"
    ACCELERATOR=""
    ACCELERATOR_TYPE=""
fi

# Image name with tag
IMAGE_NAME="${IMAGE_REGISTRY}/${PROJECT_ID}/${REPOSITORY}/${SERVICE_NAME}"
IMAGE_TAG="${ENVIRONMENT}-$(date +%Y%m%d-%H%M%S)"
FULL_IMAGE="${IMAGE_NAME}:${IMAGE_TAG}"

echo "========================================="
echo "Deploying Voice Analysis Service"
echo "========================================="
echo "Environment: ${ENVIRONMENT}"
echo "Compute Type: ${COMPUTE_TYPE}"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Image: ${FULL_IMAGE}"
echo "========================================="

# Step 1: Build Docker image
echo "Building Docker image..."
docker build \
    --platform linux/amd64 \
    --build-arg MODEL_VERSION="${IMAGE_TAG}" \
    --build-arg BUILD_DATE="$(date -u +'%Y-%m-%dT%H:%M:%SZ')" \
    -f "../${DOCKERFILE}" \
    -t "${FULL_IMAGE}" \
    ../

# Step 2: Push to Artifact Registry
echo "Pushing image to Artifact Registry..."
docker push "${FULL_IMAGE}"

# Also tag as latest for this environment
docker tag "${FULL_IMAGE}" "${IMAGE_NAME}:${ENVIRONMENT}-latest"
docker push "${IMAGE_NAME}:${ENVIRONMENT}-latest"

# Step 3: Deploy to Cloud Run
echo "Deploying to Cloud Run..."
gcloud run deploy "${SERVICE_NAME}-${ENVIRONMENT}" \
    --image="${FULL_IMAGE}" \
    --platform=managed \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --memory="${MEMORY}" \
    --cpu="${CPU_CORES}" \
    --min-instances="${MIN_INSTANCES}" \
    --max-instances="${MAX_INSTANCES}" \
    --concurrency="${CONCURRENCY}" \
    --timeout=300 \
    --no-allow-unauthenticated \
    ${ACCELERATOR} \
    ${ACCELERATOR_TYPE} \
    --set-env-vars="PROJECT_ID=${PROJECT_ID}" \
    --set-env-vars="ENVIRONMENT=${ENVIRONMENT}" \
    --set-env-vars="MODEL_VERSION=${IMAGE_TAG}" \
    --set-env-vars="GCS_BUCKET=senior-mhealth-models-${ENVIRONMENT}" \
    --set-env-vars="ENABLE_METRICS=true" \
    --set-env-vars="ENABLE_TRACING=true" \
    --set-env-vars="LOG_LEVEL=INFO" \
    --service-account="voice-analysis-sa@${PROJECT_ID}.iam.gserviceaccount.com" \
    --labels="environment=${ENVIRONMENT},version=${IMAGE_TAG},team=ai"

# Step 4: Get service URL
SERVICE_URL=$(gcloud run services describe "${SERVICE_NAME}-${ENVIRONMENT}" \
    --platform=managed \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --format="value(status.url)")

echo "========================================="
echo "Deployment Complete!"
echo "Service URL: ${SERVICE_URL}"
echo "========================================="

# Step 5: Health check
echo "Running health check..."
if command -v curl &> /dev/null; then
    # Get ID token for authentication
    ID_TOKEN=$(gcloud auth print-identity-token)
    
    # Make health check request
    HEALTH_RESPONSE=$(curl -s -H "Authorization: Bearer ${ID_TOKEN}" "${SERVICE_URL}/health")
    echo "Health check response:"
    echo "${HEALTH_RESPONSE}" | python -m json.tool
else
    echo "curl not found, skipping health check"
fi

# Step 6: Update traffic (optional - for canary deployments)
if [ "$ENVIRONMENT" = "prod" ]; then
    echo "Setting up traffic split for canary deployment..."
    gcloud run services update-traffic "${SERVICE_NAME}-${ENVIRONMENT}" \
        --to-tags="${IMAGE_TAG}=10" \
        --region="${REGION}" \
        --project="${PROJECT_ID}"
    
    echo "Canary deployment set to 10% traffic"
    echo "To promote to 100%, run:"
    echo "gcloud run services update-traffic ${SERVICE_NAME}-${ENVIRONMENT} --to-latest --region=${REGION}"
fi

echo "Deployment script completed successfully!"