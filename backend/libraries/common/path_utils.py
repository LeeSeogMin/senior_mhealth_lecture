"""
Cross-Platform Path Utilities for Senior MHealth
Python implementation of pathHelper.js patterns
"""

import os
import sys
import platform
import json
import logging
from pathlib import Path
from typing import Optional, List, Union, Dict

logger = logging.getLogger(__name__)


class PlatformDetector:
    """Detect and handle platform-specific operations"""

    @staticmethod
    def get_platform() -> str:
        """
        Detect current platform
        Returns: 'windows', 'macos', 'linux', 'wsl', or 'unknown'
        """
        system = platform.system().lower()

        if system == 'windows':
            return 'windows'
        elif system == 'darwin':
            return 'macos'
        elif system == 'linux':
            # Check for WSL
            try:
                with open('/proc/version', 'r') as f:
                    if 'microsoft' in f.read().lower():
                        return 'wsl'
            except:
                pass
            return 'linux'
        else:
            return 'unknown'

    @staticmethod
    def is_windows() -> bool:
        """Check if running on Windows"""
        return PlatformDetector.get_platform() == 'windows'

    @staticmethod
    def is_macos() -> bool:
        """Check if running on macOS"""
        return PlatformDetector.get_platform() == 'macos'

    @staticmethod
    def is_linux() -> bool:
        """Check if running on Linux (including WSL)"""
        platform = PlatformDetector.get_platform()
        return platform in ['linux', 'wsl']

    @staticmethod
    def is_wsl() -> bool:
        """Check if running in WSL"""
        return PlatformDetector.get_platform() == 'wsl'


class PathUtils:
    """Cross-platform path handling utilities"""

    @staticmethod
    def normalize_path(path: Union[str, Path]) -> str:
        """
        Normalize path for cross-platform compatibility
        Converts backslashes to forward slashes
        """
        if not path:
            return ""

        # Convert to string if Path object
        if isinstance(path, Path):
            path = str(path)

        # Replace backslashes with forward slashes
        normalized = path.replace('\\', '/')

        # Remove duplicate slashes
        while '//' in normalized:
            normalized = normalized.replace('//', '/')

        return normalized

    @staticmethod
    def to_native_path(path: Union[str, Path]) -> str:
        """
        Convert path to native format for current platform
        """
        if not path:
            return ""

        # Convert to Path object for proper handling
        path_obj = Path(path)

        # Return native string representation
        return str(path_obj)

    @staticmethod
    def get_project_root() -> Path:
        """
        Get project root directory
        Looks for markers like .git, package.json, setup/backend/frontend folders
        """
        current = Path(__file__).resolve()

        # Navigate up looking for project markers
        for parent in current.parents:
            # Check for common project root markers
            if any([
                (parent / '.git').exists(),
                (parent / 'package.json').exists(),
                (parent / 'setup.py').exists(),
                all([
                    (parent / 'setup').is_dir(),
                    (parent / 'backend').is_dir(),
                    (parent / 'frontend').is_dir()
                ])
            ]):
                return parent

        # Fallback: assume we're in backend/libraries/common/
        # Go up 3 levels
        return current.parent.parent.parent

    @staticmethod
    def get_home_dir() -> Path:
        """Get user home directory (cross-platform)"""
        return Path.home()

    @staticmethod
    def get_temp_dir() -> Path:
        """Get temporary directory (cross-platform)"""
        import tempfile
        return Path(tempfile.gettempdir())

    @staticmethod
    def resolve_path(path: Union[str, Path], base: Optional[Union[str, Path]] = None) -> Path:
        """
        Resolve a path, optionally relative to a base directory
        """
        path_obj = Path(path)

        # If path is absolute, return it
        if path_obj.is_absolute():
            return path_obj.resolve()

        # If base is provided, resolve relative to base
        if base:
            base_path = Path(base)
            return (base_path / path_obj).resolve()

        # Otherwise, resolve relative to current directory
        return path_obj.resolve()

    @staticmethod
    def ensure_dir(path: Union[str, Path]) -> Path:
        """
        Ensure directory exists, create if necessary
        """
        path_obj = Path(path)
        path_obj.mkdir(parents=True, exist_ok=True)
        return path_obj

    @staticmethod
    def join_paths(*parts: Union[str, Path]) -> str:
        """
        Join path parts in a cross-platform way
        Returns normalized string path
        """
        # Filter out empty parts
        valid_parts = [p for p in parts if p]

        if not valid_parts:
            return ""

        # Use Path to join, then normalize
        joined = Path(valid_parts[0])
        for part in valid_parts[1:]:
            joined = joined / part

        return PathUtils.normalize_path(str(joined))


