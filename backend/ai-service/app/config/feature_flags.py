"""
Feature Flags for Sequential Chaining
순차 체이닝을 위한 Feature Flag 시스템
"""

import os
import hashlib
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class FeatureFlags:
    """Feature Flag 관리 클래스"""
    
    # 환경 변수에서 플래그 읽기
    ENABLE_CHAINING = os.getenv('ENABLE_CHAINING', 'false').lower() == 'true'
    CHAINING_PERCENTAGE = float(os.getenv('CHAINING_PERCENTAGE', '0.1'))  # 기본 10% 트래픽
    CHAINING_MODE = os.getenv('CHAINING_MODE', 'gradual')  # gradual, full, off
    
    # A/B 테스트 설정
    AB_TEST_ENABLED = os.getenv('AB_TEST_ENABLED', 'true').lower() == 'true'
    AB_TEST_SEED = os.getenv('AB_TEST_SEED', 'senior-mhealth-2024')
    
    # 성능 임계값
    PERFORMANCE_THRESHOLD = float(os.getenv('PERFORMANCE_THRESHOLD', '15.0'))  # 15초
    ERROR_RATE_THRESHOLD = float(os.getenv('ERROR_RATE_THRESHOLD', '0.05'))  # 5% 에러율
    
    @classmethod
    def should_use_chaining(cls, user_id: str, force: Optional[bool] = None) -> bool:
        """
        체이닝 사용 여부 결정
        
        Args:
            user_id: 사용자 ID
            force: 강제 설정 (테스트용)
            
        Returns:
            True면 체이닝 사용
        """
        # 강제 설정 확인
        if force is not None:
            logger.info(f"Forced chaining mode: {force}")
            return force
        
        # 체이닝 비활성화 상태
        if not cls.ENABLE_CHAINING or cls.CHAINING_MODE == 'off':
            return False
        
        # 전체 활성화 모드
        if cls.CHAINING_MODE == 'full':
            return True
        
        # A/B 테스트 비활성화 시 기본값
        if not cls.AB_TEST_ENABLED:
            return cls.ENABLE_CHAINING
        
        # 점진적 롤아웃 모드 - 해시 기반 결정
        if cls.CHAINING_MODE == 'gradual':
            return cls._is_in_test_group(user_id)
        
        return False
    
    @classmethod
    def _is_in_test_group(cls, user_id: str) -> bool:
        """
        사용자가 테스트 그룹에 속하는지 확인
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            True면 테스트 그룹
        """
        # 일관된 해시 생성
        hash_input = f"{user_id}{cls.AB_TEST_SEED}"
        hash_value = hashlib.md5(hash_input.encode()).hexdigest()
        
        # 해시의 첫 8자리를 정수로 변환
        hash_int = int(hash_value[:8], 16)
        
        # 백분율 계산
        percentage = (hash_int % 100) / 100.0
        
        # 테스트 그룹 여부 결정
        in_group = percentage < cls.CHAINING_PERCENTAGE
        
        logger.debug(f"User {user_id}: hash={hash_value[:8]}, percentage={percentage:.2f}, in_group={in_group}")
        
        return in_group
    
    @classmethod
    def get_configuration(cls) -> Dict[str, Any]:
        """
        현재 Feature Flag 설정 반환
        
        Returns:
            설정 딕셔너리
        """
        return {
            'enable_chaining': cls.ENABLE_CHAINING,
            'chaining_percentage': cls.CHAINING_PERCENTAGE,
            'chaining_mode': cls.CHAINING_MODE,
            'ab_test_enabled': cls.AB_TEST_ENABLED,
            'performance_threshold': cls.PERFORMANCE_THRESHOLD,
            'error_rate_threshold': cls.ERROR_RATE_THRESHOLD,
            'timestamp': datetime.now().isoformat()
        }
    
    @classmethod
    def update_configuration(cls, config: Dict[str, Any]):
        """
        런타임 설정 업데이트 (테스트용)
        
        Args:
            config: 새로운 설정
        """
        if 'enable_chaining' in config:
            cls.ENABLE_CHAINING = config['enable_chaining']
        if 'chaining_percentage' in config:
            cls.CHAINING_PERCENTAGE = config['chaining_percentage']
        if 'chaining_mode' in config:
            cls.CHAINING_MODE = config['chaining_mode']
        
        logger.info(f"Feature flags updated: {config}")
    
    @classmethod
    def get_user_group(cls, user_id: str) -> str:
        """
        사용자의 실험 그룹 반환
        
        Args:
            user_id: 사용자 ID
            
        Returns:
            'control' 또는 'treatment'
        """
        if cls.should_use_chaining(user_id):
            return 'treatment'
        return 'control'
    
    @classmethod
    def is_rollback_needed(cls, metrics: Dict[str, float]) -> bool:
        """
        메트릭 기반 롤백 필요 여부 판단
        
        Args:
            metrics: 성능 메트릭
            
        Returns:
            True면 롤백 필요
        """
        # 응답 시간 확인
        avg_response_time = metrics.get('avg_response_time', 0)
        if avg_response_time > cls.PERFORMANCE_THRESHOLD:
            logger.warning(f"Performance threshold exceeded: {avg_response_time}s > {cls.PERFORMANCE_THRESHOLD}s")
            return True
        
        # 에러율 확인
        error_rate = metrics.get('error_rate', 0)
        if error_rate > cls.ERROR_RATE_THRESHOLD:
            logger.warning(f"Error rate threshold exceeded: {error_rate} > {cls.ERROR_RATE_THRESHOLD}")
            return True
        
        return False


