"""
음성 추출 로직 테스트 스크립트
Google Cloud STT 없이 speaker ID 매핑과 추출 로직만 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from analysis.pipeline.main_pipeline import SeniorMentalHealthPipeline
import logging
import json

# 로깅 설정
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_speaker_id_mapping():
    """화자 ID 매핑 로직 테스트"""
    import re
    
    test_cases = [
        ("화자 0", 1),  # AI returns "화자 0", STT uses 1
        ("화자 1", 2),  # AI returns "화자 1", STT uses 2
        ("화자 2", 3),  # AI returns "화자 2", STT uses 3
    ]
    
    for ai_id, expected_stt_id in test_cases:
        # AI가 반환한 "화자 0" 형식에서 숫자만 추출
        match = re.search(r'화자\s*(\d+)', str(ai_id))
        if match:
            # 숫자 추출 성공 - STT API의 speaker_tag는 1부터 시작하므로 +1
            stt_id = int(match.group(1)) + 1
            print(f"✓ {ai_id} -> {stt_id} (expected: {expected_stt_id})")
            assert stt_id == expected_stt_id
        else:
            print(f"✗ Failed to parse {ai_id}")

def test_segment_matching():
    """세그먼트 매칭 로직 테스트"""
    
    # 모의 STT 세그먼트 (Google Cloud STT 형식)
    mock_segments = [
        {'speaker_id': 1, 'text': '엄마 오늘 뭐 먹었어요?', 'start_time': 0.0, 'end_time': 2.5},
        {'speaker_id': 2, 'text': '그냥 대충 먹었어', 'start_time': 2.5, 'end_time': 4.0},
        {'speaker_id': 1, 'text': '혼자 계시니까 외로우시죠?', 'start_time': 4.0, 'end_time': 6.0},
        {'speaker_id': 2, 'text': '응, 요즘 기다리는 시간이 길어졌어', 'start_time': 6.0, 'end_time': 8.5},
    ]
    
    # AI 판별 결과
    speaker_info = {
        'senior_speaker_id': '화자 1',  # AI가 화자 1을 시니어로 판별
        'confidence': 0.9,
        'reasoning': '혼자 식사, 외로움 표현 등 시니어 특징'
    }
    
    # 화자 ID 변환 로직 테스트
    import re
    senior_speaker_id = speaker_info.get('senior_speaker_id')
    match = re.search(r'화자\s*(\d+)', str(senior_speaker_id))
    if match:
        senior_speaker_numeric = int(match.group(1)) + 1  # 화자 1 -> 2
    else:
        senior_speaker_numeric = senior_speaker_id
    
    print(f"\n화자 ID 변환: AI='{senior_speaker_id}' -> STT={senior_speaker_numeric}")
    
    # 시니어 텍스트 추출
    senior_texts = []
    for seg in mock_segments:
        seg_speaker_id = seg.get('speaker_id')
        if (seg_speaker_id == senior_speaker_numeric or 
            str(seg_speaker_id) == str(senior_speaker_numeric)):
            senior_texts.append(seg.get('text', ''))
            print(f"  ✓ 시니어 발화 추출: {seg.get('text')}")
    
    print(f"\n추출된 시니어 텍스트:")
    print(' '.join(senior_texts))
    
    expected_texts = ['그냥 대충 먹었어', '응, 요즘 기다리는 시간이 길어졌어']
    assert senior_texts == expected_texts, f"Expected {expected_texts}, got {senior_texts}"

def test_with_actual_pipeline():
    """실제 파이프라인 메서드 테스트 (STT 없이)"""
    
    pipeline = SeniorMentalHealthPipeline()
    
    # 모의 세그먼트
    segments = [
        {'speaker_id': 1, 'text': '안녕하세요 어머니', 'start_time': 0, 'end_time': 2},
        {'speaker_id': 2, 'text': '어, 안녕', 'start_time': 2, 'end_time': 3},
    ]
    
    # AI 판별 결과
    speaker_info = {
        'senior_speaker_id': '화자 1',
        'confidence': 0.85
    }
    
    # _extract_senior_text 메서드 테스트
    senior_text = pipeline._extract_senior_text(segments, speaker_info)
    print(f"\n파이프라인 추출 텍스트: '{senior_text}'")
    
    # 예상 결과: 화자 1 -> STT ID 2
    assert senior_text == '어, 안녕', f"Expected '어, 안녕', got '{senior_text}'"

if __name__ == "__main__":
    print("=" * 50)
    print("음성 추출 로직 테스트")
    print("=" * 50)
    
    print("\n1. 화자 ID 매핑 테스트")
    print("-" * 30)
    test_speaker_id_mapping()
    
    print("\n2. 세그먼트 매칭 테스트")
    print("-" * 30)
    test_segment_matching()
    
    print("\n3. 파이프라인 메서드 테스트")
    print("-" * 30)
    test_with_actual_pipeline()
    
    print("\n" + "=" * 50)
    print("✅ 모든 테스트 통과!")
    print("=" * 50)