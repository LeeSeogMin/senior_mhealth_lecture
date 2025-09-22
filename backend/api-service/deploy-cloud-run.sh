#!/bin/bash

# Senior MHealth API Service - Cloud Run Deployment Script
# Chapter 5: Cloud Run Extended Backend

set -e

# Configuration 로드
CONFIG_FILE="../../project.config.json"
if [ -f "$CONFIG_FILE" ]; then
    # Try python3 first, then python
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi

    PROJECT_ID=$($PYTHON_CMD -c "import json; print(json.load(open('$CONFIG_FILE'))['project']['id'], end='')" 2>/dev/null | tr -d '\n\r')
    REGION=$($PYTHON_CMD -c "import json; print(json.load(open('$CONFIG_FILE'))['project']['region'], end='')" 2>/dev/null | tr -d '\n\r')
    SERVICE_NAME=$($PYTHON_CMD -c "import json; print(json.load(open('$CONFIG_FILE'))['services']['apiService']['name'], end='')" 2>/dev/null | tr -d '\n\r')

    # Fallback if any value is empty
    [ -z "$PROJECT_ID" ] && PROJECT_ID="senior-mhealth-472007"
    [ -z "$REGION" ] && REGION="asia-northeast3"
    [ -z "$SERVICE_NAME" ] && SERVICE_NAME="senior-mhealth-api"
    echo "✅ Configuration loaded - Project: ${PROJECT_ID}, Region: ${REGION}"
else
    echo "⚠️ Config file not found, using defaults"
    PROJECT_ID="senior-mhealth-472007"
    REGION="asia-northeast3"
    SERVICE_NAME="senior-mhealth-api"
fi

IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Cloud Run deployment for Senior MHealth API Service${NC}"

# Step 1: Check if gcloud is configured
echo -e "${YELLOW}📋 Checking gcloud configuration...${NC}"
gcloud config set project ${PROJECT_ID}
gcloud config set run/region ${REGION}

# Step 2: Enable required APIs
echo -e "${YELLOW}🔧 Enabling required Google Cloud APIs...${NC}"
gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    containerregistry.googleapis.com \
    secretmanager.googleapis.com \
    vpcaccess.googleapis.com

# Step 3: Create service account if it doesn't exist
echo -e "${YELLOW}👤 Setting up service account...${NC}"
SERVICE_ACCOUNT="cloud-run-sa"
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com &>/dev/null; then
    gcloud iam service-accounts create ${SERVICE_ACCOUNT} \
        --display-name="Cloud Run Service Account"
    
    # Grant necessary permissions
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/datastore.user"
    
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/storage.objectViewer"
    
    gcloud projects add-iam-policy-binding ${PROJECT_ID} \
        --member="serviceAccount:${SERVICE_ACCOUNT}@${PROJECT_ID}.iam.gserviceaccount.com" \
        --role="roles/secretmanager.secretAccessor"
fi

# Step 4: Build the Docker image locally (for testing)
echo -e "${YELLOW}🔨 Building Docker image locally...${NC}"
docker build -t ${IMAGE_NAME}:local -f Dockerfile.prod .

# Step 5: Test the image locally (skip for cloud deployment)
echo -e "${YELLOW}🧪 Skipping local test, proceeding to cloud deployment...${NC}"

# Step 6: Submit to Cloud Build
echo -e "${YELLOW}☁️ Submitting to Cloud Build...${NC}"
gcloud builds submit \
    --config cloudbuild-prod.yaml \
    --substitutions=COMMIT_SHA=$(git rev-parse HEAD)

# Step 7: Verify deployment
echo -e "${YELLOW}✅ Verifying deployment...${NC}"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --region=${REGION} \
    --format='value(status.url)')

if [ -z "$SERVICE_URL" ]; then
    echo -e "${RED}❌ Failed to get service URL${NC}"
    exit 1
fi

echo -e "${GREEN}🎉 Deployment successful!${NC}"
echo -e "${GREEN}Service URL: ${SERVICE_URL}${NC}"

# Step 8: Run smoke tests
echo -e "${YELLOW}🔥 Running smoke tests...${NC}"

# Test health endpoint
if curl -f ${SERVICE_URL}/health &>/dev/null; then
    echo -e "${GREEN}✅ Health check passed${NC}"
else
    echo -e "${RED}❌ Health check failed${NC}"
    exit 1
fi

# Test API docs
if curl -f ${SERVICE_URL}/docs &>/dev/null; then
    echo -e "${GREEN}✅ API docs available${NC}"
else
    echo -e "${YELLOW}⚠️ API docs not available (might be disabled in production)${NC}"
fi

echo -e "${GREEN}🚀 Cloud Run deployment complete!${NC}"
echo -e "${GREEN}Service details:${NC}"
echo -e "  URL: ${SERVICE_URL}"
echo -e "  Region: ${REGION}"
echo -e "  Project: ${PROJECT_ID}"
echo -e "  Service: ${SERVICE_NAME}"

# Step 9: Set up monitoring (optional)
echo -e "${YELLOW}📊 Setting up monitoring alerts...${NC}"
gcloud alpha monitoring policies create \
    --notification-channels=projects/${PROJECT_ID}/notificationChannels/basic \
    --display-name="${SERVICE_NAME} High Latency" \
    --condition-display-name="Response latency > 1s" \
    --condition-threshold-value=1000 \
    --condition-threshold-duration=60s \
    --condition-metric-filter="resource.type=\"cloud_run_revision\" AND resource.labels.service_name=\"${SERVICE_NAME}\" AND metric.type=\"run.googleapis.com/request_latencies\"" \
    2>/dev/null || echo "Monitoring policy already exists or requires manual setup"

echo -e "${GREEN}✨ Deployment pipeline complete!${NC}"