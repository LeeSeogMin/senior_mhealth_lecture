# 환경변수 설정 가이드

## 📋 Overview
Senior MHealth 백엔드 서비스의 환경변수 설정 가이드입니다.

## 🔧 필수 환경변수

### Firebase Functions
```bash
# GCP Configuration
GCP_PROJECT_ID=senior-mhealth-472007
GCP_REGION=asia-northeast3

# Cloud SQL Configuration
CLOUD_SQL_HOST=/cloudsql/senior-mhealth-472007:asia-northeast3:senior-mhealth-472007-db
CLOUD_SQL_USER=root
CLOUD_SQL_PASSWORD=<your_password>
CLOUD_SQL_DATABASE=senior_mhealth

# BigQuery Configuration
BIGQUERY_DATASET=senior_mhealth_analytics

# Environment
NODE_ENV=production

# Web Application URL Configuration
# Production: https://web-eight-eosin.vercel.app
# Staging: https://senior-mhealth-staging.vercel.app
# Development: http://localhost:3000
WEB_APP_URL=https://web-eight-eosin.vercel.app

# Storage
STORAGE_BUCKET=senior-mhealth-472007.appspot.com

# Cloud Run Services
CLOUD_RUN_URL=https://senior-mhealth-ai-1054806937473.asia-northeast3.run.app
```

### Python Services (AI/Analysis)
```bash
# Project Configuration
PROJECT_ID=senior-mhealth-472007
REGION=asia-northeast3

# Web Application URL
WEB_APP_URL=https://web-eight-eosin.vercel.app

# Environment
ENVIRONMENT=production
```

## 🚀 배포 시 환경변수 설정

### Firebase Functions 배포
```bash
# Firebase Functions Config 설정
firebase functions:config:set \
    app.environment="production" \
    app.cloud_run_url="https://senior-mhealth-ai-1054806937473.asia-northeast3.run.app" \
    app.web_app_url="https://web-eight-eosin.vercel.app" \
    storage.bucket="senior-mhealth-472007.appspot.com"

# 배포
firebase deploy --only functions
```

### Cloud Run 배포
```bash
# 환경변수와 함께 배포
gcloud run deploy senior-mhealth-ai \
    --set-env-vars="WEB_APP_URL=https://web-eight-eosin.vercel.app" \
    --set-env-vars="PROJECT_ID=senior-mhealth-472007" \
    --set-env-vars="ENVIRONMENT=production" \
    --region=asia-northeast3
```

## 📌 환경별 URL 설정

| Environment | WEB_APP_URL | 용도 |
|------------|-------------|------|
| Production | https://web-eight-eosin.vercel.app | 실제 운영 환경 |
| Staging | https://senior-mhealth-staging.vercel.app | 테스트 환경 |
| Development | http://localhost:3000 | 로컬 개발 환경 |

## 🔄 FCM 알림 URL 동작

분석 완료 시 FCM 알림에 포함되는 웹 URL은 `WEB_APP_URL` 환경변수를 사용합니다:

1. **notification_service.py**:
   ```python
   web_app_url = os.environ.get('WEB_APP_URL', 'https://web-eight-eosin.vercel.app')
   web_url = f"{web_app_url}/analysis/{analysis_id}"
   ```

2. **Firebase Functions (index.js)**:
   ```javascript
   const webAppUrl = process.env.WEB_APP_URL || 'https://web-eight-eosin.vercel.app';
   const webUrl = `${webAppUrl}/analysis/${analysisId}`;
   ```

3. **FCM 알림 데이터**:
   ```json
   {
     "type": "analysis_complete",
     "analysis_id": "분석ID",
     "webUrl": "설정된_WEB_APP_URL/analysis/분석ID"
   }
   ```

## ⚠️ 주의사항

1. **환경변수 우선순위**:
   - 환경변수가 설정되면 해당 값 사용
   - 환경변수가 없으면 기본값 사용 (https://web-eight-eosin.vercel.app)

2. **배포 시 확인**:
   - 배포 환경에 맞는 WEB_APP_URL 설정 확인
   - Firebase Functions Config 업데이트 필요
   - Cloud Run 환경변수 업데이트 필요

3. **로컬 개발**:
   - `.env` 파일 생성하여 로컬 환경변수 설정
   - `.env` 파일은 `.gitignore`에 포함되어 있어야 함