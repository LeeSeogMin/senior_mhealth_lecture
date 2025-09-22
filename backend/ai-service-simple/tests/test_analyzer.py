"""
Gemini 분석기 테스트
"""

import os
import sys
import asyncio
from pathlib import Path

# 프로젝트 경로 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.gemini_analyzer import (
    GeminiTextAnalyzer,
    AnalysisRequest,
    AnalysisResponse
)


async def test_basic_analysis():
    """기본 분석 테스트"""
    print("=== 기본 분석 테스트 ===")

    # 테스트용 텍스트
    test_texts = [
        "요즘 너무 힘들어요. 아무것도 하고 싶지 않고 매일 우울해요.",
        "불안하고 초조해요. 잠도 잘 못 자고 계속 걱정만 하게 됩니다.",
        "오늘은 기분이 좋아요. 날씨도 좋고 운동도 했어요.",
        "기억력이 예전 같지 않아요. 자주 깜빡하고 집중이 안 돼요."
    ]

    try:
        # 분석기 초기화
        analyzer = GeminiTextAnalyzer()

        for i, text in enumerate(test_texts, 1):
            print(f"\n테스트 {i}: {text[:30]}...")

            request = AnalysisRequest(
                text=text,
                user_id=f"test_user_{i}",
                session_id=f"test_session_{i}"
            )

            # 분석 수행
            result = await analyzer.analyze_mental_health(request)

            print(f"  우울도: {result.depression_score}")
            print(f"  불안도: {result.anxiety_score}")
            print(f"  인지기능: {result.cognitive_score}")
            print(f"  감정상태: {result.emotional_state}")
            print(f"  신뢰도: {result.confidence}")
            print(f"  주요 우려사항: {result.key_concerns}")
            print(f"  권장사항: {result.recommendations[:2] if result.recommendations else []}")

    except Exception as e:
        print(f"테스트 실패: {str(e)}")
        return False

    return True


async def test_edge_cases():
    """엣지 케이스 테스트"""
    print("\n=== 엣지 케이스 테스트 ===")

    test_cases = [
        ("", "빈 텍스트"),
        ("안녕", "매우 짧은 텍스트"),
        ("a" * 5000, "매우 긴 텍스트"),
    ]

    try:
        analyzer = GeminiTextAnalyzer()

        for text, description in test_cases:
            print(f"\n테스트: {description}")

            request = AnalysisRequest(
                text=text,
                user_id="edge_test",
                session_id="edge_session"
            )

            result = await analyzer.analyze_mental_health(request)
            print(f"  결과: {result.emotional_state}")
            print(f"  신뢰도: {result.confidence}")

    except Exception as e:
        print(f"엣지 케이스 테스트 실패: {str(e)}")
        return False

    return True


async def main():
    """메인 테스트 함수"""
    print("Gemini 분석기 테스트 시작\n")

    # API 키 확인
    if not os.getenv("GOOGLE_API_KEY"):
        print("경고: GOOGLE_API_KEY가 설정되지 않았습니다.")
        print(".env 파일을 확인하거나 환경변수를 설정하세요.")
        return

    # 테스트 실행
    success = True

    if await test_basic_analysis():
        print("\n✅ 기본 분석 테스트 통과")
    else:
        print("\n❌ 기본 분석 테스트 실패")
        success = False

    if await test_edge_cases():
        print("\n✅ 엣지 케이스 테스트 통과")
    else:
        print("\n❌ 엣지 케이스 테스트 실패")
        success = False

    if success:
        print("\n🎉 모든 테스트 통과!")
    else:
        print("\n⚠️ 일부 테스트 실패")


if __name__ == "__main__":
    # 환경변수 로드
    from dotenv import load_dotenv
    load_dotenv()

    # 테스트 실행
    asyncio.run(main())