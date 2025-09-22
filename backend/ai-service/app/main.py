"""
Senior MHealth AI Analysis Service
통합 AI 정신건강 분석 API 서비스
"""

from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import os
import sys
import logging
from datetime import datetime
import asyncio
from pathlib import Path

# Universal Configuration System 추가
sys.path.append(str(Path(__file__).parent.parent.parent))
from config_loader import get_config, get_project_id, get_firebase_config

# 분석 모듈 경로 추가
analysis_path = Path(__file__).parent.parent / "libraries" / "voice_analysis"
if not analysis_path.exists():
    # Docker 환경에서의 경로
    analysis_path = Path("/app/libraries/voice_analysis")
sys.path.append(str(analysis_path))

try:
    # Docker 환경에서 libraries 폴더가 /app/libraries에 있음
    from libraries.voice_analysis.analysis.pipeline.main_pipeline import SeniorMentalHealthPipeline
    from libraries.voice_analysis.analysis.timeseries.risk_predictor import RiskPredictor
except ImportError:
    try:
        # sys.path에 추가된 경로로 시도
        from analysis.pipeline.main_pipeline import SeniorMentalHealthPipeline
        from analysis.timeseries.risk_predictor import RiskPredictor
    except ImportError as e:
        print(f"Error: Could not import analysis modules: {e}")
        raise
    RiskPredictor = None

# RAG 모듈은 옵션
try:
    from analysis.rag.core import RAGEnhancedTextAnalyzer, FirebaseStorageVectorStore
    RAG_AVAILABLE = True
except ImportError:
    RAG_AVAILABLE = False
    print("RAG 모듈 사용 불가 - 기본 분석만 사용됩니다")

# Sequential Chaining 모듈 임포트
from .chains import (
    ChainManager,
    CrisisDetector, 
    TranscriptionAdapter,
    VoiceAnalysisAdapter,
    TextAnalysisAdapter,
    SincNetAdapter,
    BasicScreeningAdapter
)
from .chains.result_integration import ResultIntegrator
from .config import FeatureFlags, ABTestManager
from .monitoring import ChainMetrics

# Universal Configuration 로드
try:
    config = get_config()
    project_config = config['project']
    firebase_config = get_firebase_config()
    logger = logging.getLogger(__name__)
    logger.info(f"✅ Configuration loaded - Project: {project_config['id']}")
except Exception as e:
    # Fallback to environment variables
    logger = logging.getLogger(__name__)
    logger.warning(f"⚠️ Config loader failed, using environment variables: {e}")
    project_config = {
        'id': os.getenv('GOOGLE_CLOUD_PROJECT', 'senior-mhealth-472007'),
        'region': os.getenv('REGION', 'asia-northeast3')
    }
    firebase_config = {
        'projectId': project_config['id'],
        'storageBucket': f"{project_config['id']}.firebasestorage.app"
    }

# 로깅 설정
logging.basicConfig(level=logging.INFO)

