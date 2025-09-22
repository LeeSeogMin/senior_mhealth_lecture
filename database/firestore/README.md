# Firestore 구현

Senior_MHealth 프로젝트의 Firestore NoSQL 데이터베이스 구현입니다.

## 📋 개요

Firestore는 다음과 같은 역할을 합니다:
- **실시간 데이터 동기화**: 분석 세션, 실시간 상태
- **세션 데이터 관리**: 임시 데이터, 캐시
- **실시간 알림**: 푸시 알림, 상태 변경

## 🗄️ 컬렉션 구조

### 1. users (사용자 프로필)
```javascript
{
  uid: "firebase_uid",
  email: "user@example.com",
  displayName: "사용자명",
  phoneNumber: "+82-10-1234-5678",
  role: "caregiver", // caregiver, senior, admin
  createdAt: Timestamp,
  updatedAt: Timestamp,
  isActive: true,
  // Cloud SQL과 동기화
  cloudSqlId: 123
}
```

### 2. seniors (시니어 정보)
```javascript
{
  id: "senior_id",
  name: "김철수",
  birthDate: "1940-01-01",
  gender: "male",
  address: "서울시 강남구...",
  emergencyContact: "+82-10-1234-5678",
  medicalHistory: "고혈압, 당뇨...",
  createdAt: Timestamp,
  updatedAt: Timestamp,
  // Cloud SQL과 동기화
  cloudSqlId: 456
}
```

### 3. caregiver_senior_relationships (보호자-시니어 관계)
```javascript
{
  id: "caregiver_uid_senior_id",
  caregiverId: "caregiver_uid",
  seniorId: "senior_id",
  relationshipType: "자녀", // 자녀, 배우자, 친척 등
  isPrimaryCaregiver: true,
  createdAt: Timestamp
}
```

### 4. analysis_sessions (분석 세션)
```javascript
{
  id: "session_id",
  seniorId: "senior_id",
  caregiverId: "caregiver_uid",
  sessionType: "voice", // voice, video, text
  filePath: "gs://bucket/path/file.wav",
  fileSize: 1024000,
  durationSeconds: 300,
  status: "processing", // pending, processing, completed, failed
  createdAt: Timestamp,
  completedAt: Timestamp,
  // Cloud SQL 참조
  cloudSqlId: 789
}
```

### 5. analysis_results (분석 결과)
```javascript
{
  id: "result_id",
  sessionId: "session_id",
  depressionScore: 0.75, // 0.00-1.00
  anxietyScore: 0.60,
  stressScore: 0.80,
  overallMood: "negative", // positive, neutral, negative
  confidenceScore: 0.85,
  analysisSummary: "분석 요약...",
  recommendations: "권장사항...",
  createdAt: Timestamp
}
```

### 6. notification_settings (알림 설정)
```javascript
{
  userId: "user_uid",
  email: {
    enabled: true,
    thresholdScore: 0.7
  },
  push: {
    enabled: true,
    thresholdScore: 0.8
  },
  sms: {
    enabled: false,
    thresholdScore: 0.9
  }
}
```

### 7. system_settings (시스템 설정)
```javascript
{
  id: "global_settings",
  maintenanceMode: false,
  analysisEnabled: true,
  maxFileSize: 10485760, // 10MB
  supportedFormats: ["wav", "mp3", "mp4"],
  createdAt: Timestamp,
  updatedAt: Timestamp
}
```

### 8. logs (시스템 로그)
```javascript
{
  id: "log_id",
  level: "info", // debug, info, warning, error
  message: "로그 메시지",
  userId: "user_uid",
  sessionId: "session_id",
  metadata: {
    // 추가 메타데이터
  },
  createdAt: Timestamp
}
```

## 🔗 하이브리드 데이터베이스 동기화

### 데이터 분담
- **Cloud SQL**: 관계형 데이터, 사용자 계정, 시니어 정보
- **Firestore**: 실시간 데이터, 세션 데이터, 캐시

### 동기화 전략
1. **양방향 참조**: `cloudSqlId` 필드로 상호 참조
2. **실시간 업데이트**: Firestore 리스너로 실시간 동기화
3. **트랜잭션 처리**: 일관성 보장을 위한 배치 작업

### 동기화 예시
```javascript
// Cloud SQL에서 사용자 생성 시
const user = await UserModel.create({
  uid: firebaseUser.uid,
  email: firebaseUser.email,
  role: 'caregiver'
});

// Firestore에도 동기화
await firestore.collection('users').doc(firebaseUser.uid).set({
  uid: firebaseUser.uid,
  email: firebaseUser.email,
  role: 'caregiver',
  cloudSqlId: user.id,
  createdAt: new Date(),
  isActive: true
});
```

## 🔒 보안 규칙

### 인증 기반 접근 제어
- Firebase Authentication 필수
- 사용자별 데이터 접근 제한
- 역할 기반 권한 관리

### 데이터 보호
- 개인정보 암호화
- 민감 데이터 접근 로깅
- 자동 백업 및 복구

## 📊 성능 최적화

### 인덱스 전략
- 복합 인덱스: `seniorId + status`
- 배열 인덱스: `caregiverIds`
- 시간 기반 인덱스: `createdAt`

### 쿼리 최적화
- 페이지네이션: `limit()` 사용
- 필터링: 복합 쿼리 최소화
- 캐싱: 자동 캐싱 활용

## 🚀 Phase별 구현 계획

### Phase 1: 기초 인프라 구축 ✅
- [x] 기본 컬렉션 구조 설계
- [x] 보안 규칙 구현
- [x] Cloud SQL 연동 준비

### Phase 2: 백엔드 구축
- [ ] 실시간 리스너 구현
- [ ] 데이터 동기화 메커니즘
- [ ] 오프라인 지원

### Phase 3: AI/ML 통합
- [ ] 분석 세션 실시간 업데이트
- [ ] 결과 캐싱 최적화
- [ ] 성능 모니터링

### Phase 4: 프론트엔드 연결
- [ ] 실시간 UI 업데이트
- [ ] 오프라인 데이터 동기화
- [ ] 사용자 경험 최적화

### Phase 5: 운영 및 최적화
- [ ] 자동 백업 설정
- [ ] 성능 튜닝
- [ ] 비용 최적화

## 📁 파일 구조

```
database/firestore/
├── rules.rules              # 보안 규칙
├── indexes.json             # 인덱스 설정
├── schemas/                 # 스키마 정의
│   ├── User.ts             # 사용자 스키마
│   ├── Senior.ts           # 시니어 스키마
│   └── Analysis.ts         # 분석 스키마
├── sync/                    # 동기화 로직
│   ├── cloudSqlSync.ts     # Cloud SQL 동기화
│   └── realtimeSync.ts     # 실시간 동기화
└── README.md               # 이 문서
```

## 🔧 설정 및 배포

### Firebase 프로젝트 설정
```bash
# Firebase CLI 설치
npm install -g firebase-tools

# 프로젝트 초기화
firebase init firestore

# 보안 규칙 배포
firebase deploy --only firestore:rules
```

### 환경변수
```bash
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PRIVATE_KEY=your-private-key
FIREBASE_CLIENT_EMAIL=your-client-email
```

## 📈 모니터링

### 주요 지표
- 읽기/쓰기 작업량
- 실시간 연결 수
- 오류율 및 지연시간
- 저장소 사용량

### 로깅
- 보안 규칙 위반
- 성능 지표
- 사용자 활동

이 Firestore 구현을 통해 Senior_MHealth 시스템의 실시간 데이터를 효율적으로 관리할 수 있습니다.
