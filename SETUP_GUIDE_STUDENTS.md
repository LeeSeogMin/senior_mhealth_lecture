# 🚀 Senior MHealth - 학생용 프로젝트 설정 가이드

이 가이드는 각 학생이 자신의 Firebase 프로젝트와 Vercel 계정으로 애플리케이션을 설정하는 방법을 안내합니다.

## 📋 사전 준비 사항

### 필요한 계정
- [ ] Google 계정 (Firebase용)
- [ ] GitHub 계정
- [ ] Vercel 계정 (https://vercel.com/signup)
- [ ] Node.js 18+ 설치
- [ ] Git 설치

## 1️⃣ Firebase 프로젝트 설정

### 1.1 Firebase 프로젝트 생성

1. [Firebase Console](https://console.firebase.google.com) 접속
2. "프로젝트 만들기" 클릭
3. 프로젝트 이름 입력 (예: `senior-mhealth-학번`)
4. Google Analytics 설정 (선택사항)
5. 프로젝트 생성 완료

### 1.2 Firebase 서비스 활성화

Firebase Console에서 다음 서비스들을 활성화:

```
✅ Authentication (인증)
   - 이메일/비밀번호 로그인 활성화

✅ Firestore Database
   - 위치: asia-northeast3 (서울)
   - 테스트 모드로 시작

✅ Storage
   - 위치: asia-northeast3 (서울)

✅ Cloud Functions
   - 프로젝트 업그레이드 필요 (Blaze 요금제)
```

### 1.3 Firebase 웹 앱 추가

1. 프로젝트 설정 > 일반 > 내 앱 > 웹 앱 추가
2. 앱 이름 입력
3. Firebase 호스팅 설정 체크 해제
4. 앱 등록
5. **Firebase 구성 정보 복사 (중요!)**

```javascript
// 이 정보를 안전하게 보관하세요
const firebaseConfig = {
  apiKey: "...",
  authDomain: "...",
  projectId: "...",
  storageBucket: "...",
  messagingSenderId: "...",
  appId: "..."
};
```

## 2️⃣ 프로젝트 코드 설정

### 2.1 레포지토리 클론

```bash
git clone [강사가 제공한 레포지토리 URL]
cd Senior_MHealth
```

### 2.2 Firebase 설정 파일 생성

```bash
# .firebaserc 파일 생성
cp .firebaserc.template .firebaserc
```

`.firebaserc` 파일 편집:
```json
{
  "projects": {
    "default": "여기에-본인-프로젝트-ID"
  }
}
```

### 2.3 Backend 환경 변수 설정

```bash
cd backend/functions

# 환경 변수 파일 생성
cp .env.template .env
```

`.env` 파일 편집:
```env
FIREBASE_PROJECT_ID=여기에-본인-프로젝트-ID
FIREBASE_PROJECT_LOCATION=asia-northeast3
# ... 나머지 설정
```

### 2.4 Web 프론트엔드 환경 변수 설정

```bash
cd ../../frontend/web

# 환경 변수 파일 생성
cp .env.template .env.local
```

`.env.local` 파일에 Firebase 구성 정보 입력:
```env
NEXT_PUBLIC_FIREBASE_API_KEY=여기에-API-키
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=프로젝트ID.firebaseapp.com
NEXT_PUBLIC_FIREBASE_PROJECT_ID=여기에-프로젝트-ID
# ... 나머지 Firebase 설정
```

### 2.5 Mobile 앱 Firebase 설정

```bash
cd ../mobile

# FlutterFire CLI 설치 (최초 1회)
dart pub global activate flutterfire_cli

# Firebase 설정 자동 생성
flutterfire configure
```

선택 옵션:
- 본인의 Firebase 프로젝트 선택
- 플랫폼: android, ios 선택
- 자동으로 `lib/firebase_options.dart` 생성됨

## 3️⃣ Vercel 배포 설정 (Web)

### 3.1 Vercel CLI 설치

```bash
npm install -g vercel
```

### 3.2 Vercel 로그인

```bash
vercel login
```

### 3.3 Web 앱 배포

```bash
cd frontend/web

# Vercel 프로젝트 연결
vercel

# 프로덕션 배포
vercel --prod
```

### 3.4 환경 변수 설정

Vercel 대시보드(https://vercel.com/dashboard)에서:

1. 프로젝트 선택
2. Settings > Environment Variables
3. `.env.local`의 모든 변수 추가
4. 재배포: `vercel --prod`

### 3.5 배포된 URL 업데이트

`.env.local` 파일 수정:
```env
NEXT_PUBLIC_APP_URL=https://여러분의-vercel-url.vercel.app
```

## 4️⃣ Backend Functions 배포

### 4.1 Firebase CLI 설치

```bash
npm install -g firebase-tools
```

### 4.2 Firebase 로그인

```bash
firebase login
```

### 4.3 Functions 배포

```bash
cd backend/functions

# 의존성 설치
npm install

# Functions 배포
firebase deploy --only functions
```

### 4.4 배포된 Functions URL 확인

Firebase Console > Functions에서 배포된 함수들의 URL 확인

Web `.env.local` 업데이트:
```env
NEXT_PUBLIC_API_URL=https://asia-northeast3-프로젝트ID.cloudfunctions.net/api
```

## 5️⃣ 테스트 및 확인

### 5.1 로컬 테스트

```bash
# Backend (Terminal 1)
cd backend/functions
npm run serve

# Web (Terminal 2)
cd frontend/web
npm run dev

# Mobile (Terminal 3)
cd frontend/mobile
flutter run
```

### 5.2 프로덕션 테스트

1. Web: Vercel URL 접속
2. Functions: Firebase Console에서 로그 확인
3. Database: Firestore 데이터 확인

## 🔧 자주 발생하는 문제

### Firebase 권한 오류
```bash
# 프로젝트 재선택
firebase use --add
```

### Vercel 배포 실패
```bash
# 캐시 삭제 후 재배포
vercel --force
```

### Functions 배포 오류
```bash
# Node 버전 확인 (18+ 필요)
node --version

# 클린 빌드
rm -rf node_modules
npm install
firebase deploy --only functions
```

## 📝 체크리스트

### Week 3 완료 조건
- [ ] Firebase 프로젝트 생성
- [ ] 모든 서비스 활성화
- [ ] 환경 변수 설정 완료
- [ ] `.firebaserc` 파일 설정

### Week 4 시작 전 확인
- [ ] Backend functions 로컬 실행 가능
- [ ] Web 앱 로컬 실행 가능
- [ ] Mobile 앱 빌드 가능
- [ ] Firebase Console 접근 가능

## 🆘 도움말

### 유용한 명령어

```bash
# Firebase 프로젝트 확인
firebase projects:list

# Functions 로그 확인
firebase functions:log

# Vercel 프로젝트 상태
vercel ls

# 환경 변수 확인
vercel env ls
```

### 문서 참고

- [Firebase 문서](https://firebase.google.com/docs)
- [Vercel 문서](https://vercel.com/docs)
- [Next.js 문서](https://nextjs.org/docs)
- [Flutter 문서](https://flutter.dev/docs)

## ⚠️ 보안 주의사항

**절대 커밋하지 말아야 할 파일:**
- `.env` (모든 환경 변수 파일)
- `.env.local`
- `serviceAccountKey.json`
- `firebase_options.dart` (개인 프로젝트 정보 포함)
- `.firebaserc` (개인 프로젝트 ID 포함)

**`.gitignore` 확인:**
```gitignore
# 환경 변수
.env
.env.local
.env.production

# Firebase
.firebaserc
serviceAccountKey.json
firebase_options.dart

# Vercel
.vercel
```

---

**질문이 있으면 강사 또는 조교에게 문의하세요!** 💪