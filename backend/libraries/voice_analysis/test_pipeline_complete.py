#!/usr/bin/env python
"""
전체 파이프라인 테스트 - SincNet + Librosa + GPT-4o + 시계열 분석 + AI 종합 해석
타임아웃 없이 전체 프로세스 실행
"""

import os
import sys
import asyncio
import logging
import time
from pathlib import Path
from datetime import datetime
import json

# 프로젝트 경로 설정
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

# 에뮬레이터 환경 변수 설정
os.environ['FIRESTORE_EMULATOR_HOST'] = 'localhost:8081'
os.environ['GCP_PROJECT_ID'] = 'demo-project'

# 로깅 설정 - 더 상세한 로그
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def run_full_pipeline(audio_file: str, user_id: str, iteration: int = 1):
    """전체 파이프라인 실행"""
    
    from ai.analysis.pipeline.main_pipeline import SeniorMentalHealthPipeline
    
    print(f"\n{'='*70}")
    print(f"🚀 분석 {iteration}: {audio_file}")
    print(f"{'='*70}")
    
    # 파일 확인
    test_data_dir = project_root / 'ai' / 'analysis' / 'test_data'
    audio_path = test_data_dir / audio_file
    
    if not audio_path.exists():
        print(f"❌ 파일 없음: {audio_path}")
        return None
    
    file_size_mb = audio_path.stat().st_size / (1024 * 1024)
    print(f"📁 파일: {audio_file} ({file_size_mb:.2f} MB)")
    print(f"👤 사용자: {user_id}")
    print(f"🕐 시작: {datetime.now().strftime('%H:%M:%S')}")
    
    try:
        # 파이프라인 초기화
        pipeline = SeniorMentalHealthPipeline()
        
        # 시작 시간 기록
        start_time = time.time()
        
        # 전체 파이프라인 실행
        print(f"\n📊 분석 단계:")
        print(f"  1️⃣ Phase 1: STT + 화자분리 (Google Cloud Speech)")
        print(f"  2️⃣ Phase 2: 시니어 음성 구간 추출")
        print(f"  3️⃣ Phase 3: 음성 특징 추출 (Librosa - 시니어 음성만)")
        print(f"  4️⃣ Phase 4: 텍스트 분석 (GPT-4o - 시니어 텍스트만)")
        print(f"  5️⃣ Phase 5: 딥러닝 분석 (SincNet - 시니어 음성만)")
        print(f"  6️⃣ Phase 6: 5대 지표 통합 계산")
        print(f"  7️⃣ Phase 7: 시계열 분석")
        print(f"  8️⃣ Phase 8: AI 종합 해석")
        print(f"\n⏳ 분석 진행 중... (예상 소요 시간: 1-3분)")
        
        # 비동기 파이프라인 실행
        result = await pipeline.analyze(
            audio_path=str(audio_path),
            user_id=user_id,
            user_info={
                'age': 75,
                'gender': 'F',
                'medical_history': 'unknown',
                'test_mode': True
            }
        )
        
        # 처리 시간
        elapsed = time.time() - start_time
        
        # 결과 출력
        if result['status'] == 'success':
            print(f"\n✅ 분석 완료! (소요 시간: {elapsed:.2f}초)")
            
            # 0. 시니어 음성 추출 상태 확인
            if 'senior_audio_extraction' in result:
                extraction = result['senior_audio_extraction']
                print(f"\n🎯 시니어 음성 추출 상태:")
                print(f"  • 상태: {extraction.get('status', 'unknown')}")
                print(f"  • 메시지: {extraction.get('message', 'N/A')}")
                if extraction.get('status') == 'success':
                    print(f"  • 추출된 구간: {extraction.get('segments_extracted', 0)}개")
                    print(f"  • 시니어 음성 길이: {extraction.get('total_duration', 0):.2f}초")
                    print(f"  • 추출 비율: {extraction.get('extraction_ratio', 0):.1%}")
                elif extraction.get('status') == 'fallback':
                    print(f"  • 실패 원인: {extraction.get('reason', 'unknown')}")
                    print(f"  • 원본 파일 사용: {extraction.get('using_original', False)}")
            
            # 1. 음성 분석 결과
            if 'voice_analysis' in result:
                voice = result['voice_analysis']
                print(f"\n🎤 Phase 3 - 음성 특징 (Librosa - 시니어 음성):")
                if 'features' in voice:
                    features = voice['features']
                    print(f"  • 피치 평균: {features.get('pitch_mean', 0):.2f} Hz")
                    print(f"  • 피치 변동성: {features.get('pitch_std', 0):.2f}")
                    print(f"  • 에너지: {features.get('energy_mean', 0):.4f}")
                    print(f"  • 말하기 속도: {features.get('speaking_rate', 0):.2f}")
                    print(f"  • 음성 명료도: {features.get('voice_clarity', 0):.3f}")
            
            # 2. 텍스트 분석 결과
            if 'text_analysis' in result:
                text = result['text_analysis']
                print(f"\n📝 Phase 4 - 텍스트 분석 (GPT-4o - 시니어 텍스트):")
                if result.get('transcription'):
                    trans_preview = result['transcription'][:100] + "..." if len(result.get('transcription', '')) > 100 else result.get('transcription', '')
                    print(f"  • 시니어 텍스트: {trans_preview}")
                if text.get('status') == 'success' and 'analysis' in text:
                    analysis = text['analysis']
                    if 'indicators' in analysis:
                        print(f"  • GPT-4o 지표 (DRI): {analysis['indicators'].get('DRI', 0):.3f}")
                        print(f"  • GPT-4o 지표 (CFL): {analysis['indicators'].get('CFL', 0):.3f}")
            
            # 3. SincNet 분석 결과
            if 'sincnet_analysis' in result:
                sincnet = result['sincnet_analysis']
                print(f"\n🧠 Phase 5 - 딥러닝 분석 (SincNet - 시니어 음성):")
                print(f"  • 우울증 확률: {sincnet.get('depression_probability', 0):.2%}")
                print(f"  • 불면증 확률: {sincnet.get('insomnia_probability', 0):.2%}")
                print(f"  • 신뢰도: {sincnet.get('confidence', 0):.2f}")
                print(f"  • 상태: {sincnet.get('status', 'unknown')}")
            
            # 4. 5대 지표
            if 'indicators' in result:
                indicators = result['indicators']
                print(f"\n📊 Phase 6 - 5대 정신건강 지표 (통합):")
                indicator_names = {
                    'DRI': '우울위험도',
                    'SDI': '수면장애',
                    'CFL': '인지기능',
                    'ES': '정서안정성',
                    'OV': '전반활력도'
                }
                for key, value in indicators.items():
                    if key in indicator_names:
                        level = "양호" if value > 0.7 else "주의" if value > 0.4 else "위험"
                        print(f"  • {indicator_names[key]}: {value:.3f} ({level})")
            
            # 5. 위험도 평가
            if 'risk_assessment' in result:
                risk = result['risk_assessment']
                print(f"\n⚠️ 위험도 평가:")
                print(f"  • 전체 위험도: {risk.get('overall_risk', 'unknown')}")
                if 'high_risk_indicators' in risk:
                    print(f"  • 주의 필요 지표: {', '.join(risk['high_risk_indicators'])}")
            
            # 6. 시계열 분석
            if 'trend_analysis' in result:
                trend = result['trend_analysis']
                print(f"\n📈 Phase 7 - 시계열 분석:")
                print(f"  • 분석 기간: {trend.get('time_span_days', 0)}일")
                print(f"  • 데이터 포인트: {trend.get('data_points', 0)}개")
                if 'trends' in trend:
                    for indicator, trend_info in trend['trends'].items():
                        if isinstance(trend_info, dict):
                            mk_trend = trend_info.get('mann_kendall', {}).get('trend', 'unknown')
                            print(f"  • {indicator}: {mk_trend}")
            
            # 7. AI 종합 해석
            if 'comprehensive_interpretation' in result:
                interp = result['comprehensive_interpretation']
                print(f"\n🤖 Phase 8 - AI 종합 해석:")
                print(f"  • 전반적 상태: {interp.get('overall_status', 'N/A')}")
                if 'main_findings' in interp:
                    print(f"  • 주요 발견사항:")
                    for finding in interp['main_findings'][:3]:
                        print(f"    - {finding}")
                if 'recommendations' in interp:
                    print(f"  • 권고사항:")
                    for rec in interp['recommendations'][:3]:
                        print(f"    - {rec}")
            
            # 8. Firestore 저장 확인
            if result.get('saved_to_firestore'):
                print(f"\n💾 Firestore 저장: ✅ 성공")
            else:
                print(f"\n💾 Firestore 저장: ⚠️ 실패 또는 건너뜀")
            
            # 처리 정보
            print(f"\n⏱️ 처리 정보:")
            print(f"  • 전체 소요 시간: {elapsed:.2f}초")
            print(f"  • 처리 시각: {datetime.now().strftime('%H:%M:%S')}")
            
            return result
            
        else:
            print(f"\n❌ 분석 실패!")
            print(f"  • 오류: {result.get('error', 'Unknown error')}")
            if 'details' in result:
                print(f"  • 상세: {result['details']}")
            return None
            
    except Exception as e:
        print(f"\n❌ 예외 발생: {e}")
        logger.error(f"파이프라인 실행 오류: {e}")
        import traceback
        traceback.print_exc()
        return None

