# Week 3: Cloud Platform 기초 - 이론편

## 🎯 학습 목표
Google Cloud Platform과 Firebase의 기본 개념을 이해하고, 클라우드 컴퓨팅의 핵심 원리를 학습합니다.

## 📚 핵심 개념

### 1. 클라우드 컴퓨팅 기초

#### 클라우드 서비스 모델
- **IaaS** (Infrastructure as a Service): 가상 서버, 스토리지, 네트워크
- **PaaS** (Platform as a Service): 개발 플랫폼, 데이터베이스
- **SaaS** (Software as a Service): 완성된 애플리케이션
- **BaaS** (Backend as a Service): Firebase 같은 백엔드 서비스

#### 클라우드 배포 모델
- **Public Cloud**: GCP, AWS, Azure
- **Private Cloud**: 기업 전용 클라우드
- **Hybrid Cloud**: Public + Private 조합
- **Multi-Cloud**: 여러 클라우드 제공업체 활용

### 2. Google Cloud Platform (GCP) 개요

#### GCP 핵심 서비스
```
Compute
├── Compute Engine (IaaS, 가상 머신)
├── App Engine (PaaS)
├── Cloud Run (컨테이너 기반 서버리스)
└── Cloud Functions (이벤트 기반 서버리스)

Storage & Database
├── Cloud Storage (객체 스토리지)
├── Firestore (NoSQL)
├── Cloud SQL (관계형 DB)
└── BigQuery (데이터 웨어하우스)

AI & ML
├── Vertex AI (통합 ML 플랫폼)
├── Vision API
├── Natural Language API
└── Translation API
```

#### GCP 리전과 존
- **리전**: 지리적 위치 (예: asia-northeast3 = 서울)
- **존(Zone)**: 리전 내의 독립된 데이터센터
- **멀티리전**: 여러 리전에 걸친 고가용성

### 3. Firebase 플랫폼

#### Firebase = BaaS (Backend as a Service)
모바일과 웹 앱 개발을 위한 Google의 통합 플랫폼

#### 핵심 서비스
```
개발 (Develop)
├── Authentication (인증)
├── Firestore (실시간 DB)
├── Storage (파일 저장)
├── Functions (서버리스)
└── Hosting (웹 호스팅)

품질 (Quality)
├── Crashlytics (충돌 보고)
├── Performance (성능 모니터링)
└── Test Lab (자동 테스트)

성장 (Grow)
├── Analytics (분석)
├── Cloud Messaging (푸시 알림)
└── Remote Config (원격 설정)
```

### 4. 프로젝트 구조와 IAM

#### GCP 프로젝트 계층
```
Organization (조직)
└── Folders (폴더)
    └── Projects (프로젝트)
        └── Resources (리소스)
```

#### IAM (Identity and Access Management)
- **Principal**: 누가 (사용자, 서비스 계정)
- **Role**: 무엇을 (권한 집합)
- **Resource**: 어디에 (프로젝트, 서비스)

#### 주요 역할
- **Owner**: 모든 권한 + 결제
- **Editor**: 리소스 생성/수정/삭제
- **Viewer**: 읽기 전용
- **Custom Roles**: 맞춤 권한

### 5. 서버리스 컴퓨팅 상세

#### Cloud Functions vs Cloud Run 비교

**Cloud Functions (함수 기반 서버리스)**
```javascript
// 단일 함수 단위 배포
exports.helloWorld = (req, res) => {
  res.send('Hello from Cloud Functions!');
};
```
- **특징**:
  - 단일 함수 단위로 배포
  - 이벤트 트리거 (HTTP, Pub/Sub, Firestore 변경 등)
  - 최대 실행 시간: 9분
  - 자동 확장: 0 → 1000+ 인스턴스
  - 언어: Node.js, Python, Go, Java, .NET 등
- **사용 사례**: Webhook, 데이터 변환, 실시간 파일 처리, 경량 API
- **과금**: 호출 횟수 + 실행 시간 + 메모리 사용량

**Cloud Run (컨테이너 기반 서버리스)**
```dockerfile
# 컨테이너 이미지 배포
FROM node:18
COPY . .
RUN npm install
CMD ["node", "server.js"]
```
- **특징**:
  - Docker 컨테이너 실행
  - 모든 언어/프레임워크 지원
  - 최대 실행 시간: 60분
  - 자동 확장: 0 → 1000 인스턴스
  - HTTP/gRPC 엔드포인트
- **사용 사례**: 마이크로서비스, REST API, 웹 애플리케이션, 배치 처리
- **과금**: 요청 수 + CPU/메모리 사용 시간

#### 서버리스의 장점
1. **자동 확장**: 트래픽에 따라 자동 스케일링
2. **비용 효율**: 사용한 만큼만 과금 (0 사용 = 0 비용)
3. **운영 부담 감소**: 서버 관리 불필요
4. **빠른 개발**: 비즈니스 로직에 집중
5. **고가용성**: 자동 장애 복구

