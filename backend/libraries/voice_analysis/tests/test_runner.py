# 제7강: AI 모델 이해와 로컬 테스트 - 테스트 러너
"""
종합 테스트 실행 프레임워크
단위 테스트, 통합 테스트, 성능 테스트 실행 및 리포트 생성
"""

import os
import sys
import time
import traceback
import unittest
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, Callable, Tuple
from dataclasses import dataclass, asdict
from collections import defaultdict
import json
import torch
import torch.nn as nn

from ai.monitoring.logger import get_logger, PerformanceLogger
from ai.tests.test_utils import (
    TestDataGenerator, TestValidator, generate_test_audio, 
    create_mock_model, cleanup_test_files
)


logger = get_logger(__name__)


@dataclass 
class TestResult:
    """단일 테스트 결과"""
    test_name: str
    test_type: str  # unit, integration, performance
    status: str     # passed, failed, error, skipped
    execution_time: float
    message: Optional[str] = None
    error_details: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()


@dataclass
class TestSuiteResult:
    """테스트 스위트 결과"""
    suite_name: str
    total_tests: int
    passed_tests: int
    failed_tests: int
    error_tests: int
    skipped_tests: int
    total_execution_time: float
    test_results: List[TestResult]
    summary_metrics: Dict[str, Any]
    timestamp: str = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now().isoformat()
    
    @property
    def success_rate(self) -> float:
        """성공률 계산"""
        if self.total_tests == 0:
            return 0.0
        return self.passed_tests / self.total_tests
    
    @property
    def status(self) -> str:
        """전체 상태 판정"""
        if self.failed_tests > 0 or self.error_tests > 0:
            return 'failed'
        elif self.skipped_tests > 0:
            return 'partial'
        else:
            return 'passed'


