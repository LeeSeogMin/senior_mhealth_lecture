/**
 * Senior mHealth Backend Functions
 * 학생 실습용 템플릿 - 주차별로 구현해주세요!
 */

const functions = require('firebase-functions');
const admin = require('firebase-admin');

// Firebase Admin 초기화
admin.initializeApp();

// Firestore 참조
const db = admin.firestore();
const auth = admin.auth();

// ============================================================================
// 2주차 TODO: Authentication API 구현
// ============================================================================

/**
 * 사용자 회원가입 API
 * POST /api/auth/register
 *
 * Body: {
 *   email: string,
 *   password: string,
 *   name: string,
 *   role: 'senior' | 'caregiver'
 * }
 */
// exports.authAPI = functions.https.onRequest(async (req, res) => {
//   // TODO: 2주차에 구현하세요
//   // 1. Express 앱 설정
//   // 2. CORS 설정
//   // 3. 회원가입 엔드포인트 구현
//   // 4. 로그인 엔드포인트 구현
//   // 5. Custom Claims 설정
// });

// ============================================================================
// 3주차 TODO: Health Data CRUD API 구현
// ============================================================================

/**
 * 건강 데이터 CRUD API
 * GET/POST/PUT/DELETE /api/health-data
 */
// exports.healthAPI = functions.https.onRequest(async (req, res) => {
//   // TODO: 3주차에 구현하세요
//   // 1. 건강 데이터 생성 (CREATE)
//   // 2. 건강 데이터 조회 (READ)
//   // 3. 건강 데이터 수정 (UPDATE)
//   // 4. 건강 데이터 삭제 (DELETE)
//   // 5. 실시간 리스너 설정
// });

// ============================================================================
// 4주차 TODO: Cloud Functions 트리거 및 스케줄러 구현
// ============================================================================

/**
 * Firestore 트리거 - 건강 데이터 변경 감지
 */
// exports.detectHealthAnomaly = functions.firestore
//   .document('users/{userId}/healthData/{docId}')
//   .onCreate(async (snap, context) => {
//     // TODO: 4주차에 구현하세요
//     // 1. 건강 이상 수치 감지
//     // 2. alerts 컬렉션에 알림 생성
//     // 3. 보호자에게 알림 발송 준비
//   });

/**
 * 스케줄 함수 - 일일 리포트 생성
 */
// exports.dailyReportScheduler = functions.pubsub
//   .schedule('0 9 * * *')
//   .timeZone('Asia/Seoul')
//   .onRun(async (context) => {
//     // TODO: 4주차에 구현하세요
//     // 1. 모든 활성 사용자 조회
//     // 2. 전날 건강 데이터 집계
//     // 3. 일일 리포트 생성
//     // 4. reports 컬렉션에 저장
//   });

/**
 * HTTP Functions - 리포트 생성 API
 */
// exports.reportAPI = functions.https.onRequest(async (req, res) => {
//   // TODO: 4주차에 구현하세요
//   // 1. POST /api/reports/generate 엔드포인트
//   // 2. 건강 데이터 집계 및 분석
//   // 3. PDF 또는 JSON 형식으로 리포트 생성
// });

// ============================================================================
// 5주차 TODO: Storage, AI 연동, FCM 알림 구현
// ============================================================================

/**
 * 음성 파일 업로드 API
 */
// exports.voiceAPI = functions.https.onRequest(async (req, res) => {
//   // TODO: 5주차에 구현하세요
//   // 1. POST /api/voice/upload 엔드포인트
//   // 2. Multer로 파일 업로드 처리
//   // 3. Cloud Storage에 저장
//   // 4. 메타데이터 Firestore 저장
// });

/**
 * Storage 트리거 - 음성 파일 자동 처리
 */
// exports.processVoiceFile = functions.storage
//   .object()
//   .onFinalize(async (object) => {
//     // TODO: 5주차에 구현하세요
//     // 1. 음성 파일 메타데이터 추출
//     // 2. Firestore 업데이트
//     // 3. AI 분석 큐에 추가
//   });

