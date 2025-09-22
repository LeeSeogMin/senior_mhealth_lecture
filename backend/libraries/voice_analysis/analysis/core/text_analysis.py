"""
텍스트 분석 핵심 모듈
OpenAI GPT-4o를 활용한 시니어 음성 텍스트 분석
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
from openai import OpenAI  # OpenAI 1.35.0
import os
import numpy as np

logger = logging.getLogger(__name__)

class TextAnalyzer:
    """GPT-4o 기반 텍스트 분석기 (OpenAI 전용)"""

    def __init__(self, api_key: Optional[str] = None):
        # OpenAI 클라이언트 초기화
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        self.client = OpenAI(api_key=self.api_key) if self.api_key else None
        self.model = "gpt-4o"

        # 시니어 정신건강 분석 프롬프트
        self.analysis_prompt = """
        당신은 노인 정신건강 전문가입니다. 주어진 대화 내용을 분석하여 다음 5가지 정신건강 지표를 평가해주세요.
        각 지표는 0-1 사이의 값으로, 높을수록 긍정적입니다.

        평가 지표:
        1. DRI (Depression Risk Indicator): 우울 위험도 (0=매우 우울, 1=전혀 우울하지 않음)
        2. SDI (Sleep Disorder Indicator): 수면 장애 지표 (0=심각한 수면장애, 1=양호한 수면)
        3. CFL (Cognitive Function Level): 인지 기능 수준 (0=심각한 저하, 1=정상)
        4. ES (Emotional Stability): 정서적 안정성 (0=매우 불안정, 1=매우 안정)
        5. OV (Overall Vitality): 전반적 활력도 (0=매우 낮음, 1=매우 높음)

        분석 시 고려사항:
        - 언어 패턴, 감정 표현, 논리적 일관성
        - 반복적 표현, 부정적 단어 사용 빈도
        - 대화 참여도 및 반응 속도
        - 기억력 및 집중력 관련 표현
        - 신체 증상 호소 여부

        JSON 형식으로 응답하세요:
        {
            "indicators": {
                "DRI": 0.0-1.0,
                "SDI": 0.0-1.0,
                "CFL": 0.0-1.0,
                "ES": 0.0-1.0,
                "OV": 0.0-1.0
            },
            "key_findings": ["주요 발견 1", "주요 발견 2", ...],
            "risk_factors": ["위험 요인 1", "위험 요인 2", ...],
            "recommendations": ["권고사항 1", "권고사항 2", ...]
        }
        """

    async def analyze(self, text: str, context: Optional[Dict] = None) -> Dict[str, Any]:
        """
        텍스트 분석 실행 (OpenAI GPT-4o 전용)

        Args:
            text: 분석할 텍스트
            context: 추가 컨텍스트 정보

        Returns:
            분석 결과 딕셔너리
        """

        if not self.client:
            logger.error("OpenAI API 키가 설정되지 않음")
            return self._get_default_response()

        try:
            logger.info("OpenAI GPT-4o로 텍스트 분석 시작")

            # 컨텍스트 정보 추가
            full_prompt = self.analysis_prompt
            if context:
                context_str = f"\n추가 정보:\n"
                context_str += f"- 나이: {context.get('age', '미상')}\n"
                context_str += f"- 성별: {context.get('gender', '미상')}\n"
                context_str += f"- 분석 시간: {context.get('timestamp', datetime.now().isoformat())}\n"
                full_prompt = context_str + "\n" + full_prompt

            # GPT-4o 분석 요청 (동기 클라이언트를 비동기로 실행)
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": full_prompt},
                        {"role": "user", "content": f"다음 대화 내용을 분석해주세요:\n\n{text}"}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
            )

            # 응답 파싱
            result = json.loads(response.choices[0].message.content)

            # 추가 분석
            result['linguistic_features'] = self._analyze_linguistic_features(text)
            result['emotion_analysis'] = await self._analyze_emotions(text)

            return {
                'status': 'success',
                'analysis': result,
                'timestamp': datetime.now().isoformat(),
                'model': self.model
            }

        except Exception as e:
            logger.error(f"텍스트 분석 실패: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'analysis': self._get_default_response()
            }

    def _analyze_linguistic_features(self, text: str) -> Dict[str, Any]:
        """언어적 특징 분석"""

        words = text.split()
        sentences = text.split('.')

        # 부정적 단어 목록 (한국어)
        negative_words = [
            '우울', '슬픔', '외로움', '힘들다', '아프다', '고통', '불안',
            '걱정', '무기력', '피곤', '지친다', '싫다', '못', '안'
        ]

        # 긍정적 단어 목록
        positive_words = [
            '행복', '기쁨', '좋다', '편안', '감사', '희망', '사랑',
            '건강', '활력', '즐겁다', '웃음', '만족'
        ]

        negative_count = sum(1 for word in words if any(neg in word for neg in negative_words))
        positive_count = sum(1 for word in words if any(pos in word for pos in positive_words))

        return {
            'word_count': len(words),
            'sentence_count': len(sentences),
            'avg_sentence_length': len(words) / max(len(sentences), 1),
            'negative_word_ratio': negative_count / max(len(words), 1),
            'positive_word_ratio': positive_count / max(len(words), 1),
            'sentiment_balance': (positive_count - negative_count) / max(len(words), 1)
        }

    async def _analyze_emotions(self, text: str) -> Dict[str, float]:
        """감정 분석"""

        if not self.client:
            return self._get_default_emotions()

        try:
            emotion_prompt = """
            다음 텍스트의 감정을 분석하여 각 감정의 강도를 0-1 사이 값으로 평가하세요:
            - happiness (행복)
            - sadness (슬픔)
            - anger (분노)
            - fear (두려움)
            - surprise (놀람)
            - disgust (혐오)

            JSON 형식으로 응답하세요.
            """

            # 동기 클라이언트를 비동기로 실행
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: self.client.chat.completions.create(
                    model="gpt-4o-mini",  # 빠른 응답을 위해 mini 모델 사용
                    messages=[
                        {"role": "system", "content": emotion_prompt},
                        {"role": "user", "content": text}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
            )

            emotions = json.loads(response.choices[0].message.content)
            return emotions

        except Exception as e:
            logger.warning(f"감정 분석 실패: {e}")
            return self._get_default_emotions()

    def _get_default_response(self) -> Dict[str, Any]:
        """분석 실패 시 기본 응답 반환"""
        return {
            'status': 'failed',
            'indicators': {
                'DRI': None,
                'SDI': None,
                'CFL': None,
                'ES': None,
                'OV': None
            },
            'key_findings': ['분석 실패로 인한 데이터 부족'],
            'risk_factors': ['분석 실패'],
            'recommendations': ['재분석 시도 또는 전문가 상담 권장'],
            'error': 'GPT-4o 분석 실패'
        }

    def _get_default_emotions(self) -> Dict[str, float]:
        """감정 분석 실패 시 기본값 반환"""
        return {
            'happiness': None,
            'sadness': None,
            'anger': None,
            'fear': None,
            'surprise': None,
            'disgust': None
        }

    async def analyze_conversation_history(self, conversations: List[Dict]) -> Dict[str, Any]:
        """
        대화 기록 분석

        Args:
            conversations: 대화 기록 리스트

        Returns:
            시계열 분석 결과
        """

        results = []
        for conv in conversations:
            result = await self.analyze(
                conv.get('text', ''),
                context=conv.get('context', {})
            )
            results.append({
                'timestamp': conv.get('timestamp'),
                'analysis': result
            })

        # 추세 분석
        trends = self._analyze_trends(results)

        return {
            'individual_results': results,
            'trends': trends,
            'summary': self._generate_summary(results, trends)
        }

    def _analyze_trends(self, results: List[Dict]) -> Dict[str, Any]:
        """지표 추세 분석"""

        if not results:
            return {}

        indicators_over_time = {
            'DRI': [],
            'SDI': [],
            'CFL': [],
            'ES': [],
            'OV': []
        }

        for result in results:
            if result['analysis']['status'] == 'success':
                indicators = result['analysis']['analysis']['indicators']
                for key in indicators_over_time:
                    indicators_over_time[key].append(indicators.get(key, 0.5))

        trends = {}
        for key, values in indicators_over_time.items():
            if len(values) > 1:
                # 선형 회귀를 통한 추세 계산
                x = list(range(len(values)))
                slope = np.polyfit(x, values, 1)[0] if len(values) > 1 else 0

                trends[key] = {
                    'current': values[-1] if values else 0.5,
                    'average': np.mean(values) if values else 0.5,
                    'trend': 'improving' if slope > 0.01 else 'declining' if slope < -0.01 else 'stable',
                    'slope': float(slope)
                }

        return trends

    def _generate_summary(self, results: List[Dict], trends: Dict) -> str:
        """분석 요약 생성"""

        summary_parts = []

        # 전반적 상태
        if trends:
            avg_current = np.mean([t['current'] for t in trends.values()])
            if avg_current > 0.7:
                summary_parts.append("전반적으로 양호한 정신건강 상태를 보이고 있습니다.")
            elif avg_current > 0.4:
                summary_parts.append("보통 수준의 정신건강 상태를 유지하고 있습니다.")
            else:
                summary_parts.append("정신건강 상태에 주의가 필요합니다.")

        # 주요 우려 지표
        for key, trend in trends.items():
            if trend['current'] < 0.4:
                indicator_names = {
                    'DRI': '우울 위험도',
                    'SDI': '수면 장애',
                    'CFL': '인지 기능',
                    'ES': '정서적 안정성',
                    'OV': '전반적 활력도'
                }
                summary_parts.append(f"{indicator_names.get(key, key)}에서 낮은 점수를 보이고 있습니다.")

        # 추세 정보
        improving = [k for k, v in trends.items() if v['trend'] == 'improving']
        declining = [k for k, v in trends.items() if v['trend'] == 'declining']

        if improving:
            summary_parts.append(f"개선되고 있는 지표: {', '.join(improving)}")
        if declining:
            summary_parts.append(f"악화되고 있는 지표: {', '.join(declining)}")

        return ' '.join(summary_parts) if summary_parts else "분석 데이터가 충분하지 않습니다."