class TestCase:
    """기본 테스트 케이스 클래스"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.setup_completed = False
        self.cleanup_files = []
        
    def setUp(self):
        """테스트 전 설정"""
        self.setup_completed = True
        logger.debug(f"테스트 설정 완료: {self.name}")
    
    def tearDown(self):
        """테스트 후 정리"""
        if self.cleanup_files:
            cleanup_test_files(self.cleanup_files)
            self.cleanup_files.clear()
        logger.debug(f"테스트 정리 완료: {self.name}")
    
    def run(self) -> TestResult:
        """테스트 실행 (하위 클래스에서 오버라이드)"""
        raise NotImplementedError("하위 클래스에서 구현해야 합니다")
    
    def assert_true(self, condition: bool, message: str = ""):
        """참 검증"""
        if not condition:
            raise AssertionError(f"조건이 거짓입니다: {message}")
    
    def assert_false(self, condition: bool, message: str = ""):
        """거짓 검증"""
        if condition:
            raise AssertionError(f"조건이 참입니다: {message}")
    
    def assert_equal(self, actual, expected, message: str = ""):
        """동등성 검증"""
        if actual != expected:
            raise AssertionError(f"값이 다릅니다: {actual} != {expected}. {message}")
    
    def assert_not_equal(self, actual, expected, message: str = ""):
        """비동등성 검증"""
        if actual == expected:
            raise AssertionError(f"값이 같습니다: {actual} == {expected}. {message}")
    
    def assert_greater(self, actual, expected, message: str = ""):
        """크기 비교 검증"""
        if actual <= expected:
            raise AssertionError(f"값이 더 크지 않습니다: {actual} <= {expected}. {message}")
    
    def assert_in_range(self, value, min_val, max_val, message: str = ""):
        """범위 검증"""
        if not (min_val <= value <= max_val):
            raise AssertionError(f"값이 범위를 벗어났습니다: {value} not in [{min_val}, {max_val}]. {message}")


# 구체적인 테스트 케이스들
class AudioGenerationTest(TestCase):
    """오디오 생성 테스트"""
    
    def __init__(self):
        super().__init__("audio_generation_test", "테스트 오디오 생성 기능 검증")
        self.data_generator = TestDataGenerator()
    
    def run(self) -> TestResult:
        start_time = time.time()
        
        try:
            # 다양한 타입의 오디오 생성 테스트
            signal_types = ['sine', 'noise', 'chirp', 'voice_like']
            
            for signal_type in signal_types:
                audio, file_path = generate_test_audio(
                    duration=2.0,
                    sample_rate=16000,
                    signal_type=signal_type,
                    save_path=f"/tmp/test_{signal_type}.wav"
                )
                
                self.cleanup_files.append(file_path)
                
                # 검증
                self.assert_true(TestValidator.validate_audio_tensor(audio), 
                                f"오디오 텐서 유효성 검사 실패: {signal_type}")
                self.assert_equal(audio.shape[0], 1, f"채널 수 검증 실패: {signal_type}")
                self.assert_equal(audio.shape[1], 32000, f"샘플 수 검증 실패: {signal_type}")
                self.assert_true(os.path.exists(file_path), f"파일 생성 실패: {signal_type}")
            
            execution_time = time.time() - start_time
            
            return TestResult(
                test_name=self.name,
                test_type="unit",
                status="passed",
                execution_time=execution_time,
                message="모든 오디오 생성 테스트 통과",
                metrics={
                    'tested_signal_types': len(signal_types),
                    'audio_files_created': len(self.cleanup_files)
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"오디오 생성 테스트 실패: {str(e)}")
            
            return TestResult(
                test_name=self.name,
                test_type="unit",
                status="error",
                execution_time=execution_time,
                message=f"오디오 생성 테스트 오류: {str(e)}",
                error_details=traceback.format_exc()
            )


class ModelCreationTest(TestCase):
    """모델 생성 테스트"""
    
    def __init__(self):
        super().__init__("model_creation_test", "Mock 모델 생성 및 기본 동작 검증")
    
    def run(self) -> TestResult:
        start_time = time.time()
        
        try:
            model_types = ['sincnet', 'cnn', 'rnn']
            test_metrics = {}
            
            for model_type in model_types:
                # 모델 생성
                model = create_mock_model(
                    model_type=model_type,
                    input_dim=16000,
                    num_classes=4
                )
                
                # 기본 검증
                self.assert_true(isinstance(model, nn.Module), f"모델 타입 검증 실패: {model_type}")
                
                # 순전파 테스트
                if model_type == 'rnn':
                    test_input = torch.randn(2, 16000, 1)  # RNN은 (batch, seq, features)
                else:
                    test_input = torch.randn(2, 1, 16000)  # CNN은 (batch, channels, length)
                
                with torch.no_grad():
                    output = model(test_input)
                
                # 출력 검증
                self.assert_true(TestValidator.validate_model_output(output, 4), 
                                f"모델 출력 검증 실패: {model_type}")
                
                # 파라미터 수 계산
                param_count = sum(p.numel() for p in model.parameters())
                test_metrics[f'{model_type}_params'] = param_count
                
                logger.debug(f"{model_type} 모델 생성 및 테스트 완료 (파라미터: {param_count:,}개)")
            
            execution_time = time.time() - start_time
            
            return TestResult(
                test_name=self.name,
                test_type="unit",
                status="passed",
                execution_time=execution_time,
                message="모든 모델 생성 테스트 통과",
                metrics=test_metrics
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"모델 생성 테스트 실패: {str(e)}")
            
            return TestResult(
                test_name=self.name,
                test_type="error",
                status="error",
                execution_time=execution_time,
                message=f"모델 생성 테스트 오류: {str(e)}",
                error_details=traceback.format_exc()
            )


class FeatureExtractionTest(TestCase):
    """특징 추출 테스트"""
    
    def __init__(self):
        super().__init__("feature_extraction_test", "MFCC 및 Mel-spectrogram 특징 추출 검증")
        self.data_generator = TestDataGenerator()
    
    def run(self) -> TestResult:
        start_time = time.time()
        
        try:
            from ai.features import MFCCExtractor, MelSpectrogramExtractor
            
            # 테스트 데이터 생성
            test_data = self.data_generator.generate_feature_test_data(
                num_samples=5,
                duration=3.0,
                sample_rate=16000
            )
            
            audio_batch = test_data['audio_batch']
            
            # MFCC 추출기 테스트
            mfcc_extractor = MFCCExtractor(
                sample_rate=16000,
                n_mfcc=13,
                n_fft=2048,
                hop_length=512
            )
            
            mfcc_features = mfcc_extractor.extract(audio_batch)
            self.assert_true(TestValidator.validate_feature_extraction(mfcc_features, 'mfcc'),
                            "MFCC 특징 검증 실패")
            
            # Mel-spectrogram 추출기 테스트
            mel_extractor = MelSpectrogramExtractor(
                sample_rate=16000,
                n_mels=128,
                n_fft=2048,
                hop_length=512
            )
            
            mel_features = mel_extractor.extract(audio_batch)
            self.assert_true(TestValidator.validate_feature_extraction(mel_features, 'mel_spectrogram'),
                            "Mel-spectrogram 특징 검증 실패")
            
            # 특징 차원 검증
            expected_time_steps = (48000 - 2048) // 512 + 1  # 3초 * 16kHz 오디오
            self.assert_equal(mfcc_features.shape, (5, 39, expected_time_steps), "MFCC 차원 검증 실패")  # 39 = 13*3 (델타 포함)
            self.assert_equal(mel_features.shape, (5, 128, expected_time_steps), "Mel-spectrogram 차원 검증 실패")
            
            execution_time = time.time() - start_time
            
            return TestResult(
                test_name=self.name,
                test_type="unit",
                status="passed",
                execution_time=execution_time,
                message="모든 특징 추출 테스트 통과",
                metrics={
                    'mfcc_shape': list(mfcc_features.shape),
                    'mel_shape': list(mel_features.shape),
                    'audio_samples_tested': audio_batch.shape[0]
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"특징 추출 테스트 실패: {str(e)}")
            
            return TestResult(
                test_name=self.name,
                test_type="unit",
                status="error",
                execution_time=execution_time,
                message=f"특징 추출 테스트 오류: {str(e)}",
                error_details=traceback.format_exc()
            )


class InferenceEngineTest(TestCase):
    """추론 엔진 테스트"""
    
    def __init__(self):
        super().__init__("inference_engine_test", "추론 엔진 기본 동작 검증")
        self.data_generator = TestDataGenerator()
    
    def run(self) -> TestResult:
        start_time = time.time()
        
        try:
            from ai.inference import InferenceEngine
            
            # 추론 엔진 초기화
            inference_engine = InferenceEngine()
            
            # 테스트 오디오 생성
            audio, audio_file = generate_test_audio(
                duration=3.0,
                sample_rate=16000,
                signal_type='voice_like'
            )
            self.cleanup_files.append(audio_file)
            
            # 추론 수행 테스트
            result = inference_engine.predict(
                audio_path=audio_file,
                feature_type='raw',
                use_cache=False
            )
            
            # 결과 검증
            self.assert_true(isinstance(result, dict), "추론 결과가 딕셔너리가 아닙니다")
            self.assert_true('prediction' in result, "예측 결과가 없습니다")
            self.assert_true('confidence' in result, "신뢰도가 없습니다")
            self.assert_true('processing_time' in result, "처리 시간 정보가 없습니다")
            
            # 신뢰도 범위 검증
            confidence = result['confidence']
            self.assert_in_range(confidence, 0.0, 1.0, "신뢰도가 범위를 벗어남")
            
            # 처리 시간 검증
            processing_time = result['processing_time']
            self.assert_true(TestValidator.validate_processing_time(processing_time, 10.0),
                            "처리 시간 검증 실패")
            
            execution_time = time.time() - start_time
            
            return TestResult(
                test_name=self.name,
                test_type="integration",
                status="passed",
                execution_time=execution_time,
                message="추론 엔진 테스트 통과",
                metrics={
                    'inference_time': processing_time,
                    'confidence': confidence,
                    'prediction': result.get('prediction')
                }
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"추론 엔진 테스트 실패: {str(e)}")
            
            return TestResult(
                test_name=self.name,
                test_type="integration",
                status="error",
                execution_time=execution_time,
                message=f"추론 엔진 테스트 오류: {str(e)}",
                error_details=traceback.format_exc()
            )


class PerformanceTest(TestCase):
    """성능 테스트"""
    
    def __init__(self):
        super().__init__("performance_test", "시스템 성능 및 처리 속도 검증")
        self.data_generator = TestDataGenerator()
    
    def run(self) -> TestResult:
        start_time = time.time()
        
        try:
            from ai.inference import InferenceEngine
            from ai.features import MFCCExtractor
            
            # 성능 테스트 설정
            num_iterations = 10
            batch_sizes = [1, 4, 8]
            audio_durations = [1.0, 3.0, 5.0]
            
            performance_metrics = {}
            
            # 1. 특징 추출 성능 테스트
            mfcc_extractor = MFCCExtractor()
            
            for duration in audio_durations:
                for batch_size in batch_sizes:
                    test_audio, _ = self.data_generator.generate_batch_audio(
                        batch_size=batch_size,
                        duration=duration
                    )
                    
                    # 성능 측정
                    times = []
                    for _ in range(num_iterations):
                        iter_start = time.time()
                        _ = mfcc_extractor.extract(test_audio)
                        iter_time = time.time() - iter_start
                        times.append(iter_time)
                    
                    avg_time = sum(times) / len(times)
                    throughput = batch_size / avg_time  # 초당 처리 개수
                    
                    key = f'mfcc_batch{batch_size}_dur{duration}s'
                    performance_metrics[key] = {
                        'avg_time': avg_time,
                        'throughput': throughput,
                        'min_time': min(times),
                        'max_time': max(times)
                    }
                    
                    # 성능 기준 검증
                    max_allowed_time = duration * 0.5  # 실시간의 50% 이내
                    self.assert_true(avg_time < max_allowed_time, 
                                   f"특징 추출이 너무 느림: {avg_time:.3f}s > {max_allowed_time:.3f}s")
            
            # 2. 메모리 사용량 테스트
            import psutil
            import gc
            
            process = psutil.Process()
            initial_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            # 큰 배치 처리
            large_batch, _ = self.data_generator.generate_batch_audio(batch_size=32, duration=5.0)
            _ = mfcc_extractor.extract(large_batch)
            
            peak_memory = process.memory_info().rss / 1024 / 1024  # MB
            memory_increase = peak_memory - initial_memory
            
            # 메모리 정리
            del large_batch
            gc.collect()
            
            final_memory = process.memory_info().rss / 1024 / 1024  # MB
            
            performance_metrics['memory_usage'] = {
                'initial_mb': initial_memory,
                'peak_mb': peak_memory,
                'final_mb': final_memory,
                'increase_mb': memory_increase
            }
            
            # 메모리 누수 검사
            memory_leak = final_memory - initial_memory
            self.assert_true(memory_leak < 50, f"메모리 누수 가능성: {memory_leak:.1f}MB")
            
            execution_time = time.time() - start_time
            
            return TestResult(
                test_name=self.name,
                test_type="performance",
                status="passed",
                execution_time=execution_time,
                message="성능 테스트 통과",
                metrics=performance_metrics
            )
            
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"성능 테스트 실패: {str(e)}")
            
            return TestResult(
                test_name=self.name,
                test_type="performance", 
                status="error",
                execution_time=execution_time,
                message=f"성능 테스트 오류: {str(e)}",
                error_details=traceback.format_exc()
            )


class TestSuite:
    """테스트 스위트"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.test_cases: List[TestCase] = []
        self.setup_hooks: List[Callable] = []
        self.teardown_hooks: List[Callable] = []
    
    def add_test(self, test_case: TestCase):
        """테스트 케이스 추가"""
        self.test_cases.append(test_case)
        logger.debug(f"테스트 추가: {test_case.name}")
    
    def add_setup_hook(self, hook: Callable):
        """설정 훅 추가"""
        self.setup_hooks.append(hook)
    
    def add_teardown_hook(self, hook: Callable):
        """정리 훅 추가"""
        self.teardown_hooks.append(hook)
    
    def run(self, parallel: bool = False) -> TestSuiteResult:
        """테스트 스위트 실행"""
        logger.info(f"테스트 스위트 실행 시작: {self.name}")
        start_time = time.time()
        
        # 설정 훅 실행
        for hook in self.setup_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"설정 훅 실행 실패: {str(e)}")
        
        test_results = []
        passed_tests = 0
        failed_tests = 0
        error_tests = 0
        skipped_tests = 0
        
        # 테스트 실행
        for test_case in self.test_cases:
            logger.info(f"테스트 실행: {test_case.name}")
            
            try:
                # 테스트 설정
                test_case.setUp()
                
                # 테스트 실행
                result = test_case.run()
                test_results.append(result)
                
                # 결과 집계
                if result.status == 'passed':
                    passed_tests += 1
                elif result.status == 'failed':
                    failed_tests += 1
                elif result.status == 'error':
                    error_tests += 1
                elif result.status == 'skipped':
                    skipped_tests += 1
                
                logger.info(f"테스트 완료: {test_case.name} ({result.status})")
                
            except Exception as e:
                # 테스트 케이스 자체에서 예외 발생
                error_result = TestResult(
                    test_name=test_case.name,
                    test_type="unknown",
                    status="error",
                    execution_time=0.0,
                    message=f"테스트 케이스 실행 중 예외: {str(e)}",
                    error_details=traceback.format_exc()
                )
                test_results.append(error_result)
                error_tests += 1
                
                logger.error(f"테스트 케이스 실행 실패: {test_case.name} - {str(e)}")
                
            finally:
                # 테스트 정리
                try:
                    test_case.tearDown()
                except Exception as e:
                    logger.error(f"테스트 정리 실패: {test_case.name} - {str(e)}")
        
        # 정리 훅 실행
        for hook in self.teardown_hooks:
            try:
                hook()
            except Exception as e:
                logger.error(f"정리 훅 실행 실패: {str(e)}")
        
        total_execution_time = time.time() - start_time
        
        # 요약 메트릭 계산
        summary_metrics = {
            'execution_times': [r.execution_time for r in test_results],
            'avg_execution_time': sum(r.execution_time for r in test_results) / len(test_results) if test_results else 0,
            'max_execution_time': max(r.execution_time for r in test_results) if test_results else 0,
            'test_types': list(set(r.test_type for r in test_results))
        }
        
        result = TestSuiteResult(
            suite_name=self.name,
            total_tests=len(self.test_cases),
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            error_tests=error_tests,
            skipped_tests=skipped_tests,
            total_execution_time=total_execution_time,
            test_results=test_results,
            summary_metrics=summary_metrics
        )
        
        logger.info(f"테스트 스위트 완료: {self.name} ({result.status}, {result.success_rate:.1%})")
        
        return result


