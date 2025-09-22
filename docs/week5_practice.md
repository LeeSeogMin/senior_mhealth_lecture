# Week 5: 백엔드 개발 (Firestore) - 실습편

## 🎯 실습 목표
Firestore 데이터베이스를 활용하여 Senior MHealth의 핵심 기능인 사용자 관리와 건강 데이터 저장 API를 구현합니다.

## 🔍 작업 구분
- **👤 사용자 직접 작업**: Firebase Console에서 수동으로 진행
- **🤖 AI 프롬프트**: AI에게 코드 작성을 요청하여 자동화

---

## Step 1: Firestore 데이터베이스 설정

### 1-1. Firestore 초기화 확인 👤

**목표**: Firestore 데이터베이스가 올바르게 설정되었는지 확인합니다.

1. **Firebase Console 접속**
   - https://console.firebase.google.com
   - 자신의 프로젝트 선택
   - Firestore Database 메뉴 클릭

2. **데이터베이스 상태 확인**
   - 테스트 모드인지 확인
   - 리전이 asia-northeast3인지 확인
   - 만료 날짜 확인 (30일 후)

### 1-2. 컬렉션 구조 설계 🤖

> 🤖 **AI에게 요청**:
> "Firestore에 Senior MHealth 데이터 구조를 자동으로 설정해줘.
> - users 컬렉션: 사용자 프로필 정보
> - healthRecords 컬렉션: 건강 측정 데이터
> - medications 컬렉션: 복약 정보
> - appointments 컬렉션: 진료 예약
> - 각 컬렉션에 샘플 문서 자동 생성
> - 인덱스 자동 생성"

### 1-3. 보안 규칙 설정 🤖

> 🤖 **AI에게 요청**:
> "Firestore 보안 규칙을 자동으로 설정해줘.
> - 인증된 사용자만 읽기/쓰기 가능
> - 사용자는 자신의 데이터만 접근 가능
> - 관리자는 모든 데이터 접근 가능
> - firestore.rules 파일 자동 생성
> - 규칙 테스트 및 배포"

---

## Step 2: Firebase Admin SDK 설정

### 2-1. Admin SDK 초기화 🤖

> 🤖 **AI에게 요청**:
> "backend/functions에 Firebase Admin SDK를 설정해줘.
> - serviceAccountKey.json 파일 확인
> - Admin SDK 초기화 코드 작성
> - Firestore 클라이언트 설정
> - 환경별 설정 분리 (개발/프로덕션)
> - 에러 처리 추가"

### 2-2. 데이터베이스 연결 테스트 🤖

> 🤖 **AI에게 요청**:
> "Firestore 연결을 테스트하고 결과를 보여줘.
> - 테스트 문서 생성
> - 문서 읽기 테스트
> - 문서 업데이트 테스트
> - 문서 삭제 테스트
> - 연결 상태 및 지연 시간 표시"

---

## Step 3: 사용자 관리 API 개발

### 3-1. 사용자 등록 API 🤖

> 🤖 **AI에게 요청**:
> "사용자 등록 API를 구현해줘.
> - POST /users/register 엔드포인트
> - Firebase Authentication과 연동
> - 사용자 프로필 Firestore 저장
> - 입력 검증 (이메일, 비밀번호, 이름, 나이)
> - 중복 가입 방지
> - 회원 가입 환영 이메일 발송 (선택사항)"

### 3-2. 사용자 프로필 API 🤖

> 🤖 **AI에게 요청**:
> "사용자 프로필 관리 API를 구현해줘.
> - GET /users/profile - 프로필 조회
> - PUT /users/profile - 프로필 수정
> - DELETE /users/account - 계정 삭제
> - 프로필 이미지 업로드 (Cloud Storage 연동)
> - JWT 토큰 기반 인증
> - 권한 검증 미들웨어"

### 3-3. 보호자 연결 기능 🤖

> 🤖 **AI에게 요청**:
> "시니어와 보호자 연결 기능을 구현해줘.
> - POST /users/link-guardian - 보호자 연결 요청
> - GET /users/guardians - 연결된 보호자 목록
> - POST /users/accept-link - 연결 승인
> - 연결 코드 생성 (6자리)
> - 실시간 알림 (FCM 연동)"

---

