#!/bin/bash

# Local Development Script for Senior MHealth API Service
# Chapter 5: Cloud Run Extended Backend

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}🚀 Starting Senior MHealth API Service (Local Development)${NC}"

# Step 1: Check Python version
echo -e "${YELLOW}🐍 Checking Python version...${NC}"
python_version=$(python3 --version 2>&1 | grep -oE '[0-9]+\.[0-9]+')
required_version="3.11"

if [ "$(printf '%s\n' "$required_version" "$python_version" | sort -V | head -n1)" != "$required_version" ]; then 
    echo -e "${RED}❌ Python $required_version or higher is required (found $python_version)${NC}"
    exit 1
fi
echo -e "${GREEN}✅ Python $python_version${NC}"

# Step 2: Set up virtual environment
echo -e "${YELLOW}📦 Setting up virtual environment...${NC}"
if [ ! -d "venv" ]; then
    python3 -m venv venv
    echo -e "${GREEN}✅ Virtual environment created${NC}"
else
    echo -e "${GREEN}✅ Virtual environment already exists${NC}"
fi

# Activate virtual environment
source venv/bin/activate

# Step 3: Install/upgrade dependencies
echo -e "${YELLOW}📥 Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements-prod.txt

# Step 4: Set up environment variables
echo -e "${YELLOW}🔧 Setting up environment variables...${NC}"
if [ ! -f ".env" ]; then
    cp .env.example .env
    echo -e "${YELLOW}⚠️  Please configure .env file with your settings${NC}"
fi

# Export environment variables
export ENVIRONMENT=development
export PORT=8080
export LOG_LEVEL=INFO
export GOOGLE_CLOUD_PROJECT=senior-mhealth-472007

# Step 5: Check Firestore emulator (optional)
echo -e "${YELLOW}🔍 Checking for Firestore emulator...${NC}"
if command -v firebase &> /dev/null; then
    if lsof -Pi :8085 -sTCP:LISTEN -t >/dev/null ; then
        echo -e "${GREEN}✅ Firestore emulator is running${NC}"
        export FIRESTORE_EMULATOR_HOST=localhost:8085
    else
        echo -e "${YELLOW}ℹ️  Firestore emulator not running. Using production Firestore.${NC}"
    fi
else
    echo -e "${YELLOW}ℹ️  Firebase CLI not installed. Using production Firestore.${NC}"
fi

# Step 6: Run database migrations (if needed)
echo -e "${YELLOW}🗄️ Checking database...${NC}"
# python -m app.core.database migrate

# Step 7: Start the application
echo -e "${GREEN}🚀 Starting FastAPI application...${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}📍 API URL: http://localhost:8080${NC}"
echo -e "${GREEN}📚 API Docs: http://localhost:8080/docs${NC}"
echo -e "${GREEN}📊 ReDoc: http://localhost:8080/redoc${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

# Run with auto-reload for development
uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 8080 \
    --reload \
    --reload-dir app \
    --log-level info \
    --access-log