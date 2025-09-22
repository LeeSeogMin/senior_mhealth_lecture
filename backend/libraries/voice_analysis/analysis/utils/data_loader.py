"""
데이터 로더 모듈
다양한 형식의 데이터 로드 및 전처리
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Any, Optional, Union
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class DataLoader:
    """데이터 로드 및 전처리 클래스"""
    
    def __init__(self, data_dir: Optional[str] = None):
        """
        Args:
            data_dir: 데이터 디렉토리 경로
        """
        self.data_dir = Path(data_dir) if data_dir else Path.cwd() / 'data'
        self.supported_formats = ['.json', '.csv', '.xlsx', '.txt']
        
    def load_audio_metadata(self, metadata_file: str) -> Dict[str, Any]:
        """
        오디오 메타데이터 로드
        
        Args:
            metadata_file: 메타데이터 파일 경로
            
        Returns:
            메타데이터 딕셔너리
        """
        
        try:
            path = Path(metadata_file)
            
            if path.suffix == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            elif path.suffix == '.csv':
                df = pd.read_csv(path)
                metadata = df.to_dict('records')
            else:
                raise ValueError(f"지원하지 않는 형식: {path.suffix}")
            
            return {
                'status': 'success',
                'metadata': metadata,
                'count': len(metadata) if isinstance(metadata, list) else 1
            }
            
        except Exception as e:
            logger.error(f"메타데이터 로드 실패: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def load_analysis_history(
        self,
        user_id: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict]:
        """
        분석 기록 로드
        
        Args:
            user_id: 사용자 ID
            start_date: 시작 날짜 (YYYY-MM-DD)
            end_date: 종료 날짜 (YYYY-MM-DD)
            
        Returns:
            분석 기록 리스트
        """
        
        history_file = self.data_dir / 'history' / f'{user_id}.json'
        
        if not history_file.exists():
            logger.warning(f"기록 파일 없음: {history_file}")
            return []
        
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                history = json.load(f)
            
            # 날짜 필터링
            if start_date or end_date:
                filtered = []
                for record in history:
                    record_date = record.get('timestamp', '')[:10]
                    
                    if start_date and record_date < start_date:
                        continue
                    if end_date and record_date > end_date:
                        continue
                    
                    filtered.append(record)
                
                history = filtered
            
            # 시간 순 정렬
            history.sort(key=lambda x: x.get('timestamp', ''))
            
            return history
            
        except Exception as e:
            logger.error(f"기록 로드 실패: {e}")
            return []
    
    def save_analysis_result(
        self,
        user_id: str,
        result: Dict,
        audio_path: Optional[str] = None
    ) -> bool:
        """
        분석 결과 저장
        
        Args:
            user_id: 사용자 ID
            result: 분석 결과
            audio_path: 오디오 파일 경로
            
        Returns:
            저장 성공 여부
        """
        
        try:
            # 저장 디렉토리 생성
            history_dir = self.data_dir / 'history'
            history_dir.mkdir(parents=True, exist_ok=True)
            
            # 기존 기록 로드
            history_file = history_dir / f'{user_id}.json'
            if history_file.exists():
                with open(history_file, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = []
            
            # 새 결과 추가
            record = {
                'timestamp': datetime.now().isoformat(),
                'audio_path': audio_path,
                'indicators': result.get('indicators', {}),
                'risk_assessment': result.get('risk_assessment', {}),
                'processing_time': result.get('processing_time', 0)
            }
            
            history.append(record)
            
            # 저장
            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
            
            logger.info(f"분석 결과 저장 완료: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"결과 저장 실패: {e}")
            return False
    
    def load_user_profile(self, user_id: str) -> Dict[str, Any]:
        """
        사용자 프로필 로드
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            사용자 프로필 정보
        """
        
        profile_file = self.data_dir / 'profiles' / f'{user_id}.json'
        
        if not profile_file.exists():
            # 기본 프로필 생성
            return {
                'user_id': user_id,
                'created_at': datetime.now().isoformat(),
                'age': None,
                'gender': None,
                'medical_history': [],
                'preferences': {}
            }
        
        try:
            with open(profile_file, 'r', encoding='utf-8') as f:
                profile = json.load(f)
            return profile
        except Exception as e:
            logger.error(f"프로필 로드 실패: {e}")
            return {'user_id': user_id}
    
    def save_user_profile(self, user_id: str, profile: Dict) -> bool:
        """
        사용자 프로필 저장
        
        Args:
            user_id: 사용자 ID
            profile: 프로필 정보
            
        Returns:
            저장 성공 여부
        """
        
        try:
            profile_dir = self.data_dir / 'profiles'
            profile_dir.mkdir(parents=True, exist_ok=True)
            
            profile_file = profile_dir / f'{user_id}.json'
            
            # 타임스탬프 추가
            profile['updated_at'] = datetime.now().isoformat()
            
            with open(profile_file, 'w', encoding='utf-8') as f:
                json.dump(profile, f, ensure_ascii=False, indent=2)
            
            logger.info(f"프로필 저장 완료: {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"프로필 저장 실패: {e}")
            return False
    
    def load_batch_data(self, batch_file: str) -> List[Dict]:
        """
        배치 처리용 데이터 로드
        
        Args:
            batch_file: 배치 파일 경로
            
        Returns:
            배치 데이터 리스트
        """
        
        try:
            path = Path(batch_file)
            
            if path.suffix == '.json':
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
            elif path.suffix == '.csv':
                df = pd.read_csv(path)
                data = df.to_dict('records')
            else:
                raise ValueError(f"지원하지 않는 형식: {path.suffix}")
            
            # 데이터 검증
            validated_data = []
            for item in data:
                if self._validate_batch_item(item):
                    validated_data.append(item)
                else:
                    logger.warning(f"잘못된 배치 항목: {item}")
            
            return validated_data
            
        except Exception as e:
            logger.error(f"배치 데이터 로드 실패: {e}")
            return []
    
    def _validate_batch_item(self, item: Dict) -> bool:
        """배치 항목 검증"""
        
        required_fields = ['audio_path']
        
        for field in required_fields:
            if field not in item:
                return False
        
        # 오디오 파일 존재 확인
        audio_path = Path(item['audio_path'])
        if not audio_path.exists():
            logger.warning(f"오디오 파일 없음: {audio_path}")
            return False
        
        return True
    
    def export_results(
        self,
        results: Union[Dict, List[Dict]],
        output_path: str,
        format: str = 'json'
    ) -> bool:
        """
        결과 내보내기
        
        Args:
            results: 내보낼 결과
            output_path: 출력 경로
            format: 출력 형식 ('json', 'csv', 'excel')
            
        Returns:
            내보내기 성공 여부
        """
        
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format == 'json':
                with open(output_path, 'w', encoding='utf-8') as f:
                    json.dump(results, f, ensure_ascii=False, indent=2, default=str)
            
            elif format == 'csv':
                if isinstance(results, dict):
                    results = [results]
                
                df = pd.DataFrame(results)
                df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            elif format == 'excel':
                if isinstance(results, dict):
                    results = [results]
                
                df = pd.DataFrame(results)
                df.to_excel(output_path, index=False)
            
            else:
                raise ValueError(f"지원하지 않는 형식: {format}")
            
            logger.info(f"결과 내보내기 완료: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"결과 내보내기 실패: {e}")
            return False
    
    def load_reference_data(self, data_type: str) -> Dict[str, Any]:
        """
        참조 데이터 로드 (정상 범위, 임상 기준 등)
        
        Args:
            data_type: 데이터 유형 ('norms', 'clinical_criteria', etc.)
            
        Returns:
            참조 데이터
        """
        
        reference_file = self.data_dir / 'reference' / f'{data_type}.json'
        
        if not reference_file.exists():
            logger.warning(f"참조 데이터 없음: {reference_file}")
            return self._get_default_reference(data_type)
        
        try:
            with open(reference_file, 'r', encoding='utf-8') as f:
                reference = json.load(f)
            return reference
        except Exception as e:
            logger.error(f"참조 데이터 로드 실패: {e}")
            return self._get_default_reference(data_type)
    
    def _get_default_reference(self, data_type: str) -> Dict[str, Any]:
        """기본 참조 데이터 반환"""
        
        defaults = {
            'norms': {
                'DRI': {'mean': 0.5, 'std': 0.15, 'range': [0.3, 0.7]},
                'SDI': {'mean': 0.5, 'std': 0.15, 'range': [0.3, 0.7]},
                'CFL': {'mean': 0.6, 'std': 0.15, 'range': [0.4, 0.8]},
                'ES': {'mean': 0.5, 'std': 0.15, 'range': [0.3, 0.7]},
                'OV': {'mean': 0.5, 'std': 0.15, 'range': [0.3, 0.7]}
            },
            'clinical_criteria': {
                'depression': {'DRI': 0.3, 'ES': 0.4},
                'cognitive_impairment': {'CFL': 0.4},
                'sleep_disorder': {'SDI': 0.3}
            }
        }
        
        return defaults.get(data_type, {})