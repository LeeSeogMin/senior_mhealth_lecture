#!/bin/bash

# Python Virtual Environment Setup Script for AI Analysis Service
# This script sets up a Python virtual environment for development

set -e

echo "🔧 Setting up Python virtual environment for AI Analysis Service"

# Check Python version
python_version=$(python --version 2>&1 | awk '{print $2}')
echo "📌 Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python -m venv venv

# Activate virtual environment
echo "🔄 Activating virtual environment..."
if [[ "$OSTYPE" == "msys" ]] || [[ "$OSTYPE" == "win32" ]]; then
    # Windows
    source venv/Scripts/activate
else
    # Linux/Mac
    source venv/bin/activate
fi

# Upgrade pip
echo "⬆️ Upgrading pip..."
pip install --upgrade pip

# Install core dependencies
echo "📥 Installing core dependencies..."
pip install -r ai-service/requirements.txt

# Install additional development dependencies
echo "📥 Installing development dependencies..."
pip install pytest pytest-asyncio black flake8 mypy

# Install RAG dependencies
echo "📥 Installing RAG dependencies..."
pip install chromadb langchain faiss-cpu sentence-transformers

# Create .env file if not exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << EOL
# Environment Configuration
GOOGLE_CLOUD_PROJECT=senior-mhealth-472007
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
USE_RAG=false
ENVIRONMENT=development
PYTHONUNBUFFERED=1
EOL
fi

echo "✅ Virtual environment setup complete!"
echo ""
echo "📌 To activate the virtual environment:"
echo "   source venv/Scripts/activate  (Windows)"
echo "   source venv/bin/activate      (Linux/Mac)"
echo ""
echo "📌 To run the AI service locally:"
echo "   cd ai-service"
echo "   python -m uvicorn app.main:app --reload --port 8081"
echo ""
echo "📌 To run with Docker:"
echo "   docker-compose -f docker-compose.ai.yml up"