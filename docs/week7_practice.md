# Week 7: FCM 푸시 알림 시스템 - 실습편

## 🎯 실습 목표
Firebase Cloud Messaging을 사용하여 Senior MHealth의 실시간 알림 시스템을 구축하고, 건강 이상 감지 및 일일 리포트 알림을 구현합니다.

## 🔍 작업 구분
- **👤 사용자 직접 작업**: Firebase Console에서 수동으로 진행
- **🤖 AI 프롬프트**: AI에게 코드 작성을 요청하여 자동화

---

## Step 1: 사전 요구사항 및 패키지 설치

### 1-1. 기본 설정 확인 🤖

> 🤖 **AI에게 요청**:
> "Week 6까지의 설정이 완료되었는지 직접 확인해줘.
> - backend/functions 디렉토리 확인
> - 인증 설정 파일 확인
> - FCM 관련 패키지 자동 설치
> - firebase-admin, node-cron, moment 설치
> - 설치 진행 상황 실시간으로 보여줘"

### 1-2. 환경 변수 설정 👤

**목표**: FCM 설정에 필요한 환경 변수를 추가합니다.

`.env` 파일에 추가:
```env
# Week 7 - FCM Push Notification Settings
FCM_SERVER_KEY=your_fcm_server_key_here
FCM_SENDER_ID=your_fcm_sender_id_here

# Notification Settings
NOTIFICATION_BATCH_SIZE=500
NOTIFICATION_RETRY_COUNT=3
NOTIFICATION_QUIET_HOURS_START=22
NOTIFICATION_QUIET_HOURS_END=8

# Health Alert Thresholds
HEALTH_ALERT_ENABLED=true
EMERGENCY_ALERT_ENABLED=true
DAILY_REPORT_ENABLED=true
```

---

## Step 2: FCM 기본 알림 시스템 구현

### 2-1. 알림 전송 Function 🤖

> 🤖 **AI에게 요청**:
> "FCM 알림 전송 시스템을 직접 구현해줘.
> - sendNotification Cloud Function 생성
> - 사용자 FCM 토큰 조회 로직
> - 알림 전송 및 기록 저장
> - 에러 처리 및 재시도 로직
> - 알림 히스토리 Firestore 저장"

### 2-2. FCM 토큰 관리 API 🤖

> 🤖 **AI에게 요청**:
> "FCM 토큰 관리 시스템을 직접 구현해줘.
> - updateFCMToken API 생성
> - 토큰 등록/업데이트 기능
> - 토큰 유효성 검증
> - 멀티 디바이스 지원
> - 토큰 만료 처리"

---

## Step 3: 건강 이상 감지 알림

### 3-1. 이상 감지 트리거 🤖

> 🤖 **AI에게 요청**:
> "건강 데이터 이상 감지 시스템을 직접 구현해줘.
> - healthAnomalyAlert Firestore 트리거 생성
> - 심박수, 혈압 이상 감지 로직
> - 위험 수준별 알림 우선순위
> - 보호자 자동 알림
> - 긴급 알림 즉시 전송"

### 3-2. 알림 규칙 설정 🤖

> 🤖 **AI에게 요청**:
> "건강 이상 알림 규칙을 직접 설정해줘.
> - utils/alertRules.js 파일 생성
> - 수치별 위험도 판단 기준
> - 연령별 정상 범위 설정
> - 복합 조건 판단 로직
> - 알림 빈도 제한"

---

## Step 4: 일일 리포트 시스템

### 4-1. 리포트 스케줄러 🤖

> 🤖 **AI에게 요청**:
> "일일 건강 리포트 시스템을 직접 구현해줘.
> - dailyReportNotification 스케줄 Function 생성
> - 매일 오후 8시 자동 실행 (Asia/Seoul)
> - 일일 건강 데이터 집계
> - 평균값 및 트렌드 분석
> - 맞춤형 리포트 생성"

### 4-2. 리포트 템플릿 🤖

> 🤖 **AI에게 요청**:
> "리포트 템플릿 시스템을 직접 구현해줘.
> - templates/reports.js 파일 생성
> - 일일/주간/월간 리포트 템플릿
> - 건강 트렌드 시각화 데이터
> - 맞춤형 건강 조언 추가
> - 다국어 지원 (한국어/영어)"

