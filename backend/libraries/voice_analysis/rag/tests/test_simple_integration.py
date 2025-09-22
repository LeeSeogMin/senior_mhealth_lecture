#!/usr/bin/env python3
"""
간단한 RAG 통합 테스트
기존 develop_lee 구조에서 RAG 기능이 정상 작동하는지 확인
"""

import asyncio
import os
import sys
import json
from datetime import datetime

# 프로젝트 루트를 Python 경로에 추가
current_dir = os.path.dirname(os.path.abspath(__file__))
voice_analysis_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(voice_analysis_root)

# 환경 변수 설정 (테스트용)
os.environ.setdefault('GOOGLE_CLOUD_PROJECT', 'senior-mhealth-test')

async def test_vector_store_manager():
    """벡터스토어 매니저 테스트"""
    print("🔍 벡터스토어 매니저 테스트 시작")
    print("=" * 50)
    
    try:
        from rag.core.vector_store_manager import FirebaseStorageVectorStore
        
        # Firebase 기능을 사용하지 않고 로컬 기능만 테스트
        vector_store = FirebaseStorageVectorStore()
        
        # 로컬 임베딩 파일 확인
        embeddings_path = vector_store.local_embeddings_path
        print(f"임베딩 파일 경로: {embeddings_path}")
        
        if os.path.exists(embeddings_path):
            file_size = os.path.getsize(embeddings_path)
            print(f"✅ 임베딩 파일 존재 (크기: {file_size:,} bytes)")
            
            # 로컬 임베딩 로드 테스트
            await vector_store._load_local_embeddings()
            
            if vector_store._embedding_cache:
                print(f"✅ 임베딩 캐시 로드 성공: {len(vector_store._embedding_cache)}개 문서")
                
                # 첫 번째 문서 구조 확인
                first_doc = vector_store._embedding_cache[0]
                print("📝 첫 번째 문서 구조:")
                for key in first_doc.keys():
                    if key == 'embedding':
                        print(f"  - {key}: 벡터 (길이: {len(first_doc[key])})")
                    else:
                        value = first_doc[key]
                        if isinstance(value, str) and len(value) > 50:
                            print(f"  - {key}: {value[:50]}...")
                        else:
                            print(f"  - {key}: {value}")
                
                return True
            else:
                print("❌ 임베딩 캐시 로드 실패")
                return False
        else:
            print(f"❌ 임베딩 파일이 존재하지 않음: {embeddings_path}")
            return False
            
    except Exception as e:
        print(f"❌ 벡터스토어 매니저 테스트 실패: {e}")
        return False

async def test_document_search():
    """문서 검색 테스트"""
    print("\n🔍 문서 검색 테스트 시작")
    print("=" * 50)
    
    try:
        from rag.core.vector_store_manager import FirebaseStorageVectorStore
        
        vector_store = FirebaseStorageVectorStore()
        
        # OpenAI API 키가 있는지 확인
        if not os.getenv('OPENAI_API_KEY'):
            print("⚠️ OPENAI_API_KEY가 설정되지 않음. 검색 기능은 API 키가 필요합니다.")
            return False
        
        # 테스트 쿼리
        test_queries = [
            "우울증 증상과 진단",
            "노인 인지 기능 저하",
            "수면 장애 치료 방법"
        ]
        
        for query in test_queries:
            print(f"\n검색 쿼리: '{query}'")
            try:
                results = await vector_store.search_similar_documents(
                    query_text=query,
                    max_results=3,
                    similarity_threshold=0.5  # 테스트를 위해 낮은 임계값 사용
                )
                
                if results:
                    print(f"✅ {len(results)}개 문서 검색됨")
                    for i, doc in enumerate(results, 1):
                        similarity = doc.get('similarity', 0)
                        content = doc.get('content', doc.get('text', ''))[:100]
                        print(f"  {i}. 유사도: {similarity:.3f} | 내용: {content}...")
                else:
                    print("⚠️ 검색 결과 없음")
                    
            except Exception as e:
                print(f"❌ 쿼리 '{query}' 검색 실패: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ 문서 검색 테스트 실패: {e}")
        return False

async def test_rag_enhanced_analyzer():
    """RAG 강화 분석기 테스트"""
    print("\n🧠 RAG 강화 분석기 테스트 시작")
    print("=" * 50)
    
    try:
        from rag.core.rag_enhanced_analyzer import RAGEnhancedTextAnalyzer
        
        # RAG 기능을 비활성화하고 기본 분석기로 테스트 (API 키 없이도 작동)
        analyzer = RAGEnhancedTextAnalyzer(use_rag=False)
        print("✅ RAG 강화 분석기 초기화 성공 (RAG 비활성화 모드)")
        
        # 테스트 텍스트
        test_text = "요즘 잠을 잘 못 자고, 기분도 우울해요. 기억력도 예전 같지 않고 집중하기가 어려워요."
        
        print(f"\n📝 테스트 텍스트: {test_text}")
        
        # 기본 분석 테스트 (RAG 없이)
        result = await analyzer.analyze(test_text)
        
        if result.get('status') == 'success':
            print("✅ 기본 텍스트 분석 성공")
            indicators = result.get('analysis', {}).get('indicators', {})
            print("📊 분석 지표:")
            for key, value in indicators.items():
                print(f"  - {key}: {value}")
        else:
            print(f"⚠️ 기본 분석 결과: {result.get('status')} - {result.get('error', 'Unknown error')}")
        
        # RAG 활성화 테스트 (API 키가 있는 경우에만)
        if os.getenv('OPENAI_API_KEY'):
            print("\n🔍 RAG 활성화 테스트...")
            rag_analyzer = RAGEnhancedTextAnalyzer(use_rag=True)
            
            if rag_analyzer.use_rag:
                print("✅ RAG 기능 활성화됨")
                
                rag_result = await rag_analyzer.analyze_with_rag(test_text)
                
                if rag_result.get('rag_metadata'):
                    print("✅ RAG 메타데이터 포함됨")
                    rag_meta = rag_result['rag_metadata']
                    print(f"  - RAG 사용: {rag_meta.get('rag_used')}")
                    print(f"  - 검색된 컨텍스트: {rag_meta.get('context_count')}개")
                
        return True
        
    except Exception as e:
        print(f"❌ RAG 강화 분석기 테스트 실패: {e}")
        return False

async def main():
    """메인 테스트 함수"""
    print("🚀 RAG 통합 테스트 시작")
    print("=" * 70)
    
    results = []
    
    # 1. 벡터스토어 매니저 테스트
    results.append(await test_vector_store_manager())
    
    # 2. 문서 검색 테스트
    results.append(await test_document_search())
    
    # 3. RAG 강화 분석기 테스트
    results.append(await test_rag_enhanced_analyzer())
    
    # 결과 요약
    print("\n" + "=" * 70)
    print("📊 테스트 결과 요약")
    print("=" * 70)
    
    test_names = [
        "벡터스토어 매니저",
        "문서 검색",
        "RAG 강화 분석기"
    ]
    
    passed = 0
    for i, (name, result) in enumerate(zip(test_names, results)):
        status = "✅ 통과" if result else "❌ 실패"
        print(f"{i+1}. {name}: {status}")
        if result:
            passed += 1
    
    print(f"\n전체 결과: {passed}/{len(results)} 테스트 통과")
    
    if passed == len(results):
        print("🎉 모든 테스트가 성공적으로 완료되었습니다!")
    else:
        print("⚠️ 일부 테스트가 실패했습니다. 로그를 확인해주세요.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)