"""
AI 종합해석 모듈
모든 분석 결과를 종합하여 최종 해석을 제공
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from openai import OpenAI  # OpenAI 1.51.0
import os
from ..utils.api_connectors import MultiLLMConnector
from ..utils.interface_validator import global_migrator

logger = logging.getLogger(__name__)

class ComprehensiveInterpreter:
    """AI 기반 종합 해석기"""
    
    def __init__(self, api_key: Optional[str] = None, gemini_api_key: Optional[str] = None):
        # 기존 OpenAI 전용 클라이언트 (호환성 유지)
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        # OpenAI 1.51.0 동기 클라이언트 사용
        self.client = OpenAI(
            api_key=self.api_key,
            timeout=30.0,  # 30초 타임아웃 추가
            max_retries=3  # 최대 3회 재시도
        ) if self.api_key else None
        self.model = "gpt-4o"

        # 새로운 MultiLLM 커넥터 (XAI 1순위, OpenAI 2순위, Gemini 3순위)
        try:
            self.multi_llm = MultiLLMConnector(
                xai_api_key=os.getenv('XAI_API_KEY'),  # XAI API 키 추가
                openai_api_key=self.api_key,
                gemini_api_key=gemini_api_key or os.getenv('GEMINI_API_KEY')
            )
            self.use_multi_llm = True
            logger.info("MultiLLM 커넥터 활성화 (XAI 1순위, OpenAI 2순위, Gemini 3순위)")
        except Exception as e:
            logger.warning(f"MultiLLM 커넥터 초기화 실패, OpenAI 전용 모드: {e}")
            self.multi_llm = None
            self.use_multi_llm = False
        
        # 종합 해석 프롬프트
        self.interpretation_prompt = """
        당신은 노인 정신건강 전문가입니다. 다음 분석 결과들을 종합하여 전문적인 해석을 제공해주세요.
        
        제공된 분석 데이터:
        1. 음성 분석 결과 (피치, 에너지, 말하기 속도 등)
        2. 텍스트 분석 결과 (감정, 키워드)
        3. 5대 정신건강 지표 (DRI, SDI, CFL, ES, OV)
        4. 임상 검증 결과 (위험 수준, 권장사항)
        5. 시계열 추세 분석 (제공된 경우)
        
        다음 형식으로 종합 해석을 제공하세요:
        
        {
            "overall_assessment": {
                "status": "정상|주의|위험|고위험",
                "confidence": 0.0-1.0,
                "summary": "전반적인 상태 요약 (2-3문장)"
            },
            "key_findings": [
                {
                    "category": "우울|불안|인지|수면|활력",
                    "finding": "주요 발견 사항",
                    "severity": "낮음|중간|높음",
                    "evidence": "근거가 되는 지표나 패턴"
                }
            ],
            "risk_factors": [
                {
                    "factor": "위험 요인",
                    "level": "낮음|중간|높음",
                    "description": "설명"
                }
            ],
            "strengths": [
                {
                    "area": "강점 영역",
                    "description": "설명"
                }
            ],
            "recommendations": {
                "immediate": ["즉시 필요한 조치"],
                "short_term": ["단기 권장사항 (1-2주)"],
                "long_term": ["장기 권장사항 (1개월 이상)"]
            },
            "follow_up": {
                "urgency": "즉시|1주일내|2주일내|1개월내",
                "focus_areas": ["추적 관찰이 필요한 영역"],
                "next_assessment": "다음 평가 권장 시기"
            },
            "clinical_notes": "전문가 참고사항 (선택적)"
        }
        """
    
    async def interpret(self, analysis_results: Dict[str, Any], force_openai: bool = False) -> Dict[str, Any]:
        """
        종합 해석 수행 (Gemini 우선, OpenAI fallback)
        
        Args:
            analysis_results: 모든 분석 결과를 포함한 딕셔너리
                - voice_analysis: 음성 분석 결과
                - text_analysis: 텍스트 분석 결과
                - indicators: 5대 지표
                - clinical_validation: 임상 검증
                - trend_analysis: 시계열 분석 (선택적)
            force_openai: OpenAI 강제 사용 여부
                
        Returns:
            종합 해석 결과
        """
        
        # MultiLLM 커넥터 사용 가능한 경우
        if self.use_multi_llm and self.multi_llm:
            try:
                logger.info("MultiLLM 커넥터로 종합 해석 시작")
                
                # 분석 결과를 텍스트로 변환
                prompt = self._build_prompt(analysis_results)
                
                # 파라미터 준비 (force_openai -> force_model 변환)
                # force_openai가 True면 'openai' 모델 강제, False면 자동 선택
                force_model = 'openai' if force_openai else None

                # MultiLLM으로 분석 (XAI 우선, OpenAI 2순위, Gemini 3순위)
                result = await self.multi_llm.analyze_text(
                    text=prompt,
                    context={'task': 'comprehensive_interpretation'},
                    force_model=force_model
                )
                
                # 분석 결과가 성공적인 경우
                if result.get('status') == 'success':
                    analysis = result.get('analysis', {})
                    
                    # 종합 해석 형식에 맞게 조정
                    if 'indicators' in analysis:
                        # 이미 적절한 형식이면 그대로 사용
                        interpretation = analysis
                    else:
                        # GPT 응답을 파싱
                        interpretation = self._parse_response(str(analysis))
                    
                    interpretation['timestamp'] = datetime.now().isoformat()
                    interpretation['method'] = 'multi_llm_interpretation'
                    
                    # provider 정보 추가
                    provider = result.get('provider', 'unknown')
                    fallback_used = result.get('fallback_used', False)
                    interpretation['provider'] = provider
                    interpretation['fallback_used'] = fallback_used
                    
                    logger.info(f"MultiLLM 종합 해석 완료 - Provider: {provider}, Fallback: {fallback_used}")
                    
                    return {
                        'status': 'success',
                        'analysis': interpretation,
                        'timestamp': datetime.now().isoformat(),
                        'provider': provider,
                        'fallback_used': fallback_used
                    }
                
            except Exception as e:
                logger.error(f"MultiLLM 종합 해석 실패, 기존 방식으로 fallback: {e}")
                # 기존 OpenAI 전용 로직으로 fallback
        
        # 기존 OpenAI 전용 로직 (호환성 유지)
        try:
            # API 키가 없으면 규칙 기반 해석
            if not self.client:
                logger.info("API 키 없음, 규칙 기반 해석 사용")
                return self._rule_based_interpretation(analysis_results)
            
            logger.info("기존 OpenAI 전용 모드로 종합 해석")
            
            # GPT-4o를 사용한 종합 해석
            prompt = self._build_prompt(analysis_results)
            
            # 동기 클라이언트를 비동기로 실행
            import asyncio
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": self.interpretation_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.3,
                    max_tokens=2000
                )
            )
            
            # 응답 파싱
            result = self._parse_response(response.choices[0].message.content)
            result['timestamp'] = datetime.now().isoformat()
            result['method'] = 'openai_interpretation'
            result['provider'] = 'openai'
            result['fallback_used'] = False
            
            return {
                'status': 'success',
                'analysis': result,
                'timestamp': datetime.now().isoformat(),
                'provider': 'openai',
                'fallback_used': False
            }
            
        except Exception as e:
            logger.error(f"OpenAI 종합 해석 실패: {e}")
            # 최종 폴백: 규칙 기반 해석
            interpretation = self._rule_based_interpretation(analysis_results)
            return {
                'status': 'fallback',
                'analysis': interpretation,
                'error': str(e),
                'timestamp': datetime.now().isoformat(),
                'provider': 'rule_based',
                'fallback_used': True
            }
    
    def _build_prompt(self, analysis_results: Dict[str, Any]) -> str:
        """분석 결과를 프롬프트로 변환"""
        prompt_parts = []
        
        # 음성 분석 결과
        if 'voice_analysis' in analysis_results:
            voice = analysis_results['voice_analysis']
            prompt_parts.append(f"""
            음성 분석:
            - 피치 평균: {voice.get('pitch_mean', 'N/A')} Hz
            - 에너지: {voice.get('energy_mean', 'N/A')}
            - 말하기 속도: {voice.get('speaking_rate', 'N/A')}
            """)
        
        # 5대 지표
        if 'indicators' in analysis_results:
            ind = analysis_results['indicators']
            prompt_parts.append(f"""
            5대 정신건강 지표:
            - DRI (우울): {ind.get('DRI', 'N/A')}
            - SDI (수면): {ind.get('SDI', 'N/A')}
            - CFL (인지): {ind.get('CFL', 'N/A')}
            - ES (정서): {ind.get('ES', 'N/A')}
            - OV (활력): {ind.get('OV', 'N/A')}
            """)
        
        # 임상 검증
        if 'clinical_validation' in analysis_results:
            clinical = analysis_results['clinical_validation']
            prompt_parts.append(f"""
            임상 검증:
            - 위험 수준: {clinical.get('risk_level', 'N/A')}
            - 유효성: {clinical.get('is_valid', 'N/A')}
            """)
        
        # 시계열 추세 (있는 경우)
        if 'trend_analysis' in analysis_results and analysis_results['trend_analysis']:
            trend = analysis_results['trend_analysis']
            prompt_parts.append(f"""
            시계열 추세:
            - 전반적 추세: {trend.get('summary', {}).get('overall_trend', 'N/A')}
            - 변화율: {trend.get('summary', {}).get('change_rate', 'N/A')}
            """)
        
        return "\n".join(prompt_parts)
    
    def _parse_response(self, response_text: str) -> Dict[str, Any]:
        """GPT 응답을 파싱"""
        try:
            # JSON 형식으로 응답받기를 기대
            result = json.loads(response_text)
            return result
        except:
            # JSON 파싱 실패시 텍스트 그대로 반환
            return {
                'overall_assessment': {
                    'summary': response_text
                },
                'parse_error': True
            }
    
    def _rule_based_interpretation(self, analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """규칙 기반 종합 해석 (폴백)"""
        
        interpretation = {
            'overall_assessment': {},
            'key_findings': [],
            'risk_factors': [],
            'strengths': [],
            'recommendations': {
                'immediate': [],
                'short_term': [],
                'long_term': []
            },
            'follow_up': {},
            'timestamp': datetime.now().isoformat(),
            'method': 'rule_based'
        }
        
        # 5대 지표 기반 평가
        if 'indicators' in analysis_results:
            indicators = analysis_results['indicators']
            
            # 전반적 위험도 계산
            avg_score = sum([
                indicators.get('DRI', 0.5),
                indicators.get('SDI', 0.5),
                indicators.get('CFL', 0.5),
                indicators.get('ES', 0.5),
                indicators.get('OV', 0.5)
            ]) / 5
            
            # 상태 판정
            if avg_score >= 0.7:
                status = "정상"
                urgency = "1개월내"
            elif avg_score >= 0.5:
                status = "주의"
                urgency = "2주일내"
            elif avg_score >= 0.3:
                status = "위험"
                urgency = "1주일내"
            else:
                status = "고위험"
                urgency = "즉시"
            
            interpretation['overall_assessment'] = {
                'status': status,
                'confidence': 0.4,  # 규칙 기반이므로 신뢰도 낮음 (0.3-0.5 범위)
                'summary': f"5대 지표 평균 {avg_score:.2f}로 {status} 수준입니다."
            }
            
            # 주요 발견사항
            if indicators.get('DRI', 0) < 0.4:
                interpretation['key_findings'].append({
                    'category': '우울',
                    'finding': '우울 위험도가 높습니다',
                    'severity': '높음',
                    'evidence': f"DRI 지표: {indicators.get('DRI', 0):.2f}"
                })
                interpretation['risk_factors'].append({
                    'factor': '우울증 위험',
                    'level': '높음',
                    'description': '전문가 상담이 필요할 수 있습니다'
                })
            
            if indicators.get('CFL', 0) < 0.4:
                interpretation['key_findings'].append({
                    'category': '인지',
                    'finding': '인지 기능 저하가 관찰됩니다',
                    'severity': '중간',
                    'evidence': f"CFL 지표: {indicators.get('CFL', 0):.2f}"
                })
            
            # 강점 찾기
            if indicators.get('ES', 0) >= 0.7:
                interpretation['strengths'].append({
                    'area': '정서적 안정성',
                    'description': '정서적으로 안정적인 상태를 유지하고 있습니다'
                })
            
            # 권장사항
            if status in ["위험", "고위험"]:
                interpretation['recommendations']['immediate'].append(
                    "전문가 상담을 받으시기를 권장합니다"
                )
            
            interpretation['recommendations']['short_term'].append(
                "규칙적인 생활 패턴을 유지하세요"
            )
            interpretation['recommendations']['long_term'].append(
                "정기적인 정신건강 모니터링을 받으세요"
            )
            
            # 추적 관찰
            interpretation['follow_up'] = {
                'urgency': urgency,
                'focus_areas': ['우울', '인지'] if status != "정상" else ['전반적 모니터링'],
                'next_assessment': f"{urgency} 내 재평가 권장"
            }
        
        return interpretation