# FastAPI 앱 초기화
app = FastAPI(
    title="Senior MHealth AI Analysis Service",
    description="AI 기반 시니어 정신건강 분석 서비스",
    version="2.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API 라우터 등록
from .api import analysis
app.include_router(analysis.router, prefix="/api")

# 글로벌 파이프라인 인스턴스
pipeline = None
risk_predictor = None
rag_analyzer = None
vector_store = None

# Sequential Chaining 인스턴스
chain_manager = None
chain_metrics = None
ab_test_manager = None

@app.on_event("startup")
async def startup_event():
    """서비스 시작 시 최소 초기화만 수행"""
    logger.info("AI Analysis Service 시작")
    # 무거운 초기화는 실제 요청이 올 때 lazy loading으로 처리

async def initialize_pipeline():
    """파이프라인 lazy initialization"""
    global pipeline, risk_predictor, rag_analyzer, vector_store
    global chain_manager, chain_metrics, ab_test_manager

    if pipeline is not None:
        return  # 이미 초기화됨

    logger.info("파이프라인 초기화 시작")

    # 파이프라인 설정
    config = {
        'use_sincnet': os.getenv('USE_SINCNET', 'true').lower() == 'true',  # SincNet 환경변수로 제어
        'use_rag': os.getenv('USE_RAG', 'false').lower() == 'true'  # RAG 선택적
    }

    # 파이프라인 초기화
    pipeline = SeniorMentalHealthPipeline(config=config)
    risk_predictor = RiskPredictor()

    # Sequential Chaining 초기화 (Feature Flag 확인)
    if FeatureFlags.ENABLE_CHAINING:
        logger.info(f"Sequential Chaining 초기화 (모드: {FeatureFlags.CHAINING_MODE})")

        # Chain Manager 설정
        chain_manager = ChainManager(cache_enabled=True)

        # 체인 단계 구성
        chain_manager.add_steps([
            TranscriptionAdapter(),
            CrisisDetector(model_type='gemini'),
            BasicScreeningAdapter(),
            VoiceAnalysisAdapter(),
            TextAnalysisAdapter(),
            SincNetAdapter(),
            ResultIntegrator()
        ])

        # 메트릭 및 A/B 테스트 관리자
        chain_metrics = ChainMetrics()
        ab_test_manager = ABTestManager()

        logger.info("Sequential Chaining 초기화 완료")

    # RAG 시스템 초기화 (선택적)
    if config.get('use_rag'):
        try:
            logger.info("RAG 시스템 초기화 시작")

            # 벡터스토어 초기화
            vector_store = FirebaseStorageVectorStore(
                project_id=project_config['id']
            )

            # RAG 강화 분석기 초기화
            rag_analyzer = RAGEnhancedTextAnalyzer(
                use_rag=True,
                vector_store_config={
                    'project_id': project_config['id']
                }
            )

            logger.info("RAG 시스템 초기화 완료")
        except Exception as e:
            logger.error(f"RAG 시스템 초기화 실패: {e}")
            rag_analyzer = None
            vector_store = None
    
    logger.info("AI Analysis Service 초기화 완료")

class AnalysisRequest(BaseModel):
    """분석 요청 모델"""
    user_id: Optional[str] = Field(None, description="사용자 ID")
    age: Optional[int] = Field(None, description="나이")
    gender: Optional[str] = Field(None, description="성별")
    use_rag: bool = Field(False, description="RAG 사용 여부")
    include_trend: bool = Field(True, description="추세 분석 포함")

class UserProfile(BaseModel):
    """사용자 프로필 정보"""
    user: Dict[str, Any] = Field({}, description="사용자 정보")
    senior: Dict[str, Any] = Field({}, description="시니어 정보 (나이, 성별 등)")

class StorageAnalysisRequest(BaseModel):
    """Storage 분석 요청 모델"""
    user_profile: Optional[UserProfile] = Field(None, description="사용자 프로필 정보")

class AnalysisResponse(BaseModel):
    """분석 응답 모델"""
    status: str
    analysis_id: str
    timestamp: str
    indicators: Optional[Dict[str, float]]
    risk_assessment: Optional[Dict[str, Any]]
    trend_analysis: Optional[Dict[str, Any]]
    recommendations: Optional[List[str]]
    processing_time: float

@app.get("/health")
async def health_check():
    """헬스 체크"""
    return {
        "status": "healthy",
        "service": "ai-analysis",
        "timestamp": datetime.now().isoformat(),
        "components": {
            "voice_analysis": "ready",
            "text_analysis": "ready",
            "sincnet": "ready",
            "rag": os.getenv('USE_RAG', 'false')
        }
    }

@app.get("/debug/models")
async def debug_models():
    """디버그: 모델 파일 존재 여부 확인"""
    import os
    from pathlib import Path

    debug_info = {
        "timestamp": datetime.now().isoformat(),
        "paths": {},
        "files": {},
        "model_manager_status": {}
    }

    # 예상 경로들 확인
    paths_to_check = [
        "/app/models",
        "/app/models/sincnet",
        "/app/libraries/voice_analysis/analysis/sincnet/models",
        "/app/libraries/voice_analysis/analysis/sincnet"
    ]

    for path_str in paths_to_check:
        path = Path(path_str)
        debug_info["paths"][path_str] = {
            "exists": path.exists(),
            "is_dir": path.is_dir() if path.exists() else False,
            "contents": list(path.iterdir()) if path.exists() and path.is_dir() else []
        }

    # 모델 파일 확인
    model_files = [
        "/app/models/sincnet/dep_model_10500_raw.pkl",
        "/app/models/sincnet/insom_model_38800_raw.pkl"
    ]

    for file_path in model_files:
        path = Path(file_path)
        debug_info["files"][file_path] = {
            "exists": path.exists(),
            "size_mb": round(path.stat().st_size / 1024 / 1024, 2) if path.exists() else 0
        }

    # SincNet 모델 매니저 상태 확인
    try:
        from libraries.voice_analysis.analysis.sincnet.model_manager import get_model_manager
        manager = get_model_manager()
        debug_info["model_manager_status"] = manager.get_model_info()
    except Exception as e:
        debug_info["model_manager_status"] = {"error": str(e)}

    return debug_info

@app.post("/analyze/voice", response_model=AnalysisResponse)
async def analyze_voice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    request: AnalysisRequest = AnalysisRequest()
):
    """
    음성 파일 분석 엔드포인트
    
    분석 프로세스:
    1. 음성 → 텍스트 변환 (STT)
    2. 화자 식별 및 시니어 음성 추출
    3. 음성 특징 분석 (Librosa)
    4. 텍스트 감정 분석 (GPT-4o/Gemini)
    5. SincNet 딥러닝 분석
    6. 5대 지표 통합 계산
    7. 위험도 평가 및 추세 분석
    
    Sequential Chaining 사용 시:
    - 위기 상황 조기 감지 (3-5초)
    - 순차적 체인 실행
    - 캐싱 및 성능 최적화
    """
    
    # Lazy initialization
    await initialize_pipeline()

    start_time = datetime.now()
    analysis_id = f"analysis_{start_time.strftime('%Y%m%d_%H%M%S')}"

    try:
        # 임시 파일로 저장
        temp_dir = Path("/tmp/audio_uploads")
        temp_dir.mkdir(exist_ok=True)
        
        file_path = temp_dir / f"{analysis_id}_{file.filename}"
        
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        logger.info(f"음성 파일 저장: {file_path}")
        
        # 사용자 정보 구성
        user_info = {}
        if request.age:
            user_info['age'] = request.age
        if request.gender:
            user_info['gender'] = request.gender
        
        # Sequential Chaining 사용 여부 결정
        use_chaining = False
        if FeatureFlags.ENABLE_CHAINING and chain_manager:
            use_chaining = FeatureFlags.should_use_chaining(request.user_id)
            logger.info(f"User {request.user_id}: Chaining {'enabled' if use_chaining else 'disabled'}")
        
        # 분석 실행
        if use_chaining:
            # Sequential Chaining 모드
            context = {
                'audio_path': str(file_path),
                'user_id': request.user_id,
                'user_info': user_info,
                'pipeline': pipeline  # 기존 파이프라인 참조
            }
            
            # 체인 실행
            result = await chain_manager.execute(
                audio_data=content,
                initial_context=context
            )
            
            # 메트릭 기록
            if chain_metrics:
                await chain_metrics.record_execution(
                    chain_name='voice_analysis',
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    api_calls=len(result.get('chain_metadata', {}).get('steps_executed', [])),
                    cost=0.05,  # 예상 비용
                    mode='chaining',
                    context=result,
                    success=True
                )
            
            # A/B 테스트 기록
            if ab_test_manager:
                ab_test_manager.record_result(
                    user_id=request.user_id,
                    processing_time=(datetime.now() - start_time).total_seconds(),
                    success=True,
                    score=result.get('final_indicators', {}).get('OV', {}).get('score', 0)
                )
        else:
            # 기존 파이프라인 모드
            result = await pipeline.analyze(
                audio_path=str(file_path),
                user_id=request.user_id,
                user_info=user_info
            )
            
            # 메트릭 기록 (레거시 모드)
            if chain_metrics:
                await chain_metrics.record_execution(
                    chain_name='voice_analysis',
                    execution_time=(datetime.now() - start_time).total_seconds(),
                    api_calls=3,  # 기본 API 호출 수
                    cost=0.07,  # 예상 비용
                    mode='legacy',
                    context={'indicators': result.get('indicators')},
                    success=True
                )
        
        # 추세 분석 (옵션)
        trend_analysis = None
        if request.include_trend and result.get('history'):
            trend_result = risk_predictor.predict_risk(
                historical_data=result['history'],
                prediction_horizon=7
            )
            trend_analysis = trend_result
        
        # 추천사항 생성
        recommendations = _generate_recommendations(
            result.get('indicators'),
            result.get('risk_assessment')
        )
        
        # 백그라운드에서 파일 정리
        background_tasks.add_task(cleanup_file, file_path)
        
        # 처리 시간 계산
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # 지표 추출 - 새로운 스키마에서는 legacy.indicators에 있을 수 있음
        indicators = result.get('indicators')
        if not indicators and 'legacy' in result:
            indicators = result['legacy'].get('indicators')
        
        # 위험도 평가 추출
        risk_assessment = result.get('risk_assessment')
        if not risk_assessment and 'integratedResults' in result:
            risk_assessment = result['integratedResults'].get('riskAssessment')
        elif not risk_assessment and 'legacy' in result:
            risk_assessment = result['legacy'].get('risk_assessment')
        
        return AnalysisResponse(
            status="success",
            analysis_id=analysis_id,
            timestamp=start_time.isoformat(),
            indicators=indicators,
            risk_assessment=risk_assessment,
            trend_analysis=trend_analysis,
            recommendations=recommendations,
            processing_time=processing_time
        )
        
    except Exception as e:
        logger.error(f"분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/storage")
