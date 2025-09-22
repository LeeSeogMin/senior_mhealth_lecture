#!/bin/bash

# Senior MHealth - 하드코딩된 값 치환 스크립트
# Universal Configuration System 구현의 핵심 유틸리티

set -e  # 에러 발생 시 스크립트 중단

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로깅 함수
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

# 프로젝트 루트 디렉토리 확인
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG_FILE="$PROJECT_ROOT/project.config.json"

log_info "프로젝트 루트: $PROJECT_ROOT"

# 설정 파일 존재 확인
if [ ! -f "$CONFIG_FILE" ]; then
    log_error "프로젝트 설정 파일을 찾을 수 없습니다: $CONFIG_FILE"
    log_info "먼저 project.config.json 파일을 생성해주세요."
    exit 1
fi

# JSON 파싱을 위한 함수 (jq 사용)
get_config_value() {
    local path="$1"
    if command -v jq >/dev/null 2>&1; then
        cat "$CONFIG_FILE" | jq -r "$path // empty"
    else
        log_warning "jq가 설치되지 않았습니다. 기본값을 사용합니다."
        echo ""
    fi
}

# 설정 값 로드
log_info "프로젝트 설정 로드 중..."

PROJECT_ID=$(get_config_value '.project.id')
PROJECT_REGION=$(get_config_value '.project.region')
FIREBASE_PROJECT_ID=$(get_config_value '.firebase.projectId')
FIREBASE_STORAGE_BUCKET=$(get_config_value '.firebase.storageBucket')
FIREBASE_MESSAGING_SENDER_ID=$(get_config_value '.firebase.messagingSenderId')
AI_SERVICE_URL=$(get_config_value '.services.aiService.url')
API_SERVICE_URL=$(get_config_value '.services.apiService.url')
WEB_APP_URL=$(get_config_value '.services.webApp.url')

# 기본값 설정 (설정 파일에서 로드되지 않은 경우)
PROJECT_ID=${PROJECT_ID:-"senior-mhealth-472007"}
PROJECT_REGION=${PROJECT_REGION:-"asia-northeast3"}
FIREBASE_PROJECT_ID=${FIREBASE_PROJECT_ID:-"$PROJECT_ID"}
FIREBASE_STORAGE_BUCKET=${FIREBASE_STORAGE_BUCKET:-"$PROJECT_ID.firebasestorage.app"}
FIREBASE_MESSAGING_SENDER_ID=${FIREBASE_MESSAGING_SENDER_ID:-"1054806937473"}

log_info "로드된 설정:"
log_info "  프로젝트 ID: $PROJECT_ID"
log_info "  프로젝트 리전: $PROJECT_REGION"
log_info "  Firebase 프로젝트: $FIREBASE_PROJECT_ID"
log_info "  Storage Bucket: $FIREBASE_STORAGE_BUCKET"

# 하드코딩된 값을 치환하는 함수
replace_in_file() {
    local file="$1"
    local old_value="$2"
    local new_value="$3"
    local description="$4"

    if [ -f "$file" ]; then
        if grep -q "$old_value" "$file"; then
            if [[ "$OSTYPE" == "darwin"* ]]; then
                # macOS
                sed -i '' "s|$old_value|$new_value|g" "$file"
            else
                # Linux
                sed -i "s|$old_value|$new_value|g" "$file"
            fi
            log_success "✅ $file: $description"
        fi
    else
        log_warning "⚠️ 파일을 찾을 수 없음: $file"
    fi
}

