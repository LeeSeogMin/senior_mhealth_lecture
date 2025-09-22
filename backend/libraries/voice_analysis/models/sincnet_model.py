# 제7강: AI 모델 이해와 로컬 테스트 - SincNet 모델 구현

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import math
from typing import List, Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class SincConv1d(nn.Module):
    """
    Sinc 함수 기반 1D Convolution Layer
    학습 가능한 대역통과 필터
    """
    
    def __init__(
        self,
        in_channels: int,
        out_channels: int,
        kernel_size: int,
        sample_rate: int = 16000,
        stride: int = 1,
        padding: int = 0,
        min_low_hz: float = 50,
        min_band_hz: float = 50
    ):
        """
        SincConv1d 레이어 초기화
        
        Args:
            in_channels: 입력 채널 수
            out_channels: 출력 채널 수 (필터 개수)
            kernel_size: 커널 크기
            sample_rate: 샘플링 레이트
            stride: 스트라이드
            padding: 패딩
            min_low_hz: 최소 저주파 컷오프
            min_band_hz: 최소 대역폭
        """
        super().__init__()
        
        self.out_channels = out_channels
        self.kernel_size = kernel_size
        self.sample_rate = sample_rate
        self.stride = stride
        self.padding = padding
        self.min_low_hz = min_low_hz
        self.min_band_hz = min_band_hz
        
        # 나이퀴스트 주파수
        self.nyquist = sample_rate / 2
        
        # 주파수 대역 파라미터 초기화
        # 멜 스케일로 초기화하여 더 나은 수렴
        mel_low = 2595 * np.log10(1 + min_low_hz / 700)
        mel_high = 2595 * np.log10(1 + self.nyquist / 700)
        
        mel_points = np.linspace(mel_low, mel_high, out_channels + 1)
        hz_points = 700 * (10**(mel_points / 2595) - 1)
        
        self.low_hz = nn.Parameter(torch.FloatTensor(hz_points[:-1]).view(out_channels, 1))
        self.band_hz = nn.Parameter(torch.FloatTensor(
            np.diff(hz_points)
        ).view(out_channels, 1))
        
        # Hamming window 생성
        n = torch.arange(kernel_size).float()
        self.register_buffer('window', 
            0.54 - 0.46 * torch.cos(2 * math.pi * n / kernel_size)
        )
        
        # 필터 정규화용 상수
        self.register_buffer('n_', 
            torch.arange(kernel_size).float().view(1, -1) - kernel_size // 2
        )
        
        logger.debug(f"SincConv1d 초기화: {out_channels}개 필터, 커널 크기 {kernel_size}")
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: 입력 신호 [batch, in_channels, time]
            
        Returns:
            filtered: 필터링된 신호 [batch, out_channels, time]
        """
        # 주파수 대역 제약 적용
        low = self.min_low_hz + torch.abs(self.low_hz)
        high = torch.clamp(
            low + self.min_band_hz + torch.abs(self.band_hz),
            min_low_hz, self.nyquist
        )
        
        # Sinc 필터 생성
        filters = self._create_sinc_filters(low, high)
        
        # Convolution 수행
        return F.conv1d(x, filters, stride=self.stride, padding=self.padding)
    
    def _create_sinc_filters(
        self,
        low: torch.Tensor,
        high: torch.Tensor
    ) -> torch.Tensor:
        """
        Sinc 필터 생성
        
        Args:
            low: 저주파 컷오프 [out_channels, 1]
            high: 고주파 컷오프 [out_channels, 1]
            
        Returns:
            filters: Sinc 필터 [out_channels, 1, kernel_size]
        """
        # 정규화된 주파수
        f_low = low / self.sample_rate  # [out_channels, 1]
        f_high = high / self.sample_rate  # [out_channels, 1]
        
        # 대역통과 필터 = 고주파 통과 - 저주파 통과
        band_pass = (
            2 * f_high * torch.sinc(2 * f_high * self.n_) -
            2 * f_low * torch.sinc(2 * f_low * self.n_)
        )
        
        # 윈도우 적용
        band_pass = band_pass * self.window
        
        # 정규화
        band_pass = band_pass / (torch.sum(band_pass, dim=1, keepdim=True) + 1e-8)
        
        return band_pass.unsqueeze(1)  # [out_channels, 1, kernel_size]
    
    def get_filter_parameters(self) -> Dict[str, torch.Tensor]:
        """현재 필터 파라미터 반환"""
        low = self.min_low_hz + torch.abs(self.low_hz)
        high = torch.clamp(
            low + self.min_band_hz + torch.abs(self.band_hz),
            self.min_low_hz, self.nyquist
        )
        
        return {
            'low_frequencies': low.detach(),
            'high_frequencies': high.detach(),
            'bandwidths': (high - low).detach()
        }

class SincNet(nn.Module):
    """
    SincNet: 음성 인식을 위한 신경망
    원시 음성에서 직접 학습하는 CNN 아키텍처
    """
    
    def __init__(
        self,
        input_dim: int = 16000,  # 1초 음성 @ 16kHz
        num_classes: int = 4,     # 정신건강 상태 클래스
        sinc_channels: List[int] = [80, 60, 60],
        sinc_kernel_sizes: List[int] = [251, 5, 5],
        pool_sizes: List[int] = [3, 3, 3],
        dropout: float = 0.2,
        use_batch_norm: bool = True
    ):
        """
        SincNet 모델 초기화
        
        Args:
            input_dim: 입력 차원 (샘플 수)
            num_classes: 출력 클래스 수
            sinc_channels: 각 SincNet 레이어의 채널 수
            sinc_kernel_sizes: 각 레이어의 커널 크기
            pool_sizes: 각 레이어의 풀링 크기
            dropout: 드롭아웃 비율
            use_batch_norm: 배치 정규화 사용 여부
        """
        super().__init__()
        
        self.input_dim = input_dim
        self.num_classes = num_classes
        self.use_batch_norm = use_batch_norm
        
        # SincNet layers
        self.sinc_layers = nn.ModuleList()
        self.pool_layers = nn.ModuleList()
        self.norm_layers = nn.ModuleList()
        
        in_channels = 1
        for i, (out_ch, kernel, pool) in enumerate(
            zip(sinc_channels, sinc_kernel_sizes, pool_sizes)
        ):
            # 첫 번째 레이어만 SincConv1d
            if i == 0:
                conv = SincConv1d(
                    in_channels, out_ch, kernel,
                    sample_rate=16000,
                    padding=kernel//2
                )
            else:
                conv = nn.Conv1d(
                    in_channels, out_ch, kernel,
                    padding=kernel//2
                )
            
            self.sinc_layers.append(conv)
            self.pool_layers.append(nn.MaxPool1d(pool))
            
            if use_batch_norm:
                self.norm_layers.append(nn.BatchNorm1d(out_ch))
            else:
                self.norm_layers.append(nn.Identity())
            
            in_channels = out_ch
            
        # 출력 차원 계산
        out_dim = self._calculate_output_dim(input_dim, pool_sizes)
        
        # 분류 헤드
        self.classifier = nn.Sequential(
            nn.Flatten(),
            nn.Linear(out_dim, 256),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_classes)
        )
        
        # 가중치 초기화
        self._initialize_weights()
        
        logger.info(f"SincNet 초기화 완료: {len(sinc_channels)}층, {num_classes}개 클래스")
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Forward pass
        
        Args:
            x: 입력 음성 [batch, time] or [batch, 1, time]
            
        Returns:
            logits: 분류 로짓 [batch, num_classes]
        """
        # 입력 차원 조정
        if x.dim() == 2:
            x = x.unsqueeze(1)  # [batch, 1, time]
            
        # SincNet feature extraction
        for i, (conv, pool, norm) in enumerate(
            zip(self.sinc_layers, self.pool_layers, self.norm_layers)
        ):
            x = conv(x)
            x = F.relu(norm(x))
            x = pool(x)
            
            logger.debug(f"Layer {i+1} 출력 shape: {x.shape}")
            
        # 분류
        logits = self.classifier(x)
        
        return logits
    
    def _calculate_output_dim(
        self, 
        input_dim: int, 
        pool_sizes: List[int]
    ) -> int:
        """출력 차원 계산"""
        dim = input_dim
        for pool_size in pool_sizes:
            dim = dim // pool_size
        return self.sinc_layers[-1].out_channels * dim
    
    def _initialize_weights(self):
        """가중치 초기화"""
        for module in self.modules():
            if isinstance(module, nn.Conv1d):
                nn.init.kaiming_normal_(module.weight, mode='fan_out', nonlinearity='relu')
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0)
            elif isinstance(module, nn.BatchNorm1d):
                nn.init.constant_(module.weight, 1)
                nn.init.constant_(module.bias, 0)
            elif isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, 0, 0.01)
                nn.init.constant_(module.bias, 0)
    
    def get_feature_maps(self, x: torch.Tensor) -> List[torch.Tensor]:
        """중간 특징 맵 반환 (시각화용)"""
        if x.dim() == 2:
            x = x.unsqueeze(1)
            
        feature_maps = []
        
        for conv, pool, norm in zip(self.sinc_layers, self.pool_layers, self.norm_layers):
            x = conv(x)
            x = F.relu(norm(x))
            feature_maps.append(x.clone())
            x = pool(x)
            
        return feature_maps
    
    def get_model_summary(self) -> Dict[str, Any]:
        """모델 요약 정보"""
        total_params = sum(p.numel() for p in self.parameters())
        trainable_params = sum(p.numel() for p in self.parameters() if p.requires_grad)
        
        return {
            'total_parameters': total_params,
            'trainable_parameters': trainable_params,
            'model_size_mb': total_params * 4 / 1024 / 1024,  # float32 기준
            'layers': len(self.sinc_layers),
            'input_dim': self.input_dim,
            'num_classes': self.num_classes
        }

