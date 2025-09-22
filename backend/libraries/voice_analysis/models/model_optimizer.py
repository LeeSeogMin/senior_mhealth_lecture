# 제7강: AI 모델 이해와 로컬 테스트 - 모델 최적화 유틸리티
"""
모델 최적화 및 경량화 도구
양자화, 프루닝, TorchScript 컴파일 등의 최적화 기법 제공
"""

import os
import json
import time
import torch
import torch.nn as nn
import torch.quantization as quantization
from torch.jit import ScriptModule
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, Union, List
from dataclasses import dataclass
import logging
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class OptimizationConfig:
    """모델 최적화 설정"""
    quantization_enabled: bool = True
    pruning_enabled: bool = True
    torchscript_enabled: bool = True
    quantization_qconfig: str = 'fbgemm'  # fbgemm, qnnpack
    pruning_amount: float = 0.3  # 30% 프루닝
    calibration_samples: int = 100
    optimization_level: str = 'balanced'  # aggressive, balanced, conservative


class ModelOptimizer:
    """종합적인 모델 최적화 도구"""
    
    def __init__(self, config: OptimizationConfig = None):
        self.config = config or OptimizationConfig()
        self.optimization_history = []
        
    def optimize_model(
        self, 
        model: nn.Module, 
        sample_input: torch.Tensor,
        calibration_data: Optional[List[torch.Tensor]] = None,
        output_dir: Union[str, Path] = "optimized_models"
    ) -> Dict[str, Any]:
        """
        모델 종합 최적화 수행
        
        Args:
            model: 최적화할 모델
            sample_input: 샘플 입력 데이터
            calibration_data: 캘리브레이션 데이터
            output_dir: 출력 디렉토리
            
        Returns:
            최적화 결과 정보
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        optimization_results = {
            'original_model': self._analyze_model(model, sample_input),
            'optimized_models': {},
            'optimization_log': []
        }
        
        try:
            # 1. 원본 모델 저장
            original_path = output_dir / "original_model.pth"
            torch.save({
                'model_state_dict': model.state_dict(),
                'model_class': model.__class__.__name__,
                'optimization_config': self.config.__dict__
            }, original_path)
            
            logger.info("모델 최적화 시작")
            
            # 2. 양자화
            if self.config.quantization_enabled:
                quantized_model = self._apply_quantization(
                    model, sample_input, calibration_data
                )
                quantized_results = self._analyze_model(quantized_model, sample_input)
                optimization_results['optimized_models']['quantized'] = quantized_results
                
                # 양자화 모델 저장
                quantized_path = output_dir / "quantized_model.pth"
                torch.save(quantized_model.state_dict(), quantized_path)
                
                logger.info(f"양자화 완료 - 모델 크기 감소: {quantized_results['size_reduction']:.2%}")
            
            # 3. 프루닝
            if self.config.pruning_enabled:
                pruned_model = self._apply_pruning(model, sample_input)
                pruned_results = self._analyze_model(pruned_model, sample_input)
                optimization_results['optimized_models']['pruned'] = pruned_results
                
                # 프루닝 모델 저장
                pruned_path = output_dir / "pruned_model.pth"
                torch.save(pruned_model.state_dict(), pruned_path)
                
                logger.info(f"프루닝 완료 - 파라미터 감소: {pruned_results['parameter_reduction']:.2%}")
            
            # 4. TorchScript 컴파일
            if self.config.torchscript_enabled:
                scripted_model = self._apply_torchscript(model, sample_input)
                scripted_results = self._analyze_scripted_model(scripted_model, sample_input)
                optimization_results['optimized_models']['torchscript'] = scripted_results
                
                # TorchScript 모델 저장
                scripted_path = output_dir / "scripted_model.pt"
                scripted_model.save(str(scripted_path))
                
                logger.info(f"TorchScript 컴파일 완료 - 추론 속도 향상: {scripted_results['speed_improvement']:.2%}")
            
            # 5. 복합 최적화 (양자화 + 프루닝)
            if self.config.quantization_enabled and self.config.pruning_enabled:
                combined_model = self._apply_combined_optimization(
                    model, sample_input, calibration_data
                )
                combined_results = self._analyze_model(combined_model, sample_input)
                optimization_results['optimized_models']['combined'] = combined_results
                
                # 복합 최적화 모델 저장
                combined_path = output_dir / "combined_optimized_model.pth"
                torch.save(combined_model.state_dict(), combined_path)
                
                logger.info(f"복합 최적화 완료 - 총 크기 감소: {combined_results['size_reduction']:.2%}")
            
            # 6. 최적화 결과 보고서 생성
            report_path = output_dir / "optimization_report.json"
            with open(report_path, 'w', encoding='utf-8') as f:
                json.dump(optimization_results, f, indent=2, ensure_ascii=False)
            
            # 7. 최적화 히스토리 업데이트
            self.optimization_history.append({
                'timestamp': time.time(),
                'model_name': model.__class__.__name__,
                'results': optimization_results,
                'output_dir': str(output_dir)
            })
            
            return optimization_results
            
        except Exception as e:
            logger.error(f"모델 최적화 실패: {str(e)}")
            raise
    
    def _apply_quantization(
        self, 
        model: nn.Module, 
        sample_input: torch.Tensor,
        calibration_data: Optional[List[torch.Tensor]] = None
    ) -> nn.Module:
        """동적 양자화 적용"""
        model_copy = self._copy_model(model)
        
        if self.config.quantization_qconfig == 'fbgemm':
            model_copy.qconfig = torch.quantization.get_default_qconfig('fbgemm')
        elif self.config.quantization_qconfig == 'qnnpack':
            model_copy.qconfig = torch.quantization.get_default_qconfig('qnnpack')
        
        # 모델 준비
        model_prepared = torch.quantization.prepare(model_copy, inplace=False)
        
        # 캘리브레이션
        model_prepared.eval()
        with torch.no_grad():
            if calibration_data:
                for data in calibration_data[:self.config.calibration_samples]:
                    model_prepared(data)
            else:
                # 샘플 입력으로 캘리브레이션
                model_prepared(sample_input)
        
        # 양자화 적용
        quantized_model = torch.quantization.convert(model_prepared, inplace=False)
        
        return quantized_model
    
    def _apply_pruning(self, model: nn.Module, sample_input: torch.Tensor) -> nn.Module:
        """구조적 프루닝 적용"""
        model_copy = self._copy_model(model)
        
        # 프루닝할 레이어 식별
        modules_to_prune = []
        for name, module in model_copy.named_modules():
            if isinstance(module, (nn.Linear, nn.Conv1d, nn.Conv2d)):
                modules_to_prune.append((module, 'weight'))
        
        # 전역 비구조적 프루닝 적용
        if modules_to_prune:
            import torch.nn.utils.prune as prune
            
            prune.global_unstructured(
                modules_to_prune,
                pruning_method=prune.L1Unstructured,
                amount=self.config.pruning_amount,
            )
            
            # 프루닝 마스크 영구적으로 적용
            for module, param in modules_to_prune:
                prune.remove(module, param)
        
        return model_copy
    
    def _apply_torchscript(self, model: nn.Module, sample_input: torch.Tensor) -> ScriptModule:
        """TorchScript 컴파일"""
        model.eval()
        try:
            # Trace 방식 시도
            scripted_model = torch.jit.trace(model, sample_input)
            # 최적화 적용
            scripted_model = torch.jit.optimize_for_inference(scripted_model)
        except Exception:
            # Script 방식으로 폴백
            scripted_model = torch.jit.script(model)
            scripted_model = torch.jit.optimize_for_inference(scripted_model)
        
        return scripted_model
    
    def _apply_combined_optimization(
        self, 
        model: nn.Module, 
        sample_input: torch.Tensor,
        calibration_data: Optional[List[torch.Tensor]] = None
    ) -> nn.Module:
        """프루닝 후 양자화 적용"""
        # 1. 프루닝 먼저 적용
        pruned_model = self._apply_pruning(model, sample_input)
        
        # 2. 프루닝된 모델에 양자화 적용
        combined_model = self._apply_quantization(pruned_model, sample_input, calibration_data)
        
        return combined_model
    
    def _analyze_model(self, model: nn.Module, sample_input: torch.Tensor) -> Dict[str, Any]:
        """모델 분석 및 벤치마킹"""
        model.eval()
        
        # 모델 크기 계산
        model_size = sum(p.numel() for p in model.parameters()) * 4 / (1024 * 1024)  # MB
        
        # 파라미터 수 계산
        total_params = sum(p.numel() for p in model.parameters())
        trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)
        
        # 추론 속도 벤치마크
        with torch.no_grad():
            # 워밍업
            for _ in range(10):
                _ = model(sample_input)
            
            # 실제 측정
            start_time = time.time()
            for _ in range(100):
                _ = model(sample_input)
            avg_inference_time = (time.time() - start_time) / 100 * 1000  # ms
        
        return {
            'model_size_mb': model_size,
            'total_parameters': total_params,
            'trainable_parameters': trainable_params,
            'avg_inference_time_ms': avg_inference_time,
            'size_reduction': 0.0,  # 원본 대비 감소율 (나중에 계산)
            'parameter_reduction': 0.0,
            'speed_improvement': 0.0
        }
    
    def _analyze_scripted_model(self, model: ScriptModule, sample_input: torch.Tensor) -> Dict[str, Any]:
        """TorchScript 모델 분석"""
        model.eval()
        
        # 추론 속도 벤치마크
        with torch.no_grad():
            # 워밍업
            for _ in range(10):
                _ = model(sample_input)
            
            # 실제 측정
            start_time = time.time()
            for _ in range(100):
                _ = model(sample_input)
            avg_inference_time = (time.time() - start_time) / 100 * 1000  # ms
        
        return {
            'model_type': 'torchscript',
            'avg_inference_time_ms': avg_inference_time,
            'speed_improvement': 0.0  # 나중에 계산
        }
    
    def _copy_model(self, model: nn.Module) -> nn.Module:
        """모델 깊은 복사"""
        import copy
        return copy.deepcopy(model)
    
    def compare_models(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """모델 성능 비교 분석"""
        original = results['original_model']
        optimized = results['optimized_models']
        
        comparison = {}
        
        for opt_type, opt_results in optimized.items():
            if opt_type == 'torchscript':
                comparison[opt_type] = {
                    'speed_improvement': (
                        (original['avg_inference_time_ms'] - opt_results['avg_inference_time_ms']) / 
                        original['avg_inference_time_ms']
                    )
                }
            else:
                comparison[opt_type] = {
                    'size_reduction': (
                        (original['model_size_mb'] - opt_results['model_size_mb']) / 
                        original['model_size_mb']
                    ),
                    'parameter_reduction': (
                        (original['total_parameters'] - opt_results['total_parameters']) / 
                        original['total_parameters']
                    ),
                    'speed_change': (
                        (original['avg_inference_time_ms'] - opt_results['avg_inference_time_ms']) / 
                        original['avg_inference_time_ms']
                    )
                }
        
        return comparison


class ModelPruner:
    """전문적인 모델 프루닝 도구"""
    
    def __init__(self, strategy: str = 'magnitude', sparsity: float = 0.3):
        """
        Args:
            strategy: 프루닝 전략 ('magnitude', 'random', 'structured')
            sparsity: 희소성 비율 (0.0 ~ 1.0)
        """
        self.strategy = strategy
        self.sparsity = sparsity
        self.pruning_methods = {
            'magnitude': self._magnitude_pruning,
            'random': self._random_pruning,
            'structured': self._structured_pruning
        }
    
    def prune_model(
        self, 
        model: nn.Module, 
        importance_scores: Optional[Dict[str, torch.Tensor]] = None
    ) -> Tuple[nn.Module, Dict[str, Any]]:
        """
        모델 프루닝 수행
        
        Args:
            model: 프루닝할 모델
            importance_scores: 레이어별 중요도 점수
            
        Returns:
            (프루닝된 모델, 프루닝 통계)
        """
        if self.strategy not in self.pruning_methods:
            raise ValueError(f"지원하지 않는 프루닝 전략: {self.strategy}")
        
        return self.pruning_methods[self.strategy](model, importance_scores)
    
    def _magnitude_pruning(
        self, 
        model: nn.Module, 
        importance_scores: Optional[Dict[str, torch.Tensor]]
    ) -> Tuple[nn.Module, Dict[str, Any]]:
        """가중치 크기 기반 프루닝"""
        import torch.nn.utils.prune as prune
        import copy
        
        model_copy = copy.deepcopy(model)
        pruning_stats = {
            'pruned_layers': [],
            'original_params': 0,
            'remaining_params': 0,
            'sparsity_achieved': 0.0
        }
        
        modules_to_prune = []
        for name, module in model_copy.named_modules():
            if isinstance(module, (nn.Linear, nn.Conv1d, nn.Conv2d)):
                modules_to_prune.append((module, 'weight'))
                pruning_stats['original_params'] += module.weight.numel()
                pruning_stats['pruned_layers'].append(name)
        
        if modules_to_prune:
            # L1 크기 기반 전역 프루닝
            prune.global_unstructured(
                modules_to_prune,
                pruning_method=prune.L1Unstructured,
                amount=self.sparsity,
            )
            
            # 프루닝 마스크 영구 적용
            for module, param in modules_to_prune:
                prune.remove(module, param)
                pruning_stats['remaining_params'] += (module.weight != 0).sum().item()
        
        pruning_stats['sparsity_achieved'] = 1.0 - (
            pruning_stats['remaining_params'] / pruning_stats['original_params']
        )
        
        return model_copy, pruning_stats
    
    def _random_pruning(
        self, 
        model: nn.Module, 
        importance_scores: Optional[Dict[str, torch.Tensor]]
    ) -> Tuple[nn.Module, Dict[str, Any]]:
        """랜덤 프루닝"""
        import torch.nn.utils.prune as prune
        import copy
        
        model_copy = copy.deepcopy(model)
        pruning_stats = {
            'pruned_layers': [],
            'original_params': 0,
            'remaining_params': 0,
            'sparsity_achieved': 0.0
        }
        
        modules_to_prune = []
        for name, module in model_copy.named_modules():
            if isinstance(module, (nn.Linear, nn.Conv1d, nn.Conv2d)):
                modules_to_prune.append((module, 'weight'))
                pruning_stats['original_params'] += module.weight.numel()
                pruning_stats['pruned_layers'].append(name)
        
        if modules_to_prune:
            prune.global_unstructured(
                modules_to_prune,
                pruning_method=prune.RandomUnstructured,
                amount=self.sparsity,
            )
            
            for module, param in modules_to_prune:
                prune.remove(module, param)
                pruning_stats['remaining_params'] += (module.weight != 0).sum().item()
        
        pruning_stats['sparsity_achieved'] = 1.0 - (
            pruning_stats['remaining_params'] / pruning_stats['original_params']
        )
        
        return model_copy, pruning_stats
    
    def _structured_pruning(
        self, 
        model: nn.Module, 
        importance_scores: Optional[Dict[str, torch.Tensor]]
    ) -> Tuple[nn.Module, Dict[str, Any]]:
        """구조적 프루닝 (채널/필터 단위)"""
        import torch.nn.utils.prune as prune
        import copy
        
        model_copy = copy.deepcopy(model)
        pruning_stats = {
            'pruned_layers': [],
            'original_params': 0,
            'remaining_params': 0,
            'sparsity_achieved': 0.0
        }
        
        for name, module in model_copy.named_modules():
            if isinstance(module, (nn.Linear, nn.Conv1d, nn.Conv2d)):
                original_params = module.weight.numel()
                pruning_stats['original_params'] += original_params
                
                # 구조적 프루닝 (L2 norm 기반)
                if isinstance(module, nn.Linear):
                    prune.ln_structured(
                        module, name='weight', amount=self.sparsity, n=2, dim=0
                    )
                elif isinstance(module, (nn.Conv1d, nn.Conv2d)):
                    prune.ln_structured(
                        module, name='weight', amount=self.sparsity, n=2, dim=0
                    )
                
                prune.remove(module, 'weight')
                pruning_stats['remaining_params'] += module.weight.numel()
                pruning_stats['pruned_layers'].append(name)
        
        if pruning_stats['original_params'] > 0:
            pruning_stats['sparsity_achieved'] = 1.0 - (
                pruning_stats['remaining_params'] / pruning_stats['original_params']
            )
        
        return model_copy, pruning_stats
    
    def calculate_importance_scores(
        self, 
        model: nn.Module, 
        dataloader: torch.utils.data.DataLoader,
        criterion: nn.Module
    ) -> Dict[str, torch.Tensor]:
        """레이어별 중요도 점수 계산"""
        importance_scores = {}
        
        model.eval()
        
        for name, module in model.named_modules():
            if isinstance(module, (nn.Linear, nn.Conv1d, nn.Conv2d)):
                # 그래디언트 기반 중요도 계산
                gradients = []
                
                for batch_idx, (data, target) in enumerate(dataloader):
                    if batch_idx >= 10:  # 샘플링
                        break
                    
                    model.zero_grad()
                    output = model(data)
                    loss = criterion(output, target)
                    loss.backward()
                    
                    if module.weight.grad is not None:
                        gradients.append(module.weight.grad.abs().clone())
                
                if gradients:
                    # 평균 그래디언트 크기를 중요도로 사용
                    avg_gradient = torch.stack(gradients).mean(dim=0)
                    importance_scores[name] = avg_gradient
        
        return importance_scores