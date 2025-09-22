#!/bin/bash
# Python Virtual Environment Setup Script for AI Analysis Service with SincNet (Linux/macOS)
# This script sets up a Python virtual environment for production with SincNet support

echo "🔧 Setting up Production Python virtual environment with SincNet support"

# Check Python version
python_version=$(python3 --version 2>&1)
echo "📌 Python version: $python_version"

# Create virtual environment
echo "📦 Creating virtual environment..."
python3 -m venv venv_production

# Activate virtual environment
echo "🔄 Activating virtual environment..."
source ./venv_production/bin/activate

# Upgrade pip
echo "⬆️ Upgrading pip..."
python -m pip install --upgrade pip

# Install core dependencies
echo "📥 Installing core dependencies..."
if [ -f "ai-service/requirements.txt" ]; then
    pip install -r ai-service/requirements.txt
fi

# Install SincNet specific dependencies
echo "📥 Installing SincNet dependencies..."
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install librosa
pip install pydub
pip install google-cloud-storage
pip install google-cloud-firestore
pip install google-cloud-speech

# Install additional development dependencies
echo "📥 Installing development dependencies..."
pip install pytest pytest-asyncio black flake8 mypy

# Install RAG dependencies
echo "📥 Installing RAG dependencies..."
pip install chromadb langchain faiss-cpu sentence-transformers

# Setup FFmpeg
echo "🎵 Setting up FFmpeg for audio processing..."
if command -v ffmpeg >/dev/null 2>&1; then
    echo "✅ FFmpeg already installed"
    ffmpeg -version | head -n 1
else
    echo "⚠️  FFmpeg not found. Installing..."
    if command -v apt-get >/dev/null 2>&1; then
        # Ubuntu/Debian
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    elif command -v yum >/dev/null 2>&1; then
        # CentOS/RHEL
        sudo yum install -y ffmpeg
    elif command -v brew >/dev/null 2>&1; then
        # macOS
        brew install ffmpeg
    else
        echo "⚠️  Please install FFmpeg manually for your system"
        echo "   Ubuntu/Debian: sudo apt-get install ffmpeg"
        echo "   CentOS/RHEL: sudo yum install ffmpeg"
        echo "   macOS: brew install ffmpeg"
    fi
fi

# Create .env file if not exists
if [ ! -f ".env" ]; then
    echo "📝 Creating .env file..."
    cat > .env << 'EOF'
# Environment Configuration
GOOGLE_CLOUD_PROJECT=senior-mhealth-472007
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
USE_RAG=false
ENVIRONMENT=production
PYTHONUNBUFFERED=1
EOF
fi

# Create SincNet model directory
echo "📂 Creating SincNet model directory..."
model_dir="./libraries/voice_analysis/analysis/sincnet/models"
mkdir -p "$model_dir"

echo "✅ Production virtual environment setup complete!"
echo ""
echo "📌 To activate the virtual environment:"
echo "   source ./venv_production/bin/activate"
echo ""
echo "📌 SincNet models location:"
echo "   $model_dir"
echo ""
echo "📌 To test SincNet integration:"
echo "   python -c \"from libraries.voice_analysis.analysis.core.sincnet_analysis import SincNetAnalyzer; print('SincNet OK')\""