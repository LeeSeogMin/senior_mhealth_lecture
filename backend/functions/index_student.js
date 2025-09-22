/**
 * Senior MHealth Backend Functions
 * 백엔드 개발 실습 - 8주 과정
 *
 * 이 파일은 학생들이 주차별로 구현해야 할 백엔드 API 템플릿입니다.
 * 각 주차의 TODO를 완성하면서 실제 작동하는 헬스케어 백엔드를 구축하세요.
 */

const functions = require('firebase-functions');
const admin = require('firebase-admin');
const express = require('express');
const cors = require('cors');

// Firebase Admin 초기화
admin.initializeApp();

// Firestore와 Auth 참조
const db = admin.firestore();
const auth = admin.auth();

// ============================================================================
// Week 4: Cloud Functions 기본 구조
// ============================================================================

/**
 * TODO 1: Express 앱 생성 및 미들웨어 설정
 *
 * 구현 사항:
 * 1. Express 앱 인스턴스 생성
 * 2. CORS 설정 (web과 mobile 앱의 도메인 허용)
 * 3. JSON 파싱 미들웨어
 * 4. 요청 로깅 미들웨어
 *
 * 힌트:
 * - const app = express();
 * - app.use(cors({ origin: true }));
 * - app.use(express.json());
 */

// const app = express();
// TODO: 여기에 Express 설정을 구현하세요


/**
 * TODO 2: Health Check 엔드포인트
 * GET /health
 *
 * 응답 형식:
 * {
 *   status: "healthy",
 *   timestamp: "2024-01-20T10:00:00Z",
 *   version: "1.0.0",
 *   service: "senior-mhealth-backend"
 * }
 */

// app.get('/health', (req, res) => {
//   // TODO: 구현하세요
// });


/**
 * TODO 3: 기본 Cloud Function 내보내기
 *
 * 힌트:
 * - functions.https.onRequest() 사용
 * - Express 앱을 함수로 내보내기
 */

// exports.api = functions.https.onRequest(app);


// ============================================================================
// Week 5: Firestore 데이터베이스 연동
// ============================================================================

/**
 * TODO 4: 건강 데이터 생성 (POST /api/health-data)
 *
 * 요청 본문:
 * {
 *   seniorId: string,
 *   type: "heartRate" | "bloodPressure" | "steps" | "sleep",
 *   value: number,
 *   unit: string,
 *   timestamp: string
 * }
 *
 * 구현 사항:
 * 1. 요청 본문 검증
 * 2. Firestore에 데이터 저장
 * 3. 저장된 문서 ID와 함께 응답
 *
 * 힌트:
 * - db.collection('healthData').add() 사용
 * - 타임스탬프는 admin.firestore.Timestamp 사용
 */

// app.post('/api/health-data', async (req, res) => {
//   try {
//     // TODO: 구현하세요
//   } catch (error) {
//     res.status(500).json({ error: error.message });
//   }
// });


/**
 * TODO 5: 건강 데이터 조회 (GET /api/health-data/:seniorId)
 *
 * 쿼리 파라미터:
 * - startDate: 시작 날짜 (선택)
 * - endDate: 종료 날짜 (선택)
 * - type: 데이터 유형 (선택)
 *
 * 구현 사항:
 * 1. seniorId로 필터링
 * 2. 날짜 범위 필터링
 * 3. 데이터 유형 필터링
 * 4. 시간 역순 정렬
 */

// app.get('/api/health-data/:seniorId', async (req, res) => {
//   try {
//     // TODO: 구현하세요
//   } catch (error) {
//     res.status(500).json({ error: error.message });
//   }
// });


/**
 * TODO 6: 건강 데이터 업데이트 (PUT /api/health-data/:id)
 */

// app.put('/api/health-data/:id', async (req, res) => {
//   try {
//     // TODO: 구현하세요
//   } catch (error) {
//     res.status(500).json({ error: error.message });
//   }
// });


/**
 * TODO 7: 건강 데이터 삭제 (DELETE /api/health-data/:id)
 */

// app.delete('/api/health-data/:id', async (req, res) => {
//   try {
//     // TODO: 구현하세요
//   } catch (error) {
//     res.status(500).json({ error: error.message });
//   }
// });


// ============================================================================
// Week 6: 인증 및 보안
// ============================================================================

/**
 * TODO 8: 인증 미들웨어 구현
 *
 * 구현 사항:
 * 1. Authorization 헤더에서 Bearer 토큰 추출
 * 2. Firebase Admin SDK로 토큰 검증
 * 3. 사용자 정보를 req.user에 저장
 * 4. 다음 미들웨어로 전달
 *
 * 힌트:
 * - auth.verifyIdToken(token) 사용
 * - 토큰이 없거나 유효하지 않으면 401 응답
 */

// const authenticateUser = async (req, res, next) => {
//   try {
//     // TODO: 구현하세요
//   } catch (error) {
//     res.status(401).json({ error: 'Unauthorized' });
//   }
// };


/**
 * TODO 9: 역할 기반 접근 제어 (RBAC)
 *
 * 구현 사항:
 * 1. 사용자의 커스텀 클레임에서 역할 확인
 * 2. senior, caregiver, admin 역할 구분
 * 3. 역할에 따른 접근 권한 제어
 */

// const requireRole = (roles) => {
//   return (req, res, next) => {
//     // TODO: 구현하세요
//   };
// };


/**
 * TODO 10: 보안이 적용된 사용자 프로필 API
 * GET /api/users/profile (인증 필요)
 * PUT /api/users/profile (인증 필요)
 */

// app.get('/api/users/profile', authenticateUser, async (req, res) => {
//   try {
//     // TODO: 구현하세요
//   } catch (error) {
//     res.status(500).json({ error: error.message });
//   }
// });


