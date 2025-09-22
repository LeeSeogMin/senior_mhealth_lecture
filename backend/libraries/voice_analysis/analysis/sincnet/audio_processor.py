"""
오디오 전처리 모듈
다양한 형식과 크기의 오디오 파일을 처리
"""

import wave
import subprocess
import tempfile
import os
import numpy as np
import torch
from pathlib import Path
from typing import Optional, Tuple, Union
import logging

logger = logging.getLogger(__name__)


class AudioProcessor:
    """다양한 오디오 형식과 크기를 처리하는 통합 프로세서"""
    
    SUPPORTED_FORMATS = ['.wav', '.mp3', '.m4a', '.flac', '.ogg', '.aac', '.wma']
    TARGET_SAMPLE_RATE = 16000
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.ffmpeg_available = self._check_ffmpeg()
        
    def _check_ffmpeg(self) -> bool:
        """FFmpeg 사용 가능 여부 확인"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, 
                                  text=True, 
                                  timeout=5)
            return result.returncode == 0
        except Exception:
            self.logger.warning("FFmpeg를 찾을 수 없습니다. MP3 등 변환 기능 제한")
            return False
    
    def load_audio(self, audio_path: Union[str, Path], 
                   target_sr: int = None,
                   mono: bool = True) -> Tuple[Optional[np.ndarray], int]:
        """
        다양한 형식의 오디오 파일 로드
        
        Args:
            audio_path: 오디오 파일 경로
            target_sr: 목표 샘플레이트 (기본: 16000)
            mono: 모노로 변환 여부
            
        Returns:
            (audio_array, sample_rate) or (None, 0) if failed
        """
        audio_path = Path(audio_path)
        
        if not audio_path.exists():
            self.logger.error(f"파일이 존재하지 않음: {audio_path}")
            return None, 0
        
        # 파일 형식 확인
        ext = audio_path.suffix.lower()
        
        if ext not in self.SUPPORTED_FORMATS:
            self.logger.error(f"지원하지 않는 형식: {ext}")
            return None, 0
        
        target_sr = target_sr or self.TARGET_SAMPLE_RATE
        
        # WAV 파일 직접 처리
        if ext == '.wav':
            return self._load_wav(audio_path, target_sr, mono)
        
        # 다른 형식은 FFmpeg로 변환, 없으면 Python 라이브러리 사용
        if self.ffmpeg_available:
            return self._load_with_ffmpeg(audio_path, target_sr, mono)
        else:
            # FFmpeg 없이 Python 라이브러리로 처리 시도
            return self._load_audio_fallback(audio_path, target_sr, mono)
    
    def _load_wav(self, wav_path: Path, target_sr: int, mono: bool) -> Tuple[Optional[np.ndarray], int]:
        """WAV 파일 직접 로드"""
        try:
            with wave.open(str(wav_path), 'rb') as wav:
                # WAV 파일 정보
                nchannels = wav.getnchannels()
                sampwidth = wav.getsampwidth()
                framerate = wav.getframerate()
                nframes = wav.getnframes()
                
                duration = nframes / framerate
                self.logger.info(f"WAV 정보: {nchannels}ch, {framerate}Hz, {duration:.2f}초")
                
                # 오디오 데이터 읽기
                frames = wav.readframes(nframes)
                
                # 비트 깊이에 따른 변환
                if sampwidth == 1:  # 8-bit
                    audio = np.frombuffer(frames, dtype=np.uint8).astype(np.float32)
                    audio = (audio - 128) / 128.0
                elif sampwidth == 2:  # 16-bit
                    audio = np.frombuffer(frames, dtype=np.int16).astype(np.float32)
                    audio = audio / 32768.0
                elif sampwidth == 3:  # 24-bit
                    # 24-bit는 특별 처리 필요
                    audio = self._convert_24bit_to_float(frames, nframes * nchannels)
                elif sampwidth == 4:  # 32-bit
                    audio = np.frombuffer(frames, dtype=np.int32).astype(np.float32)
                    audio = audio / 2147483648.0
                else:
                    self.logger.error(f"지원하지 않는 비트 깊이: {sampwidth * 8}bit")
                    return None, 0
                
                # 채널 처리
                if nchannels > 1:
                    audio = audio.reshape(-1, nchannels)
                    if mono:
                        audio = audio.mean(axis=1)
                
                # 리샘플링
                if framerate != target_sr:
                    audio = self._resample(audio, framerate, target_sr)
                    self.logger.info(f"리샘플링: {framerate}Hz -> {target_sr}Hz")
                
                return audio, target_sr
                
        except Exception as e:
            self.logger.error(f"WAV 로드 실패: {str(e)}", exc_info=True)
            return None, 0
    
    def _convert_24bit_to_float(self, data: bytes, n_samples: int) -> np.ndarray:
        """24-bit PCM을 float로 변환"""
        # 24-bit는 3바이트씩 처리
        result = np.zeros(n_samples, dtype=np.float32)
        for i in range(n_samples):
            # Little-endian 24-bit to 32-bit
            b1, b2, b3 = data[i*3], data[i*3+1], data[i*3+2]
            value = b1 | (b2 << 8) | (b3 << 16)
            # Sign extension
            if value & 0x800000:
                value |= 0xFF000000
            result[i] = np.int32(value) / 8388608.0
        return result
    
    def _load_with_ffmpeg(self, audio_path: Path, target_sr: int, mono: bool) -> Tuple[Optional[np.ndarray], int]:
        """FFmpeg를 사용한 오디오 로드"""
        try:
            # 임시 WAV 파일 생성
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp_wav:
                tmp_path = tmp_wav.name
            
            # FFmpeg 명령어 구성
            cmd = [
                'ffmpeg', '-i', str(audio_path),
                '-ar', str(target_sr),  # 샘플레이트
                '-acodec', 'pcm_s16le',  # 16-bit PCM
            ]
            
            if mono:
                cmd.extend(['-ac', '1'])  # 모노
            
            cmd.extend([tmp_path, '-y'])  # 출력 파일, 덮어쓰기
            
            # 변환 실행
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.logger.error(f"FFmpeg 변환 실패: {result.stderr}")
                return None, 0
            
            # 변환된 WAV 로드
            audio, sr = self._load_wav(Path(tmp_path), target_sr, mono)
            
            # 임시 파일 삭제
            try:
                os.unlink(tmp_path)
            except:
                pass
            
            return audio, sr
            
        except subprocess.TimeoutExpired:
            self.logger.error("FFmpeg 변환 시간 초과")
            return None, 0
        except Exception as e:
            self.logger.error(f"FFmpeg 변환 실패: {str(e)}", exc_info=True)
            return None, 0
    
    def _resample(self, audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
        """간단한 선형 보간 리샘플링"""
        if orig_sr == target_sr:
            return audio
        
        # 리샘플링 비율
        ratio = target_sr / orig_sr
        new_length = int(len(audio) * ratio)
        
        # 선형 보간
        old_indices = np.arange(len(audio))
        new_indices = np.linspace(0, len(audio) - 1, new_length)
        
        return np.interp(new_indices, old_indices, audio)
    
    def prepare_for_model(self, audio: np.ndarray, 
                         window_size: int,
                         stride: Optional[int] = None,
                         pad_mode: str = 'constant') -> torch.Tensor:
        """
        모델 입력을 위한 오디오 준비
        
        Args:
            audio: 오디오 배열
            window_size: 모델이 요구하는 윈도우 크기
            stride: 슬라이딩 윈도우 스트라이드 (기본: window_size // 2)
            pad_mode: 패딩 모드 ('constant', 'reflect', 'replicate')
            
        Returns:
            [n_windows, 1, window_size] 형태의 텐서
        """
        if len(audio) == 0:
            raise ValueError("빈 오디오 배열")
        
        stride = stride or window_size // 2
        
        # 너무 짧은 경우 패딩
        if len(audio) < window_size:
            pad_length = window_size - len(audio)
            if pad_mode == 'constant':
                audio = np.pad(audio, (0, pad_length), 'constant', constant_values=0)
            elif pad_mode == 'reflect':
                audio = np.pad(audio, (0, pad_length), 'reflect')
            elif pad_mode == 'replicate':
                audio = np.pad(audio, (0, pad_length), 'edge')
            else:
                raise ValueError(f"Unknown pad_mode: {pad_mode}")
        
        # 슬라이딩 윈도우 생성
        windows = []
        for i in range(0, len(audio) - window_size + 1, stride):
            window = audio[i:i + window_size]
            windows.append(window)
        
        if not windows:
            # 하나의 윈도우만 생성
            windows = [audio[:window_size]]
        
        # 텐서 변환
        windows_array = np.stack(windows)
        tensor = torch.from_numpy(windows_array).float()
        
        # [n_windows, 1, window_size] 형태로
        tensor = tensor.unsqueeze(1)
        
        return tensor
    
    def process_any_audio(self, audio_path: Union[str, Path],
                         model_window_size: int = 2937,
                         overlap: float = 0.5) -> Tuple[Optional[torch.Tensor], dict]:
        """
        어떤 오디오 파일이든 모델 입력으로 변환
        
        Args:
            audio_path: 오디오 파일 경로
            model_window_size: 모델 입력 크기
            overlap: 윈도우 오버랩 비율 (0~1)
            
        Returns:
            (tensor, info_dict) or (None, error_dict)
        """
        # 오디오 로드
        audio, sr = self.load_audio(audio_path, target_sr=16000, mono=True)
        
        if audio is None:
            return None, {'error': '오디오 로드 실패', 'path': str(audio_path)}
        
        # 스트라이드 계산
        stride = int(model_window_size * (1 - overlap))
        
        # 모델 입력 준비
        try:
            tensor = self.prepare_for_model(audio, model_window_size, stride)
            
            info = {
                'original_path': str(audio_path),
                'sample_rate': sr,
                'duration': len(audio) / sr,
                'n_samples': len(audio),
                'n_windows': tensor.shape[0],
                'window_size': model_window_size,
                'window_duration': model_window_size / sr,
                'stride': stride,
                'overlap': overlap
            }
            
            self.logger.info(f"처리 완료: {info['n_windows']}개 윈도우, "
                           f"각 {info['window_duration']:.3f}초")
            
            return tensor, info
            
        except Exception as e:
            self.logger.error(f"전처리 실패: {str(e)}", exc_info=True)
            return None, {'error': str(e), 'path': str(audio_path)}
    
    def _load_audio_fallback(self, audio_path: Path, target_sr: int = None, mono: bool = True) -> Tuple[Optional[np.ndarray], int]:
        """
        FFmpeg 없이 Python 라이브러리를 사용한 오디오 로드
        """
        ext = audio_path.suffix.lower()
        target_sr = target_sr or self.TARGET_SAMPLE_RATE
        
        self.logger.info(f"FFmpeg 없이 {ext} 파일 처리 시도...")
        
        # Try multiple libraries in order of preference
        loaders = [
            self._load_with_pydub,
            self._load_with_librosa,
            self._load_with_audioread,
        ]
        
        for loader in loaders:
            try:
                result = loader(audio_path, target_sr, mono)
                if result[0] is not None:
                    return result
            except ImportError as e:
                self.logger.debug(f"{loader.__name__} 라이브러리 없음: {e}")
                continue
            except Exception as e:
                self.logger.warning(f"{loader.__name__} 로드 실패: {e}")
                continue
        
        # All methods failed
        self.logger.error(f"모든 방법으로 {ext} 파일 로드 실패")
        self.logger.info("다음 라이브러리 설치를 권장합니다:")
        self.logger.info("  pip install pydub")
        self.logger.info("  pip install librosa")
        self.logger.info("  pip install audioread")
        return None, 0
    
    def _load_with_pydub(self, audio_path: Path, target_sr: int, mono: bool) -> Tuple[Optional[np.ndarray], int]:
        """pydub을 사용한 오디오 로드"""
        from pydub import AudioSegment
        
        # Load audio file
        ext = audio_path.suffix.lower()
        if ext == '.mp3':
            audio = AudioSegment.from_mp3(str(audio_path))
        elif ext == '.m4a':
            audio = AudioSegment.from_file(str(audio_path), format="m4a")
        elif ext == '.flac':
            audio = AudioSegment.from_file(str(audio_path), format="flac")
        elif ext == '.ogg':
            audio = AudioSegment.from_ogg(str(audio_path))
        else:
            audio = AudioSegment.from_file(str(audio_path))
        
        # Convert to mono
        if mono and audio.channels > 1:
            audio = audio.set_channels(1)
        
        # Resample if needed
        if audio.frame_rate != target_sr:
            audio = audio.set_frame_rate(target_sr)
        
        # Convert to numpy array
        samples = np.array(audio.get_array_of_samples(), dtype=np.float32)
        
        # Handle multi-channel
        if not mono and audio.channels > 1:
            samples = samples.reshape(-1, audio.channels)
        
        # Normalize to [-1, 1] range based on sample width
        if audio.sample_width == 1:  # 8-bit
            samples = (samples - 128) / 128.0
        elif audio.sample_width == 2:  # 16-bit
            samples = samples / 32768.0
        elif audio.sample_width == 4:  # 32-bit
            samples = samples / 2147483648.0
        
        self.logger.info(f"pydub 로드 성공: {len(samples)} 샘플, {audio.frame_rate}Hz, {audio.channels}ch")
        return samples, audio.frame_rate
    
    def _load_with_librosa(self, audio_path: Path, target_sr: int, mono: bool) -> Tuple[Optional[np.ndarray], int]:
        """librosa를 사용한 오디오 로드"""
        import librosa
        
        y, sr = librosa.load(str(audio_path), sr=target_sr, mono=mono)
        
        self.logger.info(f"librosa 로드 성공: {len(y)} 샘플, {sr}Hz")
        return y, sr
    
    def _load_with_audioread(self, audio_path: Path, target_sr: int, mono: bool) -> Tuple[Optional[np.ndarray], int]:
        """audioread를 사용한 오디오 로드 (기본적인 접근)"""
        import audioread
        import numpy as np
        
        samples = []
        sample_rate = None
        
        with audioread.audio_open(str(audio_path)) as input_file:
            sample_rate = input_file.samplerate
            channels = input_file.channels
            
            for frame in input_file:
                # Convert bytes to numpy array
                frame_data = np.frombuffer(frame, dtype=np.int16).astype(np.float32)
                frame_data = frame_data / 32768.0  # Normalize to [-1, 1]
                samples.append(frame_data)
        
        if not samples:
            raise Exception("No audio data read")
        
        # Concatenate all frames
        audio = np.concatenate(samples)
        
        # Handle multi-channel
        if channels > 1:
            audio = audio.reshape(-1, channels)
            if mono:
                audio = audio.mean(axis=1)
        
        # Resample if needed
        if sample_rate != target_sr:
            audio = self._resample(audio, sample_rate, target_sr)
            sample_rate = target_sr
        
        self.logger.info(f"audioread 로드 성공: {len(audio)} 샘플, {sample_rate}Hz")
        return audio, sample_rate