"""
FCM 알림 서비스
분석 완료 시 사용자에게 푸시 알림 전송
"""

import os
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Firebase Admin SDK 초기화
FIREBASE_ENABLED = False
messaging = None
firestore = None

try:
    import firebase_admin
    from firebase_admin import messaging, firestore, credentials

    # Firebase 초기화 확인
    if not firebase_admin._apps:
        try:
            # 기본 자격 증명 사용 (Google Cloud 환경에서는 자동으로 감지)
            # Storage bucket 명시적 지정
            firebase_admin.initialize_app(options={
                'storageBucket': 'senior-mhealth-472007.appspot.com',
                'projectId': 'senior-mhealth-472007'
            })
            logger.info("Firebase Admin SDK 초기화 성공")
            FIREBASE_ENABLED = True
        except Exception as e:
            logger.warning(f"Firebase Admin SDK 초기화 실패: {e} - NotificationService 비활성화")
            FIREBASE_ENABLED = False
    else:
        FIREBASE_ENABLED = True
        logger.info("Firebase Admin SDK 이미 초기화됨")

except ImportError:
    logger.warning("Firebase Admin SDK를 사용할 수 없습니다 - NotificationService 비활성화")


class NotificationService:
    """FCM 알림 전송 서비스"""

    def __init__(self):
        """NotificationService 초기화"""
        self.db = None
        if FIREBASE_ENABLED:
            try:
                # Firestore 클라이언트 초기화
                self.db = firestore.client()
                logger.info("NotificationService 초기화 완료")
            except Exception as e:
                logger.error(f"NotificationService 초기화 실패: {e}")
                self.db = None

    async def send_analysis_complete_notification(
        self,
        user_id: str,
        analysis_id: str,
        senior_name: str = "시니어",
        analysis_type: str = "comprehensive"
    ) -> bool:
        """
        분석 완료 알림 전송

        Args:
            user_id: 사용자 ID
            analysis_id: 분석 ID
            senior_name: 시니어 이름
            analysis_type: 분석 유형

        Returns:
            성공 여부
        """
        try:
            if not FIREBASE_ENABLED or not self.db:
                logger.warning("Firebase가 비활성화되어 알림을 전송할 수 없습니다")
                return False

            # 사용자의 FCM 토큰 조회
            fcm_tokens = await self._get_user_fcm_tokens(user_id)

            if not fcm_tokens:
                logger.warning(f"사용자 {user_id}의 FCM 토큰이 없습니다")
                return False

            # 알림 메시지 생성
            title = "음성 분석 완료"
            body = f"{senior_name}님의 음성 분석이 완료되었습니다. 결과를 확인해보세요."

            # 웹 URL 생성 (환경변수에서 가져오기, 기본값 설정)
            web_app_url = os.environ.get('WEB_APP_URL', 'https://web-eight-eosin.vercel.app')
            # 분석 페이지가 없으므로 메인 URL만 전송
            web_url = web_app_url

            # 알림 데이터
            data = {
                "type": "analysis_complete",
                "analysis_id": analysis_id,
                "user_id": user_id,
                "senior_name": senior_name,
                "analysis_type": analysis_type,
                "webUrl": web_url,
                "timestamp": datetime.now().isoformat()
            }

            # 각 토큰으로 알림 전송
            success_count = 0
            for token_info in fcm_tokens:
                try:
                    token = token_info.get("token")
                    if not token:
                        continue

                    # FCM 메시지 생성
                    message = messaging.Message(
                        notification=messaging.Notification(
                            title=title,
                            body=body
                        ),
                        data=data,
                        token=token,
                        android=messaging.AndroidConfig(
                            priority='high',
                            notification=messaging.AndroidNotification(
                                channel_id='analysis_complete',
                                priority='high',
                                default_vibrate_timings=True,
                                default_sound=True
                            )
                        ),
                        apns=messaging.APNSConfig(
                            payload=messaging.APNSPayload(
                                aps=messaging.Aps(
                                    alert=messaging.ApsAlert(
                                        title=title,
                                        body=body
                                    ),
                                    sound='default',
                                    badge=1
                                )
                            )
                        )
                    )

                    # 메시지 전송
                    response = messaging.send(message)
                    success_count += 1
                    logger.info(f"FCM 알림 전송 성공: {response}")

                except Exception as e:
                    logger.error(f"FCM 알림 전송 실패 (토큰: {token[:20]}...): {e}")

            # 알림 기록 저장
            await self._save_notification_history(
                user_id=user_id,
                analysis_id=analysis_id,
                title=title,
                body=body,
                data=data,
                success_count=success_count,
                total_tokens=len(fcm_tokens)
            )

            return success_count > 0

        except Exception as e:
            logger.error(f"분석 완료 알림 전송 중 오류: {e}")
            return False

    async def _get_user_fcm_tokens(self, user_id: str) -> List[Dict[str, Any]]:
        """
        사용자의 활성 FCM 토큰 조회

        Args:
            user_id: 사용자 ID

        Returns:
            FCM 토큰 목록
        """
        try:
            if not self.db:
                return []

            # 사용자 문서 조회
            user_doc = self.db.collection("users").document(user_id).get()

            if not user_doc.exists:
                logger.warning(f"사용자 {user_id}를 찾을 수 없습니다")
                return []

            user_data = user_doc.to_dict()
            fcm_tokens = user_data.get("fcm_tokens", [])

            # 활성 토큰만 필터링 (최근 30일 이내)
            active_tokens = []
            for token in fcm_tokens:
                if isinstance(token, dict) and token.get("token"):
                    # 토큰 추가 시간 확인 (옵션)
                    active_tokens.append(token)

            logger.info(f"사용자 {user_id}의 활성 FCM 토큰 {len(active_tokens)}개 조회")
            return active_tokens

        except Exception as e:
            logger.error(f"FCM 토큰 조회 실패: {e}")
            return []

    async def _save_notification_history(
        self,
        user_id: str,
        analysis_id: str,
        title: str,
        body: str,
        data: Dict[str, Any],
        success_count: int,
        total_tokens: int
    ):
        """
        알림 전송 기록 저장

        Args:
            user_id: 사용자 ID
            analysis_id: 분석 ID
            title: 알림 제목
            body: 알림 내용
            data: 알림 데이터
            success_count: 성공한 전송 수
            total_tokens: 전체 토큰 수
        """
        try:
            if not self.db:
                return

            notification_doc = {
                "user_id": user_id,
                "analysis_id": analysis_id,
                "type": "analysis_complete",
                "title": title,
                "body": body,
                "data": data,
                "success_count": success_count,
                "total_tokens": total_tokens,
                "created_at": firestore.SERVER_TIMESTAMP,
                "status": "sent" if success_count > 0 else "failed"
            }

            # notifications 컬렉션에 저장
            self.db.collection("notifications").add(notification_doc)
            logger.info(f"알림 기록 저장 완료: {user_id} -> {analysis_id}")

        except Exception as e:
            logger.error(f"알림 기록 저장 실패: {e}")

    async def send_batch_notifications(
        self,
        notifications: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        배치 알림 전송

        Args:
            notifications: 알림 목록

        Returns:
            전송 결과
        """
        try:
            if not FIREBASE_ENABLED:
                logger.warning("Firebase가 비활성화되어 배치 알림을 전송할 수 없습니다")
                return {"success": False, "message": "Firebase disabled"}

            total_sent = 0
            failed_count = 0

            for notification in notifications:
                user_id = notification.get("user_id")
                analysis_id = notification.get("analysis_id")
                senior_name = notification.get("senior_name", "시니어")

                success = await self.send_analysis_complete_notification(
                    user_id=user_id,
                    analysis_id=analysis_id,
                    senior_name=senior_name
                )

                if success:
                    total_sent += 1
                else:
                    failed_count += 1

            return {
                "success": True,
                "total_sent": total_sent,
                "failed_count": failed_count,
                "total": len(notifications)
            }

        except Exception as e:
            logger.error(f"배치 알림 전송 실패: {e}")
            return {"success": False, "error": str(e)}


# 싱글톤 인스턴스 (Firebase가 활성화된 경우에만 실제로 작동)
try:
    notification_service = NotificationService()
except Exception as e:
    logger.error(f"NotificationService 인스턴스 생성 실패: {e}")
    notification_service = None