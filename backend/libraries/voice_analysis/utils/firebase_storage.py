"""
Firebase Storage 접근을 위한 유틸리티
"""

import os
import logging
from google.cloud import storage
from google.oauth2 import service_account
import json
import base64

logger = logging.getLogger(__name__)

class FirebaseStorageClient:
    """Firebase Storage 클라이언트"""
    
    def __init__(self):
        """Firebase Storage 클라이언트 초기화"""
        self.client = None
        self.bucket = None
        self._initialize_storage()
    
    def _initialize_storage(self):
        """Storage 클라이언트 초기화"""
        try:
            # 환경 변수에서 서비스 계정 키 확인
            service_account_json = os.environ.get('GOOGLE_SERVICE_ACCOUNT_KEY')
            
            if service_account_json:
                # Base64로 인코딩된 서비스 계정 키 디코드
                try:
                    # Base64 디코딩
                    decoded_key = base64.b64decode(service_account_json)
                    credentials_dict = json.loads(decoded_key)
                except Exception as e:
                    # Base64가 아닌 경우 직접 JSON 파싱
                    logger.warning(f"Base64 디코딩 실패, JSON으로 직접 파싱: {e}")
                    credentials_dict = json.loads(service_account_json)
                
                # 서비스 계정 자격 증명 생성
                credentials = service_account.Credentials.from_service_account_info(
                    credentials_dict,
                    scopes=['https://www.googleapis.com/auth/cloud-platform']
                )
                
                # Storage 클라이언트 생성
                self.client = storage.Client(credentials=credentials)
                logger.info("Firebase Storage 클라이언트 초기화 성공 (서비스 계정 사용)")
                
            else:
                # 기본 자격 증명 사용 (로컬 개발 또는 Cloud Run)
                self.client = storage.Client()
                logger.info("Firebase Storage 클라이언트 초기화 성공 (기본 자격 증명 사용)")
            
            # 버킷 설정
            bucket_name = os.environ.get('FIREBASE_STORAGE_BUCKET', 'senior-mhealth-472007.firebasestorage.app')
            self.bucket = self.client.bucket(bucket_name)
            logger.info(f"Firebase Storage 버킷 설정: {bucket_name}")
            
        except Exception as e:
            logger.error(f"Firebase Storage 초기화 실패: {e}")
            raise
    
    def download_file(self, file_path: str) -> bytes:
        """Firebase Storage에서 파일 다운로드
        
        Args:
            file_path: Storage 내 파일 경로
            
        Returns:
            파일 바이트 데이터
        """
        try:
            blob = self.bucket.blob(file_path)
            
            # 파일 존재 확인
            if not blob.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
            # 파일 다운로드
            file_data = blob.download_as_bytes()
            logger.info(f"파일 다운로드 성공: {file_path} ({len(file_data)} bytes)")
            
            return file_data
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패: {file_path}, 오류: {e}")
            raise
    
    def generate_signed_url(self, file_path: str, expiration_minutes: int = 60) -> str:
        """Firebase Storage 파일의 서명된 URL 생성
        
        Args:
            file_path: Storage 내 파일 경로
            expiration_minutes: URL 만료 시간 (분)
            
        Returns:
            서명된 URL
        """
        try:
            blob = self.bucket.blob(file_path)
            
            # 파일 존재 확인
            if not blob.exists():
                raise FileNotFoundError(f"파일을 찾을 수 없습니다: {file_path}")
            
            # 서명된 URL 생성
            from datetime import timedelta
            url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=expiration_minutes),
                method="GET"
            )
            
            logger.info(f"서명된 URL 생성 성공: {file_path}")
            return url
            
        except Exception as e:
            logger.error(f"서명된 URL 생성 실패: {file_path}, 오류: {e}")
            raise
    
    def get_file_metadata(self, file_path: str) -> dict:
        """파일 메타데이터 조회
        
        Args:
            file_path: Storage 내 파일 경로
            
        Returns:
            파일 메타데이터
        """
        try:
            blob = self.bucket.blob(file_path)
            
            # 메타데이터 조회
            blob.reload()
            
            metadata = {
                'name': blob.name,
                'size': blob.size,
                'content_type': blob.content_type,
                'created': blob.time_created,
                'updated': blob.updated,
                'md5_hash': blob.md5_hash,
                'etag': blob.etag
            }
            
            logger.info(f"파일 메타데이터 조회 성공: {file_path}")
            return metadata
            
        except Exception as e:
            logger.error(f"파일 메타데이터 조회 실패: {file_path}, 오류: {e}")
            raise

# 싱글톤 인스턴스
_storage_client = None

def get_storage_client() -> FirebaseStorageClient:
    """Firebase Storage 클라이언트 싱글톤 반환"""
    global _storage_client
    if _storage_client is None:
        _storage_client = FirebaseStorageClient()
    return _storage_client