"""
SincNet Audio Analysis Module
Provides depression and insomnia analysis using original SincNet architecture
"""

from .original_sincnet_analyzer import OriginalSincNetAnalyzer

# Main interface - use the original (working) analyzer
SincNetAnalyzer = OriginalSincNetAnalyzer

__all__ = [
    'SincNetAnalyzer',
    'OriginalSincNetAnalyzer'
]