---

## Step 5: 조용한 시간 및 우선순위 관리

### 5-1. 조용한 시간 시스템 🤖

> 🤖 **AI에게 요청**:
> "조용한 시간 관리 시스템을 직접 구현해줘.
> - isQuietHours 함수 구현
> - 시간대별 알림 제한
> - 긴급 알림 예외 처리
> - 지연 알림 큐 시스템
> - 다음날 아침 자동 전송"

### 5-2. 알림 우선순위 🤖

> 🤖 **AI에게 요청**:
> "알림 우선순위 시스템을 직접 구현해줘.
> - utils/notificationPriority.js 생성
> - emergency, high, normal, low 레벨
> - 우선순위별 전송 규칙
> - 배치 전송 최적화
> - 사용자별 알림 설정"

---

## Step 6: 배치 알림 및 성능 최적화

### 6-1. 배치 알림 시스템 🤖

> 🤖 **AI에게 요청**:
> "대량 알림 전송 시스템을 직접 구현해줘.
> - sendBatchNotifications 함수 생성
> - 500개씩 배치 처리
> - 실패 재시도 로직
> - 전송 결과 통계
> - 성능 모니터링"

### 6-2. 알림 큐 시스템 🤖

> 🤖 **AI에게 요청**:
> "알림 큐 시스템을 직접 구현해줘.
> - Cloud Tasks 연동 설정
> - 알림 큐 관리
> - 재시도 정책 설정
> - Dead Letter Queue 구현
> - 처리량 제한"

---

## Step 7: Firebase Console 설정

### 7-1. Cloud Messaging 활성화 👤

**목표**: Firebase Console에서 FCM을 설정합니다.

1. **Firebase Console 접속**
   - https://console.firebase.google.com
   - 자신의 프로젝트 선택

2. **Cloud Messaging 설정**
   - Cloud Messaging 메뉴 클릭
   - Web Push certificates 생성
   - Server Key 복사 → .env 파일에 저장

### 7-2. 알림 채널 설정 🤖

> 🤖 **AI에게 요청**:
> "FCM 알림 채널을 자동으로 설정해줘.
> - 건강 알림 채널
> - 일일 리포트 채널
> - 긴급 알림 채널
> - 복약 알림 채널
> - 각 채널별 설정 자동화"

---

## Step 8: Flutter 모바일 앱 연동

### 8-1. Flutter 환경 확인 👤

**목표**: Flutter 개발 환경을 준비합니다.

1. **Flutter 설치 확인**
   ```bash
   flutter --version
   ```

2. **Flutter 설치** (필요시)
   - Windows: https://docs.flutter.dev/get-started/install/windows
   - Mac: https://docs.flutter.dev/get-started/install/macos

### 8-2. Firebase 연동 설정 🤖

> 🤖 **AI에게 요청**:
> "Flutter 앱을 Firebase와 직접 연동해줘.
> - frontend/mobile 디렉토리로 이동
> - FlutterFire CLI 설치 및 설정
> - flutterfire configure 자동 실행
> - Android/iOS 플랫폼 설정
> - firebase_options.dart 자동 생성"

### 8-3. Android 설정 👤

**목표**: Android 앱 설정을 완료합니다.

1. **Firebase Console에서**:
   - 앱 추가 → Android
   - 패키지명: `com.example.senior_mhealth_mobile`
   - google-services.json 다운로드
   - android/app/ 폴더에 복사

### 8-4. iOS 설정 (Mac) 👤

**목표**: iOS 앱 설정을 완료합니다.

1. **Firebase Console에서**:
   - 앱 추가 → iOS
   - 번들 ID: `com.example.seniorMhealthMobile`
   - GoogleService-Info.plist 다운로드
   - Xcode로 추가

### 8-5. FCM 통합 테스트 🤖

> 🤖 **AI에게 요청**:
> "Flutter 앱에서 FCM을 테스트해줘.
> - FCM 초기화 코드 검증
> - 토큰 획득 및 출력
> - Backend API로 토큰 전송
> - 테스트 알림 전송
> - 알림 수신 확인"

---

## Step 9: 테스트 및 모니터링

### 9-1. 통합 테스트 스크립트 🤖

