@echo off
echo ==================================
echo 🧹 Flutter 클린 빌드 스크립트
echo ==================================

echo.
echo 📍 1단계: Flutter 캐시 완전 삭제
echo ----------------------------------
echo Flutter clean 실행 중...
flutter clean

echo.
echo 📍 2단계: 빌드 캐시 삭제
echo ----------------------------------
echo 빌드 디렉토리 삭제 중...
rmdir /s /q build 2>nul
rmdir /s /q .dart_tool 2>nul
rmdir /s /q .flutter-plugins 2>nul
rmdir /s /q .flutter-plugins-dependencies 2>nul

echo.
echo 📍 3단계: Gradle 캐시 삭제
echo ----------------------------------
cd android
echo Gradle 캐시 삭제 중...
call gradlew clean
cd ..

echo.
echo 📍 4단계: pub 캐시 재설치
echo ----------------------------------
echo 패키지 재설치 중...
flutter pub get

echo.
echo 📍 5단계: 릴리즈 APK 빌드
echo ----------------------------------
echo 릴리즈 빌드 시작...
flutter build apk --release --verbose

echo.
echo ==================================
echo ✅ 빌드 완료!
echo ==================================
echo.
echo 📱 APK 위치:
echo build\app\outputs\flutter-apk\app-release.apk
echo.
echo 💡 다음 단계:
echo 1. 기존 앱을 완전히 삭제
echo 2. 새 APK 설치
echo 3. 로그인 후 테스트
echo.
pause