class EmotionSincNet(nn.Module):
    """
    감정 분석 특화 SincNet 모델
    다중 작업 학습 지원
    """
    
    def __init__(
        self,
        input_dim: int = 16000,
        num_emotions: int = 7,
        use_attention: bool = True,
        use_multi_task: bool = False
    ):
        """
        감정 분석 SincNet 초기화
        
        Args:
            input_dim: 입력 차원
            num_emotions: 감정 클래스 수
            use_attention: Attention 메커니즘 사용 여부
            use_multi_task: 다중 작업 학습 여부
        """
        super().__init__()
        
        self.use_attention = use_attention
        self.use_multi_task = use_multi_task
        
        # SincNet 백본
        self.sinc_conv1 = SincConv1d(1, 80, 251, padding=125)
        self.sinc_conv2 = SincConv1d(80, 60, 5, padding=2)
        
        # 일반 CNN 레이어
        self.conv_block = nn.Sequential(
            nn.Conv1d(60, 128, 5, padding=2),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.MaxPool1d(2),
            
            nn.Conv1d(128, 256, 5, padding=2),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.MaxPool1d(2),
            
            nn.Conv1d(256, 512, 3, padding=1),
            nn.BatchNorm1d(512),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(100)  # 고정 길이로 변환
        )
        
        # LSTM for temporal modeling
        self.lstm = nn.LSTM(
            512, 256, 2, 
            batch_first=True, 
            bidirectional=True, 
            dropout=0.3
        )
        
        # Attention mechanism
        if use_attention:
            self.attention = nn.MultiheadAttention(
                embed_dim=512,  # bidirectional LSTM
                num_heads=8,
                dropout=0.1,
                batch_first=True
            )
        
        # 분류 헤드
        final_dim = 512 if use_attention else 512
        self.emotion_classifier = nn.Sequential(
            nn.Linear(final_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, num_emotions)
        )
        
        # 다중 작업 헤드 (선택적)
        if use_multi_task:
            # 우울증 정도 회귀
            self.depression_regressor = nn.Sequential(
                nn.Linear(final_dim, 128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, 1),
                nn.Sigmoid()  # 0-1 범위
            )
            
            # 불안 수준 회귀
            self.anxiety_regressor = nn.Sequential(
                nn.Linear(final_dim, 128),
                nn.ReLU(),
                nn.Dropout(0.3),
                nn.Linear(128, 1),
                nn.Sigmoid()
            )
        
        self._initialize_weights()
        logger.info(f"EmotionSincNet 초기화: {num_emotions}개 감정, attention={use_attention}")
        
    def forward(self, x: torch.Tensor) -> Dict[str, torch.Tensor]:
        """
        Forward pass
        
        Args:
            x: 입력 음성 [batch, time] or [batch, 1, time]
            
        Returns:
            outputs: 출력 딕셔너리
        """
        if x.dim() == 2:
            x = x.unsqueeze(1)
            
        # SincNet 특징 추출
        x = self.sinc_conv1(x)
        x = F.relu(x)
        x = F.max_pool1d(x, 3)
        
        x = self.sinc_conv2(x)
        x = F.relu(x)
        x = F.max_pool1d(x, 3)
        
        # CNN 특징 추출
        x = self.conv_block(x)  # [batch, 512, 100]
        
        # LSTM 처리
        x = x.transpose(1, 2)  # [batch, time, features]
        lstm_out, _ = self.lstm(x)  # [batch, time, 512]
        
        # Attention (선택적)
        if self.use_attention:
            attn_out, _ = self.attention(lstm_out, lstm_out, lstm_out)
            # Global average pooling
            features = torch.mean(attn_out, dim=1)  # [batch, 512]
        else:
            # Global average pooling
            features = torch.mean(lstm_out, dim=1)  # [batch, 512]
        
        # 감정 분류
        emotions = self.emotion_classifier(features)
        
        outputs = {
            'emotions': F.softmax(emotions, dim=1)
        }
        
        # 다중 작업 출력 (선택적)
        if self.use_multi_task:
            outputs.update({
                'depression_score': self.depression_regressor(features),
                'anxiety_score': self.anxiety_regressor(features)
            })
        
        return outputs
    
    def _initialize_weights(self):
        """가중치 초기화"""
        for module in self.modules():
            if isinstance(module, nn.Conv1d):
                nn.init.kaiming_normal_(module.weight, mode='fan_out', nonlinearity='relu')
                if module.bias is not None:
                    nn.init.constant_(module.bias, 0)
            elif isinstance(module, nn.BatchNorm1d):
                nn.init.constant_(module.weight, 1)
                nn.init.constant_(module.bias, 0)
            elif isinstance(module, nn.Linear):
                nn.init.normal_(module.weight, 0, 0.01)
                nn.init.constant_(module.bias, 0)
            elif isinstance(module, nn.LSTM):
                for name, param in module.named_parameters():
                    if 'weight_ih' in name:
                        nn.init.xavier_uniform_(param.data)
                    elif 'weight_hh' in name:
                        nn.init.orthogonal_(param.data)
                    elif 'bias' in name:
                        param.data.fill_(0)

