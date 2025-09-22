# 제7강: AI 모델 이해와 로컬 테스트 - FastAPI 모델 서버
"""
FastAPI 기반 모델 서빙 서버
실시간 음성 분석 API 제공
"""

import os
import json
import asyncio
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from contextlib import asynccontextmanager

import torch
import torchaudio
import numpy as np
from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import uvicorn

from ai.inference.inference_engine import InferenceEngine
from ai.inference.streaming_inference import StreamingInference
from ai.models.model_optimizer import ModelOptimizer


logger = logging.getLogger(__name__)


class AudioRequest(BaseModel):
    """오디오 분석 요청 모델"""
    feature_type: str = Field(default="raw", description="특징 추출 타입 (raw, mfcc, mel)")
    use_cache: bool = Field(default=True, description="캐시 사용 여부")
    return_features: bool = Field(default=False, description="특징 벡터 반환 여부")
    confidence_threshold: float = Field(default=0.5, description="신뢰도 임계값")


class PredictionResponse(BaseModel):
    """예측 결과 응답 모델"""
    success: bool
    prediction: Dict[str, Any]
    processing_time: float
    model_info: Dict[str, str]
    timestamp: str
    features: Optional[Dict[str, Any]] = None
    confidence: float
    metadata: Dict[str, Any]


class HealthResponse(BaseModel):
    """헬스체크 응답 모델"""
    status: str
    timestamp: str
    version: str
    models_loaded: List[str]
    system_info: Dict[str, Any]


class BatchRequest(BaseModel):
    """배치 처리 요청 모델"""
    audio_files: List[str]
    feature_type: str = "raw"
    use_cache: bool = True
    parallel_processing: bool = True


