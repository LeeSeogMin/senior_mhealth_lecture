# Week 6: Firebase Authentication 다중 사용자 인증 시스템 - 실습편

## 🎯 실습 목표
Firebase Authentication을 사용하여 Senior MHealth의 다중 사용자 인증 시스템을 구축하고, 역할 기반 접근 제어를 구현합니다.

## 🔍 작업 구분
- **👤 사용자 직접 작업**: Firebase Console에서 수동으로 진행
- **🤖 AI 프롬프트**: AI에게 코드 작성을 요청하여 자동화

---

## Step 1: 사전 요구사항 및 패키지 설치

### 1-1. 기본 설정 확인 🤖

> 🤖 **AI에게 요청**:
> "Week 5까지의 설정이 완료되었는지 직접 확인해줘.
> - backend/functions 디렉토리 존재 여부 확인
> - firestore.rules 파일 존재 확인
> - 문제가 있으면 자동으로 수정해줘"

### 1-2. Authentication 패키지 설치 🤖

> 🤖 **AI에게 요청**:
> "Firebase Authentication에 필요한 모든 패키지를 backend/functions에 직접 설치해줘.
> - jsonwebtoken: JWT 토큰 생성/검증
> - bcryptjs: 비밀번호 암호화
> - validator: 입력값 검증
> - express-validator: Express 유효성 검사
> - 설치 진행 상황 실시간으로 보여줘"

---

## Step 2: 환경 변수 및 디렉토리 구성

### 2-1. 환경 변수 설정 👤

**목표**: 인증에 필요한 환경 변수를 설정합니다.

1. **`.env` 파일 편집**
   ```
   backend/functions/.env 열기
   ```

2. **다음 내용 추가**:
   ```env
   # Week 6 - Authentication Settings
   JWT_SECRET=your-super-secret-jwt-key-change-in-production
   JWT_EXPIRES_IN=24h
   BCRYPT_ROUNDS=12

   # Custom Claims
   ADMIN_EMAIL=admin@seniorhealth.com
   DEFAULT_ROLE=senior

   # Session Settings
   SESSION_TIMEOUT=86400
   REFRESH_TOKEN_EXPIRES=604800

   # Password Policy
   MIN_PASSWORD_LENGTH=8
   REQUIRE_SPECIAL_CHARS=true
   REQUIRE_NUMBERS=true
   ```

### 2-2. 프로젝트 구조 생성 🤖

> 🤖 **AI에게 요청**:
> "backend/functions에 인증 시스템을 위한 디렉토리 구조를 직접 생성해줘.
> - middleware/ 디렉토리 생성
> - utils/ 디렉토리 생성
> - models/ 디렉토리 생성
> - routes/ 디렉토리 생성
> - 각 디렉토리에 index.js 파일 생성"

---

## Step 3: 인증 미들웨어 구현

### 3-1. JWT 토큰 검증 미들웨어 🤖

> 🤖 **AI에게 요청**:
> "Firebase Authentication 미들웨어를 직접 구현해줘.
> - middleware/auth.js 파일 생성
> - JWT 토큰 검증 로직 구현
> - 역할 기반 접근 제어 구현
> - Senior 접근 권한 검증
> - 에러 처리 포함
> - 토큰 만료 처리"

### 3-2. Custom Claims 관리 시스템 🤖

> 🤖 **AI에게 요청**:
> "사용자 역할과 권한을 관리하는 시스템을 직접 구현해줘.
> - utils/userClaims.js 파일 생성
> - Senior 사용자 생성 함수
> - Caregiver 사용자 생성 함수
> - 권한 관리 함수
> - 역할별 권한 설정
> - Firestore 프로필 자동 생성"

---

## Step 4: 사용자 모델 및 검증

### 4-1. 사용자 데이터 모델 🤖

> 🤖 **AI에게 요청**:
> "사용자 데이터 모델을 직접 생성해줘.
> - models/user.js 파일 생성
> - Senior 사용자 스키마
> - Caregiver 사용자 스키마
> - 유효성 검증 규칙
> - 비밀번호 정책 적용"

### 4-2. 입력값 검증 유틸리티 🤖

> 🤖 **AI에게 요청**:
> "사용자 입력 검증 유틸리티를 직접 구현해줘.
> - utils/validators.js 파일 생성
> - 이메일 검증
> - 비밀번호 강도 검증
> - 이름 검증
> - 전화번호 검증 (선택사항)"

---

## Step 5: 회원가입 및 로그인 API

