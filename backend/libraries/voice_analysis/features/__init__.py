# 제7강: AI 모델 이해와 로컬 테스트 - 특징 추출 모듈
"""
음성 특징 추출 모듈
MFCC, Mel-spectrogram 등 오디오 신호 처리 기능 제공
"""

from .mfcc_extractor import MFCCExtractor
from .mel_extractor import MelSpectrogramExtractor

__all__ = ['MFCCExtractor', 'MelSpectrogramExtractor']