async def analyze_from_storage(
    background_tasks: BackgroundTasks,
    storage_path: str,
    session_id: str,
    user_id: str,
    senior_id: str,
    use_rag: bool = False,
    include_trend: bool = True,
    request: StorageAnalysisRequest = StorageAnalysisRequest()
):
    """Firebase Storage에서 직접 파일을 가져와서 분석"""
    # Lazy initialization
    await initialize_pipeline()

    from google.cloud import storage
    import tempfile

    start_time = datetime.now()

    try:
        # Storage에서 파일 다운로드
        client = storage.Client()
        bucket = client.bucket(firebase_config['storageBucket'])

        # 모바일 앱의 복잡한 경로 구조 처리
        if storage_path.startswith('calls/'):
            # 이미 전체 경로인 경우 그대로 사용
            actual_path = storage_path
        elif '/' in storage_path:
            # 부분 경로인 경우 calls/ 추가
            actual_path = f"calls/{storage_path}"
        else:
            # 단순 파일명인 경우 모바일 앱 경로 구조로 구성
            # calls/{user_id}/{session_id}/{filename}
            actual_path = f"calls/{user_id}/{session_id}/{storage_path}"

        blob = bucket.blob(actual_path)

        if not blob.exists():
            raise HTTPException(
                status_code=404,
                detail=f"파일을 찾을 수 없습니다: {actual_path}"
            )

        logger.info(f"파일을 찾았습니다: {actual_path}")

        # 임시 파일로 다운로드
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as tmp_file:
            blob.download_to_filename(tmp_file.name)
            temp_path = tmp_file.name

        logger.info(f"Storage에서 파일 다운로드 완료: {actual_path} -> {temp_path}")

        # 사용자 프로필 정보 구성
        user_info = None
        if request.user_profile:
            user_info = {
                'user': request.user_profile.user,
                'senior': request.user_profile.senior
            }
            logger.info(f"📋 사용자 프로필 정보 수신: {user_info}")

        # 파일 분석
        with open(temp_path, 'rb') as f:
            # 음성 분석 파이프라인 실행 (user_info 전달)
            result = await pipeline.analyze(
                audio_path=temp_path,
                user_id=user_id,
                user_info=user_info
            )

        # 임시 파일 삭제
        os.unlink(temp_path)

        # Generate analysis_id
        analysis_id = f"storage_{session_id}_{int(datetime.now().timestamp())}"

        # Generate recommendations if available
        recommendations = _generate_recommendations(
            result.get('indicators'),
            result.get('risk_assessment')
        )

        return AnalysisResponse(
            status="success",
            analysis_id=analysis_id,
            timestamp=start_time.isoformat(),
            indicators=result.get('indicators'),
            risk_assessment=result.get('risk_assessment'),
            trend_analysis=result.get('trend_analysis') if include_trend else None,
            recommendations=recommendations,
            processing_time=(datetime.now() - start_time).total_seconds()
        )

    except Exception as e:
        logger.error(f"Storage 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze/text")
