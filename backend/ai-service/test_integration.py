#!/usr/bin/env python
"""
AI Analysis Service 통합 테스트
모든 분석 컴포넌트 (음성, 텍스트, SincNet, RAG) 검증
"""

import asyncio
import json
import sys
from pathlib import Path
from datetime import datetime

# 라이브러리 경로 추가
sys.path.append(str(Path(__file__).parent.parent / "libraries" / "voice_analysis"))

from analysis.pipeline.main_pipeline import SeniorMentalHealthPipeline

async def test_text_analysis():
    """텍스트 분석 테스트 (RAG 포함/미포함)"""
    print("\n" + "="*50)
    print("텍스트 분석 테스트")
    print("="*50)
    
    # 테스트 텍스트
    test_text = """
    요즘 기분이 좀 우울해요. 밤에 잠도 잘 안 오고, 
    자꾸 옛날 생각이 나네요. 혼자 있으면 더 외로운 것 같아요.
    """
    
    # 기본 텍스트 분석 (RAG 없이)
    print("\n1. 기본 텍스트 분석 (RAG 미사용)")
    config_no_rag = {'use_rag': False}
    pipeline_no_rag = SeniorMentalHealthPipeline(config=config_no_rag)
    
    if pipeline_no_rag.text_analyzer:
        result_no_rag = await pipeline_no_rag.text_analyzer.analyze(test_text)
        print(f"   - 감정 분석: {result_no_rag.get('emotion', 'N/A')}")
        print(f"   - 주요 주제: {result_no_rag.get('topics', 'N/A')}")
    
    # RAG 강화 텍스트 분석
    print("\n2. RAG 강화 텍스트 분석")
    config_with_rag = {'use_rag': True}
    pipeline_with_rag = SeniorMentalHealthPipeline(config=config_with_rag)
    
    if pipeline_with_rag.text_analyzer:
        result_with_rag = await pipeline_with_rag.text_analyzer.analyze(test_text)
        print(f"   - 감정 분석: {result_with_rag.get('emotion', 'N/A')}")
        print(f"   - 주요 주제: {result_with_rag.get('topics', 'N/A')}")
        if 'rag_metadata' in result_with_rag:
            print(f"   - RAG 컨텍스트 사용: {result_with_rag['rag_metadata'].get('context_used', False)}")

async def test_component_availability():
    """컴포넌트 가용성 테스트"""
    print("\n" + "="*50)
    print("컴포넌트 가용성 테스트")
    print("="*50)
    
    config = {
        'use_sincnet': True,
        'use_rag': True
    }
    
    pipeline = SeniorMentalHealthPipeline(config=config)
    
    components = {
        '음성 분석 (Librosa)': pipeline.voice_analyzer is not None,
        '텍스트 분석 (GPT-4o/Gemini)': pipeline.text_analyzer is not None,
        'SincNet 딥러닝': pipeline.sincnet_analyzer is not None,
        '지표 계산기': pipeline.indicator_calculator is not None,
        'STT 커넥터': pipeline.stt_connector is not None,
        'RAG 지원': hasattr(pipeline, 'vector_store') and pipeline.vector_store is not None
    }
    
    for component, available in components.items():
        status = "✅ 사용 가능" if available else "❌ 사용 불가"
        print(f"   - {component}: {status}")
    
    return all(components.values())

async def test_indicator_calculation():
    """5대 지표 계산 테스트"""
    print("\n" + "="*50)
    print("5대 지표 계산 테스트")
    print("="*50)
    
    pipeline = SeniorMentalHealthPipeline()
    
    # 모의 분석 결과
    mock_voice_features = {
        'pitch_mean': 150.0,
        'pitch_std': 30.0,
        'energy_mean': 0.5,
        'energy_std': 0.1,
        'mfcc_features': [0.1] * 13,
        'tempo': 120.0,
        'spectral_centroid': 2000.0
    }
    
    mock_text_analysis = {
        'emotion': {'우울': 0.6, '불안': 0.3, '평온': 0.1},
        'topics': ['외로움', '수면장애', '회상'],
        'sentiment_score': -0.4
    }
    
    mock_sincnet_analysis = {
        'depression_probability': 0.65,
        'cognitive_score': 0.7,
        'emotional_stability': 0.4
    }
    
    # 지표 계산
    indicators = pipeline.indicator_calculator.calculate(
        voice_features=mock_voice_features,
        text_analysis=mock_text_analysis,
        sincnet_analysis=mock_sincnet_analysis
    )
    
    if indicators:
        print("\n   계산된 5대 지표:")
        print(f"   - DRI (우울위험도): {indicators.DRI:.2f}")
        print(f"   - SDI (수면장애): {indicators.SDI:.2f}")
        print(f"   - CFL (인지기능): {indicators.CFL:.2f}")
        print(f"   - ES (정서안정성): {indicators.ES:.2f}")
        print(f"   - OV (전반적활력도): {indicators.OV:.2f}")
        
        # 위험도 평가
        risk_level = "높음" if indicators.DRI < 0.4 else "중간" if indicators.DRI < 0.7 else "낮음"
        print(f"\n   우울 위험도: {risk_level}")

async def main():
    """메인 테스트 실행"""
    print("\n" + "🚀 AI 분석 서비스 통합 테스트 시작 " + "🚀")
    print("=" * 60)
    print(f"테스트 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # 1. 컴포넌트 가용성 테스트
        await test_component_availability()
        
        # 2. 텍스트 분석 테스트 (RAG 포함)
        await test_text_analysis()
        
        # 3. 지표 계산 테스트
        await test_indicator_calculation()
        
        print("\n" + "="*60)
        print("✅ 모든 테스트 완료!")
        print("="*60)
        
    except Exception as e:
        print(f"\n❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)