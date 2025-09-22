#!/bin/bash

# Senior MHealth - OFFICIAL Full Deployment Script
# This is the ONLY script you should use for full deployment

set -e

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🚀 Senior MHealth Full Deployment${NC}"
echo -e "${YELLOW}This script deploys all services in the correct order${NC}"

# Check prerequisites
echo -e "\n${YELLOW}📋 Checking prerequisites...${NC}"
if [ ! -f "serviceAccountKey.json" ]; then
    echo -e "${RED}❌ serviceAccountKey.json not found in root directory${NC}"
    exit 1
fi

# 1. Deploy AI Service
echo -e "\n${GREEN}1️⃣ Deploying AI Service...${NC}"
cd backend/ai-service
if [ -f "deploy.sh" ]; then
    ./deploy.sh
else
    echo -e "${YELLOW}⚠️ AI service deploy.sh not found, skipping${NC}"
fi
cd ../..

# 2. Deploy API Service
echo -e "\n${GREEN}2️⃣ Deploying API Service...${NC}"
cd backend/api-service
if [ -f "deploy-api-fixed.sh" ]; then
    ./deploy-api-fixed.sh
else
    echo -e "${YELLOW}⚠️ API service deploy script not found, skipping${NC}"
fi
cd ../..

# 3. Deploy Firebase Functions
echo -e "\n${GREEN}3️⃣ Deploying Firebase Functions...${NC}"
cd backend/firebase-functions
npm install
npm run deploy
cd ../..

# 4. Deploy Frontend to Vercel
echo -e "\n${GREEN}4️⃣ Deploying Frontend to Vercel...${NC}"
cd frontend/web
if [ -f "deploy-vercel.sh" ]; then
    ./deploy-vercel.sh
else
    echo -e "${YELLOW}⚠️ Vercel deploy script not found${NC}"
fi
cd ../..

# 5. Verify deployments
echo -e "\n${GREEN}✅ Verifying deployments...${NC}"

echo -e "${YELLOW}AI Service:${NC}"
curl -s https://senior-mhealth-ai-du6z6zbl2a-du.a.run.app/health | head -1

echo -e "${YELLOW}API Service:${NC}"
curl -s https://senior-mhealth-api-1054806937473.asia-northeast3.run.app/health | head -1

echo -e "${YELLOW}Frontend:${NC}"
curl -s https://senior-mhealth.vercel.app | grep -o '<title>[^<]*</title>' | head -1

echo -e "\n${GREEN}🎉 Full deployment complete!${NC}"
echo -e "${YELLOW}Service URLs:${NC}"
echo "  AI Service:  https://senior-mhealth-ai-du6z6zbl2a-du.a.run.app"
echo "  API Service: https://senior-mhealth-api-1054806937473.asia-northeast3.run.app"
echo "  Frontend:    https://senior-mhealth.vercel.app"

echo -e "\n${YELLOW}📖 For individual deployments, see: docs/DEPLOYMENT_GUIDE.md${NC}"