### 6. NoSQL vs SQL

#### Firestore (NoSQL) 특징
```javascript
// 문서 기반 구조
{
  users: {
    user1: {
      name: "홍길동",
      age: 30,
      hobbies: ["독서", "운동"]
    }
  }
}
```

**장점**:
- 유연한 스키마
- 수평적 확장 용이
- 실시간 동기화

**단점**:
- 복잡한 쿼리 제한
- 트랜잭션 제약

#### SQL 데이터베이스
```sql
-- 테이블 기반 구조
CREATE TABLE users (
  id INT PRIMARY KEY,
  name VARCHAR(100),
  age INT
);
```

**장점**:
- 트랜잭션
- 복잡한 조인 쿼리
- 데이터 무결성

**단점**:
- 스키마 변경 어려움
- 수직적 확장 위주

### 7. 보안 Best Practices

#### 최소 권한 원칙
- 필요한 최소한의 권한만 부여
- 서비스 계정 세분화
- 정기적인 권한 검토

#### API 키 관리
```javascript
// ❌ 하드코딩
const apiKey = "AIzaSyDxxxxx";

// ✅ 환경 변수
const apiKey = process.env.API_KEY;
```

#### 보안 규칙 설정
```javascript
// Firestore 보안 규칙
rules_version = '2';
service cloud.firestore {
  match /databases/{database}/documents {
    match /users/{userId} {
      allow read, write: if request.auth != null
        && request.auth.uid == userId;
    }
  }
}
```

### 8. 개발 워크플로우

#### CI/CD with Firebase
```yaml
# GitHub Actions 예시
deploy:
  steps:
    - uses: actions/checkout@v2
    - run: npm ci
    - run: npm test
    - run: firebase deploy --token $FIREBASE_TOKEN
```

#### 환경 분리
- **Development**: 개발용 프로젝트
- **Staging**: 테스트용 프로젝트
- **Production**: 실제 서비스용 프로젝트

### 9. 성능 최적화

#### Cloud CDN 활용
- 정적 콘텐츠 캐싱
- 글로벌 엣지 로케이션
- 자동 압축 및 최적화

#### 데이터베이스 최적화
```javascript
// ❌ N+1 쿼리 문제
users.forEach(user => {
  getPosts(user.id); // N번 쿼리
});

// ✅ 배치 조회
const posts = await db.collectionGroup('posts')
  .where('userId', 'in', userIds)
  .get();
```

## 🏗️ Senior MHealth 프로젝트 아키텍처 선택

### 왜 Cloud Functions를 선택했나?

본 프로젝트에서는 **Cloud Functions**를 주요 백엔드 서비스로 선택했습니다:

1. **Firebase와의 완벽한 통합**
   - Firebase SDK와 네이티브 통합
   - Firestore, Auth, Storage 트리거 지원
   - 단일 CLI로 전체 스택 관리 (`firebase deploy`)

2. **교육적 가치**
   - 서버리스 패러다임 학습
   - 이벤트 기반 아키텍처 이해
   - 최신 클라우드 개발 트렌드

3. **개발 편의성**
   ```javascript
   // Firebase Functions - 간단한 구조
   const { onRequest } = require('firebase-functions/v2/https');
   exports.api = onRequest((req, res) => {
     res.send('API Response');
   });
   ```

4. **비용 효율성**
   - 학생 프로젝트에 충분한 무료 할당량
   - 월 200만 호출, 400,000 GB-초 무료
   - 사용하지 않으면 비용 0원

### Cloud Run은 언제 사용하나?

프로젝트에서 Cloud Run을 보조적으로 사용하는 경우:

- **AI 서비스**: 무거운 ML 모델 실행
- **배치 처리**: 장시간 실행되는 작업
- **레거시 통합**: 기존 컨테이너 애플리케이션

```bash
# Cloud Run 배포 예시 (선택적)
cd backend/ai-service
gcloud run deploy ai-service \
  --source . \
  --region asia-northeast3 \
  --allow-unauthenticated
```

## 🎓 핵심 요약

### 기억해야 할 5가지
1. **클라우드 = 탄력성**: 필요에 따라 확장/축소
2. **서버리스 = 효율성**: 관리 부담 없이 개발
3. **Firebase = 통합 플랫폼**: 모바일/웹 개발 All-in-One
4. **보안 = 기본**: 처음부터 보안 고려
5. **비용 = 모니터링**: 지속적인 비용 관리

### 프로젝트 기술 스택
- **백엔드**: Cloud Functions (서버리스)
- **데이터베이스**: Firestore (NoSQL)
- **인증**: Firebase Authentication
- **AI/ML**: Vertex AI (Gemini API)
- **스토리지**: Cloud Storage
- **호스팅**: Firebase Hosting / Vercel
