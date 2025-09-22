"""
SincNet 모델 관리자
Firebase Storage에서 모델 다운로드 및 캐싱
"""

import os
import logging
from pathlib import Path
from typing import Optional, Dict, Any
import torch
from google.cloud import storage

logger = logging.getLogger(__name__)

class SincNetModelManager:
    """SincNet 모델 관리 클래스"""
    
    def __init__(self):
        """초기화"""
        import platform

        # 모델 파일 정보
        self.model_files = {
            'depression': 'dep_model_10500_raw.pkl',
            'insomnia': 'insom_model_38800_raw.pkl'
        }

        # Firebase Storage 설정
        self.bucket_name = 'senior-mhealth-472007.firebasestorage.app'
        self.storage_prefix = 'models/sincnet/'

        # 로컬 캐시 디렉토리 설정
        if platform.system() == 'Windows':
            # 개발 환경: 로컬 models 디렉토리 사용
            self.cache_dir = Path(__file__).parent / "models"
        else:
            # Production 환경: 임시 디렉토리 사용
            self.cache_dir = Path("/tmp/models/sincnet")

        # 캐시 디렉토리 생성
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"모델 캐시 디렉토리: {self.cache_dir}")

        # 모델 메모리 캐시
        self.models = {}

        # 초기화 시 사용 가능한 모델 확인
        self._check_available_models()

    def _check_available_models(self):
        """사용 가능한 모델 확인"""
        local_files = list(self.cache_dir.glob("*.pkl"))
        if local_files:
            logger.info(f"로컬 캐시에서 사용 가능한 모델: {[f.name for f in local_files]}")
        else:
            logger.info("로컬 캐시에 모델이 없음. Firebase Storage에서 다운로드 필요")

    def _download_model_from_storage(self, model_type: str) -> bool:
        """Firebase Storage에서 모델 다운로드"""
        try:
            filename = self.model_files[model_type]
            local_path = self.cache_dir / filename

            # 이미 존재하면 스킵
            if local_path.exists():
                logger.info(f"모델이 이미 캐시됨: {filename}")
                return True

            logger.info(f"Firebase Storage에서 모델 다운로드 시작: {filename}")

            # Firebase Storage 클라이언트 생성
            client = storage.Client()
            bucket = client.bucket(self.bucket_name)
            blob_path = f"{self.storage_prefix}{filename}"
            blob = bucket.blob(blob_path)

            # 다운로드
            blob.download_to_filename(str(local_path))

            file_size_mb = local_path.stat().st_size / 1024 / 1024
            logger.info(f"모델 다운로드 완료: {filename} ({file_size_mb:.2f} MB)")
            return True

        except Exception as e:
            logger.error(f"모델 다운로드 실패 ({model_type}): {e}")
            return False

    def _get_model_path(self, model_type: str) -> Optional[Path]:
        """모델 파일 경로 반환 (필요시 다운로드)"""
        filename = self.model_files[model_type]
        local_path = self.cache_dir / filename

        # 로컬에 없으면 다운로드
        if not local_path.exists():
            if not self._download_model_from_storage(model_type):
                return None

        return local_path
    
    def load_model(self, model_type: str, force_reload: bool = False) -> Optional[Any]:
        """모델 로드 (메모리 캐싱 지원)"""

        # 이미 메모리에 로드된 경우
        if not force_reload and model_type in self.models:
            logger.debug(f"메모리 캐시에서 모델 반환: {model_type}")
            return self.models[model_type]

        # 모델 파일 경로 확인
        model_path = self._get_model_path(model_type)
        if not model_path:
            logger.error(f"모델 디렉토리가 설정되지 않음: {model_type}")
            return None

        if not model_path.exists():
            logger.error(f"모델 파일을 찾을 수 없음: {model_path}")
            return None

        # 모델 로드
        try:
            logger.info(f"모델 로드 중: {model_path}")
            # PyTorch 모델 로드 (CPU 모드로 로드)
            model = torch.load(model_path, map_location=torch.device('cpu'))

            # 메모리 캐시에 저장
            self.models[model_type] = model
            file_size_mb = model_path.stat().st_size / 1024 / 1024
            logger.info(f"모델 로드 성공: {model_type} ({file_size_mb:.2f} MB)")
            return model

        except Exception as e:
            logger.error(f"모델 로드 실패 ({model_type}): {e}")
            return None
    
    def load_all_models(self) -> Dict[str, Any]:
        """모든 모델 로드"""
        loaded_models = {}
        
        for model_type in self.model_files.keys():
            model = self.load_model(model_type)
            if model:
                loaded_models[model_type] = model
            else:
                logger.warning(f"모델 로드 실패: {model_type}")
        
        return loaded_models
    
    def clear_memory_cache(self):
        """메모리 캐시만 클리어 (모델 파일은 그대로 유지)"""
        self.models.clear()
        logger.info("메모리 캐시 클리어 완료")

    def get_model_info(self) -> Dict[str, Any]:
        """모델 정보 반환"""
        info = {
            'cache_dir': str(self.cache_dir),
            'bucket_name': self.bucket_name,
            'storage_prefix': self.storage_prefix,
            'available_models': [],
            'loaded_models': list(self.models.keys()),
            'total_size_mb': 0
        }

        # 로컬 캐시에서 사용 가능한 모델 확인
        if self.cache_dir.exists():
            for model_file in self.cache_dir.glob("*.pkl"):
                size_mb = model_file.stat().st_size / 1024 / 1024
                info['available_models'].append({
                    'name': model_file.name,
                    'size_mb': round(size_mb, 2),
                    'cached': True
                })
                info['total_size_mb'] += size_mb

        # Firebase Storage에서 다운로드 가능한 모델 확인
        for model_type, filename in self.model_files.items():
            local_path = self.cache_dir / filename
            if not local_path.exists():
                info['available_models'].append({
                    'name': filename,
                    'size_mb': 0,  # 다운로드 전까지는 크기 모름
                    'cached': False,
                    'downloadable': True
                })

        info['total_size_mb'] = round(info['total_size_mb'], 2)
        return info

# 싱글톤 인스턴스
_model_manager = None

def get_model_manager() -> SincNetModelManager:
    """모델 매니저 싱글톤 반환"""
    global _model_manager
    if _model_manager is None:
        _model_manager = SincNetModelManager()
    return _model_manager