"""
SincNet 기반 우울/불면 분석 모듈
Phase 2: Enhanced 단계의 핵심 컴포넌트
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import logging
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
import librosa
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class SincNetConfig:
    """SincNet 설정"""
    sample_rate: int = 16000
    frame_length: int = 200  # ms
    frame_shift: int = 10  # ms
    num_filters: int = 80
    filter_length: int = 251
    hidden_size: int = 256
    num_classes: int = 2  # 우울/정상 or 불면/정상
    dropout: float = 0.2
    model_path: Optional[str] = None


class SincConv1d(nn.Module):
    """Sinc 함수 기반 1D Convolution Layer"""
    
    def __init__(self, in_channels, out_channels, kernel_size, sample_rate=16000):
        super(SincConv1d, self).__init__()
        
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.sample_rate = sample_rate
        
        # 주파수 파라미터 (학습 가능)
        hz = np.linspace(30, sample_rate/2, out_channels + 1)
        self.lower_freq = nn.Parameter(torch.Tensor(hz[:-1]).view(-1, 1))
        self.band_freq = nn.Parameter(torch.Tensor(np.diff(hz)).view(-1, 1))
        
        # Hamming window
        n = np.linspace(0, kernel_size, kernel_size)
        window = 0.54 - 0.46 * np.cos(2 * np.pi * n / kernel_size)
        self.window = torch.Tensor(window).view(1, -1)
        
    def forward(self, x):
        """Forward pass"""
        # Sinc 필터 생성
        filters = self._create_sinc_filters()
        
        # Convolution
        return F.conv1d(x, filters, stride=1, padding=self.kernel_size//2)
    
    def _create_sinc_filters(self):
        """Sinc 필터 생성"""
        # 시간 축
        n = torch.linspace(0, self.kernel_size - 1, self.kernel_size).view(1, -1) - (self.kernel_size - 1) / 2
        
        # 주파수를 라디안으로 변환
        f_lower = self.lower_freq / self.sample_rate * 2 * np.pi
        f_upper = (self.lower_freq + self.band_freq) / self.sample_rate * 2 * np.pi
        
        # Sinc 함수
        n = n / self.sample_rate
        sinc_lower = torch.sin(f_lower * n) / (n + 1e-10)
        sinc_upper = torch.sin(f_upper * n) / (n + 1e-10)
        
        # Band-pass 필터
        filters = (sinc_upper - sinc_lower) * self.window
        
        # 정규화
        filters = filters / torch.max(torch.abs(filters), dim=1, keepdim=True)[0]
        
        return filters.unsqueeze(1)


class SincNetModel(nn.Module):
    """SincNet 모델 아키텍처"""
    
    def __init__(self, config: SincNetConfig):
        super(SincNetModel, self).__init__()
        
        self.config = config
        
        # SincNet layers
        self.sinc_conv1 = SincConv1d(1, config.num_filters, config.filter_length, config.sample_rate)
        self.bn1 = nn.BatchNorm1d(config.num_filters)
        
        self.conv2 = nn.Conv1d(config.num_filters, config.num_filters, 5)
        self.bn2 = nn.BatchNorm1d(config.num_filters)
        
        self.conv3 = nn.Conv1d(config.num_filters, config.num_filters, 5)
        self.bn3 = nn.BatchNorm1d(config.num_filters)
        
        # LSTM layers
        self.lstm = nn.LSTM(
            input_size=config.num_filters,
            hidden_size=config.hidden_size,
            num_layers=2,
            batch_first=True,
            dropout=config.dropout,
            bidirectional=True
        )
        
        # Classification layers
        self.fc1 = nn.Linear(config.hidden_size * 2, 128)
        self.dropout = nn.Dropout(config.dropout)
        self.fc2 = nn.Linear(128, config.num_classes)
        
    def forward(self, x):
        """Forward pass"""
        # x shape: (batch, time)
        x = x.unsqueeze(1)  # (batch, 1, time)
        
        # SincNet layers
        x = F.relu(self.bn1(self.sinc_conv1(x)))
        x = F.max_pool1d(x, 3)
        
        x = F.relu(self.bn2(self.conv2(x)))
        x = F.max_pool1d(x, 3)
        
        x = F.relu(self.bn3(self.conv3(x)))
        x = F.max_pool1d(x, 3)
        
        # Prepare for LSTM
        x = x.transpose(1, 2)  # (batch, time, features)
        
        # LSTM
        lstm_out, _ = self.lstm(x)
        
        # Global average pooling
        x = torch.mean(lstm_out, dim=1)
        
        # Classification
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = self.fc2(x)
        
        return x


class SincNetAnalyzer:
    """SincNet 기반 우울/불면 분석기"""
    
    def __init__(self, model_type: str = 'depression', device: str = 'cpu'):
        """
        초기화
        
        Args:
            model_type: 'depression' or 'insomnia'
            device: 'cpu' or 'cuda'
        """
        self.model_type = model_type
        self.device = torch.device(device)
        
        # 설정 로드
        self.config = SincNetConfig()
        
        # 모델 로드
        self.model = self._load_model()
        self.model.to(self.device)
        self.model.eval()
        
        logger.info(f"SincNet {model_type} 모델 초기화 완료")
    
    def _load_model(self) -> SincNetModel:
        """모델 로드 (또는 초기화)"""
        model = SincNetModel(self.config)
        
        # 사전 학습된 가중치 로드 시도
        if self.config.model_path and Path(self.config.model_path).exists():
            try:
                checkpoint = torch.load(
                    self.config.model_path,
                    map_location=self.device
                )
                model.load_state_dict(checkpoint['model_state_dict'])
                logger.info(f"사전 학습된 모델 로드: {self.config.model_path}")
            except Exception as e:
                logger.warning(f"모델 로드 실패, 랜덤 초기화 사용: {e}")
        else:
            logger.warning("사전 학습된 모델 없음, 랜덤 초기화 사용")
        
        return model
    
    def analyze(self, audio_path: str) -> Dict[str, Any]:
        """
        오디오 분석
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            분석 결과
        """
        try:
            # 오디오 로드
            audio, sr = librosa.load(audio_path, sr=self.config.sample_rate)
            
            # 전처리
            audio = self._preprocess_audio(audio)
            
            # 추론
            with torch.no_grad():
                # 배치 차원 추가
                audio_tensor = torch.FloatTensor(audio).unsqueeze(0).to(self.device)
                
                # 모델 추론
                outputs = self.model(audio_tensor)
                probabilities = F.softmax(outputs, dim=1)
                
                # 결과 파싱
                prob_positive = probabilities[0, 1].item()  # 우울/불면 확률
                prob_negative = probabilities[0, 0].item()  # 정상 확률
            
            result = {
                'success': True,
                'model_type': self.model_type,
                'probability': prob_positive,
                'confidence': max(prob_positive, prob_negative),
                'prediction': 'positive' if prob_positive > 0.5 else 'negative',
                'scores': {
                    f'{self.model_type}_positive': prob_positive,
                    f'{self.model_type}_negative': prob_negative
                }
            }
            
            # 해석 추가
            result['interpretation'] = self._interpret_result(prob_positive)
            
            return result
            
        except Exception as e:
            logger.error(f"SincNet 분석 실패: {e}")
            return {
                'success': False,
                'error': str(e),
                'model_type': self.model_type
            }
    
    def analyze_segments(
        self,
        audio_path: str,
        segments: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        세그먼트별 분석
        
        Args:
            audio_path: 오디오 파일 경로
            segments: 분석할 세그먼트 리스트
            
        Returns:
            세그먼트별 분석 결과
        """
        results = []
        
        for segment in segments:
            # 세그먼트 오디오 추출
            audio, sr = librosa.load(
                audio_path,
                sr=self.config.sample_rate,
                offset=segment['start_time'],
                duration=segment['end_time'] - segment['start_time']
            )
            
            # 최소 길이 체크
            if len(audio) < self.config.sample_rate:  # 최소 1초
                continue
            
            # 임시 파일로 저장하고 분석
            # (실제로는 메모리에서 직접 처리하는 것이 효율적)
            segment_result = self._analyze_audio_array(audio)
            segment_result['segment'] = segment
            results.append(segment_result)
        
        # 전체 통계
        if results:
            avg_probability = np.mean([r['probability'] for r in results])
            max_probability = np.max([r['probability'] for r in results])
            
            return {
                'success': True,
                'model_type': self.model_type,
                'segment_results': results,
                'average_probability': avg_probability,
                'max_probability': max_probability,
                'overall_prediction': 'positive' if avg_probability > 0.5 else 'negative'
            }
        else:
            return {
                'success': False,
                'error': 'No valid segments to analyze'
            }
    
    def _preprocess_audio(self, audio: np.ndarray) -> np.ndarray:
        """오디오 전처리"""
        # 정규화
        if np.max(np.abs(audio)) > 0:
            audio = audio / np.max(np.abs(audio))
        
        # 침묵 제거
        audio, _ = librosa.effects.trim(audio, top_db=20)
        
        # 길이 조정 (필요시 패딩 또는 자르기)
        target_length = self.config.sample_rate * 10  # 10초
        
        if len(audio) > target_length:
            audio = audio[:target_length]
        elif len(audio) < target_length:
            padding = target_length - len(audio)
            audio = np.pad(audio, (0, padding), mode='constant')
        
        return audio
    
    def _analyze_audio_array(self, audio: np.ndarray) -> Dict[str, Any]:
        """오디오 배열 직접 분석"""
        try:
            audio = self._preprocess_audio(audio)
            
            with torch.no_grad():
                audio_tensor = torch.FloatTensor(audio).unsqueeze(0).to(self.device)
                outputs = self.model(audio_tensor)
                probabilities = F.softmax(outputs, dim=1)
                prob_positive = probabilities[0, 1].item()
            
            return {
                'success': True,
                'probability': prob_positive,
                'prediction': 'positive' if prob_positive > 0.5 else 'negative'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def _interpret_result(self, probability: float) -> str:
        """결과 해석"""
        if self.model_type == 'depression':
            if probability < 0.3:
                return "우울 위험이 낮습니다."
            elif probability < 0.5:
                return "경미한 우울 증상이 있을 수 있습니다."
            elif probability < 0.7:
                return "중등도 우울 위험이 있습니다."
            else:
                return "높은 우울 위험이 감지됩니다."
        
        elif self.model_type == 'insomnia':
            if probability < 0.3:
                return "수면 상태가 양호합니다."
            elif probability < 0.5:
                return "가벼운 수면 문제가 있을 수 있습니다."
            elif probability < 0.7:
                return "수면 장애 가능성이 있습니다."
            else:
                return "심각한 수면 문제가 의심됩니다."
        
        return "평가 중"
    
    def train(
        self,
        train_data: List[Tuple[str, int]],
        val_data: List[Tuple[str, int]],
        epochs: int = 50,
        batch_size: int = 32,
        learning_rate: float = 0.001
    ) -> Dict[str, Any]:
        """
        모델 학습 (한국 노인 특화)
        
        Args:
            train_data: [(audio_path, label), ...] 형식의 학습 데이터
            val_data: 검증 데이터
            epochs: 학습 에폭
            batch_size: 배치 크기
            learning_rate: 학습률
            
        Returns:
            학습 결과
        """
        # 데이터 로더 준비
        train_loader = self._prepare_dataloader(train_data, batch_size, shuffle=True)
        val_loader = self._prepare_dataloader(val_data, batch_size, shuffle=False)
        
        # 옵티마이저와 손실 함수
        optimizer = torch.optim.Adam(self.model.parameters(), lr=learning_rate)
        criterion = nn.CrossEntropyLoss()
        
        # 학습 모드
        self.model.train()
        
        history = {
            'train_loss': [],
            'train_acc': [],
            'val_loss': [],
            'val_acc': []
        }
        
        for epoch in range(epochs):
            # Training
            train_loss, train_acc = self._train_epoch(
                train_loader, optimizer, criterion
            )
            
            # Validation
            val_loss, val_acc = self._validate_epoch(val_loader, criterion)
            
            # 기록
            history['train_loss'].append(train_loss)
            history['train_acc'].append(train_acc)
            history['val_loss'].append(val_loss)
            history['val_acc'].append(val_acc)
            
            logger.info(
                f"Epoch {epoch+1}/{epochs} - "
                f"Train Loss: {train_loss:.4f}, Train Acc: {train_acc:.4f}, "
                f"Val Loss: {val_loss:.4f}, Val Acc: {val_acc:.4f}"
            )
        
        # 모델 저장
        self._save_model(history)
        
        return history
    
    def _prepare_dataloader(
        self,
        data: List[Tuple[str, int]],
        batch_size: int,
        shuffle: bool = True
    ):
        """데이터 로더 준비 (실제 구현 필요)"""
        # 여기서는 스텁 구현
        # 실제로는 torch.utils.data.DataLoader 사용
        return data
    
    def _train_epoch(self, train_loader, optimizer, criterion):
        """한 에폭 학습 (스텁)"""
        return 0.5, 0.75  # loss, accuracy
    
    def _validate_epoch(self, val_loader, criterion):
        """검증 (스텁)"""
        return 0.4, 0.80  # loss, accuracy
    
    def _save_model(self, history: Dict[str, Any]):
        """모델 저장"""
        save_path = f"sincnet_{self.model_type}_korean_elderly.pth"
        torch.save({
            'model_state_dict': self.model.state_dict(),
            'config': self.config,
            'history': history
        }, save_path)
        logger.info(f"모델 저장: {save_path}")


class DualSincNetAnalyzer:
    """우울 + 불면 통합 분석기"""
    
    def __init__(self, device: str = 'cpu'):
        """초기화"""
        self.depression_analyzer = SincNetAnalyzer('depression', device)
        self.insomnia_analyzer = SincNetAnalyzer('insomnia', device)
        
    def analyze(self, audio_path: str) -> Dict[str, float]:
        """
        우울과 불면 동시 분석
        
        Returns:
            {'depression': float, 'insomnia': float}
        """
        depression_result = self.depression_analyzer.analyze(audio_path)
        insomnia_result = self.insomnia_analyzer.analyze(audio_path)
        
        return {
            'depression': depression_result.get('probability', 0.5),
            'insomnia': insomnia_result.get('probability', 0.5),
            'depression_details': depression_result,
            'insomnia_details': insomnia_result
        }