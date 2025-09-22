"""
RAG 강화 텍스트 분석 모듈
기존 TextAnalyzer와 RAG 벡터스토어를 통합하여 향상된 분석 제공
"""

import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import asyncio
import os
import sys

# 기존 텍스트 분석기 import
sys.path.append(os.path.join(os.path.dirname(__file__), '../..'))
from analysis.core.text_analysis import TextAnalyzer
from .vector_store_manager import FirebaseStorageVectorStore
from .rag_monitor import RAGPerformanceMonitor

logger = logging.getLogger(__name__)

class RAGEnhancedTextAnalyzer(TextAnalyzer):
    """RAG 강화 텍스트 분석기"""
    
    def __init__(self, 
                 api_key: Optional[str] = None, 
                 gemini_api_key: Optional[str] = None,
                 use_rag: bool = True,
                 vector_store_config: Optional[Dict] = None):
        """
        RAG 강화 텍스트 분석기 초기화
        
        Args:
            api_key: OpenAI API 키
            gemini_api_key: Gemini API 키
            use_rag: RAG 기능 사용 여부
            vector_store_config: 벡터스토어 설정
        """
        # 부모 클래스 초기화 (기본 텍스트 분석 기능)
        super().__init__(api_key, gemini_api_key)
        
        self.use_rag = use_rag
        self.vector_store = None
        self.rag_monitor = None
        
        if self.use_rag:
            try:
                # RAG 벡터스토어 초기화
                config = vector_store_config or {}
                self.vector_store = FirebaseStorageVectorStore(
                    bucket_name=config.get('bucket_name'),
                    project_id=config.get('project_id')
                )
                
                # RAG 성능 모니터링
                self.rag_monitor = RAGPerformanceMonitor()
                
                logger.info("RAG 벡터스토어 초기화 성공")
                
            except Exception as e:
                logger.error(f"RAG 벡터스토어 초기화 실패: {e}")
                self.use_rag = False
                logger.warning("RAG 기능 비활성화, 기본 텍스트 분석만 사용")
    
    async def analyze_with_rag(self, text: str, context: Optional[Dict] = None, force_openai: bool = False) -> Dict[str, Any]:
        """
        RAG 강화 텍스트 분석
        
        Args:
            text: 분석할 텍스트
            context: 추가 컨텍스트 정보
            force_openai: OpenAI 강제 사용 여부
            
        Returns:
            RAG 강화 분석 결과
        """
        analysis_start = datetime.now()
        
        try:
            # 1. 기본 텍스트 분석 수행
            base_analysis = await self.analyze(text, context, force_openai)
            
            # RAG 기능이 비활성화된 경우 기본 분석만 반환
            if not self.use_rag or not self.vector_store:
                return base_analysis
            
            # 2. RAG 컨텍스트 검색
            rag_context = await self._retrieve_relevant_context(text, context)
            
            if not rag_context:
                logger.info("RAG 컨텍스트를 찾지 못함, 기본 분석 결과 반환")
                return base_analysis
            
            # 3. RAG 강화 분석 수행
            enhanced_analysis = await self._analyze_with_context(text, context, rag_context, force_openai)
            
            # 4. 결과 통합
            integrated_result = self._integrate_analysis_results(base_analysis, enhanced_analysis, rag_context)
            
            # 5. RAG 성능 모니터링
            if self.rag_monitor:
                analysis_time = (datetime.now() - analysis_start).total_seconds()
                await self.rag_monitor.log_analysis_performance({
                    'analysis_time': analysis_time,
                    'rag_used': True,
                    'context_found': len(rag_context) > 0,
                    'text_length': len(text)
                })
            
            return integrated_result
            
        except Exception as e:
            logger.error(f"RAG 강화 분석 실패: {e}")
            # 오류 발생 시 기본 분석 결과 반환
            return base_analysis
    
    async def _retrieve_relevant_context(self, text: str, context: Optional[Dict] = None) -> List[Dict]:
        """관련 컨텍스트 검색"""
        try:
            # 텍스트에서 키워드 추출
            keywords = await self._extract_keywords(text)
            
            # 벡터스토어에서 관련 문서 검색
            relevant_docs = await self.vector_store.search_similar_documents(
                query_text=text,
                keywords=keywords,
                max_results=5,
                similarity_threshold=0.7
            )
            
            return relevant_docs
            
        except Exception as e:
            logger.error(f"관련 컨텍스트 검색 실패: {e}")
            return []
    
    async def _extract_keywords(self, text: str) -> List[str]:
        """텍스트에서 키워드 추출"""
        # 간단한 키워드 추출 로직 (실제로는 더 정교한 방법 사용)
        import re
        
        # 정신건강 관련 주요 키워드
        mental_health_keywords = [
            '우울', '불안', '스트레스', '수면', '인지', '기억', '집중',
            '감정', '기분', '활력', '피로', '외로움', '사회적', '관계'
        ]
        
        found_keywords = []
        for keyword in mental_health_keywords:
            if keyword in text:
                found_keywords.append(keyword)
        
        # 추가적인 키워드 추출 (명사, 형용사 등)
        words = re.findall(r'\b\w+\b', text)
        important_words = [word for word in words if len(word) > 2]
        
        return found_keywords + important_words[:10]  # 상위 10개 추가
    
    async def _analyze_with_context(self, text: str, context: Optional[Dict], rag_context: List[Dict], force_openai: bool) -> Dict[str, Any]:
        """RAG 컨텍스트를 활용한 강화 분석"""
        
        # RAG 컨텍스트를 프롬프트에 포함
        context_text = self._format_rag_context(rag_context)
        
        enhanced_prompt = f"""
        당신은 노인 정신건강 전문가입니다. 주어진 대화 내용과 관련 전문 지식을 바탕으로 다음 5가지 정신건강 지표를 평가해주세요.
        
        관련 전문 지식:
        {context_text}
        
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
        - 제공된 전문 지식과의 연관성
        
        JSON 형식으로 응답하세요:
        {{
            "indicators": {{
                "DRI": 0.0-1.0,
                "SDI": 0.0-1.0,
                "CFL": 0.0-1.0,
                "ES": 0.0-1.0,
                "OV": 0.0-1.0
            }},
            "key_findings": ["주요 발견 1", "주요 발견 2", ...],
            "risk_factors": ["위험 요인 1", "위험 요인 2", ...],
            "recommendations": ["권고사항 1", "권고사항 2", ...],
            "rag_insights": ["RAG 기반 통찰 1", "RAG 기반 통찰 2", ...]
        }}
        """
        
        # MultiLLM 또는 OpenAI를 통한 분석
        if self.use_multi_llm and self.multi_llm:
            try:
                # MultiLLM의 analyze_text 메서드 사용 (enhanced_prompt를 context로 전달)
                result = await self.multi_llm.analyze_text(text, {'enhanced_prompt': enhanced_prompt}, force_openai)
                if result.get('status') == 'success':
                    return result
            except Exception as e:
                logger.error(f"MultiLLM RAG 분석 실패: {e}")
        
        # OpenAI 직접 사용
        if self.client:
            try:
                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": enhanced_prompt},
                        {"role": "user", "content": f"다음 대화 내용을 분석해주세요:\\n\\n{text}"}
                    ],
                    temperature=0.3,
                    response_format={"type": "json_object"}
                )
                
                analysis_result = json.loads(response.choices[0].message.content)
                
                return {
                    'status': 'success',
                    'analysis': analysis_result,
                    'timestamp': datetime.now().isoformat(),
                    'model': self.model,
                    'rag_enhanced': True
                }
                
            except Exception as e:
                logger.error(f"OpenAI RAG 분석 실패: {e}")
        
        # 모든 방법이 실패한 경우 기본 응답
        return self._get_default_response()
    
    def _format_rag_context(self, rag_context: List[Dict]) -> str:
        """RAG 컨텍스트를 프롬프트에 포함할 수 있도록 포맷"""
        if not rag_context:
            return "관련 전문 지식이 없습니다."
        
        formatted_context = []
        for i, doc in enumerate(rag_context, 1):
            content = doc.get('content', doc.get('text', ''))
            metadata = doc.get('metadata', {})
            
            context_item = f"{i}. {content}"
            if metadata.get('source'):
                context_item += f" (출처: {metadata['source']})"
            
            formatted_context.append(context_item)
        
        return "\n".join(formatted_context)
    
    def _integrate_analysis_results(self, base_analysis: Dict, enhanced_analysis: Dict, rag_context: List[Dict]) -> Dict[str, Any]:
        """기본 분석과 RAG 강화 분석 결과를 통합"""
        
        # 기본 분석 결과를 베이스로 사용
        integrated = base_analysis.copy()
        
        # RAG 강화 분석이 성공한 경우
        if enhanced_analysis.get('status') == 'success':
            enhanced_data = enhanced_analysis.get('analysis', {})
            
            # 지표값은 RAG 강화 분석 우선 사용
            if 'indicators' in enhanced_data:
                integrated['analysis']['indicators'] = enhanced_data['indicators']
            
            # RAG 특화 인사이트 추가
            if 'rag_insights' in enhanced_data:
                integrated['analysis']['rag_insights'] = enhanced_data['rag_insights']
            
            # 추천사항 통합
            if 'recommendations' in enhanced_data:
                base_recommendations = integrated['analysis'].get('recommendations', [])
                enhanced_recommendations = enhanced_data['recommendations']
                integrated['analysis']['recommendations'] = list(set(base_recommendations + enhanced_recommendations))
        
        # RAG 메타데이터 추가
        integrated['rag_metadata'] = {
            'rag_used': True,
            'context_count': len(rag_context),
            'sources': [doc.get('metadata', {}).get('source', 'unknown') for doc in rag_context],
            'enhancement_timestamp': datetime.now().isoformat()
        }
        
        return integrated
    
    # 기본 analyze 메서드를 오버라이드하여 RAG 기능 통합
    async def analyze(self, text: str, context: Optional[Dict] = None, force_openai: bool = False) -> Dict[str, Any]:
        """
        텍스트 분석 (RAG 기능이 활성화된 경우 자동으로 RAG 강화 분석 사용)
        """
        if self.use_rag:
            return await self.analyze_with_rag(text, context, force_openai)
        else:
            return await super().analyze(text, context, force_openai)