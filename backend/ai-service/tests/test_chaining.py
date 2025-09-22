"""
Integration and Load Tests for Sequential Chaining
순차 체이닝 통합 및 부하 테스트
"""

import pytest
import asyncio
import time
from pathlib import Path
import sys
import os
from typing import Dict, Any, List
import json
from datetime import datetime

# 프로젝트 경로 추가
sys.path.append(str(Path(__file__).parent.parent))

from app.chains import (
    ChainManager,
    CrisisDetector,
    TranscriptionAdapter,
    VoiceAnalysisAdapter,
    TextAnalysisAdapter,
    SincNetAdapter,
    BasicScreeningAdapter
)
from app.chains.result_integration import ResultIntegrator
from app.config import FeatureFlags, ABTestManager
from app.monitoring import ChainMetrics


class TestChaining:
    """체이닝 시스템 통합 테스트"""
    
    @pytest.fixture
    def chain_manager(self):
        """체인 관리자 fixture"""
        manager = ChainManager(cache_enabled=True)
        
        # 체인 단계 구성
        manager.add_steps([
            TranscriptionAdapter(),
            CrisisDetector(model_type='gemini'),
            BasicScreeningAdapter(),
            VoiceAnalysisAdapter(),
            TextAnalysisAdapter(),
            SincNetAdapter(),
            ResultIntegrator()
        ])
        
        return manager
    
    @pytest.fixture
    def sample_audio_path(self):
        """테스트용 오디오 파일 경로"""
        # 실제 테스트에서는 실제 오디오 파일 경로 사용
        return "tests/fixtures/audio_samples/test_audio.wav"
    
    @pytest.fixture
    def mock_transcript(self):
        """테스트용 전사 텍스트"""
        return {
            'normal': "오늘은 날씨가 좋네요. 산책을 하니 기분이 좋아졌어요.",
            'depressed': "요즘 너무 우울해요. 아무것도 하고 싶지 않고 매일이 힘들어요.",
            'crisis': "더 이상 살고 싶지 않아요. 모든 게 끝났으면 좋겠어요."
        }
    
    @pytest.mark.asyncio
    async def test_crisis_detection_speed(self, mock_transcript):
        """
        테스트 1: 위기 상황 감지 속도 (< 3초)
        """
        detector = CrisisDetector(model_type='gemini')
        
        start_time = time.time()
        context = {'transcript': mock_transcript['crisis']}
        
        result = await detector.process(None, context)
        
        execution_time = time.time() - start_time
        
        assert execution_time < 3.0, f"Crisis detection took {execution_time:.2f}s (> 3s)"
        assert result['crisis']['severity'] == 'critical'
        assert result['crisis']['immediate_action_required'] == True
    
    @pytest.mark.asyncio
    async def test_full_chain_execution(self, chain_manager, mock_transcript):
        """
        테스트 2: 정상 케이스 풀 체인 실행 (< 12초)
        """
        context = {'transcript': mock_transcript['normal']}
        
        start_time = time.time()
        result = await chain_manager.execute(None, context)
        execution_time = time.time() - start_time
        
        assert execution_time < 12.0, f"Full chain took {execution_time:.2f}s (> 12s)"
        assert 'final_indicators' in result
        assert all(key in result['final_indicators'] for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV'])
    
    @pytest.mark.asyncio
    async def test_error_fallback(self, chain_manager):
        """
        테스트 3: 에러 발생 시 fallback 동작
        """
        # 잘못된 입력으로 에러 유도
        context = {'transcript': None}  # None으로 에러 유도
        
        result = await chain_manager.execute_with_fallback(
            None, 
            context,
            fallback_handler=self._fallback_handler
        )
        
        assert result['fallback'] == True
        assert 'error' in result or 'message' in result
    
    async def _fallback_handler(self, audio_data, context, error):
        """Fallback 처리기"""
        return {
            'fallback': True,
            'error': str(error),
            'message': 'Fallback executed',
            'timestamp': datetime.now().isoformat()
        }
    
    @pytest.mark.asyncio
    async def test_concurrent_requests(self, chain_manager, mock_transcript):
        """
        테스트 4: 동시 요청 100개 처리 (부하 테스트)
        """
        async def single_request(index: int):
            context = {
                'transcript': mock_transcript['normal'],
                'user_id': f'test_user_{index}'
            }
            return await chain_manager.execute(None, context)
        
        # 100개 동시 요청
        tasks = [single_request(i) for i in range(100)]
        
        start_time = time.time()
        results = await asyncio.gather(*tasks, return_exceptions=True)
        execution_time = time.time() - start_time
        
        # 성공률 계산
        successes = sum(1 for r in results if not isinstance(r, Exception))
        success_rate = successes / len(results)
        
        assert success_rate >= 0.95, f"Success rate {success_rate:.2%} (< 95%)"
        assert execution_time < 60.0, f"100 requests took {execution_time:.2f}s (> 60s)"
    
    @pytest.mark.asyncio
    async def test_feature_flag_switching(self, mock_transcript):
        """
        테스트 5: Feature Flag 전환 시 무중단 동작
        """
        # Feature Flag 초기 설정
        FeatureFlags.update_configuration({
            'enable_chaining': False,
            'chaining_mode': 'off'
        })
        
        user_id = 'test_user_001'
        
        # 체이닝 비활성화 상태 확인
        assert FeatureFlags.should_use_chaining(user_id) == False
        
        # Feature Flag 활성화
        FeatureFlags.update_configuration({
            'enable_chaining': True,
            'chaining_mode': 'full'
        })
        
        # 체이닝 활성화 상태 확인
        assert FeatureFlags.should_use_chaining(user_id) == True
        
        # A/B 테스트 모드
        FeatureFlags.update_configuration({
            'enable_chaining': True,
            'chaining_mode': 'gradual',
            'chaining_percentage': 0.5
        })
        
        # 일부 사용자만 체이닝 사용
        test_users = [f'user_{i}' for i in range(100)]
        chaining_users = sum(1 for u in test_users if FeatureFlags.should_use_chaining(u))
        
        # 대략 50% 정도가 체이닝 사용
        assert 30 <= chaining_users <= 70, f"Unexpected distribution: {chaining_users}/100"
    
    @pytest.mark.asyncio
    async def test_cache_effectiveness(self, chain_manager, mock_transcript):
        """
        테스트 6: 캐싱 효과 검증
        """
        context = {'transcript': mock_transcript['normal']}
        
        # 첫 번째 실행
        start_time = time.time()
        result1 = await chain_manager.execute(None, context)
        first_execution = time.time() - start_time
        
        # 두 번째 실행 (캐시 사용)
        start_time = time.time()
        result2 = await chain_manager.execute(None, context)
        second_execution = time.time() - start_time
        
        # 캐시 사용으로 두 번째 실행이 더 빨라야 함
        assert second_execution < first_execution * 0.5, \
            f"Cache not effective: {second_execution:.2f}s vs {first_execution:.2f}s"
    
    @pytest.mark.asyncio
    async def test_metrics_collection(self, chain_manager, mock_transcript):
        """
        테스트 7: 메트릭 수집 검증
        """
        metrics = ChainMetrics()
        context = {'transcript': mock_transcript['normal'], 'user_id': 'test_user'}
        
        # 체인 실행
        result = await chain_manager.execute(None, context)
        
        # 메트릭 기록
        await metrics.record_execution(
            chain_name='test_chain',
            execution_time=10.5,
            api_calls=3,
            cost=0.05,
            mode='chaining',
            context=result,
            success=True
        )
        
        # 메트릭 확인
        real_time = metrics.get_real_time_metrics()
        assert real_time['chain_name'] == 'test_chain'
        assert real_time['mode'] == 'chaining'
        assert real_time['success'] == True
    
    @pytest.mark.asyncio
    async def test_ab_test_tracking(self):
        """
        테스트 8: A/B 테스트 추적
        """
        ab_manager = ABTestManager()
        
        # 테스트 결과 기록
        for i in range(200):
            user_id = f'test_user_{i}'
            ab_manager.record_result(
                user_id=user_id,
                processing_time=10.0 + (i % 5),
                success=(i % 10 != 0),
                score=80 + (i % 20)
            )
        
        # 통계 확인
        stats = ab_manager.get_statistics()
        assert 'groups' in stats
        assert len(stats['groups']) > 0
        
        # 테스트 종료 여부
        should_conclude = ab_manager.should_conclude_test(min_samples=50)
        assert should_conclude == True
        
        # 추천 확인
        recommendation = ab_manager.get_recommendation()
        assert recommendation in ['adopt', 'reject', 'continue']
    
    @pytest.mark.asyncio
    async def test_crisis_early_exit(self, chain_manager, mock_transcript):
        """
        테스트 9: 위기 상황 시 조기 종료
        """
        context = {'transcript': mock_transcript['crisis']}
        
        result = await chain_manager.execute(None, context)
        
        # 위기 감지 확인
        assert result['crisis']['severity'] == 'critical'
        
        # 조기 종료로 일부 단계가 스킵되었는지 확인
        metadata = result.get('chain_metadata', {})
        skipped = metadata.get('steps_skipped', [])
        assert len(skipped) > 0 or metadata.get('early_exit', False)
    
    @pytest.mark.asyncio
    async def test_indicator_calculation(self, chain_manager, mock_transcript):
        """
        테스트 10: 5대 지표 계산 정확성
        """
        context = {'transcript': mock_transcript['depressed']}
        
        result = await chain_manager.execute(None, context)
        
        # 5대 지표 확인
        indicators = result.get('final_indicators', {})
        assert 'DRI' in indicators  # Depression Risk Index
        assert 'SDI' in indicators  # Sleep Disorder Index
        assert 'CFL' in indicators  # Cognitive Function Level
        assert 'ES' in indicators   # Emotional Stability
        assert 'OV' in indicators   # Overall Vitality
        
        # 우울 텍스트에 대해 DRI가 높아야 함
        assert indicators['DRI']['score'] > 50
        assert indicators['DRI']['level'] in ['medium', 'high']


class TestPerformance:
    """성능 벤치마크 테스트"""
    
    @pytest.mark.benchmark
    def test_crisis_detection_benchmark(self, benchmark):
        """위기 감지 성능 벤치마크"""
        detector = CrisisDetector()
        context = {'transcript': "더 이상 살고 싶지 않아요."}
        
        result = benchmark(
            asyncio.run,
            detector.process(None, context)
        )
        
        assert result['crisis']['severity'] == 'critical'
    
    @pytest.mark.benchmark
    def test_full_chain_benchmark(self, benchmark):
        """풀 체인 성능 벤치마크"""
        manager = ChainManager()
        manager.add_steps([
            CrisisDetector(),
            BasicScreeningAdapter(),
            ResultIntegrator()
        ])
        
        context = {'transcript': "오늘은 기분이 좋아요."}
        
        result = benchmark(
            asyncio.run,
            manager.execute(None, context)
        )
        
        assert 'final_indicators' in result


if __name__ == "__main__":
    # 테스트 실행
    pytest.main([__file__, "-v", "--asyncio-mode=auto"])