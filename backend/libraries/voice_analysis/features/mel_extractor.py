# 제7강: AI 모델 이해와 로컬 테스트 - Mel-Spectrogram 추출기

import torch
import torchaudio
import torchaudio.transforms as T
import numpy as np
from typing import Optional, Dict, Any, Tuple
import logging

logger = logging.getLogger(__name__)

class MelSpectrogramExtractor:
    """
    Mel-Spectrogram 특징 추출기
    시간-주파수 영역에서 음성 특징 추출
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        n_fft: int = 1024,
        hop_length: int = 512,
        n_mels: int = 128,
        f_min: float = 0.0,
        f_max: Optional[float] = None,
        power: float = 2.0
    ):
        """
        Mel-Spectrogram 추출기 초기화
        
        Args:
            sample_rate: 샘플링 레이트
            n_fft: FFT 크기
            hop_length: 홉 길이
            n_mels: Mel 필터 개수
            f_min: 최소 주파수
            f_max: 최대 주파수
            power: 파워 스펙트럼 지수 (1: magnitude, 2: power)
        """
        self.sample_rate = sample_rate
        self.n_fft = n_fft
        self.hop_length = hop_length
        self.n_mels = n_mels
        self.power = power
        
        # Mel-spectrogram 변환
        self.mel_transform = T.MelSpectrogram(
            sample_rate=sample_rate,
            n_fft=n_fft,
            hop_length=hop_length,
            n_mels=n_mels,
            f_min=f_min,
            f_max=f_max or sample_rate / 2,
            power=power,
            center=True,
            pad_mode='reflect',
            norm='slaney',
            mel_scale='htk'
        )
        
        # 데시벨 변환
        self.db_transform = T.AmplitudeToDB(stype='power', top_db=80)
        
        # SpecAugment 변환
        self.time_mask = T.TimeMasking(time_mask_param=30)
        self.freq_mask = T.FrequencyMasking(freq_mask_param=20)
        
        logger.info(f"Mel-Spectrogram 추출기 초기화: {n_mels}개 필터, {sample_rate}Hz")
        
    def extract(
        self,
        waveform: torch.Tensor,
        to_db: bool = True
    ) -> torch.Tensor:
        """
        Mel-spectrogram 추출
        
        Args:
            waveform: 입력 음성 [batch, time] or [time]
            to_db: 데시벨 스케일 변환 여부
        
        Returns:
            mel_spec: Mel-spectrogram [batch, n_mels, frames]
        """
        try:
            if waveform.dim() == 1:
                waveform = waveform.unsqueeze(0)
                
            # 입력 검증
            if waveform.shape[-1] < self.n_fft:
                raise ValueError(f"오디오가 너무 짧습니다. 최소 {self.n_fft}개 샘플 필요")
                
            # Mel-spectrogram 계산
            mel_spec = self.mel_transform(waveform)
            
            # 데시벨 변환
            if to_db:
                mel_spec = self.db_transform(mel_spec)
                
            logger.debug(f"Mel-spectrogram 추출 완료: {mel_spec.shape}")
            return mel_spec
            
        except Exception as e:
            logger.error(f"Mel-spectrogram 추출 실패: {str(e)}")
            raise
    
    def augment(
        self,
        mel_spec: torch.Tensor,
        time_mask_param: int = 30,
        freq_mask_param: int = 20,
        apply_prob: float = 0.5
    ) -> torch.Tensor:
        """
        SpecAugment 적용
        
        Args:
            mel_spec: 입력 Mel-spectrogram [batch, n_mels, frames]
            time_mask_param: 시간 축 마스킹 최대 크기
            freq_mask_param: 주파수 축 마스킹 최대 크기
            apply_prob: 증강 적용 확률
            
        Returns:
            augmented_mel: 증강된 Mel-spectrogram
        """
        if torch.rand(1).item() > apply_prob:
            return mel_spec
            
        batch_size, n_mels, n_frames = mel_spec.shape
        augmented_mel = mel_spec.clone()
        
        # Time masking
        if time_mask_param > 0 and torch.rand(1).item() < 0.5:
            time_mask = T.TimeMasking(time_mask_param)
            augmented_mel = time_mask(augmented_mel)
            
        # Frequency masking
        if freq_mask_param > 0 and torch.rand(1).item() < 0.5:
            freq_mask = T.FrequencyMasking(freq_mask_param)
            augmented_mel = freq_mask(augmented_mel)
            
        return augmented_mel
    
    def extract_temporal_features(
        self,
        mel_spec: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """
        시간적 특징 추출
        
        Args:
            mel_spec: Mel-spectrogram [batch, n_mels, frames]
            
        Returns:
            temporal_features: 시간적 특징 딕셔너리
        """
        # 시간 축 통계
        features = {
            'spectral_centroid': torch.mean(mel_spec, dim=1),  # 스펙트럴 중심
            'spectral_rolloff': torch.quantile(mel_spec, 0.85, dim=1),  # 롤오프
            'spectral_flux': self._compute_spectral_flux(mel_spec),
            'zero_crossing_rate': self._compute_zcr(mel_spec),
            'energy': torch.sum(mel_spec, dim=1),  # 에너지
            'entropy': self._compute_spectral_entropy(mel_spec)
        }
        
        return features
    
    def _compute_spectral_flux(self, mel_spec: torch.Tensor) -> torch.Tensor:
        """스펙트럴 플럭스 계산"""
        diff = torch.diff(mel_spec, dim=-1)
        positive_diff = torch.where(diff > 0, diff, torch.zeros_like(diff))
        flux = torch.sum(positive_diff, dim=1)
        return flux
    
    def _compute_zcr(self, mel_spec: torch.Tensor) -> torch.Tensor:
        """제로 크로싱 레이트 근사"""
        # Mel-spectrogram에서 ZCR 근사 계산
        signs = torch.sign(mel_spec - mel_spec.mean(dim=-1, keepdim=True))
        zcr = torch.mean(torch.abs(torch.diff(signs, dim=-1)), dim=1)
        return zcr
    
    def _compute_spectral_entropy(self, mel_spec: torch.Tensor) -> torch.Tensor:
        """스펙트럴 엔트로피 계산"""
        # 확률 분포로 정규화
        probs = torch.softmax(mel_spec, dim=1)
        entropy = -torch.sum(probs * torch.log(probs + 1e-8), dim=1)
        return entropy
    
    def extract_and_aggregate(
        self,
        waveform: torch.Tensor,
        aggregation: str = 'mean'
    ) -> torch.Tensor:
        """
        특징 추출 및 집계
        
        Args:
            waveform: 입력 음성
            aggregation: 집계 방법 ('mean', 'max', 'std', 'concatenate')
            
        Returns:
            aggregated_features: 집계된 특징
        """
        mel_spec = self.extract(waveform)
        
        if aggregation == 'mean':
            return torch.mean(mel_spec, dim=-1)
        elif aggregation == 'max':
            return torch.max(mel_spec, dim=-1)[0]
        elif aggregation == 'std':
            return torch.std(mel_spec, dim=-1)
        elif aggregation == 'concatenate':
            # 평균, 최대, 표준편차 연결
            mean_feat = torch.mean(mel_spec, dim=-1)
            max_feat = torch.max(mel_spec, dim=-1)[0]
            std_feat = torch.std(mel_spec, dim=-1)
            return torch.cat([mean_feat, max_feat, std_feat], dim=-1)
        else:
            raise ValueError(f"지원하지 않는 집계 방법: {aggregation}")
    
    def visualize_spectrogram(
        self,
        mel_spec: torch.Tensor,
        title: str = "Mel-Spectrogram",
        save_path: Optional[str] = None
    ) -> None:
        """
        Mel-spectrogram 시각화
        
        Args:
            mel_spec: Mel-spectrogram [1, n_mels, frames]
            title: 그래프 제목
            save_path: 저장 경로 (선택적)
        """
        try:
            import matplotlib.pyplot as plt
            
            mel_np = mel_spec[0].numpy()  # 첫 번째 배치
            
            plt.figure(figsize=(12, 6))
            
            # Time axis (seconds)
            time_axis = np.arange(mel_np.shape[1]) * self.hop_length / self.sample_rate
            
            # Frequency axis (mel scale)
            mel_freqs = np.linspace(0, self.sample_rate/2, self.n_mels)
            
            # Spectrogram 플롯
            im = plt.imshow(
                mel_np,
                aspect='auto',
                origin='lower',
                cmap='viridis',
                extent=[0, time_axis[-1], 0, len(mel_freqs)],
                interpolation='nearest'
            )
            
            plt.colorbar(im, label='Magnitude (dB)')
            plt.xlabel('Time (seconds)')
            plt.ylabel('Mel Frequency Bins')
            plt.title(title)
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"Mel-spectrogram 시각화 저장: {save_path}")
            else:
                plt.show()
                
        except ImportError:
            logger.warning("matplotlib을 찾을 수 없습니다. 시각화를 건너뜁니다.")
        except Exception as e:
            logger.error(f"시각화 실패: {str(e)}")
    
    def compare_before_after_augment(
        self,
        mel_spec: torch.Tensor,
        augmented_mel: torch.Tensor,
        save_path: Optional[str] = None
    ) -> None:
        """원본과 증강된 spectrogram 비교"""
        try:
            import matplotlib.pyplot as plt
            
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
            
            # 원본
            ax1.imshow(mel_spec[0].numpy(), aspect='auto', origin='lower', 
                      cmap='viridis', interpolation='nearest')
            ax1.set_title('Original Mel-Spectrogram')
            ax1.set_xlabel('Time Frames')
            ax1.set_ylabel('Mel Frequency Bins')
            
            # 증강된 버전
            im = ax2.imshow(augmented_mel[0].numpy(), aspect='auto', origin='lower', 
                           cmap='viridis', interpolation='nearest')
            ax2.set_title('Augmented Mel-Spectrogram')
            ax2.set_xlabel('Time Frames')
            ax2.set_ylabel('Mel Frequency Bins')
            
            plt.colorbar(im, ax=[ax1, ax2], label='Magnitude (dB)')
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"비교 시각화 저장: {save_path}")
            else:
                plt.show()
                
        except Exception as e:
            logger.error(f"비교 시각화 실패: {str(e)}")
    
    def get_config(self) -> Dict[str, Any]:
        """현재 설정 반환"""
        return {
            'sample_rate': self.sample_rate,
            'n_fft': self.n_fft,
            'hop_length': self.hop_length,
            'n_mels': self.n_mels,
            'power': self.power,
            'f_min': self.mel_transform.mel_kwargs['f_min'],
            'f_max': self.mel_transform.mel_kwargs['f_max']
        }