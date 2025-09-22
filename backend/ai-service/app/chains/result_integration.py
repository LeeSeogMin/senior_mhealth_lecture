"""
Result Integration and Mental Health Indicators Calculation
결과 통합 및 5대 정신건강 지표 계산
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
import numpy as np
import asyncio
import json
import os
from openai import OpenAI

from .base_step import BaseChainStep

logger = logging.getLogger(__name__)


class ResultIntegrator(BaseChainStep):
    """체인 결과 통합 및 5대 지표 계산"""
    
    def __init__(self):
        """초기화"""
        super().__init__(name="result_integration", timeout=10.0)  # AI 호출 시간 고려

        # 5대 지표 설명
        self.indicators_info = {
            'DRI': 'Depression Risk Index - 우울 위험도',
            'SDI': 'Sleep Disorder Index - 수면 장애 지수',
            'CFL': 'Cognitive Function Level - 인지 기능 수준',
            'ES': 'Emotional Stability - 정서 안정성',
            'OV': 'Overall Vitality - 전반적 활력도'
        }

        # OpenAI 클라이언트 초기화
        self.openai_client = None
        self._init_openai_client()

    def _init_openai_client(self):
        """OpenAI 클라이언트 초기화"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized for narrative generation")
            else:
                logger.warning("OpenAI API key not found - narrative generation will be disabled")
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            self.openai_client = None

    async def process(self, audio_data: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        체인 결과 통합 및 5대 지표 계산
        
        Args:
            audio_data: 오디오 데이터
            context: 전체 체인 실행 컨텍스트
            
        Returns:
            5대 지표가 계산된 최종 컨텍스트
        """
        try:
            logger.info("Starting result integration")
            start_time = datetime.now()
            
            # 위기 상황 우선 처리
            if context.get('crisis', {}).get('severity') == 'critical':
                return self._generate_emergency_response(context)
            
            # 각 분석 결과 수집
            voice_result = context.get('voice_features', {})
            text_result = context.get('text_analysis', {})
            sincnet_result = context.get('sincnet_analysis', {})
            screening_result = context.get('basic_screening', {})
            
            # 가중치 적용 (30%, 40%, 30%)
            weights = {
                'voice': voice_result.get('weight', 0.3),
                'text': text_result.get('weight', 0.4),
                'sincnet': sincnet_result.get('weight', 0.3)
            }
            
            # 5대 지표 계산
            indicators = self._calculate_indicators(
                voice_result, text_result, sincnet_result, 
                screening_result, weights
            )
            
            # 종합 평가
            overall_assessment = self._generate_overall_assessment(indicators, context)
            
            # 추천 사항 생성
            recommendations = self._generate_recommendations(indicators, overall_assessment)

            # AI 기반 종합 해석 생성
            ai_narrative = await self._generate_ai_narrative(indicators, overall_assessment, context)

            # 결과 저장
            context['final_indicators'] = indicators
            context['overall_assessment'] = overall_assessment
            context['recommendations'] = recommendations
            context['ai_narrative'] = ai_narrative
            context['integration_metadata'] = {
                'processing_time': (datetime.now() - start_time).total_seconds(),
                'timestamp': datetime.now().isoformat(),
                'weights_used': weights
            }
            
            logger.info(f"Result integration completed in {context['integration_metadata']['processing_time']:.2f}s")
            
        except Exception as e:
            logger.error(f"Result integration failed: {e}")
            context = await self.handle_error(e, context)
            context['final_indicators'] = self._get_default_indicators()
            
        return context
    
    def _calculate_indicators(self, voice: Dict, text: Dict, sincnet: Dict, 
                             screening: Dict, weights: Dict) -> Dict[str, Any]:
        """
        5대 정신건강 지표 계산
        
        Returns:
            계산된 5대 지표
        """
        indicators = {}
        
        # 1. DRI (Depression Risk Index) - 우울 위험도
        dri_score = 0.0
        dri_confidence = 0.0
        
        # 음성 기반 우울 신호
        if voice.get('result'):
            voice_features = voice.get('result', {})
            # 느린 말속도, 긴 정지, 낮은 에너지는 우울 신호
            if voice_features.get('speech_rate', 1.0) < 0.8:
                dri_score += 0.3 * weights['voice']
            if voice_features.get('pause_ratio', 0) > 0.3:
                dri_score += 0.2 * weights['voice']
            if voice_features.get('energy_level', 1.0) < 0.5:
                dri_score += 0.5 * weights['voice']
            dri_confidence += weights['voice']
        
        # 텍스트 기반 우울 신호
        if text.get('result'):
            text_features = text.get('result', {})
            sentiment = text_features.get('sentiment')
            emotions = text_features.get('emotions', {})
            
            if sentiment == 'negative':
                dri_score += 0.4 * weights['text']
            if emotions.get('sadness', 0) > 0.5:
                dri_score += 0.6 * weights['text']
            dri_confidence += weights['text']
        
        # SincNet 기반 우울 점수
        if sincnet.get('result'):
            sincnet_features = sincnet.get('result', {})
            depression_score = sincnet_features.get('depression_score', 0)
            dri_score += depression_score * weights['sincnet']
            dri_confidence += weights['sincnet'] * sincnet_features.get('confidence', 0.5)
        
        indicators['DRI'] = {
            'score': min(max(dri_score * 100, 0), 100),  # 0-100 범위
            'confidence': dri_confidence,
            'level': self._get_risk_level(dri_score),
            'description': self.indicators_info['DRI']
        }
        
        # 2. SDI (Sleep Disorder Index) - 수면 장애 지수
        sdi_score = 0.0
        sdi_confidence = 0.0
        
        # 피로도 관련 음성 특징
        if voice.get('result'):
            voice_features = voice.get('result', {})
            # 느린 반응, 낮은 에너지
            if voice_features.get('response_time', 1.0) > 1.5:
                sdi_score += 0.5 * weights['voice']
            if voice_features.get('energy_level', 1.0) < 0.4:
                sdi_score += 0.5 * weights['voice']
            sdi_confidence += weights['voice'] * 0.7
        
        # 텍스트에서 수면 관련 키워드
        if text.get('result'):
            text_features = text.get('result', {})
            keywords = text_features.get('keywords', [])
            sleep_keywords = ['피곤', '잠', '못 자', '불면', '새벽', '졸려']
            
            if any(kw in ' '.join(keywords) for kw in sleep_keywords):
                sdi_score += 0.7 * weights['text']
            sdi_confidence += weights['text'] * 0.8
        
        indicators['SDI'] = {
            'score': min(max(sdi_score * 100, 0), 100),
            'confidence': sdi_confidence,
            'level': self._get_risk_level(sdi_score),
            'description': self.indicators_info['SDI']
        }
        
        # 3. CFL (Cognitive Function Level) - 인지 기능 수준
        cfl_score = 1.0  # 높을수록 좋음
        cfl_confidence = 0.0
        
        # 음성 명료도와 일관성
        if voice.get('result'):
            voice_features = voice.get('result', {})
            clarity = voice_features.get('clarity', 1.0)
            cfl_score *= clarity
            cfl_confidence += weights['voice']
        
        # 텍스트 일관성과 논리성
        if text.get('result'):
            text_features = text.get('result', {})
            coherence = text_features.get('coherence', 1.0)
            cfl_score *= coherence
            cfl_confidence += weights['text']
        
        indicators['CFL'] = {
            'score': min(max(cfl_score * 100, 0), 100),
            'confidence': cfl_confidence,
            'level': self._get_function_level(cfl_score),
            'description': self.indicators_info['CFL']
        }
        
        # 4. ES (Emotional Stability) - 정서 안정성
        es_score = 1.0  # 높을수록 안정적
        es_confidence = 0.0
        
        # 음성 변동성
        if voice.get('result'):
            voice_features = voice.get('result', {})
            pitch_variation = voice_features.get('pitch_variation', 0)
            # 과도한 변동은 불안정 신호
            if pitch_variation > 0.5:
                es_score *= (1 - pitch_variation)
            es_confidence += weights['voice']
        
        # 감정 변화
        if text.get('result'):
            text_features = text.get('result', {})
            emotions = text_features.get('emotions', {})
            emotion_variance = np.var(list(emotions.values())) if emotions else 0
            es_score *= max(0, 1 - emotion_variance)
            es_confidence += weights['text']
        
        indicators['ES'] = {
            'score': min(max(es_score * 100, 0), 100),
            'confidence': es_confidence,
            'level': self._get_stability_level(es_score),
            'description': self.indicators_info['ES']
        }
        
        # 5. OV (Overall Vitality) - 전반적 활력도
        # 다른 지표들의 종합
        ov_score = (
            (100 - indicators['DRI']['score']) * 0.3 +  # 낮은 우울
            (100 - indicators['SDI']['score']) * 0.2 +  # 낮은 수면장애
            indicators['CFL']['score'] * 0.2 +           # 높은 인지기능
            indicators['ES']['score'] * 0.3              # 높은 정서안정
        ) / 100
        
        indicators['OV'] = {
            'score': min(max(ov_score * 100, 0), 100),
            'confidence': np.mean([
                indicators['DRI']['confidence'],
                indicators['SDI']['confidence'],
                indicators['CFL']['confidence'],
                indicators['ES']['confidence']
            ]),
            'level': self._get_vitality_level(ov_score),
            'description': self.indicators_info['OV']
        }
        
        return indicators
    
    def _get_risk_level(self, score: float) -> str:
        """위험도 수준 판정"""
        if score >= 0.7:
            return 'high'
        elif score >= 0.4:
            return 'medium'
        else:
            return 'low'
    
    def _get_function_level(self, score: float) -> str:
        """기능 수준 판정"""
        if score >= 0.8:
            return 'excellent'
        elif score >= 0.6:
            return 'good'
        elif score >= 0.4:
            return 'fair'
        else:
            return 'poor'
    
    def _get_stability_level(self, score: float) -> str:
        """안정성 수준 판정"""
        if score >= 0.8:
            return 'stable'
        elif score >= 0.5:
            return 'moderate'
        else:
            return 'unstable'
    
    def _get_vitality_level(self, score: float) -> str:
        """활력도 수준 판정"""
        if score >= 0.8:
            return 'high'
        elif score >= 0.5:
            return 'moderate'
        else:
            return 'low'
    
    def _generate_overall_assessment(self, indicators: Dict, context: Dict) -> Dict[str, Any]:
        """
        종합 평가 생성
        """
        # 위험 지표 확인
        high_risk_indicators = []
        for key, value in indicators.items():
            if key in ['DRI', 'SDI'] and value['level'] == 'high':
                high_risk_indicators.append(key)
            elif key in ['CFL', 'ES', 'OV'] and value['level'] in ['poor', 'unstable', 'low']:
                high_risk_indicators.append(key)
        
        # 전반적 상태 평가
        if len(high_risk_indicators) >= 3:
            overall_status = 'critical'
            priority = 'immediate'
        elif len(high_risk_indicators) >= 2:
            overall_status = 'warning'
            priority = 'high'
        elif len(high_risk_indicators) >= 1:
            overall_status = 'caution'
            priority = 'medium'
        else:
            overall_status = 'stable'
            priority = 'low'
        
        return {
            'status': overall_status,
            'priority': priority,
            'high_risk_indicators': high_risk_indicators,
            'average_confidence': np.mean([ind['confidence'] for ind in indicators.values()]),
            'timestamp': datetime.now().isoformat()
        }
    
    def _generate_recommendations(self, indicators: Dict, assessment: Dict) -> List[Dict[str, Any]]:
        """
        지표 기반 추천 사항 생성
        """
        recommendations = []
        
        # DRI 기반 추천
        if indicators['DRI']['level'] == 'high':
            recommendations.append({
                'type': 'intervention',
                'urgency': 'high',
                'action': '정신건강 전문가 상담 권장',
                'reason': '높은 우울 위험도 감지'
            })
        elif indicators['DRI']['level'] == 'medium':
            recommendations.append({
                'type': 'monitoring',
                'urgency': 'medium',
                'action': '주기적 모니터링 강화',
                'reason': '중간 수준 우울 징후'
            })
        
        # SDI 기반 추천
        if indicators['SDI']['level'] == 'high':
            recommendations.append({
                'type': 'lifestyle',
                'urgency': 'medium',
                'action': '수면 패턴 개선 프로그램 참여',
                'reason': '수면 장애 징후 발견'
            })
        
        # CFL 기반 추천
        if indicators['CFL']['level'] == 'poor':
            recommendations.append({
                'type': 'assessment',
                'urgency': 'high',
                'action': '인지 기능 정밀 검사 권장',
                'reason': '인지 기능 저하 우려'
            })
        
        # ES 기반 추천
        if indicators['ES']['level'] == 'unstable':
            recommendations.append({
                'type': 'therapy',
                'urgency': 'medium',
                'action': '정서 안정화 프로그램 참여',
                'reason': '정서적 불안정성 감지'
            })
        
        # OV 기반 추천
        if indicators['OV']['level'] == 'low':
            recommendations.append({
                'type': 'comprehensive',
                'urgency': 'high',
                'action': '종합적 건강 관리 프로그램 필요',
                'reason': '전반적 활력도 저하'
            })
        
        # 우선순위 정렬
        urgency_order = {'high': 0, 'medium': 1, 'low': 2}
        recommendations.sort(key=lambda x: urgency_order.get(x['urgency'], 3))
        
        return recommendations
    
    def _generate_emergency_response(self, context: Dict) -> Dict[str, Any]:
        """
        위기 상황 응급 응답 생성
        """
        crisis = context.get('crisis', {})
        
        context['final_indicators'] = {
            'DRI': {'score': 100, 'level': 'critical', 'confidence': 0.95},
            'SDI': {'score': 50, 'level': 'unknown', 'confidence': 0.3},
            'CFL': {'score': 50, 'level': 'unknown', 'confidence': 0.3},
            'ES': {'score': 0, 'level': 'critical', 'confidence': 0.9},
            'OV': {'score': 10, 'level': 'critical', 'confidence': 0.9}
        }
        
        context['overall_assessment'] = {
            'status': 'emergency',
            'priority': 'immediate',
            'crisis_type': crisis.get('detected_patterns', []),
            'timestamp': datetime.now().isoformat()
        }
        
        context['recommendations'] = [{
            'type': 'emergency',
            'urgency': 'immediate',
            'action': '즉시 응급 개입 필요 - 의료진/보호자 연락',
            'reason': f"위기 상황 감지: {crisis.get('message', 'Unknown crisis')}"
        }]
        
        return context

    async def _generate_ai_narrative(self, indicators: Dict[str, Any], assessment: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        AI 기반 종합 해석 생성
        """
        if not self.openai_client:
            logger.warning("OpenAI client not available - using fallback narrative")
            return self._get_fallback_narrative(indicators, assessment)

        try:
            # 사용자 정보 추출
            user_info = context.get('user_info', {})
            age = user_info.get('age', '미상')
            gender = user_info.get('gender', '미상')

            # 분석 요약 정보 추출
            voice_summary = context.get('voice_summary', {})
            text_summary = context.get('text_summary', {})
            sincnet_summary = context.get('sincnet_summary', {})

            # AI 해석 프롬프트 구성
            narrative_prompt = f"""
당신은 노인 정신건강 전문가입니다. 다음 종합 분석 결과를 바탕으로 전문적이고 이해하기 쉬운 해석을 제공해주세요.

## 분석 대상자 정보
- 나이: {age}
- 성별: {gender}

## 5대 정신건강 지표 결과
- DRI (우울 위험도): {indicators.get('DRI', {}).get('score', 0):.1f}점 ({indicators.get('DRI', {}).get('level', '미상')})
- SDI (수면 장애 지수): {indicators.get('SDI', {}).get('score', 0):.1f}점 ({indicators.get('SDI', {}).get('level', '미상')})
- CFL (인지 기능 수준): {indicators.get('CFL', {}).get('score', 0):.1f}점 ({indicators.get('CFL', {}).get('level', '미상')})
- ES (정서 안정성): {indicators.get('ES', {}).get('score', 0):.1f}점 ({indicators.get('ES', {}).get('level', '미상')})
- OV (전반적 활력도): {indicators.get('OV', {}).get('score', 0):.1f}점 ({indicators.get('OV', {}).get('level', '미상')})

## 종합 평가
- 전반적 상태: {assessment.get('status', '미상')}
- 우선순위: {assessment.get('priority', '미상')}
- 고위험 지표: {', '.join(assessment.get('high_risk_indicators', [])) or '없음'}

## 분석 방법별 주요 소견
### 음성 분석 (30% 가중치)
- 말하기 속도: {voice_summary.get('speech_rate', '분석되지 않음')}
- 일시정지 비율: {voice_summary.get('pause_ratio', '분석되지 않음')}
- 에너지 수준: {voice_summary.get('energy_level', '분석되지 않음')}

### 텍스트 감정 분석 (40% 가중치)
- 감정 상태: {text_summary.get('sentiment', '분석되지 않음')}
- 주요 키워드: {', '.join(text_summary.get('keywords', [])) or '없음'}

### SincNet 딥러닝 분석 (30% 가중치)
- 우울 점수: {sincnet_summary.get('depression_score', '분석되지 않음')}
- 불안 점수: {sincnet_summary.get('anxiety_score', '분석되지 않음')}

다음 형식으로 전문적인 해석을 제공해주세요:

{{
    "comprehensive_interpretation": "전체 결과에 대한 종합적 해석 (3-4문장)",
    "key_findings": ["주요 발견사항 1", "주요 발견사항 2", "주요 발견사항 3"],
    "clinical_insights": "임상적 관점에서의 의견 (2-3문장)",
    "contextual_analysis": "연령과 성별을 고려한 맥락적 분석 (2-3문장)",
    "monitoring_recommendations": "향후 모니터링 권고사항 (2-3문장)"
}}
"""

            # GPT-4o 호출
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "당신은 노인 정신건강 전문가입니다. 분석 결과를 전문적이고 이해하기 쉽게 해석해주세요."},
                        {"role": "user", "content": narrative_prompt}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
            )

            # 응답 파싱
            narrative_result = json.loads(response.choices[0].message.content)

            return {
                'status': 'success',
                'narrative': narrative_result,
                'generated_at': datetime.now().isoformat(),
                'model': 'gpt-4o'
            }

        except Exception as e:
            logger.error(f"AI narrative generation failed: {e}")
            return self._get_fallback_narrative(indicators, assessment)

    def _get_fallback_narrative(self, indicators: Dict[str, Any], assessment: Dict[str, Any]) -> Dict[str, Any]:
        """AI 해석 실패 시 대체 해석"""

        # 기본 해석 생성
        overall_score = np.mean([ind.get('score', 50) for ind in indicators.values()])

        if overall_score >= 70:
            interpretation = "전반적으로 양호한 정신건강 상태를 유지하고 있습니다."
        elif overall_score >= 50:
            interpretation = "보통 수준의 정신건강 상태로, 일부 영역에서 주의가 필요합니다."
        else:
            interpretation = "정신건강 관리가 필요한 상태로, 전문가 상담을 권장합니다."

        # 고위험 지표 기반 소견
        key_findings = []
        high_risk = assessment.get('high_risk_indicators', [])

        if 'DRI' in high_risk:
            key_findings.append("우울 위험도가 높게 측정되었습니다")
        if 'SDI' in high_risk:
            key_findings.append("수면 장애 징후가 발견되었습니다")
        if 'CFL' in high_risk:
            key_findings.append("인지 기능 저하가 우려됩니다")
        if 'ES' in high_risk:
            key_findings.append("정서적 불안정성이 관찰되었습니다")
        if 'OV' in high_risk:
            key_findings.append("전반적 활력도가 낮은 상태입니다")

        if not key_findings:
            key_findings.append("특별한 위험 요인은 발견되지 않았습니다")

        return {
            'status': 'fallback',
            'narrative': {
                'comprehensive_interpretation': interpretation,
                'key_findings': key_findings[:3],  # 최대 3개
                'clinical_insights': "규칙 기반 분석을 통한 기본적인 평가 결과입니다.",
                'contextual_analysis': "추가적인 전문가 상담을 통해 더 정확한 평가가 가능합니다.",
                'monitoring_recommendations': "정기적인 모니터링을 통해 상태 변화를 추적하시기 바랍니다."
            },
            'generated_at': datetime.now().isoformat(),
            'model': 'rule_based_fallback'
        }

    def _get_default_indicators(self) -> Dict[str, Any]:
        """
        에러 시 기본 지표 반환
        """
        default = {
            'score': 50,
            'confidence': 0.0,
            'level': 'unknown',
            'description': 'Error in calculation'
        }
        
        return {
            'DRI': {**default, 'description': self.indicators_info['DRI']},
            'SDI': {**default, 'description': self.indicators_info['SDI']},
            'CFL': {**default, 'description': self.indicators_info['CFL']},
            'ES': {**default, 'description': self.indicators_info['ES']},
            'OV': {**default, 'description': self.indicators_info['OV']}
        }