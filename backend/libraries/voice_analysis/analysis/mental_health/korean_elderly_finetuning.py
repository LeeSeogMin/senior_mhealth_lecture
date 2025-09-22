"""
한국 노인 특화 Fine-tuning 모듈
한국 노인의 언어적, 문화적 특성을 반영한 모델 최적화
"""

import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Dict, Any, List, Optional, Tuple
import logging
from pathlib import Path
import json
from dataclasses import dataclass
from sklearn.preprocessing import StandardScaler
import librosa

logger = logging.getLogger(__name__)


@dataclass
class KoreanElderlyFeatures:
    """한국 노인 특화 음성 특징"""
    
    # 기본 음성 특징
    speech_rate: float  # 음절/초 (한국어 기준)
    pause_ratio: float  # 침묵 비율
    
    # 한국어 특화 특징
    honorific_usage: float  # 존댓말 사용 비율
    filler_words: float  # 간투사 사용 빈도 ("그", "저", "음")
    sentence_endings: Dict[str, float]  # 문장 종결 패턴
    
    # 감정 표현 특징
    emotion_suppression: float  # 감정 억제 정도
    indirect_expression: float  # 간접 표현 비율
    
    # 방언 특징
    dialect_features: Optional[Dict[str, float]] = None
    
    # 세대 특화 어휘
    generation_specific_words: Optional[List[str]] = None


