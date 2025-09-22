"""
Analysis API Endpoints for Senior MHealth
"""
from fastapi import APIRouter, HTTPException, Depends, File, UploadFile
from typing import Dict, Any, Optional
from datetime import datetime
import logging
import os

# Initialize logger
logger = logging.getLogger(__name__)

# Try to import Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import firestore, storage

    # Firebase 초기화 확인 및 초기화
    if not firebase_admin._apps:
        try:
            # Storage bucket 명시적 지정
            firebase_admin.initialize_app(options={
                'storageBucket': 'senior-mhealth-472007.appspot.com',
                'projectId': 'senior-mhealth-472007'
            })
            logger.info("Firebase Admin SDK 초기화 성공")
        except Exception as e:
            logger.warning(f"Firebase 초기화 실패: {e}")

    # 초기화 후 클라이언트 생성
    if firebase_admin._apps:
        db = firestore.client()
        bucket = storage.bucket()
        FIREBASE_ENABLED = True
        logger.info("Firebase integration enabled for analysis")
    else:
        FIREBASE_ENABLED = False
        db = None
        bucket = None
        logger.warning("Firebase not initialized, using mock responses")
except ImportError:
    FIREBASE_ENABLED = False
    db = None
    bucket = None
    logger.warning("Firebase Admin SDK not available, using mock responses")
except Exception as e:
    FIREBASE_ENABLED = False
    db = None
    bucket = None
    logger.error(f"Firebase initialization error: {e}")

# Import auth verification from users module
try:
    from .users import verify_token
except ImportError:
    async def verify_token(authorization: str = None) -> Optional[Dict]:
        return {"uid": "test_user_id", "email": "test@example.com"}

# Router
router = APIRouter()

@router.post("/storage")
async def analyze_storage(
    data: Dict[str, Any],
    current_user: Dict = Depends(verify_token)
):
    """Handle storage-related analysis requests"""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Log the request
        logger.info(f"Storage analysis request from user {current_user.get('uid')}: {data}")

        if FIREBASE_ENABLED and db:
            # Store analysis request in Firestore
            analysis_doc = {
                "user_id": current_user.get("uid"),
                "request_data": data,
                "status": "received",
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            }

            # Add to analysis_requests collection
            doc_ref = db.collection("analysis_requests").add(analysis_doc)

            return {
                "success": True,
                "message": "Analysis request received",
                "request_id": doc_ref[1].id,
                "status": "processing"
            }
        else:
            # Mock response for testing
            return {
                "success": True,
                "message": "Analysis request received (mock)",
                "request_id": "mock_request_id",
                "status": "processing"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Storage analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/voice")
async def analyze_voice(
    file: UploadFile = File(...),
    current_user: Dict = Depends(verify_token)
):
    """Handle voice file analysis"""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        # Validate file type
        if not file.filename.lower().endswith(('.wav', '.mp3', '.m4a', '.flac')):
            raise HTTPException(status_code=400, detail="Invalid audio file format")

        logger.info(f"Voice analysis request from user {current_user.get('uid')}: {file.filename}")

        if FIREBASE_ENABLED and bucket:
            # Upload file to Firebase Storage
            blob_name = f"voice_analysis/{current_user.get('uid')}/{datetime.utcnow().isoformat()}_{file.filename}"
            blob = bucket.blob(blob_name)

            # Upload file content
            contents = await file.read()
            blob.upload_from_string(contents, content_type=file.content_type)

            # Store analysis request in Firestore
            analysis_doc = {
                "user_id": current_user.get("uid"),
                "file_name": file.filename,
                "file_path": blob_name,
                "file_size": len(contents),
                "status": "uploaded",
                "created_at": firestore.SERVER_TIMESTAMP,
                "updated_at": firestore.SERVER_TIMESTAMP
            }

            doc_ref = db.collection("voice_analysis_requests").add(analysis_doc)

            return {
                "success": True,
                "message": "Voice file uploaded for analysis",
                "request_id": doc_ref[1].id,
                "file_path": blob_name,
                "status": "processing"
            }
        else:
            # Mock response for testing
            return {
                "success": True,
                "message": "Voice file uploaded for analysis (mock)",
                "request_id": "mock_voice_request_id",
                "file_name": file.filename,
                "status": "processing"
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Voice analysis error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{request_id}")
async def get_analysis_status(
    request_id: str,
    current_user: Dict = Depends(verify_token)
):
    """Get analysis status by request ID"""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        if FIREBASE_ENABLED and db:
            # Check analysis_requests collection
            doc = db.collection("analysis_requests").document(request_id).get()

            if not doc.exists:
                # Check voice_analysis_requests collection
                doc = db.collection("voice_analysis_requests").document(request_id).get()

            if not doc.exists:
                raise HTTPException(status_code=404, detail="Analysis request not found")

            data = doc.to_dict()
            data["request_id"] = request_id

            return {
                "success": True,
                "data": data
            }
        else:
            # Mock response
            return {
                "success": True,
                "data": {
                    "request_id": request_id,
                    "status": "completed",
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get analysis status error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/results/{request_id}")
async def get_analysis_results(
    request_id: str,
    current_user: Dict = Depends(verify_token)
):
    """Get analysis results by request ID"""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        if FIREBASE_ENABLED and db:
            # Check analysis_results collection
            doc = db.collection("analysis_results").document(request_id).get()

            if not doc.exists:
                raise HTTPException(status_code=404, detail="Analysis results not found")

            data = doc.to_dict()
            data["request_id"] = request_id

            return {
                "success": True,
                "data": data
            }
        else:
            # Mock response
            return {
                "success": True,
                "data": {
                    "request_id": request_id,
                    "analysis_results": {
                        "voice_quality": "good",
                        "emotional_state": "neutral",
                        "health_indicators": []
                    },
                    "created_at": datetime.utcnow()
                }
            }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get analysis results error: {e}")
        raise HTTPException(status_code=500, detail=str(e))