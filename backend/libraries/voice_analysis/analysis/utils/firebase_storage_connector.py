"""
Firebase Storage 연동 모듈
Firebase Storage를 사용한 파일 업로드/다운로드
"""

import os
import logging
import time
from pathlib import Path
from typing import Optional, Tuple
import tempfile

logger = logging.getLogger(__name__)

# Firebase Storage 에뮬레이터 사용 여부
USE_EMULATOR = os.getenv('FIRESTORE_EMULATOR_HOST') is not None


class FirebaseStorageConnector:
    """Firebase Storage 연동 클래스"""
    
    def __init__(self, credentials_path: Optional[str] = None):
        """
        초기화
        
        Args:
            credentials_path: Firebase 서비스 계정 키 파일 경로
        """
        # 에뮬레이터 모드에서는 로컬 임시 디렉토리 사용
        if USE_EMULATOR:
            self.use_local = True
            self.temp_dir = Path(tempfile.gettempdir()) / 'firebase_storage_emulator'
            self.temp_dir.mkdir(exist_ok=True)
            logger.info(f"Firebase Storage 에뮬레이터 모드 - 로컬 디렉토리 사용: {self.temp_dir}")
        else:
            # 실제 Firebase Storage 사용 (현재는 구현하지 않음)
            self.use_local = True
            self.temp_dir = Path(tempfile.gettempdir()) / 'firebase_storage_local'
            self.temp_dir.mkdir(exist_ok=True)
            logger.info(f"Firebase Storage 로컬 모드: {self.temp_dir}")
    
    def upload_file(self, local_path: str, remote_path: str) -> str:
        """
        파일을 Firebase Storage에 업로드
        
        Args:
            local_path: 로컬 파일 경로
            remote_path: Firebase Storage 경로
            
        Returns:
            공개 URL 또는 GS URI
        """
        try:
            if self.use_local:
                # 로컬 모드: 파일을 로컬 임시 디렉토리에 복사
                import shutil
                dest_path = self.temp_dir / remote_path.replace('/', '_')
                shutil.copy2(local_path, dest_path)
                
                # 로컬 파일 경로를 GS URI처럼 반환
                gs_uri = str(dest_path)
                
                logger.info(f"파일 업로드 완료 (로컬): {dest_path}")
                logger.info(f"로컬 경로: {gs_uri}")
                
                return gs_uri
            else:
                # 실제 Firebase Storage 사용 (구현 필요)
                raise NotImplementedError("실제 Firebase Storage는 아직 구현되지 않았습니다")
            
        except Exception as e:
            logger.error(f"파일 업로드 실패: {e}")
            raise
    
    def upload_temp_audio(self, audio_path: str) -> Tuple[str, str]:
        """
        임시 오디오 파일 업로드
        
        Args:
            audio_path: 오디오 파일 경로
            
        Returns:
            (GS URI, blob name)
        """
        # 고유한 파일명 생성
        timestamp = int(time.time() * 1000)
        filename = Path(audio_path).name
        blob_name = f"temp/audio/{timestamp}_{filename}"
        
        gs_uri = self.upload_file(audio_path, blob_name)
        return gs_uri, blob_name
    
    def delete_file(self, blob_name: str):
        """
        Firebase Storage에서 파일 삭제
        
        Args:
            blob_name: 삭제할 파일 경로
        """
        try:
            if self.use_local:
                # 로컬 모드: 로컬 파일 삭제
                file_path = self.temp_dir / blob_name.replace('/', '_')
                if file_path.exists():
                    file_path.unlink()
                    logger.info(f"파일 삭제 완료 (로컬): {file_path}")
            else:
                raise NotImplementedError("실제 Firebase Storage는 아직 구현되지 않았습니다")
        except Exception as e:
            logger.warning(f"파일 삭제 실패: {e}")
    
    def download_file(self, blob_name: str, local_path: Optional[str] = None) -> str:
        """
        Firebase Storage에서 파일 다운로드
        
        Args:
            blob_name: Storage 파일 경로
            local_path: 로컬 저장 경로 (없으면 임시 파일)
            
        Returns:
            로컬 파일 경로
        """
        try:
            blob = self.bucket.blob(blob_name)
            
            if not local_path:
                # 임시 파일 생성
                suffix = Path(blob_name).suffix
                with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                    local_path = tmp.name
            
            blob.download_to_filename(local_path)
            logger.info(f"파일 다운로드 완료: {blob_name} -> {local_path}")
            
            return local_path
            
        except Exception as e:
            logger.error(f"파일 다운로드 실패: {e}")
            raise
    
    def get_gs_uri(self, blob_name: str) -> str:
        """
        GS URI 생성
        
        Args:
            blob_name: Storage 파일 경로
            
        Returns:
            GS URI
        """
        return f"gs://{self.bucket.name}/{blob_name}"
    
    def file_exists(self, blob_name: str) -> bool:
        """
        파일 존재 여부 확인
        
        Args:
            blob_name: Storage 파일 경로
            
        Returns:
            존재 여부
        """
        blob = self.bucket.blob(blob_name)
        return blob.exists()