// ============================================================================
// Week 7: 실시간 기능 및 알림
// ============================================================================

/**
 * TODO 11: Firestore 트리거 - 건강 이상 감지
 *
 * 구현 사항:
 * 1. healthData 컬렉션 변경 감지
 * 2. 임계값 초과 시 알림 생성
 * 3. alerts 컬렉션에 저장
 *
 * 임계값:
 * - 심박수: < 60 또는 > 100
 * - 수축기 혈압: > 140
 * - 이완기 혈압: > 90
 */

// exports.detectHealthAnomaly = functions.firestore
//   .document('healthData/{docId}')
//   .onCreate(async (snap, context) => {
//     const data = snap.data();
//     // TODO: 구현하세요
//   });


/**
 * TODO 12: FCM 푸시 알림 전송
 *
 * 구현 사항:
 * 1. 대상 사용자의 FCM 토큰 조회
 * 2. 알림 메시지 구성
 * 3. FCM으로 전송
 *
 * 힌트:
 * - admin.messaging().send() 사용
 */

// exports.sendNotification = functions.https.onCall(async (data, context) => {
//   // 인증 확인
//   if (!context.auth) {
//     throw new functions.https.HttpsError('unauthenticated', '인증이 필요합니다');
//   }
//
//   try {
//     // TODO: 구현하세요
//   } catch (error) {
//     throw new functions.https.HttpsError('internal', error.message);
//   }
// });


/**
 * TODO 13: 스케줄 함수 - 일일 리포트 생성
 *
 * 구현 사항:
 * 1. 매일 오전 9시에 실행
 * 2. 전날의 건강 데이터 집계
 * 3. 일일 리포트 생성 및 저장
 * 4. 보호자에게 알림 전송
 */

// exports.dailyReport = functions.pubsub
//   .schedule('0 9 * * *')
//   .timeZone('Asia/Seoul')
//   .onRun(async (context) => {
//     // TODO: 구현하세요
//   });


// ============================================================================
// Week 8: 프로덕션 최적화
// ============================================================================

/**
 * TODO 14: 캐싱 미들웨어
 *
 * 구현 사항:
 * 1. 메모리 캐시 구현
 * 2. 캐시 키 생성
 * 3. 캐시 만료 시간 설정
 */

// const cache = new Map();
// const cacheMiddleware = (duration = 60) => {
//   return (req, res, next) => {
//     // TODO: 구현하세요
//   };
// };


/**
 * TODO 15: Rate Limiting
 *
 * 구현 사항:
 * 1. IP 기반 요청 제한
 * 2. 시간당 요청 수 제한
 * 3. 429 Too Many Requests 응답
 */

// const rateLimiter = new Map();
// const rateLimitMiddleware = (maxRequests = 100, windowMs = 3600000) => {
//   return (req, res, next) => {
//     // TODO: 구현하세요
//   };
// };


/**
 * TODO 16: 에러 처리 미들웨어
 *
 * 구현 사항:
 * 1. 모든 에러 캐치
 * 2. 에러 로깅
 * 3. 클라이언트 친화적 에러 응답
 */

// const errorHandler = (err, req, res, next) => {
//   // TODO: 구현하세요
// };


/**
 * TODO 17: 로깅 및 모니터링
 *
 * 구현 사항:
 * 1. 구조화된 로깅
 * 2. 성능 메트릭 수집
 * 3. Cloud Logging 통합
 */

// const logger = {
//   info: (message, metadata) => {
//     // TODO: 구현하세요
//   },
//   error: (message, error) => {
//     // TODO: 구현하세요
//   }
// };


// ============================================================================
// 테스트용 엔드포인트 (개발 중에만 사용)
// ============================================================================

// 개발 환경에서 API 테스트용
exports.testAPI = functions.https.onRequest((req, res) => {
  res.json({
    message: "Senior MHealth Backend API - 학생 실습 버전",
    timestamp: new Date().toISOString(),
    hint: "index.js 파일의 TODO를 완성하세요!"
  });
});


// ============================================================================
// 📚 참고 자료 및 힌트
// ============================================================================

/**
 * Firestore 쿼리 예제:
 *
 * // 단일 문서 조회
 * const doc = await db.collection('users').doc('userId').get();
 *
 * // 조건부 쿼리
 * const snapshot = await db.collection('healthData')
 *   .where('seniorId', '==', 'senior123')
 *   .orderBy('timestamp', 'desc')
 *   .limit(10)
 *   .get();
 *
 * // 배치 쓰기
 * const batch = db.batch();
 * batch.set(docRef1, data1);
 * batch.update(docRef2, data2);
 * batch.delete(docRef3);
 * await batch.commit();
 */

/**
 * FCM 메시지 형식:
 *
 * const message = {
 *   notification: {
 *     title: '건강 알림',
 *     body: '심박수가 비정상입니다'
 *   },
 *   data: {
 *     type: 'health_alert',
 *     seniorId: 'senior123'
 *   },
 *   token: 'fcm_token_here'
 * };
 *
 * await admin.messaging().send(message);
 */

/**
 * 유용한 유틸리티 함수들:
 */

// 날짜 형식 변환
const formatDate = (timestamp) => {
  return new Date(timestamp).toISOString();
};

// 입력 검증
const validateInput = (data, requiredFields) => {
  for (const field of requiredFields) {
    if (!data[field]) {
      throw new Error(`${field} is required`);
    }
  }
};

// 응답 헬퍼
const sendSuccess = (res, data, message = 'Success') => {
  res.status(200).json({
    success: true,
    message,
    data
  });
};

const sendError = (res, statusCode, message) => {
  res.status(statusCode).json({
    success: false,
    message
  });
};