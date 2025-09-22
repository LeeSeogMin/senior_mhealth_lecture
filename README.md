# 🏥 Senior MHealth - 클라우드 기반 백엔드 개발 교육 프로젝트

> **Google Cloud Platform과 Firebase를 활용한 실전 백엔드 개발 학습 프로젝트**

## 📚 프로젝트 개요

Senior MHealth는 시니어를 위한 헬스케어 애플리케이션으로, 대학 백엔드 개발 교육을 위해 설계된 실습 프로젝트입니다. 학생들은 8주에 걸쳐 실제 작동하는 클라우드 기반 백엔드 시스템을 구축하며, 현업에서 사용되는 최신 기술스택을 경험합니다.

### 🎯 학습 목표

- **클라우드 플랫폼**: Google Cloud Platform (GCP) 실습
- **서버리스 아키텍처**: Cloud Functions, Cloud Run 활용
- **AI/ML 통합**: Vertex AI (Gemini) API 활용
- **NoSQL 데이터베이스**: Firestore 설계 및 구현
- **인증/보안**: Firebase Authentication & RBAC
- **실시간 통신**: WebSocket, FCM 푸시 알림
- **프로덕션 배포**: 성능 최적화, 모니터링, CI/CD

### 📦 제공되는 것
- ✅ **AI 서비스**: 완성된 음성 분석 및 건강 예측 시스템
- ✅ **Web 앱**: Next.js 기반 관리자/보호자용 대시보드
- ✅ **Mobile 앱**: Flutter 기반 시니어용 모바일 앱
- ✅ **학습 자료**: 각 주차별 이론 및 실습 가이드
- ✅ **인프라 코드**: Terraform IaC 템플릿

### 🔨 여러분이 구현할 것
- **Backend API**: Firebase Functions 기반 RESTful API
- **데이터베이스**: Firestore 스키마 설계 및 CRUD 구현
- **인증/보안**: Firebase Auth 및 역할 기반 접근 제어
- **실시간 기능**: FCM 푸시 알림 및 실시간 데이터 동기화
- **최적화**: 캐싱, Rate Limiting, 성능 모니터링

## ⚠️ 중요 사항

**이 프로젝트는 개인별 Firebase 프로젝트 ID를 사용합니다!**
- 모든 학생은 자신만의 Firebase/GCP 프로젝트를 생성해야 합니다
- 하드코딩된 프로젝트 ID가 없으므로 반드시 자신의 ID로 설정해야 합니다
- 환경 변수 파일(.env)과 서비스 계정 키는 절대 Git에 커밋하지 마세요

## 🏗️ 프로젝트 구조

```
Senior_MHealth/
├── backend/               # 백엔드 서비스 (학생 구현 영역)
│   ├── functions/         # Cloud Functions (서버리스)
│   │   ├── index.js       # 메인 엔트리 포인트
│   │   ├── src/           # 소스 코드
│   │   │   ├── routes/    # API 라우트
│   │   │   ├── services/  # 비즈니스 로직
│   │   │   └── middleware/ # 미들웨어
│   │   └── .env.template  # 환경 변수 템플릿
│   ├── api-service/       # Cloud Run API 서비스
│   └── ai-service-simple/ # Vertex AI 연동 서비스
│
├── frontend/              # 프론트엔드 (제공 코드)
│   ├── web/              # Next.js 웹 애플리케이션
│   └── mobile/           # Flutter 모바일 앱
│
├── infrastructure/        # 인프라 설정
│   └── terraform/        # IaC (Infrastructure as Code)
│
├── docs/                 # 학습 자료
│   ├── week3_theory.md   # 이론 문서
│   ├── week3_practice.md # 실습 가이드
│   └── ...              # 주차별 자료
│
└── setup/                # 설정 스크립트
    └── scripts/         # 주차별 설정 스크립트
</```

## 🚀 시작하기

### 필수 요구사항

- Node.js 18.0.0 이상
- Python 3.9 이상 (AI 서비스용)
- Google Cloud SDK
- Firebase CLI
- Git
- (선택) Docker Desktop

### 초기 설정

#### 1. GCP 프로젝트 생성

```bash
# GCP Console에서 프로젝트 생성
# https://console.cloud.google.com
# 프로젝트 ID: senior-mhealth-[학번]

# 필수 API 활성화
gcloud services enable \
  cloudfunctions.googleapis.com \
  firestore.googleapis.com \
  cloudbuild.googleapis.com \
  aiplatform.googleapis.com
```

#### 2. Firebase 프로젝트 연결

```bash
# Firebase CLI 설치
npm install -g firebase-tools

# Firebase 로그인
firebase login

# 프로젝트 초기화
firebase init

# 선택 옵션:
# - Firestore
# - Functions
# - Hosting (선택)
# - Storage (선택)
```

#### 3. 환경 변수 설정

```bash
# Backend 환경 변수
cd backend/functions
cp .env.template .env

# .env 파일 편집하여 본인의 프로젝트 정보 입력
# GCP_PROJECT_ID=your-project-id
# FIREBASE_PROJECT_ID=your-project-id
```