class ServiceAccountResolver:
    """Resolve service account key file location"""

    @staticmethod
    def find_service_account_key() -> Optional[Path]:
        """
        Find service account key file with multiple fallback locations
        Similar to pathHelper.js getServiceAccountPath()
        """
        # Check environment variable first
        env_path = os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        if env_path:
            path = Path(env_path)
            if not path.is_absolute():
                # Relative to project root
                project_root = PathUtils.get_project_root()
                path = project_root / path

            if path.exists():
                logger.info(f"Service account key found from env: {path}")
                return path

        # Standard locations to check
        project_root = PathUtils.get_project_root()
        possible_paths = [
            # New standard name
            project_root / 'serviceAccountKey.json',
            # Old name (fallback)
            project_root / 'service-account-key.json',
            # Current directory
            Path.cwd() / 'serviceAccountKey.json',
            Path.cwd() / 'service-account-key.json',
            # Docker paths
            Path('/app/serviceAccountKey.json'),
            Path('/app/service-account-key.json'),
            # Backend directory
            project_root / 'backend' / 'serviceAccountKey.json',
            project_root / 'backend' / 'service-account-key.json',
        ]

        # Add Windows-specific path if on Windows (for backward compatibility)
        if PlatformDetector.is_windows():
            possible_paths.append(Path('C:/Senior_MHealth/serviceAccountKey.json'))

        # Check each path
        for path in possible_paths:
            if path.exists():
                logger.info(f"Service account key found: {path}")
                return path

        logger.warning("Service account key file not found in any standard location")
        return None

    @staticmethod
    def set_credentials_env() -> bool:
        """
        Set GOOGLE_APPLICATION_CREDENTIALS environment variable
        """
        key_path = ServiceAccountResolver.find_service_account_key()
        if key_path:
            os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = str(key_path)
            logger.info(f"Set GOOGLE_APPLICATION_CREDENTIALS: {key_path}")
            return True

        logger.error("Could not set GOOGLE_APPLICATION_CREDENTIALS - key file not found")
        return False


