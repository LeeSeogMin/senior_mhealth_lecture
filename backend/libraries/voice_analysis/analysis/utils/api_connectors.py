
"""
실제 API 연동 모듈
Google Cloud Speech API와 Grok(XAI) API 연동 (GPT-4o, Gemini fallback)
Firebase Storage 통합 및 화자 분리 기능 완전 구현
"""

import os
import asyncio
import logging
import json
import base64
import tempfile
import io
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import time
from datetime import datetime
import hashlib

from google.cloud import speech
from google.cloud import storage
from google.oauth2 import service_account
from google.api_core import retry
from google.api_core.exceptions import GoogleAPIError
import numpy as np
import librosa
import soundfile as sf
import openai
from openai import OpenAI  # OpenAI 1.51.0에서는 동기 클라이언트 사용
import google.generativeai as genai
from .firebase_storage_connector import FirebaseStorageConnector

logger = logging.getLogger(__name__)


class GoogleCloudConnector:
    """Google Cloud API 통합 커넥터"""
    
    def __init__(self, credentials_path: Optional[str] = None, project_id: Optional[str] = None):
        """초기화"""
        self.credentials_path = credentials_path or os.getenv('GOOGLE_APPLICATION_CREDENTIALS')
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID')


class GoogleCloudSpeechConnector:
    """Google Cloud Speech API 연동 - 화자 분리 기능 완전 구현"""
    
    def __init__(self, credentials_path: Optional[str] = None, project_id: Optional[str] = None):
        """
        초기화
        
        Args:
            credentials_path: 서비스 계정 키 파일 경로
            project_id: GCP 프로젝트 ID
        """
        self.project_id = project_id or os.getenv('GCP_PROJECT_ID', 'senior-mhealth-472007')
        
        # 인증 설정
        if credentials_path and Path(credentials_path).exists():
            credentials = service_account.Credentials.from_service_account_file(
                credentials_path
            )
            self.client = speech.SpeechClient(credentials=credentials)
            self.storage_client = storage.Client(credentials=credentials, project=self.project_id)
        else:
            # 환경 변수에서 인증 정보 로드
            self.client = speech.SpeechClient()
            self.storage_client = storage.Client(project=self.project_id)
        
        # Firebase Storage 연동
        self.storage_connector = FirebaseStorageConnector(credentials_path)
        
        # Google Cloud Storage 버킷 설정
        self.bucket_name = os.getenv('GCS_BUCKET_NAME', 'senior-mhealth-472007.firebasestorage.app')
        
        # Long Running 작업 상태 캐시
        self.operation_cache = {}
        
        logger.info(f"Google Cloud Speech API 연동 초기화 완료 - Project: {self.project_id}")
    
    async def transcribe_with_diarization(
        self,
        audio_path: str,
        language_code: str = 'ko-KR',
        enable_word_confidence: bool = True,
        use_enhanced_model: bool = True
    ) -> Dict[str, Any]:
        """
        화자 분리를 포함한 음성 인식 (3분 이상 긴 오디오 최적화)
        
        Args:
            audio_path: 오디오 파일 경로 (로컬 또는 Firebase Storage URL)
            language_code: 언어 코드
            enable_word_confidence: 단어별 신뢰도 포함 여부
            use_enhanced_model: 향상된 모델 사용 여부
            
        Returns:
            전사 결과 with 화자 분리 정보
        """
        try:
            start_time = time.time()
            
            # 1. 오디오 메타데이터 추출
            audio_metadata = self._get_audio_metadata(audio_path)
            duration = audio_metadata.get('duration', 0)
            sample_rate = audio_metadata.get('sample_rate', 16000)
            
            logger.info(f"오디오 분석 시작: {duration:.1f}초, {sample_rate}Hz")
            
            # 2. Firebase Storage에 업로드 (3분 이상은 필수)
            if duration >= 180 or not os.path.exists(audio_path):
                # Firebase Storage 또는 GCS에 업로드
                gs_uri = await self._upload_to_storage(audio_path)
                logger.info(f"오디오 파일 Storage 업로드 완료: {gs_uri}")
            else:
                # 짧은 파일도 일관성을 위해 Storage 사용 권장
                gs_uri = await self._upload_to_storage(audio_path)
            
            # 3. Speech Recognition 설정 구성
            # 변환된 LINEAR16 오디오는 항상 16000Hz
            config = self._build_recognition_config(
                sample_rate=16000,  # LINEAR16 변환 후 항상 16000Hz
                language_code=language_code,
                enable_word_confidence=enable_word_confidence,
                use_enhanced_model=use_enhanced_model,
                enable_diarization=True
            )
            
            # 4. Long Running API 실행 (3분 이상 필수)
            operation = await self._start_long_running_recognition(gs_uri, config)
            
            # 5. 작업 진행 상황 모니터링
            result = await self._wait_for_operation(operation)
            
            # 6. 화자 분리 결과 처리
            processed_result = self._process_diarization_result(result, audio_metadata)
            
            # 7. 화자 신뢰도 및 검증
            processed_result = self._validate_speaker_separation(processed_result)
            
            # 8. Storage 정리 (임시 파일)
            if 'temp/' in gs_uri:
                await self._cleanup_storage(gs_uri)
            
            processing_time = time.time() - start_time
            processed_result['metadata'] = {
                'processing_time': processing_time,
                'audio_duration': duration,
                'sample_rate': 16000,  # 변환된 샘플레이트
                'original_sample_rate': sample_rate,
                'model_used': 'enhanced' if use_enhanced_model else 'standard',
                'api_type': 'long_running'
            }
            
            logger.info(f"STT 및 화자 분리 완료 - 처리시간: {processing_time:.2f}초")
            return processed_result
                
        except Exception as e:
            logger.error(f"Google Cloud Speech API 호출 실패: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'segments': [],
                'transcript': ''
            }
    
    def _get_audio_metadata(self, audio_path: str) -> Dict[str, Any]:
        """오디오 파일 메타데이터 추출"""
        try:
            # librosa로 오디오 정보 추출
            y, sr = librosa.load(audio_path, sr=None, mono=True)
            duration = len(y) / sr
            
            # 추가 메타데이터
            metadata = {
                'duration': duration,
                'sample_rate': sr,
                'channels': 1,  # mono로 변환
                'total_samples': len(y),
                'file_size': os.path.getsize(audio_path) if os.path.exists(audio_path) else 0
            }
            
            # 오디오 품질 평가
            if len(y) > 0:
                metadata['snr'] = self._calculate_snr(y)
                metadata['energy_mean'] = np.mean(np.abs(y))
                metadata['energy_std'] = np.std(np.abs(y))
            
            return metadata
            
        except Exception as e:
            logger.error(f"오디오 메타데이터 추출 실패: {e}")
            return {'duration': 0, 'sample_rate': 16000}
    
    def _calculate_snr(self, audio: np.ndarray) -> float:
        """신호 대 잡음비 계산"""
        try:
            # 간단한 SNR 추정
            signal_power = np.mean(audio ** 2)
            noise_floor = np.percentile(np.abs(audio), 10) ** 2
            
            if noise_floor > 0:
                snr = 10 * np.log10(signal_power / noise_floor)
                return max(0, min(snr, 40))  # 0-40dB 범위
            return 20.0  # 기본값
            
        except:
            return 20.0
    
    async def _upload_to_storage(self, audio_path: str) -> str:
        """Firebase Storage 또는 Google Cloud Storage에 업로드 (PCM 변환 포함)"""
        try:
            # 파일 해시로 중복 체크
            file_hash = self._get_file_hash(audio_path)

            # 오디오 형식 변환 (PCM LINEAR16으로)
            converted_path = await self._convert_to_linear16(audio_path)

            # Firebase Storage 우선 시도
            if self.storage_connector:
                gs_uri, blob_name = self.storage_connector.upload_temp_audio(converted_path)

                # Firebase Storage는 로컬 경로를 반환하므로 GCS URI 형식으로 변환
                if not gs_uri.startswith('gs://'):
                    # Google Cloud Storage에 직접 업로드
                    gs_uri = await self._upload_to_gcs(converted_path, file_hash)

                # 임시 변환 파일 삭제
                if converted_path != audio_path:
                    os.unlink(converted_path)

                return gs_uri
            else:
                # Google Cloud Storage 직접 업로드
                gs_uri = await self._upload_to_gcs(converted_path, file_hash)

                # 임시 변환 파일 삭제
                if converted_path != audio_path:
                    os.unlink(converted_path)

                return gs_uri

        except Exception as e:
            logger.error(f"Storage 업로드 실패: {e}")
            raise
    
    async def _upload_to_gcs(self, audio_path: str, file_hash: str) -> str:
        """Google Cloud Storage에 직접 업로드"""
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            
            # 고유한 blob 이름 생성
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = Path(audio_path).name
            blob_name = f"audio/temp/{timestamp}_{file_hash[:8]}_{filename}"
            
            blob = bucket.blob(blob_name)
            
            # 업로드 (재시도 포함)
            with open(audio_path, 'rb') as audio_file:
                blob.upload_from_file(
                    audio_file,
                    retry=retry.Retry(deadline=300)  # 5분 타임아웃
                )
            
            gs_uri = f"gs://{self.bucket_name}/{blob_name}"
            logger.info(f"GCS 업로드 완료: {gs_uri}")
            
            return gs_uri
            
        except Exception as e:
            logger.error(f"GCS 업로드 실패: {e}")
            raise
    
    def _get_file_hash(self, file_path: str) -> str:
        """파일 해시 계산"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()

    async def _convert_to_linear16(self, audio_path: str) -> str:
        """오디오를 LINEAR16 PCM 형식으로 변환"""
        try:
            # 이미 WAV 파일인지 확인
            if audio_path.lower().endswith('.wav'):
                # WAV 파일이어도 형식 확인 및 변환
                audio, sr = librosa.load(audio_path, sr=16000, mono=True)

                # 16-bit PCM으로 변환
                audio_16bit = (audio * 32767).astype(np.int16)

                # 임시 파일로 저장
                temp_path = audio_path.replace('.wav', '_linear16.wav')
                sf.write(temp_path, audio_16bit, 16000, subtype='PCM_16')

                logger.info(f"WAV 파일을 LINEAR16 PCM으로 변환: {temp_path}")
                return temp_path
            else:
                # m4a, mp3 등 다른 형식
                logger.info(f"오디오 형식 변환 시작: {audio_path}")

                # librosa로 로드 (자동으로 디코딩)
                audio, sr = librosa.load(audio_path, sr=16000, mono=True)

                # 16-bit PCM으로 변환
                audio_16bit = (audio * 32767).astype(np.int16)

                # 임시 WAV 파일로 저장
                temp_path = audio_path + '_linear16.wav'
                sf.write(temp_path, audio_16bit, 16000, subtype='PCM_16')

                logger.info(f"오디오를 LINEAR16 PCM으로 변환 완료: {temp_path}")
                return temp_path

        except Exception as e:
            logger.error(f"오디오 변환 실패: {e}")
            # 변환 실패 시 원본 파일 반환
            return audio_path
    
    def _build_recognition_config(
        self,
        sample_rate: int,
        language_code: str,
        enable_word_confidence: bool,
        use_enhanced_model: bool,
        enable_diarization: bool
    ) -> speech.RecognitionConfig:
        """Speech Recognition 설정 구성"""

        # 화자 분리 설정 (2명 고정)
        diarization_config = speech.SpeakerDiarizationConfig(
            enable_speaker_diarization=True,
            min_speaker_count=2,
            max_speaker_count=2,
        )

        # 화자분리 디버깅 로그
        logger.info(f"🎯 화자분리 설정: enable={enable_diarization}, min_speakers=2, max_speakers=2")

        # 기본 설정
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=sample_rate,
            language_code=language_code,
            enable_word_time_offsets=True,
            enable_word_confidence=enable_word_confidence,
            enable_automatic_punctuation=True,
            diarization_config=diarization_config if enable_diarization else None,
            model='latest_long' if use_enhanced_model else 'default',
            use_enhanced=use_enhanced_model,
            # 한국어 특화 설정
            speech_contexts=[
                speech.SpeechContext(
                    phrases=[
                        "우울", "불안", "스트레스", "수면", "피곤",
                        "할머니", "할아버지", "어르신", "손자", "손녀"
                    ],
                    boost=10.0
                )
            ],
            metadata=speech.RecognitionMetadata(
                interaction_type=speech.RecognitionMetadata.InteractionType.DISCUSSION,
                recording_device_type=speech.RecognitionMetadata.RecordingDeviceType.OTHER_INDOOR_DEVICE,
                original_media_type=speech.RecognitionMetadata.OriginalMediaType.AUDIO,
            )
        )
        
        return config
    
    async def _start_long_running_recognition(
        self,
        gs_uri: str,
        config: speech.RecognitionConfig
    ) -> Any:
        """Long Running Recognition 시작"""
        
        audio = speech.RecognitionAudio(uri=gs_uri)
        
        # Long Running 작업 시작
        operation = self.client.long_running_recognize(
            config=config,
            audio=audio,
            retry=retry.Retry(deadline=600)  # 10분 타임아웃
        )
        
        # operation 정보 로깅 (name 속성이 없어도 안전하게 처리)
        operation_id = str(id(operation))  # 객체 ID 사용
        logger.info(f"Long Running Recognition 시작 - Operation ID: {operation_id}")
        
        # 작업 정보 캐싱 (name 대신 객체 ID 사용)
        self.operation_cache[operation_id] = {
            'started_at': datetime.now(),
            'gs_uri': gs_uri,
            'operation': operation  # operation 객체 자체를 저장
        }
        
        return operation
    
    async def _wait_for_operation(self, operation: Any, poll_interval: int = 5) -> Any:
        """Long Running 작업 완료 대기"""
        
        logger.info("작업 진행 상황 모니터링 시작...")
        
        try:
            # result() 메서드를 사용하여 완료 대기 (권장 방식)
            # timeout을 설정하여 최대 30분까지 대기
            result = operation.result(timeout=1800)  # 30분 타임아웃
            logger.info("Long Running Recognition 완료")
            return result
            
        except Exception as e:
            logger.error(f"Speech API 작업 대기 중 오류: {e}")
            # 대체 방법: 폴링을 통한 수동 대기
            try:
                start_time = time.time()
                while True:
                    # done() 메서드가 있는 경우만 사용
                    if hasattr(operation, 'done') and callable(operation.done):
                        if operation.done():
                            break
                    
                    # 타임아웃 체크
                    if time.time() - start_time > 1800:
                        raise TimeoutError("STT 처리 시간 초과 (30분)")
                    
                    await asyncio.sleep(poll_interval)
                
                # 결과 가져오기
                if hasattr(operation, 'result'):
                    result = operation.result()
                    logger.info("Long Running Recognition 완료 (폴백 방식)")
                    return result
                else:
                    raise RuntimeError("Operation 객체에 result() 메서드가 없습니다")
                    
            except Exception as fallback_error:
                logger.error(f"폴백 방식도 실패: {fallback_error}")
                raise
    
    def _process_diarization_result(
        self,
        result: Any,
        audio_metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """화자 분리 결과 처리"""

        segments = []
        full_transcript = []
        speaker_stats = {}

        # 🔍 상세 디버깅: API 응답 구조 분석
        logger.info(f"🔍 API 응답 분석: result.results 개수={len(result.results) if hasattr(result, 'results') and result.results else 0}")

        if not hasattr(result, 'results') or not result.results:
            logger.error("⚠️ result.results가 없거나 비어있음")
            return {
                'status': 'error',
                'segments': [],
                'speakers': {},
                'transcript': '',
                'error': 'API 결과에 results 속성이 없음'
            }

        # 각 결과 처리
        for i, result_item in enumerate(result.results):
            alternative = result_item.alternatives[0] if result_item.alternatives else None

            logger.info(f"🔍 결과 {i}: alternatives 개수={len(result_item.alternatives) if result_item.alternatives else 0}")

            if not alternative:
                logger.warning(f"⚠️ 결과 {i}에 alternative가 없음")
                continue

            # 화자별 단어 처리
            current_speaker = None
            current_segment = None

            words_count = len(alternative.words) if alternative.words else 0
            logger.info(f"🔍 결과 {i}: 단어 수={words_count}")

            if words_count == 0:
                logger.warning(f"⚠️ 결과 {i}에 단어가 없음")
                continue

            # 화자분리 디버깅: 첫 번째 단어의 모든 속성 확인
            if i == 0 and alternative.words:
                first_word = alternative.words[0]
                word_attrs = [attr for attr in dir(first_word) if not attr.startswith('_')]
                logger.info(f"🎯 첫 단어의 모든 속성: {word_attrs}")
                logger.info(f"🎯 speaker_tag 존재 여부: {'speaker_tag' in word_attrs}")
                if hasattr(first_word, 'speaker_tag'):
                    logger.info(f"🎯 첫 단어 speaker_tag 값: {first_word.speaker_tag}")
                else:
                    logger.warning("🚨 speaker_tag 속성이 없음 - 화자분리 설정 확인 필요")

            # 처음 몇 개 단어의 speaker_tag 확인 (디버깅용)
            for j, word in enumerate(alternative.words[:5]):
                speaker_tag = getattr(word, 'speaker_tag', None)
                word_attrs = [attr for attr in dir(word) if not attr.startswith('_')] if speaker_tag is None else []
                logger.info(f"🔍 단어 {j}: '{word.word}' speaker_tag={speaker_tag}" +
                           (f" 속성: {word_attrs}" if word_attrs else ""))

            for word_info in alternative.words:
                speaker_tag = getattr(word_info, 'speaker_tag', None)
                logger.debug(f"단어: {word_info.word}, speaker_tag: {speaker_tag}")

                if speaker_tag is None:
                    logger.warning(f"단어 '{word_info.word}'에 speaker_tag가 없음")
                    continue
                
                # 화자 변경 감지
                if speaker_tag != current_speaker:
                    # 이전 세그먼트 저장
                    if current_segment:
                        segments.append(current_segment)
                    
                    # 새 세그먼트 시작
                    current_speaker = speaker_tag
                    current_segment = {
                        'speaker_id': speaker_tag,
                        'text': word_info.word,
                        'start_time': word_info.start_time.total_seconds(),
                        'end_time': word_info.end_time.total_seconds(),
                        'confidence': word_info.confidence if hasattr(word_info, 'confidence') else 1.0,
                        'words': [word_info.word]
                    }
                    
                    # 화자 통계 업데이트
                    if speaker_tag not in speaker_stats:
                        speaker_stats[speaker_tag] = {
                            'total_duration': 0,
                            'word_count': 0,
                            'segment_count': 0,
                            'avg_confidence': []
                        }
                    speaker_stats[speaker_tag]['segment_count'] += 1
                    
                else:
                    # 현재 세그먼트에 단어 추가
                    if current_segment:
                        current_segment['text'] += ' ' + word_info.word
                        current_segment['words'].append(word_info.word)
                        current_segment['end_time'] = word_info.end_time.total_seconds()
                
                # 화자 통계 업데이트
                if speaker_tag in speaker_stats:
                    speaker_stats[speaker_tag]['word_count'] += 1
                    if hasattr(word_info, 'confidence'):
                        speaker_stats[speaker_tag]['avg_confidence'].append(word_info.confidence)
            
            # 마지막 세그먼트 저장
            if current_segment:
                segments.append(current_segment)
            
            # 전체 텍스트
            full_transcript.append(alternative.transcript)
        
        # 세그먼트 후처리
        for segment in segments:
            segment['duration'] = segment['end_time'] - segment['start_time']
        
        # 화자 통계 계산
        for speaker_id, stats in speaker_stats.items():
            stats['total_duration'] = sum(
                seg['duration'] for seg in segments if seg['speaker_id'] == speaker_id
            )
            stats['avg_confidence'] = np.mean(stats['avg_confidence']) if stats['avg_confidence'] else 1.0
            stats['speaking_rate'] = stats['word_count'] / max(stats['total_duration'], 1)
        
        # 디버깅 로그 추가
        logger.info(f"화자분리 결과: segments={len(segments)}, speakers={len(speaker_stats)}")
        if len(segments) == 0:
            logger.warning("⚠️ 화자분리 결과가 비어있음!")
            logger.warning(f"전체 결과 수: {len(result.results)}")
            for i, result_item in enumerate(result.results):
                if result_item.alternatives:
                    alt = result_item.alternatives[0]
                    logger.warning(f"결과 {i}: transcript='{alt.transcript}', words={len(alt.words)}")
                    if alt.words:
                        word_sample = alt.words[0]
                        logger.warning(f"첫 번째 단어 속성: {dir(word_sample)}")
                        logger.warning(f"speaker_tag 존재여부: {hasattr(word_sample, 'speaker_tag')}")

        return {
            'status': 'success',
            'segments': segments,
            'transcript': ' '.join(full_transcript),
            'speaker_stats': speaker_stats,
            'total_segments': len(segments),
            'total_speakers': len(speaker_stats)
        }
    
    def _validate_speaker_separation(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """화자 분리 결과 검증 및 보정"""
        
        segments = result.get('segments', [])
        speaker_stats = result.get('speaker_stats', {})
        
        # 1. 최소 발화 시간 체크 (너무 짧은 세그먼트 병합)
        MIN_SEGMENT_DURATION = 0.5  # 0.5초
        merged_segments = []
        
        for i, segment in enumerate(segments):
            if segment['duration'] < MIN_SEGMENT_DURATION and i > 0:
                # 이전 세그먼트와 같은 화자면 병합
                if merged_segments and merged_segments[-1]['speaker_id'] == segment['speaker_id']:
                    merged_segments[-1]['text'] += ' ' + segment['text']
                    merged_segments[-1]['end_time'] = segment['end_time']
                    merged_segments[-1]['duration'] = (
                        merged_segments[-1]['end_time'] - merged_segments[-1]['start_time']
                    )
                    merged_segments[-1]['words'].extend(segment.get('words', []))
                else:
                    merged_segments.append(segment)
            else:
                merged_segments.append(segment)
        
        # 2. 화자 균형 체크
        if len(speaker_stats) == 2:
            durations = [stats['total_duration'] for stats in speaker_stats.values()]
            ratio = min(durations) / max(durations) if max(durations) > 0 else 0
            
            # 너무 불균형한 경우 경고
            if ratio < 0.1:
                logger.warning(f"화자 간 발화 시간 불균형 감지: {ratio:.2%}")
                result['validation_warnings'] = result.get('validation_warnings', [])
                result['validation_warnings'].append('speaker_imbalance')
        
        # 3. 신뢰도 기반 필터링
        MIN_CONFIDENCE = 0.5
        filtered_segments = [
            seg for seg in merged_segments 
            if seg.get('confidence', 1.0) >= MIN_CONFIDENCE
        ]
        
        # 4. 화자 일관성 체크 (급격한 화자 전환 검증)
        for i in range(1, len(filtered_segments) - 1):
            prev_speaker = filtered_segments[i-1]['speaker_id']
            curr_speaker = filtered_segments[i]['speaker_id']
            next_speaker = filtered_segments[i+1]['speaker_id']
            
            # 너무 짧은 중간 발화는 의심
            if (prev_speaker == next_speaker and 
                prev_speaker != curr_speaker and 
                filtered_segments[i]['duration'] < 1.0):
                
                # 화자 태그 수정 고려
                logger.debug(f"화자 일관성 의심 구간 감지: {i}번째 세그먼트")
        
        result['segments'] = filtered_segments
        result['validation_status'] = 'validated'
        result['validation_confidence'] = self._calculate_overall_confidence(result)
        
        return result
    
    def _calculate_overall_confidence(self, result: Dict[str, Any]) -> float:
        """전체 신뢰도 계산"""
        
        segments = result.get('segments', [])
        if not segments:
            return 0.0
        
        # 세그먼트 신뢰도 가중 평균 (duration 기반)
        total_duration = sum(seg['duration'] for seg in segments)
        if total_duration == 0:
            return 0.0
        
        weighted_confidence = sum(
            seg.get('confidence', 1.0) * seg['duration'] 
            for seg in segments
        )
        
        return weighted_confidence / total_duration
    
    async def _cleanup_storage(self, gs_uri: str):
        """임시 Storage 파일 정리"""
        try:
            if 'temp/' in gs_uri:
                # GCS에서 삭제
                bucket_name = gs_uri.split('/')[2]
                blob_name = '/'.join(gs_uri.split('/')[3:])
                
                bucket = self.storage_client.bucket(bucket_name)
                blob = bucket.blob(blob_name)
                blob.delete()
                
                logger.info(f"임시 파일 삭제 완료: {gs_uri}")
        except Exception as e:
            logger.warning(f"임시 파일 삭제 실패: {e}")


class OpenAIConnector:
    """OpenAI GPT-4o API 연동"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            api_key: OpenAI API 키
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        
        if not self.api_key:
            raise ValueError("OpenAI API 키가 필요합니다")
        
        # OpenAI 클라이언트 초기화 (1.51.0 동기 버전 사용)
        self.client = OpenAI(api_key=self.api_key)
        
        logger.info("OpenAI API 연동 초기화 완료")
    
    async def analyze_text(
        self,
        text: str,
        context: Optional[Dict] = None,
        model: str = "gpt-4o"
    ) -> Dict[str, Any]:
        """
        텍스트 감정 및 의미 분석
        
        Args:
            text: 분석할 텍스트
            context: 추가 컨텍스트
            model: 사용할 모델
            
        Returns:
            분석 결과
        """
        
        try:
            # 시스템 프롬프트 구성
            system_prompt = self._build_system_prompt()
            
            # 사용자 프롬프트 구성
            user_prompt = self._build_user_prompt(text, context)
            
            # API 호출
            # 동기 클라이언트를 비동기로 실행
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
                )
            )
            
            # 응답 파싱
            result = json.loads(response.choices[0].message.content)
            
            return {
                'status': 'success',
                'analysis': result,
                'model': model,
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"OpenAI API 호출 실패: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'analysis': {}
            }
    
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 구성"""
        
        return """당신은 시니어 정신건강 분석 전문가입니다.
        
        주어진 텍스트를 분석하여 다음 지표들을 평가해주세요:
        1. DRI (우울 위험 지수): 우울증 관련 언어 패턴
        2. SDI (수면 장애 지수): 수면 문제 관련 표현
        3. CFL (인지 기능 수준): 인지 능력 및 언어 구성력
        4. ES (정서 안정성): 감정 변화 및 안정성
        5. OV (전반적 활력): 에너지 및 활동성
        
        각 지표는 0-1 사이의 값으로 평가하며, 높을수록 긍정적입니다.
        
        JSON 형식으로 응답해주세요:
        {
            "indicators": {
                "DRI": 0.0-1.0,
                "SDI": 0.0-1.0,
                "CFL": 0.0-1.0,
                "ES": 0.0-1.0,
                "OV": 0.0-1.0
            },
            "sentiment": {
                "positive": 0.0-1.0,
                "negative": 0.0-1.0,
                "neutral": 0.0-1.0
            },
            "emotions": {
                "joy": 0.0-1.0,
                "sadness": 0.0-1.0,
                "anger": 0.0-1.0,
                "fear": 0.0-1.0,
                "surprise": 0.0-1.0
            },
            "key_topics": ["주제1", "주제2"],
            "concerns": ["우려사항1", "우려사항2"],
            "coherence_score": 0.0-1.0,
            "interpretation": "종합 해석"
        }"""
    
    def _build_user_prompt(self, text: str, context: Optional[Dict]) -> str:
        """사용자 프롬프트 구성"""
        
        prompt = f"다음 시니어의 발화를 분석해주세요:\n\n{text}"
        
        if context:
            prompt += f"\n\n추가 정보:\n"
            if context.get('age'):
                prompt += f"- 연령: {context['age']}세\n"
            if context.get('gender'):
                prompt += f"- 성별: {context['gender']}\n"
            if context.get('previous_analysis'):
                prompt += f"- 이전 분석 기록 있음\n"
        
        return prompt


class XAIConnector:
    """XAI (Grok) API 연동"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            api_key: XAI API 키
        """
        self.api_key = api_key or os.getenv('XAI_API_KEY')
        self.base_url = "https://api.x.ai/v1"
        self.model = "grok-4-0709"
        
        if not self.api_key:
            logger.warning("XAI API 키가 없습니다 - OpenAI로 fallback됩니다")
            self.client = None
        else:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                api_key=self.api_key,
                base_url=self.base_url
            )
            logger.info("XAI (Grok) API 연동 초기화 완료")
    
    async def analyze_text(
        self,
        text: str,
        context: Optional[Dict] = None,
        model: str = "grok-4-0709"
    ) -> Dict[str, Any]:
        """
        텍스트 감정 및 의미 분석
        
        Args:
            text: 분석할 텍스트
            context: 추가 컨텍스트
            model: 사용할 모델
            
        Returns:
            분석 결과
        """
        
        if not self.client:
            raise ValueError("XAI API가 초기화되지 않았습니다")
        
        try:
            # 시스템 프롬프트 구성
            system_prompt = self._build_system_prompt()
            
            # 사용자 프롬프트 구성
            user_prompt = self._build_user_prompt(text, context)
            
            # API 호출
            # 동기 클라이언트를 비동기로 실행
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.3,
                max_tokens=2000,
                response_format={"type": "json_object"}
                )
            )
            
            # 응답 파싱
            result = json.loads(response.choices[0].message.content)
            
            return {
                'status': 'success',
                'analysis': result,
                'model': model,
                'provider': 'xai',
                'usage': {
                    'prompt_tokens': response.usage.prompt_tokens,
                    'completion_tokens': response.usage.completion_tokens,
                    'total_tokens': response.usage.total_tokens
                }
            }
            
        except Exception as e:
            logger.error(f"XAI API 호출 실패: {e}")
            raise  # 상위에서 fallback 처리
    
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 구성"""
        
        return """당신은 시니어 정신건강 분석 전문가입니다.
        
        주어진 텍스트를 분석하여 다음 지표들을 평가해주세요:
        1. DRI (우울 위험 지수): 우울증 관련 언어 패턴
        2. SDI (수면 장애 지수): 수면 문제 관련 표현
        3. CFL (인지 기능 수준): 인지 능력 및 언어 구성력
        4. ES (정서 안정성): 감정 변화 및 안정성
        5. OV (전반적 활력): 에너지 및 활동성
        
        각 지표는 0-1 사이의 값으로 평가하며, 높을수록 긍정적입니다.
        
        JSON 형식으로 응답해주세요:
        {
            "indicators": {
                "DRI": 0.0-1.0,
                "SDI": 0.0-1.0,
                "CFL": 0.0-1.0,
                "ES": 0.0-1.0,
                "OV": 0.0-1.0
            },
            "sentiment": {
                "positive": 0.0-1.0,
                "negative": 0.0-1.0,
                "neutral": 0.0-1.0
            },
            "emotions": {
                "joy": 0.0-1.0,
                "sadness": 0.0-1.0,
                "anger": 0.0-1.0,
                "fear": 0.0-1.0,
                "surprise": 0.0-1.0
            },
            "key_topics": ["주제1", "주제2"],
            "concerns": ["우려사항1", "우려사항2"],
            "coherence_score": 0.0-1.0,
            "interpretation": "종합 해석"
        }"""
    
    def _build_user_prompt(self, text: str, context: Optional[Dict]) -> str:
        """사용자 프롬프트 구성"""
        
        prompt = f"다음 시니어의 발화를 분석해주세요:\n\n{text}"
        
        if context:
            prompt += f"\n\n추가 정보:\n"
            if context.get('age'):
                prompt += f"- 연령: {context['age']}세\n"
            if context.get('gender'):
                prompt += f"- 성별: {context['gender']}\n"
            if context.get('previous_analysis'):
                prompt += f"- 이전 분석 기록 있음\n"
        
        return prompt


