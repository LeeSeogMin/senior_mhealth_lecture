# Samsung 통화 녹음 자동 분석 시스템 설치 가이드

## 📖 개요

Samsung Galaxy 폰의 기본 통화 녹음 기능을 활용하여 자동으로 AI 분석을 수행하는 시스템 설치 가이드입니다.

**⚠️ 중요**: Android 보안 정책으로 인해 직접 통화 녹음은 불가능하므로, Samsung 폰의 기본 통화 녹음 기능을 활용하는 우회 방식입니다.

---

## 🎯 시스템 구조

```
Samsung 통화 → 기본 녹음 앱 → /storage/emulated/0/Recordings/Call/ 
→ 앱에서 자동 감지 → 기존 AI 분석 API → 결과 저장
```

---

## 📱 1단계: Samsung 폰 설정

### 1.1 Samsung 통화 녹음 기능 활성화

1. **전화 앱** 열기
2. **⋮ (우상단 메뉴)** → **설정**
3. **통화 녹음** 활성화
4. **자동 녹음** 설정 (선택사항)

### 1.2 파일 위치 확인

Samsung 통화 녹음 파일은 다음 위치에 저장됩니다:
```
/storage/emulated/0/Recordings/Call/
```

파일명 패턴:
```
통화 녹음 [이름]_[YYMMDD]_[HHMMSS].m4a
예: 통화 녹음 어머니_250727_143638.m4a
```

---

## 💻 2단계: 앱 개발 구현

### 2.1 필요한 파일 생성

#### A. Samsung 파일 감지 서비스
**파일**: `mobile_app/lib/services/samsung_call_detector.dart`

주요 기능:
- Samsung 통화 녹음 파일 패턴 인식
- 최신 파일 자동 검색 (파일명 날짜/시간 기준)
- 권한 관리

#### B. 온보딩 마법사 구현
**파일**: `mobile_app/lib/screens/setup_wizard_screen.dart`

주요 기능:
- 4단계 PageView 구성 (환영 → 권한 → Samsung → 완료)
- 권한 자동 요청 및 설정 화면 이동
- Samsung 설정 안내 (선택사항)
- 설정 완료 상태 저장

#### C. 메인 앱 라우팅 개선
**파일**: `mobile_app/lib/main.dart`

주요 기능:
- AuthChecker에서 로그인 상태와 설정 완료 상태 체크
- 자동 라우팅: 로그인 → 설정 체크 → 온보딩 또는 홈
- SharedPreferences로 설정 완료 상태 저장

#### D. 홈 화면 통합
**파일**: `mobile_app/lib/screens/home_screen.dart`

추가 요소:
- "Samsung 통화 분석" 카드
- "최신 통화 분석하기" 버튼
- `_analyzeSamsungCall()` 메서드
- Samsung 설정 상태 체크

### 2.2 권한 설정 (중요!)

#### Android 매니페스트 수정
**파일**: `mobile_app/android/app/src/main/AndroidManifest.xml`

```xml
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.MANAGE_EXTERNAL_STORAGE" />
```

#### pubspec.yaml 의존성
**파일**: `mobile_app/pubspec.yaml`

```yaml
dependencies:
  permission_handler: ^11.1.0
```

---

## 🚀 3단계: 앱 빌드 및 배포

### 3.1 빌드

```bash
cd mobile_app
flutter clean
flutter pub get
flutter build apk --debug
```

### 3.2 설치

```bash
adb devices  # 기기 연결 확인
adb install -r build/app/outputs/flutter-apk/app-debug.apk
```

---

## 🔐 4단계: 권한 설정 (핵심!)

### ⚠️ **가장 중요한 단계**: Android 11+ 스코프드 스토리지 대응

#### 4.1 일반 권한 부여

```bash
adb shell pm grant com.example.simple_health_monitor android.permission.READ_EXTERNAL_STORAGE
adb shell pm grant com.example.simple_health_monitor android.permission.WRITE_EXTERNAL_STORAGE
```

#### 4.2 **"모든 파일 관리" 권한 (필수!)**

**방법 1: ADB 명령으로 설정 화면 열기**
```bash
adb shell am start -a android.settings.MANAGE_APP_ALL_FILES_ACCESS_PERMISSION -d package:com.example.simple_health_monitor
```

**방법 2: 수동 설정**
1. **설정** → **앱** → **Senior Health Monitor**
2. **권한** → **파일 및 미디어**
3. **모든 파일 관리** → **허용**

#### 4.3 권한 확인

```bash
# 일반 권한 확인
adb shell dumpsys package com.example.simple_health_monitor | grep -A 10 "runtime permissions"

# "모든 파일 관리" 권한 확인
adb shell appops get com.example.simple_health_monitor MANAGE_EXTERNAL_STORAGE
# 결과: "MANAGE_EXTERNAL_STORAGE: allow" 이어야 함
```

