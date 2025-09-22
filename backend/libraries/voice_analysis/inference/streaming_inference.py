# 제7강: AI 모델 이해와 로컬 테스트 - 실시간 스트리밍 추론

import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import pyaudio
import queue
import threading
import time
from typing import Dict, List, Optional, Callable, Any
import logging
from collections import deque

logger = logging.getLogger(__name__)

class StreamingInference:
    """
    실시간 음성 스트리밍 추론
    마이크 입력을 실시간으로 처리
    """
    
    def __init__(
        self,
        model: nn.Module,
        chunk_duration: float = 3.0,
        sample_rate: int = 16000,
        overlap_ratio: float = 0.5,
        buffer_size: int = 10
    ):
        """
        스트리밍 추론 초기화
        
        Args:
            model: 추론 모델
            chunk_duration: 처리 단위 시간 (초)
            sample_rate: 샘플링 레이트
            overlap_ratio: 청크 간 겹침 비율
            buffer_size: 오디오 버퍼 크기
        """
        self.model = model
        self.model.eval()
        
        self.chunk_duration = chunk_duration
        self.sample_rate = sample_rate
        self.overlap_ratio = overlap_ratio
        self.chunk_size = int(chunk_duration * sample_rate)
        self.overlap_size = int(self.chunk_size * overlap_ratio)
        
        # 오디오 큐 및 결과 큐
        self.audio_queue = queue.Queue(maxsize=buffer_size)
        self.result_queue = queue.Queue()
        
        # 순환 버퍼
        self.audio_buffer = deque(maxlen=self.chunk_size * 2)
        
        # PyAudio 초기화
        self.pa = pyaudio.PyAudio()
        self.stream = None
        self.is_running = False
        
        # 스레드
        self.process_thread = None
        
        # 결과 스무딩
        self.result_history = deque(maxlen=5)
        
        # 콜백 함수
        self.result_callback = None
        
        # 성능 메트릭
        self.performance_metrics = {
            'total_chunks': 0,
            'avg_processing_time': 0,
            'buffer_overflows': 0,
            'processing_errors': 0
        }
        
        logger.info(f"스트리밍 추론 초기화: {chunk_duration}s 청크, {sample_rate}Hz")
        
    def set_result_callback(self, callback: Callable[[Dict], None]):
        """결과 콜백 함수 설정"""
        self.result_callback = callback
        
    def audio_callback(
        self,
        in_data: bytes,
        frame_count: int,
        time_info: Dict,
        status_flags: int
    ) -> Tuple[None, int]:
        """오디오 스트림 콜백"""
        try:
            # 오디오 데이터 변환
            audio_chunk = np.frombuffer(in_data, dtype=np.float32)
            
            # 큐에 추가 (논블로킹)
            try:
                self.audio_queue.put_nowait(audio_chunk)
            except queue.Full:
                # 버퍼 오버플로우
                self.performance_metrics['buffer_overflows'] += 1
                logger.warning("오디오 버퍼 오버플로우")
                
                # 가장 오래된 청크 제거
                try:
                    self.audio_queue.get_nowait()
                    self.audio_queue.put_nowait(audio_chunk)
                except queue.Empty:
                    pass
            
            return (None, pyaudio.paContinue)
            
        except Exception as e:
            logger.error(f"오디오 콜백 에러: {str(e)}")
            return (None, pyaudio.paAbort)
    
    def start(self):
        """스트리밍 시작"""
        if self.is_running:
            logger.warning("이미 실행 중입니다")
            return
            
        self.is_running = True
        
        try:
            # 오디오 스트림 열기
            self.stream = self.pa.open(
                format=pyaudio.paFloat32,
                channels=1,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=1024,
                stream_callback=self.audio_callback
            )
            
            # 처리 스레드 시작
            self.process_thread = threading.Thread(
                target=self._process_audio_loop,
                daemon=True
            )
            self.process_thread.start()
            
            # 스트림 시작
            self.stream.start_stream()
            
            logger.info("스트리밍 시작됨")
            
        except Exception as e:
            logger.error(f"스트리밍 시작 실패: {str(e)}")
            self.stop()
            raise
    
    def stop(self):
        """스트리밍 중지"""
        logger.info("스트리밍 중지 중...")
        
        self.is_running = False
        
        # 스트림 중지
        if self.stream and self.stream.is_active():
            self.stream.stop_stream()
            self.stream.close()
        
        # PyAudio 종료
        if self.pa:
            self.pa.terminate()
        
        # 스레드 대기
        if self.process_thread and self.process_thread.is_alive():
            self.process_thread.join(timeout=5)
        
        logger.info("스트리밍 중지됨")
    
    def _process_audio_loop(self):
        """오디오 처리 루프"""
        logger.info("오디오 처리 스레드 시작")
        
        while self.is_running:
            try:
                # 오디오 청크 수집
                chunk = self.audio_queue.get(timeout=0.1)
                self.audio_buffer.extend(chunk)
                
                # 충분한 데이터가 모이면 처리
                if len(self.audio_buffer) >= self.chunk_size:
                    # 처리할 청크 추출
                    chunk_data = list(self.audio_buffer)[:self.chunk_size]
                    audio_tensor = torch.FloatTensor(chunk_data)
                    
                    # 추론 수행
                    result = self._process_chunk(audio_tensor)
                    
                    # 결과 스무딩
                    smoothed_result = self._smooth_results(result)
                    
                    # 결과 저장
                    self.result_queue.put(smoothed_result)
                    
                    # 콜백 호출
                    if self.result_callback:
                        self.result_callback(smoothed_result)
                    
                    # 버퍼 업데이트 (슬라이딩 윈도우)
                    remove_size = self.chunk_size - self.overlap_size
                    for _ in range(min(remove_size, len(self.audio_buffer))):
                        self.audio_buffer.popleft()
                    
                    # 성능 메트릭 업데이트
                    self.performance_metrics['total_chunks'] += 1
                    
            except queue.Empty:
                continue
            except Exception as e:
                logger.error(f"오디오 처리 에러: {str(e)}")
                self.performance_metrics['processing_errors'] += 1
                continue
    
    @torch.no_grad()
    def _process_chunk(self, audio: torch.Tensor) -> Dict[str, Any]:
        """단일 청크 처리"""
        start_time = time.time()
        
        try:
            # 디바이스 이동
            audio = audio.unsqueeze(0).to(self.model.device)
            
            # 모델 추론
            if hasattr(self.model, 'predict'):
                # 커스텀 predict 메서드 사용
                outputs = self.model.predict(audio)
            else:
                # 직접 forward
                logits = self.model(audio)
                if isinstance(logits, dict):
                    # 다중 출력 모델
                    outputs = logits
                else:
                    # 단일 출력 모델
                    probs = F.softmax(logits, dim=-1)
                    outputs = {'probabilities': probs[0].cpu().numpy()}
            
            processing_time = time.time() - start_time
            
            # 성능 메트릭 업데이트
            alpha = 0.1
            if self.performance_metrics['avg_processing_time'] == 0:
                self.performance_metrics['avg_processing_time'] = processing_time
            else:
                self.performance_metrics['avg_processing_time'] = (
                    alpha * processing_time + 
                    (1 - alpha) * self.performance_metrics['avg_processing_time']
                )
            
            result = {
                'timestamp': time.time(),
                'processing_time': processing_time,
                'chunk_id': self.performance_metrics['total_chunks'],
                **outputs
            }
            
            return result
            
        except Exception as e:
            logger.error(f"청크 처리 실패: {str(e)}")
            return {
                'timestamp': time.time(),
                'error': str(e),
                'chunk_id': self.performance_metrics['total_chunks']
            }
    
    def _smooth_results(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """결과 스무딩 (이동 평균)"""
        if 'error' in result:
            return result
        
        self.result_history.append(result)
        
        if len(self.result_history) < 2:
            return result
        
        # 확률값 스무딩 (지수 이동 평균)
        if 'probabilities' in result:
            alpha = 0.3  # 스무딩 계수
            
            current_probs = result['probabilities']
            if isinstance(current_probs, np.ndarray):
                current_probs = current_probs.tolist()
            
            # 이전 결과들의 평균
            prev_results = [r for r in self.result_history[:-1] if 'probabilities' in r]
            if prev_results:
                prev_probs = prev_results[-1]['probabilities']
                if isinstance(prev_probs, np.ndarray):
                    prev_probs = prev_probs.tolist()
                
                # 지수 이동 평균
                smoothed_probs = [
                    alpha * curr + (1 - alpha) * prev
                    for curr, prev in zip(current_probs, prev_probs)
                ]
                
                result['probabilities'] = smoothed_probs
                result['smoothed'] = True
        
        return result
    
    def get_recent_results(self, n: int = 10) -> List[Dict[str, Any]]:
        """최근 결과 반환"""
        results = []
        temp_queue = queue.Queue()
        
        # 큐에서 결과 수집
        while not self.result_queue.empty() and len(results) < n:
            try:
                result = self.result_queue.get_nowait()
                results.append(result)
                temp_queue.put(result)
            except queue.Empty:
                break
        
        # 큐에 다시 넣기
        while not temp_queue.empty():
            self.result_queue.put(temp_queue.get())
        
        return results[-n:]
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """성능 메트릭 반환"""
        metrics = self.performance_metrics.copy()
        
        # 추가 계산된 메트릭
        if metrics['total_chunks'] > 0:
            metrics['error_rate'] = (
                metrics['processing_errors'] / metrics['total_chunks']
            )
            metrics['overflow_rate'] = (
                metrics['buffer_overflows'] / metrics['total_chunks']
            )
        else:
            metrics['error_rate'] = 0
            metrics['overflow_rate'] = 0
        
        metrics['is_running'] = self.is_running
        metrics['buffer_size'] = len(self.audio_buffer)
        metrics['queue_size'] = self.audio_queue.qsize()
        
        return metrics
    
    def reset_metrics(self):
        """메트릭 초기화"""
        self.performance_metrics = {
            'total_chunks': 0,
            'avg_processing_time': 0,
            'buffer_overflows': 0,
            'processing_errors': 0
        }
        logger.info("성능 메트릭 초기화됨")

class AudioVisualizer:
    """
    실시간 오디오 시각화
    """
    
    def __init__(
        self,
        sample_rate: int = 16000,
        chunk_size: int = 1024,
        history_length: int = 100
    ):
        """
        시각화 초기화
        
        Args:
            sample_rate: 샘플링 레이트
            chunk_size: 청크 크기
            history_length: 히스토리 길이
        """
        self.sample_rate = sample_rate
        self.chunk_size = chunk_size
        self.history_length = history_length
        
        # 데이터 히스토리
        self.waveform_history = deque(maxlen=history_length)
        self.prediction_history = deque(maxlen=history_length)
        
        # 시각화 설정
        self.is_visualizing = False
        
    def update_audio(self, audio_chunk: np.ndarray):
        """오디오 데이터 업데이트"""
        self.waveform_history.append(audio_chunk)
    
    def update_prediction(self, prediction: Dict[str, Any]):
        """예측 결과 업데이트"""
        self.prediction_history.append(prediction)
    
    def start_visualization(self):
        """실시간 시각화 시작"""
        try:
            import matplotlib.pyplot as plt
            from matplotlib.animation import FuncAnimation
            
            self.is_visualizing = True
            
            # Figure 설정
            self.fig, (self.ax1, self.ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # 애니메이션 설정
            self.animation = FuncAnimation(
                self.fig, 
                self._update_plots, 
                interval=100,  # 100ms 업데이트
                blit=False
            )
            
            plt.show()
            
        except ImportError:
            logger.warning("matplotlib을 찾을 수 없습니다. 시각화를 건너뜁니다.")
        except Exception as e:
            logger.error(f"시각화 시작 실패: {str(e)}")
    
    def _update_plots(self, frame):
        """플롯 업데이트"""
        try:
            # 웨이브폼 플롯
            self.ax1.clear()
            if self.waveform_history:
                # 최근 데이터 연결
                recent_audio = np.concatenate(list(self.waveform_history)[-10:])
                time_axis = np.arange(len(recent_audio)) / self.sample_rate
                
                self.ax1.plot(time_axis, recent_audio, 'b-', alpha=0.7)
                self.ax1.set_title('Real-time Audio Waveform')
                self.ax1.set_xlabel('Time (s)')
                self.ax1.set_ylabel('Amplitude')
                self.ax1.set_ylim([-1, 1])
                self.ax1.grid(True, alpha=0.3)
            
            # 예측 결과 플롯
            self.ax2.clear()
            if self.prediction_history:
                # 예측 히스토리 표시
                timestamps = [p.get('timestamp', 0) for p in self.prediction_history]
                confidences = [p.get('confidence', 0) for p in self.prediction_history]
                
                if timestamps and confidences:
                    # 상대 시간으로 변환
                    base_time = timestamps[0] if timestamps else 0
                    rel_times = [(t - base_time) for t in timestamps]
                    
                    self.ax2.plot(rel_times, confidences, 'r-', marker='o', markersize=3)
                    self.ax2.set_title('Prediction Confidence Over Time')
                    self.ax2.set_xlabel('Time (s)')
                    self.ax2.set_ylabel('Confidence')
                    self.ax2.set_ylim([0, 1])
                    self.ax2.grid(True, alpha=0.3)
                    
                    # 최근 예측 표시
                    if self.prediction_history:
                        recent_pred = self.prediction_history[-1]
                        if 'prediction' in recent_pred:
                            self.ax2.text(
                                0.02, 0.98,
                                f"Current: {recent_pred['prediction']}",
                                transform=self.ax2.transAxes,
                                verticalalignment='top',
                                bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.8)
                            )
            
            plt.tight_layout()
            
        except Exception as e:
            logger.error(f"플롯 업데이트 실패: {str(e)}")
    
    def stop_visualization(self):
        """시각화 중지"""
        self.is_visualizing = False
        if hasattr(self, 'animation'):
            self.animation.event_source.stop()

class RealTimeProcessor:
    """
    실시간 음성 처리 통합 클래스
    """
    
    def __init__(
        self,
        model: nn.Module,
        enable_visualization: bool = True,
        enable_callbacks: bool = True
    ):
        """
        실시간 처리기 초기화
        
        Args:
            model: 추론 모델
            enable_visualization: 시각화 활성화
            enable_callbacks: 콜백 활성화
        """
        self.streaming_engine = StreamingInference(model)
        
        if enable_visualization:
            self.visualizer = AudioVisualizer()
        else:
            self.visualizer = None
        
        if enable_callbacks:
            self.streaming_engine.set_result_callback(self._result_handler)
        
        # 결과 저장
        self.session_results = []
        
    def _result_handler(self, result: Dict[str, Any]):
        """결과 처리 핸들러"""
        # 세션 결과에 추가
        self.session_results.append(result)
        
        # 시각화 업데이트
        if self.visualizer:
            self.visualizer.update_prediction(result)
        
        # 로깅
        if 'prediction' in result:
            logger.info(
                f"실시간 예측: {result['prediction']} "
                f"(신뢰도: {result.get('confidence', 0):.3f})"
            )
    
    def start_session(self):
        """세션 시작"""
        logger.info("실시간 처리 세션 시작")
        
        # 스트리밍 시작
        self.streaming_engine.start()
        
        # 시각화 시작
        if self.visualizer:
            self.visualizer.start_visualization()
    
    def stop_session(self):
        """세션 종료"""
        logger.info("실시간 처리 세션 종료")
        
        # 스트리밍 중지
        self.streaming_engine.stop()
        
        # 시각화 중지
        if self.visualizer:
            self.visualizer.stop_visualization()
    
    def get_session_summary(self) -> Dict[str, Any]:
        """세션 요약 반환"""
        if not self.session_results:
            return {'message': '결과 없음'}
        
        # 예측 분포 계산
        predictions = [r.get('prediction') for r in self.session_results if 'prediction' in r]
        
        if predictions:
            from collections import Counter
            pred_counts = Counter(predictions)
            
            # 평균 신뢰도
            confidences = [r.get('confidence', 0) for r in self.session_results if 'confidence' in r]
            avg_confidence = np.mean(confidences) if confidences else 0
            
            # 처리 시간 통계
            proc_times = [r.get('processing_time', 0) for r in self.session_results if 'processing_time' in r]
            
            return {
                'total_predictions': len(predictions),
                'prediction_distribution': dict(pred_counts),
                'avg_confidence': avg_confidence,
                'avg_processing_time': np.mean(proc_times) if proc_times else 0,
                'session_duration': time.time() - (self.session_results[0].get('timestamp', time.time())),
                'performance_metrics': self.streaming_engine.get_performance_metrics()
            }
        
        return {'message': '유효한 예측 없음'}

# 사용 예제
if __name__ == "__main__":
    # 모델 로드 (예제)
    from ..models.sincnet_model import SincNet
    
    model = SincNet()
    # model.load_state_dict(torch.load('model.pt'))
    
    # 실시간 처리기 생성
    processor = RealTimeProcessor(model)
    
    try:
        # 세션 시작
        processor.start_session()
        
        # 10초간 실행
        time.sleep(10)
        
        # 세션 종료
        processor.stop_session()
        
        # 결과 요약
        summary = processor.get_session_summary()
        print(f"세션 요약: {summary}")
        
    except KeyboardInterrupt:
        logger.info("사용자에 의해 중단됨")
        processor.stop_session()