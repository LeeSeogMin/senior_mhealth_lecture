# Week 4: Cloud Functions & AI 서비스 - 실습편

## 🎯 실습 목표
Express.js와 Cloud Functions를 사용하여 Senior MHealth의 첫 번째 API 엔드포인트를 구현하고, Vertex AI를 통합합니다.

## 🔍 작업 구분
- **👤 사용자 직접 작업**: GCP Console에서 수동으로 진행
- **🤖 AI 프롬프트**: AI에게 코드 작성을 요청하여 자동화

---

## Step 1: GCP 프로젝트 확인 및 API 활성화

### 1-1. 프로젝트 상태 확인 🤖

> 🤖 **AI에게 요청**:
> "현재 GCP 프로젝트 상태를 확인하고 필요한 설정을 자동으로 수행해줘.
> - 현재 프로젝트 ID 확인 및 표시
> - 프로젝트가 올바르게 설정되어 있는지 검증
> - 문제가 있으면 자동으로 수정"

### 1-2. Vertex AI 및 관련 API 활성화 🤖

> 🤖 **AI에게 요청**:
> "AI 서비스를 위한 필수 API들을 자동으로 활성화해줘.
> - Vertex AI API (aiplatform.googleapis.com)
> - Cloud Functions API
> - Cloud Build API
> - Artifact Registry API
> - 활성화 완료 후 상태 확인해서 보여줘
> - 이미 활성화되어 있으면 건너뛰기"

### 1-3. 결제 계정 확인 👤

**목표**: API 사용을 위한 결제 설정을 확인합니다.

1. **GCP Console 접속**
   - https://console.cloud.google.com/billing
   - 프로젝트에 결제 계정이 연결되어 있는지 확인
   - 무료 크레딧 잔액 확인

---

## Step 2: Cloud Functions 환경 설정

### 2-1. Functions 프로젝트 초기화 🤖

> 🤖 **AI에게 요청**:
> "Cloud Functions 프로젝트를 자동으로 초기화하고 설정해줘.
> - Firebase Functions 초기화 (이미 있으면 건너뛰기)
> - JavaScript 언어 선택
> - ESLint 자동 설정
> - 의존성 자동 설치
> - .firebaserc 파일 자동 생성 및 프로젝트 ID 설정"

### 2-2. Express 및 필수 패키지 설치 🤖

> 🤖 **AI에게 요청**:
> "backend/functions 디렉토리에 필요한 모든 패키지를 자동으로 설치해줘.
> - Express.js와 미들웨어: express, cors, helmet, express-rate-limit
> - Firebase Admin SDK
> - Vertex AI SDK (@google-cloud/aiplatform)
> - 개발 도구: nodemon, @types/node
> - 설치 진행 상황 실시간으로 보여줘"

### 2-3. 환경 변수 설정 👤

**목표**: Functions 실행에 필요한 환경 변수를 설정합니다.

`backend/functions/.env` 파일 생성 및 편집:
```env
# Cloud Functions & AI Environment
NODE_ENV=development

# Firebase Project Settings
FIREBASE_PROJECT_ID=senior-mhealth-학번
FIREBASE_PROJECT_LOCATION=asia-northeast3

# Vertex AI Settings
GCP_PROJECT_ID=senior-mhealth-학번
GCP_LOCATION=asia-northeast3

# CORS Settings
ALLOWED_ORIGINS=http://localhost:3000,http://localhost:5001

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000
RATE_LIMIT_MAX_REQUESTS=100
```

---

## Step 3: Vertex AI 설정 및 테스트

### 3-1. 인증 설정 🤖

> 🤖 **AI에게 요청**:
> "Vertex AI 사용을 위한 인증을 자동으로 설정해줘.
> - Application Default Credentials 자동 설정
> - 서비스 계정 권한 확인 및 부여
> - Vertex AI API 접근 권한 검증
> - 인증 상태 확인 후 결과 보여줘"

### 3-2. Vertex AI 연결 테스트 🤖