class GeminiConnector:
    """Google Gemini API 연동"""
    
    def __init__(self, api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            api_key: Google Gemini API 키
        """
        self.api_key = api_key or os.getenv('GEMINI_API_KEY')
        
        if not self.api_key:
            logger.warning("Gemini API 키가 없습니다 - OpenAI로 fallback됩니다")
            self.client = None
        else:
            genai.configure(api_key=self.api_key)
            self.client = genai.GenerativeModel('gemini-1.5-pro')
            logger.info("Gemini API 연동 초기화 완료")
    
    async def analyze_text(
        self,
        text: str,
        context: Optional[Dict] = None,
        model: str = "gemini-1.5-pro"
    ) -> Dict[str, Any]:
        """
        텍스트 감정 및 의미 분석
        
        Args:
            text: 분석할 텍스트
            context: 추가 컨텍스트
            model: 사용할 모델
            
        Returns:
            분석 결과
        """
        
        if not self.client:
            raise ValueError("Gemini API가 초기화되지 않았습니다")
        
        try:
            # 시스템 프롬프트 구성
            system_prompt = self._build_system_prompt()
            
            # 사용자 프롬프트 구성
            user_prompt = self._build_user_prompt(text, context)
            
            # 전체 프롬프트 조합
            full_prompt = f"{system_prompt}\n\n{user_prompt}"
            
            # Gemini API 호출
            response = await asyncio.to_thread(
                self.client.generate_content,
                full_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=2000,
                )
            )
            
            # 응답 파싱
            try:
                result = json.loads(response.text)
            except json.JSONDecodeError:
                # JSON 파싱 실패 시 텍스트에서 JSON 추출 시도
                result = self._extract_json_from_text(response.text)
            
            return {
                'status': 'success',
                'analysis': result,
                'model': model,
                'provider': 'gemini',
                'usage': {
                    'prompt_tokens': len(full_prompt.split()),
                    'completion_tokens': len(response.text.split()),
                    'total_tokens': len(full_prompt.split()) + len(response.text.split())
                }
            }
            
        except Exception as e:
            logger.error(f"Gemini API 호출 실패: {e}")
            raise  # 상위에서 fallback 처리
    
    def _build_system_prompt(self) -> str:
        """시스템 프롬프트 구성"""
        
        return """당신은 시니어 정신건강 분석 전문가입니다.

주어진 텍스트를 분석하여 다음 지표들을 평가해주세요:
1. DRI (우울 위험 지수): 우울증 관련 언어 패턴
2. SDI (수면 장애 지수): 수면 문제 관련 표현
3. CFL (인지 기능 수준): 인지 능력 및 언어 구성력
4. ES (정서 안정성): 감정 변화 및 안정성
5. OV (전반적 활력): 에너지 및 활동성

각 지표는 0-1 사이의 값으로 평가하며, 높을수록 긍정적입니다.

JSON 형식으로만 응답해주세요:
{
    "indicators": {
        "DRI": 0.0-1.0,
        "SDI": 0.0-1.0,
        "CFL": 0.0-1.0,
        "ES": 0.0-1.0,
        "OV": 0.0-1.0
    },
    "sentiment": {
        "positive": 0.0-1.0,
        "negative": 0.0-1.0,
        "neutral": 0.0-1.0
    },
    "emotions": {
        "joy": 0.0-1.0,
        "sadness": 0.0-1.0,
        "anger": 0.0-1.0,
        "fear": 0.0-1.0,
        "surprise": 0.0-1.0
    },
    "key_topics": ["주제1", "주제2"],
    "concerns": ["우려사항1", "우려사항2"],
    "coherence_score": 0.0-1.0,
    "interpretation": "종합 해석"
}"""
    
    def _build_user_prompt(self, text: str, context: Optional[Dict]) -> str:
        """사용자 프롬프트 구성"""
        
        prompt = f"다음 시니어의 발화를 분석해주세요:\n\n{text}"
        
        if context:
            prompt += f"\n\n추가 정보:\n"
            if context.get('age'):
                prompt += f"- 연령: {context['age']}세\n"
            if context.get('gender'):
                prompt += f"- 성별: {context['gender']}\n"
            if context.get('previous_analysis'):
                prompt += f"- 이전 분석 기록 있음\n"
        
        return prompt
    
    def _extract_json_from_text(self, text: str) -> Dict[str, Any]:
        """텍스트에서 JSON 추출"""
        try:
            # JSON 블록 찾기
            import re
            json_match = re.search(r'\{.*\}', text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # 기본 구조 반환
                return {
                    "indicators": {
                        "DRI": 0.5, "SDI": 0.5, "CFL": 0.5, "ES": 0.5, "OV": 0.5
                    },
                    "sentiment": {"positive": 0.3, "negative": 0.3, "neutral": 0.4},
                    "emotions": {
                        "joy": 0.2, "sadness": 0.2, "anger": 0.1, "fear": 0.1, "surprise": 0.1
                    },
                    "key_topics": ["일반적 대화"],
                    "concerns": [],
                    "coherence_score": 0.7,
                    "interpretation": "JSON 파싱 실패로 인한 기본값"
                }
        except:
            return {
                "indicators": {
                    "DRI": 0.5, "SDI": 0.5, "CFL": 0.5, "ES": 0.5, "OV": 0.5
                },
                "sentiment": {"positive": 0.3, "negative": 0.3, "neutral": 0.4},
                "emotions": {
                    "joy": 0.2, "sadness": 0.2, "anger": 0.1, "fear": 0.1, "surprise": 0.1
                },
                "key_topics": ["파싱 오류"],
                "concerns": [],
                "coherence_score": 0.5,
                "interpretation": "응답 파싱 실패"
            }


class MultiLLMConnector:
    """다중 LLM API 연동 (XAI 1순위, OpenAI 2순위, Gemini 3순위)"""
    
    def __init__(self, xai_api_key: Optional[str] = None, openai_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None):
        """
        초기화
        
        Args:
            xai_api_key: XAI API 키
            openai_api_key: OpenAI API 키
            gemini_api_key: Gemini API 키
        """
        # XAI 커넥터 초기화 (1순위)
        try:
            self.xai_connector = XAIConnector(xai_api_key)
            self.xai_available = self.xai_connector.client is not None
        except Exception as e:
            logger.warning(f"XAI 커넥터 초기화 실패: {e}")
            self.xai_connector = None
            self.xai_available = False
        
        # OpenAI 커넥터 초기화 (2순위)
        try:
            self.openai_connector = OpenAIConnector(openai_api_key)
            self.openai_available = self.openai_connector.client is not None
        except Exception as e:
            logger.warning(f"OpenAI 커넥터 초기화 실패: {e}")
            self.openai_connector = None
            self.openai_available = False
        
        # Gemini 커넥터 초기화 (3순위)
        try:
            self.gemini_connector = GeminiConnector(gemini_api_key)
            self.gemini_available = self.gemini_connector.client is not None
        except Exception as e:
            logger.warning(f"Gemini 커넥터 초기화 실패: {e}")
            self.gemini_connector = None
            self.gemini_available = False
        
        # 사용 가능한 API 체크
        if not self.xai_available and not self.openai_available and not self.gemini_available:
            raise ValueError("XAI, OpenAI, Gemini API 모두 사용할 수 없습니다")
        
        logger.info(f"MultiLLM 초기화 완료 - XAI: {self.xai_available}, OpenAI: {self.openai_available}, Gemini: {self.gemini_available}")
    
    async def analyze_text(
        self,
        text: str,
        context: Optional[Dict] = None,
        force_model: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        텍스트 분석 (XAI 1순위, OpenAI 2순위, Gemini 3순위)
        
        Args:
            text: 분석할 텍스트
            context: 추가 컨텍스트
            force_model: 강제 사용 모델 ('xai', 'openai', 'gemini')
            
        Returns:
            분석 결과
        """
        
        # 특정 모델 강제 사용
        if force_model:
            if force_model == 'xai' and self.xai_available:
                logger.info("XAI 강제 사용 모드")
                return await self.xai_connector.analyze_text(text, context)
            elif force_model == 'openai' and self.openai_available:
                logger.info("OpenAI 강제 사용 모드")
                return await self.openai_connector.analyze_text(text, context)
            elif force_model == 'gemini' and self.gemini_available:
                logger.info("Gemini 강제 사용 모드")
                return await self.gemini_connector.analyze_text(text, context)
        
        # XAI 우선 시도 (1순위)
        if self.xai_available:
            try:
                logger.info("XAI (Grok) API 시도 중...")
                result = await self.xai_connector.analyze_text(text, context)
                logger.info("XAI (Grok) API 성공")
                return result
                
            except Exception as e:
                logger.warning(f"XAI API 실패, OpenAI로 fallback: {e}")
                
                # OpenAI fallback (2순위)
                if self.openai_available:
                    try:
                        logger.info("OpenAI API fallback 시도 중...")
                        result = await self.openai_connector.analyze_text(text, context)
                        result['fallback_used'] = True
                        result['fallback_reason'] = str(e)
                        logger.info("OpenAI API fallback 성공")
                        return result
                    except Exception as openai_error:
                        logger.warning(f"OpenAI fallback 실패, Gemini로 시도: {openai_error}")
                        
                        # Gemini fallback (3순위)
                        if self.gemini_available:
                            try:
                                logger.info("Gemini API fallback 시도 중...")
                                result = await self.gemini_connector.analyze_text(text, context)
                                result['fallback_used'] = True
                                result['fallback_level'] = 2
                                result['fallback_reason'] = f"XAI: {e}, OpenAI: {openai_error}"
                                logger.info("Gemini API fallback 성공")
                                return result
                            except Exception as gemini_error:
                                logger.error(f"모든 API 실패: XAI: {e}, OpenAI: {openai_error}, Gemini: {gemini_error}")
                                return self._get_error_response(f"모든 API 실패")
                        else:
                            return self._get_error_response(f"XAI/OpenAI 실패, Gemini 사용 불가")
                else:
                    return self._get_error_response(f"XAI 실패, OpenAI 사용 불가: {e}")
        
        # XAI 사용 불가시 OpenAI 사용 (2순위)
        elif self.openai_available:
            logger.info("XAI 사용 불가, OpenAI 사용")
            try:
                result = await self.openai_connector.analyze_text(text, context)
                result['xai_unavailable'] = True
                return result
            except Exception as e:
                logger.warning(f"OpenAI 실패, Gemini로 fallback: {e}")
                if self.gemini_available:
                    try:
                        result = await self.gemini_connector.analyze_text(text, context)
                        result['fallback_used'] = True
                        return result
                    except Exception as gemini_error:
                        return self._get_error_response(f"OpenAI/Gemini 모두 실패")
                        
        # Gemini만 사용 가능 (3순위)
        elif self.gemini_available:
            logger.info("XAI/OpenAI 사용 불가, Gemini만 사용")
            result = await self.gemini_connector.analyze_text(text, context)
            result['only_gemini'] = True
            return result
        
        else:
            return self._get_error_response("사용 가능한 API가 없습니다")
    
    def _get_error_response(self, error_message: str) -> Dict[str, Any]:
        """에러 응답 생성"""
        return {
            'status': 'error',
            'error': error_message,
            'analysis': {
                "indicators": {
                    "DRI": 0.5, "SDI": 0.5, "CFL": 0.5, "ES": 0.5, "OV": 0.5
                },
                "sentiment": {"positive": 0.3, "negative": 0.3, "neutral": 0.4},
                "emotions": {
                    "joy": 0.2, "sadness": 0.2, "anger": 0.1, "fear": 0.1, "surprise": 0.1
                },
                "key_topics": ["API 오류"],
                "concerns": ["API 연결 실패"],
                "coherence_score": 0.0,
                "interpretation": f"API 오류로 인한 기본값: {error_message}"
            }
        }