async def main():
    """메인 테스트 함수"""
    
    print("🔬 Senior MHealth 전체 파이프라인 테스트")
    print(f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🔗 에뮬레이터: {os.getenv('FIRESTORE_EMULATOR_HOST')}")
    print(f"📦 프로젝트: {os.getenv('GCP_PROJECT_ID')}")
    
    # 테스트 설정
    test_user = f"pipeline_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    test_files = ['day1.wav', 'day2.wav', 'day3.wav']
    
    print(f"\n📋 테스트 계획:")
    print(f"  • 사용자 ID: {test_user}")
    print(f"  • 테스트 파일: {', '.join(test_files)}")
    print(f"  • 분석 내용: SincNet + Librosa + GPT-4o + 시계열 + AI종합")
    
    # 각 파일 순차 분석 (시계열 분석을 위해)
    results = []
    for i, audio_file in enumerate(test_files, 1):
        result = await run_full_pipeline(audio_file, test_user, i)
        if result:
            results.append(result)
            
            # 결과를 JSON으로 저장
            output_file = project_root / 'ai' / 'analysis' / 'test_data' / f'pipeline_result_{i}.json'
            with open(output_file, 'w', encoding='utf-8') as f:
                # 일부 필드만 저장 (너무 크지 않게)
                save_data = {
                    'file': audio_file,
                    'timestamp': result.get('timestamp'),
                    'status': result.get('status'),
                    'indicators': result.get('indicators'),
                    'risk_assessment': result.get('risk_assessment'),
                    'processing_time': result.get('processing_time'),
                    'senior_audio_extraction': result.get('senior_audio_extraction'),
                    'sincnet_enabled': result.get('sincnet_analysis', {}).get('status') == 'success'
                }
                json.dump(save_data, f, indent=2, ensure_ascii=False)
            print(f"💾 결과 저장: {output_file.name}")
        
        # 다음 분석 전 대기 (시계열 분석을 위해)
        if i < len(test_files):
            print(f"\n⏳ 다음 분석 대기 중... (3초)")
            await asyncio.sleep(3)
    
    # 최종 결과
    print(f"\n{'='*70}")
    print(f"📊 전체 테스트 결과:")
    print(f"  • 성공: {len(results)}/{len(test_files)}")
    
    if len(results) == len(test_files):
        print(f"\n🎉 모든 파이프라인 테스트 성공!")
        print(f"✅ STT + 화자분리 완료")
        print(f"✅ 시니어 음성 추출 완료")
        print(f"✅ Librosa 음성 분석 완료 (시니어 음성)")
        print(f"✅ GPT-4o 텍스트 분석 완료 (시니어 텍스트)")
        print(f"✅ SincNet 분석 완료 (시니어 음성)")
        print(f"✅ 5대 지표 통합 계산 완료")
        print(f"✅ 시계열 분석 완료")
        print(f"✅ AI 종합 해석 완료")
        
        # 시니어 음성 추출 상태 요약
        success_extractions = sum(1 for r in results if r.get('senior_audio_extraction', {}).get('status') == 'success')
        print(f"\n🎯 시니어 음성 추출 성공률: {success_extractions}/{len(results)}")
        
        print(f"\n💾 Firestore 에뮬레이터에서 확인: http://127.0.0.1:4001/firestore")
        return True
    else:
        print(f"\n⚠️ 일부 테스트 실패")
        return False

if __name__ == "__main__":
    # 비동기 실행
    success = asyncio.run(main())
    sys.exit(0 if success else 1)