#### 4. 의존성 설치

```bash
# Backend
cd backend/functions
npm install

# Web (선택사항 - 프론트엔드 테스트용)
cd ../../frontend/web
npm install

# Mobile (선택사항 - 모바일 테스트용)
cd ../mobile
flutter pub get
```

## 📖 학습 커리큘럼 (8주 과정)

### Week 3: Cloud Platform 기초
- GCP 계정 생성 및 프로젝트 설정
- Firebase 프로젝트 초기화
- 개발 환경 구성
- **실습**: `setup/scripts/week3-setup.sh` 실행
- **문서**: `docs/week3_theory.md`, `docs/week3_practice.md`

### Week 4: Cloud Functions & AI 통합
- Express.js 기반 API 구조
- Vertex AI (Gemini) API 통합
- 서버리스 함수 작성 및 배포
- **실습**: `setup/scripts/week4-setup.sh` 실행
- **구현**: 기본 API 엔드포인트

### Week 5: Firestore 데이터베이스
- NoSQL 데이터 모델링
- CRUD 작업 구현
- 실시간 리스너 및 트리거
- 보안 규칙 설정
- **실습**: `setup/scripts/week5-setup.sh` 실행
- **구현**: 데이터 모델 및 API

### Week 6: 웹 애플리케이션 배포
- Next.js 앱 이해
- Vercel 배포 프로세스
- 환경 변수 관리
- CORS 및 API 연동
- **실습**: `setup/scripts/week6-setup.sh` 실행
- **배포**: Vercel 플랫폼

### Week 7: 모바일 앱 통합
- Flutter 앱 설정
- Firebase SDK 통합
- FCM 푸시 알림 구현
- 실시간 데이터 동기화
- **실습**: `setup/scripts/week7-setup.sh` 실행
- **구현**: 푸시 알림 및 실시간 기능

### Week 8: 프로덕션 최적화
- 성능 최적화 (캐싱, 압축)
- 모니터링 및 로깅 설정
- CI/CD 파이프라인 구축
- 보안 강화 및 테스트
- **실습**: `setup/scripts/week8-setup.sh` 실행
- **배포**: 프로덕션 환경

## 💻 개발 가이드

### Backend 개발 (학생 구현 영역)

#### Cloud Functions 기본 구조

```javascript
// backend/functions/index.js
const { onRequest } = require('firebase-functions/v2/https');
const express = require('express');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// Health Check
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date().toISOString()
  });
});

// TODO: API 엔드포인트 구현
app.post('/api/health-data', async (req, res) => {
  // 건강 데이터 저장 로직
});

exports.api = onRequest(app);
```

#### Vertex AI 연동 예제

```javascript
// backend/functions/src/services/ai-service.js
const { VertexAI } = require('@google-cloud/vertexai');

class AIService {
  constructor() {
    this.vertexAI = new VertexAI({
      project: process.env.GCP_PROJECT_ID,
      location: 'asia-northeast3'
    });
    this.model = 'gemini-1.5-flash';
  }

  async analyzeHealthData(data) {
    // AI 분석 로직 구현
    const generativeModel = this.vertexAI.preview.getGenerativeModel({
      model: this.model,
    });

    // 분석 실행 및 결과 반환
  }
}

module.exports = new AIService();
```

### 배포

#### 개발 환경 (로컬 테스트)

```bash
# Firebase 에뮬레이터 실행
cd backend/functions
firebase emulators:start

# 또는 개별 서비스만
firebase emulators:start --only functions,firestore
```

#### 프로덕션 배포

```bash
# Cloud Functions 배포
firebase deploy --only functions

# 특정 함수만 배포
firebase deploy --only functions:api

# Cloud Run 배포 (선택사항)
cd backend/api-service
gcloud run deploy api-service \
  --source . \
  --region asia-northeast3
```

## 📋 구현 체크리스트

### 필수 기능 (60%)
- [ ] Health Check 엔드포인트
- [ ] 사용자 인증 미들웨어
- [ ] 시니어 정보 CRUD API
- [ ] 건강 데이터 CRUD API
- [ ] 역할 기반 접근 제어 (RBAC)
- [ ] Vertex AI 연동 (건강 분석)
- [ ] FCM 푸시 알림
- [ ] 일일/주간 리포트 생성
- [ ] 에러 처리 및 로깅

### 고급 기능 (40%)
- [ ] 캐싱 구현 (Redis/Memory)
- [ ] Rate Limiting
- [ ] 배치 처리 최적화
- [ ] 실시간 모니터링 대시보드
- [ ] GraphQL API (선택)
- [ ] 마이크로서비스 아키텍처 (선택)

## 🧪 테스트

### API 테스트 예제

```bash
# Health Check
curl http://localhost:5001/[project-id]/us-central1/api/health

# 건강 데이터 생성
curl -X POST http://localhost:5001/[project-id]/us-central1/api/health-data \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [token]" \
  -d '{
    "seniorId": "senior001",
    "type": "heartRate",
    "value": 75,
    "unit": "bpm",
    "timestamp": "2024-09-20T10:00:00Z"
  }'

# AI 분석 요청
curl -X POST http://localhost:5001/[project-id]/us-central1/api/analyze \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer [token]" \
  -d '{
    "seniorId": "senior001",
    "dataType": "voice",
    "audioUrl": "gs://bucket/path/to/audio.wav"
  }'
```

