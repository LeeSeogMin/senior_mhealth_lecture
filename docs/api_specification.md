# Senior mHealth API 명세서 및 데이터 스키마

## 📋 목차
1. [API 개요](#api-개요)
2. [인증 시스템](#인증-시스템)
3. [2주차: Authentication API](#2주차-authentication-api)
4. [3주차: Health Data CRUD API](#3주차-health-data-crud-api)
5. [4주차: Cloud Functions 트리거](#4주차-cloud-functions-트리거)
6. [5주차: Storage & AI API](#5주차-storage--ai-api)
7. [6주차: FCM 알림 API](#6주차-fcm-알림-api)
8. [데이터 스키마](#데이터-스키마)
9. [에러 코드](#에러-코드)

---

## API 개요

### Base URL
- **개발환경**: `http://localhost:5001/senior-mhealth-472007/us-central1`
- **프로덕션**: `https://us-central1-senior-mhealth-472007.cloudfunctions.net`

### 공통 응답 형식
```json
{
  "success": true,
  "message": "성공",
  "data": {},
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

### 에러 응답 형식
```json
{
  "success": false,
  "message": "에러 메시지",
  "error": "상세 에러 정보",
  "timestamp": "2024-01-01T00:00:00.000Z"
}
```

---

## 인증 시스템

### Firebase Authentication 토큰
모든 API 요청은 다음 헤더가 필요합니다:

```http
Authorization: Bearer <Firebase_ID_Token>
Content-Type: application/json
```

### Custom Claims 구조
```json
{
  "userType": "senior" | "caregiver",
  "permissions": ["read:health_data", "write:health_data"],
  "managedSeniors": ["senior_id_1", "senior_id_2"]
}
```

---

## 2주차: Authentication API

### POST /authAPI/register
사용자 회원가입

**요청:**
```json
{
  "email": "user@example.com",
  "password": "password123",
  "name": "홍길동",
  "userType": "senior",
  "additionalInfo": {
    "age": 70,
    "phone": "010-1234-5678"
  }
}
```

**응답:**
```json
{
  "success": true,
  "message": "회원가입 성공",
  "data": {
    "uid": "firebase_user_id",
    "email": "user@example.com",
    "userType": "senior",
    "customClaims": {
      "userType": "senior",
      "permissions": ["read:health_data", "write:health_data"]
    }
  }
}
```

### POST /authAPI/login
사용자 로그인

**요청:**
```json
{
  "email": "user@example.com",
  "password": "password123"
}
```

**응답:**
```json
{
  "success": true,
  "message": "로그인 성공",
  "data": {
    "idToken": "firebase_id_token",
    "refreshToken": "firebase_refresh_token",
    "user": {
      "uid": "firebase_user_id",
      "email": "user@example.com",
      "userType": "senior"
    }
  }
}
```

### POST /authAPI/refresh
토큰 갱신

**요청:**
```json
{
  "refreshToken": "firebase_refresh_token"
}
```

**응답:**
```json
{
  "success": true,
  "message": "토큰 갱신 성공",
  "data": {
    "idToken": "new_firebase_id_token",
    "refreshToken": "new_firebase_refresh_token"
  }
}
```

---

## 3주차: Health Data CRUD API

### POST /healthAPI/data
건강 데이터 생성

**요청:**
```json
{
  "type": "blood_pressure",
  "values": {
    "systolic": 120,
    "diastolic": 80,
    "pulse": 72
  },
  "unit": "mmHg",
  "notes": "아침 측정",
  "measuredAt": "2024-01-01T09:00:00.000Z"
}
```

**응답:**
```json
{
  "success": true,
  "message": "건강 데이터 저장 완료",
  "data": {
    "id": "health_data_id",
    "userId": "user_id",
    "type": "blood_pressure",
    "values": {
      "systolic": 120,
      "diastolic": 80,
      "pulse": 72
    },
    "createdAt": "2024-01-01T09:00:00.000Z"
  }
}
```

### GET /healthAPI/data
건강 데이터 조회

**쿼리 파라미터:**
- `type`: 데이터 타입 (blood_pressure, blood_sugar, weight 등)
- `startDate`: 시작 날짜 (ISO 8601)
- `endDate`: 종료 날짜 (ISO 8601)
- `limit`: 제한 개수 (기본: 50)

**요청:**
```http
GET /healthAPI/data?type=blood_pressure&startDate=2024-01-01&limit=10
```

**응답:**
```json
{
  "success": true,
  "message": "건강 데이터 조회 완료",
  "data": {
    "items": [
      {
        "id": "health_data_id",
        "type": "blood_pressure",
        "values": { "systolic": 120, "diastolic": 80 },
        "measuredAt": "2024-01-01T09:00:00.000Z"
      }
    ],
    "total": 1,
    "hasMore": false
  }
}
```

### PUT /healthAPI/data/{dataId}
건강 데이터 수정

**요청:**
```json
{
  "values": {
    "systolic": 125,
    "diastolic": 82,
    "pulse": 75
  },
  "notes": "오후 재측정"
}
```

### DELETE /healthAPI/data/{dataId}
건강 데이터 삭제

**응답:**
```json
{
  "success": true,
  "message": "건강 데이터 삭제 완료"
}
```

---

## 4주차: Cloud Functions 트리거

### POST /reportAPI/generate
리포트 생성 API

**요청:**
```json
{
  "userId": "user_id",
  "type": "daily" | "weekly" | "monthly",
  "startDate": "2024-01-01",
  "endDate": "2024-01-07",
  "includeAnalysis": true
}
```

**응답:**
```json
{
  "success": true,
  "message": "리포트 생성 완료",
  "data": {
    "reportId": "report_id",
    "type": "daily",
    "summary": {
      "totalMeasurements": 14,
      "averageValues": {
        "systolic": 125,
        "diastolic": 82
      },
      "trends": "안정적",
      "alerts": []
    },
    "generatedAt": "2024-01-01T10:00:00.000Z"
  }
}
```

### GET /reportAPI/reports/{reportId}
리포트 조회

**응답:**
```json
{
  "success": true,
  "message": "리포트 조회 완료",
  "data": {
    "reportId": "report_id",
    "userId": "user_id",
    "type": "daily",
    "period": {
      "startDate": "2024-01-01",
      "endDate": "2024-01-07"
    },
    "data": {
      "measurements": [],
      "analysis": {},
      "recommendations": []
    }
  }
}
```

---

## 5주차: Storage & AI API

### POST /voiceAPI/upload
음성 파일 업로드

**요청 (multipart/form-data):**
```
Content-Type: multipart/form-data

file: [음성 파일]
metadata: {
  "seniorId": "senior_id",
  "duration": 30,
  "recordedAt": "2024-01-01T10:00:00.000Z"
}
```

**응답:**
```json
{
  "success": true,
  "message": "음성 파일 업로드 완료",
  "data": {
    "fileId": "voice_file_id",
    "fileName": "voice_20240101_100000.wav",
    "uploadUrl": "gs://bucket/voice_analysis/user_id/call_id/file.wav",
    "size": 1024000,
    "status": "uploaded"
  }
}
```

### POST /aiAPI/analyze-voice
AI 음성 분석 요청

**요청:**
```json
{
  "fileId": "voice_file_id",
  "analysisType": "emotion" | "speech_pattern" | "health_indicators",
  "options": {
    "includeTranscript": true,
    "detectAnomalies": true
  }
}
```

**응답:**
```json
{
  "success": true,
  "message": "AI 분석 시작",
  "data": {
    "analysisId": "analysis_id",
    "status": "processing",
    "estimatedTime": "30초",
    "callbackUrl": "/aiAPI/analysis-result/{analysisId}"
  }
}
```

### GET /aiAPI/analysis-result/{analysisId}
AI 분석 결과 조회

**응답:**
```json
{
  "success": true,
  "message": "분석 완료",
  "data": {
    "analysisId": "analysis_id",
    "fileId": "voice_file_id",
    "status": "completed",
    "result": {
      "transcript": "음성 인식 결과",
      "emotions": {
        "happiness": 0.7,
        "sadness": 0.1,
        "anger": 0.05,
        "fear": 0.15
      },
      "healthIndicators": {
        "voiceStability": "정상",
        "speechClarity": 85,
        "pausePattern": "정상"
      },
      "anomalies": [],
      "confidence": 0.92
    },
    "completedAt": "2024-01-01T10:02:00.000Z"
  }
}
```

---

## 6주차: FCM 알림 API

### POST /notificationAPI/send
알림 발송

**요청:**
```json
{
  "targetUsers": ["user_id_1", "user_id_2"],
  "type": "health_alert" | "reminder" | "system",
  "title": "건강 이상 감지",
  "body": "혈압 수치가 정상 범위를 벗어났습니다.",
  "data": {
    "alertType": "blood_pressure_high",
    "value": "150/95",
    "timestamp": "2024-01-01T10:00:00.000Z"
  },
  "priority": "high" | "normal",
  "scheduleAt": "2024-01-01T11:00:00.000Z"
}
```

**응답:**
```json
{
  "success": true,
  "message": "알림 발송 완료",
  "data": {
    "notificationId": "notification_id",
    "sentCount": 2,
    "failedCount": 0,
    "sentAt": "2024-01-01T10:01:00.000Z"
  }
}
```

### GET /notificationAPI/history
알림 내역 조회

**쿼리 파라미터:**
- `type`: 알림 타입
- `startDate`: 시작 날짜
- `endDate`: 종료 날짜
- `limit`: 제한 개수

**응답:**
```json
{
  "success": true,
  "message": "알림 내역 조회 완료",
  "data": {
    "notifications": [
      {
        "id": "notification_id",
        "type": "health_alert",
        "title": "건강 이상 감지",
        "sentAt": "2024-01-01T10:01:00.000Z",
        "status": "delivered"
      }
    ],
    "total": 1
  }
}
```

---

## 데이터 스키마

### users 컬렉션
```json
{
  "userId": "firebase_user_id",
  "email": "user@example.com",
  "name": "홍길동",
  "userType": "senior" | "caregiver",
  "profile": {
    "age": 70,
    "gender": "male" | "female",
    "phone": "010-1234-5678",
    "emergencyContact": "010-9876-5432",
    "photoURL": "https://storage.googleapis.com/profile.jpg"
  },
  "preferences": {
    "language": "ko",
    "timezone": "Asia/Seoul",
    "notifications": {
      "email": true,
      "push": true,
      "sms": false
    }
  },
  "createdAt": "2024-01-01T00:00:00.000Z",
  "updatedAt": "2024-01-01T00:00:00.000Z",
  "lastLoginAt": "2024-01-01T00:00:00.000Z"
}
```

### healthData 컬렉션
```json
{
  "id": "health_data_id",
  "userId": "user_id",
  "type": "blood_pressure" | "blood_sugar" | "weight" | "heart_rate",
  "values": {
    "systolic": 120,
    "diastolic": 80,
    "pulse": 72
  },
  "unit": "mmHg",
  "notes": "측정 메모",
  "location": "집",
  "device": "오므론 혈압계",
  "measuredAt": "2024-01-01T09:00:00.000Z",
  "createdAt": "2024-01-01T09:05:00.000Z",
  "tags": ["아침", "약물복용후"]
}
```

### voiceFiles 컬렉션
```json
{
  "fileId": "voice_file_id",
  "userId": "user_id",
  "seniorId": "senior_id",
  "fileName": "voice_20240101_100000.wav",
  "storagePath": "voice_analysis/user_id/call_id/file.wav",
  "size": 1024000,
  "duration": 30,
  "format": "wav",
  "sampleRate": 44100,
  "status": "uploaded" | "processing" | "analyzed" | "error",
  "metadata": {
    "recordedAt": "2024-01-01T10:00:00.000Z",
    "device": "iPhone",
    "quality": "high"
  },
  "uploadedAt": "2024-01-01T10:01:00.000Z"
}
```

### analyses 컬렉션
```json
{
  "analysisId": "analysis_id",
  "fileId": "voice_file_id",
  "userId": "user_id",
  "seniorId": "senior_id",
  "type": "voice_analysis",
  "status": "processing" | "completed" | "failed",
  "result": {
    "transcript": "음성 인식 텍스트",
    "emotions": {
      "happiness": 0.7,
      "sadness": 0.1,
      "anger": 0.05,
      "fear": 0.15
    },
    "healthIndicators": {
      "voiceStability": "정상",
      "speechClarity": 85,
      "pausePattern": "정상",
      "volume": "적정"
    },
    "anomalies": [],
    "confidence": 0.92,
    "aiModel": "gemini-pro",
    "processingTime": 25
  },
  "createdAt": "2024-01-01T10:00:00.000Z",
  "completedAt": "2024-01-01T10:02:00.000Z"
}
```

### notifications 컬렉션
```json
{
  "notificationId": "notification_id",
  "userId": "target_user_id",
  "type": "health_alert" | "reminder" | "system" | "caregiver_alert",
  "title": "알림 제목",
  "body": "알림 내용",
  "data": {
    "alertType": "blood_pressure_high",
    "value": "150/95",
    "actionRequired": true,
    "deepLink": "/health-data/blood-pressure"
  },
  "priority": "high" | "normal" | "low",
  "status": "sent" | "delivered" | "read" | "failed",
  "channels": ["fcm", "email", "sms"],
  "scheduledAt": "2024-01-01T10:00:00.000Z",
  "sentAt": "2024-01-01T10:01:00.000Z",
  "readAt": "2024-01-01T10:05:00.000Z"
}
```

### reports 컬렉션
```json
{
  "reportId": "report_id",
  "userId": "user_id",
  "type": "daily" | "weekly" | "monthly",
  "period": {
    "startDate": "2024-01-01",
    "endDate": "2024-01-07"
  },
  "summary": {
    "totalMeasurements": 14,
    "averageValues": {
      "systolic": 125,
      "diastolic": 82
    },
    "trends": "상승" | "하락" | "안정",
    "alerts": ["혈압 상승 경향"],
    "recommendations": ["정기적인 측정 권장"]
  },
  "data": {
    "measurements": [],
    "charts": [],
    "analysis": {}
  },
  "format": "json" | "pdf",
  "status": "generated" | "sent" | "viewed",
  "generatedAt": "2024-01-01T10:00:00.000Z"
}
```

---

## 에러 코드

### 인증 관련 (AUTH_*)
- `AUTH_001`: 인증 토큰이 없음
- `AUTH_002`: 유효하지 않은 토큰
- `AUTH_003`: 토큰이 만료됨
- `AUTH_004`: 권한이 부족함
- `AUTH_005`: 사용자를 찾을 수 없음

### 데이터 관련 (DATA_*)
- `DATA_001`: 필수 필드가 누락됨
- `DATA_002`: 유효하지 않은 데이터 형식
- `DATA_003`: 데이터를 찾을 수 없음
- `DATA_004`: 데이터 저장 실패
- `DATA_005`: 데이터 삭제 실패

### 파일 관련 (FILE_*)
- `FILE_001`: 파일 업로드 실패
- `FILE_002`: 지원하지 않는 파일 형식
- `FILE_003`: 파일 크기 초과
- `FILE_004`: 파일을 찾을 수 없음
- `FILE_005`: 파일 처리 중 오류

### AI 분석 관련 (AI_*)
- `AI_001`: AI 서비스 연결 실패
- `AI_002`: 분석 처리 중 오류
- `AI_003`: 분석 결과를 찾을 수 없음
- `AI_004`: 지원하지 않는 분석 타입
- `AI_005`: AI 서비스 할당량 초과

### 알림 관련 (NOTIFICATION_*)
- `NOTIFICATION_001`: FCM 토큰이 유효하지 않음
- `NOTIFICATION_002`: 알림 발송 실패
- `NOTIFICATION_003`: 지원하지 않는 알림 타입
- `NOTIFICATION_004`: 알림 스케줄링 실패

### 시스템 관련 (SYSTEM_*)
- `SYSTEM_001`: 서버 내부 오류
- `SYSTEM_002`: 데이터베이스 연결 실패
- `SYSTEM_003`: 외부 서비스 연결 실패
- `SYSTEM_004`: 서비스 일시 중단
- `SYSTEM_005`: 요청 처리 시간 초과

---

## 🚨 중요 참고사항

### 1. 보안 가이드라인
- 모든 API는 Firebase Authentication 토큰 필수
- 사용자는 본인의 데이터만 접근 가능
- 민감한 정보는 로그에 기록하지 않음
- HTTPS 통신 필수

### 2. 에러 처리
- 모든 API는 일관된 에러 응답 형식 사용
- 에러 코드와 메시지는 한국어로 제공
- 디버깅을 위한 상세 정보는 개발환경에서만 제공

### 3. 성능 고려사항
- 페이지네이션을 통한 대용량 데이터 처리
- 적절한 캐싱 전략 적용
- 데이터베이스 인덱스 최적화

### 4. 테스트 방법
- Firebase 에뮬레이터를 활용한 로컬 테스트
- Postman 또는 Thunder Client를 활용한 API 테스트
- 다양한 사용자 시나리오 테스트

이 API 명세서는 학생들이 각 주차별로 구현할 백엔드 기능의 상세한 가이드라인을 제공합니다. 실제 구현 시 이 명세서를 참고하여 일관된 API 설계를 유지하세요.