async def analyze_text(text: str, request: AnalysisRequest = AnalysisRequest()):
    # Lazy initialization
    await initialize_pipeline()
    """텍스트만 분석 (음성 없이)"""
    
    start_time = datetime.now()
    
    try:
        # RAG 사용 여부에 따라 분석기 선택
        if request.use_rag and rag_analyzer:
            logger.info("RAG 강화 텍스트 분석 사용")
            text_result = await rag_analyzer.analyze_with_rag(
                text,
                context={'age': request.age, 'gender': request.gender}
            )
        else:
            logger.info("기본 텍스트 분석 사용")
            text_result = await pipeline.text_analyzer.analyze(
                text,
                context={'age': request.age, 'gender': request.gender}
            )
        
        # 텍스트 기반 지표 계산
        indicators = pipeline.indicator_calculator.calculate(
            voice_features=None,
            text_analysis=text_result,
            sincnet_results=None
        )
        
        # RAG 메타데이터 포함
        response_data = {
            "status": "success",
            "timestamp": start_time.isoformat(),
            "text_analysis": text_result,
            "indicators": indicators.to_dict() if indicators else None,
            "processing_time": (datetime.now() - start_time).total_seconds()
        }
        
        # RAG 사용 시 추가 정보
        if request.use_rag and text_result.get('rag_metadata'):
            response_data['rag_info'] = text_result['rag_metadata']
        
        return response_data
        
    except Exception as e:
        logger.error(f"텍스트 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/models/status")