> 🤖 **AI에게 요청**:
> "Vertex AI Gemini 모델 연결을 테스트하고 결과를 보여줘.
> - test-vertex-ai.js 파일 자동 생성
> - Gemini 1.5 Flash 모델로 연결 테스트
> - 간단한 한국어 프롬프트로 응답 확인
> - 성공/실패 상태 명확하게 표시
> - 실패 시 원인 분석 및 자동 해결"

---

## Step 4: Cloud Functions 개발

### 4-1. 기본 Express 앱 구성 🤖

> 🤖 **AI에게 요청**:
> "backend/functions/index.js 파일을 생성하고 Express 앱을 구성해줘.
> - Firebase Functions v2 사용
> - Express 앱 설정 (CORS, JSON 파싱)
> - 헬스체크 엔드포인트 (/health) 구현
> - 환경 변수 자동 로드
> - 에러 핸들링 미들웨어 추가"

### 4-2. AI 분석 엔드포인트 구현 🤖

> 🤖 **AI에게 요청**:
> "Vertex AI를 사용한 감정 분석 API를 구현해줘.
> - POST /analyze-simple 엔드포인트 생성
> - Gemini 모델로 텍스트 감정 분석
> - 긍정/부정/중립 분류
> - 응답 캐싱 기능 추가 (5분)
> - 에러 처리 및 로깅 구현"

### 4-3. 건강 상태 모니터링 API 🤖

> 🤖 **AI에게 요청**:
> "시니어 건강 데이터 분석 API를 추가로 구현해줘.
> - POST /analyze-health 엔드포인트
> - 혈압, 맥박, 활동량 데이터 입력
> - Gemini를 통한 건강 상태 분석
> - 위험 수준 판단 (정상/주의/위험)
> - 간단한 건강 조언 생성"

---

## Step 5: 로컬 테스트

### 5-1. Firebase 에뮬레이터 설정 🤖

> 🤖 **AI에게 요청**:
> "Firebase 에뮬레이터를 설정하고 실행해줘.
> - Functions 에뮬레이터 자동 설정
> - 포트 설정 (Functions: 5001)
> - 에뮬레이터 시작
> - 접속 URL 표시"

### 5-2. API 로컬 테스트 🤖

> 🤖 **AI에게 요청**:
> "로컬에서 모든 API 엔드포인트를 테스트하고 결과를 보여줘.
> - 헬스체크 API 테스트
> - 감정 분석 API 테스트 (샘플 텍스트 사용)
> - 건강 분석 API 테스트 (샘플 건강 데이터 사용)
> - 각 API의 응답 시간 측정
> - 테스트 결과 요약 표시"

---

## Step 6: 프로덕션 배포

### 6-1. Firebase 프로젝트 확인 👤

**목표**: 배포 전 프로젝트 설정을 최종 확인합니다.

1. **Firebase Console 접속**
   - https://console.firebase.google.com
   - 자신의 프로젝트 선택
   - Functions 메뉴 확인

2. **.firebaserc 파일 확인**
   - 프로젝트 ID가 올바른지 확인
   - 리전이 asia-northeast3인지 확인

### 6-2. Functions 배포 🤖

> 🤖 **AI에게 요청**:
> "Cloud Functions를 프로덕션 환경에 자동으로 배포해줘.
> - 배포 전 빌드 검증
> - Firebase에 Functions 배포
> - 배포 진행 상황 실시간 표시
> - 배포 완료 후 URL 표시
> - 배포 실패 시 롤백 수행"

### 6-3. 프로덕션 테스트 🤖

> 🤖 **AI에게 요청**:
> "배포된 Functions를 프로덕션 환경에서 테스트해줘.
> - 실제 배포 URL로 API 호출
> - 모든 엔드포인트 동작 확인
> - 응답 시간 및 성능 측정
> - Vertex AI 연동 상태 확인
> - 테스트 결과 리포트 생성"

---

## Step 7: 모니터링 설정

### 7-1. 로그 모니터링 설정 🤖

> 🤖 **AI에게 요청**:
> "Cloud Functions와 Vertex AI 로그 모니터링을 설정해줘.
> - 실시간 로그 스트리밍 시작
> - 에러 로그 필터링 설정
> - Vertex AI 사용량 로그 확인
> - 성능 메트릭 표시
> - 알림 규칙 설정 (선택사항)"

