#!/usr/bin/env python3
"""
AI 음성 분석 서비스 메인 애플리케이션
FastAPI 기반 REST API 서비스
"""

import os
import logging
import asyncio
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from typing import Optional, Dict, Any
import json
import tempfile
from pathlib import Path
from utils.firebase_storage import get_storage_client
from analysis.pipeline.main_pipeline import SeniorMentalHealthPipeline
from analysis.utils.firestore_connector import FirestoreConnector

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 분석 파이프라인 초기화
pipeline = None
firestore_connector = None

def initialize_pipeline():
    """분석 파이프라인 초기화"""
    global pipeline, firestore_connector
    try:
        pipeline = SeniorMentalHealthPipeline()
        firestore_connector = FirestoreConnector()
        logger.info("분석 파이프라인 초기화 성공")
    except Exception as e:
        logger.error(f"파이프라인 초기화 실패: {e}")
        pipeline = None
        firestore_connector = None

# FastAPI 앱 생성
app = FastAPI(
    title="AI 음성 분석 서비스",
    description="노인 음성 분석을 위한 AI 서비스 API",
    version="1.0.0"
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 파이프라인 초기화"""
    initialize_pipeline()

# 요청 모델
class AnalysisRequest(BaseModel):
    audio_url: Optional[str] = None
    analysis_type: str = "comprehensive"
    user_id: Optional[str] = None
    call_id: Optional[str] = None
    senior_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

class AnalysisResponse(BaseModel):
    success: bool
    analysis_id: str
    status: str
    message: str
    data: Optional[Dict[str, Any]] = None

@app.get("/")
async def root():
    """루트 엔드포인트"""
    return {
        "message": "AI 음성 분석 서비스가 실행 중입니다",
        "version": "1.0.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """헬스 체크 엔드포인트"""
    return {
        "status": "healthy",
        "service": "ai-analysis-service",
        "timestamp": "2025-08-15T14:30:00Z"
    }

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_audio(request: AnalysisRequest):
    """음성 분석 API 엔드포인트"""
    try:
        logger.info(f"음성 분석 요청 수신: {request.analysis_type}")
        logger.info(f"요청 데이터: call_id={request.call_id}, senior_id={request.senior_id}, user_id={request.user_id}")
        logger.info(f"audio_url={request.audio_url}, metadata={request.metadata}")
        logger.info(f"전체 요청: {request.model_dump()}")
        
        # Firebase Storage 파일 경로 처리
        audio_file_path = None
        temp_audio_file = None
        
        if request.audio_url:
            logger.info(f"오디오 URL 수신: {request.audio_url}")
            
            # Signed URL 또는 Firebase Storage 경로 처리
            if request.audio_url.startswith('http'):
                # Signed URL인 경우 - 직접 다운로드
                logger.info("Signed URL로 파일 다운로드 시도")
                try:
                    import httpx
                    async with httpx.AsyncClient() as client:
                        response = await client.get(request.audio_url, timeout=30.0)
                        response.raise_for_status()
                        file_data = response.content
                        logger.info(f"Signed URL에서 파일 다운로드 성공: {len(file_data)} bytes")
                    
                    # 임시 파일로 저장
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                        temp_file.write(file_data)
                        temp_audio_file = temp_file.name
                        logger.info(f"임시 파일 생성: {temp_audio_file}")
                        
                except Exception as e:
                    logger.error(f"Signed URL 다운로드 실패: {e}")
                    raise HTTPException(status_code=500, detail=f"파일 다운로드 실패: {e}")
            else:
                # Firebase Storage 경로인 경우
                audio_file_path = request.audio_url
                logger.info(f"Firebase Storage 파일 경로: {audio_file_path}")
                
                try:
                    storage_client = get_storage_client()
                    file_data = storage_client.download_file(audio_file_path)
                    logger.info(f"Firebase Storage에서 파일 다운로드 성공: {len(file_data)} bytes")
                    
                    # 임시 파일로 저장
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                        temp_file.write(file_data)
                        temp_audio_file = temp_file.name
                        logger.info(f"임시 파일 생성: {temp_audio_file}")
                    
                except Exception as e:
                    logger.error(f"Firebase Storage 접근 실패: {e}")
                    raise HTTPException(status_code=500, detail=f"파일 다운로드 실패: {e}")
        else:
            logger.warning("audio_url이 제공되지 않았습니다")
            raise HTTPException(status_code=400, detail="audio_url이 필요합니다")
        
        # 분석 ID 생성
        analysis_id = f"analysis_{request.call_id or int(os.urandom(4).hex(), 16)}"
        
        # 파이프라인 상태 확인
        if not pipeline:
            logger.error("분석 파이프라인이 초기화되지 않음")
            raise HTTPException(status_code=503, detail="분석 서비스가 준비되지 않았습니다")
        
        # 실제 AI 분석 실행
        if temp_audio_file:
            try:
                logger.info("분석 파이프라인 실행 시작")
                
                # Firestore에서 시니어/사용자 정보 가져오기
                senior_info = {}
                user_info = {}
                
                if firestore_connector and request.senior_id and request.user_id:
                    try:
                        # 시니어 정보 조회 (사용자별 서브컬렉션)
                        senior_doc = firestore_connector.db.collection('users').document(request.user_id).collection('seniors').document(request.senior_id).get()
                        if senior_doc.exists:
                            senior_data = senior_doc.to_dict()
                            senior_info = {
                                'age': senior_data.get('age'),
                                'gender': senior_data.get('gender'),
                                'name': senior_data.get('name'),
                                'relationship': senior_data.get('relationship')
                            }
                            logger.info(f"시니어 정보 조회 성공: {senior_info['age']}세, {senior_info['gender']}")
                    except Exception as e:
                        logger.warning(f"시니어 정보 조회 실패: {e}")
                
                if firestore_connector and request.user_id:
                    try:
                        # 사용자(보호자) 정보 조회
                        user_doc = firestore_connector.db.collection('users').document(request.user_id).get()
                        if user_doc.exists:
                            user_data = user_doc.to_dict()
                            user_info = {
                                'age': user_data.get('age'),
                                'gender': user_data.get('gender'),
                                'name': user_data.get('name')
                            }
                            logger.info(f"사용자 정보 조회 성공: {user_info['age']}세, {user_info['gender']}")
                    except Exception as e:
                        logger.warning(f"사용자 정보 조회 실패: {e}")
                
                # 비동기 분석 실행 (DB에서 가져온 정보 포함)
                analysis_result = await pipeline.analyze(
                    audio_path=temp_audio_file,
                    user_id=request.user_id,
                    user_info={
                        'senior_id': request.senior_id,
                        'call_id': request.call_id,
                        'senior': senior_info,  # 시니어 정보 추가
                        'user': user_info       # 사용자 정보 추가
                    }
                )
                
                logger.info("분석 파이프라인 완료")
                
                # 시니어 텍스트 로깅 추가
                if 'transcription' in analysis_result and 'senior_text' in analysis_result['transcription']:
                    senior_text = analysis_result['transcription'].get('senior_text', '')
                    logger.info(f"[시니어 텍스트 추출] call_id={request.call_id}")
                    logger.info(f"[시니어 텍스트 내용] {senior_text[:500]}...")  # 처음 500자만 로깅
                
                # Firestore에 결과 저장
                if firestore_connector and request.call_id:
                    try:
                        # 비동기를 동기로 변환 (FirestoreConnector가 동기식)
                        loop = asyncio.get_event_loop()
                        await loop.run_in_executor(
                            None,
                            firestore_connector.save_analysis_result,
                            request.user_id,
                            analysis_result,
                            audio_file_path,
                            request.call_id,
                            request.senior_id
                        )
                        logger.info(f"Firestore에 분석 결과 저장 완료: {request.call_id}")
                        
                        # 5대 지표 로깅
                        if 'coreIndicators' in analysis_result:
                            indicators = analysis_result['coreIndicators']
                            logger.info("5대 지표 저장 완료:")
                            for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
                                if key in indicators:
                                    value = indicators[key].get('value', 'N/A')
                                    level = indicators[key].get('level', 'N/A')
                                    logger.info(f"  {key}: {value} ({level})")
                    except Exception as e:
                        logger.error(f"Firestore 저장 실패: {e}")
                
                # 응답 포맷 변환
                response_data = {
                    "call_id": request.call_id,
                    "results": {
                        "transcription": analysis_result.get('transcription', {}),
                        "mentalHealthAnalysis": analysis_result.get('indicators', {}),
                        "voicePatterns": analysis_result.get('voice_features', {}),
                        "sincnetAnalysis": analysis_result.get('sincnet_results', {}),
                        "summary": analysis_result.get('report', {}).get('summary', ''),
                        "recommendations": analysis_result.get('report', {}).get('recommendations', []),
                        "interpretation": analysis_result.get('comprehensive_interpretation', {}).get('overall_assessment', {}).get('summary', '')
                    },
                    "metadata": {
                        "analysis_type": request.analysis_type,
                        "processing_time": analysis_result.get('metadata', {}).get('processing_time', 0),
                        "model_version": "2.0.0",
                        "confidence": analysis_result.get('metadata', {}).get('confidence', 0)
                    }
                }
                
            except Exception as e:
                logger.error(f"분석 파이프라인 실행 오류: {e}")
                # 파이프라인 오류 시 기본 응답
                response_data = {
                    "call_id": request.call_id,
                    "results": {
                        "error": str(e),
                        "summary": "분석 중 오류가 발생했습니다.",
                        "recommendations": ["재분석을 시도해주세요."]
                    },
                    "metadata": {
                        "analysis_type": request.analysis_type,
                        "error": True
                    }
                }
            finally:
                # 임시 파일 삭제
                if temp_audio_file and os.path.exists(temp_audio_file):
                    os.remove(temp_audio_file)
                    logger.info(f"임시 파일 삭제: {temp_audio_file}")
        else:
            # 오디오 파일이 없는 경우 기본 응답
            logger.warning("오디오 파일이 제공되지 않았거나 다운로드 실패")
            response_data = {
                "call_id": request.call_id,
                "results": {
                    "summary": "오디오 파일이 제공되지 않았습니다.",
                    "recommendations": ["올바른 오디오 파일 경로를 제공해주세요."]
                },
                "metadata": {
                    "analysis_type": request.analysis_type,
                    "status": "initializing"
                }
            }
        
        response = AnalysisResponse(
            success=True,
            analysis_id=analysis_id,
            status="completed",
            message="음성 분석이 완료되었습니다",
            data=response_data
        )
        
        logger.info(f"분석 요청 처리 완료: {analysis_id}")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"음성 분석 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail=f"분석 처리 중 오류가 발생했습니다: {str(e)}")

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """오디오 파일 업로드 엔드포인트"""
    try:
        logger.info(f"오디오 파일 업로드: {file.filename}")
        
        # 파일 크기 제한 (100MB)
        if file.size and file.size > 100 * 1024 * 1024:
            raise HTTPException(status_code=400, detail="파일 크기는 100MB를 초과할 수 없습니다")
        
        # 파일 형식 검증
        allowed_extensions = ['.wav', '.mp3', '.flac', '.m4a', '.ogg']
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        if file_extension not in allowed_extensions:
            raise HTTPException(
                status_code=400, 
                detail=f"지원되지 않는 파일 형식입니다. 지원 형식: {', '.join(allowed_extensions)}"
            )
        
        # 임시 응답 (실제 구현에서는 파일 저장 및 처리)
        return {
            "success": True,
            "message": "파일 업로드가 완료되었습니다",
            "filename": file.filename,
            "file_size": file.size,
            "file_type": file.content_type
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"파일 업로드 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="파일 업로드 중 오류가 발생했습니다")

@app.get("/status/{analysis_id}")
async def get_analysis_status(analysis_id: str):
    """분석 상태 조회 엔드포인트"""
    try:
        logger.info(f"분석 상태 조회: {analysis_id}")
        
        # 임시 응답 (실제 구현에서는 데이터베이스에서 상태 조회)
        return {
            "analysis_id": analysis_id,
            "status": "completed",
            "progress": 100,
            "message": "분석이 완료되었습니다"
        }
        
    except Exception as e:
        logger.error(f"상태 조회 중 오류 발생: {str(e)}")
        raise HTTPException(status_code=500, detail="상태 조회 중 오류가 발생했습니다")

if __name__ == "__main__":
    # 포트 설정 (환경변수 또는 기본값)
    port = int(os.getenv("PORT", 8080))
    
    logger.info(f"AI 음성 분석 서비스 시작 - 포트: {port}")
    
    # uvicorn으로 서버 실행
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=False,
        log_level="info"
    )
