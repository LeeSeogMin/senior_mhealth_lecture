# AI Service Deployment Guide

## Overview
This guide documents the optimized deployment process for the AI service using a pre-built base image strategy that reduces build time from 20 minutes to 3-5 minutes.

## Current Configuration
- **Base Image Version**: `v3` (includes statsmodels)
- **Build Time**: ~3-5 minutes (down from 20 minutes)
- **Registry**: `asia-northeast3-docker.pkg.dev/senior-mhealth-472007/ai-service/`

## Docker Image Architecture

### Base Image (ai-base:v3)
Pre-built image containing all heavy dependencies:
- **PyTorch Stack**: torch==2.1.2, torchaudio==2.1.2, torchvision==0.16.2 (CPU versions)
- **ML Libraries**: numpy==1.24.3, pandas==2.1.4, scikit-learn==1.3.0, scipy==1.11.4
- **Deep Learning**: transformers==4.36.2, sentence-transformers==2.2.2
- **Audio Processing**: librosa==0.10.1, soundfile==0.12.1
- **Statistical Analysis**: statsmodels==0.14.0 (added in v3)
- **Web Framework**: fastapi==0.109.0, uvicorn==0.27.0, python-multipart==0.0.6
- **AI APIs**: openai==1.6.1, google-generativeai==0.3.2
- **Visualization**: matplotlib==3.7.4, pillow==10.1.0

### Application Image (ai-service-sincnet)
Lightweight image using base image with only:
- Google Cloud specific packages
- Application code
- Configuration files

## Deployment Process

### 1. Quick Deployment (Using Existing Base Image v3)
```bash
# Deploy application using pre-built base image v3
cd /c/Senior_MHealth
gcloud builds submit --config=backend/ai-service/cloudbuild-app.yaml --timeout=600s .
```
**Time**: ~3-5 minutes

### 2. Base Image Update (When Dependencies Change)
```bash
# Only needed when adding new dependencies to base image
cd /c/Senior_MHealth/backend/ai-service

# 1. Update Dockerfile.base with new dependencies
# 2. Update version tag in cloudbuild-base.yaml (e.g., v3 → v4)
# 3. Build new base image
gcloud builds submit --config=cloudbuild-base.yaml --timeout=30m .

# 4. Update Dockerfile.optimized to use new version
# 5. Deploy application
cd /c/Senior_MHealth
gcloud builds submit --config=backend/ai-service/cloudbuild-app.yaml --timeout=600s .
```
**Time**: Base image build ~3-4 minutes, App deployment ~3-5 minutes

### 3. Interactive Deployment Script
```bash
cd /c/Senior_MHealth/backend/ai-service
./deploy-fast.sh
```
Options:
1. Quick deploy (app only) - 3-5 minutes
2. Update base image - 3-4 minutes
3. Full rebuild - 7-10 minutes total

## File Structure

### Key Files
- `Dockerfile.base` - Base image with all heavy dependencies
- `Dockerfile.optimized` - App image using base image
- `cloudbuild-base.yaml` - Cloud Build config for base image
- `cloudbuild-app.yaml` - Cloud Build config for app deployment
- `deploy-fast.sh` - Interactive deployment script

### Version History
- **v1**: Initial base image with PyTorch and basic packages
- **v2**: Added pandas, scikit-learn, fastapi, uvicorn, openai, google-generativeai
- **v3**: Added statsmodels==0.14.0 (fixes ModuleNotFoundError)

## Troubleshooting

### Common Issues

#### 1. ModuleNotFoundError
**Symptom**: Container fails to start with missing module error
**Solution**: Add missing package to Dockerfile.base and rebuild base image

#### 2. Port 8080 Not Responding
**Symptom**: Cloud Run deployment fails with "container failed to start and listen on port 8080"
**Causes**:
- Missing Python package (check logs)
- Import errors in application code
- Incorrect start script

**Debug Commands**:
```bash
# Check deployment logs
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=senior-mhealth-ai" --limit=20 --format="value(textPayload)"

# Check specific revision logs
gcloud logging read "resource.labels.revision_name=senior-mhealth-ai-00042-wh2" --limit=20
```

#### 3. Build Timeout
**Symptom**: Build exceeds timeout limit
**Solution**: Increase timeout in gcloud command or use base image strategy

### Performance Optimization

#### Build Time Comparison
| Method | Time | Notes |
|--------|------|-------|
| Full rebuild (old) | 20+ minutes | Rebuilds PyTorch every time |
| Base image strategy (v3) | 3-5 minutes | Uses cached base image |
| Base image update | 3-4 minutes | Only when dependencies change |

#### Best Practices
1. **Use Base Image v3**: Always use the latest base image version
2. **Minimize App Image**: Only include app-specific dependencies
3. **Cache Optimization**: Leverage Docker layer caching
4. **Parallel Builds**: Use high-CPU machines for faster builds

## Cloud Build Configuration

### Machine Types
- Base image build: `E2_HIGHCPU_32` (for faster dependency installation)
- App build: `N1_HIGHCPU_8` (sufficient for app packaging)

### Timeout Settings
- Base image: 30 minutes (safety margin)
- App deployment: 10 minutes (usually completes in 3-5)

## Monitoring

### Health Check Endpoint
```bash
curl https://senior-mhealth-ai-u3m35d42ya-an.a.run.app/health
```

### Service Status
```bash
gcloud run services describe senior-mhealth-ai --region=asia-northeast3
```

### Recent Deployments
```bash
gcloud run revisions list --service=senior-mhealth-ai --region=asia-northeast3 --limit=5
```

## Important Notes

1. **Always use v3 or later**: Version 3 includes statsmodels which is required for voice analysis
2. **Don't modify base image unnecessarily**: It's shared across deployments
3. **Test locally first**: Use `docker build` locally for quick iteration
4. **Monitor costs**: Base image strategy reduces build costs significantly

## Quick Reference

### Deploy Commands
```bash
# Quick deploy (most common)
cd /c/Senior_MHealth && gcloud builds submit --config=backend/ai-service/cloudbuild-app.yaml --timeout=600s .

# Check deployment status
gcloud run services describe senior-mhealth-ai --region=asia-northeast3 --format="value(status.url)"

# View logs
gcloud logging read "resource.type=cloud_run_revision" --limit=20
```

### Environment Variables
- `PORT`: 8080 (required by Cloud Run)
- `GOOGLE_CLOUD_PROJECT`: senior-mhealth-472007
- `USE_SINCNET`: true (enables SincNet models)

## Contact
For issues or questions, check the deployment logs first, then consult the team lead.

---
*Last Updated: 2025-09-15*
*Base Image Version: v3 (with statsmodels)*
*Average Deployment Time: 3-5 minutes*