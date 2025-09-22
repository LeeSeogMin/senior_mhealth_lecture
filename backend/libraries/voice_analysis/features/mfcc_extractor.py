# 제7강: AI 모델 이해와 로컬 테스트 - MFCC 특징 추출기

import torch
import torchaudio
import torchaudio.transforms as T
import numpy as np
from typing import Tuple, Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)

class MFCCExtractor:
    """
    MFCC 특징 추출기
    음성 신호에서 Mel-frequency cepstral coefficients 추출
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        n_mfcc: int = 13,
        n_fft: int = 400,
        hop_length: int = 160,
        n_mels: int = 23,
        f_min: float = 0.0,
        f_max: Optional[float] = None
    ):
        """
        MFCC 추출기 초기화
        
        Args:
            sample_rate: 샘플링 레이트 (Hz)
            n_mfcc: MFCC 계수 개수
            n_fft: FFT 크기
            hop_length: 프레임 간 간격
            n_mels: Mel 필터뱅크 개수
            f_min: 최소 주파수
            f_max: 최대 주파수 (None이면 sample_rate/2)
        """
        self.sample_rate = sample_rate
        self.n_mfcc = n_mfcc
        self.n_fft = n_fft
        self.hop_length = hop_length
        
        # MFCC 변환 초기화
        self.mfcc_transform = T.MFCC(
            sample_rate=sample_rate,
            n_mfcc=n_mfcc,
            melkwargs={
                'n_fft': n_fft,
                'hop_length': hop_length,
                'n_mels': n_mels,
                'f_min': f_min,
                'f_max': f_max or sample_rate / 2,
                'center': True,
                'pad_mode': 'reflect',
                'power': 2.0,
                'norm': 'slaney',
                'mel_scale': 'htk'
            }
        )
        
        # 델타 특징 추출기
        self.delta_transform = T.ComputeDeltas()
        
        logger.info(f"MFCC 추출기 초기화 완료: {n_mfcc}개 계수, {sample_rate}Hz")
        
    def extract(
        self,
        waveform: torch.Tensor,
        compute_deltas: bool = True
    ) -> torch.Tensor:
        """
        음성에서 MFCC 특징 추출
        
        Args:
            waveform: 입력 음성 신호 [batch, time] or [time]
            compute_deltas: 델타, 델타-델타 특징 포함 여부
            
        Returns:
            mfcc_features: MFCC 특징 텐서 [batch, features, frames]
        """
        try:
            # 배치 차원 확인
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
                
            # 입력 검증
            if waveform.shape[-1] < self.n_fft:
                raise ValueError(f"오디오가 너무 짧습니다. 최소 {self.n_fft}개 샘플 필요")
                
            # MFCC 추출
            mfcc = self.mfcc_transform(waveform)
            
            if compute_deltas:
                # 1차 미분 (델타)
                delta = self.delta_transform(mfcc)
                # 2차 미분 (델타-델타)
                delta_delta = self.delta_transform(delta)
                # 결합 [MFCC, Delta, Delta-Delta]
                mfcc = torch.cat([mfcc, delta, delta_delta], dim=1)
                
            logger.debug(f"MFCC 추출 완료: {mfcc.shape}")
            return mfcc
            
        except Exception as e:
            logger.error(f"MFCC 추출 실패: {str(e)}")
            raise
    
    def normalize(
        self,
        features: torch.Tensor,
        method: str = 'standardize'
    ) -> torch.Tensor:
        """
        특징 정규화
        
        Args:
            features: 입력 특징 [batch, features, frames]
            method: 'standardize', 'minmax', 'robust'
            
        Returns:
            normalized_features: 정규화된 특징
        """
        if method == 'standardize':
            # Z-score 정규화
            mean = features.mean(dim=-1, keepdim=True)
            std = features.std(dim=-1, keepdim=True)
            return (features - mean) / (std + 1e-8)
            
        elif method == 'minmax':
            # Min-Max 정규화
            min_val = features.min(dim=-1, keepdim=True)[0]
            max_val = features.max(dim=-1, keepdim=True)[0]
            return (features - min_val) / (max_val - min_val + 1e-8)
            
        elif method == 'robust':
            # Robust 정규화 (중간값 기반)
            median = features.median(dim=-1, keepdim=True)[0]
            mad = torch.median(torch.abs(features - median), dim=-1, keepdim=True)[0]
            return (features - median) / (mad + 1e-8)
            
        else:
            logger.warning(f"알 수 없는 정규화 방법: {method}")
            return features
    
    def extract_statistics(
        self,
        features: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """
        MFCC 통계 특징 추출
        
        Args:
            features: MFCC 특징 [batch, features, frames]
            
        Returns:
            statistics: 통계 특징 딕셔너리
        """
        stats = {
            'mean': torch.mean(features, dim=-1),
            'std': torch.std(features, dim=-1),
            'median': torch.median(features, dim=-1)[0],
            'q25': torch.quantile(features, 0.25, dim=-1),
            'q75': torch.quantile(features, 0.75, dim=-1),
            'skewness': self._compute_skewness(features),
            'kurtosis': self._compute_kurtosis(features)
        }
        
        return stats
    
    def _compute_skewness(self, features: torch.Tensor) -> torch.Tensor:
        """왜도 계산"""
        mean = torch.mean(features, dim=-1, keepdim=True)
        std = torch.std(features, dim=-1, keepdim=True)
        centered = (features - mean) / (std + 1e-8)
        skewness = torch.mean(centered ** 3, dim=-1)
        return skewness
    
    def _compute_kurtosis(self, features: torch.Tensor) -> torch.Tensor:
        """첨도 계산"""
        mean = torch.mean(features, dim=-1, keepdim=True)
        std = torch.std(features, dim=-1, keepdim=True)
        centered = (features - mean) / (std + 1e-8)
        kurtosis = torch.mean(centered ** 4, dim=-1) - 3
        return kurtosis
    
    def visualize_features(
        self,
        features: torch.Tensor,
        save_path: Optional[str] = None
    ) -> None:
        """
        MFCC 특징 시각화
        
        Args:
            features: MFCC 특징 [1, features, frames]
            save_path: 저장 경로 (선택적)
        """
        try:
            import matplotlib.pyplot as plt
            
            features_np = features[0].numpy()  # 첫 번째 배치
            
            plt.figure(figsize=(12, 8))
            
            # MFCC만 표시 (델타 제외)
            mfcc_only = features_np[:self.n_mfcc, :]
            
            plt.imshow(mfcc_only, aspect='auto', origin='lower', 
                      cmap='viridis', interpolation='nearest')
            plt.colorbar(label='MFCC Coefficient Value')
            plt.xlabel('Time Frames')
            plt.ylabel('MFCC Coefficients')
            plt.title('MFCC Features Visualization')
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"MFCC 시각화 저장: {save_path}")
            else:
                plt.show()
                
        except ImportError:
            logger.warning("matplotlib을 찾을 수 없습니다. 시각화를 건너뜁니다.")
        except Exception as e:
            logger.error(f"시각화 실패: {str(e)}")
            
    def get_config(self) -> Dict[str, Any]:
        """현재 설정 반환"""
        return {
            'sample_rate': self.sample_rate,
            'n_mfcc': self.n_mfcc,
            'n_fft': self.n_fft,
            'hop_length': self.hop_length,
            'n_mels': self.mfcc_transform.mel_kwargs['n_mels'],
            'f_min': self.mfcc_transform.mel_kwargs['f_min'],
            'f_max': self.mfcc_transform.mel_kwargs['f_max']
        }