---

## 🧪 5단계: 테스트 및 문제 해결

### 5.1 기본 테스트

1. **앱 실행**
2. **"Samsung 통화 분석" 카드** 확인
3. **"최신 통화 분석하기" 버튼** 클릭
4. **결과 확인**

### 5.2 예상 결과

#### ✅ 성공 시:
```
"파일 발견: 통화 녹음 어머니_250727_143638.m4a"
"AI 분석을 요청하는 중..."
"✅ AI 분석이 성공적으로 요청되었습니다!"
```

#### ❌ 실패 시:
```
"Samsung 통화 녹음 파일을 찾을 수 없습니다"
→ 정상적인 상황: 아직 통화 녹음을 하지 않은 경우
→ 문제 상황: 권한이 없거나 Samsung 녹음 기능이 비활성화된 경우
```

### 5.3 문제 해결

#### 문제 1: "통화 녹음 파일을 찾을 수 없습니다"

**원인**: 권한 부족
**해결**: 4단계 권한 설정 다시 확인, 특히 "모든 파일 관리" 권한

#### 문제 2: 앱이 파일을 인식하지 못함

**디버그 방법**:
```bash
# 실제 파일 존재 확인
adb shell ls -la /storage/emulated/0/Recordings/Call/

# 앱 로그 확인
adb logcat -s flutter | grep -E "(통화|Samsung|📁|📄)"
```

#### 문제 3: 권한은 있는데 파일 목록이 비어있음

**원인**: Android 11+ 스코프드 스토리지
**해결**: `MANAGE_EXTERNAL_STORAGE` 권한 필수 설정

---

## 📊 6단계: 성능 및 보안 고려사항

### 6.1 보안

- **최소 권한 원칙**: 필요한 권한만 요청
- **사용자 동의**: 권한 요청 시 명확한 설명 제공
- **데이터 암호화**: 전송 중 파일 암호화

### 6.2 성능

- **파일 크기 체크**: 대용량 파일 업로드 전 확인
- **네트워크 상태 확인**: WiFi 연결 시에만 자동 업로드
- **배터리 최적화**: 백그라운드 작업 최소화

---

## 🛠️ 7단계: 유지보수

### 7.1 로그 모니터링

```bash
# 실시간 앱 로그 확인
adb logcat -s flutter

# 특정 키워드 필터링
adb logcat -s flutter | grep -E "(통화|Samsung|분석)"
```

### 7.2 백엔드 분석 결과 확인

```bash
cd backend/api/functions
node scripts/check-mobile-analysis-logs.js
```

---

## 📋 체크리스트

### 개발 환경 준비
- [ ] Flutter 개발 환경 설정
- [ ] Samsung Galaxy 폰 (Android 11+)
- [ ] USB 디버깅 활성화
- [ ] ADB 설치 및 연결 확인

### 앱 구현
- [ ] `samsung_call_detector.dart` 구현
- [ ] 홈 화면 UI 추가
- [ ] Android 권한 설정
- [ ] 의존성 패키지 추가
- [ ] 온보딩 마법사 구현

### 권한 설정 (필수!)
- [ ] READ_EXTERNAL_STORAGE 권한
- [ ] WRITE_EXTERNAL_STORAGE 권한  
- [ ] **MANAGE_EXTERNAL_STORAGE 권한 (가장 중요!)**
- [ ] 권한 상태 확인

### 테스트
- [ ] 온보딩 마법사 4단계 테스트
- [ ] 권한 설정 자동화 테스트
- [ ] Samsung 통화 녹음 기능 활성화 (선택사항)
- [ ] 앱에서 파일 감지 테스트
- [ ] AI 분석 요청 테스트
- [ ] 분석 결과 확인

---

## ⚠️ 주의사항

1. **Android 11+ 필수**: 스코프드 스토리지로 인해 이전 버전과 다른 권한 처리 필요
2. **Samsung 전용**: 다른 제조사는 파일명 패턴이 다를 수 있음
3. **사용자 교육**: "모든 파일 관리" 권한의 중요성을 사용자에게 설명 필요
4. **Samsung 설정 선택사항**: 통화 녹음 폴더가 없어도 온보딩 완료 가능
5. **개인정보 보호**: 통화 녹음은 민감한 데이터이므로 보안 강화 필수

---

## 📞 지원

문제 발생 시:
1. 로그 확인 (`adb logcat -s flutter`)
2. 권한 상태 재확인
3. Samsung 통화 녹음 기능 상태 확인
4. 파일 시스템 직접 확인 (`adb shell ls -la /storage/emulated/0/Recordings/Call/`)

**성공 기준**: 
- 온보딩 마법사 완료 (권한 설정 완료)
- 홈 화면 정상 진입
- Samsung 통화 녹음 후 "✅ AI 분석이 성공적으로 요청되었습니다!" 메시지 출력 