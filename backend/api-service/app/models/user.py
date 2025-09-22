"""
사용자 모델 정의 (보호자 + 시니어 통합 관리)
"""

from pydantic import BaseModel, EmailStr, validator
from typing import Optional, List
from datetime import datetime
from enum import Enum

class GenderEnum(str, Enum):
    MALE = "male"
    FEMALE = "female"
    OTHER = "other"

class UserRole(str, Enum):
    CAREGIVER = "caregiver"
    SENIOR = "senior"
    ADMIN = "admin"

class FCMTokenStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"
    EXPIRED = "expired"

class FCMToken(BaseModel):
    """FCM 토큰 관리"""
    token: str
    device_type: str  # android, ios, web
    device_id: str
    status: FCMTokenStatus = FCMTokenStatus.ACTIVE
    created_at: datetime
    updated_at: datetime
    last_used: Optional[datetime] = None

class SeniorProfile(BaseModel):
    """시니어 프로필"""
    name: str
    phone: str
    birth_date: str  # YYYY-MM-DD format
    gender: GenderEnum
    address: Optional[str] = None
    relationship: str  # 보호자와의 관계
    medical_conditions: Optional[List[str]] = []
    emergency_contact: Optional[str] = None
    notes: Optional[str] = None

    @validator('birth_date')
    def validate_birth_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('생년월일은 YYYY-MM-DD 형식이어야 합니다')

class CaregiverProfile(BaseModel):
    """보호자 프로필"""
    name: str
    phone: str
    birth_date: str  # YYYY-MM-DD format
    gender: GenderEnum
    address: Optional[str] = None
    occupation: Optional[str] = None
    emergency_contact: Optional[str] = None

    @validator('birth_date')
    def validate_birth_date(cls, v):
        try:
            datetime.strptime(v, '%Y-%m-%d')
            return v
        except ValueError:
            raise ValueError('생년월일은 YYYY-MM-DD 형식이어야 합니다')

class UserProfile(BaseModel):
    """통합 사용자 프로필"""
    user_id: str  # Firebase Auth UID
    email: EmailStr
    role: UserRole = UserRole.CAREGIVER

    # 보호자 정보
    caregiver: CaregiverProfile

    # 시니어 정보 (보호자인 경우 관리하는 시니어들)
    seniors: List[SeniorProfile] = []

    # FCM 토큰 관리
    fcm_tokens: List[FCMToken] = []

    # 서비스 설정
    notifications_enabled: bool = True
    voice_analysis_enabled: bool = True
    health_report_enabled: bool = True

    # 메타데이터
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime] = None
    is_active: bool = True

class UserRegistrationRequest(BaseModel):
    """회원가입 요청"""
    # Firebase Auth 정보
    firebase_uid: str
    email: EmailStr

    # 보호자 정보
    caregiver_name: str
    caregiver_phone: str
    caregiver_birth_date: str
    caregiver_gender: GenderEnum
    caregiver_address: Optional[str] = None

    # 시니어 정보
    senior_name: str
    senior_phone: str
    senior_birth_date: str
    senior_gender: GenderEnum
    senior_address: Optional[str] = None
    relationship: str

    # FCM 토큰 (선택)
    fcm_token: Optional[str] = None
    device_type: Optional[str] = None
    device_id: Optional[str] = None

class UserUpdateRequest(BaseModel):
    """사용자 정보 업데이트 요청"""
    caregiver: Optional[CaregiverProfile] = None
    seniors: Optional[List[SeniorProfile]] = None
    notifications_enabled: Optional[bool] = None
    voice_analysis_enabled: Optional[bool] = None
    health_report_enabled: Optional[bool] = None

class FCMTokenRequest(BaseModel):
    """FCM 토큰 등록/업데이트 요청"""
    token: str
    device_type: str
    device_id: str

class UserResponse(BaseModel):
    """사용자 정보 응답"""
    user_id: str
    email: str
    caregiver: CaregiverProfile
    seniors: List[SeniorProfile]
    notifications_enabled: bool
    voice_analysis_enabled: bool
    health_report_enabled: bool
    created_at: datetime
    updated_at: datetime
    last_login: Optional[datetime]
    is_active: bool