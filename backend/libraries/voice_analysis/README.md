# AI 음성 분석 서비스

## 개요
노인 정신건강 평가를 위한 AI 기반 음성 분석 서비스입니다. Google Cloud Run에서 실행되며, 음성 데이터를 분석하여 정신건강 지표를 제공합니다.

## 🚀 배포 상태
- **서비스 URL**: https://ai-analysis-service-nv7k642v4a-du.a.run.app
- **Region**: asia-northeast3
- **Status**: ✅ Active

## 📋 주요 기능
- 음성 파일 업로드 및 분석
- Google Speech-to-Text 통합
- 정신건강 지표 분석
- 시계열 데이터 추적
- 종합 보고서 생성

## 🛠️ 기술 스택
- **Language**: Python 3.11
- **Framework**: FastAPI
- **Cloud**: Google Cloud Run
- **Storage**: Firebase Storage
- **Database**: Firestore
- **AI/ML**: OpenAI API, Google Speech-to-Text

## 📦 프로젝트 구조
```
ai/
├── analysis/           # 분석 모듈
│   ├── core/          # 핵심 분석 기능
│   ├── mental_health/ # 정신건강 분석
│   ├── pipeline/      # 파이프라인 처리
│   ├── sincnet/       # SincNet 모델
│   └── timeseries/    # 시계열 분석
├── utils/             # 유틸리티 함수
├── main.py           # FastAPI 앱 진입점
├── Dockerfile        # Docker 설정
├── cloudbuild.yaml   # Cloud Build 설정
├── requirements-base.txt  # 기본 의존성
├── requirements-ml.txt    # ML 의존성
└── serviceAccountKey.json # 서비스 계정 키
```

## 🔧 로컬 개발

### 환경 설정

**Windows (기본):**
```cmd
REM Python 가상환경 생성
python -m venv venv
venv\Scripts\activate

REM 의존성 설치
pip install -r requirements-base.txt
pip install -r requirements-ml.txt

REM 환경변수 설정
copy .env.example .env
REM .env 파일 편집하여 필요한 값 설정
```

**Mac/Linux (대안):**
```bash
# Python 가상환경 생성
python -m venv venv
source venv/bin/activate

# 의존성 설치
pip install -r requirements-base.txt
pip install -r requirements-ml.txt

# 환경변수 설정
cp .env.example .env
# .env 파일 편집하여 필요한 값 설정
```

### 로컬 실행

**Windows (기본):**
```cmd
python main.py
REM http://localhost:8080 에서 확인
```

**Mac/Linux (대안):**
```bash
python main.py
# http://localhost:8080 에서 확인
```

## 🚀 배포

### Cloud Build를 통한 자동 배포
```bash
gcloud builds submit --config cloudbuild.yaml .
```

### 수동 배포
```bash
# Docker 이미지 빌드
docker build -t ai-analysis-service .

# Artifact Registry에 푸시
docker tag ai-analysis-service asia-northeast3-docker.pkg.dev/PROJECT_ID/ai-services/ai-analysis-service
docker push asia-northeast3-docker.pkg.dev/PROJECT_ID/ai-services/ai-analysis-service

# Cloud Run 배포
gcloud run deploy ai-analysis-service \
  --image asia-northeast3-docker.pkg.dev/PROJECT_ID/ai-services/ai-analysis-service \
  --region asia-northeast3 \
  --memory 2Gi \
  --timeout 300
```

## 📊 모니터링

### Health Check
```bash
curl https://ai-analysis-service-nv7k642v4a-du.a.run.app/health
```

### 로그 확인
```bash
gcloud run services logs read ai-analysis-service --region=asia-northeast3
```

### 메트릭 확인
- [Cloud Console](https://console.cloud.google.com/run/detail/asia-northeast3/ai-analysis-service)에서 확인

## ⚠️ 주의사항

### 이미지 크기 관리
- 현재 이미지 크기: ~703MB
- Multi-stage 빌드로 최적화됨
- 불필요한 파일은 .dockerignore에 추가

### 빌드 시간
- 평균 빌드 시간: 7-8분
- 캐시 활용으로 시간 단축 가능

### IAM 정책
- cloudbuild.yaml에 IAM 정책 자동 설정 포함
- 403 에러 시 수동으로 IAM 정책 추가 필요

## 🔒 보안
- 서비스 계정 키는 이미지에 포함 (개선 필요)
- OpenAI API 키는 Google Secret Manager 사용
- HTTPS를 통한 보안 통신

## 📚 참고 문서
- [build.md](../build.md) - 전체 시스템 빌드 가이드
- [측정방법.md](./측정방법.md) - 음성 분석 측정 방법
- [Google Cloud Run 문서](https://cloud.google.com/run/docs)

## 🤝 기여
문제 발견 시 Issue를 등록하거나 Pull Request를 제출해주세요.