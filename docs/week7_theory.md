# Week 7: FCM 푸시 알림 시스템 - 이론편

## 📚 학습 목표
Firebase Cloud Messaging(FCM)의 원리를 이해하고, 실시간 푸시 알림 시스템을 구축하는 방법을 학습합니다. 다양한 알림 시나리오와 배포 준비 과정을 다룹니다.

## 🌟 핵심 개념

### 1. 푸시 알림(Push Notification)이란?
**정의**: 서버에서 클라이언트 디바이스로 직접 전송하는 메시지

**Pull vs Push 방식**:
```
Pull (클라이언트 요청):
클라이언트 ──요청──> 서버
클라이언트 <──응답── 서버

Push (서버 전송):
서버 ──알림 전송──> 클라이언트
(클라이언트 요청 없이 자동 수신)
```

### 2. FCM 아키텍처
```
┌────────────────────────────────────────┐
│           애플리케이션 서버              │
│         (Cloud Functions)               │
└──────────────┬─────────────────────────┘
               │ 메시지 전송
               ▼
┌────────────────────────────────────────┐
│            FCM 서버                     │
│         (Google 인프라)                 │
└──────────┬──────────┬──────────────────┘
           │          │
           ▼          ▼
    ┌──────────┐ ┌──────────┐
    │ Android  │ │   iOS    │
    │  Device  │ │  Device  │
    └──────────┘ └──────────┘
```

### 3. 메시지 유형

#### 알림 메시지 (Notification Message)
```javascript
{
  notification: {
    title: "건강 알림",
    body: "오늘 걸음수 목표를 달성했습니다!",
    icon: "notification_icon",
    sound: "default"
  }
}
```
- 자동으로 시스템 트레이에 표시
- 앱이 백그라운드일 때 자동 처리

#### 데이터 메시지 (Data Message)
```javascript
{
  data: {
    type: "health_update",
    seniorId: "senior001",
    heartRate: "75",
    timestamp: "2024-01-20T10:30:00Z"
  }
}
```
- 앱에서 직접 처리
- 백그라운드에서도 커스텀 로직 실행

#### 혼합 메시지
```javascript
{
  notification: { /* ... */ },
  data: { /* ... */ }
}
```

### 4. FCM 토큰
**정의**: 각 디바이스를 고유하게 식별하는 문자열

```
토큰 생명주기:
생성 → 저장 → 사용 → 갱신 → 만료
 │      │      │      │      │
 │      │      │      │      └─ 앱 삭제/재설치
 │      │      │      └─ 주기적 갱신
 │      │      └─ 알림 전송
 │      └─ 서버에 저장
 └─ 앱 설치/첫 실행
```

## 🔧 주요 기능

### 알림 시나리오 분류

| 유형 | 설명 | 예시 |
|------|------|------|
| **즉시 알림** | 즉각 전송 | 긴급 건강 상태 |
| **예약 알림** | 특정 시간 전송 | 약 복용 시간 |
| **조건부 알림** | 특정 조건 충족 시 | 심박수 이상 |
| **배치 알림** | 여러 사용자 동시 | 일일 리포트 |
| **토픽 알림** | 구독 기반 | 건강 팁 구독 |

### 알림 우선순위
```
HIGH (높음):
├── 즉시 전달
├── 디바이스 깨우기
└── 예: 긴급 알림

NORMAL (보통):
├── 일반 전달
├── 배터리 최적화
└── 예: 일반 알림

LOW (낮음):
├── 지연 가능
├── 배터리 절약
└── 예: 홍보 메시지
```

## 💡 용어 설명

| 용어 | 설명 | 예시 |
|-----|------|------|
| **FCM Token** | 디바이스 식별자 | `fKBd3...xyz` |
| **Topic** | 구독 채널 | `/topics/health_tips` |
| **Payload** | 메시지 내용 | JSON 데이터 |
| **TTL** | Time To Live | 메시지 유효 기간 |
| **Priority** | 전송 우선순위 | high, normal |
| **Sound** | 알림 소리 | default, custom |

## 📊 알림 처리 플로우

### 건강 이상 알림 플로우
```
1. 건강 데이터 수집
       ↓
2. 이상 수치 감지
       ↓
3. 알림 대상 결정
       ↓
4. FCM 메시지 생성
       ↓
5. 토큰별 전송
       ↓
6. 디바이스 수신
       ↓
7. 사용자 확인
       ↓
8. 알림 기록 저장
```

### 스케줄 알림 시스템
```javascript
// Cloud Scheduler 구조
┌──────────────┐
│  Scheduler   │
│  (cron job)  │
└──────┬───────┘
       │ 트리거
       ▼
┌──────────────┐
│   Function   │
│ (알림 로직)   │
└──────┬───────┘
       │ 실행
       ▼
┌──────────────┐
│     FCM      │
│   (전송)     │
└──────────────┘
```

## 🎯 학습 체크리스트

- [ ] Push vs Pull 방식의 차이 이해
- [ ] FCM 아키텍처 구조 파악
- [ ] 알림/데이터 메시지 구분
- [ ] FCM 토큰 관리 방법 이해
- [ ] 알림 우선순위 설정 이해
- [ ] 스케줄 알림 구현 방법 파악

## 🔍 심화 개념

### 알림 채널 (Android)
```javascript
// Android 알림 채널 설정
const channel = {
  id: 'health_alerts',
  name: '건강 알림',
  importance: 'high',
  vibration: true,
  sound: 'notification_sound.mp3'
};
```

### 조용한 시간 (Quiet Hours)
```javascript
function isQuietHours() {
  const hour = new Date().getHours();
  return hour >= 22 || hour < 8; // 오후 10시 ~ 오전 8시
}

if (!isQuietHours() || priority === 'emergency') {
  // 알림 전송
}
```

### 배치 전송 최적화
```javascript
// 500개씩 배치 전송
async function sendBatchNotifications(tokens, message) {
  const batchSize = 500;
  const batches = [];

  for (let i = 0; i < tokens.length; i += batchSize) {
    const batch = tokens.slice(i, i + batchSize);
    batches.push(
      admin.messaging().sendMulticast({
        tokens: batch,
        ...message
      })
    );
  }

  return Promise.all(batches);
}
```

### 실패 처리 및 재시도
```javascript
async function sendWithRetry(token, message, retries = 3) {
  for (let i = 0; i < retries; i++) {
    try {
      return await admin.messaging().send({
        token,
        ...message
      });
    } catch (error) {
      if (error.code === 'messaging/registration-token-not-registered') {
        // 토큰 삭제
        await removeToken(token);
        break;
      }
      if (i === retries - 1) throw error;
      await new Promise(resolve => setTimeout(resolve, 1000 * Math.pow(2, i)));
    }
  }
}
```

## 배포 준비 사항

### 1. FCM 설정
- Firebase Console에서 Cloud Messaging 활성화
- 서버 키 및 발신자 ID 확인
- iOS의 경우 APNs 인증서 설정

### 2. 클라이언트 설정
```javascript
// 클라이언트 토큰 획득
const token = await firebase.messaging().getToken();

// 토큰 갱신 리스너
firebase.messaging().onTokenRefresh(async () => {
  const newToken = await firebase.messaging().getToken();
  // 서버에 새 토큰 업데이트
});
```

### 3. 권한 요청
```javascript
// 알림 권한 요청
const permission = await Notification.requestPermission();
if (permission === 'granted') {
  // 알림 활성화
}
```

## 🚀 다음 단계
Week 8에서는 프로덕션 배포를 위한 성능 최적화, 모니터링 설정, 그리고 실제 배포 과정을 학습합니다.