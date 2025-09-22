# Senior MHealth API Service

## 📋 개요
AI/ML 기반 음성 분석 및 건강 리포트 생성을 담당하는 **통합 백엔드 서비스**

## 🚀 개요

이 서비스는 기존에 분산되어 있던 여러 서비스를 하나로 통합한 코어 백엔드 서비스입니다:
- 건강 리포트 생성 API (기존 cloud-run 서비스)
- 음성 분석 API (기존 ai/voice-analysis-service 통합)

## 📁 디렉토리 구조

```
backend/api-service/
├── app/
│   ├── main.py                 # FastAPI 애플리케이션 진입점
│   ├── api/                    # API 엔드포인트
│   │   ├── health_reports.py   # 건강 리포트 API
│   │   └── voice_analysis.py   # 음성 분석 API
│   ├── models/                 # Pydantic 데이터 모델
│   ├── services/               # 비즈니스 로직
│   └── utils/                  # 유틸리티 함수
├── ../libraries/               # 공통 라이브러리
│   └── voice_analysis/         # 음성 분석 모듈 (ai/ 폴더에서 이동)
├── tests/                      # 테스트 코드
├── Dockerfile                  # 멀티스테이지 Docker 빌드
├── cloudbuild.yaml            # Cloud Build 배포 설정
├── requirements.txt           # 의존성
└── README.md                  # 이 문서
```

## 🔧 주요 기능

### 통합 API 엔드포인트
- **건강 리포트**: `/api/v1/health/*`
- **음성 분석**: `/api/v1/voice/*`
- **헬스 체크**: `/health`
- **API 문서**: `/docs` (Swagger UI)

### 기술 스택
- **Python 3.11+**
- **FastAPI 0.116+** - 현대적인 API 프레임워크
- **Uvicorn** - ASGI 서버
- **Docker** - 컨테이너화
- **Google Cloud Run** - 서버리스 배포
- **Pydantic** - 데이터 검증

## 🚦 시작하기

### 로컬 개발 환경

**Windows (기본):**
```cmd
cd backend\api-service

REM 의존성 설치
pip install -r requirements.txt

REM 개발 서버 실행
python -m app.main

REM 또는 uvicorn으로 직접 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**Mac/Linux (대안):**
```bash
cd backend/api-service

# 의존성 설치
pip install -r requirements.txt

# 개발 서버 실행
python -m app.main

# 또는 uvicorn으로 직접 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

### Docker로 실행

**Windows (기본):**
```cmd
REM Docker 이미지 빌드
docker build -t senior-mhealth-api-service .

REM 컨테이너 실행
docker run -p 8080:8080 senior-mhealth-api-service
```

**Mac/Linux (대안):**
```bash
# Docker 이미지 빌드
docker build -t senior-mhealth-api-service .

# 컨테이너 실행
docker run -p 8080:8080 senior-mhealth-api-service
```

### Cloud Run 배포

```cmd
REM Cloud Build로 배포 (Windows/Mac/Linux 공통)
gcloud builds submit --config=cloudbuild.yaml .
```

## 📊 API 사용법

### 헬스 체크
```bash
curl http://localhost:8080/health
```

### 음성 분석 요청
```bash
curl -X POST http://localhost:8080/api/v1/voice/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "audio_url": "path/to/audio.wav",
    "analysis_type": "comprehensive",
    "user_id": "user123",
    "call_id": "call456"
  }'
```

### API 문서 확인
- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## 📈 정리된 아키텍처

### 이전 (분산)
```
ai/main.py                     # 음성 분석 서비스
backend/cloud-run/            # 건강 리포트 서비스  
backend/voice-analysis-service/ # 중복된 음성 분석 서비스
```

### 현재 (통합)
```
backend/api-service/         # 🎯 통합 백엔드 서비스
├── 건강 리포트 API
└── 음성 분석 API

backend/libraries/            # 📚 공통 라이브러리
└── voice_analysis/          # 재사용 가능한 AI 모듈
```

## 🔄 마이그레이션 가이드

### 1. 클라이언트 엔드포인트 변경
```diff
- POST /voice-api/analyze        # 기존 음성 분석
+ POST /api/v1/voice/analyze     # 새 통합 서비스

- GET /health-reports            # 기존 건강 리포트  
+ GET /api/v1/health/reports     # 새 통합 서비스
```

### 2. 배포 URL 변경
```diff
- multiple-services.run.app      # 여러 서비스
+ senior-mhealth-core-service    # 단일 통합 서비스
```

## 🎯 제5강 구현 완료

✅ **통합 백엔드 서비스 구축**
✅ **API 엔드포인트 통일**
✅ **공통 라이브러리 분리**
✅ **Docker 컨테이너화**
✅ **Cloud Run 배포 설정**

이제 제5강 "Cloud Run과 FastAPI로 확장된 백엔드 구현"을 위한 통합 서비스가 준비되었습니다!