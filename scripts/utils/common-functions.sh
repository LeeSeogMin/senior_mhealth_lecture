#!/bin/bash

# =============================================================================
# Common Functions Library for Senior MHealth
# =============================================================================
# Provides reusable functions for all shell scripts
# Includes: logging, error handling, validation, etc.
# =============================================================================

# Source platform detector if not already loaded
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if ! command -v detect_platform >/dev/null 2>&1; then
    source "$SCRIPT_DIR/platform-detector.sh"
fi

# =============================================================================
# Color Definitions (cross-platform)
# =============================================================================
setup_colors() {
    local platform=$(detect_platform)

    # Check if terminal supports colors
    if [[ -t 1 ]] && command -v tput >/dev/null 2>&1 && tput colors >/dev/null 2>&1; then
        # Use colors
        RED='\033[0;31m'
        GREEN='\033[0;32m'
        YELLOW='\033[1;33m'
        BLUE='\033[0;34m'
        MAGENTA='\033[0;35m'
        CYAN='\033[0;36m'
        WHITE='\033[1;37m'
        BOLD='\033[1m'
        NC='\033[0m' # No Color
    else
        # No colors for non-terminal or Windows CMD
        RED=''
        GREEN=''
        YELLOW=''
        BLUE=''
        MAGENTA=''
        CYAN=''
        WHITE=''
        BOLD=''
        NC=''
    fi

    export RED GREEN YELLOW BLUE MAGENTA CYAN WHITE BOLD NC
}

# Initialize colors
setup_colors

# =============================================================================
# Logging Functions
# =============================================================================

# Log levels
LOG_LEVEL_DEBUG=0
LOG_LEVEL_INFO=1
LOG_LEVEL_WARN=2
LOG_LEVEL_ERROR=3
LOG_LEVEL_FATAL=4

# Current log level (default: INFO)
CURRENT_LOG_LEVEL=${CURRENT_LOG_LEVEL:-$LOG_LEVEL_INFO}

# Log with timestamp
log_with_time() {
    local level="$1"
    shift
    local message="$*"
    local timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo "[$timestamp] $level $message"
}

# Debug log
log_debug() {
    if [[ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_DEBUG ]]; then
        echo -e "${CYAN}[DEBUG]${NC} $*" >&2
        [[ -n "$LOG_FILE" ]] && log_with_time "DEBUG" "$*" >> "$LOG_FILE"
    fi
}

# Info log
log_info() {
    if [[ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_INFO ]]; then
        echo -e "${GREEN}[INFO]${NC} $*"
        [[ -n "$LOG_FILE" ]] && log_with_time "INFO" "$*" >> "$LOG_FILE"
    fi
}

# Warning log
log_warn() {
    if [[ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_WARN ]]; then
        echo -e "${YELLOW}[WARN]${NC} $*" >&2
        [[ -n "$LOG_FILE" ]] && log_with_time "WARN" "$*" >> "$LOG_FILE"
    fi
}

# Error log
log_error() {
    if [[ $CURRENT_LOG_LEVEL -le $LOG_LEVEL_ERROR ]]; then
        echo -e "${RED}[ERROR]${NC} $*" >&2
        [[ -n "$LOG_FILE" ]] && log_with_time "ERROR" "$*" >> "$LOG_FILE"
    fi
}

# Fatal log (exits script)
log_fatal() {
    echo -e "${RED}${BOLD}[FATAL]${NC} $*" >&2
    [[ -n "$LOG_FILE" ]] && log_with_time "FATAL" "$*" >> "$LOG_FILE"
    exit 1
}

# Step log (for showing progress)
log_step() {
    echo -e "${BLUE}[STEP]${NC} $*"
    [[ -n "$LOG_FILE" ]] && log_with_time "STEP" "$*" >> "$LOG_FILE"
}

# Success log
log_success() {
    echo -e "${GREEN}✓${NC} $*"
    [[ -n "$LOG_FILE" ]] && log_with_time "SUCCESS" "$*" >> "$LOG_FILE"
}

# =============================================================================
# Error Handling
# =============================================================================

# Set error trap
set_error_trap() {
    trap 'handle_error $? $LINENO "$BASH_COMMAND"' ERR
}

# Handle errors
handle_error() {
    local exit_code=$1
    local line_number=$2
    local command=$3

    log_error "Command failed with exit code $exit_code at line $line_number: $command"

    # Call cleanup if defined
    if declare -f cleanup >/dev/null; then
        log_debug "Running cleanup function..."
        cleanup
    fi

    exit "$exit_code"
}

# =============================================================================
# Validation Functions
# =============================================================================

# Check if command exists
check_command() {
    local cmd="$1"
    if ! command -v "$cmd" >/dev/null 2>&1; then
        log_error "Required command not found: $cmd"
        return 1
    fi
    return 0
}

# Check if file exists
check_file() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        log_error "File not found: $file"
        return 1
    fi
    return 0
}

# Check if directory exists
check_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        log_error "Directory not found: $dir"
        return 1
    fi
    return 0
}

# Validate environment variable
check_env() {
    local var_name="$1"
    local var_value="${!var_name}"

    if [[ -z "$var_value" ]]; then
        log_error "Environment variable not set: $var_name"
        return 1
    fi
    return 0
}

# =============================================================================
# Project Path Functions
# =============================================================================