async def get_models_status():
    """모델 상태 확인"""
    return {
        "voice_analyzer": pipeline.voice_analyzer is not None,
        "text_analyzer": pipeline.text_analyzer is not None,
        "sincnet_analyzer": pipeline.sincnet_analyzer is not None,
        "stt_connector": pipeline.stt_connector is not None,
        "rag_enabled": pipeline.config.get('use_rag', False),
        "chaining_enabled": FeatureFlags.ENABLE_CHAINING,
        "chaining_mode": FeatureFlags.CHAINING_MODE if FeatureFlags.ENABLE_CHAINING else None
    }

@app.get("/metrics/chaining")
async def get_chaining_metrics():
    """Sequential Chaining 메트릭 조회"""
    if not chain_metrics:
        raise HTTPException(status_code=404, detail="Chaining not enabled")
    
    return {
        "comparison": chain_metrics.get_comparison_metrics(),
        "percentiles": chain_metrics.get_percentile_metrics(),
        "real_time": chain_metrics.get_real_time_metrics()
    }

@app.get("/metrics/ab-test")
async def get_ab_test_status():
    """A/B 테스트 상태 조회"""
    if not ab_test_manager:
        raise HTTPException(status_code=404, detail="A/B testing not enabled")
    
    return {
        "statistics": ab_test_manager.get_statistics(),
        "should_conclude": ab_test_manager.should_conclude_test(),
        "recommendation": ab_test_manager.get_recommendation()
    }

@app.post("/api/analysis/comprehensive")
async def analyze_comprehensive(request: Dict[str, Any]):
    """
    종합 분석 엔드포인트 - 모바일 앱과의 호환성을 위해 추가
    /analyze/storage와 동일한 기능을 제공하지만 다른 경로로 접근
    """
    # Lazy initialization
    await initialize_pipeline()

    from google.cloud import storage
    import tempfile

    start_time = datetime.now()

    try:
        # 요청 파라미터 추출
        user_email = request.get("user_email")
        audio_path = request.get("audio_path")
        session_id = request.get("session_id", f"session_{datetime.now().timestamp()}")

        if not user_email or not audio_path:
            raise HTTPException(status_code=400, detail="user_email과 audio_path는 필수 항목입니다")

        logger.info(f"종합 분석 시작 - User: {user_email}, Path: {audio_path}")

        # Storage에서 파일 다운로드
        client = storage.Client()
        bucket = client.bucket(firebase_config['storageBucket'])
        blob = bucket.blob(audio_path)

        if not blob.exists():
            raise HTTPException(status_code=404, detail=f"파일을 찾을 수 없습니다: {audio_path}")

        # 임시 파일로 다운로드
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
            blob.download_to_filename(tmp_file.name)
            temp_path = tmp_file.name

        logger.info(f"파일 다운로드 완료: {audio_path} -> {temp_path}")

        # 음성 분석 파이프라인 실행
        result = await pipeline.analyze(
            audio_path=temp_path,
            user_id=user_email
        )

        # 임시 파일 삭제
        os.unlink(temp_path)

        processing_time = (datetime.now() - start_time).total_seconds()

        return {
            "status": "success",
            "timestamp": start_time.isoformat(),
            "user_email": user_email,
            "audio_path": audio_path,
            "session_id": session_id,
            "analysis_results": result,
            "processing_time": processing_time
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"종합 분석 실패: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/crisis/alert")
async def handle_crisis_alert(
    user_id: str,
    severity: str,
    transcript: str,
    confidence: float
):
    """위기 상황 알림 처리"""
    logger.critical(f"CRISIS ALERT - User: {user_id}, Severity: {severity}, Confidence: {confidence}")

    # 여기에 실제 알림 로직 구현
    # - 의료진 알림
    # - 긴급 연락처 통보
    # - 위기 개입 프로토콜 실행

    return {
        "status": "alert_received",
        "user_id": user_id,
        "severity": severity,
        "timestamp": datetime.now().isoformat(),
        "action": "emergency_protocol_activated"
    }

