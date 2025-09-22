"""
사용자 관리 서비스 (Firebase Firestore + FCM 통합)
"""

import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
from firebase_admin import firestore, messaging
import firebase_admin
from firebase_admin import credentials

from ..models.user import (
    UserProfile, UserRegistrationRequest, UserUpdateRequest,
    FCMTokenRequest, FCMToken, FCMTokenStatus,
    CaregiverProfile, SeniorProfile, UserRole
)
from ..core.logging import get_logger

logger = get_logger(__name__)

class UserService:
    def __init__(self):
        self.db = firestore.client()
        self.users_collection = "users"
        self.fcm_tokens_collection = "fcm_tokens"

    async def register_user(self, registration_data: UserRegistrationRequest) -> UserProfile:
        """통합 회원가입 처리"""
        try:
            logger.info(f"사용자 등록 시작: {registration_data.email}")

            # 기존 사용자 확인
            existing_user = await self.get_user_by_firebase_uid(registration_data.firebase_uid)
            if existing_user:
                raise HTTPException(status_code=400, detail="이미 등록된 사용자입니다.")

            # 현재 시간
            now = datetime.utcnow()

            # 보호자 프로필 생성
            caregiver_profile = CaregiverProfile(
                name=registration_data.caregiver_name,
                phone=registration_data.caregiver_phone,
                birth_date=registration_data.caregiver_birth_date,
                gender=registration_data.caregiver_gender,
                address=registration_data.caregiver_address
            )

            # 시니어 프로필 생성
            senior_profile = SeniorProfile(
                name=registration_data.senior_name,
                phone=registration_data.senior_phone,
                birth_date=registration_data.senior_birth_date,
                gender=registration_data.senior_gender,
                address=registration_data.senior_address,
                relationship=registration_data.relationship
            )

            # FCM 토큰 처리
            fcm_tokens = []
            if registration_data.fcm_token:
                fcm_token = FCMToken(
                    token=registration_data.fcm_token,
                    device_type=registration_data.device_type or "web",
                    device_id=registration_data.device_id or f"web_{now.timestamp()}",
                    status=FCMTokenStatus.ACTIVE,
                    created_at=now,
                    updated_at=now
                )
                fcm_tokens.append(fcm_token)

            # 사용자 프로필 생성
            user_profile = UserProfile(
                user_id=registration_data.firebase_uid,
                email=registration_data.email,
                role=UserRole.CAREGIVER,
                caregiver=caregiver_profile,
                seniors=[senior_profile],
                fcm_tokens=fcm_tokens,
                created_at=now,
                updated_at=now,
                is_active=True
            )

            # Firestore에 저장
            user_doc_ref = self.db.collection(self.users_collection).document(registration_data.firebase_uid)
            user_doc_ref.set(user_profile.dict())

            # FCM 토큰 별도 저장 (푸시 알림용)
            if fcm_tokens:
                await self._save_fcm_token(registration_data.firebase_uid, fcm_tokens[0])

            logger.info(f"사용자 등록 완료: {registration_data.email}")
            return user_profile

        except Exception as e:
            logger.error(f"사용자 등록 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"사용자 등록에 실패했습니다: {str(e)}")

    async def get_user_by_firebase_uid(self, firebase_uid: str) -> Optional[UserProfile]:
        """Firebase UID로 사용자 조회"""
        try:
            user_doc = self.db.collection(self.users_collection).document(firebase_uid).get()

            if not user_doc.exists:
                return None

            user_data = user_doc.to_dict()
            return UserProfile(**user_data)

        except Exception as e:
            logger.error(f"사용자 조회 실패: {str(e)}")
            return None

    async def update_user(self, firebase_uid: str, update_data: UserUpdateRequest) -> UserProfile:
        """사용자 정보 업데이트"""
        try:
            user_doc_ref = self.db.collection(self.users_collection).document(firebase_uid)
            user_doc = user_doc_ref.get()

            if not user_doc.exists:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            # 현재 데이터 가져오기
            current_data = user_doc.to_dict()

            # 업데이트할 필드만 변경
            update_fields = {}
            if update_data.caregiver:
                update_fields["caregiver"] = update_data.caregiver.dict()
            if update_data.seniors:
                update_fields["seniors"] = [senior.dict() for senior in update_data.seniors]
            if update_data.notifications_enabled is not None:
                update_fields["notifications_enabled"] = update_data.notifications_enabled
            if update_data.voice_analysis_enabled is not None:
                update_fields["voice_analysis_enabled"] = update_data.voice_analysis_enabled
            if update_data.health_report_enabled is not None:
                update_fields["health_report_enabled"] = update_data.health_report_enabled

            update_fields["updated_at"] = datetime.utcnow()

            # Firestore 업데이트
            user_doc_ref.update(update_fields)

            # 업데이트된 데이터 반환
            updated_doc = user_doc_ref.get()
            return UserProfile(**updated_doc.to_dict())

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"사용자 업데이트 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"사용자 업데이트에 실패했습니다: {str(e)}")

    async def register_fcm_token(self, firebase_uid: str, fcm_data: FCMTokenRequest) -> Dict[str, Any]:
        """FCM 토큰 등록/업데이트"""
        try:
            logger.info(f"FCM 토큰 등록: {firebase_uid}")

            # 사용자 존재 확인
            user = await self.get_user_by_firebase_uid(firebase_uid)
            if not user:
                raise HTTPException(status_code=404, detail="사용자를 찾을 수 없습니다.")

            now = datetime.utcnow()

            # 새 FCM 토큰 생성
            fcm_token = FCMToken(
                token=fcm_data.token,
                device_type=fcm_data.device_type,
                device_id=fcm_data.device_id,
                status=FCMTokenStatus.ACTIVE,
                created_at=now,
                updated_at=now,
                last_used=now
            )

            # 기존 토큰 비활성화 (같은 디바이스)
            await self._deactivate_device_tokens(firebase_uid, fcm_data.device_id)

            # FCM 토큰 저장
            await self._save_fcm_token(firebase_uid, fcm_token)

            # 사용자 프로필에도 토큰 추가
            user_doc_ref = self.db.collection(self.users_collection).document(firebase_uid)

            # 기존 FCM 토큰 리스트에서 같은 디바이스 토큰 제거 후 새 토큰 추가
            current_tokens = user.fcm_tokens
            active_tokens = [token for token in current_tokens if token.device_id != fcm_data.device_id]
            active_tokens.append(fcm_token)

            user_doc_ref.update({
                "fcm_tokens": [token.dict() for token in active_tokens],
                "updated_at": now
            })

            return {"message": "FCM 토큰이 성공적으로 등록되었습니다.", "token_id": fcm_token.device_id}

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"FCM 토큰 등록 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"FCM 토큰 등록에 실패했습니다: {str(e)}")

    async def send_push_notification(self, firebase_uid: str, title: str, body: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """푸시 알림 전송"""
        try:
            logger.info(f"푸시 알림 전송: {firebase_uid}")

            # 사용자의 활성 FCM 토큰 조회
            fcm_tokens = await self._get_active_fcm_tokens(firebase_uid)

            if not fcm_tokens:
                return {"success": False, "message": "활성 FCM 토큰이 없습니다."}

            successful_sends = 0
            failed_tokens = []

            for token in fcm_tokens:
                try:
                    # FCM 메시지 생성
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body,
                        ),
                        data=data or {},
                        token=token.token,
                    )

                    # 메시지 전송
                    response = messaging.send(message)
                    successful_sends += 1
                    logger.info(f"FCM 메시지 전송 성공: {response}")

                    # 토큰 사용 시간 업데이트
                    await self._update_token_last_used(firebase_uid, token.device_id)

                except messaging.UnregisteredError:
                    # 토큰이 무효한 경우
                    logger.warning(f"무효한 FCM 토큰: {token.token[:20]}...")
                    failed_tokens.append(token.device_id)
                    await self._deactivate_token(firebase_uid, token.device_id)

                except Exception as e:
                    logger.error(f"FCM 메시지 전송 실패: {str(e)}")
                    failed_tokens.append(token.device_id)

            # 실패한 토큰 정리
            if failed_tokens:
                for device_id in failed_tokens:
                    await self._deactivate_token(firebase_uid, device_id)

            return {
                "success": successful_sends > 0,
                "successful_sends": successful_sends,
                "failed_tokens": len(failed_tokens),
                "total_tokens": len(fcm_tokens)
            }

        except Exception as e:
            logger.error(f"푸시 알림 전송 실패: {str(e)}")
            raise HTTPException(status_code=500, detail=f"푸시 알림 전송에 실패했습니다: {str(e)}")

    async def _save_fcm_token(self, firebase_uid: str, fcm_token: FCMToken):
        """FCM 토큰을 별도 컬렉션에 저장"""
        token_doc_ref = self.db.collection(self.fcm_tokens_collection).document(f"{firebase_uid}_{fcm_token.device_id}")
        token_data = fcm_token.dict()
        token_data["firebase_uid"] = firebase_uid
        token_doc_ref.set(token_data)

    async def _get_active_fcm_tokens(self, firebase_uid: str) -> List[FCMToken]:
        """사용자의 활성 FCM 토큰 조회"""
        tokens_query = self.db.collection(self.fcm_tokens_collection)\
            .where("firebase_uid", "==", firebase_uid)\
            .where("status", "==", FCMTokenStatus.ACTIVE.value)

        tokens_docs = tokens_query.stream()
        tokens = []

        for doc in tokens_docs:
            token_data = doc.to_dict()
            tokens.append(FCMToken(**token_data))

        return tokens

    async def _deactivate_device_tokens(self, firebase_uid: str, device_id: str):
        """특정 디바이스의 모든 토큰 비활성화"""
        tokens_query = self.db.collection(self.fcm_tokens_collection)\
            .where("firebase_uid", "==", firebase_uid)\
            .where("device_id", "==", device_id)

        tokens_docs = tokens_query.stream()

        for doc in tokens_docs:
            doc.reference.update({
                "status": FCMTokenStatus.INACTIVE.value,
                "updated_at": datetime.utcnow()
            })

    async def _deactivate_token(self, firebase_uid: str, device_id: str):
        """FCM 토큰 비활성화"""
        token_doc_ref = self.db.collection(self.fcm_tokens_collection).document(f"{firebase_uid}_{device_id}")
        token_doc_ref.update({
            "status": FCMTokenStatus.INACTIVE.value,
            "updated_at": datetime.utcnow()
        })

    async def _update_token_last_used(self, firebase_uid: str, device_id: str):
        """FCM 토큰 마지막 사용 시간 업데이트"""
        token_doc_ref = self.db.collection(self.fcm_tokens_collection).document(f"{firebase_uid}_{device_id}")
        token_doc_ref.update({
            "last_used": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

# 서비스 인스턴스
user_service = UserService()