# Get project root directory
get_project_root() {
    local current_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    # Navigate up until we find a marker file (package.json, .git, etc.)
    while [[ "$current_dir" != "/" ]]; do
        if [[ -f "$current_dir/package.json" ]] || \
           [[ -d "$current_dir/.git" ]] || \
           [[ -f "$current_dir/.env" ]] || \
           [[ -d "$current_dir/setup" && -d "$current_dir/backend" && -d "$current_dir/frontend" ]]; then
            echo "$current_dir"
            return 0
        fi
        current_dir="$(dirname "$current_dir")"
    done

    # Fallback: assume we're in scripts/utils/
    echo "$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
}

# Get absolute path
get_absolute_path() {
    local path="$1"

    if [[ -d "$path" ]]; then
        echo "$(cd "$path" && pwd)"
    elif [[ -f "$path" ]]; then
        echo "$(cd "$(dirname "$path")" && pwd)/$(basename "$path")"
    else
        # Path doesn't exist yet, try to resolve parent
        local parent="$(dirname "$path")"
        local name="$(basename "$path")"
        if [[ -d "$parent" ]]; then
            echo "$(cd "$parent" && pwd)/$name"
        else
            echo "$path"
        fi
    fi
}

# =============================================================================
# User Interaction
# =============================================================================

# Prompt for yes/no
confirm() {
    local prompt="${1:-Continue?}"
    local default="${2:-n}"

    local yn
    if [[ "$default" == "y" ]]; then
        read -p "$prompt [Y/n]: " yn
        yn=${yn:-y}
    else
        read -p "$prompt [y/N]: " yn
        yn=${yn:-n}
    fi

    [[ "$yn" =~ ^[Yy] ]]
}

# Prompt for input with default
prompt_input() {
    local prompt="$1"
    local default="$2"
    local var_name="$3"

    local input
    if [[ -n "$default" ]]; then
        read -p "$prompt [$default]: " input
        input="${input:-$default}"
    else
        read -p "$prompt: " input
    fi

    if [[ -n "$var_name" ]]; then
        eval "$var_name='$input'"
    else
        echo "$input"
    fi
}

# =============================================================================
# Progress Indicators
# =============================================================================

# Show spinner
show_spinner() {
    local pid=$1
    local message="${2:-Working...}"
    local spinner='⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏'
    local i=0

    while kill -0 "$pid" 2>/dev/null; do
        i=$(( (i+1) % ${#spinner} ))
        printf "\r${BLUE}${spinner:$i:1}${NC} %s" "$message"
        sleep 0.1
    done

    printf "\r%*s\r" "${#message}" ""
}

# Progress bar
show_progress() {
    local current=$1
    local total=$2
    local message="${3:-Progress}"

    local percent=$((current * 100 / total))
    local filled=$((percent / 2))
    local empty=$((50 - filled))

    printf "\r%s: [" "$message"
    printf "%${filled}s" | tr ' ' '='
    printf "%${empty}s" | tr ' ' ' '
    printf "] %d%%" "$percent"

    if [[ $current -eq $total ]]; then
        echo
    fi
}

# =============================================================================
# Utility Functions
# =============================================================================

# Retry command with exponential backoff
retry_command() {
    local max_attempts="${1:-3}"
    shift
    local delay="${1:-1}"
    shift
    local command="$*"

    local attempt=1
    while [[ $attempt -le $max_attempts ]]; do
        log_debug "Attempt $attempt of $max_attempts: $command"

        if eval "$command"; then
            return 0
        fi

        if [[ $attempt -lt $max_attempts ]]; then
            log_warn "Command failed, retrying in ${delay}s..."
            sleep "$delay"
            delay=$((delay * 2))
        fi

        attempt=$((attempt + 1))
    done

    log_error "Command failed after $max_attempts attempts: $command"
    return 1
}

# Create directory if not exists
ensure_dir() {
    local dir="$1"
    if [[ ! -d "$dir" ]]; then
        log_debug "Creating directory: $dir"
        mkdir -p "$dir"
    fi
}

# Backup file
backup_file() {
    local file="$1"
    local backup="${2:-${file}.backup.$(date +%Y%m%d_%H%M%S)}"

    if [[ -f "$file" ]]; then
        log_debug "Backing up $file to $backup"
        cp "$file" "$backup"
    fi
}

# =============================================================================
# Export Functions
# =============================================================================
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    # Script is being sourced
    export -f log_debug log_info log_warn log_error log_fatal log_step log_success
    export -f check_command check_file check_dir check_env
    export -f get_project_root get_absolute_path
    export -f confirm prompt_input
    export -f show_spinner show_progress
    export -f retry_command ensure_dir backup_file
    export -f set_error_trap handle_error
fi

# =============================================================================
# Self-Test
# =============================================================================
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Common Functions Library Test"
    echo "=============================="

    # Test logging
    log_info "This is an info message"
    log_warn "This is a warning message"
    log_error "This is an error message"
    log_success "This is a success message"
    log_step "This is a step message"

    # Test project root detection
    echo ""
    echo "Project Root: $(get_project_root)"

    # Test platform-specific functions
    echo "Platform: $(detect_platform)"
    echo "Home Dir: $(get_home_dir)"

    # Test validation
    echo ""
    check_command "bash" && log_success "bash command found"
    check_command "nonexistent" || log_warn "nonexistent command not found (expected)"

    echo ""
    echo "All tests completed!"
fi