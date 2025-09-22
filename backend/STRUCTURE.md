# 🏗️ Backend 구조 가이드

**정리 완료일**: 2025-08-20  
**구조 방식**: 표준 Firebase Functions 구조

## 📁 디렉토리 구조

```
backend/
├── functions/                 # Firebase Functions 프로젝트 (표준 구조)
│   ├── firebase.json         # Firebase 프로젝트 설정
│   ├── firestore.rules       # Firestore 보안 규칙
│   ├── firestore.indexes.json # Firestore 인덱스 설정
│   ├── storage.rules         # Storage 보안 규칙
│   ├── deploy.sh            # 배포 스크립트
│   │
│   ├── src/                 # TypeScript 소스 코드
│   │   ├── index.ts        # 메인 진입점
│   │   ├── routes/         # API 라우트
│   │   ├── controllers/    # 비즈니스 로직
│   │   ├── services/       # 서비스 레이어
│   │   ├── middlewares/    # 미들웨어
│   │   ├── models/         # 데이터 모델
│   │   ├── types/          # TypeScript 타입
│   │   └── utils/          # 유틸리티
│   │
│   ├── lib/                # 컴파일된 JavaScript (빌드 결과)
│   ├── tests/              # 테스트 파일들
│   │   ├── test-auth.js    # Authentication 테스트
│   │   ├── test-firestore-rules.js # Firestore 규칙 테스트
│   │   ├── test-upload.js  # 파일 업로드 테스트
│   │   └── setup-test-users.js # 테스트 사용자 생성
│   │
│   ├── scripts/            # 관리 스크립트
│   ├── package.json        # Functions 의존성
│   ├── tsconfig.json       # TypeScript 설정
│   ├── serviceAccountKey.json # Firebase Admin SDK 키
│   └── node_modules/       # 의존성 모듈
│
├── scripts/               # 백엔드 전체 관리 스크립트
│   ├── cleanup_firestore.js
│   ├── migrate_firestore_data.py
│   └── ...
│
└── README.md             # 백엔드 전체 가이드
```

## 🎯 주요 특징

### **표준 Firebase Functions 구조**
- `functions/` - Firebase 프로젝트 루트 (표준)
- `src/` - TypeScript 소스 코드 (직접 접근)
- `tests/` - 테스트 파일들 (별도 폴더로 정리)
- 중복된 `functions/functions/` 구조 제거 완료


### **핵심 진입점**
- **API 서버**: `src/index.ts`
- **배포**: `deploy.sh`
- **테스트**: `tests/test-*.js`

## 🚀 사용 방법

### **개발 환경**
```bash
cd backend/functions
npm install
npm run build
npm run serve
```

### **배포**
```bash
cd backend/functions
./deploy.sh
# 또는
firebase deploy
```

### **테스트**
```bash
cd backend/functions
node tests/test-auth.js
node tests/test-firestore-rules.js
node tests/test-upload.js
```

## 📡 배포된 엔드포인트

- **API**: https://api-nv7k642v4a-du.a.run.app
- **Health Check**: https://healthcheck-nv7k642v4a-du.a.run.app
- **Storage Trigger**: processAudioFile (자동 실행)

## 🔧 주요 설정 파일

| 파일 | 용도 | 위치 |
|------|------|------|
| `firebase.json` | Firebase 프로젝트 설정 | `functions/` |
| `firestore.rules` | 보안 규칙 | `functions/` |
| `package.json` | Functions 의존성 | `functions/` |
| `tsconfig.json` | TypeScript 설정 | `functions/` |

## 📚 학습 자료 체계

### 🎓 **실습가이드** (`docs/2chp_실습가이드_Firebase설치.md`)
- **목적**: 강의 내용을 순차적으로 구현하는 학습 과정
- **대상**: 학생들이 단계별로 따라하는 실습
- **경로**: `backend/functions/src/` (실제 구현 파일들)

### 🤖 **Vibe 코딩** (`docs/2chp_Vibe코딩미션.md`)  
- **목적**: 실습가이드 순서대로 구현해주는 AI 도구 활용법
- **대상**: AI 도구를 활용한 자동 구현
- **경로**: `backend/functions/src/` (동일한 파일들을 AI로 구현)

### 🧪 **Tests 폴더** (`backend/functions/tests/`)
- **목적**: 마지막 통합 테스트를 위한 코드 모음  
- **대상**: 구현 완료 후 전체 시스템 검증
- **파일**: `test-auth.js`, `test-firestore-rules.js`, `test-upload.js`, `setup-test-users.js`

## ⚠️ 중요 참고사항

1. **표준 구조**: 중복된 `functions/functions/` 제거하여 표준 Firebase 구조 준수
2. **빌드 결과**: `lib/` 폴더는 자동 생성되는 빌드 결과입니다
3. **환경 변수**: `.env` 파일들은 로컬 개발용입니다
4. **보안**: `serviceAccountKey.json`은 민감한 파일입니다
5. **테스트**: `tests/` 폴더는 통합 테스트 전용입니다

## 🎯 다음 단계

1. ✅ 백엔드 구조 완전 정리 완료
2. ✅ 테스트 파일 분리 정리 완료
3. ✅ 모든 문서 경로 업데이트 완료
4. 📋 학습자료 체계 확립 완료