class ABTestManager:
    """A/B 테스트 관리자"""
    
    def __init__(self):
        """초기화"""
        self.test_results = {
            'control': {
                'count': 0,
                'total_time': 0,
                'errors': 0,
                'scores': []
            },
            'treatment': {
                'count': 0,
                'total_time': 0,
                'errors': 0,
                'scores': []
            }
        }
        self.start_time = datetime.now()
    
    def record_result(self, user_id: str, processing_time: float, 
                      success: bool, score: Optional[float] = None):
        """
        테스트 결과 기록
        
        Args:
            user_id: 사용자 ID
            processing_time: 처리 시간
            success: 성공 여부
            score: 품질 점수 (선택)
        """
        group = FeatureFlags.get_user_group(user_id)
        
        self.test_results[group]['count'] += 1
        self.test_results[group]['total_time'] += processing_time
        
        if not success:
            self.test_results[group]['errors'] += 1
        
        if score is not None:
            self.test_results[group]['scores'].append(score)
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        A/B 테스트 통계 반환
        
        Returns:
            통계 정보
        """
        stats = {
            'duration': (datetime.now() - self.start_time).total_seconds(),
            'groups': {}
        }
        
        for group, data in self.test_results.items():
            count = data['count']
            if count == 0:
                continue
            
            avg_time = data['total_time'] / count
            error_rate = data['errors'] / count
            avg_score = sum(data['scores']) / len(data['scores']) if data['scores'] else 0
            
            stats['groups'][group] = {
                'count': count,
                'avg_response_time': avg_time,
                'error_rate': error_rate,
                'avg_score': avg_score
            }
        
        # 개선율 계산
        if 'control' in stats['groups'] and 'treatment' in stats['groups']:
            control = stats['groups']['control']
            treatment = stats['groups']['treatment']
            
            stats['improvement'] = {
                'response_time': (control['avg_response_time'] - treatment['avg_response_time']) / control['avg_response_time'] * 100,
                'error_rate': (control['error_rate'] - treatment['error_rate']) / max(control['error_rate'], 0.001) * 100,
                'quality_score': (treatment['avg_score'] - control['avg_score']) / max(control['avg_score'], 0.001) * 100
            }
        
        return stats
    
    def should_conclude_test(self, min_samples: int = 100) -> bool:
        """
        테스트 종료 여부 판단
        
        Args:
            min_samples: 최소 샘플 수
            
        Returns:
            True면 테스트 종료 가능
        """
        control_count = self.test_results['control']['count']
        treatment_count = self.test_results['treatment']['count']
        
        # 최소 샘플 수 확인
        if control_count < min_samples or treatment_count < min_samples:
            return False
        
        # 통계적 유의성 확인 (간단한 버전)
        # 실제로는 더 정교한 통계 검정 필요
        total_samples = control_count + treatment_count
        if total_samples >= min_samples * 4:  # 충분한 샘플
            return True
        
        return False
    
    def get_recommendation(self) -> str:
        """
        A/B 테스트 결과 기반 추천
        
        Returns:
            'adopt' (채택), 'reject' (거부), 'continue' (계속 테스트)
        """
        if not self.should_conclude_test():
            return 'continue'
        
        stats = self.get_statistics()
        
        if 'improvement' not in stats:
            return 'continue'
        
        improvement = stats['improvement']
        
        # 응답 시간 20% 이상 개선 AND 에러율 증가 없음
        if improvement['response_time'] > 20 and improvement['error_rate'] >= 0:
            return 'adopt'
        
        # 응답 시간 악화 OR 에러율 20% 이상 증가
        if improvement['response_time'] < -10 or improvement['error_rate'] < -20:
            return 'reject'
        
        return 'continue'