## 🔐 보안 고려사항

### 필수 보안 설정
- **환경 변수**: 절대 하드코딩 금지, .env 파일 사용
- **API 키**: Secret Manager 사용 권장
- **서비스 계정**: 최소 권한 원칙 적용
- **CORS**: 허용된 오리진만 설정
- **Rate Limiting**: DDoS 공격 방어
- **입력 검증**: 모든 사용자 입력 검증

### Firestore 보안 규칙 예제

```javascript
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    // 인증된 사용자만 읽기/쓰기
    match /users/{userId} {
      allow read, write: if request.auth != null && request.auth.uid == userId;
    }

    // 시니어 데이터는 보호자도 접근 가능
    match /seniors/{seniorId} {
      allow read: if request.auth != null &&
        (request.auth.uid == resource.data.userId ||
         request.auth.uid in resource.data.guardianIds);
    }
  }
}
```

## 📊 평가 기준

### 1. 기능 구현 (40%)
- API 엔드포인트 완성도
- 데이터베이스 연동 정확성
- AI 서비스 통합
- 실시간 기능 작동

### 2. 코드 품질 (30%)
- 클린 코드 원칙 준수
- 에러 처리 완성도
- 비동기 처리 정확성
- 주석 및 문서화

### 3. 클라우드 활용 (20%)
- 서비스 배포 성공
- 확장성 고려
- 비용 최적화
- 모니터링 구현

### 4. 보안 (10%)
- 인증/인가 구현
- 데이터 보호
- 보안 best practices
- 취약점 방어

## 🛠️ 문제 해결

### 자주 발생하는 문제

#### 1. Firebase 권한 오류
```bash
# 서비스 계정 재인증
gcloud auth application-default login

# Firebase 재로그인
firebase login --reauth
```

#### 2. Vertex AI API 오류
```bash
# API 활성화
gcloud services enable aiplatform.googleapis.com

# 권한 부여
gcloud projects add-iam-policy-binding [PROJECT_ID] \
  --member="serviceAccount:[SERVICE_ACCOUNT]" \
  --role="roles/aiplatform.user"
```

#### 3. CORS 오류
```javascript
// Express CORS 설정
const cors = require('cors');
app.use(cors({
  origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
}));
```

#### 4. Firestore 연결 오류
```javascript
// 올바른 초기화
const admin = require('firebase-admin');

if (!admin.apps.length) {
  admin.initializeApp({
    projectId: process.env.FIREBASE_PROJECT_ID,
  });
}

const db = admin.firestore();
```

## 📚 참고 자료

### 공식 문서
- [Google Cloud Platform 문서](https://cloud.google.com/docs)
- [Firebase 문서](https://firebase.google.com/docs)
- [Vertex AI 문서](https://cloud.google.com/vertex-ai/docs)
- [Express.js 가이드](https://expressjs.com/)

### 추가 학습 자료
- [Node.js Best Practices](https://github.com/goldbergyoni/nodebestpractices)
- [REST API 설계 가이드](https://restfulapi.net/)
- [Cloud Architecture Framework](https://cloud.google.com/architecture/framework)
- [Firebase 성능 최적화](https://firebase.google.com/docs/perf-mon)

## 💡 개발 팁

1. **단계별 구현**: TODO를 순서대로 구현하고 테스트
2. **버전 관리**: Git으로 진행 상황을 체계적으로 관리
3. **로그 활용**: Cloud Logging으로 디버깅 및 모니터링
4. **테스트 주도**: 구현 전 테스트 케이스 작성
5. **문서화**: API 문서와 코드 주석 충실히 작성
6. **보안 우선**: 처음부터 보안을 고려한 설계
7. **성능 측정**: 초기부터 성능 메트릭 수집

## 🤝 지원

### 학습 지원
- **문서**: `docs/` 폴더의 주차별 학습 자료
- **설정 스크립트**: `setup/scripts/` 의 자동화 스크립트
- **예제 코드**: 각 기능별 구현 예제 제공

### 커뮤니티
- **이슈 트래커**: GitHub Issues 활용
- **디스커션**: GitHub Discussions 또는 Slack
- **오피스 아워**: 매주 화/목 오후 2-4시
- **스터디 그룹**: 자율 스터디 그룹 운영

---

## 📄 라이선스

이 프로젝트는 교육 목적으로 설계되었습니다. 실제 프로덕션 환경에서는 추가적인 보안 및 최적화가 필요합니다.

---

**🚀 행운을 빕니다! 실제 작동하는 클라우드 기반 헬스케어 백엔드를 만들어보세요!**

**💪 여러분은 이 과정을 통해 현업에서 바로 활용 가능한 클라우드 백엔드 개발 역량을 갖추게 될 것입니다.**