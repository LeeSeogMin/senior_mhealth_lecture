#!/bin/bash
# AI Service 최적화된 배포 스크립트
# 문서: deploy-ai.md 기반

set -e

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 상태 메시지 출력 함수 (config 로드 전에 필요)
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Configuration 로드
CONFIG_FILE="../../project.config.json"
if [ -f "$CONFIG_FILE" ]; then
    # Try python3 first, then python
    PYTHON_CMD="python3"
    if ! command -v python3 &> /dev/null; then
        PYTHON_CMD="python"
    fi

    PROJECT_ID=$($PYTHON_CMD -c "import json; print(json.load(open('$CONFIG_FILE'))['project']['id'], end='')" 2>/dev/null | tr -d '\n\r')
    REGION=$($PYTHON_CMD -c "import json; print(json.load(open('$CONFIG_FILE'))['project']['region'], end='')" 2>/dev/null | tr -d '\n\r')
    SERVICE_NAME=$($PYTHON_CMD -c "import json; print(json.load(open('$CONFIG_FILE'))['services']['aiService']['name'], end='')" 2>/dev/null | tr -d '\n\r')

    # Fallback if any value is empty
    [ -z "$PROJECT_ID" ] && PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-senior-mhealth-472007}"
    [ -z "$REGION" ] && REGION="${REGION:-asia-northeast3}"
    [ -z "$SERVICE_NAME" ] && SERVICE_NAME="senior-mhealth-ai"

    if [ -n "$PROJECT_ID" ] && [ -n "$REGION" ]; then
        log_info "✅ Configuration loaded - Project: ${PROJECT_ID}, Region: ${REGION}"
    else
        log_warning "Config parsing failed, using environment variables"
        PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-senior-mhealth-472007}"
        REGION="${REGION:-asia-northeast3}"
        SERVICE_NAME="${SERVICE_NAME:-senior-mhealth-ai}"
    fi
else
    log_warning "Config file not found, using environment variables"
    PROJECT_ID="${GOOGLE_CLOUD_PROJECT:-senior-mhealth-472007}"
    REGION="${REGION:-asia-northeast3}"
    SERVICE_NAME="${SERVICE_NAME:-senior-mhealth-ai}"
fi

# 변수 설정
REGISTRY="${REGION}-docker.pkg.dev/${PROJECT_ID}/ai-service"
BASE_VERSION="v9"  # resampy 추가된 새 버전
TIMESTAMP=$(date +%Y%m%d-%H%M%S)

# 도움말 함수
show_help() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --base     베이스 이미지 빌드 (의존성 변경 시)"
    echo "  --app      앱 이미지 빌드 및 배포 (코드 변경 시)"
    echo "  --full     전체 빌드 및 배포 (베이스 + 앱)"
    echo "  --quick    빠른 배포 (기존 베이스 사용)"
    echo "  --status   배포 상태 확인"
    echo "  --logs     서비스 로그 확인"
    echo "  --help     도움말 표시"
    echo ""
    echo "Examples:"
    echo "  $0 --quick   # 코드만 변경된 경우 (2-3분)"
    echo "  $0 --full    # 패키지 변경 시 (5-7분)"
}


# 베이스 이미지 빌드
build_base() {
    log_info "베이스 이미지 빌드 시작 (base:${BASE_VERSION})"

    # 현재 스크립트 위치 기준으로 프로젝트 루트 찾기
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

    log_info "스크립트 위치: ${SCRIPT_DIR}"
    log_info "프로젝트 루트: ${PROJECT_ROOT}"

    # 프로젝트 루트로 이동
    cd "${PROJECT_ROOT}"

    # 베이스 이미지 빌드
    docker build \
        -f backend/ai-service/Dockerfile.base \
        -t ${REGISTRY}/base:${BASE_VERSION} \
        -t ${REGISTRY}/base:latest \
        --platform linux/amd64 \
        .

    # 이미지 푸시
    log_info "베이스 이미지 푸시 중..."
    docker push ${REGISTRY}/base:${BASE_VERSION}
    docker push ${REGISTRY}/base:latest

    log_success "베이스 이미지 빌드 완료!"

    # 원래 디렉토리로 복귀
    cd backend/ai-service
}

# SincNet 모델을 Firebase Storage에 업로드
upload_models() {
    log_info "SincNet 모델을 Firebase Storage에 업로드 중..."

    # 모델 파일 경로
    MODEL_DIR="backend/libraries/voice_analysis/analysis/sincnet/models"
    STORAGE_BUCKET="${PROJECT_ID}.firebasestorage.app"
    STORAGE_PATH="models/sincnet/"

    # 모델 파일이 존재하는지 확인
    if [ ! -d "$MODEL_DIR" ]; then
        log_error "모델 디렉토리를 찾을 수 없습니다: $MODEL_DIR"
        return 1
    fi

    # 모델 파일 개수 확인
    MODEL_COUNT=$(find "$MODEL_DIR" -name "*.pkl" | wc -l)
    if [ "$MODEL_COUNT" -eq 0 ]; then
        log_error "모델 파일을 찾을 수 없습니다: $MODEL_DIR/*.pkl"
        return 1
    fi

    log_info "발견된 모델 파일: $MODEL_COUNT 개"

    # Firebase Storage에 업로드
    gcloud storage cp "${MODEL_DIR}/"*.pkl "gs://${STORAGE_BUCKET}/${STORAGE_PATH}" || {
        log_error "모델 업로드 실패"
        return 1
    }

    log_success "모델 업로드 완료: gs://${STORAGE_BUCKET}/${STORAGE_PATH}"

    # 업로드된 파일 확인
    log_info "업로드된 파일 목록:"
    gcloud storage ls "gs://${STORAGE_BUCKET}/${STORAGE_PATH}"
}

