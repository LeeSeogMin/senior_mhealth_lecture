# 제7강: AI 모델 이해와 로컬 테스트 - 추론 엔진

import torch
import torch.nn as nn
import torch.nn.functional as F
import soundfile as sf
import torchaudio
import torchaudio.transforms as T
import numpy as np
from pathlib import Path
from typing import Dict, List, Union, Optional, Any
import time
import logging
import json
from ..features.mfcc_extractor import MFCCExtractor
from ..features.mel_extractor import MelSpectrogramExtractor
from ..models.sincnet_model import SincNet, EmotionSincNet

logger = logging.getLogger(__name__)

class InferenceEngine:
    """
    모델 추론 엔진
    음성 파일 또는 실시간 음성 스트림 처리
    """
    
    def __init__(
        self,
        model_path: str,
        device: str = 'cuda' if torch.cuda.is_available() else 'cpu',
        model_type: str = 'basic',
        use_optimization: bool = True
    ):
        """
        추론 엔진 초기화
        
        Args:
            model_path: 학습된 모델 경로
            device: 추론 디바이스 (cuda/cpu)
            model_type: 모델 타입 ('basic', 'emotion')
            use_optimization: 최적화 적용 여부
        """
        self.device = torch.device(device)
        self.model_type = model_type
        self.use_optimization = use_optimization
        
        # 모델 로드
        self.model = self._load_model(model_path)
        self.model.to(self.device)
        self.model.eval()
        
        # 특징 추출기
        self.mfcc_extractor = MFCCExtractor()
        self.mel_extractor = MelSpectrogramExtractor()
        
        # 클래스 매핑
        if model_type == 'basic':
            self.class_labels = {
                0: 'normal',
                1: 'mild_depression',
                2: 'moderate_depression',
                3: 'severe_depression'
            }
        elif model_type == 'emotion':
            self.class_labels = {
                0: 'neutral',
                1: 'happy', 
                2: 'sad',
                3: 'angry',
                4: 'fearful',
                5: 'disgusted',
                6: 'surprised'
            }
        
        # 성능 추적
        self.inference_stats = {
            'total_inferences': 0,
            'avg_inference_time': 0,
            'cache_hits': 0,
            'errors': 0
        }
        
        # 캐시 (간단한 LRU)
        self.cache = {}
        self.cache_size = 100
        
        logger.info(f"추론 엔진 초기화 완료: {device}, {model_type} 모델")
        
    def _load_model(self, model_path: str) -> nn.Module:
        """모델 로드 및 초기화"""
        try:
            checkpoint = torch.load(model_path, map_location='cpu')
            
            # 모델 구조 재생성
            if self.model_type == 'basic':
                model = SincNet(
                    num_classes=checkpoint.get('num_classes', 4)
                )
            elif self.model_type == 'emotion':
                model = EmotionSincNet(
                    num_emotions=checkpoint.get('num_emotions', 7),
                    use_attention=checkpoint.get('use_attention', True),
                    use_multi_task=checkpoint.get('use_multi_task', False)
                )
            else:
                raise ValueError(f"지원하지 않는 모델 타입: {self.model_type}")
            
            # 가중치 로드
            if 'model_state_dict' in checkpoint:
                model.load_state_dict(checkpoint['model_state_dict'])
            else:
                model.load_state_dict(checkpoint)
            
            # TorchScript 최적화 (선택적)
            if self.use_optimization and checkpoint.get('use_torchscript', False):
                dummy_input = torch.randn(1, 16000)
                model = torch.jit.trace(model, dummy_input)
                logger.info("TorchScript 최적화 적용됨")
            
            return model
            
        except Exception as e:
            logger.error(f"모델 로드 실패: {str(e)}")
            raise
    
    @torch.no_grad()
    def predict(
        self,
        audio_path: Union[str, Path],
        feature_type: str = 'raw',
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        음성 파일 예측
        
        Args:
            audio_path: 음성 파일 경로
            feature_type: 'raw', 'mfcc', or 'mel'
            use_cache: 캐시 사용 여부
            
        Returns:
            predictions: 예측 결과 딕셔너리
        """
        start_time = time.time()
        
        try:
            # 캐시 확인
            cache_key = f"{audio_path}_{feature_type}"
            if use_cache and cache_key in self.cache:
                logger.debug(f"캐시 히트: {cache_key}")
                self.inference_stats['cache_hits'] += 1
                return self.cache[cache_key]
            
            # 오디오 로드
            waveform, sr = sf.read(audio_path)
            waveform = torch.FloatTensor(waveform)
            
            # 리샘플링 (필요시)
            if sr != 16000:
                resampler = T.Resample(sr, 16000)
                waveform = resampler(waveform)
                logger.debug(f"리샘플링: {sr}Hz -> 16000Hz")
            
            # 길이 조정 (1초로 패딩/자르기)
            target_length = 16000
            if len(waveform) < target_length:
                # 패딩
                waveform = F.pad(waveform, (0, target_length - len(waveform)))
            elif len(waveform) > target_length:
                # 중앙에서 자르기
                start = (len(waveform) - target_length) // 2
                waveform = waveform[start:start + target_length]
            
            # 특징 추출
            features = self._extract_features(waveform, feature_type)
            
            # 디바이스 이동
            features = features.to(self.device)
            
            # 추론
            if self.model_type == 'emotion':
                outputs = self.model(features)
                if isinstance(outputs, dict):
                    # 다중 작업 모델
                    emotions = outputs['emotions']
                    result = self._format_emotion_result(outputs, waveform)
                else:
                    # 단일 작업 모델
                    result = self._format_basic_result(outputs, waveform)
            else:
                logits = self.model(features)
                result = self._format_basic_result(logits, waveform)
            
            # 추론 시간 기록
            inference_time = time.time() - start_time
            result['inference_time'] = inference_time
            result['feature_type'] = feature_type
            
            # 캐시 저장
            if use_cache:
                self._update_cache(cache_key, result)
            
            # 통계 업데이트
            self._update_stats(inference_time)
            
            return result
            
        except Exception as e:
            logger.error(f"예측 실패 - {audio_path}: {str(e)}")
            self.inference_stats['errors'] += 1
            raise
    
    def _extract_features(
        self, 
        waveform: torch.Tensor, 
        feature_type: str
    ) -> torch.Tensor:
        """특징 추출"""
        if feature_type == 'mfcc':
            features = self.mfcc_extractor.extract(waveform)
            # MFCC는 2D CNN으로 처리하기 위해 차원 조정
            features = features.unsqueeze(1)  # [batch, 1, mfcc, frames]
        elif feature_type == 'mel':
            features = self.mel_extractor.extract(waveform)
            features = features.unsqueeze(1)  # [batch, 1, mels, frames]
        else:  # raw
            features = waveform.unsqueeze(0)  # [1, time]
        
        return features
    
    def _format_basic_result(
        self, 
        logits: torch.Tensor, 
        waveform: torch.Tensor
    ) -> Dict[str, Any]:
        """기본 모델 결과 포맷팅"""
        probs = F.softmax(logits, dim=-1)
        pred_class = torch.argmax(probs, dim=-1).item()
        confidence = probs.max().item()
        
        return {
            'prediction': self.class_labels[pred_class],
            'confidence': confidence,
            'probabilities': {
                self.class_labels[i]: p.item()
                for i, p in enumerate(probs[0])
            },
            'audio_duration': len(waveform) / 16000,
            'raw_logits': logits[0].cpu().numpy().tolist()
        }
    
    def _format_emotion_result(
        self, 
        outputs: Dict[str, torch.Tensor], 
        waveform: torch.Tensor
    ) -> Dict[str, Any]:
        """감정 모델 결과 포맷팅"""
        emotions = outputs['emotions']
        pred_emotion = torch.argmax(emotions, dim=-1).item()
        confidence = emotions.max().item()
        
        result = {
            'emotion_prediction': self.class_labels[pred_emotion],
            'emotion_confidence': confidence,
            'emotion_probabilities': {
                self.class_labels[i]: p.item()
                for i, p in enumerate(emotions[0])
            },
            'audio_duration': len(waveform) / 16000
        }
        
        # 다중 작업 결과 추가
        if 'depression_score' in outputs:
            result['depression_score'] = outputs['depression_score'][0].item()
        if 'anxiety_score' in outputs:
            result['anxiety_score'] = outputs['anxiety_score'][0].item()
        
        return result
    
    def predict_batch(
        self,
        audio_paths: List[Union[str, Path]],
        batch_size: int = 32,
        feature_type: str = 'raw'
    ) -> List[Dict[str, Any]]:
        """
        배치 예측
        
        Args:
            audio_paths: 음성 파일 경로 리스트
            batch_size: 배치 크기
            feature_type: 특징 타입
            
        Returns:
            results: 예측 결과 리스트
        """
        results = []
        
        for i in range(0, len(audio_paths), batch_size):
            batch_paths = audio_paths[i:i+batch_size]
            
            # 배치 데이터 준비
            batch_waveforms = []
            batch_info = []
            
            for path in batch_paths:
                try:
                    waveform, sr = sf.read(path)
                    waveform = torch.FloatTensor(waveform)
                    
                    if sr != 16000:
                        resampler = T.Resample(sr, 16000)
                        waveform = resampler(waveform)
                    
                    # 길이 정규화
                    target_length = 16000
                    if len(waveform) < target_length:
                        waveform = F.pad(waveform, (0, target_length - len(waveform)))
                    elif len(waveform) > target_length:
                        start = (len(waveform) - target_length) // 2
                        waveform = waveform[start:start + target_length]
                    
                    batch_waveforms.append(waveform)
                    batch_info.append({'path': path, 'original_sr': sr})
                    
                except Exception as e:
                    logger.error(f"배치 처리 실패 - {path}: {str(e)}")
                    results.append({
                        'error': str(e),
                        'path': str(path)
                    })
            
            if batch_waveforms:
                # 배치 텐서 생성
                batch_tensor = torch.stack(batch_waveforms)
                
                # 배치 추론
                batch_results = self._batch_inference(
                    batch_tensor, batch_info, feature_type
                )
                results.extend(batch_results)
        
        return results
    
    @torch.no_grad()
    def _batch_inference(
        self,
        batch_waveforms: torch.Tensor,
        batch_info: List[Dict],
        feature_type: str
    ) -> List[Dict[str, Any]]:
        """배치 추론 실행"""
        start_time = time.time()
        
        # 특징 추출
        if feature_type == 'mfcc':
            features = self.mfcc_extractor.extract(batch_waveforms)
            features = features.unsqueeze(2)  # [batch, mfcc, 1, frames]
        elif feature_type == 'mel':
            features = self.mel_extractor.extract(batch_waveforms)
            features = features.unsqueeze(2)  # [batch, mels, 1, frames]
        else:  # raw
            features = batch_waveforms
        
        features = features.to(self.device)
        
        # 모델 추론
        if self.model_type == 'emotion':
            outputs = self.model(features)
            if isinstance(outputs, dict):
                emotions = outputs['emotions']
            else:
                emotions = outputs
        else:
            logits = self.model(features)
            emotions = F.softmax(logits, dim=-1)
        
        # 결과 포맷팅
        inference_time = time.time() - start_time
        results = []
        
        for i, info in enumerate(batch_info):
            if self.model_type == 'emotion' and isinstance(outputs, dict):
                result = {
                    'prediction': self.class_labels[torch.argmax(emotions[i]).item()],
                    'confidence': emotions[i].max().item(),
                    'probabilities': {
                        self.class_labels[j]: emotions[i][j].item()
                        for j in range(len(self.class_labels))
                    },
                    'inference_time': inference_time / len(batch_info),
                    'audio_duration': 1.0,  # 1초로 정규화됨
                    'feature_type': feature_type
                }
                
                # 추가 점수
                if 'depression_score' in outputs:
                    result['depression_score'] = outputs['depression_score'][i].item()
                if 'anxiety_score' in outputs:
                    result['anxiety_score'] = outputs['anxiety_score'][i].item()
            else:
                result = {
                    'prediction': self.class_labels[torch.argmax(emotions[i]).item()],
                    'confidence': emotions[i].max().item(),
                    'probabilities': {
                        self.class_labels[j]: emotions[i][j].item()
                        for j in range(len(self.class_labels))
                    },
                    'inference_time': inference_time / len(batch_info),
                    'audio_duration': 1.0,
                    'feature_type': feature_type
                }
            
            result.update(info)
            results.append(result)
        
        return results
    
    def predict_with_uncertainty(
        self,
        audio_path: Union[str, Path],
        n_samples: int = 10,
        dropout_rate: float = 0.1
    ) -> Dict[str, Any]:
        """
        불확실성 추정을 포함한 예측
        Monte Carlo Dropout 사용
        
        Args:
            audio_path: 음성 파일 경로
            n_samples: 샘플링 횟수
            dropout_rate: 드롭아웃 비율
            
        Returns:
            result: 불확실성 정보 포함 결과
        """
        # 드롭아웃 활성화
        self.model.train()
        
        predictions = []
        
        for _ in range(n_samples):
            # 각 샘플에 대해 예측
            result = self.predict(audio_path)
            predictions.append(result['probabilities'])
        
        # 모델을 다시 eval 모드로
        self.model.eval()
        
        # 통계 계산
        probs_array = np.array([
            list(pred.values()) for pred in predictions
        ])
        
        mean_probs = np.mean(probs_array, axis=0)
        std_probs = np.std(probs_array, axis=0)
        
        # 엔트로피 기반 불확실성
        uncertainty = -np.sum(mean_probs * np.log(mean_probs + 1e-8))
        
        return {
            'prediction': self.class_labels[np.argmax(mean_probs)],
            'confidence': np.max(mean_probs),
            'uncertainty': uncertainty,
            'mean_probabilities': {
                self.class_labels[i]: prob
                for i, prob in enumerate(mean_probs)
            },
            'std_probabilities': {
                self.class_labels[i]: std
                for i, std in enumerate(std_probs)
            },
            'n_samples': n_samples
        }
    
    def explain_prediction(
        self,
        audio_path: Union[str, Path],
        method: str = 'integrated_gradients'
    ) -> Dict[str, Any]:
        """
        예측 결과 해석
        
        Args:
            audio_path: 음성 파일 경로
            method: 해석 방법 ('integrated_gradients', 'gradcam')
            
        Returns:
            explanation: 해석 결과
        """
        # 그래디언트 계산 활성화
        waveform, sr = sf.read(audio_path)
        waveform = torch.FloatTensor(waveform).unsqueeze(0)
        
        if sr != 16000:
            resampler = T.Resample(sr, 16000)
            waveform = resampler(waveform)
        
        waveform = waveform.to(self.device)
        waveform.requires_grad_(True)
        
        # Forward pass
        if self.model_type == 'emotion':
            outputs = self.model(waveform)
            if isinstance(outputs, dict):
                logits = outputs['emotions']
            else:
                logits = outputs
        else:
            logits = self.model(waveform)
        
        # 예측 클래스
        pred_class = torch.argmax(logits, dim=-1)
        
        # 그래디언트 계산
        self.model.zero_grad()
        logits[0, pred_class].backward()
        
        # 중요도 점수
        importance = torch.abs(waveform.grad).squeeze().cpu().numpy()
        
        return {
            'prediction': self.class_labels[pred_class.item()],
            'importance_scores': importance.tolist(),
            'method': method,
            'max_importance': float(np.max(importance)),
            'avg_importance': float(np.mean(importance))
        }
    
    def _update_cache(self, key: str, result: Dict):
        """캐시 업데이트 (LRU)"""
        if len(self.cache) >= self.cache_size:
            # 가장 오래된 항목 제거
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]
        
        self.cache[key] = result
    
    def _update_stats(self, inference_time: float):
        """통계 업데이트"""
        self.inference_stats['total_inferences'] += 1
        
        # 이동 평균으로 평균 시간 업데이트
        alpha = 0.1  # 학습률
        if self.inference_stats['avg_inference_time'] == 0:
            self.inference_stats['avg_inference_time'] = inference_time
        else:
            self.inference_stats['avg_inference_time'] = (
                alpha * inference_time + 
                (1 - alpha) * self.inference_stats['avg_inference_time']
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """통계 정보 반환"""
        cache_hit_rate = (
            self.inference_stats['cache_hits'] / 
            max(self.inference_stats['total_inferences'], 1)
        )
        
        return {
            **self.inference_stats,
            'cache_hit_rate': cache_hit_rate,
            'cache_size': len(self.cache),
            'device': str(self.device),
            'model_type': self.model_type
        }
    
    def benchmark(
        self,
        test_audio_paths: List[str],
        n_runs: int = 100
    ) -> Dict[str, Any]:
        """
        성능 벤치마크
        
        Args:
            test_audio_paths: 테스트 오디오 파일들
            n_runs: 실행 횟수
            
        Returns:
            benchmark_results: 벤치마크 결과
        """
        logger.info(f"벤치마크 시작: {n_runs}회 실행")
        
        inference_times = []
        memory_usage = []
        
        # GPU 메모리 추적
        if self.device.type == 'cuda':
            torch.cuda.empty_cache()
            initial_memory = torch.cuda.memory_allocated(self.device)
        
        # 워밍업
        for _ in range(10):
            if test_audio_paths:
                self.predict(test_audio_paths[0], use_cache=False)
        
        # 실제 벤치마크
        for i in range(n_runs):
            audio_path = test_audio_paths[i % len(test_audio_paths)]
            
            start_time = time.time()
            result = self.predict(audio_path, use_cache=False)
            inference_time = time.time() - start_time
            
            inference_times.append(inference_time)
            
            if self.device.type == 'cuda':
                current_memory = torch.cuda.memory_allocated(self.device)
                memory_usage.append(current_memory - initial_memory)
        
        # 통계 계산
        benchmark_results = {
            'n_runs': n_runs,
            'avg_inference_time': np.mean(inference_times),
            'std_inference_time': np.std(inference_times),
            'p95_inference_time': np.percentile(inference_times, 95),
            'p99_inference_time': np.percentile(inference_times, 99),
            'min_inference_time': np.min(inference_times),
            'max_inference_time': np.max(inference_times),
        }
        
        if memory_usage:
            benchmark_results.update({
                'avg_memory_mb': np.mean(memory_usage) / 1024 / 1024,
                'max_memory_mb': np.max(memory_usage) / 1024 / 1024
            })
        
        logger.info(f"벤치마크 완료: 평균 {benchmark_results['avg_inference_time']:.3f}s")
        
        return benchmark_results
    
    def clear_cache(self):
        """캐시 초기화"""
        self.cache.clear()
        logger.info("캐시 초기화됨")
    
    def save_stats(self, filepath: str):
        """통계를 파일로 저장"""
        stats = self.get_stats()
        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)
        logger.info(f"통계 저장: {filepath}")

# 사용 예제
if __name__ == "__main__":
    # 기본 사용법
    engine = InferenceEngine(
        model_path="./models/sincnet_model.pt",
        model_type="basic"
    )
    
    # 단일 예측
    result = engine.predict("./test_audio.wav")
    print(f"예측 결과: {result}")
    
    # 배치 예측
    batch_results = engine.predict_batch([
        "./test1.wav", "./test2.wav", "./test3.wav"
    ])
    
    # 통계 확인
    stats = engine.get_stats()
    print(f"엔진 통계: {stats}")