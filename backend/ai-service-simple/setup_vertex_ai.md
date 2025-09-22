# Vertex AI 설정 가이드

## 1. 사전 요구사항

### GCP 프로젝트 설정
1. Google Cloud Console 접속: https://console.cloud.google.com
2. 프로젝트 선택 또는 생성
3. Billing 계정 연결 확인

### 필요한 API 활성화
```bash
# Vertex AI API 활성화
gcloud services enable aiplatform.googleapis.com

# 기타 필요한 API들
gcloud services enable compute.googleapis.com
gcloud services enable storage-api.googleapis.com
```

## 2. 인증 설정

### 옵션 1: Application Default Credentials (권장)
```bash
# gcloud CLI로 인증
gcloud auth application-default login

# 프로젝트 설정
gcloud config set project YOUR_PROJECT_ID
```

### 옵션 2: 서비스 계정 사용
```bash
# 서비스 계정 생성
gcloud iam service-accounts create vertex-ai-service \
    --display-name="Vertex AI Service Account"

# 권한 부여
gcloud projects add-iam-policy-binding YOUR_PROJECT_ID \
    --member="serviceAccount:vertex-ai-service@YOUR_PROJECT_ID.iam.gserviceaccount.com" \
    --role="roles/aiplatform.user"

# 키 생성
gcloud iam service-accounts keys create key.json \
    --iam-account=vertex-ai-service@YOUR_PROJECT_ID.iam.gserviceaccount.com

# 환경 변수 설정
export GOOGLE_APPLICATION_CREDENTIALS="$(pwd)/key.json"
```

## 3. 환경 변수 설정

`.env` 파일 생성:
```env
# Google Cloud Project
GCP_PROJECT_ID=your-actual-project-id
GCP_LOCATION=asia-northeast3

# Service Configuration
SERVICE_NAME=senior-mhealth-ai-vertex
PORT=8080
LOG_LEVEL=INFO
```

## 4. Python 패키지 설치

```bash
# 가상 환경 생성 (선택사항)
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

## 5. 로컬 테스트

```bash
# 애플리케이션 실행
python -m app.main

# 헬스체크
curl http://localhost:8080/health

# 분석 테스트
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "오늘은 기분이 좋지 않아요. 계속 우울하고 불안해요.",
    "user_id": "test_user",
    "session_id": "test_session"
  }'
```

## 6. Cloud Run 배포 (선택사항)

### Dockerfile 생성
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
```

### 배포
```bash
# Docker 이미지 빌드 및 푸시
gcloud builds submit --tag gcr.io/YOUR_PROJECT_ID/vertex-ai-service

# Cloud Run 배포
gcloud run deploy vertex-ai-service \
  --image gcr.io/YOUR_PROJECT_ID/vertex-ai-service \
  --region asia-northeast3 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars GCP_PROJECT_ID=YOUR_PROJECT_ID,GCP_LOCATION=asia-northeast3
```

## 7. 비용 관리

### Vertex AI Gemini 가격 (asia-northeast3)
- **Gemini 1.5 Flash**:
  - Input: $0.00001875 per 1K characters
  - Output: $0.000075 per 1K characters

- **Gemini 1.5 Pro**:
  - Input: $0.0000625 per 1K characters
  - Output: $0.00025 per 1K characters

### 비용 최적화 팁
1. 개발/테스트 환경에서는 Flash 모델 사용
2. 응답 캐싱 구현
3. 배치 처리 활용
4. 할당량 및 제한 설정

## 8. 모니터링

### Cloud Logging
```bash
# 로그 확인
gcloud logging read "resource.type=aiplatform.googleapis.com/Model" --limit 10

# 실시간 로그 스트리밍
gcloud alpha logging tail "resource.type=cloud_run_revision"
```

### 메트릭 모니터링
1. Cloud Console > Vertex AI > Models
2. 사용량, 지연 시간, 오류율 확인

## 9. 트러블슈팅

### 일반적인 오류

#### API not enabled
```
Error: Vertex AI API has not been used in project
해결: gcloud services enable aiplatform.googleapis.com
```

#### 권한 오류
```
Error: Permission denied
해결: IAM에서 Vertex AI User 역할 추가
```

#### 리전 오류
```
Error: Model not available in region
해결: asia-northeast3 또는 지원되는 다른 리전 사용
```

## 10. 참고 문서

- [Vertex AI Documentation](https://cloud.google.com/vertex-ai/docs)
- [Gemini API in Vertex AI](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/gemini-use-cases)
- [Pricing](https://cloud.google.com/vertex-ai/pricing#generative_ai_models)
- [Available Regions](https://cloud.google.com/vertex-ai/docs/general/locations)