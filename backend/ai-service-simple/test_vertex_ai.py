"""
Vertex AI Gemini API 테스트 스크립트
실제 작동 확인용
"""

import os
import asyncio
from dotenv import load_dotenv
import vertexai
from vertexai.generative_models import GenerativeModel

# 환경 변수 로드
load_dotenv()


def test_basic_connection():
    """기본 연결 테스트"""
    print("=== Vertex AI 연결 테스트 ===")

    project_id = os.getenv('GCP_PROJECT_ID')
    location = os.getenv('GCP_LOCATION', 'asia-northeast3')

    if not project_id:
        print("❌ GCP_PROJECT_ID가 설정되지 않았습니다.")
        return False

    print(f"프로젝트 ID: {project_id}")
    print(f"리전: {location}")

    try:
        # Vertex AI 초기화
        vertexai.init(project=project_id, location=location)
        print("✅ Vertex AI 초기화 성공")
        return True
    except Exception as e:
        print(f"❌ Vertex AI 초기화 실패: {e}")
        return False


def test_simple_generation():
    """간단한 텍스트 생성 테스트"""
    print("\n=== 텍스트 생성 테스트 ===")

    try:
        # 모델 초기화
        model = GenerativeModel("gemini-1.5-flash")

        # 간단한 프롬프트
        prompt = "한국의 수도는 어디인가요? 한 문장으로 답해주세요."

        print(f"프롬프트: {prompt}")

        # 응답 생성
        response = model.generate_content(prompt)

        print(f"응답: {response.text}")
        print("✅ 텍스트 생성 성공")
        return True

    except Exception as e:
        print(f"❌ 텍스트 생성 실패: {e}")
        return False


def test_mental_health_analysis():
    """정신건강 분석 테스트"""
    print("\n=== 정신건강 분석 테스트 ===")

    try:
        model = GenerativeModel(
            "gemini-1.5-flash",
            generation_config={
                'temperature': 0.7,
                'top_p': 0.95,
                'max_output_tokens': 1024,
            }
        )

        test_text = "요즘 계속 피곤하고 무기력해요. 아무것도 하기 싫고 그냥 누워있고 싶어요."

        prompt = f"""
        다음 텍스트를 분석하여 정신건강 상태를 평가해주세요.

        텍스트: "{test_text}"

        다음 형식의 JSON으로 응답해주세요:
        {{
            "depression_score": 0-100 사이의 우울증 가능성 점수,
            "anxiety_score": 0-100 사이의 불안 수준 점수,
            "emotional_state": "현재 감정 상태",
            "recommendations": ["권장사항"]
        }}
        """

        print(f"분석할 텍스트: {test_text}")

        response = model.generate_content(prompt)

        print(f"분석 결과:\n{response.text}")
        print("✅ 정신건강 분석 성공")
        return True

    except Exception as e:
        print(f"❌ 정신건강 분석 실패: {e}")
        return False


async def test_async_generation():
    """비동기 생성 테스트"""
    print("\n=== 비동기 생성 테스트 ===")

    try:
        model = GenerativeModel("gemini-1.5-flash")

        prompt = "AI가 정신건강 분석에 어떻게 도움이 될 수 있나요? 간단히 설명해주세요."

        print(f"프롬프트: {prompt}")

        # 비동기 응답 생성
        response = await model.generate_content_async(prompt)

        print(f"응답: {response.text}")
        print("✅ 비동기 생성 성공")
        return True

    except Exception as e:
        print(f"❌ 비동기 생성 실패: {e}")
        return False


def test_chat_session():
    """대화 세션 테스트"""
    print("\n=== 대화 세션 테스트 ===")

    try:
        model = GenerativeModel("gemini-1.5-flash")

        # 채팅 세션 시작
        chat = model.start_chat()

        # 첫 번째 메시지
        response1 = chat.send_message("안녕하세요, 저는 우울증 증상이 있는 것 같아요.")
        print(f"사용자: 안녕하세요, 저는 우울증 증상이 있는 것 같아요.")
        print(f"AI: {response1.text}")

        # 두 번째 메시지 (컨텍스트 유지)
        response2 = chat.send_message("어떤 도움을 받을 수 있을까요?")
        print(f"\n사용자: 어떤 도움을 받을 수 있을까요?")
        print(f"AI: {response2.text}")

        print("✅ 대화 세션 성공")
        return True

    except Exception as e:
        print(f"❌ 대화 세션 실패: {e}")
        return False


def test_model_listing():
    """사용 가능한 모델 확인"""
    print("\n=== 사용 가능한 모델 ===")

    available_models = [
        "gemini-1.5-flash",
        "gemini-1.5-pro",
        "gemini-1.0-pro"
    ]

    for model_name in available_models:
        try:
            model = GenerativeModel(model_name)
            # 간단한 테스트로 모델 가용성 확인
            response = model.generate_content("Hi")
            print(f"✅ {model_name}: 사용 가능")
        except Exception as e:
            print(f"❌ {model_name}: 사용 불가 - {str(e)[:50]}")


async def main():
    """메인 테스트 실행"""
    print("=" * 50)
    print("Vertex AI Gemini API 테스트 시작")
    print("=" * 50)

    # 1. 기본 연결 테스트
    if not test_basic_connection():
        print("\n⚠️ 기본 연결 실패. 환경 설정을 확인하세요.")
        return

    # 2. 간단한 생성 테스트
    test_simple_generation()

    # 3. 정신건강 분석 테스트
    test_mental_health_analysis()

    # 4. 비동기 생성 테스트
    await test_async_generation()

    # 5. 대화 세션 테스트
    test_chat_session()

    # 6. 모델 목록 확인
    test_model_listing()

    print("\n" + "=" * 50)
    print("테스트 완료!")
    print("=" * 50)


if __name__ == "__main__":
    # 비동기 실행
    asyncio.run(main())