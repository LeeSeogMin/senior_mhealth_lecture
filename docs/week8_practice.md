# Week 8: 프로덕션 배포 및 최적화 - 실습편

## 🎯 실습 목표
Senior MHealth 애플리케이션의 성능을 최적화하고, 모니터링을 설정하며, 프로덕션 환경에 배포하는 과정을 실습합니다.

## 📝 실습 순서 (week8-setup.sh 기반)

### Step 1: 사전 요구사항 확인
**목표**: Week 7까지의 설정이 완료되었는지 확인합니다.

```bash
# 프롬프트: Functions 환경 설정 확인
cat backend/functions/.env | grep FCM

# 프롬프트: Firebase 설정 파일 확인
ls firebase.json
```

**경로**: `C:\Senior_MHealth`

**확인 사항**:
- FCM 설정 완료
- firebase.json 존재
- 개인 Firebase 프로젝트 설정 완료

---

### Step 2: 성능 최적화 패키지 설치
**목표**: 성능 모니터링과 최적화에 필요한 패키지를 설치합니다.

```bash
# 프롬프트: Functions 디렉토리로 이동
cd backend/functions

# 프롬프트: 성능 최적화 패키지 설치
npm install @google-cloud/logging@^10.0.0 @google-cloud/monitoring@^4.0.0 @google-cloud/trace-agent@^7.0.0 compression@^1.7.0 express-slow-down@^1.4.0 memory-cache@^0.2.0 node-cache@^5.1.0
```

**경로**: `C:\Senior_MHealth\backend\functions`

**패키지 설명**:
- `@google-cloud/logging`: 로그 수집
- `@google-cloud/monitoring`: 성능 모니터링
- `compression`: 응답 압축
- `express-slow-down`: 속도 제한
- `node-cache`: 메모리 캐싱

---

### Step 3: 개발/테스트 도구 설치
**목표**: 테스트와 성능 측정 도구를 설치합니다.

```bash
# 프롬프트: 개발 도구 설치
npm install --save-dev firebase-functions-test@^3.0.0 mocha@^10.0.0 chai@^4.3.0 nyc@^15.1.0 lighthouse@^11.0.0 autocannon@^7.0.0
```

**경로**: `C:\Senior_MHealth\backend\functions`

**도구 설명**:
- `mocha`, `chai`: 테스트 프레임워크
- `nyc`: 코드 커버리지
- `lighthouse`: 성능 측정
- `autocannon`: 부하 테스트

---

### Step 4: 프로덕션 환경 변수 설정
**목표**: 프로덕션 환경에 필요한 설정을 추가합니다.

`.env.template` 파일을 기반으로 `.env` 파일 생성:
```bash
# 프롬프트: 환경 변수 템플릿 복사
cp .env.template .env

# 프롬프트: .env 파일 편집하여 자신의 프로젝트 정보 입력
```

`.env` 파일에 추가:
```env
# Week 8 - Production Environment Settings
NODE_ENV=production
PRODUCTION_MODE=true

# 자신의 Firebase 프로젝트 정보
FIREBASE_PROJECT_ID=your-project-id
FIREBASE_PROJECT_LOCATION=asia-northeast3

# Performance Settings
CACHE_TTL=3600
RATE_LIMIT_WINDOW=900000
RATE_LIMIT_MAX=1000
CONNECTION_POOL_SIZE=10

# Monitoring Settings
ENABLE_LOGGING=true
ENABLE_MONITORING=true
ENABLE_TRACING=true
LOG_LEVEL=info

# Security Settings (프로덕션용 URL로 변경)
ALLOWED_ORIGINS=https://your-project-id.web.app,https://your-project-id.firebaseapp.com,https://your-vercel-app.vercel.app
ENABLE_CORS_STRICT=true
ENABLE_HELMET=true
ENABLE_COMPRESSION=true

# Database Settings
FIRESTORE_CACHE_SIZE=100000000
FIRESTORE_OFFLINE_PERSISTENCE=true

# Function Settings
MAX_INSTANCES=100
MIN_INSTANCES=1
CONCURRENCY=80
MEMORY_ALLOCATION=1GB
TIMEOUT_SECONDS=300
```

**경로**: `C:\Senior_MHealth\backend\functions\.env`

---

### Step 5: 성능 모니터링 미들웨어 구현
**목표**: 성능을 모니터링하고 최적화하는 미들웨어를 작성합니다.

