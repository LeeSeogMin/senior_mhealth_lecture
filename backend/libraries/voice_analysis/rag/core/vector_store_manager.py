"""
Firebase Storage 기반 벡터스토어 관리자
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import asyncio
import tempfile
import firebase_admin
from firebase_admin import credentials, storage
from firebase_admin.exceptions import FirebaseError

logger = logging.getLogger(__name__)

class FirebaseStorageVectorStore:
    """Firebase Storage 기반 벡터스토어 관리자"""
    
    def __init__(self, bucket_name: Optional[str] = None, project_id: Optional[str] = None):
        """
        Args:
            bucket_name: Firebase Storage 버킷 이름 (기본값: 프로젝트 ID + .appspot.com)
            project_id: Firebase 프로젝트 ID (기본값: 환경변수에서 가져옴)
        """
        self.project_id = project_id or os.getenv('GOOGLE_CLOUD_PROJECT')
        self.bucket_name = bucket_name or f"{self.project_id}.appspot.com"
        
        # Firebase 초기화 (이미 초기화되어 있지 않은 경우)
        try:
            firebase_admin.get_app()
            logger.info("Firebase가 이미 초기화되어 있습니다.")
        except ValueError:
            # Firebase 초기화
            cred = credentials.ApplicationDefault()
            firebase_admin.initialize_app(cred, {
                'storageBucket': self.bucket_name
            })
            logger.info(f"Firebase 초기화 완료: {self.bucket_name}")
        
        # Firebase Storage 버킷
        self.bucket = storage.bucket()
        
        # 로컬 캐시 디렉토리
        self.cache_dir = tempfile.mkdtemp(prefix="vector_store_cache_")
        
        # 파일 경로 설정
        self.embeddings_blob_name = "vector_store/embeddings.jsonl"
        self.manifest_blob_name = "vector_store/manifest.json"
        
        logger.info(f"Firebase Storage 벡터스토어 초기화: {self.bucket_name}")
        
        # 로컬 벡터스토어 경로 (develop_lee 구조에 맞춤)
        self.local_vector_store_dir = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            "analysis", "vector_store"
        )
        self.local_embeddings_path = os.path.join(self.local_vector_store_dir, "embeddings.jsonl")
        
        # 임베딩 검색을 위한 캐시
        self._embedding_cache = None
        self._cache_loaded = False
    
    async def upload_vector_store(self, local_embeddings_path: str, local_manifest_path: str) -> bool:
        """로컬 벡터스토어를 Firebase Storage에 업로드"""
        try:
            # 임베딩 파일 업로드
            embeddings_blob = self.bucket.blob(self.embeddings_blob_name)
            embeddings_blob.upload_from_filename(local_embeddings_path)
            
            # 매니페스트 파일 업로드
            manifest_blob = self.bucket.blob(self.manifest_blob_name)
            manifest_blob.upload_from_filename(local_manifest_path)
            
            logger.info(f"벡터스토어 업로드 완료: {self.bucket_name}")
            return True
            
        except FirebaseError as e:
            logger.error(f"Firebase Storage 업로드 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"벡터스토어 업로드 실패: {e}")
            return False
    
    async def download_vector_store(self, local_dir: str) -> bool:
        """Firebase Storage에서 로컬로 벡터스토어 다운로드"""
        try:
            os.makedirs(local_dir, exist_ok=True)
            
            # 임베딩 파일 다운로드
            embeddings_blob = self.bucket.blob(self.embeddings_blob_name)
            local_embeddings_path = os.path.join(local_dir, "embeddings.jsonl")
            embeddings_blob.download_to_filename(local_embeddings_path)
            
            # 매니페스트 파일 다운로드
            manifest_blob = self.bucket.blob(self.manifest_blob_name)
            local_manifest_path = os.path.join(local_dir, "manifest.json")
            manifest_blob.download_to_filename(local_manifest_path)
            
            logger.info(f"벡터스토어 다운로드 완료: {local_dir}")
            return True
            
        except FirebaseError as e:
            logger.error(f"Firebase Storage 다운로드 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"벡터스토어 다운로드 실패: {e}")
            return False
    
    async def search_similar_documents(self, 
                                     query_text: str, 
                                     keywords: List[str] = None, 
                                     max_results: int = 5, 
                                     similarity_threshold: float = 0.7) -> List[Dict]:
        """
        유사한 문서 검색
        
        Args:
            query_text: 검색할 텍스트
            keywords: 추가 키워드 필터
            max_results: 최대 반환 결과 수
            similarity_threshold: 유사도 임계값
            
        Returns:
            유사한 문서 리스트
        """
        try:
            # 로컬 임베딩 캐시 로드
            if not self._cache_loaded:
                await self._load_local_embeddings()
            
            if not self._embedding_cache:
                logger.warning("임베딩 캐시가 비어있음")
                return []
            
            # 쿼리 텍스트 임베딩 생성
            query_embedding = await self._generate_query_embedding(query_text)
            if query_embedding is None:
                return []
            
            # 유사도 계산 및 정렬
            similarities = []
            for doc in self._embedding_cache:
                similarity = self._calculate_cosine_similarity(query_embedding, doc.get('embedding', []))
                if similarity >= similarity_threshold:
                    doc_with_similarity = doc.copy()
                    doc_with_similarity['similarity'] = similarity
                    similarities.append(doc_with_similarity)
            
            # 유사도 순으로 정렬
            similarities.sort(key=lambda x: x['similarity'], reverse=True)
            
            # 키워드 필터링 (선택적)
            if keywords:
                filtered_results = []
                for doc in similarities[:max_results * 2]:  # 더 많이 검색해서 필터링
                    doc_text = doc.get('content', doc.get('text', ''))
                    if any(keyword in doc_text for keyword in keywords):
                        filtered_results.append(doc)
                        if len(filtered_results) >= max_results:
                            break
                return filtered_results
            
            return similarities[:max_results]
            
        except Exception as e:
            logger.error(f"문서 검색 실패: {e}")
            return []
    
    async def _load_local_embeddings(self):
        """로컬 임베딩 파일 로드"""
        try:
            if not os.path.exists(self.local_embeddings_path):
                logger.warning(f"로컬 임베딩 파일이 없음: {self.local_embeddings_path}")
                return
            
            embeddings = []
            with open(self.local_embeddings_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        doc = json.loads(line.strip())
                        embeddings.append(doc)
            
            self._embedding_cache = embeddings
            self._cache_loaded = True
            logger.info(f"로컬 임베딩 {len(embeddings)}개 로드 완료")
            
        except Exception as e:
            logger.error(f"로컬 임베딩 로드 실패: {e}")
            self._embedding_cache = []
    
    async def _generate_query_embedding(self, text: str) -> Optional[List[float]]:
        """쿼리 텍스트의 임베딩 생성"""
        try:
            # OpenAI 임베딩 API 사용 (기존 임베딩과 동일한 모델)
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            if not client:
                logger.error("OpenAI API 키가 설정되지 않음")
                return None
            
            response = await client.embeddings.create(
                model="text-embedding-3-small",  # 기존 임베딩과 동일한 모델
                input=text
            )
            
            return response.data[0].embedding
            
        except Exception as e:
            logger.error(f"쿼리 임베딩 생성 실패: {e}")
            return None
    
    def _calculate_cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """코사인 유사도 계산"""
        try:
            # numpy 없이도 작동하도록 기본 Python 구현
            if not vec1 or not vec2 or len(vec1) != len(vec2):
                return 0.0
            
            # 내적 계산
            dot_product = sum(a * b for a, b in zip(vec1, vec2))
            
            # 벡터 크기 계산
            norm1 = sum(a * a for a in vec1) ** 0.5
            norm2 = sum(b * b for b in vec2) ** 0.5
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
            
            # 코사인 유사도 계산
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"코사인 유사도 계산 실패: {e}")
            return 0.0
    
    async def get_manifest(self) -> Optional[Dict[str, Any]]:
        """매니페스트 정보 조회"""
        try:
            manifest_blob = self.bucket.blob(self.manifest_blob_name)
            manifest_content = manifest_blob.download_as_text()
            return json.loads(manifest_content)
        except FirebaseError as e:
            logger.error(f"Firebase Storage 매니페스트 조회 실패: {e}")
            return None
        except Exception as e:
            logger.error(f"매니페스트 조회 실패: {e}")
            return None
    
    async def check_vector_store_exists(self) -> bool:
        """벡터스토어 존재 여부 확인"""
        try:
            embeddings_blob = self.bucket.blob(self.embeddings_blob_name)
            return embeddings_blob.exists()
        except FirebaseError as e:
            logger.error(f"Firebase Storage 존재 확인 실패: {e}")
            return False
        except Exception as e:
            logger.error(f"벡터스토어 존재 확인 실패: {e}")
            return False
    
    async def get_vector_store_info(self) -> Dict[str, Any]:
        """벡터스토어 정보 조회"""
        try:
            embeddings_blob = self.bucket.blob(self.embeddings_blob_name)
            manifest_blob = self.bucket.blob(self.manifest_blob_name)
            
            info = {
                'bucket_name': self.bucket_name,
                'embeddings_exists': embeddings_blob.exists(),
                'manifest_exists': manifest_blob.exists(),
                'embeddings_size': embeddings_blob.size if embeddings_blob.exists() else 0,
                'manifest_size': manifest_blob.size if manifest_blob.exists() else 0,
                'last_updated': None
            }
            
            if manifest_blob.exists():
                manifest = await self.get_manifest()
                if manifest:
                    info['last_updated'] = manifest.get('created_at')
                    info['file_count'] = len(manifest.get('files', []))
                    info['model'] = manifest.get('model')
            
            return info
            
        except FirebaseError as e:
            logger.error(f"Firebase Storage 정보 조회 실패: {e}")
            return {'error': str(e)}
        except Exception as e:
            logger.error(f"벡터스토어 정보 조회 실패: {e}")
            return {'error': str(e)}
    
    async def load_index(self):
        """Firebase Storage에서 임베딩 인덱스 로드"""
        try:
            from .text_analysis import EmbeddingIndex
            
            # 임시 디렉토리에 다운로드
            temp_dir = tempfile.mkdtemp(prefix="vector_store_temp_")
            success = await self.download_vector_store(temp_dir)
            
            if success:
                embeddings_path = os.path.join(temp_dir, "embeddings.jsonl")
                if os.path.exists(embeddings_path):
                    return EmbeddingIndex(embeddings_path)
            
            return None
            
        except Exception as e:
            logger.error(f"임베딩 인덱스 로드 실패: {e}")
            return None

class VectorStoreDeployer:
    """벡터스토어 배포 관리자"""
    
    def __init__(self, bucket_name: Optional[str] = None, project_id: Optional[str] = None):
        self.firebase_store = FirebaseStorageVectorStore(bucket_name, project_id)
    
    async def deploy_vector_store(self, local_vector_store_dir: str) -> bool:
        """벡터스토어 배포"""
        try:
            local_embeddings_path = os.path.join(local_vector_store_dir, "embeddings.jsonl")
            local_manifest_path = os.path.join(local_vector_store_dir, "manifest.json")
            
            if not os.path.exists(local_embeddings_path):
                logger.error(f"임베딩 파일이 없습니다: {local_embeddings_path}")
                return False
            
            if not os.path.exists(local_manifest_path):
                logger.error(f"매니페스트 파일이 없습니다: {local_manifest_path}")
                return False
            
            # Firebase Storage에 업로드
            success = await self.firebase_store.upload_vector_store(
                local_embeddings_path, 
                local_manifest_path
            )
            
            if success:
                logger.info("벡터스토어 배포 완료")
                return True
            else:
                logger.error("벡터스토어 배포 실패")
                return False
                
        except Exception as e:
            logger.error(f"벡터스토어 배포 중 오류: {e}")
            return False
    
    async def verify_deployment(self) -> Dict[str, Any]:
        """배포 검증"""
        return await self.firebase_store.get_vector_store_info()
