# Voice Analysis Service - Cloud Deployment

AI model serving infrastructure for Senior_MHealth mental health assessment platform.

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Client App    │────▶│    Cloud Run     │────▶│   Vertex AI     │
│   (Flutter)     │     │  (FastAPI)       │     │   (Optional)    │
└─────────────────┘     └──────────────────┘     └─────────────────┘
                               │                          │
                               ▼                          ▼
                        ┌──────────────┐          ┌──────────────┐
                        │ Cloud Storage│          │ Model Registry│
                        │   (Audio)    │          │   (Models)   │
                        └──────────────┘          └──────────────┘
```

## 📁 Project Structure

```
ai/serving/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI application
│   ├── models.py         # Pydantic models
│   ├── inference.py      # Model inference engine
│   └── config.py         # Configuration management
├── deploy/
│   ├── deploy.sh         # Cloud Run deployment script
│   ├── vertex_ai_deploy.py # Vertex AI deployment
│   └── service.yaml      # Service configuration
├── monitoring/
│   ├── dashboard.json    # Monitoring dashboard
│   └── alerts.yaml       # Alert policies
├── tests/
│   └── test_*.py         # Unit tests
├── Dockerfile           # CPU container
├── Dockerfile.gpu       # GPU container
└── requirements.txt     # Dependencies
```

## 🚀 Quick Start

### Prerequisites

1. **Google Cloud Setup**
```bash
# Install gcloud CLI
curl https://sdk.cloud.google.com | bash

# Authenticate
gcloud auth login
gcloud config set project senior-mhealth-2025

# Enable required APIs
gcloud services enable \
  run.googleapis.com \
  aiplatform.googleapis.com \
  artifactregistry.googleapis.com \
  storage.googleapis.com
```

2. **Create Service Account**
```bash
# Create service account
gcloud iam service-accounts create voice-analysis-sa \
  --display-name="Voice Analysis Service Account"

# Grant permissions
gcloud projects add-iam-policy-binding senior-mhealth-2025 \
  --member="serviceAccount:voice-analysis-sa@senior-mhealth-2025.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

gcloud projects add-iam-policy-binding senior-mhealth-2025 \
  --member="serviceAccount:voice-analysis-sa@senior-mhealth-2025.iam.gserviceaccount.com" \
  --role="roles/storage.objectViewer"
```

3. **Create Artifact Registry**
```bash
gcloud artifacts repositories create ml-models \
  --repository-format=docker \
  --location=asia-northeast3 \
  --description="ML model containers"
```

### Local Development

1. **Setup Environment**
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp .env.example .env
# Edit .env with your configuration
```

2. **Run Locally**
```bash
# Start the service
python -m uvicorn app.main:app --reload --port 8080

# Test the service
curl http://localhost:8080/health
```

3. **Run with Docker**
```bash
# Build image
docker build -t voice-analysis:local .

# Run container
docker run -p 8080:8080 \
  -e PROJECT_ID=senior-mhealth-2025 \
  -e ENVIRONMENT=development \
  voice-analysis:local
```

## 🚢 Deployment

### Deploy to Cloud Run (CPU)

```bash
cd deploy
./deploy.sh prod cpu
```

### Deploy to Cloud Run (GPU)

```bash
cd deploy
./deploy.sh prod gpu
```

### Deploy to Vertex AI

```bash
cd deploy
python vertex_ai_deploy.py \
  --project-id senior-mhealth-2025 \
  --location asia-northeast3 \
  --model-path ../models/voice_analysis.pt \
  --model-name voice-analysis-model \
  --endpoint-name voice-analysis-endpoint \
  --machine-type n1-standard-4 \
  --gpu-type NVIDIA_TESLA_T4 \
  --gpu-count 1 \
  --min-replicas 1 \
  --max-replicas 5 \
  --test
```

## 📊 API Documentation

### Health Check
```http
GET /health
```

Response:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "v1.0.0",
  "environment": "production",
  "uptime_seconds": 3600,
  "gpu_available": false,
  "memory_usage_mb": 2048
}
```

### Prediction
```http
POST /predict
Content-Type: application/json

{
  "audio_url": "gs://bucket/audio.wav",
  "audio_format": "wav",
  "analysis_type": "comprehensive",
  "language": "ko",
  "user_id": "user123"
}
```

Response:
```json
{
  "request_id": "abc-123",
  "timestamp": "2025-08-25T10:30:00Z",
  "status": "success",
  "emotions": {
    "happiness": 0.2,
    "sadness": 0.5,
    "anger": 0.1,
    "fear": 0.05,
    "surprise": 0.05,
    "disgust": 0.05,
    "neutral": 0.05
  },
  "mental_health": {
    "depression_risk": 0.7,
    "anxiety_level": 0.4,
    "stress_level": 0.6,
    "cognitive_load": 0.3,
    "emotional_stability": 0.4,
    "social_engagement": 0.5
  },
  "voice_features": {
    "pitch_mean": 180.5,
    "pitch_std": 25.3,
    "energy_mean": 0.03,
    "speaking_rate": 3.2,
    "pause_ratio": 0.15
  },
  "confidence": 0.85,
  "processing_time_ms": 1250,
  "model_version": "v1.0.0",
  "recommendations": [
    "Consider stress management techniques",
    "Elevated emotional indicators detected"
  ]
}
```

### Batch Prediction
```http
POST /batch_predict
Content-Type: application/json