class EnvironmentUtils:
    """Environment detection and configuration utilities"""

    @staticmethod
    def is_docker() -> bool:
        """Check if running in Docker container"""
        return (
            Path('/.dockerenv').exists() or
            Path('/var/run/secrets/kubernetes.io').exists() or
            os.getenv('KUBERNETES_SERVICE_HOST') is not None
        )

    @staticmethod
    def is_cloud_run() -> bool:
        """Check if running on Google Cloud Run"""
        return os.getenv('K_SERVICE') is not None

    @staticmethod
    def is_github_actions() -> bool:
        """Check if running in GitHub Actions"""
        return os.getenv('GITHUB_ACTIONS') == 'true'

    @staticmethod
    def is_ci() -> bool:
        """Check if running in any CI environment"""
        ci_env_vars = ['CI', 'CONTINUOUS_INTEGRATION', 'GITHUB_ACTIONS', 'GITLAB_CI', 'JENKINS_URL']
        return any(os.getenv(var) for var in ci_env_vars)

    @staticmethod
    def get_environment() -> str:
        """
        Get current environment (development, staging, production)
        """
        env = os.getenv('ENVIRONMENT', os.getenv('ENV', 'development')).lower()
        if env in ['prod', 'production']:
            return 'production'
        elif env in ['stage', 'staging']:
            return 'staging'
        else:
            return 'development'

    @staticmethod
    def load_env_file(env_file: Optional[Union[str, Path]] = None) -> Dict[str, str]:
        """
        Load environment variables from .env file
        """
        if not env_file:
            # Try to find .env file
            project_root = PathUtils.get_project_root()
            for name in ['.env.local', '.env']:
                env_path = project_root / name
                if env_path.exists():
                    env_file = env_path
                    break

        if not env_file or not Path(env_file).exists():
            logger.debug("No .env file found")
            return {}

        env_vars = {}
        try:
            with open(env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        # Remove quotes if present
                        value = value.strip()
                        if value.startswith('"') and value.endswith('"'):
                            value = value[1:-1]
                        elif value.startswith("'") and value.endswith("'"):
                            value = value[1:-1]
                        env_vars[key.strip()] = value

            logger.info(f"Loaded {len(env_vars)} environment variables from {env_file}")
        except Exception as e:
            logger.error(f"Error loading env file {env_file}: {e}")

        return env_vars


def initialize_environment():
    """
    Initialize environment for cross-platform compatibility
    Similar to pathHelper.js initializeEnvironment()
    """
    # Load environment variables
    env_vars = EnvironmentUtils.load_env_file()
    for key, value in env_vars.items():
        if key not in os.environ:
            os.environ[key] = value

    # Set up service account if needed
    if not EnvironmentUtils.is_cloud_run():
        ServiceAccountResolver.set_credentials_env()

    # Log platform info
    platform_info = PlatformDetector.get_platform()
    environment = EnvironmentUtils.get_environment()

    logger.info(f"Platform: {platform_info}")
    logger.info(f"Environment: {environment}")
    logger.info(f"Project Root: {PathUtils.get_project_root()}")
    logger.info(f"Working Directory: {Path.cwd()}")

    if EnvironmentUtils.is_docker():
        logger.info("Running in Docker container")
    if EnvironmentUtils.is_cloud_run():
        logger.info("Running on Google Cloud Run")
    if EnvironmentUtils.is_ci():
        logger.info("Running in CI environment")


# Self-test when run directly
if __name__ == "__main__":
    # Configure logging for test
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')

    print("Path Utilities Test")
    print("=" * 50)

    # Test platform detection
    print(f"Platform: {PlatformDetector.get_platform()}")
    print(f"Is Windows: {PlatformDetector.is_windows()}")
    print(f"Is macOS: {PlatformDetector.is_macos()}")
    print(f"Is Linux: {PlatformDetector.is_linux()}")
    print(f"Is WSL: {PlatformDetector.is_wsl()}")
    print()

    # Test path utilities
    print(f"Project Root: {PathUtils.get_project_root()}")
    print(f"Home Dir: {PathUtils.get_home_dir()}")
    print(f"Temp Dir: {PathUtils.get_temp_dir()}")
    print()

    # Test path normalization
    test_paths = [
        "C:\\Users\\test\\file.txt",
        "/home/user/file.txt",
        "relative/path/to\\file.txt"
    ]
    for path in test_paths:
        print(f"Normalize '{path}': {PathUtils.normalize_path(path)}")
    print()

    # Test path joining
    joined = PathUtils.join_paths("base", "dir", "file.txt")
    print(f"Join paths: {joined}")
    print()

    # Test environment detection
    print(f"Is Docker: {EnvironmentUtils.is_docker()}")
    print(f"Is Cloud Run: {EnvironmentUtils.is_cloud_run()}")
    print(f"Is CI: {EnvironmentUtils.is_ci()}")
    print(f"Environment: {EnvironmentUtils.get_environment()}")
    print()

    # Test service account resolution
    key_path = ServiceAccountResolver.find_service_account_key()
    if key_path:
        print(f"Service Account Key: {key_path}")
    else:
        print("Service Account Key: Not found")

    print("\nAll tests completed!")