`performance.js` 파일 생성:
```javascript
// Week 8 - Performance Optimization & Monitoring

const compression = require('compression');
const slowDown = require('express-slow-down');
const NodeCache = require('node-cache');
const { Logging } = require('@google-cloud/logging');
const { Monitoring } = require('@google-cloud/monitoring');

// Cache 설정
const cache = new NodeCache({
  stdTTL: parseInt(process.env.CACHE_TTL) || 3600,
  checkperiod: 120,
  useClones: false,
});

// Logging 설정 (프로젝트 ID는 환경 변수에서 가져옴)
const logging = new Logging({
  projectId: process.env.FIREBASE_PROJECT_ID
});
const log = logging.log('senior-mhealth-functions');

// Performance 미들웨어
const performanceMiddleware = {
  // Compression 미들웨어
  compression: compression({
    level: 6,
    threshold: 1024,
    filter: (req, res) => {
      if (req.headers['x-no-compression']) {
        return false;
      }
      return compression.filter(req, res);
    },
  }),

  // Rate limiting
  rateLimiter: slowDown({
    windowMs: parseInt(process.env.RATE_LIMIT_WINDOW) || 900000,
    delayAfter: 100,
    delayMs: 500,
    maxDelayMs: 20000,
    skipSuccessfulRequests: true,
  }),

  // 캐시 미들웨어
  cacheMiddleware: (duration = 300) => {
    return (req, res, next) => {
      const key = `cache_${req.originalUrl || req.url}`;
      const cachedResponse = cache.get(key);

      if (cachedResponse) {
        return res.json(cachedResponse);
      }

      res.sendResponse = res.json;
      res.json = (body) => {
        cache.set(key, body, duration);
        res.sendResponse(body);
      };

      next();
    };
  },

  // 성능 모니터링
  performanceMonitor: (req, res, next) => {
    const startTime = Date.now();

    res.on('finish', () => {
      const duration = Date.now() - startTime;
      const statusCode = res.statusCode;

      // 로그 기록
      log.write(log.entry({
        resource: { type: 'cloud_function' },
        severity: statusCode >= 400 ? 'ERROR' : 'INFO',
      }, {
        method: req.method,
        url: req.url,
        statusCode,
        duration,
        userAgent: req.get('User-Agent'),
        timestamp: new Date().toISOString(),
      }));
    });

    next();
  },
};

// 헬스체크 함수
function createHealthCheck() {
  return async (req, res) => {
    const startTime = Date.now();

    try {
      // 데이터베이스 연결 확인
      const admin = require('firebase-admin');
      const testDoc = await admin.firestore()
        .collection('health-check')
        .doc('test')
        .get();

      const dbLatency = Date.now() - startTime;

      res.json({
        status: 'healthy',
        timestamp: new Date().toISOString(),
        version: process.env.npm_package_version || '1.0.0',
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        dbLatency,
        environment: process.env.NODE_ENV,
        projectId: process.env.FIREBASE_PROJECT_ID,
      });

    } catch (error) {
      res.status(503).json({
        status: 'unhealthy',
        error: error.message,
        timestamp: new Date().toISOString(),
      });
    }
  };
}

module.exports = {
  performanceMiddleware,
  createHealthCheck,
  cache,
};
```

**경로**: `C:\Senior_MHealth\backend\functions\performance.js`

---

### Step 6: 최적화된 API 엔드포인트 구현
**목표**: 성능 미들웨어를 적용한 최적화된 API를 구현합니다.

```javascript
// 프롬프트: index.js에 최적화된 API를 추가하세요

const { performanceMiddleware, createHealthCheck } = require('./performance');

// 헬스체크 엔드포인트
exports.healthCheck = onRequest(
  {
    timeoutSeconds: 30,
    memory: '256MB',
    minInstances: 1,
  },
  (req, res) => {
    const healthCheck = createHealthCheck();
    healthCheck(req, res);
  }
);

// 최적화된 API
exports.optimizedAPI = onRequest(
  {
    timeoutSeconds: 300,
    memory: '2GB',
    minInstances: parseInt(process.env.MIN_INSTANCES) || 1,
    maxInstances: parseInt(process.env.MAX_INSTANCES) || 100,
    concurrency: parseInt(process.env.CONCURRENCY) || 80,
  },
  (req, res) => {
    const app = express();

    // 성능 미들웨어 적용
    app.use(performanceMiddleware.compression);
    app.use(performanceMiddleware.rateLimiter);
    app.use(performanceMiddleware.performanceMonitor);
    app.use(performanceMiddleware.cacheMiddleware(600)); // 10분 캐시

    app.use(cors({
      origin: process.env.ALLOWED_ORIGINS?.split(',') || ['http://localhost:3000'],
      credentials: true,
    }));

    // 기존 라우트들
    app.get('/api/health-data/:seniorId', /* ... */);
    app.post('/api/health-data', /* ... */);

    return app(req, res);
  }
);
```

**경로**: `C:\Senior_MHealth\backend\functions\index.js` (추가)

---

### Step 7: 유닛 테스트 작성
**목표**: Functions에 대한 기본 테스트를 작성합니다.