{
  "requests": [
    {
      "audio_url": "gs://bucket/audio1.wav",
      "analysis_type": "emotion"
    },
    {
      "audio_url": "gs://bucket/audio2.wav",
      "analysis_type": "mental_health"
    }
  ]
}
```

## 📈 Monitoring

### View Metrics
```bash
# View service metrics
gcloud run services describe voice-analysis-service-prod \
  --region asia-northeast3 \
  --format="get(status.traffic)"

# View logs
gcloud logging read "resource.type=cloud_run_revision \
  AND resource.labels.service_name=voice-analysis-service-prod" \
  --limit 50
```

### Create Dashboard
```bash
# Import dashboard configuration
gcloud monitoring dashboards create \
  --config-from-file=monitoring/dashboard.json
```

### Setup Alerts
```bash
# Create alert policies
gcloud alpha monitoring policies create \
  --policy-from-file=monitoring/alerts.yaml
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PROJECT_ID` | GCP Project ID | senior-mhealth-2025 |
| `ENVIRONMENT` | Deployment environment | development |
| `MODEL_VERSION` | Model version | v1.0.0 |
| `GCS_BUCKET` | Model storage bucket | senior-mhealth-models |
| `VERTEX_ENDPOINT_ID` | Vertex AI endpoint | (optional) |
| `ENABLE_GPU` | Enable GPU acceleration | true |
| `MAX_BATCH_SIZE` | Maximum batch size | 32 |
| `LOG_LEVEL` | Logging level | INFO |

### Performance Tuning

1. **Cold Start Optimization**
```yaml
# In service.yaml
metadata:
  annotations:
    run.googleapis.com/startup-cpu-boost: "true"
    autoscaling.knative.dev/minScale: "1"  # Keep warm instance
```

2. **Memory Configuration**
```yaml
resources:
  limits:
    memory: "8Gi"  # Adjust based on model size
  requests:
    memory: "4Gi"
```

3. **Concurrency Settings**
```yaml
containerConcurrency: 50  # Requests per instance
```

## 💰 Cost Optimization

### Estimated Monthly Costs (Production)

| Component | Configuration | Est. Cost |
|-----------|--------------|-----------|
| Cloud Run (CPU) | 4 vCPU, 8GB RAM, 10 instances | $300 |
| Cloud Run (GPU) | L4 GPU, 10 instances | $800 |
| Vertex AI Endpoint | T4 GPU, 5 replicas | $1,200 |
| Cloud Storage | 100GB models + audio | $20 |
| Monitoring | Metrics + logs | $50 |
| **Total (CPU)** | | **$370/month** |
| **Total (GPU)** | | **$870/month** |

### Cost Reduction Strategies

1. **Scale to Zero**: Enable for dev/staging environments
2. **Spot Instances**: Use for batch processing
3. **Regional Deployment**: Deploy closer to users
4. **Caching**: Implement Redis for repeated predictions
5. **Model Optimization**: Quantization and pruning

## 🧪 Testing

### Unit Tests
```bash
pytest tests/ -v --cov=app
```

### Integration Tests
```bash
# Test local endpoint
python tests/test_integration.py --endpoint http://localhost:8080

# Test deployed service
python tests/test_integration.py \
  --endpoint https://voice-analysis-service.a.run.app \
  --auth-token $(gcloud auth print-identity-token)
```

### Load Testing
```bash
# Install locust
pip install locust

# Run load test
locust -f tests/load_test.py \
  --host https://voice-analysis-service.a.run.app \
  --users 100 \
  --spawn-rate 10
```

## 🔒 Security

### Best Practices

1. **Authentication**: Use IAM for service-to-service auth
2. **Secrets Management**: Store sensitive data in Secret Manager
3. **Network Security**: Use VPC connector for private access
4. **Data Encryption**: Enable CMEK for Cloud Storage
5. **Audit Logging**: Enable Cloud Audit Logs

### Security Checklist

- [ ] Service account with minimal permissions
- [ ] HTTPS only endpoints
- [ ] Input validation on all endpoints
- [ ] Rate limiting configured
- [ ] Security scanning in CI/CD
- [ ] Regular dependency updates
- [ ] Data retention policies

## 📚 Resources

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Project Documentation](../../docs/8chp_contents.md)

## 🤝 Contributing

1. Create feature branch
2. Make changes and test
3. Update documentation
4. Submit pull request

## 📝 License

Copyright 2025 Senior_MHealth Team. All rights reserved.