# 제7강: AI 모델 이해와 로컬 테스트 - 테스트 유틸리티
"""
테스트를 위한 유틸리티 함수들
테스트 데이터 생성, 목 객체 생성, 검증 도구 제공
"""

import os
import numpy as np
import torch
import torch.nn as nn
import torchaudio
from typing import Dict, Any, Optional, Tuple, List, Union
from pathlib import Path
import tempfile
import json
from datetime import datetime
import random

from ai.monitoring.logger import get_logger


logger = get_logger(__name__)


def generate_test_audio(
    duration: float = 3.0,
    sample_rate: int = 16000,
    signal_type: str = 'sine',
    frequency: float = 440.0,
    noise_level: float = 0.1,
    save_path: Optional[str] = None
) -> Tuple[torch.Tensor, str]:
    """
    테스트용 오디오 데이터 생성
    
    Args:
        duration: 오디오 길이 (초)
        sample_rate: 샘플레이트
        signal_type: 신호 타입 ('sine', 'noise', 'chirp', 'voice_like')
        frequency: 주파수 (Hz)
        noise_level: 노이즈 레벨 (0-1)
        save_path: 저장 경로 (선택사항)
        
    Returns:
        (오디오 텐서, 파일 경로)
    """
    num_samples = int(duration * sample_rate)
    t = torch.linspace(0, duration, num_samples)
    
    if signal_type == 'sine':
        # 사인파 생성
        signal = torch.sin(2 * np.pi * frequency * t)
        
    elif signal_type == 'noise':
        # 백색 노이즈
        signal = torch.randn(num_samples)
        
    elif signal_type == 'chirp':
        # 주파수가 변화하는 신호 (chirp)
        f_start, f_end = frequency, frequency * 2
        phase = 2 * np.pi * (f_start * t + (f_end - f_start) * t**2 / (2 * duration))
        signal = torch.sin(phase)
        
    elif signal_type == 'voice_like':
        # 음성과 유사한 신호 생성
        # 여러 주파수 성분 결합
        fundamentals = [220, 440, 880, 1760]  # 기본 주파수들
        harmonics = []
        
        for f in fundamentals:
            harmonics.append(torch.sin(2 * np.pi * f * t) * np.exp(-f/2000))  # 고주파 감쇠
        
        signal = sum(harmonics) / len(harmonics)
        
        # 음성같은 변조 추가
        modulation = 0.3 * torch.sin(2 * np.pi * 5 * t)  # 5Hz 변조
        signal = signal * (1 + modulation)
        
    else:
        raise ValueError(f"지원하지 않는 신호 타입: {signal_type}")
    
    # 노이즈 추가
    if noise_level > 0:
        noise = torch.randn(num_samples) * noise_level
        signal = signal + noise
    
    # 정규화
    signal = signal / torch.max(torch.abs(signal))
    
    # 스테레오로 확장하지 않고 모노 유지
    waveform = signal.unsqueeze(0)  # (1, num_samples)
    
    # 파일 저장
    if save_path is None:
        save_path = os.path.join(tempfile.gettempdir(), f"test_audio_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
    
    # 디렉토리 생성
    os.makedirs(os.path.dirname(save_path), exist_ok=True)
    
    # 오디오 파일 저장
    torchaudio.save(save_path, waveform, sample_rate)
    
    logger.debug(f"테스트 오디오 생성 완료: {save_path} ({signal_type}, {duration}초)")
    
    return waveform, save_path


class MockSincNet(nn.Module):
    """테스트용 SincNet 모델"""
    
    def __init__(self, input_dim: int = 16000, num_classes: int = 4):
        super().__init__()
        self.input_dim = input_dim
        self.num_classes = num_classes
        
        # 간단한 CNN 구조
        self.conv_layers = nn.Sequential(
            nn.Conv1d(1, 64, kernel_size=251, stride=5),
            nn.ReLU(),
            nn.MaxPool1d(3),
            
            nn.Conv1d(64, 128, kernel_size=5),
            nn.ReLU(),
            nn.MaxPool1d(3),
            
            nn.Conv1d(128, 256, kernel_size=5),
            nn.ReLU(),
            nn.MaxPool1d(3),
        )
        
        # 출력 크기 계산을 위한 더미 입력
        with torch.no_grad():
            dummy_input = torch.randn(1, 1, input_dim)
            conv_output = self.conv_layers(dummy_input)
            flattened_size = conv_output.numel()
        
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(flattened_size, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )
    
    def forward(self, x):
        x = self.conv_layers(x)
        x = self.classifier(x)
        return x


def create_mock_model(
    model_type: str = 'sincnet',
    input_dim: int = 16000,
    num_classes: int = 4,
    pretrained_weights: bool = False
) -> nn.Module:
    """
    테스트용 모델 생성
    
    Args:
        model_type: 모델 타입 ('sincnet', 'cnn', 'rnn')
        input_dim: 입력 차원
        num_classes: 클래스 수
        pretrained_weights: 사전 학습된 가중치 사용 여부
        
    Returns:
        생성된 모델
    """
    if model_type == 'sincnet':
        model = MockSincNet(input_dim, num_classes)
        
    elif model_type == 'cnn':
        model = nn.Sequential(
            nn.Conv1d(1, 32, kernel_size=25, stride=2),
            nn.ReLU(),
            nn.MaxPool1d(4),
            
            nn.Conv1d(32, 64, kernel_size=15, stride=2),
            nn.ReLU(),
            nn.MaxPool1d(4),
            
            nn.Flatten(),
            nn.Linear(64 * (input_dim // 64), 128),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(128, num_classes)
        )
        
    elif model_type == 'rnn':
        model = nn.Sequential(
            nn.LSTM(1, 128, batch_first=True, bidirectional=True),
            nn.Lambda(lambda x: x[0][:, -1, :]),  # 마지막 출력만 사용
            nn.Linear(256, 64),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(64, num_classes)
        )
        
    else:
        raise ValueError(f"지원하지 않는 모델 타입: {model_type}")
    
    if pretrained_weights:
        # 임의의 가중치로 초기화 (실제로는 사전 학습된 가중치)
        with torch.no_grad():
            for param in model.parameters():
                param.normal_(0, 0.02)
    
    logger.debug(f"Mock 모델 생성 완료: {model_type}")
    return model


class TestDataGenerator:
    """테스트 데이터 생성기"""
    
    def __init__(self, seed: int = 42):
        """
        Args:
            seed: 랜덤 시드
        """
        self.seed = seed
        self.rng = random.Random(seed)
        np.random.seed(seed)
        torch.manual_seed(seed)
    
    def generate_batch_audio(
        self, 
        batch_size: int = 8,
        duration: float = 3.0,
        sample_rate: int = 16000,
        signal_types: List[str] = None
    ) -> Tuple[torch.Tensor, List[str]]:
        """
        배치 오디오 데이터 생성
        
        Args:
            batch_size: 배치 크기
            duration: 오디오 길이
            sample_rate: 샘플레이트
            signal_types: 사용할 신호 타입들
            
        Returns:
            (배치 텐서, 신호 타입 리스트)
        """
        if signal_types is None:
            signal_types = ['sine', 'noise', 'chirp', 'voice_like']
        
        batch_audio = []
        batch_types = []
        
        num_samples = int(duration * sample_rate)
        
        for i in range(batch_size):
            signal_type = self.rng.choice(signal_types)
            frequency = self.rng.uniform(200, 2000)  # 200Hz ~ 2kHz
            noise_level = self.rng.uniform(0.05, 0.2)
            
            audio, _ = generate_test_audio(
                duration=duration,
                sample_rate=sample_rate,
                signal_type=signal_type,
                frequency=frequency,
                noise_level=noise_level,
                save_path=None
            )
            
            batch_audio.append(audio.squeeze(0))  # (num_samples,)
            batch_types.append(signal_type)
        
        # 배치 텐서로 변환
        batch_tensor = torch.stack(batch_audio).unsqueeze(1)  # (batch_size, 1, num_samples)
        
        return batch_tensor, batch_types
    
    def generate_classification_dataset(
        self,
        num_samples: int = 100,
        num_classes: int = 4,
        duration: float = 3.0,
        sample_rate: int = 16000,
        output_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        분류 데이터셋 생성
        
        Args:
            num_samples: 총 샘플 수
            num_classes: 클래스 수
            duration: 오디오 길이
            sample_rate: 샘플레이트
            output_dir: 저장 디렉토리
            
        Returns:
            데이터셋 정보
        """
        if output_dir is None:
            output_dir = os.path.join(tempfile.gettempdir(), f"test_dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 클래스별 오디오 패턴 정의
        class_patterns = {
            0: {'signal_type': 'sine', 'freq_range': (200, 500)},      # 저음
            1: {'signal_type': 'sine', 'freq_range': (500, 1000)},     # 중음
            2: {'signal_type': 'sine', 'freq_range': (1000, 2000)},    # 고음
            3: {'signal_type': 'voice_like', 'freq_range': (100, 300)} # 음성형
        }
        
        # 사용 가능한 클래스만 선택
        available_classes = list(class_patterns.keys())[:num_classes]
        
        dataset_info = {
            'num_samples': num_samples,
            'num_classes': num_classes,
            'duration': duration,
            'sample_rate': sample_rate,
            'output_dir': output_dir,
            'class_patterns': {k: v for k, v in class_patterns.items() if k in available_classes},
            'files': [],
            'labels': []
        }
        
        samples_per_class = num_samples // num_classes
        
        for class_idx in available_classes:
            pattern = class_patterns[class_idx]
            
            for sample_idx in range(samples_per_class):
                # 주파수 범위에서 랜덤 선택
                freq_min, freq_max = pattern['freq_range']
                frequency = self.rng.uniform(freq_min, freq_max)
                
                # 노이즈 레벨 랜덤화
                noise_level = self.rng.uniform(0.05, 0.15)
                
                # 파일 이름 생성
                filename = f"class_{class_idx:02d}_sample_{sample_idx:04d}.wav"
                file_path = os.path.join(output_dir, filename)
                
                # 오디오 생성
                audio, saved_path = generate_test_audio(
                    duration=duration,
                    sample_rate=sample_rate,
                    signal_type=pattern['signal_type'],
                    frequency=frequency,
                    noise_level=noise_level,
                    save_path=file_path
                )
                
                dataset_info['files'].append(saved_path)
                dataset_info['labels'].append(class_idx)
        
        # 데이터셋 메타데이터 저장
        metadata_path = os.path.join(output_dir, 'dataset_info.json')
        with open(metadata_path, 'w', encoding='utf-8') as f:
            json.dump(dataset_info, f, indent=2, ensure_ascii=False)
        
        logger.info(f"분류 데이터셋 생성 완료: {output_dir} ({num_samples}개 샘플)")
        
        return dataset_info
    
    def generate_feature_test_data(
        self,
        num_samples: int = 20,
        duration: float = 2.0,
        sample_rate: int = 16000
    ) -> Dict[str, torch.Tensor]:
        """
        특징 추출 테스트용 데이터 생성
        
        Args:
            num_samples: 샘플 수
            duration: 오디오 길이
            sample_rate: 샘플레이트
            
        Returns:
            테스트 데이터 딕셔너리
        """
        batch_audio, signal_types = self.generate_batch_audio(
            batch_size=num_samples,
            duration=duration,
            sample_rate=sample_rate
        )
        
        return {
            'audio_batch': batch_audio,
            'signal_types': signal_types,
            'sample_rate': sample_rate,
            'duration': duration
        }
    
    def generate_streaming_test_data(
        self,
        total_duration: float = 10.0,
        chunk_duration: float = 0.5,
        sample_rate: int = 16000
    ) -> List[torch.Tensor]:
        """
        스트리밍 테스트용 데이터 생성
        
        Args:
            total_duration: 전체 오디오 길이
            chunk_duration: 청크 길이
            sample_rate: 샘플레이트
            
        Returns:
            오디오 청크 리스트
        """
        # 전체 오디오 생성
        full_audio, _ = generate_test_audio(
            duration=total_duration,
            sample_rate=sample_rate,
            signal_type='voice_like',
            frequency=440,
            noise_level=0.1
        )
        
        # 청크로 분할
        chunk_samples = int(chunk_duration * sample_rate)
        total_samples = full_audio.shape[1]
        
        chunks = []
        for start in range(0, total_samples, chunk_samples):
            end = min(start + chunk_samples, total_samples)
            chunk = full_audio[:, start:end]
            
            # 짧은 청크는 패딩
            if chunk.shape[1] < chunk_samples:
                padding = chunk_samples - chunk.shape[1]
                chunk = torch.cat([chunk, torch.zeros(1, padding)], dim=1)
            
            chunks.append(chunk)
        
        logger.info(f"스트리밍 테스트 데이터 생성: {len(chunks)}개 청크")
        
        return chunks


class TestValidator:
    """테스트 결과 검증기"""
    
    @staticmethod
    def validate_audio_tensor(tensor: torch.Tensor, expected_shape: Tuple[int, ...] = None) -> bool:
        """오디오 텐서 유효성 검사"""
        if not isinstance(tensor, torch.Tensor):
            logger.error("입력이 torch.Tensor가 아닙니다")
            return False
        
        if tensor.dim() not in [1, 2, 3]:  # (samples,), (channels, samples), (batch, channels, samples)
            logger.error(f"잘못된 텐서 차원: {tensor.dim()}")
            return False
        
        if expected_shape and tensor.shape != expected_shape:
            logger.error(f"예상 모양 불일치: {tensor.shape} != {expected_shape}")
            return False
        
        # NaN이나 무한대 값 검사
        if torch.isnan(tensor).any():
            logger.error("텐서에 NaN 값이 포함되어 있습니다")
            return False
        
        if torch.isinf(tensor).any():
            logger.error("텐서에 무한대 값이 포함되어 있습니다")
            return False
        
        return True
    
    @staticmethod
    def validate_model_output(output: torch.Tensor, num_classes: int) -> bool:
        """모델 출력 유효성 검사"""
        if not isinstance(output, torch.Tensor):
            logger.error("모델 출력이 torch.Tensor가 아닙니다")
            return False
        
        if output.dim() != 2:  # (batch_size, num_classes)
            logger.error(f"모델 출력 차원 오류: {output.dim()} != 2")
            return False
        
        if output.shape[1] != num_classes:
            logger.error(f"클래스 수 불일치: {output.shape[1]} != {num_classes}")
            return False
        
        # NaN이나 무한대 값 검사
        if torch.isnan(output).any():
            logger.error("모델 출력에 NaN 값이 포함되어 있습니다")
            return False
        
        if torch.isinf(output).any():
            logger.error("모델 출력에 무한대 값이 포함되어 있습니다")
            return False
        
        return True
    
    @staticmethod
    def validate_feature_extraction(features: torch.Tensor, feature_type: str) -> bool:
        """특징 추출 결과 유효성 검사"""
        if not isinstance(features, torch.Tensor):
            logger.error("특징이 torch.Tensor가 아닙니다")
            return False
        
        # 특징 타입별 검증
        if feature_type == 'mfcc':
            if features.dim() != 3:  # (batch, n_mfcc, time)
                logger.error(f"MFCC 특징 차원 오류: {features.dim()} != 3")
                return False
        
        elif feature_type == 'mel_spectrogram':
            if features.dim() != 3:  # (batch, n_mels, time)
                logger.error(f"Mel-spectrogram 특징 차원 오류: {features.dim()} != 3")
                return False
        
        # 모든 값이 유한한지 검사
        if not torch.isfinite(features).all():
            logger.error("특징에 무한대 또는 NaN 값이 포함되어 있습니다")
            return False
        
        return True
    
    @staticmethod
    def validate_processing_time(processing_time: float, max_time: float = 5.0) -> bool:
        """처리 시간 유효성 검사"""
        if not isinstance(processing_time, (int, float)):
            logger.error("처리 시간이 숫자가 아닙니다")
            return False
        
        if processing_time < 0:
            logger.error("처리 시간이 음수입니다")
            return False
        
        if processing_time > max_time:
            logger.warning(f"처리 시간이 너무 깁니다: {processing_time:.3f}초 > {max_time}초")
            return False
        
        return True


def cleanup_test_files(file_paths: List[str]):
    """테스트 파일들 정리"""
    cleaned_count = 0
    for file_path in file_paths:
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                cleaned_count += 1
        except Exception as e:
            logger.error(f"파일 삭제 실패 {file_path}: {str(e)}")
    
    if cleaned_count > 0:
        logger.info(f"테스트 파일 {cleaned_count}개 정리 완료")


def compare_tensors(tensor1: torch.Tensor, tensor2: torch.Tensor, tolerance: float = 1e-6) -> bool:
    """텐서 비교"""
    if tensor1.shape != tensor2.shape:
        logger.error(f"텐서 모양 불일치: {tensor1.shape} != {tensor2.shape}")
        return False
    
    diff = torch.abs(tensor1 - tensor2)
    max_diff = torch.max(diff).item()
    
    if max_diff > tolerance:
        logger.error(f"텐서 값 차이가 허용 범위를 초과: {max_diff} > {tolerance}")
        return False
    
    return True