`test/index.test.js` 파일 생성:
```javascript
// 프롬프트: test 디렉토리를 생성하고 테스트 파일을 작성하세요

const { expect } = require('chai');
const admin = require('firebase-admin');
const test = require('firebase-functions-test')({
  projectId: process.env.FIREBASE_PROJECT_ID || 'test-project'
});

describe('Cloud Functions', () => {
  let myFunctions;

  before(() => {
    myFunctions = require('../index');
  });

  after(() => {
    test.cleanup();
  });

  describe('healthCheck', () => {
    it('should return healthy status', async () => {
      const req = {};
      const res = {
        json: (data) => {
          expect(data.status).to.equal('healthy');
          expect(data).to.have.property('timestamp');
          expect(data).to.have.property('uptime');
        },
      };

      await myFunctions.healthCheck(req, res);
    });
  });

  describe('sendNotification', () => {
    it('should require authentication', async () => {
      const wrapped = test.wrap(myFunctions.sendNotification);

      try {
        await wrapped({});
      } catch (error) {
        expect(error.code).to.equal('unauthenticated');
      }
    });
  });
});
```

**경로**: `C:\Senior_MHealth\backend\functions\test\index.test.js`

---

### Step 8: 부하 테스트
**목표**: API의 성능을 측정하고 병목 지점을 파악합니다.

`load-test.js` 파일 생성:
```javascript
// 프롬프트: 부하 테스트 스크립트를 작성하세요

const autocannon = require('autocannon');

// 프로젝트 ID를 환경 변수에서 가져오기
const projectId = process.env.FIREBASE_PROJECT_ID || 'your-project-id';
const region = process.env.FIREBASE_PROJECT_LOCATION || 'asia-northeast3';

async function loadTest() {
  const result = await autocannon({
    url: `https://${region}-${projectId}.cloudfunctions.net/healthCheck`,
    connections: 10,     // 동시 연결 수
    pipelining: 1,       // 파이프라이닝
    duration: 30,        // 테스트 기간 (초)
    headers: {
      'Content-Type': 'application/json',
    },
  });

  console.log('부하 테스트 결과:');
  console.log('평균 응답시간:', result.latency.mean, 'ms');
  console.log('초당 요청 수:', result.requests.mean);
  console.log('총 요청 수:', result.requests.total);
  console.log('에러 수:', result.errors);
}