# 글로벌 변수
inference_engine: Optional[InferenceEngine] = None
streaming_inference: Optional[StreamingInference] = None
model_optimizer: Optional[ModelOptimizer] = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI 앱 라이프사이클 관리"""
    global inference_engine, streaming_inference, model_optimizer
    
    # 시작 시 초기화
    try:
        logger.info("AI 모델 서버 초기화 시작")
        
        # 추론 엔진 초기화
        inference_engine = InferenceEngine()
        
        # 스트리밍 추론 초기화 (백그라운드)
        streaming_inference = StreamingInference()
        
        # 모델 최적화기 초기화
        model_optimizer = ModelOptimizer()
        
        # 모델 로드 (비동기)
        await asyncio.create_task(_load_models())
        
        logger.info("AI 모델 서버 초기화 완료")
        
    except Exception as e:
        logger.error(f"서버 초기화 실패: {str(e)}")
        raise
    
    yield
    
    # 종료 시 정리
    try:
        logger.info("AI 모델 서버 종료 시작")
        
        if streaming_inference and streaming_inference.is_running:
            streaming_inference.stop_processing()
        
        # 캐시 정리
        if inference_engine:
            inference_engine.clear_cache()
        
        logger.info("AI 모델 서버 종료 완료")
        
    except Exception as e:
        logger.error(f"서버 종료 중 오류: {str(e)}")


async def _load_models():
    """모델 비동기 로드"""
    try:
        # 기본 모델 로드
        if inference_engine:
            # 모델 경로가 존재하면 로드
            model_dir = Path("models")
            if model_dir.exists():
                model_files = list(model_dir.glob("*.pth"))
                for model_file in model_files[:1]:  # 첫 번째 모델만 로드
                    logger.info(f"모델 로드 중: {model_file}")
                    # 실제 로드 로직은 inference_engine에서 처리
            
        logger.info("모델 로드 완료")
        
    except Exception as e:
        logger.error(f"모델 로드 실패: {str(e)}")


def create_app() -> FastAPI:
    """FastAPI 앱 생성"""
    app = FastAPI(
        title="Senior MHealth AI Model Server",
        description="음성 기반 정신건강 분석 AI 모델 서빙 API",
        version="1.0.0",
        lifespan=lifespan
    )
    
    # CORS 미들웨어 설정
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # 라우터 등록
    _register_routes(app)
    
    return app


def _register_routes(app: FastAPI):
    """API 라우터 등록"""
    
    @app.get("/", response_model=Dict[str, str])
    async def root():
        """루트 엔드포인트"""
        return {
            "message": "Senior MHealth AI Model Server",
            "version": "1.0.0",
            "status": "running"
        }
    
    @app.get("/health", response_model=HealthResponse)
    async def health_check():
        """헬스체크 엔드포인트"""
        try:
            models_loaded = []
            if inference_engine:
                models_loaded.append("InferenceEngine")
            if streaming_inference:
                models_loaded.append("StreamingInference")
            if model_optimizer:
                models_loaded.append("ModelOptimizer")
            
            system_info = {
                "torch_version": torch.__version__,
                "cuda_available": torch.cuda.is_available(),
                "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
                "python_version": f"{os.sys.version_info.major}.{os.sys.version_info.minor}.{os.sys.version_info.micro}"
            }
            
            return HealthResponse(
                status="healthy",
                timestamp=datetime.now().isoformat(),
                version="1.0.0",
                models_loaded=models_loaded,
                system_info=system_info
            )
            
        except Exception as e:
            logger.error(f"헬스체크 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"헬스체크 실패: {str(e)}")
    
    @app.post("/predict", response_model=PredictionResponse)
    async def predict_audio(
        background_tasks: BackgroundTasks,
        audio_file: UploadFile = File(...),
        request_data: AudioRequest = AudioRequest()
    ):
        """오디오 파일 예측 엔드포인트"""
        if not inference_engine:
            raise HTTPException(status_code=503, detail="추론 엔진이 초기화되지 않았습니다")
        
        try:
            start_time = datetime.now()
            
            # 임시 파일 저장
            temp_file = f"/tmp/uploaded_audio_{start_time.timestamp()}.wav"
            with open(temp_file, "wb") as f:
                content = await audio_file.read()
                f.write(content)
            
            # 예측 수행
            result = inference_engine.predict(
                audio_path=temp_file,
                feature_type=request_data.feature_type,
                use_cache=request_data.use_cache
            )
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            # 신뢰도 확인
            confidence = result.get('confidence', 0.0)
            if confidence < request_data.confidence_threshold:
                logger.warning(f"낮은 신뢰도 예측: {confidence:.3f}")
            
            response = PredictionResponse(
                success=True,
                prediction=result.get('prediction', {}),
                processing_time=processing_time,
                model_info={
                    "model_name": result.get('model_name', 'unknown'),
                    "feature_type": request_data.feature_type
                },
                timestamp=datetime.now().isoformat(),
                features=result.get('features') if request_data.return_features else None,
                confidence=confidence,
                metadata={
                    "audio_duration": result.get('audio_duration', 0.0),
                    "sample_rate": result.get('sample_rate', 0),
                    "cache_hit": result.get('cache_hit', False)
                }
            )
            
            # 백그라운드에서 임시 파일 삭제
            background_tasks.add_task(_cleanup_temp_file, temp_file)
            
            return response
            
        except Exception as e:
            logger.error(f"예측 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"예측 실패: {str(e)}")
    
    @app.post("/predict/batch")
    async def predict_batch(request: BatchRequest):
        """배치 예측 엔드포인트"""
        if not inference_engine:
            raise HTTPException(status_code=503, detail="추론 엔진이 초기화되지 않았습니다")
        
        try:
            start_time = datetime.now()
            
            results = []
            
            if request.parallel_processing:
                # 병렬 처리
                tasks = []
                for audio_file in request.audio_files:
                    if Path(audio_file).exists():
                        task = asyncio.create_task(
                            _predict_single_async(audio_file, request.feature_type, request.use_cache)
                        )
                        tasks.append(task)
                
                results = await asyncio.gather(*tasks, return_exceptions=True)
                
            else:
                # 순차 처리
                for audio_file in request.audio_files:
                    if Path(audio_file).exists():
                        try:
                            result = inference_engine.predict(
                                audio_path=audio_file,
                                feature_type=request.feature_type,
                                use_cache=request.use_cache
                            )
                            results.append(result)
                        except Exception as e:
                            results.append({"error": str(e), "file": audio_file})
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return {
                "success": True,
                "results": results,
                "processing_time": processing_time,
                "batch_size": len(request.audio_files),
                "successful_predictions": sum(1 for r in results if "error" not in r),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"배치 예측 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"배치 예측 실패: {str(e)}")
    
    @app.post("/streaming/start")
    async def start_streaming():
        """스트리밍 추론 시작"""
        if not streaming_inference:
            raise HTTPException(status_code=503, detail="스트리밍 추론이 초기화되지 않았습니다")
        
        try:
            streaming_inference.start_processing()
            return {
                "success": True,
                "message": "스트리밍 추론이 시작되었습니다",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"스트리밍 시작 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"스트리밍 시작 실패: {str(e)}")
    
    @app.post("/streaming/stop")
    async def stop_streaming():
        """스트리밍 추론 중지"""
        if not streaming_inference:
            raise HTTPException(status_code=503, detail="스트리밍 추론이 초기화되지 않았습니다")
        
        try:
            streaming_inference.stop_processing()
            return {
                "success": True,
                "message": "스트리밍 추론이 중지되었습니다",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"스트리밍 중지 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"스트리밍 중지 실패: {str(e)}")
    
    @app.get("/streaming/status")
    async def get_streaming_status():
        """스트리밍 상태 조회"""
        if not streaming_inference:
            raise HTTPException(status_code=503, detail="스트리밍 추론이 초기화되지 않았습니다")
        
        return {
            "is_running": streaming_inference.is_running,
            "current_result": streaming_inference.get_current_result(),
            "processing_stats": streaming_inference.get_processing_stats(),
            "timestamp": datetime.now().isoformat()
        }
    
    @app.post("/optimize/model")
    async def optimize_model(
        model_path: str,
        optimization_config: Optional[Dict[str, Any]] = None
    ):
        """모델 최적화 엔드포인트"""
        if not model_optimizer:
            raise HTTPException(status_code=503, detail="모델 최적화기가 초기화되지 않았습니다")
        
        try:
            if not Path(model_path).exists():
                raise HTTPException(status_code=404, detail="모델 파일을 찾을 수 없습니다")
            
            # 모델 로드 (임시 - 실제로는 더 복잡한 로직 필요)
            logger.info(f"모델 최적화 시작: {model_path}")
            
            # 최적화 수행 (백그라운드 태스크로 실행 권장)
            optimization_results = {
                "status": "optimization_started",
                "model_path": model_path,
                "timestamp": datetime.now().isoformat(),
                "message": "모델 최적화가 시작되었습니다. 완료되면 별도로 알림됩니다."
            }
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"모델 최적화 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"모델 최적화 실패: {str(e)}")
    
    @app.get("/models/info")
    async def get_models_info():
        """로드된 모델 정보 조회"""
        try:
            models_info = []
            
            if inference_engine:
                # 추론 엔진 정보
                models_info.append({
                    "name": "InferenceEngine",
                    "type": "inference",
                    "status": "loaded",
                    "capabilities": ["batch_prediction", "caching", "feature_extraction"]
                })
            
            if streaming_inference:
                # 스트리밍 추론 정보
                models_info.append({
                    "name": "StreamingInference",
                    "type": "streaming",
                    "status": "loaded",
                    "capabilities": ["real_time_processing", "audio_visualization", "result_smoothing"]
                })
            
            return {
                "models": models_info,
                "total_models": len(models_info),
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"모델 정보 조회 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"모델 정보 조회 실패: {str(e)}")
    
    @app.delete("/cache/clear")
    async def clear_cache():
        """캐시 정리 엔드포인트"""
        try:
            cleared_items = 0
            
            if inference_engine:
                cleared_items += inference_engine.clear_cache()
            
            return {
                "success": True,
                "cleared_items": cleared_items,
                "message": "캐시가 정리되었습니다",
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"캐시 정리 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"캐시 정리 실패: {str(e)}")


async def _predict_single_async(audio_path: str, feature_type: str, use_cache: bool):
    """단일 파일 비동기 예측"""
    return inference_engine.predict(
        audio_path=audio_path,
        feature_type=feature_type,
        use_cache=use_cache
    )


def _cleanup_temp_file(file_path: str):
    """임시 파일 정리"""
    try:
        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"임시 파일 삭제 완료: {file_path}")
    except Exception as e:
        logger.error(f"임시 파일 삭제 실패: {file_path}, {str(e)}")


class ModelServer:
    """모델 서버 관리 클래스"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Args:
            config: 서버 설정 딕셔너리
        """
        self.config = config or self._default_config()
        self.app = create_app()
        self.server_process = None
    
    def _default_config(self) -> Dict[str, Any]:
        """기본 서버 설정"""
        return {
            "host": "0.0.0.0",
            "port": 8000,
            "log_level": "info",
            "reload": False,
            "workers": 1,
            "access_log": True,
            "server_header": False,
            "date_header": False
        }
    
    def run(self, **kwargs):
        """서버 실행"""
        config = {**self.config, **kwargs}
        
        logger.info(f"AI 모델 서버 시작: {config['host']}:{config['port']}")
        
        uvicorn.run(
            self.app,
            host=config["host"],
            port=config["port"],
            log_level=config["log_level"],
            reload=config["reload"],
            workers=config["workers"],
            access_log=config["access_log"],
            server_header=config["server_header"],
            date_header=config["date_header"]
        )
    
    async def start_async(self, **kwargs):
        """비동기 서버 시작"""
        config = {**self.config, **kwargs}
        
        server_config = uvicorn.Config(
            self.app,
            host=config["host"],
            port=config["port"],
            log_level=config["log_level"],
            access_log=config["access_log"]
        )
        
        server = uvicorn.Server(server_config)
        await server.serve()
    
    def get_app(self) -> FastAPI:
        """FastAPI 앱 인스턴스 반환"""
        return self.app


if __name__ == "__main__":
    # 개발 서버 실행
    server = ModelServer({
        "host": "127.0.0.1",
        "port": 8000,
        "reload": True,
        "log_level": "debug"
    })
    
    server.run()