def _generate_recommendations(indicators: Dict, risk_assessment: Dict) -> List[str]:
    """지표 기반 추천사항 생성"""
    recommendations = []
    
    if not indicators:
        return ["분석 데이터가 부족합니다. 정기적인 모니터링을 권장합니다."]
    
    # 우울 위험도 기반
    if indicators.get('DRI', 0) < 0.4:
        recommendations.append("우울 위험이 높습니다. 전문가 상담을 고려해주세요.")
    
    # 수면 장애 기반
    if indicators.get('SDI', 0) < 0.4:
        recommendations.append("수면 패턴 개선이 필요합니다. 규칙적인 수면 습관을 만들어보세요.")
    
    # 인지 기능 기반
    if indicators.get('CFL', 0) < 0.4:
        recommendations.append("인지 활동 프로그램 참여를 권장합니다.")
    
    # 정서 안정성 기반
    if indicators.get('ES', 0) < 0.4:
        recommendations.append("정서 안정을 위한 명상이나 이완 운동을 시도해보세요.")
    
    # 활력도 기반
    if indicators.get('OV', 0) < 0.4:
        recommendations.append("가벼운 운동과 사회 활동 참여를 늘려보세요.")
    
    return recommendations if recommendations else ["전반적으로 양호한 상태입니다. 현재 활동을 유지하세요."]

@app.post("/complete")
async def complete_analysis(request: dict):
    """
    간단한 우회 종합분석 엔드포인트
    Field 호환성 문제 없이 JSON으로 처리
    """
    await initialize_pipeline()
    from google.cloud import storage
    import tempfile
    start_time = datetime.now()

    try:
        user_email = request.get("user_email")
        audio_path = request.get("audio_path")
        session_id = request.get("session_id", f"session_{datetime.now().timestamp()}")

        if not user_email or not audio_path:
            return {"error": "user_email과 audio_path가 필요합니다"}

        # Firebase Storage에서 파일 다운로드
        client = storage.Client()
        bucket = client.bucket(firebase_config['storageBucket'])
        blob = bucket.blob(audio_path)

        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            blob.download_to_filename(temp_file.name)
            temp_path = Path(temp_file.name)

        # 음성 분석 수행
        analysis_results = await pipeline.analyze(str(temp_path))

        # 처리 시간 계산
        processing_time = (datetime.now() - start_time).total_seconds()

        # 임시 파일 정리
        await cleanup_file(temp_path)

        return {
            "session_id": session_id,
            "user_email": user_email,
            "audio_path": audio_path,
            "analysis": analysis_results,
            "processing_time": processing_time,
            "status": "success"
        }

    except Exception as e:
        logger.error(f"Complete 분석 실패: {e}")
        return {"error": str(e), "status": "failed"}

async def cleanup_file(file_path: Path):
    """임시 파일 정리"""
    try:
        if file_path.exists():
            file_path.unlink()
            logger.info(f"임시 파일 삭제: {file_path}")
    except Exception as e:
        logger.error(f"파일 삭제 실패: {e}")

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)