# 확장자별 파일 치환 함수
replace_hardcoded_values() {
    local target_dir="$1"
    log_info "하드코딩된 값 치환 중: $target_dir"

    # 기본 프로젝트 ID 치환 (senior-mhealth-472007)
    find "$target_dir" -type f \( \
        -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \
        -o -name "*.py" -o -name "*.dart" -o -name "*.yaml" -o -name "*.yml" \
        -o -name "*.json" -o -name "*.md" -o -name "*.sh" -o -name "*.bat" \
        \) -not -path "*/node_modules/*" \
        -not -path "*/build/*" \
        -not -path "*/.git/*" \
        -not -path "*/lib/*" \
        -not -path "*/.dart_tool/*" \
        -exec grep -l "senior-mhealth-472007" {} \; 2>/dev/null | while read -r file; do

        # project.config.json 파일은 제외 (템플릿 파일)
        if [[ "$file" == *"project.config.json" ]]; then
            continue
        fi

        replace_in_file "$file" "senior-mhealth-472007" "$PROJECT_ID" "프로젝트 ID 치환"
    done

    # Firebase Storage Bucket 치환
    find "$target_dir" -type f \( \
        -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \
        -o -name "*.py" -o -name "*.dart" -o -name "*.yaml" -o -name "*.yml" \
        -o -name "*.json" \
        \) -not -path "*/node_modules/*" \
        -not -path "*/build/*" \
        -not -path "*/.git/*" \
        -not -path "*/lib/*" \
        -not -path "*/.dart_tool/*" \
        -exec grep -l "senior-mhealth-472007\.firebasestorage\.app" {} \; 2>/dev/null | while read -r file; do

        if [[ "$file" == *"project.config.json" ]]; then
            continue
        fi

        replace_in_file "$file" "senior-mhealth-472007.firebasestorage.app" "$FIREBASE_STORAGE_BUCKET" "Storage Bucket 치환"
    done

    # Cloud Run 서비스 URL 치환 (API 서비스)
    if [ -n "$API_SERVICE_URL" ]; then
        find "$target_dir" -type f \( \
            -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \
            -o -name "*.py" -o -name "*.dart" \
            \) -not -path "*/node_modules/*" \
            -not -path "*/build/*" \
            -not -path "*/.git/*" \
            -not -path "*/lib/*" \
            -not -path "*/.dart_tool/*" \
            -exec grep -l "senior-mhealth-api-1054806937473\.asia-northeast3\.run\.app" {} \; 2>/dev/null | while read -r file; do

            if [[ "$file" == *"project.config.json" ]]; then
                continue
            fi

            # URL에서 프로토콜 제거
            api_host=$(echo "$API_SERVICE_URL" | sed 's|https\?://||')
            replace_in_file "$file" "senior-mhealth-api-1054806937473.asia-northeast3.run.app" "$api_host" "API 서비스 URL 치환"
        done
    fi

    # AI 서비스 URL 치환
    if [ -n "$AI_SERVICE_URL" ]; then
        find "$target_dir" -type f \( \
            -name "*.js" -o -name "*.ts" -o -name "*.jsx" -o -name "*.tsx" \
            -o -name "*.py" -o -name "*.dart" \
            \) -not -path "*/node_modules/*" \
            -not -path "*/build/*" \
            -not -path "*/.git/*" \
            -not -path "*/lib/*" \
            -not -path "*/.dart_tool/*" \
            -exec grep -l "senior-mhealth-ai-du6z6zbl2a-du\.a\.run\.app" {} \; 2>/dev/null | while read -r file; do

            if [[ "$file" == *"project.config.json" ]]; then
                continue
            fi

            # URL에서 프로토콜 제거
            ai_host=$(echo "$AI_SERVICE_URL" | sed 's|https\?://||')
            replace_in_file "$file" "senior-mhealth-ai-du6z6zbl2a-du.a.run.app" "$ai_host" "AI 서비스 URL 치환"
        done
    fi

    # 리전 치환
    find "$target_dir" -type f \( \
        -name "*.yaml" -o -name "*.yml" -o -name "*.py" -o -name "*.sh" -o -name "*.bat" \
        \) -not -path "*/node_modules/*" \
        -not -path "*/build/*" \
        -not -path "*/.git/*" \
        -exec grep -l "asia-northeast3" {} \; 2>/dev/null | while read -r file; do

        if [[ "$file" == *"project.config.json" ]]; then
            continue
        fi

        replace_in_file "$file" "asia-northeast3" "$PROJECT_REGION" "리전 치환"
    done
}

# 메인 실행
main() {
    log_info "=== Senior MHealth 하드코딩 값 치환 시작 ==="

    # 백엔드 폴더 처리
    if [ -d "$PROJECT_ROOT/backend" ]; then
        replace_hardcoded_values "$PROJECT_ROOT/backend"
    fi

    # 프론트엔드 폴더 처리
    if [ -d "$PROJECT_ROOT/frontend" ]; then
        replace_hardcoded_values "$PROJECT_ROOT/frontend"
    fi

    # 설정 스크립트 폴더 처리
    if [ -d "$PROJECT_ROOT/setup" ]; then
        replace_hardcoded_values "$PROJECT_ROOT/setup"
    fi

    # 스크립트 폴더 처리
    if [ -d "$PROJECT_ROOT/scripts" ]; then
        replace_hardcoded_values "$PROJECT_ROOT/scripts"
    fi

    # GitHub Actions 워크플로우 처리
    if [ -d "$PROJECT_ROOT/.github" ]; then
        replace_hardcoded_values "$PROJECT_ROOT/.github"
    fi

    # 루트 레벨 파일들 처리
    for file in "$PROJECT_ROOT"/*.md "$PROJECT_ROOT"/*.yml "$PROJECT_ROOT"/*.yaml "$PROJECT_ROOT"/*.json; do
        if [ -f "$file" ] && [[ "$(basename "$file")" != "project.config.json" ]]; then
            if grep -q "senior-mhealth-472007" "$file" 2>/dev/null; then
                replace_in_file "$file" "senior-mhealth-472007" "$PROJECT_ID" "프로젝트 ID 치환"
            fi
        fi
    done

    log_success "=== 하드코딩 값 치환 완료 ==="
    log_info "변경된 파일들을 확인하고 git commit을 진행하세요."
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi