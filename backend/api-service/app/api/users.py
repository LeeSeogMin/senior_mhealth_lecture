"""
User Management API Endpoints for Senior MHealth
"""
from fastapi import APIRouter, HTTPException, Header, status, Depends
from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, EmailStr
import os
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize logger
logger = logging.getLogger(__name__)

# Try to import Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth

    # Initialize Firebase Admin SDK if not already initialized
    if not firebase_admin._apps:
        # Check if service account key exists
        service_account_path = '/app/serviceAccountKey.json'
        if os.path.exists(service_account_path):
            cred = credentials.Certificate(service_account_path)
            firebase_admin.initialize_app(cred, {
                'storageBucket': 'senior-mhealth-472007.appspot.com'
            })
            logger.info("Firebase Admin SDK initialized with service account")
        else:
            # Use Application Default Credentials
            firebase_admin.initialize_app()
            logger.info("Firebase Admin SDK initialized with default credentials")

    db = firestore.client()
    FIREBASE_ENABLED = True
    logger.info("Firebase integration enabled")
except ImportError:
    logger.warning("Firebase Admin SDK not installed. Using mock data.")
    FIREBASE_ENABLED = False
    db = None
except Exception as e:
    logger.error(f"Firebase initialization error: {e}")
    FIREBASE_ENABLED = False
    db = None

# Router
router = APIRouter()

# Models
class UserRegistration(BaseModel):
    email: EmailStr
    name: str
    phone: str
    role: str = "caregiver"
    fcm_token: Optional[str] = None
    device_id: Optional[str] = None
    device_type: Optional[str] = "web"

class UserProfile(BaseModel):
    user_id: str
    email: EmailStr
    name: str
    phone: str
    role: str
    created_at: datetime
    updated_at: datetime
    fcm_tokens: Optional[List[Dict[str, Any]]] = []

class FCMToken(BaseModel):
    token: str
    device_id: str
    device_type: str = "mobile"

class SeniorData(BaseModel):
    name: str
    age: int
    phone_number: str
    relationship: str = "parent"
    health_conditions: Optional[List[str]] = []

# Helper function to verify Firebase Auth token
async def verify_token(authorization: str = Header(None)) -> Optional[Dict]:
    """Verify Firebase ID token from Authorization header"""
    if not authorization or not authorization.startswith("Bearer "):
        return None

    if not FIREBASE_ENABLED:
        # Return mock user for testing
        return {"uid": "test_user_id", "email": "test@example.com"}

    try:
        id_token = authorization.replace("Bearer ", "")
        decoded_token = auth.verify_id_token(id_token)
        return decoded_token
    except Exception as e:
        logger.error(f"Token verification error: {e}")
        return None