### 7-2. 비용 모니터링 👤

**목표**: API 사용 비용을 모니터링합니다.

1. **GCP Console 비용 대시보드**
   - https://console.cloud.google.com/billing
   - Vertex AI 사용량 확인
   - Cloud Functions 실행 시간 확인
   - 일일/월별 비용 추이 확인

2. **예산 알림 설정**
   - 월 $10 예산 설정 (학습용)
   - 50%, 90% 도달 시 이메일 알림

---

## Step 8: 보안 및 최적화

### 8-1. 보안 설정 강화 🤖

> 🤖 **AI에게 요청**:
> "프로덕션 환경의 보안을 강화해줘.
> - CORS 설정을 프로덕션 URL로 제한
> - Rate limiting 규칙 적용
> - API 키 기반 인증 구현 (선택사항)
> - 환경 변수를 Firebase Config로 이전
> - 보안 헤더 설정 (Helmet)"

### 8-2. 성능 최적화 🤖

> 🤖 **AI에게 요청**:
> "Cloud Functions 성능을 최적화해줘.
> - 콜드 스타트 최소화 설정
> - 메모리 할당 최적화 (512MB)
> - 응답 캐싱 구현
> - 타임아웃 설정 조정
> - 번들 크기 최적화"

---

## 실습 검증

### 종합 검증 테스트 🤖

> 🤖 **AI에게 요청**:
> "Week 4 실습이 모두 완료되었는지 종합 검증하고 결과를 보여줘:
> - Vertex AI API 활성화 상태
> - Cloud Functions 배포 상태
> - 모든 API 엔드포인트 동작 확인
> - 로그 및 모니터링 설정 확인
> - 보안 설정 검증
> - 비용 사용량 체크
> 문제가 발견되면 자동으로 수정해줘."

---

## 프로젝트 구조 이해

```
Senior_MHealth/
├── backend/
│   └── functions/
│       ├── index.js         # Cloud Functions 메인 파일
│       ├── package.json     # 의존성 정의
│       ├── .env            # 환경 변수 (Git 제외)
│       ├── test-vertex-ai.js # AI 테스트 파일
│       └── src/
│           ├── routes/     # API 라우트
│           ├── services/   # 비즈니스 로직
│           └── utils/      # 유틸리티 함수
├── .firebaserc             # Firebase 프로젝트 설정
└── firebase.json           # Firebase 서비스 설정
```

---

## 실습 완료! 🎉

### ✅ 체크리스트
- [x] GCP 프로젝트 설정 확인
- [x] Vertex AI API 활성화
- [x] Cloud Functions 환경 구성
- [x] Express.js API 구현
- [x] Gemini 모델 통합
- [x] 감정 분석 API 구현
- [x] 건강 분석 API 구현
- [x] 로컬 테스트 완료
- [x] 프로덕션 배포 성공
- [x] 모니터링 설정

### 💰 Vertex AI 비용 정보
- **Gemini 1.5 Flash** (asia-northeast3):
  - Input: $0.00001875 per 1K characters
  - Output: $0.000075 per 1K characters
- 개발/테스트는 무료 크레딧 활용
- 캐싱으로 비용 절감 가능

### 🔒 보안 주의사항
- **API 엔드포인트**: 프로덕션에서는 인증 필수
- **CORS 설정**: 허용 도메인 제한
- **Rate Limiting**: DDoS 방지
- **환경 변수**: Firebase Config 사용

### 📚 다음 단계
- **Week 5**: Firestore 데이터베이스 통합
- **Week 6**: 웹 애플리케이션 배포 (Vercel)
- **Week 7**: Flutter 모바일 앱 개발
- **Week 8**: 운영 및 모니터링

### 🆘 도움이 필요하면
- Vertex AI 문서: https://cloud.google.com/vertex-ai/docs
- Cloud Functions 문서: https://firebase.google.com/docs/functions
- Express.js 문서: https://expressjs.com
- 강의 자료: `docs/` 디렉토리 참조