class TestRunner:
    """테스트 실행기"""
    
    def __init__(self, output_dir: str = "test_reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.test_suites: List[TestSuite] = []
        
    def add_suite(self, test_suite: TestSuite):
        """테스트 스위트 추가"""
        self.test_suites.append(test_suite)
        logger.info(f"테스트 스위트 추가: {test_suite.name}")
    
    def create_default_suite(self) -> TestSuite:
        """기본 테스트 스위트 생성"""
        suite = TestSuite("default_ai_tests", "AI 시스템 기본 테스트")
        
        # 기본 테스트들 추가
        suite.add_test(AudioGenerationTest())
        suite.add_test(ModelCreationTest())
        suite.add_test(FeatureExtractionTest())
        suite.add_test(InferenceEngineTest())
        suite.add_test(PerformanceTest())
        
        return suite
    
    def run_all(self, parallel: bool = False) -> Dict[str, TestSuiteResult]:
        """모든 테스트 스위트 실행"""
        logger.info(f"전체 테스트 실행 시작 ({len(self.test_suites)}개 스위트)")
        
        results = {}
        
        for suite in self.test_suites:
            suite_result = suite.run(parallel=parallel)
            results[suite.name] = suite_result
            
            # 개별 결과 저장
            self._save_suite_result(suite_result)
        
        # 전체 결과 보고서 생성
        self._generate_overall_report(results)
        
        return results
    
    def run_suite(self, suite_name: str) -> Optional[TestSuiteResult]:
        """특정 테스트 스위트 실행"""
        for suite in self.test_suites:
            if suite.name == suite_name:
                result = suite.run()
                self._save_suite_result(result)
                return result
        
        logger.error(f"테스트 스위트를 찾을 수 없습니다: {suite_name}")
        return None
    
    def _save_suite_result(self, result: TestSuiteResult):
        """테스트 스위트 결과 저장"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"{result.suite_name}_{timestamp}.json"
        filepath = self.output_dir / filename
        
        # JSON 직렬화 가능한 형태로 변환
        result_dict = asdict(result)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
        
        logger.info(f"테스트 결과 저장: {filepath}")
    
    def _generate_overall_report(self, results: Dict[str, TestSuiteResult]):
        """전체 결과 보고서 생성"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_file = self.output_dir / f"overall_report_{timestamp}.json"
        
        # 전체 통계 계산
        total_tests = sum(r.total_tests for r in results.values())
        total_passed = sum(r.passed_tests for r in results.values())
        total_failed = sum(r.failed_tests for r in results.values())
        total_errors = sum(r.error_tests for r in results.values())
        total_skipped = sum(r.skipped_tests for r in results.values())
        total_execution_time = sum(r.total_execution_time for r in results.values())
        
        overall_success_rate = total_passed / total_tests if total_tests > 0 else 0
        
        # 보고서 데이터 구성
        report_data = {
            'report_metadata': {
                'generated_at': timestamp,
                'total_suites': len(results),
                'output_directory': str(self.output_dir)
            },
            'overall_statistics': {
                'total_tests': total_tests,
                'passed_tests': total_passed,
                'failed_tests': total_failed,
                'error_tests': total_errors,
                'skipped_tests': total_skipped,
                'success_rate': round(overall_success_rate, 3),
                'total_execution_time': round(total_execution_time, 3),
                'avg_execution_time_per_test': round(total_execution_time / total_tests, 3) if total_tests > 0 else 0
            },
            'suite_summaries': {},
            'detailed_results': {}
        }
        
        # 스위트별 요약 및 상세 결과
        for suite_name, suite_result in results.items():
            # 요약 정보
            report_data['suite_summaries'][suite_name] = {
                'status': suite_result.status,
                'success_rate': round(suite_result.success_rate, 3),
                'total_tests': suite_result.total_tests,
                'execution_time': round(suite_result.total_execution_time, 3)
            }
            
            # 상세 결과
            report_data['detailed_results'][suite_name] = asdict(suite_result)
        
        # 보고서 저장
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        # 요약 로그 출력
        logger.info("=" * 60)
        logger.info("테스트 실행 완료 - 전체 요약")
        logger.info("=" * 60)
        logger.info(f"총 스위트 수: {len(results)}")
        logger.info(f"총 테스트 수: {total_tests}")
        logger.info(f"성공: {total_passed}, 실패: {total_failed}, 오류: {total_errors}, 건너뜀: {total_skipped}")
        logger.info(f"성공률: {overall_success_rate:.1%}")
        logger.info(f"총 실행 시간: {total_execution_time:.3f}초")
        logger.info(f"보고서 저장: {report_file}")
        logger.info("=" * 60)
    
    def list_available_tests(self) -> Dict[str, List[str]]:
        """사용 가능한 테스트 목록 반환"""
        test_list = {}
        
        for suite in self.test_suites:
            test_list[suite.name] = [test.name for test in suite.test_cases]
        
        return test_list


# 메인 실행 함수
def run_default_tests():
    """기본 테스트 실행"""
    runner = TestRunner()
    
    # 기본 테스트 스위트 생성 및 추가
    default_suite = runner.create_default_suite()
    runner.add_suite(default_suite)
    
    # 실행
    results = runner.run_all()
    
    return results


if __name__ == "__main__":
    # 직접 실행 시 기본 테스트 수행
    logger.info("AI 시스템 테스트 시작")
    results = run_default_tests()
    logger.info("AI 시스템 테스트 완료")