## Step 4: 건강 데이터 API 개발

### 4-1. 건강 기록 저장 API 🤖

> 🤖 **AI에게 요청**:
> "건강 데이터 저장 API를 구현해줘.
> - POST /health/record - 건강 데이터 저장
> - 혈압, 맥박, 혈당, 체온, 체중 필드
> - 측정 시간 자동 기록
> - 비정상 수치 자동 감지
> - 보호자에게 자동 알림 (위험 수치일 때)
> - 일일 측정 횟수 제한"

### 4-2. 건강 기록 조회 API 🤖

> 🤖 **AI에게 요청**:
> "건강 데이터 조회 및 분석 API를 구현해줘.
> - GET /health/records - 기록 목록 조회
> - GET /health/records/:id - 특정 기록 조회
> - GET /health/statistics - 통계 분석
> - 기간별 필터링 (일/주/월)
> - 페이지네이션 구현
> - 데이터 집계 (평균, 최대, 최소)"

### 4-3. AI 건강 분석 통합 🤖

> 🤖 **AI에게 요청**:
> "Vertex AI를 활용한 건강 분석 기능을 추가해줘.
> - POST /health/analyze - AI 건강 분석
> - 최근 7일 데이터 자동 수집
> - Gemini 모델로 패턴 분석
> - 건강 위험도 평가
> - 맞춤형 건강 조언 생성
> - 분석 결과 저장 및 이력 관리"

---

## Step 5: 복약 관리 API 개발

### 5-1. 복약 정보 관리 🤖

> 🤖 **AI에게 요청**:
> "복약 관리 API를 구현해줘.
> - POST /medications - 약물 정보 등록
> - GET /medications - 복약 목록 조회
> - PUT /medications/:id - 복약 정보 수정
> - DELETE /medications/:id - 복약 정보 삭제
> - 복용 시간 알림 설정
> - 약물 상호작용 경고 (선택사항)"

### 5-2. 복약 기록 추적 🤖

> 🤖 **AI에게 요청**:
> "복약 기록 추적 시스템을 구현해줘.
> - POST /medications/:id/taken - 복약 기록
> - GET /medications/history - 복약 이력 조회
> - GET /medications/adherence - 복약 순응도 분석
> - 미복약 알림 자동 발송
> - 주간/월간 복약 리포트 생성"

---

## Step 6: 실시간 기능 구현

### 6-1. 실시간 데이터 동기화 🤖

> 🤖 **AI에게 요청**:
> "Firestore 실시간 리스너를 구현해줘.
> - 건강 데이터 실시간 업데이트
> - 보호자 대시보드 실시간 동기화
> - 알림 실시간 전송
> - 연결 상태 모니터링
> - 오프라인 지원 설정"

### 6-2. 푸시 알림 시스템 🤖

> 🤖 **AI에게 요청**:
> "FCM을 활용한 푸시 알림 시스템을 구현해줘.
> - 복약 알림 예약 발송
> - 건강 이상 징후 즉시 알림
> - 보호자 알림 설정 관리
> - 알림 히스토리 저장
> - 알림 읽음 상태 추적"

---

## Step 7: 배치 작업 및 스케줄러

### 7-1. 일일 리포트 생성 👤

**목표**: 매일 자정에 실행되는 리포트 생성 작업을 설정합니다.

1. **Firebase Console에서 Cloud Scheduler 설정**
   - Extensions → Cloud Scheduler
   - 새 작업 생성
   - 실행 시간: 매일 00:00
   - 타임존: Asia/Seoul

### 7-2. 스케줄 함수 구현 🤖

> 🤖 **AI에게 요청**:
> "일일 건강 리포트 생성 스케줄러를 구현해줘.
> - Cloud Scheduler와 연동
> - 매일 자정 실행
> - 사용자별 일일 건강 요약 생성
> - 이상 징후 자동 감지
> - 보호자에게 일일 리포트 이메일 발송
> - 실행 로그 저장"

---

## Step 8: 테스트 및 배포

### 8-1. 통합 테스트 🤖

> 🤖 **AI에게 요청**:
> "모든 API 엔드포인트의 통합 테스트를 수행해줘.
> - 사용자 등록부터 건강 기록까지 전체 플로우 테스트
> - 각 API의 성공/실패 케이스 테스트
> - 성능 테스트 (응답 시간, 동시 접속)
> - 보안 테스트 (인증, 권한)
> - 테스트 결과 리포트 생성"