// 로컬 에뮬레이터 테스트
async function localLoadTest() {
  const result = await autocannon({
    url: `http://localhost:5001/${projectId}/${region}/healthCheck`,
    connections: 5,
    duration: 10,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  console.log('로컬 부하 테스트 결과:');
  console.log('평균 응답시간:', result.latency.mean, 'ms');
  console.log('초당 요청 수:', result.requests.mean);
}

// 명령줄 인자로 로컬/프로덕션 선택
if (process.argv[2] === 'local') {
  localLoadTest();
} else {
  loadTest();
}
```

**경로**: `C:\Senior_MHealth\backend\functions\load-test.js`

---

### Step 9: 배포 스크립트 설정
**목표**: 프로덕션 배포를 위한 스크립트를 설정합니다.

`package.json`에 스크립트 추가:
```json
{
  "scripts": {
    "test": "mocha test/*.test.js",
    "test:coverage": "nyc mocha test/*.test.js",
    "load:test": "node load-test.js",
    "load:test:local": "node load-test.js local",
    "deploy:functions": "firebase deploy --only functions",
    "deploy:rules": "firebase deploy --only firestore:rules,firestore:indexes",
    "deploy:all": "firebase deploy",
    "logs:tail": "firebase functions:log --only tail",
    "performance:report": "lighthouse http://localhost:5001 --output html --output-path ./lighthouse-report.html"
  }
}
```

**경로**: `C:\Senior_MHealth\backend\functions\package.json`

---

### Step 10: Firebase 프로젝트 확인 및 설정
**목표**: 자신의 Firebase 프로젝트가 올바르게 설정되었는지 확인합니다.

```bash
# 프롬프트: Firebase 프로젝트 확인
firebase projects:list

# 프롬프트: 현재 프로젝트 설정 확인
firebase use

# 프롬프트: 프로젝트가 설정되지 않았다면
firebase use --add
# 자신의 프로젝트 선택하고 alias로 'default' 입력
```

---

### Step 11: 테스트 실행
**목표**: 작성한 테스트를 실행하고 코드 품질을 검증합니다.

```bash
# 프롬프트: 유닛 테스트 실행
npm test

# 프롬프트: 코드 커버리지 확인
npm run test:coverage

# 프롬프트: 로컬 부하 테스트 실행 (에뮬레이터 실행 중)
firebase emulators:start --only functions,firestore
# 다른 터미널에서
npm run load:test:local
```

**경로**: `C:\Senior_MHealth\backend\functions`

---

### Step 12: 프로덕션 배포 전 체크리스트
**목표**: 배포 전 최종 점검을 수행합니다.

```bash
# 프롬프트: 배포 전 체크리스트 확인

# 1. 환경 변수 설정
firebase functions:config:set \
  api.key="your-api-key" \
  api.url="https://your-api-url.com"

# 2. 환경 변수 확인
firebase functions:config:get

# 3. 보안 규칙 테스트
firebase emulators:exec --only firestore "npm test"

# 4. 린트 실행
npm run lint

# 5. 빌드 테스트
npm run build

# 6. 로컬 테스트
firebase emulators:start
```

---

### Step 13: 프로덕션 배포
**목표**: 실제 프로덕션 환경에 배포합니다.

```bash
# 프롬프트: Functions 배포
npm run deploy:functions

# 프롬프트: Firestore 규칙 및 인덱스 배포
npm run deploy:rules

# 프롬프트: 전체 배포 (Functions, Hosting, Rules 등)
npm run deploy:all

# 프롬프트: 배포 확인
firebase functions:log --only tail
```

---

### Step 14: Vercel 프로덕션 배포
**목표**: Web 프론트엔드를 Vercel에 프로덕션 배포합니다.

```bash
# 프롬프트: Web 디렉토리로 이동
cd ../../frontend/web

# 프롬프트: 환경 변수 설정
vercel env add NEXT_PUBLIC_FIREBASE_API_KEY
vercel env add NEXT_PUBLIC_FIREBASE_PROJECT_ID
vercel env add NEXT_PUBLIC_API_URL

# 프롬프트: 프로덕션 배포
vercel --prod

# 배포된 URL 확인 및 테스트
```

**경로**: `C:\Senior_MHealth\frontend\web`

---

### Step 15: 모니터링 대시보드 설정
**목표**: Firebase Console과 Google Cloud Console에서 모니터링을 설정합니다.

Firebase Console에서:
1. **Functions** → 사용량 및 성능 모니터링
2. **Firestore** → 읽기/쓰기 작업 모니터링
3. **Authentication** → 사용자 활동 모니터링
4. **Cloud Messaging** → 메시지 전송 통계

Google Cloud Console에서:
1. **Monitoring** → 대시보드 생성
   - URL: https://console.cloud.google.com/monitoring
   - 자신의 프로젝트 선택
2. **Logging** → 로그 필터 설정
   - Functions 로그 필터 생성
3. **Error Reporting** → 에러 알림 설정
4. **Trace** → 성능 추적

---

### Step 16: 최종 프로덕션 테스트
**목표**: 배포된 애플리케이션이 정상 작동하는지 확인합니다.

```bash
# 프롬프트: 헬스체크 엔드포인트 테스트
curl https://asia-northeast3-your-project-id.cloudfunctions.net/healthCheck

# 프롬프트: Web 애플리케이션 테스트
# Vercel에서 제공한 URL로 접속하여 테스트

# 프롬프트: Mobile 앱 테스트
# 빌드된 APK를 설치하여 테스트
```

---

## 🎉 실습 완료!

축하합니다! 8주간의 Cloud Engineering 교육 과정을 완료했습니다!

### 최종 체크리스트
- ✅ 개인 Firebase 프로젝트로 설정 완료
- ✅ 성능 최적화 미들웨어 구현
- ✅ 캐싱 전략 적용
- ✅ 모니터링 및 로깅 설정
- ✅ 헬스체크 엔드포인트 구현
- ✅ 유닛 테스트 작성
- ✅ 부하 테스트 수행
- ✅ Firebase Functions 프로덕션 배포
- ✅ Vercel 웹 애플리케이션 배포
- ✅ 모니터링 대시보드 설정

### 개인 프로젝트 URL
배포 완료 후 다음 URL들을 기록해두세요:
- Firebase Functions: `https://asia-northeast3-[YOUR-PROJECT-ID].cloudfunctions.net/`
- Vercel Web App: `https://[YOUR-APP-NAME].vercel.app`
- Firebase Hosting: `https://[YOUR-PROJECT-ID].web.app`

### 운영 팁
1. **정기 모니터링**: 일일 메트릭 확인
2. **백업 정책**: 주간 자동 백업 설정
3. **보안 업데이트**: 월간 의존성 업데이트
4. **성능 리뷰**: 분기별 성능 최적화
5. **비용 관리**: Firebase 및 Vercel 사용량 모니터링

### 다음 단계
- 추가 기능 개발
- A/B 테스트 구현
- 머신러닝 통합
- 국제화 (i18n) 지원
- PWA 전환

## 🚀 Senior MHealth 완성!
이제 실제 사용자를 위한 안정적이고 확장 가능한 헬스케어 애플리케이션을 운영할 수 있습니다!

각 학생은 자신의 Firebase 프로젝트와 Vercel 계정으로 독립적인 애플리케이션을 배포하고 운영할 수 있습니다.