### 5-1. Senior 회원가입 API 🤖

> 🤖 **AI에게 요청**:
> "Senior 사용자 회원가입 API를 직접 구현해줘.
> - routes/auth.js 파일 생성
> - POST /api/auth/register/senior 엔드포인트
> - 입력값 검증
> - Firebase Auth 사용자 생성
> - Custom Claims 설정
> - Firestore 프로필 저장
> - 에러 처리 및 중복 체크"

### 5-2. Caregiver 회원가입 API 🤖

> 🤖 **AI에게 요청**:
> "Caregiver 사용자 회원가입 API를 직접 구현해줘.
> - POST /api/auth/register/caregiver 엔드포인트
> - 관리할 Senior ID 연결
> - 다중 Senior 관리 지원
> - 권한 설정
> - 프로필 생성"

### 5-3. 로그인 API 🤖

> 🤖 **AI에게 요청**:
> "로그인 API를 직접 구현해줘.
> - POST /api/auth/login 엔드포인트
> - Firebase 토큰 생성
> - Refresh 토큰 지원
> - 로그인 이력 저장
> - 비정상 로그인 감지"

---

## Step 6: 보호된 라우트 구현

### 6-1. 프로필 관리 API 🤖

> 🤖 **AI에게 요청**:
> "인증이 필요한 프로필 관리 API를 직접 구현해줘.
> - GET /api/profile - 프로필 조회
> - PUT /api/profile - 프로필 수정
> - DELETE /api/account - 계정 삭제
> - 인증 미들웨어 적용
> - 본인 데이터만 접근 가능"

### 6-2. 역할별 접근 제어 🤖

> 🤖 **AI에게 요청**:
> "역할 기반 접근 제어가 적용된 API를 직접 구현해줘.
> - GET /api/admin/users - 관리자 전용
> - GET /api/caregiver/seniors - 보호자 전용
> - GET /api/senior/health - 시니어 전용
> - 권한 검증 로직
> - 접근 거부 처리"

---

## Step 7: Firebase Console 설정

### 7-1. Authentication 활성화 👤

**목표**: Firebase Console에서 Authentication을 설정합니다.

1. **Firebase Console 접속**
   - https://console.firebase.google.com
   - 자신의 프로젝트 선택

2. **Authentication 설정**
   - Authentication 메뉴 클릭
   - Sign-in method 탭
   - 이메일/비밀번호 공급자 활성화
   - 저장

### 7-2. 테스트 사용자 생성 🤖

> 🤖 **AI에게 요청**:
> "테스트용 사용자를 자동으로 생성해줘.
> - test-users.js 스크립트 작성
> - Senior 테스트 사용자 3명 생성
> - Caregiver 테스트 사용자 2명 생성
> - 각 사용자에 적절한 Custom Claims 설정
> - 스크립트 실행 및 결과 표시"

---

## Step 8: 로컬 테스트 및 검증

### 8-1. Firebase 에뮬레이터 실행 🤖

> 🤖 **AI에게 요청**:
> "Firebase 에뮬레이터를 실행하고 Authentication을 테스트해줘.
> - Authentication 에뮬레이터 시작
> - Functions 에뮬레이터 시작
> - Firestore 에뮬레이터 시작
> - 에뮬레이터 UI URL 표시"

### 8-2. API 통합 테스트 🤖

> 🤖 **AI에게 요청**:
> "모든 인증 API를 테스트하고 결과를 보여줘.
> - Senior 회원가입 테스트
> - Caregiver 회원가입 테스트
> - 로그인 테스트
> - 토큰 검증 테스트
> - 프로필 조회 테스트
> - 권한 테스트
> - 각 테스트 결과와 응답 시간 표시"

---

## Step 9: Web 프론트엔드 Vercel 배포

### 9-1. Vercel 계정 생성 👤

**목표**: Vercel에 가입하고 프로젝트를 준비합니다.

1. **Vercel 가입**
   - https://vercel.com/signup
   - GitHub 계정으로 가입 (권장)
   - 이메일 인증 완료

### 9-2. Vercel CLI 설치 및 로그인 🤖

> 🤖 **AI에게 요청**:
> "Vercel CLI를 설치하고 로그인을 진행해줘.
> - Vercel CLI 글로벌 설치
> - vercel login 실행
> - 인증 완료 확인"

### 9-3. 환경 변수 설정 👤

**목표**: Web 애플리케이션의 환경 변수를 설정합니다.