> 🤖 **AI에게 요청**:
> "FCM 시스템 전체를 테스트해줘.
> - test-fcm-system.js 스크립트 생성
> - 단일 알림 테스트
> - 배치 알림 테스트
> - 건강 이상 알림 시뮬레이션
> - 일일 리포트 테스트
> - 테스트 결과 리포트 생성"

### 9-2. 모니터링 설정 🤖

> 🤖 **AI에게 요청**:
> "FCM 모니터링 시스템을 구축해줘.
> - 알림 전송 성공률 추적
> - 실패 원인 분석
> - 전송 지연 시간 측정
> - 일일 통계 생성
> - Firebase Console 연동"

---

## Step 10: 프로덕션 배포

### 10-1. 배포 전 체크리스트 🤖

> 🤖 **AI에게 요청**:
> "프로덕션 배포를 위한 검증을 수행해줘.
> - 모든 환경 변수 확인
> - FCM 서버 키 검증
> - 알림 템플릿 테스트
> - 조용한 시간 설정 확인
> - 배치 크기 최적화"

### 10-2. Functions 배포 🤖

> 🤖 **AI에게 요청**:
> "FCM Functions를 프로덕션에 배포해줘.
> - firebase deploy --only functions
> - 배포 상태 모니터링
> - 배포 후 동작 검증
> - 알림 전송 테스트
> - 롤백 준비"

### 10-3. 모바일 앱 빌드 🤖

> 🤖 **AI에게 요청**:
> "모바일 앱을 배포용으로 빌드해줘.
> - Android APK 빌드 (release)
> - 빌드 파일 위치 확인
> - 서명 설정 (필요시)
> - 최종 테스트
> - 배포 준비 완료"

---

## 실습 검증

### 종합 검증 테스트 🤖

> 🤖 **AI에게 요청**:
> "Week 7 실습이 모두 완료되었는지 종합 검증하고 결과를 보여줘:
> - FCM 시스템 전체 동작 확인
> - 모든 알림 타입 테스트
> - 건강 이상 감지 동작
> - 일일 리포트 생성
> - 조용한 시간 동작
> - 모바일 앱 알림 수신
> 문제가 발견되면 자동으로 수정해줘."

---

## 프로젝트 구조 이해

```
Senior_MHealth/
├── backend/
│   └── functions/
│       ├── index.js            # FCM Functions
│       ├── utils/
│       │   ├── alertRules.js   # 알림 규칙
│       │   └── notificationPriority.js
│       ├── templates/          # 알림 템플릿
│       │   └── reports.js
│       └── test-fcm-system.js # 테스트 스크립트
├── frontend/
│   └── mobile/                # Flutter 앱
│       ├── lib/
│       │   ├── firebase_options.dart
│       │   └── main.dart
│       ├── android/
│       │   └── app/
│       │       └── google-services.json
│       └── ios/
│           └── Runner/
│               └── GoogleService-Info.plist
└── firebase.json             # Firebase 설정
```

---

## 실습 완료! 🎉

### ✅ 체크리스트
- [x] FCM 기본 설정
- [x] 알림 전송 시스템
- [x] 건강 이상 감지 알림
- [x] 일일 리포트 생성
- [x] 조용한 시간 관리
- [x] 배치 알림 처리
- [x] Flutter 앱 연동
- [x] 푸시 알림 테스트
- [x] 모니터링 설정
- [x] 프로덕션 배포

### 📱 알림 종류
- **긴급 알림**: 건강 위험 감지 시 즉시
- **일일 리포트**: 매일 오후 8시
- **복약 알림**: 설정된 시간
- **활동 알림**: 장시간 미활동 시

### 🔒 보안 주의사항
- **FCM 서버 키**: 절대 노출 금지
- **토큰 관리**: 안전한 저장 및 갱신
- **알림 내용**: 민감정보 포함 금지
- **권한 검증**: 알림 대상 확인 필수

### 📚 다음 단계
- **Week 8**: 운영 및 모니터링 시스템

### 🆘 도움이 필요하면
- FCM 문서: https://firebase.google.com/docs/cloud-messaging
- Flutter FCM: https://firebase.flutter.dev/docs/messaging
- Firebase Functions: https://firebase.google.com/docs/functions
- 강의 자료: `docs/` 디렉토리 참조