# 앱 이미지 빌드 및 배포
build_app() {
    log_info "앱 이미지 빌드 시작 (base:${BASE_VERSION} 사용)"

    # 현재 스크립트 위치 기준으로 프로젝트 루트 찾기
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

    log_info "스크립트 위치: ${SCRIPT_DIR}"
    log_info "프로젝트 루트: ${PROJECT_ROOT}"

    # 프로젝트 루트로 이동
    cd "${PROJECT_ROOT}"

    # 모델 파일을 Firebase Storage에 업로드
    upload_models

    # Dockerfile.optimized 업데이트 (베이스 버전)
    sed -i "s/base:v[0-9]*/base:${BASE_VERSION}/g" backend/ai-service/Dockerfile.optimized

    # 앱 이미지 빌드
    docker build \
        -f backend/ai-service/Dockerfile.optimized \
        -t ${REGISTRY}/ai-service-sincnet:latest \
        -t ${REGISTRY}/ai-service-sincnet:${TIMESTAMP} \
        --build-arg BASE_IMAGE=${REGISTRY}/base:${BASE_VERSION} \
        --platform linux/amd64 \
        .

    # 이미지 푸시
    log_info "앱 이미지 푸시 중..."
    docker push ${REGISTRY}/ai-service-sincnet:latest
    docker push ${REGISTRY}/ai-service-sincnet:${TIMESTAMP}

    # Cloud Run 배포
    log_info "Cloud Run 서비스 배포 중..."
    gcloud run deploy ${SERVICE_NAME} \
        --image ${REGISTRY}/ai-service-sincnet:latest \
        --region ${REGION} \
        --platform managed \
        --allow-unauthenticated \
        --memory 8Gi \
        --cpu 2 \
        --timeout 540 \
        --max-instances 10 \
        --min-instances 1 \
        --concurrency 10 \
        --set-env-vars "GOOGLE_CLOUD_PROJECT=${PROJECT_ID}" \
        --set-env-vars "SERVICE_NAME=${SERVICE_NAME}"

    log_success "앱 배포 완료!"

    # 원래 디렉토리로 복귀
    cd backend/ai-service
}

# 서비스 상태 확인
check_status() {
    log_info "서비스 상태 확인 중..."

    # 서비스 정보
    echo ""
    echo "=== 서비스 정보 ==="
    gcloud run services describe ${SERVICE_NAME} \
        --region ${REGION} \
        --format "table(status.url,status.latestReadyRevisionName,status.traffic[0].percent)"

    # 새 서비스 URL 표시
    echo ""
    echo "=== 현재 서비스 URL ==="
    echo "https://ai-service-du6z6zbl2a-du.a.run.app"

    # 최근 리비전
    echo ""
    echo "=== 최근 리비전 ==="
    gcloud run revisions list \
        --service ${SERVICE_NAME} \
        --region ${REGION} \
        --limit 3 \
        --format "table(metadata.name,status.conditions[0].status,metadata.creationTimestamp)"

    # Health check
    echo ""
    echo "=== Health Check ==="
    SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')
    curl -s "${SERVICE_URL}/health" | python -m json.tool || echo "Health check failed"
}

# 로그 확인
check_logs() {
    log_info "최근 로그 확인 중..."
    gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=${SERVICE_NAME}" \
        --limit 50 \
        --format "table(timestamp,severity,textPayload)"
}

# 메인 로직
main() {
    case "$1" in
        --base)
            log_info "베이스 이미지 빌드 모드"
            build_base
            ;;
        --app)
            log_info "앱 이미지 빌드 및 배포 모드"
            build_app
            ;;
        --full)
            log_info "전체 빌드 및 배포 모드"
            build_base
            build_app
            ;;
        --quick)
            log_info "빠른 배포 모드 (베이스 이미지 재사용)"
            build_app
            ;;
        --status)
            check_status
            ;;
        --logs)
            check_logs
            ;;
        --help|*)
            show_help
            ;;
    esac
}

# 시작 시간 기록
START_TIME=$(date +%s)

echo "========================================="
echo "AI Service 최적화된 배포 스크립트"
echo "시작 시간: $(date)"
echo "========================================="

# 메인 함수 실행
main "$@"

# 종료 시간 및 소요 시간 계산
END_TIME=$(date +%s)
ELAPSED_TIME=$((END_TIME - START_TIME))

echo ""
echo "========================================="
echo "배포 완료"
echo "소요 시간: ${ELAPSED_TIME}초"
echo "========================================="