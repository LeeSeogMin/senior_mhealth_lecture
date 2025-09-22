"""
Firebase Admin SDK 초기화
"""

import os
import json
import firebase_admin
from firebase_admin import credentials, firestore, messaging
from ..core.logging import get_logger

logger = get_logger(__name__)

def initialize_firebase():
    """Firebase Admin SDK 초기화"""
    try:
        if not firebase_admin._apps:
            # 환경 변수에서 서비스 계정 키 확인
            service_account_key = os.getenv("FIREBASE_SERVICE_ACCOUNT_KEY")

            if service_account_key:
                # JSON 문자열을 dict로 변환
                service_account_info = json.loads(service_account_key)
                cred = credentials.Certificate(service_account_info)
            elif os.path.exists('/app/serviceAccountKey.json'):
                # Docker 환경에서 파일로부터 로드
                cred = credentials.Certificate('/app/serviceAccountKey.json')
            else:
                # 기본 인증 (Cloud Run에서 자동)
                cred = credentials.ApplicationDefault()

            firebase_admin.initialize_app(cred, {
                'projectId': os.getenv("FIREBASE_PROJECT_ID", "senior-mhealth-472007")
            })

            logger.info("Firebase Admin SDK 초기화 완료")
        else:
            logger.info("Firebase Admin SDK 이미 초기화됨")

    except Exception as e:
        logger.error(f"Firebase Admin SDK 초기화 실패: {str(e)}")
        raise

# 앱 시작 시 Firebase 초기화
initialize_firebase()