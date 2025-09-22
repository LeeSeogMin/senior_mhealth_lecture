# AI 분석 서비스 배포 가이드

## 📋 시스템 아키텍처

### 통합 AI 분석 프레임워크
```
┌─────────────────────────────────────────────────────────┐
│                     Client (Flutter App)                 │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                  API Gateway (port 8080)                 │
│                     - 인증/인가                          │
│                     - 라우팅                             │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│               AI Analysis Service (port 8081)            │
│                                                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Voice (30%)  │  │ Text (40%)   │  │SincNet (30%) │  │
│  │   Librosa    │  │  GPT-4o/     │  │  Deep        │  │
│  │              │  │  Gemini      │  │  Learning    │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│                           │                              │
│                    ┌──────▼──────┐                      │
│                    │     RAG      │                      │
│                    │ (Optional)   │                      │
│                    └──────────────┘                      │
└─────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────┐
│                        Firestore                         │
│                    - 분석 결과 저장                      │
│                    - 시계열 데이터                       │
└─────────────────────────────────────────────────────────┘
```

## 🚀 배포 옵션

### 1. 로컬 개발 환경 (가상환경)

#### Windows (PowerShell)
```powershell
# 가상환경 설정 (SincNet 포함)
cd backend
.\setup_production_venv.ps1  # SincNet 의존성 포함

# 가상환경 활성화
.\venv_production\Scripts\Activate.ps1

# FFmpeg 설정 확인 (M4A/MP3 처리 필요)
ffmpeg -version

# AI 서비스 실행
cd ai-service
python -m uvicorn app.main:app --reload --port 8081
```

#### Linux/Mac
```bash
# 가상환경 설정 (SincNet 포함)
cd backend
bash setup_production_venv.sh  # SincNet 의존성 포함

# 가상환경 활성화
source venv_production/bin/activate

# FFmpeg 설정 확인 (M4A/MP3 처리 필요)
ffmpeg -version

# AI 서비스 실행
cd ai-service
python -m uvicorn app.main:app --reload --port 8081
```

### 2. Docker 배포 (권장)

#### 전체 스택 실행
```bash
# Docker Compose로 모든 서비스 실행
docker-compose -f docker-compose.ai.yml up -d

# 서비스 확인
docker-compose -f docker-compose.ai.yml ps

# 로그 확인
docker-compose -f docker-compose.ai.yml logs -f ai-service
```

#### 개별 서비스 빌드
```bash
# AI 서비스만 빌드
cd backend/ai-service
docker build -t senior-mhealth-ai .

# 실행
docker run -p 8081:8081 \
  -e GOOGLE_CLOUD_PROJECT=senior-mhealth-472007 \
  -e OPENAI_API_KEY=$OPENAI_API_KEY \
  -e GEMINI_API_KEY=$GEMINI_API_KEY \
  -e USE_RAG=true \
  senior-mhealth-ai
```

### 3. Google Cloud Run 배포 (프로덕션)

#### 사전 준비
```bash
# Google Cloud SDK 설치 확인
gcloud --version

# 프로젝트 설정
gcloud config set project senior-mhealth-472007

# 인증
gcloud auth login
gcloud auth configure-docker
```

#### 배포 스크립트 실행
```bash
cd backend/ai-service
bash deploy.sh
```

또는 수동 배포:
```bash
# 이미지 빌드 및 푸시
docker build -t gcr.io/senior-mhealth-472007/senior-mhealth-ai .
docker push gcr.io/senior-mhealth-472007/senior-mhealth-ai

# Cloud Run 배포
gcloud run deploy senior-mhealth-ai \
  --image gcr.io/senior-mhealth-472007/senior-mhealth-ai \
  --platform managed \
  --region asia-northeast3 \
  --memory 2Gi \
  --cpu 2 \
  --timeout 300 \
  --concurrency 10 \
  --max-instances 5 \
  --allow-unauthenticated \
  --set-env-vars="PROJECT_ID=senior-mhealth-472007,ENVIRONMENT=production,USE_RAG=true"
```

## 🔧 환경 변수 설정

### 필수 환경 변수
```env
# Google Cloud
GOOGLE_CLOUD_PROJECT=senior-mhealth-472007

# AI API Keys
OPENAI_API_KEY=your_openai_api_key
GEMINI_API_KEY=your_gemini_api_key

# 서비스 설정
ENVIRONMENT=development|production
USE_RAG=true|false

# SincNet 설정 (새로 추가)
FFMPEG_PATH=/usr/local/bin/ffmpeg  # Linux/Mac
# FFMPEG_PATH=C:\Senior_MHealth\backend\ffmpeg\bin  # Windows
```

### 선택적 환경 변수
```env
# 성능 튜닝
MAX_WORKERS=4
TIMEOUT_SECONDS=300

# 로깅
LOG_LEVEL=INFO|DEBUG|WARNING|ERROR

# SincNet 모델 캐시
SINCNET_MODEL_DIR=/app/models  # Docker
# SINCNET_MODEL_DIR=C:\Senior_MHealth\backend\libraries\voice_analysis\analysis\sincnet\models  # Windows
```

