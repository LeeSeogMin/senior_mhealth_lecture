#!/usr/bin/env python3
"""
RAG 통합 테스트 스크립트
"""

import asyncio
import os
import sys
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.pipeline.main_pipeline import AnalysisPipeline
from analysis.core.text_analysis import TextAnalyzer
from analysis.core.comprehensive_interpreter import ComprehensiveInterpreter
from analysis.core.indicators import IndicatorCalculator
from analysis.timeseries.trend_analyzer import TrendAnalyzer

async def test_rag_integration():
    """RAG 통합 테스트"""
    print("🚀 RAG 통합 테스트 시작")
    print("=" * 50)
    
    # 1. RAG 설정 확인
    print("1. RAG 설정 확인...")
    embeddings_path = "analysis/vector_store/embeddings.jsonl"
    if not os.path.exists(embeddings_path):
        print(f"❌ 벡터스토어 파일이 없습니다: {embeddings_path}")
        return False
    print(f"✅ 벡터스토어 파일 확인: {embeddings_path}")
    
    # 2. TextAnalyzer RAG 테스트
    print("\n2. TextAnalyzer RAG 테스트...")
    try:
        text_analyzer = TextAnalyzer(use_rag=True)
        test_text = "노인 우울증 증상과 치료 방법에 대해 알려주세요."
        
        result = await text_analyzer.analyze(test_text)
        print(f"✅ TextAnalyzer RAG 테스트 성공")
        print(f"   - 분석 결과: {result.get('analysis', {}).get('summary', 'N/A')}")
        print(f"   - RAG 출처: {result.get('sources', [])[:2]}...")  # 처음 2개만 표시
    except Exception as e:
        print(f"❌ TextAnalyzer RAG 테스트 실패: {e}")
        return False
    
    # 3. ComprehensiveInterpreter RAG 테스트
    print("\n3. ComprehensiveInterpreter RAG 테스트...")
    try:
        interpreter = ComprehensiveInterpreter(use_rag=True)
        
        # 가상의 분석 결과 생성
        mock_analysis = {
            'indicators': {
                'DRI': 0.3,  # 우울 위험
                'SDI': 0.6,
                'CFL': 0.4,  # 인지 기능 저하
                'ES': 0.7,
                'OV': 0.5
            },
            'clinical_validation': {
                'risk_level': 'moderate'
            },
            'text_analysis': {
                'analysis': {
                    'key_findings': ['우울감', '의욕 저하']
                }
            }
        }
        
        result = await interpreter.interpret(mock_analysis)
        print(f"✅ ComprehensiveInterpreter RAG 테스트 성공")
        print(f"   - 해석 방법: {result.get('method', 'N/A')}")
        print(f"   - RAG 출처: {result.get('rag_sources', [])[:2]}...")
    except Exception as e:
        print(f"❌ ComprehensiveInterpreter RAG 테스트 실패: {e}")
        return False
    
    # 4. IndicatorCalculator RAG 테스트
    print("\n4. IndicatorCalculator RAG 테스트...")
    try:
        from analysis.core.indicators import MentalHealthIndicators
        calculator = IndicatorCalculator(use_rag=True)
        
        indicators = MentalHealthIndicators(
            DRI=0.3,  # 우울 위험
            SDI=0.6,
            CFL=0.4,  # 인지 기능 저하
            ES=0.7,
            OV=0.5
        )
        
        risk_result = calculator.calculate_risk_scores(indicators)
        print(f"✅ IndicatorCalculator RAG 테스트 성공")
        print(f"   - 위험도 평가 방법: {risk_result.get('method', 'N/A')}")
        print(f"   - 종합 위험도: {risk_result.get('overall_risk', 'N/A')}")
        print(f"   - RAG 출처: {risk_result.get('rag_sources', [])[:2]}...")
    except Exception as e:
        print(f"❌ IndicatorCalculator RAG 테스트 실패: {e}")
        return False
    
    # 5. TrendAnalyzer RAG 테스트
    print("\n5. TrendAnalyzer RAG 테스트...")
    try:
        trend_analyzer = TrendAnalyzer(use_rag=True)
        
        # 가상의 시계열 데이터 생성
        mock_trend_data = [
            {
                'analysis_timestamp': '2024-01-01T10:00:00Z',
                'indicators': {'DRI': 0.3, 'SDI': 0.6, 'CFL': 0.4, 'ES': 0.7, 'OV': 0.5}
            },
            {
                'analysis_timestamp': '2024-01-08T10:00:00Z',
                'indicators': {'DRI': 0.2, 'SDI': 0.5, 'CFL': 0.3, 'ES': 0.6, 'OV': 0.4}
            },
            {
                'analysis_timestamp': '2024-01-15T10:00:00Z',
                'indicators': {'DRI': 0.1, 'SDI': 0.4, 'CFL': 0.2, 'ES': 0.5, 'OV': 0.3}
            }
        ]
        
        result = trend_analyzer.analyze_trends(mock_trend_data)
        print(f"✅ TrendAnalyzer RAG 테스트 성공")
        print(f"   - 분석 방법: {result.get('method', 'N/A')}")
        if 'clinical_interpretation' in result:
            print(f"   - 임상적 해석: {result['clinical_interpretation'].get('clinical_significance', 'N/A')[:50]}...")
    except Exception as e:
        print(f"❌ TrendAnalyzer RAG 테스트 실패: {e}")
        return False
    
    # 6. 전체 파이프라인 RAG 테스트
    print("\n6. 전체 파이프라인 RAG 테스트...")
    try:
        pipeline = AnalysisPipeline(config={'use_rag': True})
        print(f"✅ 파이프라인 RAG 설정 성공")
        print(f"   - TextAnalyzer RAG: {pipeline.text_analyzer.use_rag}")
        print(f"   - ComprehensiveInterpreter RAG: {pipeline.comprehensive_interpreter.use_rag}")
        print(f"   - IndicatorCalculator RAG: {pipeline.indicator_calculator.use_rag}")
        print(f"   - TrendAnalyzer RAG: {pipeline.trend_analyzer.use_rag}")
    except Exception as e:
        print(f"❌ 파이프라인 RAG 테스트 실패: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("🎉 모든 RAG 통합 테스트 성공!")
    print("✅ RAG가 모든 분석 단계에 성공적으로 통합되었습니다.")
    
    return True

async def test_rag_performance():
    """RAG 성능 테스트"""
    print("\n🔍 RAG 성능 테스트")
    print("=" * 30)
    
    try:
        from analysis.core.rag_monitor import RAGPerformanceMonitor, RAGOptimizer
        
        # 모니터 초기화
        monitor = RAGPerformanceMonitor()
        optimizer = RAGOptimizer(monitor)
        
        # 성능 리포트 확인
        report = monitor.get_performance_report()
        print(f"📊 성능 통계:")
        print(f"   - 총 쿼리 수: {report.get('total_queries', 0)}")
        print(f"   - 평균 검색 시간: {report.get('avg_search_time', 0):.3f}초")
        print(f"   - 캐시 히트율: {report.get('cache_hit_rate', 0):.2%}")
        
        # 최적화 제안 확인
        suggestions = monitor.get_optimization_suggestions()
        if suggestions:
            print(f"💡 최적화 제안:")
            for suggestion in suggestions:
                print(f"   - {suggestion}")
        else:
            print("✅ 성능 최적화 제안사항 없음")
        
        return True
    except Exception as e:
        print(f"❌ RAG 성능 테스트 실패: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("🧪 Senior MHealth RAG 통합 테스트")
    print(f"시작 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # RAG 통합 테스트
    integration_success = await test_rag_integration()
    
    # RAG 성능 테스트
    performance_success = await test_rag_performance()
    
    print("\n" + "=" * 60)
    print("📋 테스트 결과 요약:")
    print(f"   - RAG 통합 테스트: {'✅ 성공' if integration_success else '❌ 실패'}")
    print(f"   - RAG 성능 테스트: {'✅ 성공' if performance_success else '❌ 실패'}")
    
    if integration_success and performance_success:
        print("\n🎊 모든 테스트 통과! RAG 시스템이 정상적으로 작동합니다.")
        return 0
    else:
        print("\n⚠️ 일부 테스트가 실패했습니다. 로그를 확인해주세요.")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
