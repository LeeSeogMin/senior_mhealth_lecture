"""
개선된 분석 스키마 테스트
5대 핵심 지표 및 통합 스키마 검증
"""

import unittest
import sys
import os
import json
from datetime import datetime
from typing import Dict, Any

# 프로젝트 루트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from analysis.core.indicators import MentalHealthIndicators, IndicatorCalculator
from analysis.utils.firestore_connector import FirestoreConnector

class TestImprovedSchema(unittest.TestCase):
    """개선된 스키마 테스트 클래스"""
    
    def setUp(self):
        """테스트 초기화"""
        self.calculator = IndicatorCalculator()
        
        # 테스트용 데이터
        self.test_voice_features = {
            'pitch_mean': 150,
            'pitch_std': 25,
            'energy_mean': 0.12,
            'energy_std': 0.04,
            'speaking_rate': 3.2,
            'pause_ratio': 0.25,
            'zcr_mean': 0.055,
            'tremor_amplitude': 0.02,
            'voice_clarity': 0.75
        }
        
        self.test_text_analysis = {
            'analysis': {
                'indicators': {
                    'DRI': 0.65,
                    'SDI': 0.70,
                    'CFL': 0.72,
                    'ES': 0.68,
                    'OV': 0.69
                }
            }
        }
        
        self.test_sincnet_results = {
            'depression_probability': 0.25,
            'insomnia_probability': 0.30
        }
    
    def test_indicator_calculation(self):
        """5대 지표 계산 테스트"""
        indicators = self.calculator.calculate(
            voice_features=self.test_voice_features,
            text_analysis=self.test_text_analysis,
            sincnet_results=self.test_sincnet_results
        )
        
        # 지표 타입 확인
        self.assertIsInstance(indicators, MentalHealthIndicators)
        
        # 각 지표가 0-1 범위인지 확인
        for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
            value = getattr(indicators, key)
            self.assertGreaterEqual(value, 0.0)
            self.assertLessEqual(value, 1.0)
            print(f"{key}: {value:.3f}")
    
    def test_indicator_levels(self):
        """지표 레벨 판정 테스트"""
        test_cases = [
            (0.15, 'DRI', 'critical'),
            (0.35, 'SDI', 'high'),
            (0.55, 'CFL', 'moderate'),
            (0.75, 'ES', 'low'),
            (0.85, 'OV', 'normal')
        ]
        
        for value, indicator_type, expected_level in test_cases:
            level = self.calculator.get_indicator_level(value, indicator_type)
            self.assertEqual(level, expected_level)
            print(f"{indicator_type} = {value:.2f} -> {level}")
    
    def test_indicator_confidence(self):
        """지표 신뢰도 계산 테스트"""
        for indicator_type in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
            confidence = self.calculator.calculate_indicator_confidence(
                indicator_type,
                librosa_data=self.test_voice_features,
                gpt4o_data=self.test_text_analysis,
                sincnet_data=self.test_sincnet_results
            )
            
            self.assertGreaterEqual(confidence, 0.0)
            self.assertLessEqual(confidence, 1.0)
            print(f"{indicator_type} confidence: {confidence:.3f}")
    
    def test_improved_schema_format(self):
        """개선된 스키마 포맷 테스트"""
        # 지표 계산
        indicators = self.calculator.calculate(
            voice_features=self.test_voice_features,
            text_analysis=self.test_text_analysis,
            sincnet_results=self.test_sincnet_results
        )
        
        # 개선된 스키마 생성
        improved_schema = {
            'analysisId': 'test_analysis_001',
            'callId': 'call_001',
            'userId': 'user_001',
            'seniorId': 'senior_001',
            'coreIndicators': {},
            'analysisMethodologies': {
                'librosa': {
                    'weight': 0.3,
                    'confidence': 0.75,
                    'features': self.test_voice_features
                },
                'gpt4o': {
                    'weight': 0.4,
                    'confidence': 0.82,
                    'transcription': {
                        'text': '테스트 음성 전사',
                        'confidence': 0.95,
                        'language': 'ko'
                    }
                },
                'sincnet': {
                    'weight': 0.3,
                    'confidence': 0.88,
                    'predictions': {
                        'depression': 0.25,
                        'anxiety': 0.20,
                        'stress': 0.22
                    }
                }
            },
            'integratedResults': {
                'method': 'weighted_average',
                'weights': {
                    'librosa': 0.3,
                    'gpt4o': 0.4,
                    'sincnet': 0.3
                },
                'confidence': 0.80,
                'consensusLevel': 'high'
            },
            'metadata': {
                'processing': {
                    'totalTime': 12.5,
                    'pipelineVersion': '2.0.0'
                }
            },
            'createdAt': datetime.now().isoformat(),
            'status': 'completed'
        }
        
        # coreIndicators 채우기
        for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
            value = getattr(indicators, key)
            improved_schema['coreIndicators'][key] = {
                'value': value,
                'level': self.calculator.get_indicator_level(value, key),
                'confidence': self.calculator.calculate_indicator_confidence(
                    key,
                    librosa_data=self.test_voice_features,
                    gpt4o_data=self.test_text_analysis,
                    sincnet_data=self.test_sincnet_results
                ),
                'trend': 'stable'
            }
        
        # 스키마 구조 검증
        self.assertIn('coreIndicators', improved_schema)
        self.assertIn('analysisMethodologies', improved_schema)
        self.assertIn('integratedResults', improved_schema)
        
        # 5대 지표 존재 확인
        for key in ['DRI', 'SDI', 'CFL', 'ES', 'OV']:
            self.assertIn(key, improved_schema['coreIndicators'])
            indicator = improved_schema['coreIndicators'][key]
            self.assertIn('value', indicator)
            self.assertIn('level', indicator)
            self.assertIn('confidence', indicator)
        
        # JSON 직렬화 가능 확인
        try:
            json_str = json.dumps(improved_schema, indent=2, ensure_ascii=False)
            print("\n개선된 스키마 JSON:")
            print(json_str[:500] + "...")  # 처음 500자만 출력
        except Exception as e:
            self.fail(f"JSON 직렬화 실패: {e}")
    
    def test_risk_assessment(self):
        """위험도 평가 테스트"""
        indicators = self.calculator.calculate(
            voice_features=self.test_voice_features,
            text_analysis=self.test_text_analysis,
            sincnet_results=self.test_sincnet_results
        )
        
        risk_scores = self.calculator.calculate_risk_scores(indicators)
        
        self.assertIn('individual_risks', risk_scores)
        self.assertIn('overall_risk', risk_scores)
        self.assertIn('high_risk_indicators', risk_scores)
        self.assertIn('recommendations', risk_scores)
        
        print("\n위험도 평가 결과:")
        print(f"전체 위험도: {risk_scores['overall_risk']}")
        print(f"고위험 지표: {risk_scores['high_risk_indicators']}")
        print(f"권장사항: {risk_scores['recommendations'][:2]}")  # 처음 2개만
    
    def test_trend_tracking(self):
        """트렌드 추적 테스트"""
        # 이전 지표
        previous = MentalHealthIndicators(
            DRI=0.60, SDI=0.65, CFL=0.70, ES=0.62, OV=0.64
        )
        
        # 현재 지표
        current = self.calculator.calculate(
            voice_features=self.test_voice_features,
            text_analysis=self.test_text_analysis,
            sincnet_results=self.test_sincnet_results
        )
        
        # 변화 추적
        changes = self.calculator.track_changes(previous, current, time_delta_hours=24)
        
        self.assertIn('changes', changes)
        self.assertIn('significant_changes', changes)
        self.assertIn('overall_trend', changes)
        
        print("\n트렌드 분석:")
        print(f"전체 트렌드: {changes['overall_trend']}")
        for key, data in changes['changes'].items():
            print(f"{key}: {data['previous']:.2f} -> {data['current']:.2f} ({data['trend']})")
    
    def test_correlation_adjustment(self):
        """지표 간 상관관계 조정 테스트"""
        # 극단적인 값으로 테스트
        extreme_indicators = {
            'DRI': 0.9,  # 매우 낮은 우울
            'SDI': 0.2,  # 매우 높은 수면 장애
            'CFL': 0.8,  # 좋은 인지 기능
            'ES': 0.9,   # 높은 정서 안정
            'OV': 0.5    # 중간 활력도
        }
        
        # 검증 및 조정
        adjusted = self.calculator._validate_and_adjust(extreme_indicators)
        
        # 조정 후 일관성 확인
        dri_sdi_diff = abs(adjusted['DRI'] - adjusted['SDI'])
        self.assertLess(dri_sdi_diff, 0.5, "DRI와 SDI 간 차이가 너무 큽니다")
        
        print("\n상관관계 조정:")
        for key in extreme_indicators:
            print(f"{key}: {extreme_indicators[key]:.2f} -> {adjusted[key]:.2f}")

def run_tests():
    """테스트 실행"""
    print("=" * 60)
    print("개선된 분석 스키마 테스트 시작")
    print("=" * 60)
    
    # 테스트 스위트 생성
    suite = unittest.TestLoader().loadTestsFromTestCase(TestImprovedSchema)
    
    # 테스트 실행
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 결과 요약
    print("\n" + "=" * 60)
    print("테스트 결과 요약")
    print("=" * 60)
    print(f"실행된 테스트: {result.testsRun}")
    print(f"성공: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"실패: {len(result.failures)}")
    print(f"오류: {len(result.errors)}")
    
    if result.wasSuccessful():
        print("\n✅ 모든 테스트 통과!")
    else:
        print("\n❌ 일부 테스트 실패")
    
    return result.wasSuccessful()

if __name__ == '__main__':
    success = run_tests()
    sys.exit(0 if success else 1)