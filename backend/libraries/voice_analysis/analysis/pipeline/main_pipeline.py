"""
메인 분석 파이프라인
음성 데이터를 받아 5대 지표를 계산하고 리포트를 생성하는 통합 파이프라인
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from pathlib import Path
import traceback

from ..core import (
    VoiceAnalyzer,
    TextAnalyzer,
    SincNetAnalyzer,
    IndicatorCalculator,
    MentalHealthIndicators
)
from ..core.comprehensive_interpreter import ComprehensiveInterpreter
from ..utils.api_connectors import GoogleCloudSpeechConnector
from ..utils.firestore_connector import FirestoreConnector
from .speaker_identifier import SpeakerIdentifier
from .report_generator import ReportGenerator
from ..timeseries.trend_analyzer import TrendAnalyzer
from ..mental_health.optimized_weight_calculator import (
    OptimizedWeightCalculator,
    DataQuality,
    IndicatorType,
    OptimizedWeights
)

# RAG 통합 모듈 추가
logger = logging.getLogger(__name__)

try:
    from ..rag.core import RAGEnhancedTextAnalyzer, FirebaseStorageVectorStore
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    logger.warning("RAG 모듈 사용 불가 - 기본 텍스트 분석만 사용됩니다")

class SeniorMentalHealthPipeline:
    """시니어 정신건강 분석 파이프라인"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Args:
            config: 파이프라인 설정 (선택적)
        """
        self.config = config or {}

        # 적응형 가중치 시스템 사용 여부 (기본값: True)
        self.config.setdefault('use_adaptive_weights', True)

        # 기본 고정 가중치 (적응형 미사용 시 백업)
        self.default_weights = {
            'voice': 0.3,      # Librosa 음성 특징
            'text': 0.4,       # GPT-4o 텍스트 분석
            'sincnet': 0.3     # SincNet 딥러닝
        }

        # SincNet 기본 활성화
        self.config.setdefault('use_sincnet', True)
        # RAG 옵션 (기본값: False)
        self.config.setdefault('use_rag', False)

        # 가중치 초기화
        self.weights = self.default_weights.copy()
        
        # 분석 컴포넌트 초기화
        self.voice_analyzer = VoiceAnalyzer()
        
        # RAG 강화 텍스트 분석기 또는 기본 텍스트 분석기 선택
        if self.config.get('use_rag') and RAG_AVAILABLE:
            try:
                # RAG 벡터 스토어 초기화
                self.vector_store = FirebaseStorageVectorStore(
                    project_id=self.config.get('project_id', 'senior-mhealth-472007')
                )
                # RAG 강화 텍스트 분석기
                self.text_analyzer = RAGEnhancedTextAnalyzer(
                    use_rag=True,
                    vector_store_config={
                        'project_id': self.config.get('project_id', 'senior-mhealth-472007')
                    }
                )
                logger.info("RAG 강화 텍스트 분석기 초기화 성공")
            except Exception as e:
                logger.warning(f"RAG 초기화 실패, 기본 분석기 사용: {e}")
                self.text_analyzer = TextAnalyzer()
                self.config['use_rag'] = False
        else:
            self.text_analyzer = TextAnalyzer()
            
        self.sincnet_analyzer = SincNetAnalyzer()
        self.indicator_calculator = IndicatorCalculator()
        self.speaker_identifier = SpeakerIdentifier()
        self.report_generator = ReportGenerator()
        self.trend_analyzer = TrendAnalyzer()
        self.comprehensive_interpreter = ComprehensiveInterpreter()

        # 적응형 가중치 계산기 초기화
        if self.config.get('use_adaptive_weights', True):
            self.weight_calculator = OptimizedWeightCalculator(use_rag=self.config.get('use_rag', False))
            logger.info("적응형 가중치 시스템 활성화")
        else:
            self.weight_calculator = None
            logger.info("고정 가중치 모드 사용")

        # Google Cloud STT (고정)
        try:
            import os
            from pathlib import Path

            # Cloud Run에서는 기본 서비스 계정 사용
            if os.getenv('K_SERVICE'):  # Cloud Run 환경 체크
                self.stt_connector = GoogleCloudSpeechConnector(
                    credentials_path=None,  # 기본 인증 사용
                    project_id='senior-mhealth-472007'
                )
                logger.info("Google Cloud STT 초기화 성공 (Cloud Run 기본 인증)")
            else:
                # 로컬 환경에서는 키 파일 사용 - 크로스플랫폼 지원
                try:
                    # Import cross-platform utilities
                    import sys
                    sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
                    from common.path_utils import ServiceAccountResolver

                    credentials_path = ServiceAccountResolver.find_service_account_key()
                except ImportError:
                    # Fallback to old method if import fails
                    credentials_path = Path('/app/serviceAccountKey.json')
                    if not credentials_path.exists():
                        credentials_path = Path(__file__).parent.parent.parent.parent.parent / 'serviceAccountKey.json'

                if credentials_path and credentials_path.exists():
                    self.stt_connector = GoogleCloudSpeechConnector(
                        credentials_path=str(credentials_path),
                        project_id='senior-mhealth-472007'
                    )
                    logger.info(f"Google Cloud STT 초기화 성공: {credentials_path}")
                else:
                    self.stt_connector = None
                    logger.warning(f"서비스 계정 키 파일 없음 - STT 기능 제한됨")
        except Exception as e:
            self.stt_connector = None
            logger.warning(f"Google Cloud 커넥터 초기화 실패: {e}")
        
        # Firestore 연동 (GCP 운영용)
        try:
            self.firestore_connector = FirestoreConnector()
        except:
            self.firestore_connector = None
            logger.warning("Firestore 커넥터 초기화 실패 - 시계열 분석 제한됨")
        
        # 결과 캐시
        self.cache = {}
        
    async def analyze(
        self,
        audio_path: str,
        user_id: Optional[str] = None,
        user_info: Optional[Dict] = None,
        history: Optional[List[Dict]] = None
    ) -> Dict[str, Any]:
        """
        음성 파일 분석 실행
        
        Args:
            audio_path: 오디오 파일 경로
            user_id: 사용자 ID (Firestore 시계열 분석용)
            user_info: 사용자 정보 (나이, 성별 등)
            history: 과거 분석 기록 (로컬 테스트용, user_id가 있으면 무시됨)
            
        Returns:
            종합 분석 결과
        """
        
        start_time = datetime.now()
        result = {
            'status': 'processing',
            'timestamp': start_time.isoformat(),
            'audio_path': audio_path
        }
        
        try:
            # Phase 1: STT 및 화자 식별 (먼저 수행)
            logger.info("Phase 1: 음성-텍스트 변환 및 화자 식별")
            stt_result = await self._perform_stt(audio_path)
            
            senior_audio_path = audio_path  # 기본값은 원본 파일
            
            if stt_result['status'] == 'success':
                # Google Cloud Speech의 화자 통계 활용
                speaker_stats = stt_result.get('speaker_stats', {})
                
                # Google Cloud Speech의 화자 분리 결과 사용
                logger.info("Google Cloud Speech 화자 분리 결과 사용")
                speaker_result = self.speaker_identifier.identify(
                    stt_result['segments'],
                    None,  # 음성 특징은 나중에 분석
                    user_profile=user_info  # 사용자/시니어 프로필 정보 전달
                )
                
                # Google Cloud 통계 정보 병합
                if speaker_stats:
                    speaker_result['gcs_speaker_stats'] = speaker_stats
                    logger.info(f"Google Cloud 화자 통계: {len(speaker_stats)}명 감지")
                    # 각 화자별 세부 통계
                    for speaker_id, stats in speaker_stats.items():
                        word_count = stats.get('word_count', 0)
                        duration = stats.get('speech_duration', 0)
                        logger.info(f"  화자 {speaker_id}: {word_count}단어, {duration:.1f}초 발화")
                
                result['speaker_identification'] = speaker_result
                
                # 시니어 발화만 추출
                senior_text = self._extract_senior_text(
                    stt_result['segments'],
                    speaker_result
                )
                result['transcription'] = senior_text
                
                # 시니어 텍스트 로깅 (디버깅용)
                if senior_text:
                    preview_length = min(500, len(senior_text))
                    logger.info(f"시니어 텍스트 추출 완료: 총 {len(senior_text)}자")
                    logger.info(f"시니어 텍스트 앞부분: {senior_text[:preview_length]}...")
                else:
                    logger.warning("시니어 텍스트가 비어있습니다")
                
                # 시니어 음성 구간만 추출
                extraction_result = self._extract_senior_audio_segments(
                    audio_path,
                    stt_result['segments'],
                    speaker_result
                )
                senior_audio_path = extraction_result['audio_path']
                result['senior_audio_extraction'] = extraction_result
                
                if extraction_result['status'] == 'success':
                    logger.info(f"시니어 음성 추출 성공: {senior_audio_path}")
                else:
                    logger.warning(f"시니어 음성 추출 문제: {extraction_result['message']}")
                
            else:
                result['transcription'] = ""
                result['senior_audio_extraction'] = {
                    'status': 'fallback',
                    'audio_path': audio_path,
                    'message': 'STT 실패로 인한 화자 분리 불가',
                    'reason': 'stt_failed',
                    'segments_extracted': 0,
                    'total_duration': 0,
                    'using_original': True
                }
                logger.warning("STT 실패, 원본 파일로 음성 분석 진행")
            
            # Phase 2: 음성 분석 (시니어 음성으로)
            logger.info("Phase 2: 음성 특징 추출 시작")
            voice_features = await self._analyze_voice(senior_audio_path)
            logger.info(f"Phase 2 완료: 음성 분석 상태 = {voice_features.get('status', 'unknown')}")
            if voice_features.get('status') == 'error':
                logger.error(f"음성 분석 오류: {voice_features.get('error')}")
            result['voice_analysis'] = voice_features
            
            # Phase 3: 텍스트 분석
            if result.get('transcription'):
                logger.info("Phase 3: 텍스트 분석")
                # 분석에 사용될 텍스트 확인
                text_for_analysis = result['transcription']
                logger.info(f"텍스트 분석 입력: {len(text_for_analysis)}자")
                logger.info(f"분석 텍스트 미리보기: {text_for_analysis[:300]}...")
                
                text_analysis = await self.text_analyzer.analyze(
                    text_for_analysis,
                    context=user_info
                )
                result['text_analysis'] = text_analysis
            else:
                result['text_analysis'] = None
            
            # Phase 4: SincNet 분석 (시니어 음성으로)
            if self.config.get('use_sincnet', False):
                logger.info("Phase 4: SincNet 딥러닝 분석 (시니어 음성)")
                try:
                    # CPU 집약적인 동기 함수를 별도 스레드에서 실행
                    import asyncio
                    from concurrent.futures import ThreadPoolExecutor
                    
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        sincnet_result = await loop.run_in_executor(
                            executor,
                            self.sincnet_analyzer.analyze,
                            senior_audio_path
                        )
                    logger.info(f"Phase 4 완료: SincNet 분석 상태 = {sincnet_result.get('status', 'unknown')}")
                    result['sincnet_analysis'] = sincnet_result
                except Exception as e:
                    logger.error(f"SincNet 분석 실패: {e}")
                    result['sincnet_analysis'] = {'status': 'error', 'error': str(e)}
            else:
                result['sincnet_analysis'] = None
            
            # Phase 5: 5대 지표 계산 (적응형 가중치 적용)
            logger.info("Phase 5: 정신건강 지표 계산")
            try:
                # 적응형 가중치 계산
                adaptive_weights = None
                confidence_scores = None

                if self.weight_calculator and self.config.get('use_adaptive_weights', True):
                    logger.info("Phase 5-1: 데이터 품질 평가 및 적응형 가중치 계산")

                    # 데이터 품질 평가
                    data_quality = DataQuality.from_analysis_results(
                        voice_analysis=voice_features,
                        text_analysis=result.get('text_analysis'),
                        audio_path=audio_path
                    )

                    # 적응형 가중치 계산
                    adaptive_weights = self.weight_calculator.calculate_adaptive_weights(
                        data_quality=data_quality,
                        user_profile=user_info
                    )

                    # 신뢰도 계산
                    confidence_scores = self.weight_calculator.calculate_confidence(
                        weights=adaptive_weights,
                        data_quality=data_quality
                    )

                    result['data_quality'] = {
                        'voice_quality': data_quality.voice_quality,
                        'text_quality': data_quality.text_quality,
                        'deep_quality': data_quality.deep_quality,
                        'audio_duration': data_quality.audio_duration,
                        'text_length': data_quality.text_length
                    }

                    result['adaptive_weights'] = {
                        indicator.value: {
                            'voice': weight.voice,
                            'text': weight.text,
                            'deep': weight.deep
                        }
                        for indicator, weight in adaptive_weights.items()
                    }

                    result['confidence_scores'] = {
                        indicator.value: score
                        for indicator, score in confidence_scores.items()
                    }

                    logger.info(f"적응형 가중치 적용: {result['adaptive_weights']}")

                # CPU 집약적인 동기 함수를 별도 스레드에서 실행
                import asyncio
                from concurrent.futures import ThreadPoolExecutor

                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    indicators = await loop.run_in_executor(
                        executor,
                        lambda: self.indicator_calculator.calculate(
                            voice_features=voice_features.get('features'),
                            text_analysis=result.get('text_analysis'),
                            sincnet_results=result.get('sincnet_analysis'),
                            adaptive_weights=adaptive_weights  # 적응형 가중치 전달
                        )
                    )
                logger.info("Phase 5 완료: 정신건강 지표 계산 성공")
                result['indicators'] = indicators.to_dict()
                
                # Phase 6: 위험도 평가
                logger.info("Phase 6: 위험도 평가")
                with ThreadPoolExecutor(max_workers=1) as executor:
                    risk_assessment = await loop.run_in_executor(
                        executor,
                        self.indicator_calculator.calculate_risk_scores,
                        indicators
                    )
                logger.info("Phase 6 완료: 위험도 평가 성공")
                result['risk_assessment'] = risk_assessment
            except Exception as e:
                logger.error(f"지표 계산/위험도 평가 실패: {e}")
                import traceback
                logger.error(f"Traceback: {traceback.format_exc()}")
                result['indicators'] = None
                result['risk_assessment'] = None
            
            # Phase 7: 시계열 분석
            logger.info("Phase 7: 시계열 추세 분석")
            if user_id and self.firestore_connector:
                # GCP 운영 환경: Firestore에서 과거 기록 조회
                logger.info("Firestore에서 과거 분석 기록 조회")
                firestore_history = self.firestore_connector.get_user_analysis_history(user_id, days_back=30)
                
                if len(firestore_history) >= 2:  # 최소 2개 이상의 기록 필요
                    # 현재 결과 추가
                    current_record = {
                        'analysis_timestamp': start_time.isoformat(),
                        'indicators': indicators.to_dict() if indicators else None
                    }
                    firestore_history.append(current_record)
                    
                    # 동기 함수를 별도 스레드에서 실행
                    import asyncio
                    from concurrent.futures import ThreadPoolExecutor
                    
                    loop = asyncio.get_event_loop()
                    with ThreadPoolExecutor(max_workers=1) as executor:
                        trend_result = await loop.run_in_executor(
                            executor,
                            self.trend_analyzer.analyze_trends,
                            firestore_history
                        )
                    logger.info("Phase 7 완료: 시계열 분석 성공")
                    result['trend_analysis'] = trend_result
                else:
                    logger.info("시계열 분석을 위한 충분한 과거 기록이 없습니다")
                    result['trend_analysis'] = None
                    
            elif history and len(history) > 0:
                # 로컬 테스트 환경: 전달받은 history 사용
                logger.info("로컬 테스트: 전달받은 history로 시계열 분석")
                # 현재 결과를 기록에 추가
                history.append({
                    'analysis_timestamp': start_time.isoformat(),
                    'indicators': indicators.to_dict() if indicators else None
                })
                
                # 동기 함수를 별도 스레드에서 실행
                import asyncio
                from concurrent.futures import ThreadPoolExecutor
                
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    trend_result = await loop.run_in_executor(
                        executor,
                        self.trend_analyzer.analyze_trends,
                        history
                    )
                logger.info("Phase 7 완료: 시계열 분석 성공 (로컬)")
                result['trend_analysis'] = trend_result
            else:
                logger.info("시계열 분석을 위한 데이터가 없습니다")
                result['trend_analysis'] = None
            
            # Phase 8: AI 종합 해석
            logger.info("Phase 8: AI 종합 해석")
            comprehensive_analysis = {
                'voice_analysis': voice_features.get('features'),
                'text_analysis': result.get('text_analysis'),
                'indicators': indicators.to_dict(),
                'clinical_validation': risk_assessment,
                'trend_analysis': result.get('trend_analysis')
            }
            
            # AI 종합 해석 수행
            interpretation = await self.comprehensive_interpreter.interpret(comprehensive_analysis)
            result['comprehensive_interpretation'] = interpretation
            
            # Phase 9: 리포트 생성
            logger.info("Phase 9: 종합 리포트 생성")
            try:
                # 동기 함수를 별도 스레드에서 실행
                import asyncio
                from concurrent.futures import ThreadPoolExecutor
                
                loop = asyncio.get_event_loop()
                with ThreadPoolExecutor(max_workers=1) as executor:
                    report = await loop.run_in_executor(
                        executor,
                        self.report_generator.generate,
                        indicators,
                        risk_assessment,
                        result.get('trend_analysis'),
                        user_info
                    )
                logger.info("Phase 9 완료: 리포트 생성 성공")
                result['report'] = report
            except Exception as e:
                logger.error(f"리포트 생성 실패: {e}")
                result['report'] = None
            
            # Phase 10: 새로운 스키마 형식으로 변환
            logger.info("Phase 10: 개선된 스키마 형식으로 변환")
            result = self._format_to_improved_schema(
                result=result,
                indicators=indicators,
                voice_features=voice_features,
                text_analysis=result.get('text_analysis'),
                sincnet_result=result.get('sincnet_analysis'),
                interpretation=interpretation,
                risk_assessment=risk_assessment,
                start_time=start_time
            )
            
            # 처리 시간 계산
            processing_time = (datetime.now() - start_time).total_seconds()
            result['metadata']['processing']['totalTime'] = processing_time * 1000  # ms로 변환
            result['status'] = 'completed'
            
            # GCP 운영 환경: 분석 결과를 Firestore에 저장
            if user_id and self.firestore_connector:
                logger.info("분석 결과를 Firestore에 저장")
                save_success = self.firestore_connector.save_analysis_result(
                    user_id=user_id,
                    analysis_result=result,
                    audio_path=audio_path
                )
                result['saved_to_firestore'] = save_success
            
            logger.info(f"분석 완료: {processing_time:.2f}초 소요")
            
        except Exception as e:
            logger.error(f"파이프라인 실행 중 오류: {e}")
            logger.error(traceback.format_exc())
            result['status'] = 'error'
            result['error'] = str(e)
            result['traceback'] = traceback.format_exc()
        finally:
            # 임시 파일 정리
            if ('senior_audio_path' in locals() and 
                senior_audio_path != audio_path and 
                result.get('senior_audio_extraction', {}).get('temp_file_created', False)):
                try:
                    import os
                    if os.path.exists(senior_audio_path):
                        os.unlink(senior_audio_path)
                        logger.info(f"임시 파일 삭제: {senior_audio_path}")
                except Exception as cleanup_error:
                    logger.warning(f"임시 파일 삭제 실패: {cleanup_error}")
        
        return result
    
    async def _analyze_voice(self, audio_path: str) -> Dict[str, Any]:
        """음성 분석 실행 (타임아웃 관리 추가)"""
        import asyncio
        from concurrent.futures import ThreadPoolExecutor
        from pathlib import Path
        
        try:
            # 파일 크기에 따른 동적 타임아웃 설정
            file_size_mb = Path(audio_path).stat().st_size / (1024 * 1024)
            
            # 타임아웃 계산: 기본 60초 + MB당 20초 (최대 4분)
            timeout_seconds = min(60 + (file_size_mb * 20), 240)
            logger.info(f"음성 분석 타임아웃 설정: {timeout_seconds}초 (파일: {file_size_mb:.1f}MB)")
            
            # CPU 집약적인 동기 함수를 별도 스레드에서 실행
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = loop.run_in_executor(
                    executor,
                    self.voice_analyzer.analyze,
                    audio_path
                )
                
                # 타임아웃 적용
                result = await asyncio.wait_for(future, timeout=timeout_seconds)
                
            return result
            
        except asyncio.TimeoutError:
            logger.error(f"음성 분석 타임아웃 ({timeout_seconds}초)")
            # 타임아웃 시 부분 분석 결과 반환
            logger.warning(f"타임아웃으로 부분 분석 결과만 제공: {file_size_mb:.1f}MB 파일")
            return {
                'status': 'partial',
                'features': {},
                'duration': timeout_seconds,
                'analysis_method': 'timeout',
                'error': f'Analysis timeout after {timeout_seconds}s'
            }
            
        except Exception as e:
            logger.error(f"음성 분석 실패: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'status': 'error', 'error': str(e)}
    
    # 비상 분석 함수 제거 - 실패 시 바로 에러 발생
    
    async def _perform_stt(self, audio_path: str) -> Dict[str, Any]:
        """STT 실행"""
        try:
            # Google Cloud STT 사용
            if self.stt_connector:
                result = await self.stt_connector.transcribe_with_diarization(audio_path)
                return result
            else:
                logger.error("STT 커넥터가 초기화되지 않았습니다. Google Cloud 인증을 확인하세요.")
                return {'status': 'error', 'error': 'STT connector not available'}
        except Exception as e:
            logger.error(f"STT 실패: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _extract_senior_text(
        self,
        segments: List[Dict],
        speaker_info: Dict
    ) -> str:
        """시니어 화자의 발화만 추출"""
        import re
        
        senior_speaker_id = speaker_info.get('senior_speaker_id')
        if senior_speaker_id is None:
            # 화자 식별 실패 시 모든 텍스트 반환
            return ' '.join([seg.get('text', '') for seg in segments])
        
        # AI가 반환한 "화자 0" 형식에서 숫자만 추출
        match = re.search(r'화자\s*(\d+)', str(senior_speaker_id))
        if match:
            # 숫자 추출 성공 - STT API의 speaker_tag는 1부터 시작하므로 +1
            senior_speaker_numeric = int(match.group(1)) + 1
        else:
            # 숫자가 아닌 경우 원본 사용
            senior_speaker_numeric = senior_speaker_id
        
        senior_texts = []
        for seg in segments:
            seg_speaker_id = seg.get('speaker_id')
            # 숫자 형식과 문자열 형식 모두 비교
            if (seg_speaker_id == senior_speaker_numeric or 
                str(seg_speaker_id) == str(senior_speaker_numeric) or
                seg_speaker_id == senior_speaker_id):
                senior_texts.append(seg.get('text', ''))
        
        return ' '.join(senior_texts)
    
    def _extract_senior_audio_segments(
        self,
        audio_path: str,
        segments: List[Dict],
        speaker_info: Dict
    ) -> Dict[str, Any]:
        """시니어 화자의 음성 구간만 추출하여 임시 파일로 저장"""
        import librosa
        import soundfile as sf
        import tempfile
        import numpy as np
        from pathlib import Path
        import re
        
        senior_speaker_id = speaker_info.get('senior_speaker_id')
        if senior_speaker_id is None:
            # 화자 식별 실패 시 - segments가 있으면 첫 번째 화자 사용
            if segments and len(segments) > 0:
                # 가장 많이 발화한 화자를 시니어로 간주
                from collections import Counter
                speaker_counts = Counter(seg.get('speaker_id', 0) for seg in segments)
                if speaker_counts:
                    senior_speaker_id = speaker_counts.most_common(1)[0][0]
                    logger.info(f"화자 식별 fallback: 가장 많이 발화한 화자 {senior_speaker_id}를 시니어로 간주")

            if senior_speaker_id is None:
                # 여전히 실패시 원본 파일 반환
                return {
                    'status': 'fallback',
                    'audio_path': audio_path,
                    'message': '화자 식별 실패: segments가 없거나 화자 정보 없음',
                    'reason': 'no_speaker_info',
                    'segments_extracted': 0,
                    'total_duration': 0,
                    'using_original': True
                }
        
        # AI가 반환한 "화자 0" 형식에서 숫자만 추출
        match = re.search(r'화자\s*(\d+)', str(senior_speaker_id))
        if match:
            # 숫자 추출 성공 - STT API의 speaker_tag는 1부터 시작하므로 +1
            senior_speaker_numeric = int(match.group(1)) + 1
        else:
            # 숫자가 아닌 경우 원본 사용
            senior_speaker_numeric = senior_speaker_id
        
        logger.info(f"화자 ID 변환: AI='{senior_speaker_id}' -> STT={senior_speaker_numeric}")
        
        try:
            # 원본 오디오 로드
            y, sr = librosa.load(audio_path, sr=None)
            
            # 시니어 음성 구간 수집
            senior_segments = []
            for seg in segments:
                # 숫자 형식과 문자열 형식 모두 비교
                seg_speaker_id = seg.get('speaker_id')
                if (seg_speaker_id == senior_speaker_numeric or 
                    str(seg_speaker_id) == str(senior_speaker_numeric) or
                    seg_speaker_id == senior_speaker_id):
                    start_time = seg.get('start_time', 0)
                    end_time = seg.get('end_time', 0)
                    
                    # 시간을 샘플 인덱스로 변환
                    start_sample = int(start_time * sr)
                    end_sample = int(end_time * sr)
                    
                    # 유효한 범위 확인
                    if start_sample < len(y) and end_sample <= len(y) and start_sample < end_sample:
                        segment_audio = y[start_sample:end_sample]
                        senior_segments.append(segment_audio)
            
            if not senior_segments:
                # 디버깅 정보 출력
                logger.warning(f"시니어 음성 구간을 찾을 수 없음. AI ID: {senior_speaker_id}, STT ID: {senior_speaker_numeric}")
                
                # 사용 가능한 speaker_id들 출력
                available_speakers = set()
                for seg in segments:
                    available_speakers.add(seg.get('speaker_id'))
                logger.warning(f"세그먼트에서 발견된 화자 ID들: {sorted(available_speakers)}")
                logger.warning(f"총 세그먼트 수: {len(segments)}")
                
                # 처음 몇 개 세그먼트 샘플 출력
                if segments:
                    for i, seg in enumerate(segments[:3]):
                        logger.debug(f"세그먼트 {i}: speaker_id={seg.get('speaker_id')}, text={seg.get('text', '')[:50]}...")
                
                logger.warning("원본 파일 사용")
                return {
                    'status': 'fallback',
                    'audio_path': audio_path,
                    'message': '시니어 음성 구간을 찾을 수 없음',
                    'reason': 'no_senior_segments_found',
                    'segments_extracted': 0,
                    'total_duration': 0,
                    'using_original': True,
                    'total_segments_analyzed': len(segments),
                    'senior_speaker_id_ai': senior_speaker_id,
                    'senior_speaker_id_stt': senior_speaker_numeric,
                    'available_speakers': list(available_speakers)
                }
            
            # 시니어 구간들을 연결
            senior_audio = np.concatenate(senior_segments)
            total_duration = len(senior_audio) / sr
            
            # 임시 파일에 저장
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            temp_path = temp_file.name
            temp_file.close()
            
            sf.write(temp_path, senior_audio, sr)
            
            logger.info(f"시니어 음성 구간 추출 완료: {len(senior_segments)}개 구간, {total_duration:.2f}초")
            return {
                'status': 'success',
                'audio_path': temp_path,
                'message': f'시니어 음성 구간 추출 성공: {len(senior_segments)}개 구간',
                'segments_extracted': len(senior_segments),
                'total_duration': total_duration,
                'using_original': False,
                'temp_file_created': True,
                'original_file_duration': len(y) / sr,
                'extraction_ratio': total_duration / (len(y) / sr)
            }
            
        except Exception as e:
            logger.error(f"시니어 음성 구간 추출 실패: {e}")
            return {
                'status': 'error',
                'audio_path': audio_path,
                'message': f'시니어 음성 구간 추출 중 오류 발생: {str(e)}',
                'reason': 'extraction_error',
                'error': str(e),
                'segments_extracted': 0,
                'total_duration': 0,
                'using_original': True
            }
    
    async def batch_analyze(
        self,
        audio_files: List[str],
        user_info: Optional[Dict] = None
    ) -> List[Dict[str, Any]]:
        """
        여러 오디오 파일 일괄 분석
        
        Args:
            audio_files: 오디오 파일 경로 리스트
            user_info: 사용자 정보
            
        Returns:
            분석 결과 리스트
        """
        
        results = []
        history = []
        
        for audio_path in audio_files:
            logger.info(f"분석 중: {audio_path}")
            
            result = await self.analyze(
                audio_path=audio_path,
                user_info=user_info,
                history=history if history else None
            )
            
            results.append(result)
            
            # 성공한 결과를 기록에 추가
            if result['status'] == 'success':
                history.append({
                    'timestamp': result['timestamp'],
                    'indicators': result['indicators']
                })
        
        return results
    
    def validate_audio_file(self, audio_path: str) -> Tuple[bool, str]:
        """
        오디오 파일 유효성 검사
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            (유효 여부, 메시지)
        """
        
        path = Path(audio_path)
        
        # 파일 존재 확인
        if not path.exists():
            return False, f"파일을 찾을 수 없습니다: {audio_path}"
        
        # 파일 형식 확인
        valid_extensions = ['.wav', '.mp3', '.m4a', '.flac', '.ogg']
        if path.suffix.lower() not in valid_extensions:
            return False, f"지원하지 않는 파일 형식: {path.suffix}"
        
        # 파일 크기 확인 (최대 100MB)
        max_size = 100 * 1024 * 1024  # 100MB
        if path.stat().st_size > max_size:
            return False, f"파일 크기가 너무 큽니다: {path.stat().st_size / 1024 / 1024:.1f}MB"
        
        return True, "유효한 오디오 파일"
    
    def _format_to_improved_schema(
        self,
        result: Dict,
        indicators: 'MentalHealthIndicators',
        voice_features: Dict,
        text_analysis: Optional[Dict],
        sincnet_result: Optional[Dict],
        interpretation: Dict,
        risk_assessment: Dict,
        start_time: datetime
    ) -> Dict[str, Any]:
        """
        분석 결과를 개선된 스키마 형식으로 변환
        """
        import numpy as np
        
        # 5대 핵심 지표를 새로운 형식으로 변환
        core_indicators = {}
        for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
            value = getattr(indicators, key)
            core_indicators[key] = {
                'value': float(value),
                'level': self._calculate_level(value, key),
                'confidence': self._calculate_indicator_confidence(
                    key, voice_features, text_analysis, sincnet_result
                ),
                'trend': self._extract_trend(key, result.get('trend_analysis'))
            }
        
        # 3가지 분석 방법론 결과 구조화
        analysis_methodologies = {
            'librosa': self._format_librosa_result(voice_features),
            'gpt4o': self._format_gpt_result(text_analysis),
            'sincnet': self._format_sincnet_result(sincnet_result)
        }
        
        # 통합 결과
        integrated_results = {
            'method': 'weighted_average',
            'weights': {
                'librosa': self.weights['voice'],
                'gpt4o': self.weights['text'],
                'sincnet': self.weights['sincnet']
            },
            'confidence': self._calculate_overall_confidence(
                voice_features, text_analysis, sincnet_result
            ),
            'consistency': self._calculate_consistency(
                analysis_methodologies
            ),
            'riskAssessment': {
                'overall': risk_assessment['overall_risk'],
                'primaryConcerns': risk_assessment.get('high_risk_indicators', []),
                'urgency': self._determine_urgency(risk_assessment),
                'requiresAction': risk_assessment['overall_risk'] in ['high', 'moderate']
            }
        }
        
        # 시계열 분석 (있는 경우)
        time_series_analysis = None
        if result.get('trend_analysis'):
            time_series_analysis = self._format_time_series_analysis(
                result['trend_analysis'], core_indicators
            )
        
        # 종합 해석 및 권고
        interpretation_formatted = {
            'comprehensive': {
                'summary': interpretation.get('overall_interpretation', ''),
                'detailedAnalysis': interpretation.get('detailed_interpretation', ''),
                'keyFindings': interpretation.get('key_findings', []),
                'strengths': interpretation.get('positive_indicators', []),
                'concerns': interpretation.get('concerns', [])
            },
            'recommendations': {
                'immediate': risk_assessment.get('recommendations', [])[:2],
                'shortTerm': risk_assessment.get('recommendations', [])[2:4],
                'longTerm': risk_assessment.get('recommendations', [])[4:],
                'lifestyle': self._generate_lifestyle_recommendations(indicators),
                'medical': self._generate_medical_recommendations(risk_assessment)
            },
            'interventionLevel': {
                'required': risk_assessment['overall_risk'] in ['high', 'critical'],
                'type': self._determine_intervention_type(risk_assessment),
                'priority': self._determine_priority(risk_assessment),
                'suggestedActions': interpretation.get('action_items', [])
            }
        }
        
        # 메타데이터
        metadata = {
            'processing': {
                'totalTime': 0,  # 나중에 업데이트됨
                'pipelineVersion': '2.0.0',
                'timestamps': {
                    'started': start_time.isoformat(),
                    'completed': datetime.now().isoformat()
                }
            },
            'quality': {
                'audioQuality': self._assess_audio_quality(voice_features),
                'dataCompleteness': self._calculate_completeness(result),
                'analysisDepth': 'comprehensive',
                'limitations': self._identify_limitations(result)
            },
            'models': {
                'stt': 'google-cloud-speech-v1',
                'llm': 'gpt-4o',
                'sincnet': 'sincnet-v2.0',
                'librosa': '0.10.0'
            }
        }
        
        # 최종 결과 구성
        return {
            'analysisId': result.get('audio_path', '').split('/')[-1].split('.')[0],
            'callId': result.get('call_id', ''),
            'userId': result.get('user_id', ''),
            'seniorId': result.get('senior_id', ''),
            'coreIndicators': core_indicators,
            'analysisMethodologies': analysis_methodologies,
            'integratedResults': integrated_results,
            'timeSeriesAnalysis': time_series_analysis,
            'interpretation': interpretation_formatted,
            'metadata': metadata,
            'createdAt': start_time.isoformat(),
            'updatedAt': datetime.now().isoformat(),
            'status': 'completed',
            
            # 하위 호환성을 위한 레거시 필드
            'legacy': {
                'indicators': indicators.to_dict(),
                'voice_analysis': result.get('voice_analysis'),
                'text_analysis': result.get('text_analysis'),
                'sincnet_analysis': result.get('sincnet_analysis'),
                'risk_assessment': risk_assessment,
                'report': result.get('report'),
                'transcription': result.get('transcription')
            }
        }
    
    def _calculate_level(self, value: float, indicator: str) -> str:
        """지표 값에 따른 레벨 계산"""
        if indicator in ['DRI', 'SDI']:  # 낮을수록 위험
            if value >= 0.7:
                return 'low'
            elif value >= 0.4:
                return 'moderate'
            elif value >= 0.2:
                return 'high'
            else:
                return 'critical'
        else:  # CFL, ES, OV - 높을수록 좋음
            if value >= 0.7:
                return 'normal'
            elif value >= 0.4:
                return 'mild'
            elif value >= 0.2:
                return 'moderate'
            else:
                return 'severe'
    
    def _calculate_indicator_confidence(
        self, indicator: str, voice: Dict, text: Dict, sincnet: Dict
    ) -> float:
        """개별 지표의 신뢰도 계산"""
        confidences = []
        if voice and voice.get('status') == 'success':
            confidences.append(0.7)
        if text:
            confidences.append(0.8)
        if sincnet:
            confidences.append(0.75)
        
        if not confidences:
            logger.warning("신뢰도 계산: 신뢰도 값이 없습니다")
            return 0.5  # 중간 신뢰도
        return sum(confidences) / len(confidences)
    
    def _extract_trend(self, indicator: str, trend_analysis: Optional[Dict]) -> Optional[str]:
        """시계열 분석에서 트렌드 추출"""
        if not trend_analysis:
            return None
        
        trends = trend_analysis.get('indicator_trends', {})
        trend_value = trends.get(indicator, {}).get('trend')
        
        if trend_value == 'increasing':
            return 'improving' if indicator in ['CFL', 'ES', 'OV'] else 'declining'
        elif trend_value == 'decreasing':
            return 'declining' if indicator in ['CFL', 'ES', 'OV'] else 'improving'
        else:
            return 'stable'
    
    def _format_librosa_result(self, voice_features: Dict) -> Dict:
        """Librosa 분석 결과 포맷팅"""
        if not voice_features or voice_features.get('status') != 'success':
            return {
                'status': 'skipped',
                'weight': self.weights['voice'],
                'features': {},
                'indicators': {}
            }
        
        features = voice_features.get('features', {})
        
        # Librosa 기반 지표 계산
        # 음성 특징에서 직접 지표 추출
        indicators = {
            'pitch': features.get('pitch_mean', 0.0),
            'energy': features.get('energy_mean', 0.0),
            'speaking_rate': features.get('speaking_rate', 0.0),
            'pause_ratio': features.get('pause_ratio', 0.0),
            'voice_clarity': features.get('voice_clarity', 0.5),
            'tremor': features.get('tremor_amplitude', 0.0)
        }
        
        return {
            'status': 'success',
            'weight': self.weights['voice'],
            'features': {
                'pitch': {
                    'mean': features.get('pitch_mean', 0),
                    'std': features.get('pitch_std', 0),
                    'range': features.get('pitch_range', 0)
                },
                'energy': {
                    'mean': features.get('energy_mean', 0),
                    'std': features.get('energy_std', 0)
                },
                'speechRate': features.get('speaking_rate', 0),
                'pauseRatio': features.get('pause_ratio', 0),
                'voiceStability': features.get('voice_stability', 0),
                'tremor': {
                    'amplitude': features.get('tremor_amplitude', 0),
                    'frequency': features.get('tremor_frequency', 0)
                }
            },
            'indicators': indicators
        }
    
    def _format_gpt_result(self, text_analysis: Optional[Dict]) -> Dict:
        """GPT-4o 분석 결과 포맷팅"""
        if not text_analysis:
            return {
                'status': 'skipped',
                'weight': self.weights['text'],
                'transcription': {},
                'semanticAnalysis': {},
                'indicators': {}
            }
        
        analysis = text_analysis.get('analysis', {})
        
        return {
            'status': 'success',
            'weight': self.weights['text'],
            'transcription': {
                'text': text_analysis.get('text', ''),
                'confidence': 0.9,
                'language': 'ko'
            },
            'semanticAnalysis': {
                'sentiment': analysis.get('sentiment', {}),
                'emotions': analysis.get('emotions', {}),
                'topics': analysis.get('key_topics', []),
                'concerns': analysis.get('concerns', []),
                'coherence': analysis.get('coherence_score', 0.5)
            },
            'indicators': analysis.get('indicators', {})
        }
    
    def _format_sincnet_result(self, sincnet_result: Optional[Dict]) -> Dict:
        """SincNet 분석 결과 포맷팅"""
        if not sincnet_result:
            return {
                'status': 'skipped',
                'weight': self.weights['sincnet'],
                'predictions': {},
                'modelInfo': {},
                'indicators': {}
            }
        
        # SincNet 기반 지표 계산
        indicators = self.indicator_calculator._calculate_sincnet_indicators(sincnet_result)
        
        return {
            'status': 'success',
            'weight': self.weights['sincnet'],
            'predictions': {
                'depression': {
                    'probability': sincnet_result.get('depression_probability', 0),
                    'confidence': sincnet_result.get('depression_confidence', 0),
                    'features': []
                },
                'insomnia': {
                    'probability': sincnet_result.get('insomnia_probability', 0),
                    'confidence': sincnet_result.get('insomnia_confidence', 0),
                    'features': []
                }
            },
            'modelInfo': {
                'version': '2.0.0',
                'trainingDate': '2024-01-01',
                'accuracy': 0.85
            },
            'indicators': indicators
        }
    
    def _calculate_overall_confidence(self, voice: Dict, text: Dict, sincnet: Dict) -> float:
        """전체 신뢰도 계산"""
        confidences = []
        weights = []
        
        if voice and voice.get('status') == 'success':
            confidences.append(0.7)
            weights.append(self.weights['voice'])
        
        if text:
            confidences.append(0.8)
            weights.append(self.weights['text'])
        
        if sincnet:
            confidences.append(0.75)
            weights.append(self.weights['sincnet'])
        
        if not confidences:
            return 0.5
        
        # 가중 평균
        total_weight = sum(weights)
        weighted_conf = sum(c * w for c, w in zip(confidences, weights))
        if total_weight <= 0:
            logger.warning("가중 신뢰도 계산: 총 가중치가 0")
            return 0.5  # 중간 신뢰도
        return weighted_conf / total_weight
    
    def _calculate_consistency(self, methodologies: Dict) -> float:
        """방법론 간 일관성 계산"""
        import numpy as np
        
        # 각 방법론의 지표들을 비교
        indicators_list = []
        
        for method in ['librosa', 'gpt4o', 'sincnet']:
            if methodologies[method]['status'] == 'success':
                indicators = methodologies[method].get('indicators', {})
                if indicators:
                    indicators_list.append(indicators)
        
        if len(indicators_list) < 2:
            return 1.0  # 비교할 수 없으면 일관성 100%
        
        # 지표별 표준편차 계산
        consistency_scores = []
        for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
            values = [ind.get(key, 0.5) for ind in indicators_list]
            if values:
                std_dev = np.std(values)
                # 표준편차가 작을수록 일관성이 높음
                consistency = max(0, 1 - (std_dev * 2))
                consistency_scores.append(consistency)
        
        if not consistency_scores:
            logger.warning("일관성 점수 계산: 점수가 없습니다")
            return 0.5  # 중간 일관성
        return sum(consistency_scores) / len(consistency_scores)
    
    def _determine_urgency(self, risk_assessment: Dict) -> str:
        """긴급도 결정"""
        overall_risk = risk_assessment.get('overall_risk', 'low')
        
        if overall_risk == 'critical':
            return 'immediate'
        elif overall_risk == 'high':
            return 'within_24h'
        elif overall_risk == 'moderate':
            return 'within_week'
        else:
            return 'routine'
    
    def _determine_intervention_type(self, risk_assessment: Dict) -> str:
        """개입 유형 결정"""
        overall_risk = risk_assessment.get('overall_risk', 'low')
        
        if overall_risk == 'critical':
            return 'urgent_care'
        elif overall_risk == 'high':
            return 'consultation'
        elif overall_risk == 'moderate':
            return 'monitoring'
        else:
            return 'none'
    
    def _determine_priority(self, risk_assessment: Dict) -> str:
        """우선순위 결정"""
        overall_risk = risk_assessment.get('overall_risk', 'low')
        
        if overall_risk in ['critical', 'high']:
            return 'high'
        elif overall_risk == 'moderate':
            return 'medium'
        else:
            return 'low'
    
    def _format_time_series_analysis(self, trend_analysis: Dict, indicators: Dict) -> Dict:
        """시계열 분석 결과 포맷팅"""
        return {
            'baseline': {
                'established': trend_analysis.get('baseline_established', False),
                'dataPoints': trend_analysis.get('data_points', 0),
                'indicators': trend_analysis.get('baseline_values', {})
            },
            'trends': {
                'shortTerm': {
                    key: self._extract_trend(key, trend_analysis)
                    for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV']
                }
            },
            'changeDetection': {
                'significantChanges': trend_analysis.get('significant_changes', [])
            }
        }
    
    def _generate_lifestyle_recommendations(self, indicators: 'MentalHealthIndicators') -> List[str]:
        """생활습관 권고사항 생성"""
        recommendations = []
        
        if indicators.SDI < 0.5:
            recommendations.append("규칙적인 수면 습관 유지 (매일 같은 시간 취침/기상)")
        
        if indicators.OV < 0.5:
            recommendations.append("가벼운 운동이나 산책을 일상에 포함")
        
        if indicators.ES < 0.5:
            recommendations.append("명상이나 심호흡 등 스트레스 관리 기법 실천")
        
        return recommendations
    
    def _generate_medical_recommendations(self, risk_assessment: Dict) -> List[str]:
        """의료 상담 권고사항 생성"""
        recommendations = []
        overall_risk = risk_assessment.get('overall_risk', 'low')
        
        if overall_risk in ['high', 'critical']:
            recommendations.append("정신건강의학과 전문의 상담 권장")
        
        high_risk_indicators = risk_assessment.get('high_risk_indicators', [])
        if 'DRI' in high_risk_indicators:
            recommendations.append("우울증 선별 검사 실시")
        
        if 'CFL' in high_risk_indicators:
            recommendations.append("인지 기능 정밀 검사 고려")
        
        return recommendations
    
    def _assess_audio_quality(self, voice_features: Dict) -> str:
        """오디오 품질 평가"""
        if not voice_features or voice_features.get('status') != 'success':
            return 'low'
        
        features = voice_features.get('features', {})
        snr = features.get('snr', 0)  # Signal-to-Noise Ratio
        
        if snr > 20:
            return 'high'
        elif snr > 10:
            return 'medium'
        else:
            return 'low'
    
    def _calculate_completeness(self, result: Dict) -> float:
        """데이터 완성도 계산"""
        components = [
            'transcription',
            'voice_analysis',
            'text_analysis',
            'sincnet_analysis',
            'indicators',
            'risk_assessment',
            'comprehensive_interpretation'
        ]
        
        completed = sum(1 for comp in components if result.get(comp))
        return completed / len(components)
    
    def _identify_limitations(self, result: Dict) -> List[str]:
        """분석 제한사항 식별"""
        limitations = []
        
        if not result.get('transcription'):
            limitations.append("음성-텍스트 변환 실패로 텍스트 분석 제한")
        
        if not result.get('sincnet_analysis'):
            limitations.append("SincNet 모델 분석 미수행")
        
        if not result.get('trend_analysis'):
            limitations.append("과거 데이터 부족으로 시계열 분석 제한")
        
        return limitations
    
    def get_analysis_summary(self, result: Dict) -> Dict[str, Any]:
        """
        분석 결과 요약 생성
        
        Args:
            result: 전체 분석 결과
            
        Returns:
            요약 정보
        """
        
        if result.get('status') != 'success':
            return {
                'status': result.get('status'),
                'error': result.get('error')
            }
        
        indicators = result.get('indicators', {})
        risk = result.get('risk_assessment', {})
        
        summary = {
            'timestamp': result.get('timestamp'),
            'indicators': indicators,
            'overall_risk': risk.get('overall_risk', 'unknown'),
            'high_risk_indicators': risk.get('high_risk_indicators', []),
            'primary_concerns': [],
            'recommendations': risk.get('recommendations', [])[:3]  # 상위 3개
        }
        
        # 주요 우려사항 도출
        for key, value in indicators.items():
            if value < 0.4:
                concern = {
                    'DRI': '우울 위험',
                    'SDI': '수면 장애',
                    'CFL': '인지 기능 저하',
                    'ES': '정서 불안정',
                    'OV': '활력 저하'
                }.get(key, key)
                summary['primary_concerns'].append(concern)
        
        return summary
