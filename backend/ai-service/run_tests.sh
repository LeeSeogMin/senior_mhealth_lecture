#!/bin/bash

# AI Service Simple 테스트 실행 스크립트

set -e

echo "==================================="
echo "AI Service Simple - 통합 테스트 실행"
echo "==================================="

# 가상환경 활성화 (있는 경우)
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
fi

# 환경변수 로드
if [ -f ".env" ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 테스트 실행
echo -e "\n📋 통합 테스트 실행 중..."
pytest tests/test_integration.py -v --tb=short

# 커버리지 리포트 (옵션)
echo -e "\n📊 테스트 커버리지 계산 중..."
pytest tests/ --cov=app --cov-report=term-missing --cov-report=html

echo -e "\n✅ 테스트 완료!"
echo "커버리지 리포트: htmlcov/index.html"