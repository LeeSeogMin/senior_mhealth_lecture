#!/bin/bash

# AI Service Simple 배포 스크립트
# Cloud Build를 사용한 자동 빌드 및 배포

set -e

# 색상 코드
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 환경변수 로드
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# 프로젝트 설정 (환경변수 필수)
if [ -z "$GCP_PROJECT_ID" ]; then
    echo -e "${RED}Error: GCP_PROJECT_ID가 설정되지 않았습니다${NC}"
    echo "export GCP_PROJECT_ID=your-project-id 를 실행하세요"
    exit 1
fi

PROJECT_ID="${GCP_PROJECT_ID}"
REGION="${GCP_REGION:-asia-northeast3}"
SERVICE_NAME="${SERVICE_NAME:-ai-service-simple}"

echo -e "${GREEN}=== AI Service Simple 배포 (Cloud Build) ===${NC}"
echo "프로젝트 ID: $PROJECT_ID"
echo "리전: $REGION"
echo "서비스명: $SERVICE_NAME"

# GEMINI API 키 확인
if [ -z "$GEMINI_API_KEY" ]; then
    echo -e "${RED}Error: GEMINI_API_KEY가 설정되지 않았습니다${NC}"
    echo "export GEMINI_API_KEY=your_api_key 를 실행하세요"
    exit 1
fi

# Cloud Build 실행
echo -e "\n${YELLOW}🚀 Cloud Build 시작...${NC}"
gcloud builds submit \
    --config=cloudbuild.yaml \
    --substitutions=_GEMINI_API_KEY="$GEMINI_API_KEY" \
    --project="$PROJECT_ID"

if [ $? -ne 0 ]; then
    echo -e "${RED}Cloud Build 실패${NC}"
    exit 1
fi

# 4. 서비스 URL 확인
echo -e "\n${YELLOW}4. 서비스 URL 확인 중...${NC}"
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} \
    --platform managed \
    --region ${REGION} \
    --format 'value(status.url)')

echo -e "\n${GREEN}=== 배포 완료 ===${NC}"
echo "서비스 URL: $SERVICE_URL"
echo ""
echo "테스트 명령어:"
echo "curl -X GET ${SERVICE_URL}/health"
echo ""
echo "분석 테스트:"
echo "curl -X POST ${SERVICE_URL}/analyze \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"text\": \"오늘은 기분이 좋아요\", \"user_id\": \"test\"}'"