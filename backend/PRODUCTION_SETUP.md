# Production Environment Setup for SincNet Integration

This document describes how to set up the production environment for the AI Analysis Service with SincNet neural network support.

## Prerequisites

- Python 3.8+ (3.11+ recommended)
- Git
- FFmpeg (for audio processing)
- Google Cloud Service Account Key

## Quick Setup

### Windows
```powershell
cd C:\Senior_MHealth\backend
.\setup_production_venv.ps1
```

### Linux/macOS
```bash
cd /path/to/Senior_MHealth/backend
./setup_production_venv.sh
```

## Manual Setup

### 1. Create Virtual Environment

```bash
# Create virtual environment
python -m venv venv_production

# Activate virtual environment
# Windows:
.\venv_production\Scripts\activate
# Linux/macOS:
source ./venv_production/bin/activate
```

### 2. Install Dependencies

```bash
# Upgrade pip
python -m pip install --upgrade pip

# Install core dependencies
pip install -r ai-service/requirements.txt  # if exists

# Install SincNet specific dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip install librosa pydub
pip install google-cloud-storage google-cloud-firestore google-cloud-speech
```

### 3. Setup FFmpeg

#### Windows
1. Download FFmpeg from https://ffmpeg.org/download.html
2. Extract to `C:\Senior_MHealth\backend\ffmpeg`
3. Add `C:\Senior_MHealth\backend\ffmpeg\bin` to PATH

#### Linux/macOS
```bash
# Ubuntu/Debian
sudo apt-get install ffmpeg

# CentOS/RHEL  
sudo yum install ffmpeg

# macOS
brew install ffmpeg
```

### 4. Setup SincNet Models

SincNet models are automatically downloaded and cached in:
```
C:\Senior_MHealth\backend\libraries\voice_analysis\analysis\sincnet\models\
```

Models included:
- `dep_model_10500_raw.pkl` - Depression detection model
- `insom_model_38800_raw.pkl` - Insomnia detection model

### 5. Environment Configuration

Create `.env` file in the backend directory:
```env
# Environment Configuration
GOOGLE_CLOUD_PROJECT=senior-mhealth-472007
OPENAI_API_KEY=your_openai_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here  
USE_RAG=false
ENVIRONMENT=production
PYTHONUNBUFFERED=1
```

### 6. Service Account Setup

Place your Google Cloud Service Account key at:
```
C:\Senior_MHealth\serviceAccountKey.json
```

## Testing SincNet Integration

### Quick Test
```python
python -c "from libraries.voice_analysis.analysis.core.sincnet_analysis import SincNetAnalyzer; print('SincNet OK')"
```

### Full Pipeline Test
```python
import asyncio
from libraries.voice_analysis.analysis.pipeline.main_pipeline import SeniorMentalHealthPipeline

async def test():
    pipeline = SeniorMentalHealthPipeline()
    result = await pipeline.analyze(
        audio_path="path/to/audio.mp3",
        user_id="test_user",
        user_info={'call_id': 'test_call', 'senior_id': 'test_senior'}
    )
    print("✅ Pipeline test successful!")

asyncio.run(test())
```

## Architecture Overview

### SincNet Components
- **Original SincNet Model**: Complete implementation with 200ms windows
- **Audio Processor**: Handles MP3/M4A/WAV with FFmpeg fallback
- **Model Manager**: Firebase Storage integration with local caching

### Key Features
- **Real Audio Support**: M4A, MP3, WAV processing
- **Original Architecture**: 80 sinc filters, 3-layer CNN [80,60,60], 3-layer DNN [2048,2048,2048]
- **Production Ready**: Error handling, logging, caching
- **Cloud Integration**: Firebase Storage, Google Cloud Speech

## Troubleshooting

### Common Issues

1. **PyTorch Installation**
   ```bash
   # If CPU-only version needed
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
   ```

2. **FFmpeg Not Found**
   - Windows: Ensure ffmpeg.exe is in PATH or in `C:\Senior_MHealth\backend\ffmpeg\bin`
   - Linux/macOS: Install via package manager

3. **Google Cloud Authentication**
   - Ensure service account key is properly placed
   - Check file permissions and JSON validity

4. **Model Loading Issues**
   - Models are cached locally on first use
   - Check internet connection for initial download
   - Verify Firebase Storage credentials

### Performance Optimization

- **Memory Usage**: ~167MB for both models loaded
- **Processing Time**: ~2-3 seconds per minute of audio  
- **Recommended**: 4GB+ RAM, multi-core CPU

## Production Deployment

### Environment Variables
```env
ENVIRONMENT=production
PYTHONUNBUFFERED=1
GOOGLE_CLOUD_PROJECT=senior-mhealth-472007
```

### Monitoring
- SincNet analysis logs: Level INFO
- Model loading: Check Firebase Storage connectivity
- Audio processing: Monitor FFmpeg availability

### Scaling Considerations
- Models loaded once per process
- Concurrent analysis supported
- Consider memory limits for multiple instances