## 📊 모니터링

### 헬스 체크
```bash
# 로컬
curl http://localhost:8081/health

# Cloud Run
curl https://senior-mhealth-ai-xxxxx-an.a.run.app/health
```

### 예상 응답
```json
{
  "status": "healthy",
  "service": "ai-analysis",
  "timestamp": "2024-09-12T10:00:00",
  "components": {
    "voice_analysis": "ready",
    "text_analysis": "ready",
    "sincnet": "ready",
    "rag": "true"
  }
}
```

## 🔍 API 엔드포인트

### 1. 음성 분석 (통합)
```http
POST /analyze/voice
Content-Type: multipart/form-data

file: <audio_file>
request: {
  "user_id": "user123",
  "age": 75,
  "gender": "male",
  "use_rag": true,
  "include_trend": true
}
```

### 2. 텍스트 분석 (RAG 포함)
```http
POST /analyze/text
Content-Type: application/json

{
  "text": "분석할 텍스트",
  "use_rag": true,
  "age": 75,
  "gender": "female"
}
```

### 3. 모델 상태 확인
```http
GET /models/status
```

## 📈 성능 최적화

### 리소스 할당
- **메모리**: 최소 2GB, 권장 4GB (SincNet 모델 로딩 시 ~200MB 추가 필요)
- **CPU**: 최소 1 core, 권장 2 cores (SincNet 추론 시 CPU 사용)
- **타임아웃**: 300초 (음성 파일 처리 고려)
- **디스크**: 최소 1GB (SincNet 모델 캐시 ~170MB)

### 스케일링 정책
```yaml
# Cloud Run 자동 스케일링
min_instances: 0
max_instances: 5
concurrency: 10

# 부하 기준
cpu_utilization: 70%
memory_utilization: 80%
```

## 🔒 보안 고려사항

1. **API 키 관리**
   - Secret Manager 사용 권장
   - 환경 변수로 주입
   - 절대 코드에 하드코딩 금지

2. **서비스 계정**
   - 최소 권한 원칙 적용
   - Firestore, Storage 접근 권한만 부여

3. **네트워크 보안**
   - HTTPS 강제
   - API Gateway 통한 인증/인가

## 🐛 트러블슈팅

### 일반적인 문제

1. **librosa 설치 실패**
   ```bash
   # Docker 사용 권장
   docker-compose -f docker-compose.ai.yml up
   ```

2. **메모리 부족**
   - Cloud Run 메모리 증가: `--memory 4Gi`
   - 동시 처리 수 감소: `--concurrency 5`

3. **타임아웃 에러**
   - 타임아웃 증가: `--timeout 600`
   - 음성 파일 크기 제한 (10MB)

4. **RAG 초기화 실패**
   - Firebase 권한 확인
   - embeddings.jsonl 파일 존재 확인

5. **SincNet 관련 문제 (새로 추가)**
   - **모델 로딩 실패**: Firebase Storage 권한 확인, 로컬 캐시 디렉토리 권한
   - **FFmpeg 없음**: M4A/MP3 처리 불가 → FFmpeg 설치 필요
   - **PyTorch 설치**: CPU 버전 설치 `pip install torch --index-url https://download.pytorch.org/whl/cpu`
   - **0.00 결과값**: Original SincNet 아키텍처 확인 (200ms 윈도우, Layer Norm)

## 📝 체크리스트

### 배포 전
- [ ] 환경 변수 설정 확인
- [ ] API 키 설정
- [ ] 서비스 계정 키 배치
- [ ] Docker 이미지 빌드 테스트
- [ ] **SincNet 모델 파일 확인** (dep_model_10500_raw.pkl, insom_model_38800_raw.pkl)
- [ ] **FFmpeg 설치/경로 확인** (M4A/MP3 처리용)
- [ ] **PyTorch CPU 버전 설치 확인**

### 배포 후
- [ ] 헬스 체크 확인
- [ ] 각 엔드포인트 테스트
- [ ] 로그 모니터링 설정
- [ ] 알림 설정
- [ ] **SincNet 분석 테스트** (실제 음성 파일로)

## 🔄 업데이트 프로세스

1. **코드 변경**
   ```bash
   git checkout develop_lee
   git pull origin develop_lee
   ```

2. **이미지 재빌드**
   ```bash
   docker build -t gcr.io/senior-mhealth-472007/senior-mhealth-ai:v2 .
   docker push gcr.io/senior-mhealth-472007/senior-mhealth-ai:v2
   ```

3. **롤링 업데이트**
   ```bash
   gcloud run deploy senior-mhealth-ai \
     --image gcr.io/senior-mhealth-472007/senior-mhealth-ai:v2
   ```

## 📞 지원

문제 발생 시:
1. 로그 확인: `docker-compose logs` 또는 Cloud Run 콘솔
2. GitHub Issues 생성
3. 팀 슬랙 채널 문의