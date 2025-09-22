# ========================================
# Vercel 배포 자동 설정 스크립트 (Windows)
# Senior_MHealth 프로젝트
# ========================================

Write-Host "🚀 Senior_MHealth Vercel 배포 설정 시작" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "⚠️  중요: 이 프로젝트는 monorepo 구조입니다!" -ForegroundColor Yellow
Write-Host "📁 Next.js 앱 위치: frontend/web" -ForegroundColor Yellow
Write-Host ""

# Vercel CLI 설치 확인
try {
    $vercelVersion = vercel --version 2>$null
    Write-Host "✅ Vercel CLI 이미 설치됨: $vercelVersion" -ForegroundColor Green
} catch {
    Write-Host "📦 Vercel CLI 설치 중..." -ForegroundColor Yellow
    npm install -g vercel
}

# 프로젝트 루트 확인
if (-not (Test-Path "frontend/web")) {
    Write-Host "❌ 오류: frontend/web 디렉토리를 찾을 수 없습니다." -ForegroundColor Red
    Write-Host "프로젝트 루트 디렉토리에서 실행해주세요." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "🔧 Vercel 프로젝트 설정" -ForegroundColor Cyan
Write-Host "=======================" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 설정을 사용하세요:" -ForegroundColor White
Write-Host ""
Write-Host "1️⃣  Framework Preset: Next.js"
Write-Host "2️⃣  Root Directory: frontend/web" -ForegroundColor Yellow -NoNewline
Write-Host " (⭐ 매우 중요!)" -ForegroundColor Red
Write-Host "3️⃣  Build Command: npm run build (기본값)"
Write-Host "4️⃣  Output Directory: .next (기본값)"
Write-Host "5️⃣  Install Command: npm install (기본값)"
Write-Host ""

# Vercel 설정 파일 생성 여부 확인
$createConfig = Read-Host "❓ Vercel Dashboard 대신 설정 파일을 생성하시겠습니까? (y/N)"

if ($createConfig -eq 'y' -or $createConfig -eq 'Y') {
    Write-Host "📝 vercel.json 생성 중..." -ForegroundColor Yellow

    # 루트에 vercel.json 생성 (monorepo 설정)
    $vercelConfig = @'
{
  "buildCommand": "cd frontend/web && npm run build",
  "outputDirectory": "frontend/web/.next",
  "installCommand": "cd frontend/web && npm install",
  "devCommand": "cd frontend/web && npm run dev",
  "framework": "nextjs"
}
'@

    $vercelConfig | Out-File -FilePath "vercel.json" -Encoding UTF8

    Write-Host "✅ vercel.json 생성 완료" -ForegroundColor Green
    Write-Host ""
    Write-Host "📌 생성된 설정:" -ForegroundColor Cyan
    Get-Content "vercel.json"
} else {
    Write-Host ""
    Write-Host "📌 Vercel Dashboard 설정 가이드:" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "1. https://vercel.com 접속"
    Write-Host "2. Project Settings → General"
    Write-Host "3. Root Directory: 'frontend/web' 입력" -ForegroundColor Yellow
    Write-Host "4. Save"
    Write-Host ""
    Write-Host "또는 Build & Deployment에서:" -ForegroundColor White
    Write-Host "- Build Command Override: cd frontend/web && npm run build"
    Write-Host "- Install Command Override: cd frontend/web && npm install"
}

Write-Host ""
Write-Host "📋 환경 변수 템플릿" -ForegroundColor Cyan
Write-Host "==================" -ForegroundColor Cyan
Write-Host ""
Write-Host "다음 환경 변수를 Vercel Dashboard에 추가하세요:" -ForegroundColor White
Write-Host ""
Write-Host @'
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
NEXT_PUBLIC_API_URL=
'@ -ForegroundColor Gray

Write-Host ""
Write-Host "🎉 설정 가이드 완료!" -ForegroundColor Green
Write-Host ""
Write-Host "📚 추가 도움말:" -ForegroundColor Cyan
Write-Host "- 문서: docs/VERCEL_DEPLOYMENT_GUIDE.md"
Write-Host "- 문제 발생 시 GitHub Issues 참고"
Write-Host ""

# Vercel 연결 시작 옵션
$connectNow = Read-Host "🚀 지금 Vercel과 연결하시겠습니까? (y/N)"

if ($connectNow -eq 'y' -or $connectNow -eq 'Y') {
    Write-Host "🔗 Vercel 연결 시작..." -ForegroundColor Cyan
    Write-Host "⚠️  중요: Root Directory를 'frontend/web'으로 설정하세요!" -ForegroundColor Yellow
    vercel
} else {
    Write-Host "나중에 'vercel' 명령어로 연결할 수 있습니다." -ForegroundColor Gray
}

Write-Host ""
Write-Host "✅ 스크립트 완료!" -ForegroundColor Green