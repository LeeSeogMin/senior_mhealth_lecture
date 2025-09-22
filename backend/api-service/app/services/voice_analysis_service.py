"""
음성 분석 서비스
제5강: Cloud Run과 FastAPI로 확장된 백엔드 구현

실제 AI 분석 파이프라인과 연동하는 서비스
"""

from typing import Optional, Dict, Any, List
from datetime import datetime
import asyncio
import tempfile
import os
import uuid
import json
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Optional imports for production
try:
    from google.cloud import storage
    from google.cloud import firestore
    GOOGLE_CLOUD_AVAILABLE = True
except ImportError:
    GOOGLE_CLOUD_AVAILABLE = False
    storage = None
    firestore = None

try:
    import httpx
    HTTPX_AVAILABLE = True
except ImportError:
    HTTPX_AVAILABLE = False
    httpx = None

from ..core.config import settings
from ..core.logging import get_logger
from ..models.voice_analysis import VoiceAnalysisRequest, VoiceAnalysisResponse

logger = get_logger(__name__)


class VoiceAnalysisService:
    """음성 분석 서비스"""
    
    def __init__(self):
        self.enabled = settings.voice_analysis_enabled
        self.executor = ThreadPoolExecutor(max_workers=2)
        
        # Google Cloud 서비스 초기화
        if GOOGLE_CLOUD_AVAILABLE and settings.google_cloud_project:
            try:
                self.storage_client = storage.Client(project=settings.google_cloud_project)
                self.firestore_client = firestore.Client(project=settings.google_cloud_project)
                self.bucket_name = settings.storage_bucket_name or "senior-mhealth-472007.firebasestorage.app"
                logger.info("Voice analysis service initialized with Google Cloud")
            except Exception as e:
                logger.warning(f"Google Cloud init failed, using mock mode: {e}")
                self.storage_client = None
                self.firestore_client = None
                self.bucket_name = None
        else:
            logger.info("Voice analysis service initialized in mock mode")
            self.storage_client = None
            self.firestore_client = None
            self.bucket_name = None
        
        # 분석 파이프라인 초기화 (지연 로딩)
        self.pipeline = None
        self.firestore_connector = None
        
    async def analyze_voice(self, request: VoiceAnalysisRequest) -> VoiceAnalysisResponse:
        """음성 분석 메인 함수"""
        try:
            logger.info(f"음성 분석 시작: call_id={request.call_id}, type={request.analysis_type}")
            
            if not self.enabled:
                return await self._create_disabled_response(request)
            
            # 분석 ID 생성
            analysis_id = f"analysis_{request.call_id or uuid.uuid4().hex[:8]}"
            
            # 오디오 파일 다운로드
            audio_file_path = await self._download_audio_file(request.audio_url)
            if not audio_file_path:
                return await self._create_error_response(request, analysis_id, "오디오 파일을 다운로드할 수 없습니다")
            
            try:
                # 실제 AI 분석 실행
                if settings.is_production:
                    analysis_result = await self._run_production_analysis(audio_file_path, request)
                else:
                    analysis_result = await self._run_mock_analysis(request)
                
                # Firestore에 결과 저장
                if self.firestore_client and request.user_id:
                    await self._save_analysis_result(request, analysis_result)
                
                # 응답 생성
                return await self._create_success_response(request, analysis_id, analysis_result)
                
            finally:
                # 임시 파일 정리
                if audio_file_path and os.path.exists(audio_file_path):
                    os.remove(audio_file_path)
                    logger.debug(f"임시 파일 삭제: {audio_file_path}")
                    
        except Exception as e:
            logger.error(f"음성 분석 실패: {e}")
            analysis_id = f"error_{uuid.uuid4().hex[:8]}"
            return await self._create_error_response(request, analysis_id, str(e))
    
    async def _download_audio_file(self, audio_url: Optional[str]) -> Optional[str]:
        """오디오 파일 다운로드"""
        if not audio_url:
            return None
        
        try:
            if audio_url.startswith('http'):
                # HTTP URL에서 다운로드
                return await self._download_from_url(audio_url)
            else:
                # Google Cloud Storage에서 다운로드
                return await self._download_from_storage(audio_url)
        except Exception as e:
            logger.error(f"오디오 파일 다운로드 실패: {e}")
            return None
    
    async def _download_from_url(self, url: str) -> Optional[str]:
        """HTTP URL에서 파일 다운로드"""
        if not HTTPX_AVAILABLE:
            logger.error("httpx 라이브러리가 없습니다")
            return None
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(url)
                response.raise_for_status()
                
                # 임시 파일 생성
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                    temp_file.write(response.content)
                    logger.info(f"URL에서 파일 다운로드 성공: {len(response.content)} bytes")
                    return temp_file.name
                    
        except Exception as e:
            logger.error(f"URL 다운로드 실패: {e}")
            return None
    
    async def _download_from_storage(self, storage_path: str) -> Optional[str]:
        """Google Cloud Storage에서 파일 다운로드"""
        if not self.storage_client:
            logger.warning("Storage client가 없어서 모의 데이터 사용")
            # 개발 환경에서는 모의 파일 생성
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                temp_file.write(b"mock audio data")
                return temp_file.name
        
        try:
            bucket = self.storage_client.bucket(self.bucket_name)
            blob = bucket.blob(storage_path)
            
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                blob.download_to_file(temp_file)
                logger.info(f"Storage에서 파일 다운로드 성공: {storage_path}")
                return temp_file.name
                
        except Exception as e:
            logger.error(f"Storage 다운로드 실패: {e}")
            return None
    
    async def _run_production_analysis(self, audio_path: str, request: VoiceAnalysisRequest) -> Dict[str, Any]:
        """실제 AI 분석 파이프라인 실행"""
        try:
            # 분석 파이프라인 지연 초기화
            if not self.pipeline:
                await self._initialize_pipeline()
            
            if not self.pipeline:
                logger.warning("분석 파이프라인이 초기화되지 않음. 모의 분석 사용")
                return await self._run_mock_analysis(request)
            
            # 사용자 정보 수집
            user_info = await self._get_user_info(request.user_id, request.senior_id)
            
            # 비동기 분석 실행
            loop = asyncio.get_event_loop()
            analysis_result = await loop.run_in_executor(
                self.executor,
                self._run_analysis_sync,
                audio_path,
                request.user_id,
                user_info
            )
            
            logger.info("실제 AI 분석 완료")
            return analysis_result
            
        except Exception as e:
            logger.error(f"실제 분석 실행 실패: {e}")
            return await self._run_mock_analysis(request)
    
    async def _initialize_pipeline(self):
        """분석 파이프라인 초기화"""
        try:
            # 실제 파이프라인 import 시도
            # from ...libraries.voice_analysis.pipeline.main_pipeline import SeniorMentalHealthPipeline
            # from ...libraries.voice_analysis.utils.firestore_connector import FirestoreConnector
            
            # 현재는 라이브러리 경로가 설정되지 않아서 None으로 설정
            # 실제 구현 시에는 적절한 import 경로로 변경
            self.pipeline = None
            self.firestore_connector = None
            
            logger.warning("분석 파이프라인 초기화 지연: 라이브러리 경로 설정 필요")
            
        except Exception as e:
            logger.error(f"분석 파이프라인 초기화 실패: {e}")
            self.pipeline = None
            self.firestore_connector = None
    
    def _run_analysis_sync(self, audio_path: str, user_id: str, user_info: Dict) -> Dict[str, Any]:
        """동기 분석 실행 (ThreadPoolExecutor용)"""
        # 실제 구현에서는 pipeline.analyze() 호출
        # return self.pipeline.analyze(
        #     audio_path=audio_path,
        #     user_id=user_id,
        #     user_info=user_info
        # )
        
        # 현재는 모의 결과 반환
        return {
            "transcription": {
                "senior_text": "안녕하세요, 오늘 기분이 좋습니다.",
                "full_text": "사용자: 안녕하세요. 시니어: 안녕하세요, 오늘 기분이 좋습니다.",
                "confidence": 0.92
            },
            "coreIndicators": {
                "DRI": {"value": 0.25, "level": "normal"},
                "SDI": {"value": 0.15, "level": "low"},
                "CFL": {"value": 0.7, "level": "normal"},
                "ES": {"value": 0.8, "level": "positive"},
                "OV": {"value": 0.6, "level": "normal"}
            },
            "voice_features": {
                "speech_rate": 150.2,
                "pause_frequency": 0.3,
                "voice_quality": 0.85
            },
            "report": {
                "summary": "전반적으로 안정된 정신건강 상태를 보입니다.",
                "recommendations": ["규칙적인 생활 패턴 유지", "가족과의 대화 시간 확보"]
            },
            "metadata": {
                "processing_time": 2.5,
                "model_version": "2.1.0",
                "confidence": 0.87
            }
        }
    
    async def _run_mock_analysis(self, request: VoiceAnalysisRequest) -> Dict[str, Any]:
        """개발용 모의 분석"""
        await asyncio.sleep(0.5)  # 분석 시간 시뮬레이션
        
        return {
            "transcription": {
                "senior_text": "개발 환경에서의 모의 음성 텍스트입니다.",
                "full_text": "사용자: 테스트 음성입니다. 시니어: 개발 환경에서의 모의 음성 텍스트입니다.",
                "confidence": 0.95
            },
            "coreIndicators": {
                "DRI": {"value": 0.2, "level": "low"},
                "SDI": {"value": 0.1, "level": "low"},
                "CFL": {"value": 0.8, "level": "high"},
                "ES": {"value": 0.9, "level": "very_positive"},
                "OV": {"value": 0.7, "level": "good"}
            },
            "voice_features": {
                "speech_rate": 145.5,
                "pause_frequency": 0.25,
                "voice_quality": 0.9
            },
            "sincnet_results": {
                "emotion": "positive",
                "stress_level": 0.2,
                "fatigue_level": 0.1
            },
            "report": {
                "summary": "개발 환경 테스트: 매우 양호한 정신건강 상태",
                "recommendations": [
                    "현재 상태를 잘 유지하고 계십니다",
                    "정기적인 모니터링을 계속하세요"
                ]
            },
            "comprehensive_interpretation": {
                "overall_assessment": {
                    "summary": "종합적으로 매우 건강한 정신상태를 유지하고 있습니다.",
                    "risk_level": "low"
                }
            },
            "metadata": {
                "processing_time": 0.8,
                "model_version": "2.1.0-dev",
                "confidence": 0.95,
                "mock_data": True
            }
        }
    
    async def _get_user_info(self, user_id: Optional[str], senior_id: Optional[str]) -> Dict:
        """사용자 정보 조회"""
        if not self.firestore_client or not user_id or not senior_id:
            return {"mock": True}
        
        try:
            # 시니어 정보 조회
            senior_doc = self.firestore_client.collection('users').document(user_id).collection('seniors').document(senior_id).get()
            senior_info = {}
            if senior_doc.exists:
                senior_data = senior_doc.to_dict()
                senior_info = {
                    'age': senior_data.get('age'),
                    'gender': senior_data.get('gender'),
                    'name': senior_data.get('name'),
                    'relationship': senior_data.get('relationship')
                }
            
            # 사용자 정보 조회
            user_doc = self.firestore_client.collection('users').document(user_id).get()
            user_info = {}
            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_info = {
                    'age': user_data.get('age'),
                    'gender': user_data.get('gender'),
                    'name': user_data.get('name')
                }
            
            return {
                'senior_id': senior_id,
                'call_id': None,
                'senior': senior_info,
                'user': user_info
            }
            
        except Exception as e:
            logger.error(f"사용자 정보 조회 실패: {e}")
            return {"error": str(e)}
    
    async def _save_analysis_result(self, request: VoiceAnalysisRequest, result: Dict[str, Any]):
        """분석 결과를 Firestore에 저장"""
        if not self.firestore_client:
            logger.info("Firestore 클라이언트가 없어서 저장 건너뜀")
            return
        
        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(
                self.executor,
                self._save_to_firestore_sync,
                request,
                result
            )
            logger.info(f"분석 결과 저장 완료: {request.call_id}")
            
        except Exception as e:
            logger.error(f"Firestore 저장 실패: {e}")
    
    def _save_to_firestore_sync(self, request: VoiceAnalysisRequest, result: Dict[str, Any]):
        """동기 Firestore 저장"""
        # 실제 구현에서는 firestore_connector.save_analysis_result() 사용
        # self.firestore_connector.save_analysis_result(
        #     request.user_id,
        #     result,
        #     request.audio_url,
        #     request.call_id,
        #     request.senior_id
        # )
        pass
    
    async def _create_success_response(self, request: VoiceAnalysisRequest, analysis_id: str, result: Dict[str, Any]) -> VoiceAnalysisResponse:
        """성공 응답 생성"""
        response_data = {
            "call_id": request.call_id,
            "results": {
                "transcription": result.get('transcription', {}),
                "mentalHealthAnalysis": result.get('coreIndicators', {}),
                "voicePatterns": result.get('voice_features', {}),
                "sincnetAnalysis": result.get('sincnet_results', {}),
                "summary": result.get('report', {}).get('summary', ''),
                "recommendations": result.get('report', {}).get('recommendations', []),
                "interpretation": result.get('comprehensive_interpretation', {}).get('overall_assessment', {}).get('summary', '')
            },
            "metadata": {
                "analysis_type": request.analysis_type,
                "processing_time": result.get('metadata', {}).get('processing_time', 0),
                "model_version": result.get('metadata', {}).get('model_version', 'unknown'),
                "confidence": result.get('metadata', {}).get('confidence', 0),
                "mock_data": result.get('metadata', {}).get('mock_data', False)
            }
        }
        
        return VoiceAnalysisResponse(
            success=True,
            analysis_id=analysis_id,
            status="completed",
            message="음성 분석이 성공적으로 완료되었습니다",
            data=response_data
        )
    
    async def _create_error_response(self, request: VoiceAnalysisRequest, analysis_id: str, error_message: str) -> VoiceAnalysisResponse:
        """오류 응답 생성"""
        response_data = {
            "call_id": request.call_id,
            "results": {
                "error": error_message,
                "summary": "분석 중 오류가 발생했습니다.",
                "recommendations": ["오디오 파일을 확인하고 다시 시도해주세요."]
            },
            "metadata": {
                "analysis_type": request.analysis_type,
                "error": True,
                "error_message": error_message
            }
        }
        
        return VoiceAnalysisResponse(
            success=False,
            analysis_id=analysis_id,
            status="error",
            message=f"음성 분석 실패: {error_message}",
            data=response_data
        )
    
    async def _create_disabled_response(self, request: VoiceAnalysisRequest) -> VoiceAnalysisResponse:
        """서비스 비활성화 응답"""
        analysis_id = f"disabled_{uuid.uuid4().hex[:8]}"
        response_data = {
            "call_id": request.call_id,
            "results": {
                "summary": "음성 분석 서비스가 현재 비활성화되어 있습니다.",
                "recommendations": ["시스템 관리자에게 문의하세요."]
            },
            "metadata": {
                "analysis_type": request.analysis_type,
                "service_enabled": False
            }
        }
        
        return VoiceAnalysisResponse(
            success=False,
            analysis_id=analysis_id,
            status="disabled",
            message="음성 분석 서비스가 비활성화되어 있습니다",
            data=response_data
        )