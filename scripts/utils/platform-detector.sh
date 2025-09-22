#!/bin/bash

# =============================================================================
# Platform Detection Utility for Senior MHealth
# =============================================================================
# Provides consistent platform detection across all scripts
# Supports: Windows (Git Bash, WSL, Cygwin), macOS, Linux
# =============================================================================

# Detect the current platform
detect_platform() {
    local platform=""

    # Check OSTYPE environment variable
    case "$OSTYPE" in
        linux-gnu*)
            # Linux or WSL
            if grep -qi microsoft /proc/version 2>/dev/null; then
                platform="wsl"
            else
                platform="linux"
            fi
            ;;
        darwin*)
            # macOS
            platform="macos"
            ;;
        cygwin* | msys* | win32*)
            # Windows (Git Bash, Cygwin, MSYS2)
            platform="windows"
            ;;
        freebsd* | openbsd* | netbsd*)
            # BSD variants
            platform="bsd"
            ;;
        *)
            # Unknown, try uname
            case "$(uname -s)" in
                Linux*)
                    platform="linux"
                    ;;
                Darwin*)
                    platform="macos"
                    ;;
                CYGWIN* | MINGW* | MSYS*)
                    platform="windows"
                    ;;
                *)
                    platform="unknown"
                    ;;
            esac
            ;;
    esac

    echo "$platform"
}

# Get platform-specific command
get_platform_command() {
    local command_type="$1"
    local platform=$(detect_platform)

    case "$command_type" in
        "open")
            # Command to open files/URLs
            case "$platform" in
                macos) echo "open" ;;
                linux | wsl) echo "xdg-open" ;;
                windows) echo "start" ;;
                *) echo "echo 'Cannot open on platform: $platform'" ;;
            esac
            ;;
        "copy")
            # Command to copy to clipboard
            case "$platform" in
                macos) echo "pbcopy" ;;
                linux | wsl) echo "xclip -selection clipboard" ;;
                windows) echo "clip" ;;
                *) echo "cat" ;;
            esac
            ;;
        "paste")
            # Command to paste from clipboard
            case "$platform" in
                macos) echo "pbpaste" ;;
                linux | wsl) echo "xclip -selection clipboard -o" ;;
                windows) echo "powershell Get-Clipboard" ;;
                *) echo "echo ''" ;;
            esac
            ;;
        "sha256")
            # Command to calculate SHA256
            case "$platform" in
                macos) echo "shasum -a 256" ;;
                linux | wsl | bsd) echo "sha256sum" ;;
                windows) echo "certutil -hashfile" ;;
                *) echo "echo 'SHA256 not available'" ;;
            esac
            ;;
        "sed")
            # Sed command with platform-specific options
            case "$platform" in
                macos | bsd) echo "sed -i ''" ;;
                linux | wsl | windows) echo "sed -i" ;;
                *) echo "sed" ;;
            esac
            ;;
        *)
            echo "echo 'Unknown command type: $command_type'"
            ;;
    esac
}

# Get platform-specific path separator
get_path_separator() {
    local platform=$(detect_platform)

    case "$platform" in
        windows)
            echo "\\"
            ;;
        *)
            echo "/"
            ;;
    esac
}

# Normalize path for current platform
normalize_path() {
    local path="$1"
    local platform=$(detect_platform)

    # Convert Windows paths to Unix format for Git Bash
    if [[ "$platform" == "windows" ]]; then
        # Running in Git Bash or similar
        echo "$path" | sed 's|\\|/|g'
    else
        # Unix-like systems
        echo "$path"
    fi
}

# Convert path to native format
to_native_path() {
    local path="$1"
    local platform=$(detect_platform)

    case "$platform" in
        windows)
            # Convert to Windows format if needed
            if command -v cygpath >/dev/null 2>&1; then
                cygpath -w "$path"
            else
                echo "$path" | sed 's|/|\\|g'
            fi
            ;;
        *)
            # Keep Unix format
            echo "$path"
            ;;
    esac
}

# Get home directory path
get_home_dir() {
    local platform=$(detect_platform)

    case "$platform" in
        windows)
            # Windows home directory
            if [[ -n "$USERPROFILE" ]]; then
                normalize_path "$USERPROFILE"
            else
                echo "$HOME"
            fi
            ;;
        *)
            echo "$HOME"
            ;;
    esac
}

# Get temp directory path
get_temp_dir() {
    local platform=$(detect_platform)

    case "$platform" in
        windows)
            if [[ -n "$TEMP" ]]; then
                normalize_path "$TEMP"
            elif [[ -n "$TMP" ]]; then
                normalize_path "$TMP"
            else
                echo "/tmp"
            fi
            ;;
        macos | linux | wsl)
            echo "${TMPDIR:-/tmp}"
            ;;
        *)
            echo "/tmp"
            ;;
    esac
}

# Check if running with admin/sudo privileges
is_admin() {
    local platform=$(detect_platform)

    case "$platform" in
        windows)
            # Check if running as administrator in Windows
            if net session >/dev/null 2>&1; then
                return 0
            else
                return 1
            fi
            ;;
        *)
            # Check if running as root or with sudo
            if [[ $EUID -eq 0 ]] || sudo -n true 2>/dev/null; then
                return 0
            else
                return 1
            fi
            ;;
    esac
}

# Get number of CPU cores
get_cpu_cores() {
    local platform=$(detect_platform)

    case "$platform" in
        macos | bsd)
            sysctl -n hw.ncpu 2>/dev/null || echo "1"
            ;;
        linux | wsl)
            nproc 2>/dev/null || echo "1"
            ;;
        windows)
            echo "$NUMBER_OF_PROCESSORS" || echo "1"
            ;;
        *)
            echo "1"
            ;;
    esac
}

# Export functions if sourced
if [[ "${BASH_SOURCE[0]}" != "${0}" ]]; then
    export -f detect_platform
    export -f get_platform_command
    export -f get_path_separator
    export -f normalize_path
    export -f to_native_path
    export -f get_home_dir
    export -f get_temp_dir
    export -f is_admin
    export -f get_cpu_cores
fi

# If run directly, show platform info
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Platform Detection Utility"
    echo "=========================="
    echo "Platform: $(detect_platform)"
    echo "Home Dir: $(get_home_dir)"
    echo "Temp Dir: $(get_temp_dir)"
    echo "CPU Cores: $(get_cpu_cores)"
    echo "Admin/Root: $(is_admin && echo 'Yes' || echo 'No')"
    echo ""
    echo "Platform Commands:"
    echo "  Open: $(get_platform_command open)"
    echo "  Copy: $(get_platform_command copy)"
    echo "  SHA256: $(get_platform_command sha256)"
fi