class KoreanElderlyDataset(torch.utils.data.Dataset):
    """한국 노인 음성 데이터셋"""
    
    def __init__(
        self,
        data_path: str,
        transform=None,
        augment: bool = False
    ):
        """
        초기화
        
        Args:
            data_path: 데이터 경로
            transform: 전처리 변환
            augment: 데이터 증강 여부
        """
        self.data_path = Path(data_path)
        self.transform = transform
        self.augment = augment
        
        # 데이터 로드
        self.data = self._load_data()
        
        # 한국어 특화 전처리
        self.korean_preprocessor = KoreanSpeechPreprocessor()
        
    def _load_data(self) -> List[Dict[str, Any]]:
        """데이터 로드"""
        data = []
        
        # JSON 형식 데이터 로드
        if self.data_path.suffix == '.json':
            with open(self.data_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        
        # CSV 형식 데이터 로드
        elif self.data_path.suffix == '.csv':
            df = pd.read_csv(self.data_path)
            data = df.to_dict('records')
        
        return data
    
    def __len__(self) -> int:
        return len(self.data)
    
    def __getitem__(self, idx: int) -> Tuple[torch.Tensor, torch.Tensor]:
        """데이터 아이템 반환"""
        item = self.data[idx]
        
        # 오디오 로드
        audio, sr = librosa.load(item['audio_path'], sr=16000)
        
        # 한국어 특화 전처리
        audio = self.korean_preprocessor.process(audio, sr)
        
        # 데이터 증강
        if self.augment:
            audio = self._augment_audio(audio, sr)
        
        # 특징 추출
        features = self._extract_features(audio, sr)
        
        # 레이블
        labels = torch.tensor([
            item.get('depression', 0),
            item.get('insomnia', 0),
            item.get('cognitive', 0.5)
        ], dtype=torch.float32)
        
        if self.transform:
            features = self.transform(features)
        
        return features, labels
    
    def _augment_audio(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """데이터 증강"""
        # 속도 변경 (노인 말속도 특성 반영)
        if np.random.random() > 0.5:
            speed_factor = np.random.uniform(0.8, 1.2)
            audio = librosa.effects.time_stretch(audio, rate=speed_factor)
        
        # 노이즈 추가
        if np.random.random() > 0.5:
            noise = np.random.normal(0, 0.005, len(audio))
            audio = audio + noise
        
        return audio
    
    def _extract_features(self, audio: np.ndarray, sr: int) -> torch.Tensor:
        """특징 추출"""
        # MFCC
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        
        # 델타 특징
        delta_mfccs = librosa.feature.delta(mfccs)
        delta2_mfccs = librosa.feature.delta(mfccs, order=2)
        
        # 결합
        features = np.vstack([mfccs, delta_mfccs, delta2_mfccs])
        
        return torch.FloatTensor(features.T)


class KoreanSpeechPreprocessor:
    """한국어 음성 전처리기"""
    
    def __init__(self):
        """초기화"""
        # 한국어 특화 파라미터
        self.korean_speech_params = {
            'syllable_duration': 0.15,  # 평균 음절 길이 (초)
            'pause_threshold': 0.3,  # 휴지 임계값 (초)
            'energy_threshold': 0.02  # 에너지 임계값
        }
        
        # 한국 노인 특화 어휘
        self.elderly_vocabulary = {
            'fillers': ['그', '저', '음', '어', '아', '에'],
            'endings': ['네요', '지요', '구만', '구먼', '고만', '라니'],
            'dialect_markers': ['기라', '니더', '니껴', '그래가지고']
        }
    
    def process(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """한국어 특화 전처리"""
        # 침묵 제거 (한국어 기준)
        audio = self._remove_silence_korean(audio, sr)
        
        # 정규화
        audio = self._normalize(audio)
        
        # 노인 특화 처리
        audio = self._process_elderly_speech(audio, sr)
        
        return audio
    
    def _remove_silence_korean(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """한국어 특화 침묵 제거"""
        # 에너지 계산
        frame_length = int(0.025 * sr)
        hop_length = int(0.010 * sr)
        energy = librosa.feature.rms(y=audio, frame_length=frame_length, hop_length=hop_length)[0]
        
        # 한국어 특화 임계값
        threshold = np.mean(energy) * 0.2
        
        # 음성 구간 검출
        voice_frames = energy > threshold
        
        # 연속된 침묵 제거
        voiced_audio = []
        for i in range(len(voice_frames)):
            if voice_frames[i]:
                start = i * hop_length
                end = min(start + frame_length, len(audio))
                voiced_audio.extend(audio[start:end])
        
        return np.array(voiced_audio) if voiced_audio else audio
    
    def _normalize(self, audio: np.ndarray) -> np.ndarray:
        """정규화"""
        if np.max(np.abs(audio)) > 0:
            return audio / np.max(np.abs(audio))
        return audio
    
    def _process_elderly_speech(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """노인 음성 특화 처리"""
        # 떨림 보정 (노인 특성)
        audio = self._reduce_tremor(audio, sr)
        
        # 음성 명료도 향상
        audio = self._enhance_clarity(audio, sr)
        
        return audio
    
    def _reduce_tremor(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """떨림 감소"""
        # 저주파 필터링으로 떨림 감소
        nyquist = sr // 2
        low_cutoff = 50 / nyquist
        b, a = librosa.filters.mel(sr=sr, n_mels=1, fmin=50)
        
        return audio
    
    def _enhance_clarity(self, audio: np.ndarray, sr: int) -> np.ndarray:
        """명료도 향상"""
        # 스펙트럼 서브트랙션 (간단한 버전)
        D = librosa.stft(audio)
        magnitude = np.abs(D)
        phase = np.angle(D)
        
        # 노이즈 추정 (첫 10프레임)
        noise_profile = np.mean(magnitude[:, :10], axis=1, keepdims=True)
        
        # 노이즈 제거
        magnitude_clean = magnitude - noise_profile
        magnitude_clean = np.maximum(magnitude_clean, 0)
        
        # 재구성
        D_clean = magnitude_clean * np.exp(1j * phase)
        audio_clean = librosa.istft(D_clean)
        
        return audio_clean


class KoreanElderlyFineTuner:
    """한국 노인 특화 Fine-tuning 시스템"""
    
    def __init__(
        self,
        base_model,
        device: str = 'cpu'
    ):
        """
        초기화
        
        Args:
            base_model: 기본 모델
            device: 디바이스 ('cpu' or 'cuda')
        """
        self.device = torch.device(device)
        self.base_model = base_model.to(self.device)
        
        # 한국 노인 특화 레이어 추가
        self.korean_adapter = self._create_korean_adapter()
        
        # 특징 스케일러
        self.feature_scaler = StandardScaler()
        
        logger.info("한국 노인 특화 Fine-tuner 초기화 완료")
    
    def _create_korean_adapter(self) -> nn.Module:
        """한국 특화 어댑터 레이어 생성"""
        return nn.Sequential(
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 32)
        ).to(self.device)
    
    def fine_tune(
        self,
        train_dataset: KoreanElderlyDataset,
        val_dataset: KoreanElderlyDataset,
        epochs: int = 30,
        batch_size: int = 16,
        learning_rate: float = 0.0001
    ) -> Dict[str, Any]:
        """
        Fine-tuning 실행
        
        Args:
            train_dataset: 학습 데이터셋
            val_dataset: 검증 데이터셋
            epochs: 에폭 수
            batch_size: 배치 크기
            learning_rate: 학습률
            
        Returns:
            학습 결과
        """
        # 데이터 로더
        train_loader = torch.utils.data.DataLoader(
            train_dataset,
            batch_size=batch_size,
            shuffle=True,
            num_workers=2
        )
        
        val_loader = torch.utils.data.DataLoader(
            val_dataset,
            batch_size=batch_size,
            shuffle=False,
            num_workers=2
        )
        
        # 옵티마이저 (어댑터만 학습)
        optimizer = torch.optim.AdamW(
            self.korean_adapter.parameters(),
            lr=learning_rate,
            weight_decay=0.01
        )
        
        # 학습률 스케줄러
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(
            optimizer,
            T_max=epochs,
            eta_min=learning_rate * 0.01
        )
        
        # 손실 함수 (가중치 적용)
        class_weights = torch.tensor([1.5, 1.5, 1.0]).to(self.device)  # 우울, 불면 가중치 높임
        criterion = nn.BCEWithLogitsLoss(pos_weight=class_weights)
        
        history = {
            'train_loss': [],
            'val_loss': [],
            'train_metrics': [],
            'val_metrics': []
        }
        
        best_val_loss = float('inf')
        
        for epoch in range(epochs):
            # Training
            train_loss, train_metrics = self._train_epoch(
                train_loader, optimizer, criterion
            )
            
            # Validation
            val_loss, val_metrics = self._validate_epoch(
                val_loader, criterion
            )
            
            # 스케줄러 업데이트
            scheduler.step()
            
            # 기록
            history['train_loss'].append(train_loss)
            history['val_loss'].append(val_loss)
            history['train_metrics'].append(train_metrics)
            history['val_metrics'].append(val_metrics)
            
            # 최고 모델 저장
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                self._save_best_model(epoch, val_loss)
            
            logger.info(
                f"Epoch {epoch+1}/{epochs} - "
                f"Train Loss: {train_loss:.4f}, Val Loss: {val_loss:.4f}, "
                f"LR: {scheduler.get_last_lr()[0]:.6f}"
            )
        
        return history
    
    def _train_epoch(
        self,
        train_loader,
        optimizer,
        criterion
    ) -> Tuple[float, Dict[str, float]]:
        """한 에폭 학습"""
        self.base_model.train()
        self.korean_adapter.train()
        
        total_loss = 0
        all_predictions = []
        all_labels = []
        
        for batch_features, batch_labels in train_loader:
            batch_features = batch_features.to(self.device)
            batch_labels = batch_labels.to(self.device)
            
            optimizer.zero_grad()
            
            # Forward pass
            base_output = self.base_model(batch_features)
            adapted_output = self.korean_adapter(base_output)
            
            # Loss
            loss = criterion(adapted_output, batch_labels)
            
            # Backward pass
            loss.backward()
            optimizer.step()
            
            total_loss += loss.item()
            all_predictions.extend(torch.sigmoid(adapted_output).cpu().numpy())
            all_labels.extend(batch_labels.cpu().numpy())
        
        avg_loss = total_loss / len(train_loader)
        metrics = self._calculate_metrics(all_predictions, all_labels)
        
        return avg_loss, metrics
    
    def _validate_epoch(
        self,
        val_loader,
        criterion
    ) -> Tuple[float, Dict[str, float]]:
        """검증"""
        self.base_model.eval()
        self.korean_adapter.eval()
        
        total_loss = 0
        all_predictions = []
        all_labels = []
        
        with torch.no_grad():
            for batch_features, batch_labels in val_loader:
                batch_features = batch_features.to(self.device)
                batch_labels = batch_labels.to(self.device)
                
                # Forward pass
                base_output = self.base_model(batch_features)
                adapted_output = self.korean_adapter(base_output)
                
                # Loss
                loss = criterion(adapted_output, batch_labels)
                
                total_loss += loss.item()
                all_predictions.extend(torch.sigmoid(adapted_output).cpu().numpy())
                all_labels.extend(batch_labels.cpu().numpy())
        
        avg_loss = total_loss / len(val_loader)
        metrics = self._calculate_metrics(all_predictions, all_labels)
        
        return avg_loss, metrics
    
    def _calculate_metrics(
        self,
        predictions: List[np.ndarray],
        labels: List[np.ndarray]
    ) -> Dict[str, float]:
        """메트릭 계산"""
        predictions = np.array(predictions)
        labels = np.array(labels)
        
        # 지표별 정확도
        metrics = {}
        
        for i, name in enumerate(['depression', 'insomnia', 'cognitive']):
            pred_binary = (predictions[:, i] > 0.5).astype(int)
            label_binary = (labels[:, i] > 0.5).astype(int)
            
            correct = (pred_binary == label_binary).sum()
            total = len(pred_binary)
            
            metrics[f'{name}_accuracy'] = correct / total if total > 0 else 0
        
        return metrics
    
    def _save_best_model(self, epoch: int, val_loss: float):
        """최고 모델 저장"""
        save_path = f"korean_elderly_model_epoch{epoch}_loss{val_loss:.4f}.pth"
        
        torch.save({
            'epoch': epoch,
            'base_model_state': self.base_model.state_dict(),
            'adapter_state': self.korean_adapter.state_dict(),
            'val_loss': val_loss
        }, save_path)
        
        logger.info(f"최고 모델 저장: {save_path}")
    
    def predict(self, audio_path: str) -> Dict[str, float]:
        """
        예측
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            예측 결과
        """
        self.base_model.eval()
        self.korean_adapter.eval()
        
        # 오디오 로드 및 전처리
        preprocessor = KoreanSpeechPreprocessor()
        audio, sr = librosa.load(audio_path, sr=16000)
        audio = preprocessor.process(audio, sr)
        
        # 특징 추출
        mfccs = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=13)
        features = torch.FloatTensor(mfccs.T).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            base_output = self.base_model(features)
            adapted_output = self.korean_adapter(base_output)
            predictions = torch.sigmoid(adapted_output).cpu().numpy()[0]
        
        return {
            'depression': float(predictions[0]),
            'insomnia': float(predictions[1]),
            'cognitive': float(predictions[2])
        }


def create_korean_elderly_dataset(
    data_dir: str,
    output_path: str = "korean_elderly_dataset.json"
) -> str:
    """
    한국 노인 데이터셋 생성 (샘플)
    
    Args:
        data_dir: 오디오 파일 디렉토리
        output_path: 출력 경로
        
    Returns:
        데이터셋 파일 경로
    """
    dataset = []
    
    # 샘플 데이터 생성
    for i in range(100):
        sample = {
            'id': f'KE_{i:04d}',
            'audio_path': f'{data_dir}/audio_{i:04d}.wav',
            'age': np.random.randint(65, 90),
            'gender': np.random.choice(['남', '여']),
            'region': np.random.choice(['서울', '경기', '경상', '전라', '충청', '강원']),
            'depression': np.random.random(),
            'insomnia': np.random.random(),
            'cognitive': np.random.uniform(0.5, 1.0),
            'transcript': '샘플 전사 텍스트입니다.',
            'metadata': {
                'recording_date': '2024-01-01',
                'hospital': '샘플병원',
                'phq9_score': np.random.randint(0, 27),
                'mmse_score': np.random.randint(20, 30)
            }
        }
        dataset.append(sample)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)
    
    logger.info(f"한국 노인 데이터셋 생성: {output_path}")
    
    return output_path