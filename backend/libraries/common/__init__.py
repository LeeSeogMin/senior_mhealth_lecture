"""
Common utilities for Senior MHealth backend
Cross-platform support utilities
"""

from .path_utils import (
    PlatformDetector,
    PathUtils,
    ServiceAccountResolver,
    EnvironmentUtils,
    initialize_environment
)

__all__ = [
    'PlatformDetector',
    'PathUtils',
    'ServiceAccountResolver',
    'EnvironmentUtils',
    'initialize_environment'
]

__version__ = '1.0.0'