### 8-2. 프로덕션 배포 🤖

> 🤖 **AI에게 요청**:
> "백엔드를 프로덕션 환경에 배포해줘.
> - 환경 변수 프로덕션 설정
> - Firestore 보안 규칙 배포
> - Cloud Functions 배포
> - 배포 상태 모니터링
> - 롤백 준비"

### 8-3. 배포 검증 🤖

> 🤖 **AI에게 요청**:
> "프로덕션 환경을 검증하고 결과를 보여줘.
> - 모든 API 엔드포인트 동작 확인
> - Firestore 데이터 쓰기/읽기 테스트
> - 실시간 기능 동작 확인
> - 푸시 알림 발송 테스트
> - 성능 메트릭 수집"

---

## 실습 검증

### 종합 검증 테스트 🤖

> 🤖 **AI에게 요청**:
> "Week 5 실습이 모두 완료되었는지 종합 검증하고 결과를 보여줘:
> - Firestore 데이터베이스 구조 확인
> - 모든 API 엔드포인트 목록 및 상태
> - 실시간 기능 동작 상태
> - 보안 규칙 적용 상태
> - 스케줄러 설정 상태
> - 데이터 백업 상태
> 문제가 발견되면 자동으로 수정해줘."

---

## 프로젝트 구조 이해

```
Senior_MHealth/
├── backend/
│   └── functions/
│       ├── index.js            # Cloud Functions 메인
│       ├── src/
│       │   ├── models/        # 데이터 모델
│       │   │   ├── user.js
│       │   │   ├── health.js
│       │   │   └── medication.js
│       │   ├── routes/        # API 라우트
│       │   │   ├── users.js
│       │   │   ├── health.js
│       │   │   └── medications.js
│       │   ├── services/      # 비즈니스 로직
│       │   │   ├── firestore.js
│       │   │   ├── auth.js
│       │   │   └── notification.js
│       │   └── utils/         # 유틸리티
│       │       ├── validators.js
│       │       └── helpers.js
│       └── tests/            # 테스트 코드
├── firestore.rules           # 보안 규칙
├── firestore.indexes.json    # 인덱스 설정
└── firebase.json            # Firebase 설정
```

---

## 실습 완료! 🎉

### ✅ 체크리스트
- [x] Firestore 데이터베이스 설정
- [x] 컬렉션 구조 설계 및 생성
- [x] 보안 규칙 구성
- [x] 사용자 관리 API 구현
- [x] 건강 데이터 API 구현
- [x] 복약 관리 API 구현
- [x] 실시간 동기화 구현
- [x] 푸시 알림 시스템 구축
- [x] 배치 작업 스케줄러 설정
- [x] 통합 테스트 완료

### 💾 데이터베이스 구조
```
📁 users (컬렉션)
  └── {userId} (문서)
      ├── name: string
      ├── email: string
      ├── age: number
      ├── role: 'senior' | 'guardian'
      └── createdAt: timestamp

📁 healthRecords (컬렉션)
  └── {recordId} (문서)
      ├── userId: string
      ├── bloodPressure: object
      ├── heartRate: number
      ├── temperature: number
      └── measuredAt: timestamp

📁 medications (컬렉션)
  └── {medicationId} (문서)
      ├── userId: string
      ├── name: string
      ├── dosage: string
      └── schedule: array
```

### 🔒 보안 주의사항
- **보안 규칙**: 프로덕션 전 반드시 강화
- **인증 검증**: 모든 API에 인증 미들웨어
- **데이터 검증**: 입력값 검증 필수
- **백업 설정**: 일일 자동 백업 구성

### 📚 다음 단계
- **Week 6**: 웹 애플리케이션 배포 (Vercel)
- **Week 7**: Flutter 모바일 앱 개발
- **Week 8**: 운영 및 모니터링

### 🆘 도움이 필요하면
- Firestore 문서: https://firebase.google.com/docs/firestore
- Firebase Admin SDK: https://firebase.google.com/docs/admin/setup
- Cloud Functions 문서: https://firebase.google.com/docs/functions
- 강의 자료: `docs/` 디렉토리 참조