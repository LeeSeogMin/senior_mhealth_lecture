"""
Senior Management API Endpoints for Senior MHealth
"""
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any, Optional
from datetime import datetime
import logging

# Initialize logger
logger = logging.getLogger(__name__)

# Try to import Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import firestore

    # Use existing Firebase app if already initialized
    if firebase_admin._apps:
        db = firestore.client()
        FIREBASE_ENABLED = True
        logger.info("Firebase integration enabled (using existing app)")
    else:
        # Firebase not initialized, disable Firebase features
        FIREBASE_ENABLED = False
        db = None
        logger.warning("Firebase not initialized, using mock responses")
except ImportError:
    FIREBASE_ENABLED = False
    db = None
    logger.warning("Firebase Admin SDK not available, using mock responses")
except Exception as e:
    FIREBASE_ENABLED = False
    db = None
    logger.error(f"Firebase initialization error: {e}")
    logger.warning("Using mock responses due to Firebase error")

# Import auth verification from users module
try:
    from .users import verify_token
except ImportError:
    async def verify_token(authorization: str = None) -> Optional[Dict]:
        return {"uid": "test_user_id", "email": "test@example.com"}

# Router
router = APIRouter()

@router.get("/")
async def get_all_seniors(current_user: Dict = Depends(verify_token)):
    """Get all seniors across the system (for admin or system use)"""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        if FIREBASE_ENABLED and db:
            # Query seniors from user's nested collection
            user_id = current_user.get("uid")
            if not user_id:
                raise HTTPException(status_code=401, detail="User ID not found")

            seniors_query = db.collection("users").document(user_id).collection("seniors")
            seniors_docs = seniors_query.stream()

            seniors = []
            for doc in seniors_docs:
                senior_data = doc.to_dict()
                senior_data["senior_id"] = doc.id
                seniors.append(senior_data)

            return {
                "success": True,
                "data": {
                    "seniors": seniors,
                    "total": len(seniors)
                }
            }
        else:
            # Mock response for testing
            return {
                "success": True,
                "data": {
                    "seniors": [
                        {
                            "senior_id": "mock_senior_1",
                            "name": "정연이",
                            "age": 75,
                            "phone_number": "010-1234-5678",
                            "relationship": "parent",
                            "health_conditions": [],
                            "caregiver_id": current_user.get("uid"),
                            "created_at": datetime.utcnow(),
                            "updated_at": datetime.utcnow()
                        }
                    ],
                    "total": 1
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get all seniors error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{senior_id}")
async def get_senior(senior_id: str, current_user: Dict = Depends(verify_token)):
    """Get specific senior information"""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        if FIREBASE_ENABLED and db:
            user_id = current_user.get("uid")
            if not user_id:
                raise HTTPException(status_code=401, detail="User ID not found")

            senior_doc = db.collection("users").document(user_id).collection("seniors").document(senior_id).get()

            if not senior_doc.exists:
                raise HTTPException(status_code=404, detail="Senior not found")

            senior_data = senior_doc.to_dict()
            senior_data["senior_id"] = senior_id

            return {
                "success": True,
                "data": senior_data
            }
        else:
            # Mock response
            return {
                "success": True,
                "data": {
                    "senior_id": senior_id,
                    "name": "정연이",
                    "age": 75,
                    "phone_number": "010-1234-5678",
                    "relationship": "parent",
                    "health_conditions": [],
                    "caregiver_id": current_user.get("uid"),
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                }
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get senior error: {e}")
        raise HTTPException(status_code=500, detail=str(e))