class AdvancedSincNet(nn.Module):
    """
    고급 SincNet 모델
    Skip connections, Attention, Multi-scale 특징 포함
    """
    
    def __init__(
        self,
        input_dim: int = 16000,
        num_classes: int = 4,
        use_skip_connections: bool = True,
        use_multi_scale: bool = True
    ):
        super().__init__()
        
        self.use_skip_connections = use_skip_connections
        self.use_multi_scale = use_multi_scale
        
        # Multi-scale SincNet blocks
        self.sinc_block1 = self._make_sinc_block(1, 80, 251, 3)
        self.sinc_block2 = self._make_sinc_block(80, 60, 5, 3)
        self.sinc_block3 = self._make_sinc_block(60, 60, 5, 3)
        
        # Skip connection projections
        if use_skip_connections:
            self.skip_proj1 = nn.Conv1d(80, 60, 1)
            self.skip_proj2 = nn.Conv1d(60, 60, 1)
        
        # Multi-scale feature extraction
        if use_multi_scale:
            self.multi_scale_conv = nn.ModuleList([
                nn.Conv1d(60, 128, kernel_size=k, padding=k//2)
                for k in [3, 5, 7, 9]
            ])
            final_channels = 128 * 4  # multi-scale
        else:
            self.final_conv = nn.Conv1d(60, 256, 5, padding=2)
            final_channels = 256
        
        # Global feature aggregation
        self.global_pool = nn.AdaptiveAvgPool1d(1)
        
        # Classifier
        self.classifier = nn.Sequential(
            nn.Linear(final_channels, 512),
            nn.ReLU(),
            nn.Dropout(0.5),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, num_classes)
        )
        
    def _make_sinc_block(
        self, 
        in_ch: int, 
        out_ch: int, 
        kernel: int, 
        pool: int
    ) -> nn.Module:
        """SincNet 블록 생성"""
        if in_ch == 1:
            conv = SincConv1d(in_ch, out_ch, kernel, padding=kernel//2)
        else:
            conv = nn.Conv1d(in_ch, out_ch, kernel, padding=kernel//2)
            
        return nn.Sequential(
            conv,
            nn.BatchNorm1d(out_ch),
            nn.ReLU(),
            nn.MaxPool1d(pool)
        )
    
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass with skip connections"""
        if x.dim() == 2:
            x = x.unsqueeze(1)
            
        # Block 1
        x1 = self.sinc_block1(x)
        
        # Block 2 with skip connection
        x2 = self.sinc_block2(x1)
        if self.use_skip_connections:
            skip1 = F.adaptive_avg_pool1d(self.skip_proj1(x1), x2.size(-1))
            x2 = x2 + skip1
        
        # Block 3 with skip connection
        x3 = self.sinc_block3(x2)
        if self.use_skip_connections:
            skip2 = F.adaptive_avg_pool1d(self.skip_proj2(x2), x3.size(-1))
            x3 = x3 + skip2
        
        # Multi-scale feature extraction
        if self.use_multi_scale:
            multi_features = []
            for conv in self.multi_scale_conv:
                feat = conv(x3)
                feat = self.global_pool(feat).squeeze(-1)
                multi_features.append(feat)
            
            features = torch.cat(multi_features, dim=1)
        else:
            features = self.final_conv(x3)
            features = self.global_pool(features).squeeze(-1)
        
        # Classification
        logits = self.classifier(features)
        
        return logits

def create_model(
    model_type: str = 'basic',
    **kwargs
) -> nn.Module:
    """
    모델 팩토리 함수
    
    Args:
        model_type: 'basic', 'emotion', 'advanced'
        **kwargs: 모델별 추가 인자
        
    Returns:
        model: 생성된 모델
    """
    if model_type == 'basic':
        return SincNet(**kwargs)
    elif model_type == 'emotion':
        return EmotionSincNet(**kwargs)
    elif model_type == 'advanced':
        return AdvancedSincNet(**kwargs)
    else:
        raise ValueError(f"지원하지 않는 모델 타입: {model_type}")

# 예제 사용법
if __name__ == "__main__":
    # 기본 SincNet 테스트
    model = SincNet()
    dummy_input = torch.randn(4, 16000)  # 4개 배치, 1초 오디오
    
    output = model(dummy_input)
    print(f"출력 shape: {output.shape}")
    print(f"모델 요약: {model.get_model_summary()}")
    
    # 감정 분석 모델 테스트
    emotion_model = EmotionSincNet(use_attention=True, use_multi_task=True)
    emotion_output = emotion_model(dummy_input)
    
    print(f"감정 예측: {emotion_output['emotions'].shape}")
    if 'depression_score' in emotion_output:
        print(f"우울증 점수: {emotion_output['depression_score'].shape}")
        print(f"불안 점수: {emotion_output['anxiety_score'].shape}")