1. **frontend/web/.env.local 파일 생성**
2. **Firebase 설정 정보 입력** (Firebase Console에서 확인)
   ```env
   NEXT_PUBLIC_FIREBASE_API_KEY=your-api-key
   NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   NEXT_PUBLIC_FIREBASE_PROJECT_ID=your-project-id
   ```

### 9-4. Vercel 배포 🤖

> 🤖 **AI에게 요청**:
> "Web 애플리케이션을 Vercel에 직접 배포해줘.
> - frontend/web 디렉토리로 이동
> - npm install 실행
> - npm run build로 빌드 테스트
> - vercel 명령으로 초기 배포
> - 프로젝트 이름: senior-mhealth-학번
> - 환경 변수 자동 설정
> - 배포 URL 표시"

### 9-5. 프로덕션 배포 및 검증 🤖

> 🤖 **AI에게 요청**:
> "프로덕션 환경에 배포하고 동작을 검증해줘.
> - vercel --prod 실행
> - 배포 상태 모니터링
> - 배포된 URL로 접속 테스트
> - 회원가입/로그인 기능 테스트
> - Firebase Console에서 사용자 생성 확인
> - CORS 설정 자동 업데이트"

---

## Step 10: 보안 설정 강화

### 10-1. Firestore 보안 규칙 🤖

> 🤖 **AI에게 요청**:
> "Firestore 보안 규칙을 강화해줘.
> - firestore.rules 파일 업데이트
> - 사용자별 데이터 접근 제한
> - 역할별 권한 규칙
> - Caregiver의 Senior 데이터 접근 허용
> - 규칙 배포 및 테스트"

### 10-2. 비밀번호 정책 강화 🤖

> 🤖 **AI에게 요청**:
> "비밀번호 정책을 강화하고 적용해줘.
> - 최소 8자, 대소문자, 숫자, 특수문자 필수
> - 최근 사용한 비밀번호 재사용 방지
> - 비밀번호 만료 정책 (90일)
> - 비밀번호 재설정 이메일 기능"

---

## 실습 검증

### 종합 검증 테스트 🤖

> 🤖 **AI에게 요청**:
> "Week 6 실습이 모두 완료되었는지 종합 검증하고 결과를 보여줘:
> - Authentication 시스템 동작 확인
> - 모든 API 엔드포인트 테스트
> - 역할별 접근 제어 검증
> - Vercel 배포 상태 확인
> - Firebase Console 사용자 목록
> - 보안 규칙 적용 상태
> 문제가 발견되면 자동으로 수정해줘."

---

## 프로젝트 구조 이해

```
Senior_MHealth/
├── backend/
│   └── functions/
│       ├── index.js            # Cloud Functions 메인
│       ├── middleware/         # 인증 미들웨어
│       │   └── auth.js
│       ├── utils/             # 유틸리티 함수
│       │   ├── userClaims.js
│       │   └── validators.js
│       ├── models/            # 데이터 모델
│       │   └── user.js
│       ├── routes/            # API 라우트
│       │   └── auth.js
│       └── test-users.js      # 테스트 사용자 생성
├── frontend/
│   └── web/                   # Next.js 웹 앱
│       ├── .env.local         # 환경 변수
│       └── vercel.json        # Vercel 설정
└── firestore.rules            # 보안 규칙
```

---

## 실습 완료! 🎉

### ✅ 체크리스트
- [x] Firebase Authentication 설정
- [x] JWT 토큰 기반 인증
- [x] Custom Claims 구현
- [x] Senior/Caregiver 역할 구분
- [x] 회원가입/로그인 API
- [x] 역할 기반 접근 제어
- [x] 보호된 라우트 구현
- [x] Vercel 웹 배포
- [x] 보안 규칙 적용
- [x] 통합 테스트 완료

### 🔒 보안 주의사항
- **JWT_SECRET**: 프로덕션에서는 강력한 시크릿 키 사용
- **비밀번호 정책**: 최소 8자, 복잡도 규칙 적용
- **CORS 설정**: 허용된 도메인만 접근 가능
- **Rate Limiting**: API 호출 제한 설정

### 📚 다음 단계
- **Week 7**: FCM 푸시 알림 시스템
- **Week 8**: 운영 및 모니터링

### 🆘 도움이 필요하면
- Firebase Auth 문서: https://firebase.google.com/docs/auth
- Vercel 문서: https://vercel.com/docs
- JWT 문서: https://jwt.io/introduction
- 강의 자료: `docs/` 디렉토리 참조