# Endpoints
@router.post("/register")
async def register_user(registration: UserRegistration):
    """Register a new user after Firebase Auth signup"""
    try:
        if FIREBASE_ENABLED and db:
            # Generate user ID (normally comes from Firebase Auth)
            import uuid
            user_id = str(uuid.uuid4())

            # Store user data in Firestore
            user_data = {
                "email": registration.email,
                "name": registration.name,
                "phone": registration.phone,
                "role": registration.role,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
                "fcm_tokens": []
            }

            # Add FCM token if provided
            if registration.fcm_token:
                user_data["fcm_tokens"].append({
                    "token": registration.fcm_token,
                    "device_id": registration.device_id or "unknown",
                    "device_type": registration.device_type,
                    "added_at": datetime.utcnow()
                })

            # Save to Firestore
            db.collection("users").document(user_id).set(user_data)

            return {
                "user_id": user_id,
                "email": registration.email,
                "name": registration.name,
                "phone": registration.phone,
                "role": registration.role,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
        else:
            # Mock response for testing
            return {
                "user_id": "mock_user_id",
                "email": registration.email,
                "name": registration.name,
                "phone": registration.phone,
                "role": registration.role,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
    except Exception as e:
        logger.error(f"User registration error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}")
async def get_user(user_id: str, current_user: Dict = Depends(verify_token)):
    """Get user profile"""
    try:
        if FIREBASE_ENABLED and db:
            # Get user from Firestore
            user_doc = db.collection("users").document(user_id).get()

            if not user_doc.exists:
                raise HTTPException(status_code=404, detail="User not found")

            user_data = user_doc.to_dict()
            user_data["user_id"] = user_id
            return user_data
        else:
            # Mock response
            return {
                "user_id": user_id,
                "email": "user@example.com",
                "name": "Test User",
                "phone": "010-1234-5678",
                "role": "caregiver",
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Get user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}")
async def update_user(
    user_id: str,
    user_update: Dict[str, Any],
    current_user: Dict = Depends(verify_token)
):
    """Update user profile"""
    try:
        # Verify user is updating their own profile
        if current_user and current_user.get("uid") != user_id:
            raise HTTPException(status_code=403, detail="Cannot update other user's profile")

        if FIREBASE_ENABLED and db:
            # Update Firestore
            user_update["updated_at"] = datetime.utcnow()
            db.collection("users").document(user_id).update(user_update)

            return {
                "message": "User updated successfully",
                "user_id": user_id
            }
        else:
            return {
                "message": "User updated successfully (mock)",
                "user_id": user_id
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Update user error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/fcm-token")
async def add_fcm_token(
    user_id: str,
    token_data: FCMToken,
    current_user: Dict = Depends(verify_token)
):
    """Add or update FCM token for push notifications"""
    try:
        if FIREBASE_ENABLED and db:
            # Get existing user document
            user_ref = db.collection("users").document(user_id)
            user_doc = user_ref.get()

            if not user_doc.exists:
                raise HTTPException(status_code=404, detail="User not found")

            # Get current user data
            user_data = user_doc.to_dict()
            fcm_tokens = user_data.get("fcm_tokens", [])

            # Remove old token from same device if exists
            fcm_tokens = [t for t in fcm_tokens if t.get("device_id") != token_data.device_id]

            # Add new token
            fcm_token_entry = {
                "token": token_data.token,
                "device_id": token_data.device_id,
                "device_type": token_data.device_type,
                "added_at": datetime.utcnow()
            }
            fcm_tokens.append(fcm_token_entry)

            # Update user document
            user_ref.update({
                "fcm_tokens": fcm_tokens,
                "updated_at": datetime.utcnow()
            })

            return {
                "message": "FCM token added successfully",
                "user_id": user_id
            }
        else:
            return {
                "message": "FCM token added successfully (mock)",
                "user_id": user_id
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add FCM token error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/fcm-token")
async def add_fcm_token_auth(
    token_data: Dict[str, Any],
    current_user: Dict = Depends(verify_token)
):
    """Add FCM token using authenticated user's ID"""
    try:
        if not current_user:
            raise HTTPException(status_code=401, detail="Authentication required")

        user_id = current_user.get("uid")

        if FIREBASE_ENABLED and db:
            # Get existing user document
            user_ref = db.collection("users").document(user_id)
            user_doc = user_ref.get()

            if not user_doc.exists:
                # Create user document if it doesn't exist
                user_ref.set({
                    "fcm_tokens": [],
                    "created_at": datetime.utcnow(),
                    "updated_at": datetime.utcnow()
                })
                user_doc = user_ref.get()

            # Get current tokens
            user_data = user_doc.to_dict()
            fcm_tokens = user_data.get("fcm_tokens", [])

            # Check if token already exists
            token_value = token_data.get("fcmToken")
            if not any(t.get("token") == token_value for t in fcm_tokens):
                # Add new token
                fcm_token_entry = {
                    "token": token_value,
                    "device_type": token_data.get("deviceType", "mobile"),
                    "added_at": datetime.utcnow()
                }
                fcm_tokens.append(fcm_token_entry)

            # Update user document
            user_ref.update({
                "fcm_tokens": fcm_tokens,
                "updated_at": datetime.utcnow()
            })

            return {
                "success": True,
                "message": "FCM token registered successfully",
                "user_id": user_id
            }
        else:
            return {
                "success": True,
                "message": "FCM token registered successfully (mock)",
                "user_id": user_id
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Add FCM token auth error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{caregiver_id}/seniors")
async def add_senior(
    caregiver_id: str,
    senior_data: SeniorData,
    current_user: Dict = Depends(verify_token)
):
    """Add a senior to caregiver's profile"""
    try:
        if FIREBASE_ENABLED and db:
            import uuid
            senior_id = str(uuid.uuid4())

            # Create senior document
            senior_doc = {
                "senior_id": senior_id,
                "caregiver_id": caregiver_id,
                "name": senior_data.name,
                "age": senior_data.age,
                "phone_number": senior_data.phone_number,
                "relationship": senior_data.relationship,
                "health_conditions": senior_data.health_conditions or [],
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow()
            }

            # Save to Firestore - use nested collection under user
            db.collection("users").document(caregiver_id).collection("seniors").document(senior_id).set(senior_doc)

            # Get current user document
            caregiver_ref = db.collection("users").document(caregiver_id)
            caregiver_doc = caregiver_ref.get()

            if caregiver_doc.exists:
                caregiver_data = caregiver_doc.to_dict()
                senior_ids = caregiver_data.get("senior_ids", [])
                if senior_id not in senior_ids:
                    senior_ids.append(senior_id)
                    # Update caregiver's senior list
                    caregiver_ref.update({
                        "senior_ids": senior_ids,
                        "updated_at": datetime.utcnow()
                    })

            return {
                "success": True,
                "message": "Senior added successfully",
                "data": {
                    "seniorId": senior_id,
                    "caregiverId": caregiver_id
                }
            }
        else:
            return {
                "message": "Senior added successfully (mock)",
                "caregiver_id": caregiver_id,
                "senior_id": "mock_senior_id"
            }
    except Exception as e:
        logger.error(f"Add senior error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/seniors")
async def get_seniors(
    user_id: str,
    current_user: Dict = Depends(verify_token)
):
    """Get all seniors for a caregiver"""
    try:
        logger.info(f"=== Get Seniors Request ===")
        logger.info(f"Requested user_id: {user_id}")
        logger.info(f"Current user from token: {current_user}")
        logger.info(f"Firebase enabled: {FIREBASE_ENABLED}")

        if FIREBASE_ENABLED and db:
            # Query seniors nested collection under user
            seniors_path = f"users/{user_id}/seniors"
            logger.info(f"Querying Firestore path: {seniors_path}")

            seniors_query = db.collection("users").document(user_id).collection("seniors")
            seniors_docs = seniors_query.stream()

            seniors = []
            doc_count = 0
            for doc in seniors_docs:
                doc_count += 1
                senior_data = doc.to_dict()
                senior_data["senior_id"] = doc.id
                seniors.append(senior_data)
                logger.info(f"Found senior {doc_count}: {doc.id} - {senior_data.get('name', 'NO_NAME')}")

            logger.info(f"Total seniors found: {doc_count}")

            return {
                "success": True,
                "data": {
                    "seniors": seniors,
                    "user_id": user_id
                }
            }
        else:
            return {
                "success": True,
                "data": {
                    "seniors": [],
                    "user_id": user_id
                }
            }
    except Exception as e:
        logger.error(f"Get seniors error: {e}")
        raise HTTPException(status_code=500, detail=str(e))