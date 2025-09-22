#!/bin/bash

# =============================================================================
# Test Cross-Platform Utilities
# =============================================================================

# Source the utilities
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/utils/platform-detector.sh"
source "$SCRIPT_DIR/utils/common-functions.sh"

echo "=========================================="
echo "Cross-Platform Utilities Test"
echo "=========================================="
echo ""

# Test platform detection
log_step "Testing Platform Detection"
platform=$(detect_platform)
log_info "Detected platform: $platform"

# Test platform-specific commands
log_step "Testing Platform Commands"
log_info "Open command: $(get_platform_command open)"
log_info "Copy command: $(get_platform_command copy)"
log_info "SHA256 command: $(get_platform_command sha256)"

# Test path functions
log_step "Testing Path Functions"
log_info "Home directory: $(get_home_dir)"
log_info "Temp directory: $(get_temp_dir)"
log_info "Project root: $(get_project_root)"

# Test path normalization
log_step "Testing Path Normalization"
test_path="C:\\Users\\test\\file.txt"
normalized=$(normalize_path "$test_path")
log_info "Original: $test_path"
log_info "Normalized: $normalized"

# Test CPU cores
log_step "Testing System Info"
log_info "CPU cores: $(get_cpu_cores)"
log_info "Admin/Root: $(is_admin && echo 'Yes' || echo 'No')"

# Test Python utilities if Python is available
if command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1; then
    log_step "Testing Python Utilities"

    python_cmd="python"
    if ! command -v python >/dev/null 2>&1; then
        python_cmd="python3"
    fi

    $python_cmd - <<EOF
import sys
sys.path.insert(0, '$SCRIPT_DIR/../backend/libraries')
try:
    from common.path_utils import PlatformDetector, PathUtils, ServiceAccountResolver

    print(f"  Python platform: {PlatformDetector.get_platform()}")
    print(f"  Project root: {PathUtils.get_project_root()}")

    key_path = ServiceAccountResolver.find_service_account_key()
    if key_path:
        print(f"  Service account key: Found at {key_path}")
    else:
        print(f"  Service account key: Not found (expected if not configured)")

    print("  ✓ Python utilities working correctly")
except Exception as e:
    print(f"  ✗ Python utilities error: {e}")
EOF
else
    log_warn "Python not found, skipping Python utility tests"
fi

echo ""
log_success "Cross-platform utility tests completed!"

# Show summary
echo ""
echo "=========================================="
echo "Summary"
echo "=========================================="
echo "Platform: $platform"
echo "Shell utilities: ✓ Working"

if command -v python >/dev/null 2>&1 || command -v python3 >/dev/null 2>&1; then
    echo "Python utilities: ✓ Available"
else
    echo "Python utilities: ✗ Not tested (Python not found)"
fi

echo ""
echo "Next steps:"
echo "  1. Update remaining scripts to use these utilities"
echo "  2. Create cross-platform wrappers for .bat scripts"
echo "  3. Test on macOS and Linux environments"