/**
 * AI 분석 API
 */
// exports.aiAPI = functions.https.onRequest(async (req, res) => {
//   // TODO: 5주차에 구현하세요
//   // 1. POST /api/ai/analyze-voice 엔드포인트
//   // 2. Gemini API 호출 (시뮬레이션)
//   // 3. 분석 결과 저장
//   // 4. 이상 감지 시 알림 트리거
// });

/**
 * FCM 알림 API
 */
// exports.notificationAPI = functions.https.onRequest(async (req, res) => {
//   // TODO: 5주차에 구현하세요
//   // 1. POST /api/notifications/send 엔드포인트
//   // 2. FCM 메시지 생성
//   // 3. 대상별 알림 발송
// });

// ============================================================================
// 6주차 TODO: 프로덕션 배포 준비
// ============================================================================

/**
 * 헬스체크 API
 */
// exports.healthCheck = functions.https.onRequest(async (req, res) => {
//   // TODO: 6주차에 구현하세요
//   // 1. 시스템 상태 확인
//   // 2. 데이터베이스 연결 확인
//   // 3. 외부 API 상태 확인
// });

// ============================================================================
// 유틸리티 함수들 (참고용)
// ============================================================================

/**
 * 인증 미들웨어 (참고용)
 */
async function authenticateUser(req, res, next) {
  try {
    const token = req.headers.authorization?.split('Bearer ')[1];
    if (!token) {
      return res.status(401).json({ error: '토큰이 필요합니다' });
    }

    const decodedToken = await auth.verifyIdToken(token);
    req.user = decodedToken;
    next();
  } catch (error) {
    return res.status(401).json({ error: '유효하지 않은 토큰입니다' });
  }
}

/**
 * 에러 처리 미들웨어 (참고용)
 */
function handleError(error, req, res, next) {
  console.error('에러 발생:', error);
  res.status(500).json({
    error: '서버 내부 오류',
    message: error.message
  });
}

/**
 * 성공 응답 헬퍼 (참고용)
 */
function sendSuccess(res, data, message = '성공') {
  res.status(200).json({
    success: true,
    message: message,
    data: data
  });
}

/**
 * 에러 응답 헬퍼 (참고용)
 */
function sendError(res, statusCode, message, error = null) {
  res.status(statusCode).json({
    success: false,
    message: message,
    error: error
  });
}

// ============================================================================
// 개발용 테스트 함수 (삭제 예정)
// ============================================================================

/**
 * 테스트용 Hello World
 * 개발 환경에서만 사용 (프로덕션에서는 삭제)
 */
exports.helloWorld = functions.https.onRequest((request, response) => {
  functions.logger.info("Hello World 함수 호출됨", { structuredData: true });
  response.send("Hello from Senior mHealth Backend! 🏥💪");
});

/**
 * 테스트용 데이터베이스 연결 확인
 */
exports.testDB = functions.https.onRequest(async (request, response) => {
  try {
    // Firestore 연결 테스트
    const testDoc = await db.collection('test').doc('connection').get();
    response.json({
      success: true,
      message: 'Firestore 연결 성공',
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    response.status(500).json({
      success: false,
      message: 'Firestore 연결 실패',
      error: error.message
    });
  }
});

// ============================================================================
// 주의사항 및 가이드라인
// ============================================================================

/**
 * 🚨 개발 시 주의사항:
 *
 * 1. 각 주차별로 주석을 해제하며 구현하세요
 * 2. 에러 처리를 반드시 포함하세요
 * 3. 로그를 적절히 남기세요 (functions.logger 사용)
 * 4. 보안을 고려하여 인증/인가를 구현하세요
 * 5. API 응답 형식을 일관성 있게 유지하세요
 *
 * 📚 참고 자료:
 * - Firebase Functions 문서: https://firebase.google.com/docs/functions
 * - Express.js 문서: https://expressjs.com/
 * - Firebase Admin SDK: https://firebase.google.com/docs/admin/setup
 */