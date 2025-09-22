#!/bin/bash

# ========================================
# Vercel 배포 자동 설정 스크립트
# Senior_MHealth 프로젝트
# ========================================

echo "🚀 Senior_MHealth Vercel 배포 설정 시작"
echo "==========================================="
echo ""
echo "⚠️  중요: 이 프로젝트는 monorepo 구조입니다!"
echo "📁 Next.js 앱 위치: frontend/web"
echo ""

# Vercel CLI 설치 확인
if ! command -v vercel &> /dev/null; then
    echo "📦 Vercel CLI 설치 중..."
    npm install -g vercel
else
    echo "✅ Vercel CLI 이미 설치됨"
fi

# 프로젝트 루트 확인
if [ ! -d "frontend/web" ]; then
    echo "❌ 오류: frontend/web 디렉토리를 찾을 수 없습니다."
    echo "프로젝트 루트 디렉토리에서 실행해주세요."
    exit 1
fi

echo ""
echo "🔧 Vercel 프로젝트 설정"
echo "======================="
echo ""
echo "다음 설정을 사용하세요:"
echo ""
echo "1️⃣  Framework Preset: Next.js"
echo "2️⃣  Root Directory: frontend/web (⭐ 매우 중요!)"
echo "3️⃣  Build Command: npm run build (기본값)"
echo "4️⃣  Output Directory: .next (기본값)"
echo "5️⃣  Install Command: npm install (기본값)"
echo ""

# Vercel 설정 파일 생성 여부 확인
read -p "❓ Vercel Dashboard 대신 설정 파일을 생성하시겠습니까? (y/N): " create_config

if [[ $create_config == "y" || $create_config == "Y" ]]; then
    echo "📝 vercel.json 생성 중..."

    # 루트에 vercel.json 생성 (monorepo 설정)
    cat > vercel.json << 'EOF'
{
  "buildCommand": "cd frontend/web && npm run build",
  "outputDirectory": "frontend/web/.next",
  "installCommand": "cd frontend/web && npm install",
  "devCommand": "cd frontend/web && npm run dev",
  "framework": "nextjs"
}
EOF

    echo "✅ vercel.json 생성 완료"
    echo ""
    echo "📌 생성된 설정:"
    cat vercel.json
else
    echo ""
    echo "📌 Vercel Dashboard 설정 가이드:"
    echo "================================"
    echo ""
    echo "1. https://vercel.com 접속"
    echo "2. Project Settings → General"
    echo "3. Root Directory: 'frontend/web' 입력"
    echo "4. Save"
    echo ""
    echo "또는 Build & Deployment에서:"
    echo "- Build Command Override: cd frontend/web && npm run build"
    echo "- Install Command Override: cd frontend/web && npm install"
fi

echo ""
echo "📋 환경 변수 템플릿"
echo "=================="
echo ""
echo "다음 환경 변수를 Vercel Dashboard에 추가하세요:"
echo ""
cat << 'EOF'
NEXT_PUBLIC_FIREBASE_API_KEY=
NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=
NEXT_PUBLIC_FIREBASE_PROJECT_ID=
NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET=
NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID=
NEXT_PUBLIC_FIREBASE_APP_ID=
NEXT_PUBLIC_API_URL=
EOF

echo ""
echo "🎉 설정 가이드 완료!"
echo ""
echo "📚 추가 도움말:"
echo "- 문서: docs/VERCEL_DEPLOYMENT_GUIDE.md"
echo "- 문제 발생 시 GitHub Issues 참고"
echo ""

# Vercel 연결 시작 옵션
read -p "🚀 지금 Vercel과 연결하시겠습니까? (y/N): " connect_now

if [[ $connect_now == "y" || $connect_now == "Y" ]]; then
    echo "🔗 Vercel 연결 시작..."
    echo "⚠️  중요: Root Directory를 'frontend/web'으로 설정하세요!"
    vercel
else
    echo "나중에 'vercel' 명령어로 연결할 수 있습니다."
fi

echo ""
echo "✅ 스크립트 완료!"