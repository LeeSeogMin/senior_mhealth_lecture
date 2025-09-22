"""
LLM 합의 기반 레이블링 시스템
여러 LLM의 합의를 통한 준전문가(Semi-Expert) 레이블 생성
"""

from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import logging
import json
import hashlib
from datetime import datetime

logger = logging.getLogger(__name__)


class LLMProvider(Enum):
    """LLM 제공자"""
    OPENAI_GPT4 = "openai_gpt4"
    ANTHROPIC_CLAUDE = "anthropic_claude"
    GOOGLE_GEMINI = "google_gemini"
    XAI_GROK = "xai_grok"


@dataclass
class LLMJudgment:
    """개별 LLM 판단 결과"""
    provider: LLMProvider
    diagnosis: str
    severity: str
    confidence: float
    reasoning: str
    evidence: List[str]
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ConsensusLabel:
    """LLM 합의 레이블"""
    final_diagnosis: str
    final_severity: str
    consensus_level: float  # 합의 수준 (0-1)
    individual_judgments: List[LLMJudgment]
    agreement_matrix: Dict[str, float]
    is_unanimous: bool
    requires_expert_review: bool
    metadata: Dict = field(default_factory=dict)


class LLMConsensusLabeling:
    """LLM 합의 기반 레이블링 시스템"""
    
    def __init__(self, rag_knowledge_base: Optional[str] = None):
        """
        Args:
            rag_knowledge_base: RAG 지식 베이스 경로
        """
        self.providers = list(LLMProvider)
        self.rag_kb = rag_knowledge_base
        self.min_consensus_threshold = 0.75  # 75% 이상 동의 필요
        self.unanimous_bonus = 0.1  # 만장일치시 신뢰도 보너스
        
        # DSM-5 기반 프롬프트 템플릿
        self.assessment_prompt = self._load_assessment_prompt()
        
        logger.info(f"LLM Consensus Labeling initialized with {len(self.providers)} providers")
    
    def _load_assessment_prompt(self) -> str:
        """평가 프롬프트 템플릿 로드"""
        return """
        You are a mental health assessment specialist. Based on the following data, 
        provide a diagnostic assessment using DSM-5 criteria.
        
        **Patient Data:**
        - Transcription: {transcription}
        - PHQ-9 Score: {phq9_score}
        - GAD-7 Score: {gad7_score}
        - Voice Features: {voice_features}
        - Behavioral Patterns: {patterns}
        
        **Assessment Guidelines:**
        1. Use DSM-5 diagnostic criteria
        2. Consider cultural factors
        3. Evaluate severity levels
        4. Identify key symptoms
        
        **Required Output (JSON):**
        {{
            "primary_diagnosis": "specific DSM-5 diagnosis",
            "severity": "mild|moderate|severe",
            "confidence": 0.0-1.0,
            "evidence": ["symptom1", "symptom2"],
            "reasoning": "diagnostic reasoning",
            "differential_diagnosis": ["alternative1", "alternative2"],
            "recommendations": ["recommendation1", "recommendation2"]
        }}
        
        **Important:** This is for research purposes only, not clinical diagnosis.
        """
    
    async def get_consensus_label(self, data: Dict[str, Any]) -> Optional[ConsensusLabel]:
        """
        여러 LLM의 합의를 통한 레이블 생성
        
        Args:
            data: 평가할 데이터
            
        Returns:
            합의 레이블 또는 None
        """
        # 1. 각 LLM에게 평가 요청 (병렬 처리)
        judgments = await self._get_llm_judgments(data)
        
        if len(judgments) < 3:
            logger.warning("Insufficient LLM responses for consensus")
            return None
        
        # 2. 합의 수준 계산
        consensus_level, agreement_matrix = self._calculate_consensus(judgments)
        
        # 3. 최종 레이블 결정
        final_diagnosis, final_severity = self._determine_final_label(judgments)
        
        # 4. 전문가 검토 필요 여부 판단
        requires_expert = self._requires_expert_review(
            consensus_level, 
            judgments,
            data
        )
        
        # 5. 합의 레이블 생성
        consensus_label = ConsensusLabel(
            final_diagnosis=final_diagnosis,
            final_severity=final_severity,
            consensus_level=consensus_level,
            individual_judgments=judgments,
            agreement_matrix=agreement_matrix,
            is_unanimous=(consensus_level == 1.0),
            requires_expert_review=requires_expert,
            metadata={
                'num_llms': len(judgments),
                'timestamp': datetime.now().isoformat(),
                'data_hash': self._hash_data(data)
            }
        )
        
        logger.info(f"Consensus reached: {final_diagnosis} (level: {consensus_level:.2f})")
        
        return consensus_label
    
    async def _get_llm_judgments(self, data: Dict[str, Any]) -> List[LLMJudgment]:
        """
        각 LLM으로부터 판단 수집
        
        Args:
            data: 평가 데이터
            
        Returns:
            LLM 판단 리스트
        """
        tasks = []
        
        for provider in self.providers:
            task = self._get_single_llm_judgment(provider, data)
            tasks.append(task)
        
        # 병렬 실행
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 성공한 결과만 수집
        judgments = []
        for result in results:
            if isinstance(result, LLMJudgment):
                judgments.append(result)
            else:
                logger.error(f"LLM judgment failed: {result}")
        
        return judgments
    
    async def _get_single_llm_judgment(self, provider: LLMProvider, 
                                      data: Dict[str, Any]) -> LLMJudgment:
        """
        단일 LLM 판단 획득
        
        Args:
            provider: LLM 제공자
            data: 평가 데이터
            
        Returns:
            LLM 판단
        """
        # 프롬프트 생성
        prompt = self.assessment_prompt.format(
            transcription=data.get('transcription', ''),
            phq9_score=data.get('phq9_score', 'N/A'),
            gad7_score=data.get('gad7_score', 'N/A'),
            voice_features=json.dumps(data.get('voice_features', {})),
            patterns=json.dumps(data.get('patterns', {}))
        )
        
        # RAG 컨텍스트 추가
        if self.rag_kb:
            context = await self._get_rag_context(data)
            prompt = f"{context}\n\n{prompt}"
        
        # LLM 호출 (실제 구현 필요)
        response = await self._call_llm_api(provider, prompt)
        
        # 응답 파싱
        try:
            result = json.loads(response)
            
            return LLMJudgment(
                provider=provider,
                diagnosis=result['primary_diagnosis'],
                severity=result['severity'],
                confidence=result['confidence'],
                reasoning=result['reasoning'],
                evidence=result['evidence']
            )
        except Exception as e:
            logger.error(f"Failed to parse LLM response from {provider.value}: {e}")
            raise
    
    def _calculate_consensus(self, judgments: List[LLMJudgment]) -> Tuple[float, Dict]:
        """
        합의 수준 계산
        
        Args:
            judgments: LLM 판단들
            
        Returns:
            (합의 수준, 동의 매트릭스)
        """
        n = len(judgments)
        if n == 0:
            return 0.0, {}
        
        # 진단 일치도
        diagnoses = [j.diagnosis for j in judgments]
        diagnosis_consensus = self._calculate_agreement(diagnoses)
        
        # 심각도 일치도
        severities = [j.severity for j in judgments]
        severity_consensus = self._calculate_agreement(severities)
        
        # 가중 평균 (진단이 더 중요)
        consensus_level = 0.7 * diagnosis_consensus + 0.3 * severity_consensus
        
        # 동의 매트릭스
        agreement_matrix = {
            'diagnosis_agreement': diagnosis_consensus,
            'severity_agreement': severity_consensus,
            'pairwise_agreements': self._calculate_pairwise_agreement(judgments)
        }
        
        return consensus_level, agreement_matrix
    
    def _calculate_agreement(self, values: List[str]) -> float:
        """리스트 내 동의 수준 계산"""
        if not values:
            return 0.0
        
        from collections import Counter
        counter = Counter(values)
        most_common_count = counter.most_common(1)[0][1]
        
        return most_common_count / len(values)
    
    def _calculate_pairwise_agreement(self, judgments: List[LLMJudgment]) -> Dict:
        """LLM 쌍별 동의도 계산"""
        agreements = {}
        
        for i, j1 in enumerate(judgments):
            for j, j2 in enumerate(judgments[i+1:], i+1):
                pair_key = f"{j1.provider.value}-{j2.provider.value}"
                
                # 진단 일치
                diag_match = 1.0 if j1.diagnosis == j2.diagnosis else 0.0
                
                # 심각도 일치
                sev_match = 1.0 if j1.severity == j2.severity else 0.0
                
                agreements[pair_key] = (diag_match + sev_match) / 2
        
        return agreements
    
    def _determine_final_label(self, judgments: List[LLMJudgment]) -> Tuple[str, str]:
        """
        최종 레이블 결정 (가중 투표)
        
        Args:
            judgments: LLM 판단들
            
        Returns:
            (최종 진단, 최종 심각도)
        """
        # 신뢰도 가중 투표
        diagnosis_votes = {}
        severity_votes = {}
        
        for judgment in judgments:
            weight = judgment.confidence
            
            # 진단 투표
            if judgment.diagnosis not in diagnosis_votes:
                diagnosis_votes[judgment.diagnosis] = 0
            diagnosis_votes[judgment.diagnosis] += weight
            
            # 심각도 투표
            if judgment.severity not in severity_votes:
                severity_votes[judgment.severity] = 0
            severity_votes[judgment.severity] += weight
        
        # 최다 득표
        final_diagnosis = max(diagnosis_votes, key=diagnosis_votes.get)
        final_severity = max(severity_votes, key=severity_votes.get)
        
        return final_diagnosis, final_severity
    
    def _requires_expert_review(self, consensus_level: float, 
                               judgments: List[LLMJudgment],
                               data: Dict) -> bool:
        """
        전문가 검토 필요 여부 판단
        
        Args:
            consensus_level: 합의 수준
            judgments: LLM 판단들
            data: 원본 데이터
            
        Returns:
            전문가 검토 필요 여부
        """
        # 1. 낮은 합의 수준
        if consensus_level < self.min_consensus_threshold:
            return True
        
        # 2. 고위험 진단
        high_risk_diagnoses = {
            'major_depression_severe',
            'bipolar_disorder',
            'psychotic_disorder',
            'suicidal_ideation'
        }
        
        for judgment in judgments:
            if any(risk in judgment.diagnosis.lower() for risk in high_risk_diagnoses):
                return True
        
        # 3. 높은 PHQ-9/GAD-7 점수
        if data.get('phq9_score', 0) >= 20:  # Severe depression
            return True
        if data.get('gad7_score', 0) >= 15:  # Severe anxiety
            return True
        
        # 4. 자살 위험 키워드
        transcription = data.get('transcription', '').lower()
        suicide_keywords = ['자살', '죽고싶', 'suicide', 'kill myself']
        if any(keyword in transcription for keyword in suicide_keywords):
            return True
        
        return False
    
    async def _call_llm_api(self, provider: LLMProvider, prompt: str) -> str:
        """
        실제 LLM API 호출
        
        Args:
            provider: LLM 제공자
            prompt: 프롬프트
            
        Returns:
            API 응답
        """
        # TODO: 실제 API 구현
        # 임시 모의 응답
        import random
        
        diagnoses = ['depression', 'anxiety', 'adjustment_disorder', 'normal']
        severities = ['mild', 'moderate', 'severe']
        
        return json.dumps({
            'primary_diagnosis': random.choice(diagnoses),
            'severity': random.choice(severities),
            'confidence': random.uniform(0.7, 0.95),
            'evidence': ['symptom1', 'symptom2'],
            'reasoning': 'Based on DSM-5 criteria...',
            'differential_diagnosis': ['alternative1'],
            'recommendations': ['therapy', 'monitoring']
        })
    
    async def _get_rag_context(self, data: Dict) -> str:
        """
        RAG 지식베이스에서 관련 컨텍스트 검색
        
        Args:
            data: 평가 데이터
            
        Returns:
            관련 의료 지식
        """
        # TODO: 실제 RAG 구현
        return """
        **Relevant DSM-5 Criteria:**
        - Major Depressive Disorder: 5+ symptoms for 2+ weeks
        - Generalized Anxiety Disorder: Excessive worry for 6+ months
        - Adjustment Disorder: Symptoms within 3 months of stressor
        """
    
    def _hash_data(self, data: Dict) -> str:
        """데이터 해시 생성"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.md5(data_str.encode()).hexdigest()
    
    def validate_consensus_quality(self, consensus: ConsensusLabel) -> Dict:
        """
        합의 품질 검증
        
        Args:
            consensus: 합의 레이블
            
        Returns:
            품질 메트릭
        """
        quality_metrics = {
            'consensus_strength': consensus.consensus_level,
            'is_unanimous': consensus.is_unanimous,
            'num_agreeing': sum(1 for j in consensus.individual_judgments 
                              if j.diagnosis == consensus.final_diagnosis),
            'avg_confidence': sum(j.confidence for j in consensus.individual_judgments) / 
                            len(consensus.individual_judgments),
            'requires_expert': consensus.requires_expert_review
        }
        
        # 품질 점수 계산
        quality_score = (
            quality_metrics['consensus_strength'] * 0.4 +
            quality_metrics['avg_confidence'] * 0.3 +
            (1.0 if quality_metrics['is_unanimous'] else 0.7) * 0.3
        )
        
        quality_metrics['overall_quality'] = quality_score
        quality_metrics['can_use_as_label'] = (
            quality_score >= 0.8 and not consensus.requires_expert_review
        )
        
        return quality_metrics