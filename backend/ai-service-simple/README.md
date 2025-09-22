# Senior MHealth AI Service - Simplified Version

Gemini API 기반 정신건강 텍스트 분석 서비스 (간소화 버전)

## 주요 변경사항

### 제거된 기능
- ❌ SincNet 음성 분석
- ❌ Librosa 음향 특징 추출
- ❌ RAG (Retrieval-Augmented Generation)
- ❌ LangChain 체이닝
- ❌ 화자 분리 (Speaker Diarization)
- ❌ 복잡한 파이프라인

### 유지된 기능
- ✅ Gemini API 텍스트 분석
- ✅ 정신건강 지표 평가 (우울도, 불안도, 인지기능)
- ✅ 간단한 REST API
- ✅ Docker 지원

## 구조

```
ai-service-simple/
├── app/
│   ├── main.py                 # FastAPI 메인 애플리케이션
│   └── services/
│       └── gemini_analyzer.py  # Gemini 텍스트 분석기
├── tests/
│   └── test_analyzer.py        # 테스트
├── requirements.txt            # 최소 의존성 (10개)
├── Dockerfile                 # 경량 Docker 이미지
├── docker-compose.yml         # 로컬 개발용
└── deploy.sh                  # Cloud Run 배포 스크립트
```

## 설치 및 실행

### 1. 환경 설정

```bash
# .env 파일 생성
cp .env.example .env

# .env 파일 편집하여 GOOGLE_API_KEY 설정
```

### 2. 로컬 실행

```bash
# 가상환경 생성 및 활성화
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 서버 실행
python -m app.main
```

### 3. Docker 실행

```bash
# Docker Compose로 실행
docker-compose up --build

# 또는 Docker로 직접 실행
docker build -t ai-simple .
docker run -p 8080:8080 --env-file .env ai-simple
```

## API 사용법

### 헬스체크

```bash
curl http://localhost:8080/health
```

### 텍스트 분석

```bash
curl -X POST http://localhost:8080/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "text": "요즘 기분이 우울하고 힘들어요",
    "user_id": "user123",
    "session_id": "session456"
  }'
```

### 응답 형식

```json
{
  "depression_score": 75.5,
  "anxiety_score": 60.0,
  "cognitive_score": 85.0,
  "emotional_state": "우울",
  "key_concerns": ["우울감", "무기력"],
  "recommendations": ["전문가 상담 권장", "규칙적인 운동"],
  "confidence": 0.85,
  "timestamp": "2024-01-20T12:00:00Z"
}
```

## 배포

### Cloud Build를 통한 자동 배포

```bash
# 환경변수 설정
export GEMINI_API_KEY="your-gemini-api-key"

# Cloud Build로 자동 빌드 및 배포
./deploy.sh
```

Cloud Build가 자동으로:
1. Docker 이미지 빌드
2. Container Registry에 푸시
3. Cloud Run에 배포
4. 환경변수 및 설정 적용

### 수동 배포 (필요시)

```bash
# Google Cloud Console에서 직접 배포
gcloud run deploy senior-mhealth-ai-simple \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated
```

## 테스트

```bash
# 테스트 실행
python -m pytest tests/

# 또는 직접 실행
python tests/test_analyzer.py
```

## 성능 개선

### Before (복잡한 버전)
- Docker 이미지 크기: ~2.5GB
- 시작 시간: ~30초
- 메모리 사용: ~2GB
- 의존성: 48개

### After (간소화 버전)
- Docker 이미지 크기: ~200MB
- 시작 시간: ~5초
- 메모리 사용: ~500MB
- 의존성: 10개

## 라이선스

MIT